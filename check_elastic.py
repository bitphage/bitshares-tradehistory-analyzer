#!/usr/bin/env python

import argparse
import logging

from ruamel.yaml import YAML

from bitshares_tradehistory_analyzer.wrapper import Wrapper

log = logging.getLogger('bitshares_tradehistory_analyzer')


def main():
    parser = argparse.ArgumentParser(
        description='Analyze bitshares trading history using FIFO/LIFO/LPFO accounting methods',
        epilog='Report bugs to: https://github.com/bitfag/bitshares-tradehistory-analyzer/issues',
    )
    parser.add_argument('-d', '--debug', action='store_true', help='enable debug output'),
    parser.add_argument('-c', '--config', default='./config.yml', help='specify custom path for config file')
    args = parser.parse_args()

    # create logger
    if args.debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    log.addHandler(handler)

    # parse config
    yaml = YAML(typ="safe")
    with open(args.config, 'r') as ymlfile:
        conf = yaml.load(ymlfile)

    for url in conf.get('wrappers', []):
        alive = Wrapper.is_alive(url)
        print('Wrapper {} is {}'.format(url, 'alive' if alive else 'not alive'))


if __name__ == '__main__':
    main()
