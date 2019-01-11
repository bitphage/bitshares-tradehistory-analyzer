Bitshares trading history analyzer
==================================

This is a set of scripts for analyzing trading history on the [Bitshares DEX](https://bitshares.org) and thus for all
exchanges running on top ([RuDEX](https://rudex.org/), [Cryptobridge](https://crypto-bridge.org/),
[Openledger](https://openledger.info/), [SparkDex](https://dex.bitspark.io/) etc).

Supported inventory accounting methods:

- FIFO (first-in/first-out)
- LIFO (last-in/first-out)
- LPFO (lowest-price/first-out)

Installation using pipenv
-------------------------

1. Install [pipenv](https://docs.pipenv.org/).
2. Run the following code

```
pipenv install
```

Running
-------

1. Prepare working environment using virtualenv (see above)
2. Copy `common.yml.example` to `common.yml` and change variables according to your needs
3. Run the scripts:

```
pipenv shell
./script.py
exit
```

Download history
----------------

Use `./download_history.py account_name` to get transfers and trading history. Export format is generic
[ccGains](https://github.com/probstj/ccGains/) format.

Features:

- History obtained from public elasticsearch wrapper node
- Trading history aggregated by price, e.g. if you had single order for example of buying 1000 BTS at 0.10 USD/BTS and
  it was filled in small chunks of BTS, this feature will aggregate all these trades into single trade. Use
  `'--no-aggregate'` to disable
- The script can continue previously exported data from the previous point, e.g. download fresh history and append it to
  the existing files
- Fixed-point math is used to maintain strict precision in records
