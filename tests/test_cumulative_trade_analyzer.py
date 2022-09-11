from decimal import Decimal

import pandas as pd
import pytest

from bitshares_tradehistory_analyzer.ccgains_helper import Trade, TradeKind
from bitshares_tradehistory_analyzer.cumulative_trade_analyzer import (
    ZERO,
    AssetTransferStats,
    CumulativeAnalyzer,
    PairTradeStats,
    pair_from_trade,
)


@pytest.fixture()
def analyzer():
    return CumulativeAnalyzer()


def test_pair_trade_stats_dict_access():
    stats1 = PairTradeStats(spent_asset="USDT", acquired_asset="BTC")
    stats2 = PairTradeStats(spent_asset="USDT", acquired_asset="ETH")
    stats = {stats1.pair: stats1, stats2.pair: stats2}
    assert stats["USDT-BTC"] is stats1


def test_process_deposit(analyzer):
    ts = pd.Timestamp("2021-01-01", tz="UTC")
    trade = Trade(
        kind=TradeKind.DEPOSIT.value,
        dtime=ts,
        buy_currency="BTC",
        buy_amount=Decimal("0.1"),
        sell_currency=None,
        sell_amount=ZERO,
    )
    analyzer.process_transfer(trade)
    stats = analyzer.transfer_stats[trade.buycur]
    assert stats.deposit_amount == Decimal("0.1")
    assert stats.last_transfer_timestamp == ts


def test_process_withdrawal(analyzer):
    ts = pd.Timestamp("2021-01-01", tz="UTC")
    trade = Trade(
        kind=TradeKind.WITHDRAWAL.value,
        dtime=ts,
        sell_currency="BTC",
        sell_amount=Decimal("0.1"),
        buy_currency=None,
        buy_amount=ZERO,
    )
    analyzer.process_transfer(trade)
    stats = analyzer.transfer_stats[trade.sellcur]
    assert stats.withdraw_amount == Decimal("0.1")
    assert stats.last_transfer_timestamp == ts


def test_process_trade(analyzer):
    ts = pd.Timestamp("2021-01-01", tz="UTC")
    trade = Trade(
        kind=TradeKind.TRADE.value,
        dtime=ts,
        buy_currency="BTC",
        buy_amount=Decimal("0.1"),
        sell_currency="USDT",
        sell_amount=Decimal("9000"),
    )
    analyzer.process_trade(trade)
    pair = pair_from_trade(trade)
    stats = analyzer.trade_stats[pair]
    assert stats.spent_amount == Decimal("9000")
    assert stats.acquired_amount == Decimal("0.1")
    assert stats.spent_asset == "USDT"
    assert stats.acquired_asset == "BTC"
    assert stats.last_trade_timestamp == ts


def test_transfer_results(analyzer):
    analyzer.transfer_stats = {
        "BTC": AssetTransferStats(asset="BTC", deposit_amount=Decimal("3"), withdraw_amount=Decimal("2"))
    }
    df = analyzer.transfer_results
    assert df is not None
    btc_result = df.loc[df["Asset"] == "BTC"]
    assert btc_result["Deposited"].item() == Decimal("3")
    assert btc_result["Withdrawn"].item() == Decimal("2")


def test_trade_results(analyzer):
    analyzer.trade_stats = {
        "USDT-BTC": PairTradeStats(
            spent_asset="USDT", acquired_asset="BTC", spent_amount=Decimal("9000"), acquired_amount=Decimal("1")
        )
    }
    df = analyzer.trade_results
    assert df is not None
    btc_result = df.loc[df["Acquired Asset"] == "BTC"]
    assert btc_result["Spent Amount"].item() == Decimal("9000")


def test_run_analysis_time_ranged(analyzer):
    start = pd.Timestamp("2021-01-01", tz="UTC")
    end = pd.Timestamp("2021-06-01", tz="UTC")
    trade_ts_before_start = start - pd.Timedelta(hours=1)
    trade_ts_in_between = pd.Timestamp("2021-03-01", tz="UTC")
    trade_ts_after_end = end + pd.Timedelta(hours=1)
    for ts in (trade_ts_before_start, start, trade_ts_in_between, end, trade_ts_after_end):
        trade = Trade(
            kind=TradeKind.DEPOSIT.value,
            dtime=ts,
            buy_currency="BTC",
            buy_amount=Decimal("0.1"),
            sell_currency=None,
            sell_amount=ZERO,
        )
        analyzer.th.tlist.append(trade)
    analyzer.run_analysis(start, end)
    stats = analyzer.transfer_stats["BTC"]
    assert stats.deposit_amount == Decimal("0.2")
    assert stats.last_transfer_timestamp == trade_ts_in_between
