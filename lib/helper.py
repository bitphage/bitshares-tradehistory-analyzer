import ccgains
import pandas as pd

from decimal import Decimal
from dateutil import tz

from ccgains.bags import is_short_term
from ccgains import reports

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

class BagQueue(ccgains.BagQueue):
    """ Override:
        - rate when no relation passed
    """
    def pay(self, dtime, currency, amount, exchange, fee_ratio=0,
            custom_rate=None, report_info=None):
        self._check_order(dtime)
        amount = Decimal(amount)
        fee_ratio = Decimal(fee_ratio)
        if amount <= 0: return
        exchange = str(exchange).capitalize()
        if currency == self.currency:
            self._abort(
                'Payments with the base currency are not relevant here.')
        if exchange not in self.bags or not self.bags[exchange]:
            self._abort(
                "You don't own any funds on %s" % exchange)
        if fee_ratio < 0 or fee_ratio > 1:
            self._abort("Fee ratio must be between 0 and 1.")
        if exchange not in self.totals:
            total = 0
        else:
            total = self.totals[exchange].get(currency, 0)
        if amount > total:
            self._abort(
                "Amount to be paid ({1} {0}) is higher than total "
                "available on {3}: {2} {0}.".format(
                        currency, amount, total, exchange))
        # expenses (original cost of spent money):
        cost = Decimal()
        # expenses only of short term trades:
        st_cost = Decimal()
        # proceeds (value of spent money at dtime):
        proc = Decimal()
        # proceeds only of short term trades:
        st_proc = Decimal()
        # exchange rate at time of payment:
        rate = Decimal(0)
        if custom_rate is not None:
            rate = Decimal(custom_rate)
        elif self.relation is None:
            log.debug('Relation is not provided, will use bag price as rate')
        else:
            try:
                rate = Decimal(
                    self.relation.get_rate(dtime, currency, self.currency))
            except KeyError:
                self._abort(
                    'Could not fetch the price for currency_pair %s_%s on '
                    '%s from provided CurrencyRelation object.' % (
                            currency, self.currency, dtime))
        # due payment:
        to_pay = amount
        log.info(
            "Paying %(to_pay).8f %(curr)s from %(exchange)s "
            "(including %(fees).8f %(curr)s fees)",
            {'to_pay': to_pay, 'curr': currency,
             'exchange': exchange, 'fees': to_pay * fee_ratio})
        # Find bags with this currency and use them to pay for
        # this:
        bag_index = None
        self.sort_bags(exchange)
        while to_pay > 0:
            bag_index, bag = self.pick_bag(exchange, currency, start_index=bag_index)

            # Spend as much as possible from this bag:
            log.info("Paying with bag from %s, containing %.8f %s",
                     bag.dtime, bag.amount, bag.currency)
            spent, bcost, remainder = bag.spend(to_pay)
            log.info("Contents of bag after payment: %.8f %s (spent %.8f %s)",
                 bag.amount, bag.currency, spent, currency)

            # The proceeds are the value of spent amount at dtime:
            if not rate:
                # XXX: Fallback rate to bag price
                rate = bag.price
            thisproc = spent * rate
            # update totals for the full payment:
            proc += thisproc
            cost += bcost
            short_term = is_short_term(bag.dtime, dtime)
            if short_term:
                st_proc += thisproc
                st_cost += bcost

            # fee-corrected proceeds for this partial sale:
            corrproc = thisproc * (1 - fee_ratio)
            # profit for this partial sale (not short term only):
            prof = corrproc - bcost

            log.info("Profits in this transaction:\n"
                 "    Original bag cost: %.3f %s (Price %.8f %s/%s)\n"
                 "    Proceeds         : %.3f %s (Price %.8f %s/%s)\n"
                 "    Proceeds w/o fees: %.3f %s\n"
                 "    Profit           : %.3f %s\n"
                 "    Taxable?         : %s (held for %s than a year)",
                 bcost, self.currency, bag.price, bag.cost_currency,
                 currency,
                 thisproc, self.currency, rate, self.currency, currency,
                 corrproc, self.currency,
                 prof, self.currency,
                 'yes' if short_term else 'no',
                 'less' if short_term else 'more')

            # Store report data:
            repinfo = {
                'kind': 'payment', 'buy_currency': '', 'buy_ratio': 0}
            if report_info is not None:
                repinfo.update(report_info)
            if not repinfo.get('buy_currency', ''):
                repinfo['buy_ratio'] = 0
            self.report.add_payment(
                reports.PaymentReport(
                    kind=repinfo['kind'],
                    exchange=exchange,
                    sell_date=pd.Timestamp(dtime).tz_convert('UTC'),
                    currency=currency,
                    to_pay=to_pay,
                    fee_ratio=fee_ratio,
                    bag_date=bag.dtime,
                    bag_amount=bag.amount + spent,
                    bag_spent=spent,
                    cost_currency=bag.cost_currency,
                    spent_cost=bcost,
                    short_term=short_term,
                    ex_rate=rate,
                    proceeds=corrproc,
                    profit=prof,
                    buy_currency=repinfo['buy_currency'],
                    buy_ratio=repinfo['buy_ratio']))

            to_pay = remainder
            if to_pay > 0:
                log.info("Still to be paid with another bag: %.8f %s",
                     to_pay, currency)
            if bag.is_empty():
                del self.bags[exchange][bag_index]

        # update and clean up totals:
        if total - amount == 0:
            del self.totals[exchange][currency]
            if not self.totals[exchange]:
                del self.totals[exchange]
            if not self.bags[exchange]:
                del self.bags[exchange]
        else:
            self.totals[exchange][currency] = total - amount

        # Return the tuple (short_term_profit, total_proceeds):
        # Note: if it is not completely clear how we arrive at these
        # formulas (i.e. the proceeds are the value of the spent amount,
        # minus fees, at time of payment; the profit equals these
        # proceeds minus the initial cost of the full amount), here
        # is a different view point:
        # The cost and proceeds attributable to fees are split
        # proportionately from st_cost and st_proceeds, i.e.
        # the fee's cost is `fee_p * st_cost` and the lost proceeds
        # due to the fee is `fee_p * st_proceeds`.
        # The fee's cost is counted as loss:
        # (but only the taxable short term portion!)
        # ==>
        # Total profit =
        #  profit putting fees aside: (1-fee_p) * (st_proceeds - st_cost)
        #  - fee cost loss          : - fee_p * st_cost
        #  = (1 - fee_p) * st_proceeds - st_cost
        return st_proc * (1 - fee_ratio) - st_cost, proc * (1 - fee_ratio)


