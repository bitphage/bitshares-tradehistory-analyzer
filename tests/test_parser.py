import pytest
import json

from bitshares_tradehistory_analyzer.parser import Parser


@pytest.fixture(scope='module')
def account_name():
    return 'aleks'


@pytest.fixture(scope='module')
def parser(bitshares, account_name):
    return Parser(bitshares, account_name)


@pytest.fixture()
def transfer_entry():
    with open('tests/fixture_data/transfer.json') as f:
        entry = json.load(f)[0]
    return entry


@pytest.fixture()
def transfer_entry_null_op_object():
    with open('tests/fixture_data/transfer_null_op_object.json') as f:
        entry = json.load(f)
    return entry


@pytest.fixture()
def trade_entry():
    with open('tests/fixture_data/trade.json') as f:
        entry = json.load(f)[0]
    return entry


@pytest.fixture()
def trade_entry_null_op_object():
    with open('tests/fixture_data/trade_null_op_object.json') as f:
        entry = json.load(f)
    return entry


def test_parse_transfer_entry(parser, transfer_entry, transfer_entry_null_op_object):
    data = parser.parse_transfer_entry(transfer_entry)
    assert data['buy_amount'] > 0

    data = parser.parse_transfer_entry(transfer_entry_null_op_object)
    assert data['buy_amount'] > 0


def test_parse_trade_entry(parser, trade_entry, trade_entry_null_op_object):
    data = parser.parse_trade_entry(trade_entry)
    assert data['buy_amount'] > 0

    data = parser.parse_trade_entry(trade_entry_null_op_object)
    assert data['buy_amount'] > 0
