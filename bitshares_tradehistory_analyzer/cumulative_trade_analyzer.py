from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional

import pandas as pd

from bitshares_tradehistory_analyzer.ccgains_helper import Trade, TradeHistory, TradeKind

Asset = str
AssetPair = str

ZERO = Decimal("0")


def make_pair(spent_asset: Asset, acquired_asset: Asset) -> AssetPair:
    return f"{spent_asset}-{acquired_asset}"


def pair_from_trade(trade: Trade) -> AssetPair:
    return make_pair(trade.sellcur, trade.buycur)


@dataclass
class PairTradeStats:
    spent_asset: Asset
    acquired_asset: Asset
    spent_amount: Decimal = ZERO
    acquired_amount: Decimal = ZERO
    last_trade_timestamp: pd.Timestamp = pd.Timestamp(0, unit="ms")

    @property
    def pair(self) -> AssetPair:
        return make_pair(self.spent_asset, self.acquired_asset)


@dataclass
class AssetTransferStats:
    asset: Asset
    deposit_amount: Decimal = ZERO
    withdraw_amount: Decimal = ZERO
    last_transfer_timestamp: pd.Timestamp = pd.Timestamp(0, unit="ms")


class CumulativeAnalyzer:
    """Analyzes transfers and trades and produces summary result."""

    def __init__(self):
        self.th = TradeHistory()
        self.transfer_stats: Dict[Asset, AssetTransferStats] = {}
        self.trade_stats: Dict[AssetPair, PairTradeStats] = {}

    @property
    def transfer_results(self):
        transfer_results = pd.DataFrame(
            [
                {
                    "Asset": stat.asset,
                    "Deposited": stat.deposit_amount,
                    "Withdrawn": stat.withdraw_amount,
                    "Delta": stat.deposit_amount - stat.withdraw_amount,
                    "Last Transfer Timestamp": stat.last_transfer_timestamp,
                }
                for stat in self.transfer_stats.values()
            ],
            columns=["Asset", "Deposited", "Withdrawn", "Delta", "Last Transfer Timestamp"],
        )
        return transfer_results

    @property
    def trade_results(self):
        trade_results = pd.DataFrame(
            [
                {
                    "Spent Asset": stat.spent_asset,
                    "Spent Amount": stat.spent_amount,
                    "Acquired Asset": stat.acquired_asset,
                    "Acquired Amount": stat.acquired_amount,
                    "Last Trade Timestamp": stat.last_trade_timestamp,
                }
                for stat in self.trade_stats.values()
            ],
            columns=["Spent Asset", "Spent Amount", "Acquired Asset", "Acquired Amount", "Last Trade Timestamp"],
        )
        return trade_results

    def append_csv(self, csv_file: str):
        # Note: ccgains is sorting trades on each append
        self.th.append_csv(csv_file)

    def process_transfer(self, trade: Trade):
        if trade.kind == TradeKind.DEPOSIT.value:
            asset: Asset = trade.buycur
            self.transfer_stats.setdefault(asset, AssetTransferStats(asset=asset)).deposit_amount += trade.buyval
        elif trade.kind == TradeKind.WITHDRAWAL.value:
            asset = trade.sellcur
            self.transfer_stats.setdefault(asset, AssetTransferStats(asset=asset)).withdraw_amount += trade.sellval
        else:
            raise ValueError(f"Unexpected trade kind: {trade.kind}")
        self.transfer_stats[asset].last_transfer_timestamp = trade.dtime

    def process_trade(self, trade: Trade):
        pair: AssetPair = pair_from_trade(trade)
        stats = self.trade_stats.setdefault(
            pair, PairTradeStats(spent_asset=trade.sellcur, acquired_asset=trade.buycur)
        )
        stats.acquired_amount += trade.buyval
        stats.spent_amount += trade.sellval
        stats.last_trade_timestamp = trade.dtime

    def run_analysis(self, start: Optional[pd.Timestamp] = None, end: Optional[pd.Timestamp] = None) -> None:
        self.reset_stats()
        for trade in self.th.tlist:
            if start is not None and trade.dtime < start:
                continue
            if end is not None and trade.dtime >= end:
                break
            if trade.kind == TradeKind.DEPOSIT.value:
                self.process_transfer(trade)
            elif trade.kind == TradeKind.WITHDRAWAL.value:
                self.process_transfer(trade)
            elif trade.kind == TradeKind.TRADE.value:
                self.process_trade(trade)
            else:
                raise ValueError(f"Unexpected trade kind: {trade.kind}")

    def reset_stats(self):
        self.transfer_stats.clear()
        self.trade_stats.clear()
