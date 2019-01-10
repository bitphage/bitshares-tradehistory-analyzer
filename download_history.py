#!/usr/bin/env python

import os.path
import sys
import argparse
import logging
import yaml
import requests
import random

from bitshares import BitShares
from bitshares.account import Account
from bitshares.amount import Amount

log = logging.getLogger(__name__)

LINE_TEMPLATE = {
                    'kind': '',
                    'buy_cur': '',
                    'buy_amount': 0,
                    'sell_cur': '',
                    'sell_amount': 0,
                    'fee_cur': '',
                    'fee_amount': 0,
                    'exchange': 'Bitshares',
                    'mark': -1,
                    'comment': ''
                }

# CSV format is ccGains generic format
HEADER = 'Kind,Date,Buy currency,Buy amount,Sell currency,Sell amount,Fee currency,Fee amount,Exchange,Mark,Comment\n'

class Wrapper():
    """ Wrapper for querying bitshares elasticsearch wrapper
    """
    def __init__(self, url, account_id):
        self.url = url
        self.account_id = account_id

    def _query(self, params, *args, **kwargs):
        url = self.url + 'get_account_history'
        payload = {
                    'account_id': self.account_id,
                    'size': 100,
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

def get_write_point(filename):
    """ Check csv-file for number of records and last op id

        :param str filename: path to the file to check
        :return: int, str: number of records and last op id
    """
    prev_op_id = None
    record_num = 0

    if os.path.isfile(filename):
        line_counter = 0
        f = open(filename, 'r')
        for line in f:
            line_counter += 1
        f.close()

        prev_op_id = line.split(',')[-1].rstrip('\n')
        record_num = line_counter - 1
        log.debug('records: {}, last op id: {}'.format(record_num, prev_op_id))

    return record_num, prev_op_id

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
    with open(args.config, 'r') as ymlfile:
        conf = yaml.load(ymlfile)

    bitshares = BitShares(node=conf['nodes'])
    account = Account(args.account, bitshares_instance=bitshares)

    if args.url:
        wrapper_url = args.url
    else:
        wrapper_url = random.choice(conf['wrappers'])
    log.debug('Using wrapper {}'.format(wrapper_url))
    wrapper = Wrapper(wrapper_url, account['id'])

    ##################
    # Export transfers
    ##################
    filename = 'transfers-{}.csv'.format(account.name)
    record_num, prev_op_id = get_write_point(filename)
    if not (record_num and prev_op_id):
        record_num = 0
        f = open(filename, 'w')
        f.write(HEADER)
    else:
        f = open(filename, 'a')

    history = wrapper.get_transfers(from_=record_num)
    while history:
        for entry in history:
            op_id = entry['account_history']['operation_id']
            if op_id == prev_op_id:
                log.warning('op id intersection')
                continue

            line_dict = LINE_TEMPLATE
            line_dict['date'] = entry['block_data']['block_time']
            op = entry['operation_history']['op_object']

            amount = Amount(op['amount_'], bitshares_instance=bitshares)
            from_account = Account(op['from'], bitshares_instance=bitshares)
            to_account = Account(op['to'], bitshares_instance=bitshares)
            fee = Amount(op['fee'], bitshares_instance=bitshares)

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
            record_num += 1
        prev_op_id = op_id
        history = wrapper.get_transfers(from_=record_num)
    f.close()

    ########################
    # Export trading history
    ########################
    filename = 'trades-{}.csv'.format(account.name)
    record_num, prev_op_id = get_write_point(filename)
    if not (record_num and prev_op_id):
        record_num = 0
        f = open(filename, 'w')
        f.write(HEADER)
    else:
        f = open(filename, 'a')

    history = wrapper.get_trades(from_=record_num)
    while history:
        for entry in history:
            op_id = entry['account_history']['operation_id']
            if op_id == prev_op_id:
                log.warning('op id intersection')
                continue

            line_dict = LINE_TEMPLATE
            line_dict['date'] = entry['block_data']['block_time']
            op = entry['operation_history']['op_object']
            
            sell = Amount(op['pays'], bitshares_instance=bitshares)
            buy = Amount(op['receives'], bitshares_instance=bitshares)
            fee = Amount(op['fee'], bitshares_instance=bitshares)

            # Subtract fee from buy_amount
            if fee.symbol == buy.symbol:
                buy['amount'] -= fee.amount

            line_dict['kind'] = 'Trade'
            line_dict['sell_cur'] = sell.symbol
            line_dict['sell_amount'] = sell.amount
            line_dict['buy_cur'] = buy.symbol
            line_dict['buy_amount'] = buy.amount
            line_dict['fee_cur'] = fee.symbol
            line_dict['fee_amount'] = fee.amount
            line_dict['comment'] = op_id

            line = ('{kind},{date},{buy_cur},{buy_amount},{sell_cur},{sell_amount},{fee_cur},{fee_amount},{exchange},'
                    '{mark},{comment}\n'.format(**line_dict))
            f.write(line)
            record_num += 1
        # Elastic wrapper return only limited amount of items, so iterate until the end
        prev_op_id = op_id
        history = wrapper.get_trades(from_=record_num)
    f.close()

if __name__ == '__main__':
    main()
