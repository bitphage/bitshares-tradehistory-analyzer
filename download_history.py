#!/usr/bin/env python

import sys
import argparse
import logging
import yaml
import requests

from pprint import pprint

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

        pprint(payload)
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

def main():

    parser = argparse.ArgumentParser(
            description='',
            epilog='Report bugs to: ')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='enable debug output'),
    parser.add_argument('-c', '--config', default='./config.yml',
                        help='specify custom path for config file')
    parser.add_argument('-u', '--url', default='https://wrapper.elasticsearch.bitshares.ws/',
                        help='URL of elasticsearch wrapper plugin')
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

    # Known wrappers
    # https://wrapper.elasticsearch.bitshares.ws/
    # http://bts-es.clockwork.gr:5000/

    bitshares = BitShares(node=conf['node_bts'])
    account = Account(args.account, bitshares_instance=bitshares)
    wrapper = Wrapper(args.url, account['id'])

    # CSV format is ccGains generic format
    header = 'Kind,Date,Buy currency,Buy amount,Sell currency,Sell amount,Fee currency,Fee amount,Exchange,Mark,Comment\n'

    ##################
    # Export transfers
    ##################
    transfers = wrapper.get_transfers()
    filename = 'transfers-{}.csv'.format(account.name)
    f = open(filename, 'w')
    f.write(header)

    for entry in transfers:
        line_dict = LINE_TEMPLATE
        line_dict['date'] = entry['block_data']['block_time']
        op = entry['operation_history']['op_object']

        amount = Amount(op['amount_'], bitshares_instance=bitshares)
        from_account = Account(op['from'], bitshares_instance=bitshares)
        to_account = Account(op['to'], bitshares_instance=bitshares)
        # TODO: transfer fee
        
        if from_account.name == account.name:
            line_dict['kind'] = 'Withdrawal'
            line_dict['sell_cur'] = amount.symbol
            line_dict['sell_amount'] = amount.amount
        else:
            line_dict['kind'] = 'Deposit'
            line_dict['buy_cur'] = amount.symbol
            line_dict['buy_amount'] = amount.amount

        line = ('{kind},{date},{buy_cur},{buy_amount},{sell_cur},{sell_amount},{fee_cur},{fee_amount},{exchange},'
                '{mark},{comment}\n'.format(**line_dict))
        f.write(line)
    f.close()

    ########################
    # Export trading history
    ########################
    filename = 'trades-{}.csv'.format(account.name)
    f = open(filename, 'w')
    f.write(header)

    trades = wrapper.get_trades()
    prev_op_id = ''
    counter = 0
    while trades:
        for entry in trades:
            op_id = entry['account_history']['operation_id']
            if op_id == prev_op_id:
                log.warning('op id intersection')

            line_dict = LINE_TEMPLATE
            line_dict['date'] = entry['block_data']['block_time']
            op = entry['operation_history']['op_object']
            
            sell = Amount(op['pays'], bitshares_instance=bitshares)
            buy = Amount(op['receives'], bitshares_instance=bitshares)
            fee = Amount(op['fee'], bitshares_instance=bitshares)

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
            counter += 1
        # Elastic wrapper return only limited amount of items, so iterate until the end
        prev_op_id = op_id
        #trades = wrapper.get_trades(from_date=line_dict['date'])
        trades = wrapper.get_trades(from_=counter)
    f.close()

    # TODO: store operation_id. Count number of records to use `from_`. Do additional comparison by operation_id to
    # correctly determine from where to continue

if __name__ == '__main__':
    main()
