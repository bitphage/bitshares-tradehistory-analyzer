#!/usr/bin/env python

import logging
import time
import sys
import os.path
import argparse
import ccgains

from lib.helper import TradeHistory, BagQueue

logger = logging.getLogger('ccgains')
logger.setLevel(logging.DEBUG)
# This is my highest logger, don't propagate to root logger:
logger.propagate = 0
# Reset logger in case any handlers were already added:
for h in logger.handlers[::-1]:
    h.close()
    logger.removeHandler(h)
# Create file handler which logs even debug messages
fname = 'ccgains_%s.log' % time.strftime("%Y%m%d-%H%M%S")
fh = logging.FileHandler(fname, mode='w')
fh.setLevel(logging.DEBUG)
# Create console handler for debugging:
ch = logging.StreamHandler(stream=sys.stdout)
ch.setLevel(logging.DEBUG)
# Create formatters and add them to the handlers
fhformatter = logging.Formatter(
    '%(asctime)s %(levelname)-8s - %(module)13s -> %(funcName)-13s: '
    '%(message)s')
chformatter = logging.Formatter('%(levelname)-8s: %(message)s')
#fh.setFormatter(fhformatter)
fh.setFormatter(chformatter)
ch.setFormatter(chformatter)
# Add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)

def log_bags(bags):
    logger.info("State of bags: \n%s\n",
                '    ' + '\n    '.join(str(bags).split('\n')))


def main():
    parser = argparse.ArgumentParser(
            description='Analyze bitshares trading history using FIFO/LIFO/LPFO accounting methods',
            epilog='Report bugs to: https://github.com/bitfag/bitshares-tradehistory-analyzer/issues')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='enable debug output'),
    parser.add_argument('-c', '--config', default='./config.yml',
                        help='specify custom path for config file')
    parser.add_argument('-m', '--mode', default='LPFO',
                        help='inventory accounting mode')
    parser.add_argument('-p', '--precision', type=int,
                        help='custom precision for BASE currency columns')
    parser.add_argument('-y', '--year', default=None, type=int,
                        help='Generate report for specified year only')
    parser.add_argument('base_currency',
                        help='BASE currency like USD/CNY/RUDEX.BTC')
    parser.add_argument('account',
                        help='bitshares account name')
    args = parser.parse_args()

    bf = BagQueue(args.base_currency, None, mode=args.mode)
    th = TradeHistory()
    th.append_csv('transfers-{}.csv'.format(args.account))
    th.append_csv('trades-{}.csv'.format(args.account))

    status_filename = 'status-{}-{}-{}.json'.format(args.account, args.mode, args.base_currency)
    if os.path.isfile(status_filename):
        bf.load(status_filename)

    last_trade = 0
    while (last_trade < len(th.tlist)
           and th[last_trade].dtime <= bf._last_date):
        last_trade += 1
    if last_trade > 0:
        logger.info("continuing with trade #%i" % (last_trade + 1))

    # Now, the calculation. This goes through your imported list of trades:
    for i, trade in enumerate(th.tlist[last_trade:]):
        # Most of this is just the log output to the console and to the
        # file 'ccgains_<date-time>.log'
        # (check out this file for all gory calculation details!):
        logger.info('TRADE #%i', i + last_trade + 1)
        logger.info(trade)

        # Don't try to process base currency transfers to avoid error from ccgains
        if trade.kind == 'Deposit' and trade.buycur == args.base_currency:
            continue
        elif trade.kind == 'Withdrawal' and trade.sellcur == args.base_currency:
            continue
        elif trade.kind == 'Withdrawal':
            # TODO: don't process withdrawals for now
            continue

        # This is the important part:
        bf.process_trade(trade)
        # more logging:
        log_bags(bf)
        logger.info("Totals: %s", str(bf.totals))
        logger.info("Gains (in %s): %s\n" % (bf.currency, str(bf.profit)))

    bf.save(status_filename)

    my_column_names=[
        'Type', 'Amount spent', u'Currency', 'Purchase date',
        'Sell date', u'Exchange', u'Short term', 'Purchase cost',
        'Proceeds', 'Profit']

    formatters = {}
    if args.precision:
        btc_formatter = lambda x: '{:.{prec}f}'.format(x, prec=args.precision)
        formatters = {'Purchase cost': btc_formatter, 'Proceeds': btc_formatter, 'Profit': btc_formatter}

    bf.report.export_report_to_pdf(
        'Report-{}-{}-{}.pdf'.format(args.account, args.mode, args.year),
        date_precision='D', combine=True,
        custom_column_names=my_column_names,
        custom_formatters=formatters,
        year=args.year,
        locale="en_US"
    )

    bf.report.export_extended_report_to_pdf(
        'Details-{}-{}-{}.pdf'.format(args.account, args.mode, args.year),
        date_precision='S', combine=False,
        font_size=10,
        year=args.year,
        locale="en_US")

# run the main() function above:
if __name__ == "__main__":
    main()

