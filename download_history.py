#!/usr/bin/env python

import os.path
import sys
import argparse
import logging
import requests
import random
import copy

from ruamel.yaml import YAML
from decimal import Decimal
from bitshares import BitShares
from bitshares.account import Account
from bitshares.amount import Amount
from bitshares.asset import Asset

log = logging.getLogger(__name__)

LINE_DICT_TEMPLATE = {
                        'kind': '',
                        'buy_cur': '',
                        'buy_amount': 0,
                        'sell_cur': '',
                        'sell_amount': 0,
                        'fee_cur': '',
                        'fee_amount': 0,
                        'exchange': 'Bitshares',
                        'mark': -1,
                        'comment': '',
                        'order_id': '',
                    }

# CSV format is ccGains generic format
HEADER = 'Kind,Date,Buy currency,Buy amount,Sell currency,Sell amount,Fee currency,Fee amount,Exchange,Mark,Comment\n'

LINE_TEMPLATE = ('{kind},{date},{buy_cur},{buy_amount},{sell_cur},{sell_amount},{fee_cur},{fee_amount},{exchange},'
                 '{mark},{comment}\n')

SELL_LOG_TEMPLATE = ('Sold {sell_amount} {sell_cur} for {buy_amount} {buy_cur} @ {price:.{prec}} {buy_cur}/{sell_cur}'
                     ' ({price_inverted:.{prec}f} {sell_cur}/{buy_cur})')

class Wrapper():
    """ Wrapper for querying bitshares elasticsearch wrapper
    """
    def __init__(self, url, account_id):
        self.url = url
        self.account_id = account_id
        self.size = 100

    def _query(self, params, *args, **kwargs):
        url = self.url + 'get_account_history'
        payload = {
                    'account_id': self.account_id,
                    'size': self.size,
                    'operation_type': 0,
                    'sort_by': 'block_data.block_time',
                    'type': 'data',
                    'agg_field': 'operation_type'
                    }
        payload.update(params)

        if kwargs:
            payload.update(kwargs)

        r = requests.get(url, params=payload)
        return r.json()

    def get_transfers(self, *args, **kwargs):
        params = {}
        params['operation_type'] = 0
        return self._query(params, *args, **kwargs)

    def get_trades(self, *args, **kwargs):
        params = {}
        params['operation_type'] = 4
        return self._query(params, *args, **kwargs)

def get_continuation_point(filename):
    """ Check csv-file for number of records and last op id

        :param str filename: path to the file to check
        :return: str, str: datetime string of last record and last op id
    """
    dtime = '2010-10-10'
    last_op_id = None

    if os.path.isfile(filename):
        with open(filename, 'rb') as fd:
            # Move reading position 2 bytes before EOF
            fd.seek(-2, os.SEEK_END)
            # Jump backward until EOL found
            while fd.read(1) != b"\n":
                fd.seek(-2, os.SEEK_CUR)

            # Take last line into list object
            last_line = fd.readline().decode('utf-8').rstrip('\n').split(',')

        dtime = last_line[1]
        last_op_id = last_line[-1].split()[-1]
        log.info('Continuing {} from {}, op id: {}'.format(filename, dtime, last_op_id))

    return dtime, last_op_id

