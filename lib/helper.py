import ccgains
import pandas as pd

from decimal import Decimal
from dateutil import tz

import logging
log = logging.getLogger('ccgains')

def _parse_trade(str_list, param_locs, default_timezone):
    """ 1-1 copy from ccgains
    """
    # make a dict:
    if not isinstance(param_locs, dict):
        varnames = Trade.__init__.__code__.co_varnames[1:12]
        param_locs = dict(
            (varnames[i], p) for i, p in enumerate(param_locs))

    pdict = {}
    for key, val in param_locs.items():
        if isinstance(val, int):
            if val == -1:
                pdict[key] = ''
            else:
                pdict[key] = str_list[val].strip('" \n\t')
        elif callable(val):
            pdict[key] = val(str_list)
        else:
            pdict[key] = val

    return Trade(default_timezone=default_timezone, **pdict)

class Trade(ccgains.Trade):
    """ Override handling of fee currency for bitshares
    """
    def __init__(
            self, kind, dtime, buy_currency, buy_amount,
            sell_currency, sell_amount, fee_currency='', fee_amount=0,
            exchange='', mark='', comment='', default_timezone=None):
        self.kind = kind
        if buy_amount:
            self.buyval = Decimal(buy_amount)
        else:
            self.buyval = Decimal()
        self.buycur = buy_currency
        if sell_amount:
            self.sellval = Decimal(sell_amount)
        else:
            self.sellval = Decimal()
        self.sellcur = sell_currency
        if self.sellval < 0 and self.buyval < 0:
            raise ValueError(
                    'Ambiguity: Only one of buy_amount or '
                    'sell_amount may be negative')
        elif self.buyval < 0:
            self.buyval, self.sellval = self.sellval, abs(self.buyval)
            self.buycur, self.sellcur = self.sellcur, self.buycur
        else:
            self.sellval = abs(self.sellval)

        if not fee_amount:
            self.feeval = Decimal()
            if fee_currency != self.sellcur and self.buycur:
                self.feecur = self.buycur
            else:
                self.feecur = self.sellcur
        else:
            self.feeval = abs(Decimal(fee_amount))
            self.feecur = fee_currency
        self.exchange = exchange
        self.mark = mark
        self.comment = comment
        # save the time as pandas.Timestamp object:
        if isinstance(dtime, (float, int)):
            # unix timestamp
            self.dtime = pd.Timestamp(dtime, unit='s').tz_localize('UTC')
        else:
            self.dtime = pd.Timestamp(dtime)
        # add default timezone if not included:
        if self.dtime.tzinfo is None:
            self.dtime = self.dtime.tz_localize(
                tz.tzlocal() if default_timezone is None else default_timezone)
        # internally, dtime is saved as UTC time:
        self.dtime = self.dtime.tz_convert('UTC')

        if (self.feeval > 0
                and self.feecur != buy_currency
                and self.feecur != sell_currency):
            # Pretend there is no fee
            # TODO: implement more elegant solution
            log.warning('Fee in foreign currency: {} {}'.format(self.feecur, self.feeval))
            self.feeval = 0

class TradeHistory(ccgains.TradeHistory):

    def append_csv(
            self, file_name, param_locs=range(11), delimiter=',', skiprows=1,
            default_timezone=None):
        """ 1-1 copy from ccgains
        """
        with open(file_name) as f:
            csvlines = f.readlines()

        if default_timezone is None:
            default_timezone = tz.tzlocal()

        numtrades = len(self.tlist)

        # convert input lines to Trades:
        for csvline in csvlines[skiprows:]:
            line = csvline.split(delimiter)
            if not line:
                # ignore empty lines
                continue
            self.tlist.append(
                _parse_trade(line, param_locs, default_timezone))

        log.info("Loaded %i transactions from %s",
                 len(self.tlist) - numtrades, file_name)
        # trades must be sorted:
        self.tlist.sort(key=self._trade_sort_key, reverse=False)


