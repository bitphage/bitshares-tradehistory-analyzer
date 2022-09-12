import json

import pytest

from bitshares_tradehistory_analyzer.parser import Parser


def load_full_json(filename):
    with open(filename) as f:
        entry = json.load(f)
    return entry


def load_first_json_entry(filename):
    return load_full_json(filename)[0]


@pytest.fixture(scope='module')
def account_name():
    return 'aleks'


@pytest.fixture(scope='module')
def parser(bitshares, account_name):
    return Parser(bitshares, account_name)


@pytest.fixture()
def transfer_entry():
    return load_first_json_entry('tests/fixture_data/transfer.json')


@pytest.fixture()
def transfer_entry_null_op_object():
    return load_full_json('tests/fixture_data/transfer_null_op_object.json')


@pytest.fixture()
def trade_entry():
    return load_first_json_entry('tests/fixture_data/trade.json')


@pytest.fixture()
def trade_entry_null_op_object():
    return load_full_json('tests/fixture_data/trade_null_op_object.json')


@pytest.fixture()
def settlement_regular_entry():
    return load_first_json_entry('tests/fixture_data/settlement_regular.json')


@pytest.fixture()
def settlement_gs_entry():
    return load_first_json_entry('tests/fixture_data/settlement_gs.json')


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


def test_parse_regular_settle_entry(parser, settlement_regular_entry):
    data = parser.parse_settle_entry(settlement_regular_entry)
    assert data['buy_amount'] > 0


def test_parse_gs_settle_entry(parser, settlement_gs_entry):
    data = parser.parse_settle_entry(settlement_gs_entry)
    assert data['buy_amount'] > 0
    assert data['sell_amount'] > 0
