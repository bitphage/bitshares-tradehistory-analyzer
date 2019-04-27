#!/usr/bin/env python

import os.path
import argparse
import logging
import random
import copy

from ruamel.yaml import YAML
from bitshares import BitShares
from decimal import Decimal

from bitshares_tradehistory_analyzer.wrapper import Wrapper
from bitshares_tradehistory_analyzer.parser import Parser
from bitshares_tradehistory_analyzer.consts import LINE_TEMPLATE, LINE_DICT_TEMPLATE, HEADER

log = logging.getLogger('bitshares_tradehistory_analyzer')

SELL_LOG_TEMPLATE = (
    'Sold {sell_amount} {sell_cur} for {buy_amount} {buy_cur} @ {price:.{prec}} {buy_cur}/{sell_cur}'
    ' ({price_inverted:.{prec}f} {sell_cur}/{buy_cur})'
)


def get_continuation_point(filename):
    """ Check csv-file for number of records and last op id

        :param str filename: path to the file to check
        :return: str, str: datetime string of last record and last op id
    """
    dtime = '2010-10-10'
    last_op_id = None

    if os.path.isfile(filename) and os.path.getsize(filename) > 0:
        with open(filename, 'rb') as fd:
            # Move reading position 2 bytes before EOF
            fd.seek(-2, os.SEEK_END)
            # Jump backward until EOL found
            while fd.read(1) != b"\n":
                try:
                    fd.seek(-2, os.SEEK_CUR)
                except OSError:
                    # Probably file is just one-line
                    return dtime, last_op_id

            # Take last line into list object
            last_line = fd.readline().decode('utf-8').rstrip('\n').split(',')

        dtime = last_line[1]
        last_op_id = last_line[-1].split()[-1]
        log.info('Continuing {} from {}, op id: {}'.format(filename, dtime, last_op_id))

    return dtime, last_op_id


def main():

    parser = argparse.ArgumentParser(
        description='Export bitshares transfer and trading history for an account',
        epilog='Report bugs to: https://github.com/bitfag/bitshares-tradehistory-analyzer/issues',
    )
    parser.add_argument('-d', '--debug', action='store_true', help='enable debug output'),
    parser.add_argument('-c', '--config', default='./config.yml', help='specify custom path for config file')
    parser.add_argument('-u', '--url', help='override URL of elasticsearch wrapper plugin')
    parser.add_argument('--no-aggregate', action='store_true', help='do not aggregate trades by same order')
    parser.add_argument('account')
    args = parser.parse_args()

    # create logger
    if args.debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    log.addHandler(handler)

    # parse config
    yaml = YAML(typ="safe")
    with open(args.config, 'r') as ymlfile:
        conf = yaml.load(ymlfile)

    bitshares = BitShares(node=conf['nodes'])
    parser = Parser(bitshares, args.account)

    if args.url:
        wrapper_url = args.url
    else:
        wrapper_url = random.choice(conf['wrappers'])
    log.info('Using wrapper {}'.format(wrapper_url))
    wrapper = Wrapper(wrapper_url, parser.account['id'])

    ##################
    # Export transfers
    ##################
    filename = 'transfers-{}.csv'.format(args.account)
    dtime, last_op_id = get_continuation_point(filename)
    if not (dtime and last_op_id):
        f = open(filename, 'w')
        f.write(HEADER)
    else:
        f = open(filename, 'a')

    history = wrapper.get_transfers(from_date=dtime)
    while history:
        for entry in history:
            op_id = entry['account_history']['operation_id']
            op_date = entry['block_data']['block_time']
            # Skip entries until last_op_id found
            if last_op_id and op_id != last_op_id:
                log.debug('skipping entry {}'.format(entry))
                continue
            elif last_op_id and op_id == last_op_id:
                # Ok, last_op_id found, let's start to write entries from the next one
                last_op_id = None
                log.debug('skipping entry {}'.format(entry))
                continue

            parsed_data = parser.parse_transfer_entry(entry)
            f.write(LINE_TEMPLATE.format(**parsed_data))

        # Remember last op id for the next chunk
        last_op_id = op_id

        # Break `while` loop on least history chunk
        if len(history) < wrapper.size:
            break

        # Get next data chunk
        history = wrapper.get_transfers(from_date=op_date)
    f.close()

    ########################
    # Export trading history
    ########################
    filename = 'trades-{}.csv'.format(args.account)
    dtime, last_op_id = get_continuation_point(filename)
    if not (dtime and last_op_id):
        f = open(filename, 'w')
        f.write(HEADER)
    else:
        f = open(filename, 'a')

    history = wrapper.get_trades(from_date=dtime)
    aggregated_line = copy.deepcopy(LINE_DICT_TEMPLATE)
    while history:
        for entry in history:
            op_id = entry['account_history']['operation_id']
            op_date = entry['block_data']['block_time']
            log.debug('Processing op {} @ {}'.format(op_date, op_id))
            # Skip entries until last_op_id found
            if last_op_id and op_id != last_op_id:
                log.debug('skipping earlier op {} < {}'.format(op_id, last_op_id))
                continue
            elif last_op_id and op_id == last_op_id:
                last_op_id = None
                continue

            line_dict = parser.parse_trade_entry(entry)

            if args.no_aggregate:
                log.info(SELL_LOG_TEMPLATE.format(**line_dict))
                f.write(LINE_TEMPLATE.format(**line_dict))
                continue

            if not aggregated_line['order_id']:
                # Aggregated line is empty, store current entry data
                aggregated_line = line_dict
            elif aggregated_line['order_id'] == op['order_id']:
                # If selling same asset at the same rate, just aggregate the trades
                aggregated_line['date'] = line_dict['date']
                aggregated_line['sell_amount'] += sell_amount
                aggregated_line['buy_amount'] += buy_amount
                aggregated_line['fee_amount'] += fee_amount
                aggregated_line['comment'] += ' {}'.format(op_id)
                # Prevent division by zero
                price = Decimal('0')
                price_inverted = Decimal('0')
                if aggregated_line['sell_amount'] and aggregated_line['buy_amount']:
                    price = aggregated_line['buy_amount'] / aggregated_line['sell_amount']
                    price_inverted = aggregated_line['sell_amount'] / aggregated_line['buy_amount']
                aggregated_line['price'] = price
                aggregated_line['price_inverted'] = price_inverted
            else:
                log.info(SELL_LOG_TEMPLATE.format(**line_dict))
                # Write current aggregated line
                f.write(LINE_TEMPLATE.format(**aggregated_line))
                aggregated_line = copy.deepcopy(LINE_DICT_TEMPLATE)
                # Save current entry into new aggregation object
                aggregated_line = line_dict

        # Remember last op id for the next chunk
        last_op_id = op_id

        # Break `while` loop on least history chunk
        if len(history) < wrapper.size:
            break

        # Get next data chunk
        history = wrapper.get_trades(from_date=op_date)

    # At the end, write remaining line
    if aggregated_line['order_id']:
        log.info(SELL_LOG_TEMPLATE.format(**aggregated_line))
        f.write(LINE_TEMPLATE.format(**aggregated_line))
    f.close()


if __name__ == '__main__':
    main()
