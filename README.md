Bitshares trading history analyzer
==================================

This is a set of scripts for analyzing trading history on the [Bitshares DEX](https://bitshares.org) and thus for all
exchanges running on top ([RuDEX](https://rudex.org/), [Cryptobridge](https://crypto-bridge.org/),
[Openledger](https://openledger.info/), [SparkDex](https://dex.bitspark.io/) etc).

Supported inventory accounting methods:

- FIFO (first-in/first-out)
- LIFO (last-in/first-out)
- LPFO (lowest-price/first-out)

**Note:** this is a beta software. Feel free to report bugs.

Installation using pipenv
-------------------------

1. Make sure you have libssl-dev installed.
2. Install [pipenv](https://docs.pipenv.org/).
3. Run `pipenv install` to install the dependencies
4. Copy `common.yml.example` to `common.yml` and change variables according to your needs
5. Now you're ready to run scripts:

```
pipenv shell
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
