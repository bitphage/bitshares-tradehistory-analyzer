Bitshares trading history analyzer
==================================

This is a set of scripts for analyzing trading history on the [Bitshares DEX](https://bitshares.org) and thus for all
exchanges running on the same software, e.g. ([RuDEX](https://rudex.org/).

Supported inventory accounting methods:

- FIFO (first-in/first-out)
- LIFO (last-in/first-out)
- LPFO (lowest-price/first-out)

**Note:** this is a beta software. Feel free to report bugs.

Limitations
-----------

* Blockchain fees are currently not taken into account (market fees are correctly counted). Blockchain fees are fees
  charged by the blockchain itself, like transfer fee, fee for creating limit order etc.
* Analyzer is not intended to generate tax reports, it's main purpose is to evaluate strategy performance. Origianlly
  ccgains library requires historic data to estimate profits for trades not involving BASE currency. For example, your
  base currency is USD, you bought BTC and than trading BTS/BTC pair. Such trades will not show any profits. Imagine
  finally you got more amount of BTC than initially and then you sold BTC for USD. This is where finally you will see
  the profits.
* Another ccgains assumption is that if you deposited some quote currency and sold it for base currency, all obtained
  amount will be considered as a profit. Because we primarily interesting in evaluating strategy performance, we
  considering profit as a result of buy+sell only. So such deposited and then sold currency will be counted for 0
  profit.

Installation using poetry
-------------------------

1. Make sure you have installed required packages: `apt-get install gcc make libssl-dev`
2. Install [poetry](https://python-poetry.org/)
3. Run `poetry install` to install the dependencies
4. Copy `common.yml.example` to `common.yml` and change variables according to your needs
5. Now you're ready to run scripts:

```
poetry shell
./script.py
exit
```

Usage
=====

Step one: export transfers and trading history
----------------------------------------------

Use `./download_history.py account_name` to get transfers and trading history. Export format is generic
[ccGains](https://github.com/probstj/ccGains/) format. After running this script you'll get csv files with exported
history.

Features:

- History obtained from public elasticsearch wrapper node
- Trading history aggregated by price, e.g. if you had single order for example of buying 1000 BTS at 0.10 USD/BTS and
  it was filled in small chunks of BTS, this feature will aggregate all these trades into single trade. Use
  `'--no-aggregate'` to disable
- The script can continue previously exported data from the previous point, e.g. download fresh history and append it to
  the existing files
- Fixed-point math is used to maintain strict precision in records

Step two: analyze history
-------------------------

Use `./analyzer.py base_currency account_name` to analyze history. After running you'll get reports in pdf format and
status-xxx.json file. Status file will be used as cache later when you'll need to analyze fresh data.

Features:

- `--mode` flag let you specify accounting mode you wish to use (FIFO/LIFO/LPFO)
- `--precision` flag is for defining base currency precision in reports. By default, precision is set to handle fiat
  currencies, so precision is 2 (numbers in 0.00 format). If you need to analyze BTC:XXX markets, use `--precision 8`
- `--year` option let you limit reporting year. This is obvious, no need to generate full report each time while you
  already have a reports for previous years.


Cumulative analysis
-------------------

The package is also provides a helper script to get a high-level overview of all transfers and trades across single or multiple accounts.
It shows in easy to use format all deposits and withrawals, and all trades accumulated into a single entry. For example,
you've bought 1 BTC in 100 transactions with different prices across one year. This script will consolidate all of them
into a single entry. Also, it allows to limit a time range for analisys by `--start` and `--end` options.

Example output:

```
% ./bitshares_tradehistory_analyzer/cumulative_analyzer_cli.py transfers-id-b0t1.csv trades-id-b0t1.csv
Asset transfer stats:
               Asset    Deposited    Withdrawn         Delta   Last Transfer Timestamp
0                CNY    3005.6267     317.8022     2687.8245 2020-02-01 10:26:45+00:00
1    OPTIONS.J19CALL         0.01            0          0.01 2019-07-01 20:44:12+00:00
2                BTS   2842.38061  16992.77614  -14150.39553 2020-09-11 04:41:18+00:00
3   OPTIONS.19NO025C         0.01            0          0.01 2019-10-25 02:51:12+00:00
4            DIGITAL          1.0            0           1.0 2019-10-26 11:42:24+00:00
5      ECURREX.YMRUB       1580.1     10708.83      -9128.73 2020-07-10 06:43:12+00:00
6              RUBLE  12800.00002       6100.7    6699.30002 2020-03-03 04:54:21+00:00
7          RUDEX.BTC   0.00378297            0    0.00378297 2020-04-01 12:25:51+00:00
8   OPTIONS.21JA1USD         0.01            0          0.01 2020-04-05 18:26:18+00:00
9             MVCOIN        0.001            0         0.001 2020-05-14 02:01:21+00:00
10  OPTIONS.20SE1BTC         0.01            0          0.01 2020-05-19 18:41:27+00:00
Trading stats:
      Spent Asset  Spent Amount Acquired Asset Acquired Amount      Last Trade Timestamp
0             CNY    53067.1083            BTS    136677.78457 2020-02-01 10:17:09+00:00
1             BTS  129199.10876            CNY      50379.7836 2020-02-01 10:25:09+00:00
2   ECURREX.YMRUB      14749.91          RUBLE     14749.32009 2020-09-08 22:00:54+00:00
3           RUBLE    5223.69820            BTS      3641.97014 2020-09-11 03:56:57+00:00
4           RUBLE   16224.92190  ECURREX.YMRUB        16388.81 2020-03-10 12:55:18+00:00
5             BTS     599.99984      RUDEX.BTC      0.00157049 2020-04-05 16:54:30+00:00
6       RUDEX.BTC    0.00535346            BTS      2136.58400 2020-04-11 15:21:39+00:00
7   ECURREX.YMRUB       2904.08            BTS      2100.93268 2020-06-17 14:24:24+00:00
8             BTS    1172.68463     RUDEX.USDT       20.665472 2020-04-18 13:26:30+00:00
9      RUDEX.USDT     20.665472            BTS      1222.80901 2020-04-20 07:00:42+00:00
10            BTS     611.65091  ECURREX.YMRUB         1945.05 2020-09-05 06:02:57+00:00
```


Support
=======

If you have any issues, please open a github issue (and maybe search for similar open/closed issues).
