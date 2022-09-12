import copy
import json
import logging
from decimal import Decimal

from bitshares.account import Account
from bitshares.amount import Amount
from bitshares.asset import Asset

from .consts import LINE_DICT_TEMPLATE

log = logging.getLogger(__name__)


class Parser:
    """Entries parser

    :param BitShares bitshares_instance:
    :param Account account:
    """

    def __init__(self, bitshares_instance, account):
        self.bitshares = bitshares_instance
        self.account = Account(account, bitshares_instance=self.bitshares)

    def load_op(self, entry):
        """Try to load operation from account history entry

        :param dict entry:
        """
        try:
            op = json.loads(entry['operation_history']['op'])[1]
        except json.decoder.JSONDecodeError:
            try:
                op = entry['operation_history']['op_object']
            except TypeError:
                raise ValueError('Could not find op data in op %s', entry['account_history']['operation_id'])
        return op

    def parse_transfer_entry(self, entry):
        """Parse single transfer entry into a dict object suitable for writing line

        :param dict entry: elastic wrapper entry
        :return: dict object suitable for writing line
        """

        op_id = entry['account_history']['operation_id']
        op_date = entry['block_data']['block_time']
        op = self.load_op(entry)

        data = copy.deepcopy(LINE_DICT_TEMPLATE)

        raw_amount = op['amount'] if 'amount' in op else op['amount_']
        amount = Amount(raw_amount, bitshares_instance=self.bitshares)
        from_account = Account(op['from'], bitshares_instance=self.bitshares)
        to_account = Account(op['to'], bitshares_instance=self.bitshares)
        fee = Amount(op['fee'], bitshares_instance=self.bitshares)
        log.info('Transfer: {} -> {}, {}'.format(from_account.name, to_account.name, amount))

        if from_account.name == self.account.name:
            data['kind'] = 'Withdrawal'
            data['sell_cur'] = amount.symbol
            data['sell_amount'] = amount.amount
            data['fee_cur'] = fee.symbol
            data['fee_amount'] = fee.amount
        else:
            data['kind'] = 'Deposit'
            data['buy_cur'] = amount.symbol
            data['buy_amount'] = amount.amount

        data['comment'] = op_id
        data['date'] = op_date

        return data

    def parse_trade_entry(self, entry):
        """Parse single trade entry (fill order) into a dict object suitable for writing line

        :param dict entry: elastic wrapper entry
        :return: dict object suitable for writing line
        """

        op_id = entry['account_history']['operation_id']
        op = self.load_op(entry)

        data = copy.deepcopy(LINE_DICT_TEMPLATE)

        sell_asset = Asset(op['pays']['asset_id'], bitshares_instance=self.bitshares)
        sell_amount = Decimal(op['pays']['amount']).scaleb(-sell_asset['precision'])
        buy_asset = Asset(op['receives']['asset_id'], bitshares_instance=self.bitshares)
        buy_amount = Decimal(op['receives']['amount']).scaleb(-buy_asset['precision'])
        fee_asset = Asset(op['fee']['asset_id'], bitshares_instance=self.bitshares)
        fee_amount = Decimal(op['fee']['amount']).scaleb(-fee_asset['precision'])

        # Subtract fee from buy_amount
        # For ccgains, any fees for the transaction should already have been subtracted from *amount*, but included
        # in *cost*.
        if fee_asset.symbol == buy_asset.symbol:
            buy_amount -= fee_amount

        data['kind'] = 'Trade'
        data['sell_cur'] = sell_asset.symbol
        data['sell_amount'] = sell_amount
        data['buy_cur'] = buy_asset.symbol
        data['buy_amount'] = buy_amount
        data['fee_cur'] = fee_asset.symbol
        data['fee_amount'] = fee_amount
        data['comment'] = op_id
        data['order_id'] = op['order_id']
        data['prec'] = max(sell_asset['precision'], buy_asset['precision'])

        # Prevent division by zero
        price = Decimal('0')
        price_inverted = Decimal('0')
        if sell_amount and buy_amount:
            price = buy_amount / sell_amount
            price_inverted = sell_amount / buy_amount

        data['price'] = price
        data['price_inverted'] = price_inverted
        data['date'] = entry['block_data']['block_time']

        return data