def main():

    parser = argparse.ArgumentParser(
            description='',
            epilog='Report bugs to: ')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='enable debug output'),
    parser.add_argument('-c', '--config', default='./config.yml',
                        help='specify custom path for config file')
    parser.add_argument('-u', '--url',
                        help='override URL of elasticsearch wrapper plugin')
    parser.add_argument('--no-aggregate', action='store_true',
                        help='do not aggregate trades by same order')
    parser.add_argument('account')
    args = parser.parse_args()

    # create logger
    if args.debug == True:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    log.addHandler(handler)

    # parse config
    yaml=YAML(typ="safe")
    with open(args.config, 'r') as ymlfile:
        conf = yaml.load(ymlfile)

    bitshares = BitShares(node=conf['nodes'])
    account = Account(args.account, bitshares_instance=bitshares)

    if args.url:
        wrapper_url = args.url
    else:
        wrapper_url = random.choice(conf['wrappers'])
    log.info('Using wrapper {}'.format(wrapper_url))
    wrapper = Wrapper(wrapper_url, account['id'])

    ##################
    # Export transfers
    ##################
    filename = 'transfers-{}.csv'.format(account.name)
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

            line_dict = copy.deepcopy(LINE_DICT_TEMPLATE)
            line_dict['date'] = op_date
            op = entry['operation_history']['op_object']

            amount = Amount(op['amount_'], bitshares_instance=bitshares)
            from_account = Account(op['from'], bitshares_instance=bitshares)
            to_account = Account(op['to'], bitshares_instance=bitshares)
            fee = Amount(op['fee'], bitshares_instance=bitshares)
            log.info('Transfer: {} -> {}, {}'.format(from_account.name, to_account.name, amount))

            if from_account.name == account.name:
                line_dict['kind'] = 'Withdrawal'
                line_dict['sell_cur'] = amount.symbol
                line_dict['sell_amount'] = amount.amount
                line_dict['fee_cur'] = fee.symbol
                line_dict['fee_amount'] = fee.amount
            else:
                line_dict['kind'] = 'Deposit'
                line_dict['buy_cur'] = amount.symbol
                line_dict['buy_amount'] = amount.amount

            line_dict['comment'] = op_id

            line = ('{kind},{date},{buy_cur},{buy_amount},{sell_cur},{sell_amount},{fee_cur},{fee_amount},{exchange},'
                    '{mark},{comment}\n'.format(**line_dict))
            f.write(line)
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
    filename = 'trades-{}.csv'.format(account.name)
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
            # Skip entries until last_op_id found
            if last_op_id and op_id != last_op_id:
                log.debug('skipping entry {}'.format(entry))
                continue
            elif last_op_id and op_id == last_op_id:
                last_op_id = None
                continue

            line_dict = copy.deepcopy(LINE_DICT_TEMPLATE)
            line_dict['date'] = entry['block_data']['block_time']
            op = entry['operation_history']['op_object']
            
            sell_asset = Asset(op['pays']['asset_id'], bitshares_instance=bitshares)
            sell_amount = Decimal(op['pays']['amount']).scaleb(-sell_asset['precision'])
            buy_asset = Asset(op['receives']['asset_id'], bitshares_instance=bitshares)
            buy_amount = Decimal(op['receives']['amount']).scaleb(-buy_asset['precision'])
            fee_asset = Asset(op['fee']['asset_id'], bitshares_instance=bitshares)
            fee_amount = Decimal(op['fee']['amount']).scaleb(-fee_asset['precision'])

            # Subtract fee from buy_amount
            if fee_asset.symbol == buy_asset.symbol:
                buy_amount -= fee_amount

            line_dict['kind'] = 'Trade'
            line_dict['sell_cur'] = sell_asset.symbol
            line_dict['sell_amount'] = sell_amount
            line_dict['buy_cur'] = buy_asset.symbol
            line_dict['buy_amount'] = buy_amount
            line_dict['fee_cur'] = fee_asset.symbol
            line_dict['fee_amount'] = fee_amount
            line_dict['comment'] = op_id
            line_dict['order_id'] = op['order_id']
            line_dict['prec'] = max(sell_asset['precision'], buy_asset['precision'])

            # Prevent division by zero
            price = Decimal('0')
            price_inverted = Decimal('0')
            if sell_amount and buy_amount:
                price = buy_amount / sell_amount
                price_inverted = sell_amount / buy_amount

            line_dict['price'] = price
            line_dict['price_inverted'] = price_inverted

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
                aggregated_line['price'] = aggregated_line['buy_amount'] / aggregated_line['sell_amount']
                aggregated_line['price_inverted'] = aggregated_line['sell_amount'] / aggregated_line['buy_amount']
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
