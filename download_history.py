#!/usr/bin/env python

import argparse
import logging
import random

from ruamel.yaml import YAML

from bitshares_tradehistory_analyzer.history_downloader import HistoryDownloader

log = logging.getLogger(__name__)


def main():

    parser = argparse.ArgumentParser(
        description='Export bitshares transfer and trading history for an account',
        epilog='Report bugs to: https://github.com/bitfag/bitshares-tradehistory-analyzer/issues',
    )
    parser.add_argument('-d', '--debug', action='store_true', help='enable debug output'),
    parser.add_argument('-c', '--config', default='./config.yml', help='specify custom path for config file')
    parser.add_argument('-u', '--url', help='override URL of elasticsearch wrapper plugin')
    parser.add_argument('--no-aggregate', action='store_true', help='do not aggregate trades by same order')
    parser.add_argument('account')
    args = parser.parse_args()

    # create logger
    library_logger = logging.getLogger("bitshares_tradehistory_analyzer")
    if args.debug:
        log.setLevel(logging.DEBUG)
        library_logger.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)
        library_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    library_logger.addHandler(handler)

    # parse config
    yaml = YAML(typ="safe")
    with open(args.config, 'r') as ymlfile:
        conf = yaml.load(ymlfile)

    if args.url:
        wrapper_url = args.url
    else:
        wrapper_url = random.choice(conf['wrappers'])  # noqa: DUO102
    log.info('Using wrapper {}'.format(wrapper_url))

    downloader = HistoryDownloader(
        account=args.account, wrapper_url=wrapper_url, api_node=conf["nodes"], no_aggregate=args.no_aggregate
    )
    downloader.fetch_transfers()
    downloader.fetch_trades()
    downloader.fetch_settlements_in_gs_state()


if __name__ == '__main__':
    main()
