import copy
import logging
import os.path
import time
from decimal import Decimal
from pathlib import Path
from typing import Optional, Tuple, Union

from bitshares import BitShares

from bitshares_tradehistory_analyzer.consts import HEADER, LINE_DICT_TEMPLATE, LINE_TEMPLATE
from bitshares_tradehistory_analyzer.parser import Parser, UnsupportedSettleEntry
from bitshares_tradehistory_analyzer.wrapper import Wrapper

log = logging.getLogger(__name__)


SELL_LOG_TEMPLATE = (
    'Sold {sell_amount} {sell_cur} for {buy_amount} {buy_cur} @ {price:.{prec}} {buy_cur}/{sell_cur}'
    ' ({price_inverted:.{prec}f} {sell_cur}/{buy_cur})'
)


def get_continuation_point(filename: Union[str, Path]) -> Tuple[str, Optional[str]]:
    """Check csv-file for number of records and last op id

    :param filename: path to the file to check
    :return: datetime string of last record and last op id
    """
    dtime = '2010-10-10'
    last_op_id = None

    if os.path.isfile(filename) and os.path.getsize(filename) > 0:
        with open(filename, 'rb') as fd:
            # Move reading position 2 bytes before EOF
            fd.seek(-2, os.SEEK_END)
            # Jump backward until EOL found
            while fd.read(1) != b"\n":
                try:
                    fd.seek(-2, os.SEEK_CUR)
                except OSError:
                    # Probably file is just one-line
                    return dtime, last_op_id

            # Take last line into list object
            last_line = fd.readline().decode('utf-8').rstrip('\n').split(',')

        dtime = last_line[1]
        last_op_id = last_line[-1].split()[-1]
        log.info('Continuing {} from {}, op id: {}'.format(filename, dtime, last_op_id))

    return dtime, last_op_id


class HistoryDownloader:
    def __init__(
        self,
        account: str,
        wrapper_url: str,
        api_node: str,
        no_aggregate: bool = False,
        output_directory: Optional[str] = None,
    ):
        self.account = account

        out_dir = Path(output_directory) if output_directory is not None else Path(".")
        out_dir.mkdir(parents=True, exist_ok=True)
        self.transfers_file = out_dir / Path(f'transfers-{self.account}.csv')
        self.trades_file = out_dir / f"trades-{self.account}.csv"
        self.global_settlements_file = out_dir / f"gs-{self.account}.csv"

        bitshares = BitShares(node=api_node)
        self.parser = Parser(bitshares, self.account)
        self.wrapper = Wrapper(wrapper_url, account_id=self.parser.account["id"])

        self.no_aggregate = no_aggregate

    def fetch_transfers(self):
        dtime, last_op_id = get_continuation_point(self.transfers_file)
        if not (dtime and last_op_id):
            with open(self.transfers_file, 'w') as fd:
                fd.write(HEADER)

        with open(self.transfers_file, "a") as fd:
            history = self.wrapper.get_transfers(from_date=dtime)
            while history:
                for entry in history:
                    op_id = entry['account_history']['operation_id']
                    op_date = entry['block_data']['block_time']
                    # Skip entries until last_op_id found
                    if last_op_id and op_id != last_op_id:
                        log.debug('skipping entry {}'.format(entry))
                        continue
                    elif last_op_id and op_id == last_op_id:
                        # Ok, last_op_id found, let's start to write entries from the next one
                        last_op_id = None
                        log.debug('skipping entry {}'.format(entry))
                        continue

                    parsed_data = self.parser.parse_transfer_entry(entry)
                    fd.write(LINE_TEMPLATE.format(**parsed_data))

                # Remember last op id for the next chunk
                last_op_id = op_id

                # Break `while` loop on least history chunk
                if len(history) < self.wrapper.size:
                    break

                # Get next data chunk
                history = self.wrapper.get_transfers(from_date=op_date)

    def fetch_trades(self):
        dtime, last_op_id = get_continuation_point(self.trades_file)
        if not (dtime and last_op_id):
            with open(self.trades_file, 'w') as fd:
                fd.write(HEADER)

        with open(self.trades_file, "a") as fd:
            history = self.wrapper.get_trades(from_date=dtime)
            aggregated_line = copy.deepcopy(LINE_DICT_TEMPLATE)
            while history:
                for entry in history:
                    op = self.parser.load_op(entry)
                    op_id = entry['account_history']['operation_id']
                    op_date = entry['block_data']['block_time']

                    log.debug('Processing op {} @ {}'.format(op_date, op_id))
                    # Skip entries until last_op_id found
                    if last_op_id and op_id != last_op_id:
                        log.debug('skipping earlier op {} < {}'.format(op_id, last_op_id))
                        continue
                    elif last_op_id and op_id == last_op_id:
                        last_op_id = None
                        continue

                    line_dict = self.parser.parse_trade_entry(entry)

                    if self.no_aggregate:
                        log.info(SELL_LOG_TEMPLATE.format(**line_dict))
                        fd.write(LINE_TEMPLATE.format(**line_dict))
                        continue

                    if not aggregated_line['order_id']:
                        # Aggregated line is empty, store current entry data
                        aggregated_line = line_dict
                    elif aggregated_line['order_id'] == op['order_id']:
                        # If selling same asset at the same rate, just aggregate the trades
                        aggregated_line['date'] = line_dict['date']
                        aggregated_line['sell_amount'] += line_dict['sell_amount']
                        aggregated_line['buy_amount'] += line_dict['buy_amount']
                        aggregated_line['fee_amount'] += line_dict['fee_amount']
                        aggregated_line['comment'] += ' {}'.format(op_id)
                        # Prevent division by zero
                        price = Decimal('0')
                        price_inverted = Decimal('0')
                        if aggregated_line['sell_amount'] and aggregated_line['buy_amount']:
                            price = aggregated_line['buy_amount'] / aggregated_line['sell_amount']
                            price_inverted = aggregated_line['sell_amount'] / aggregated_line['buy_amount']
                        aggregated_line['price'] = price
                        aggregated_line['price_inverted'] = price_inverted
                    else:
                        log.info(SELL_LOG_TEMPLATE.format(**line_dict))
                        # Write current aggregated line
                        fd.write(LINE_TEMPLATE.format(**aggregated_line))
                        aggregated_line = copy.deepcopy(LINE_DICT_TEMPLATE)
                        # Save current entry into new aggregation object
                        aggregated_line = line_dict

                # Remember last op id for the next chunk
                last_op_id = op_id

                # Break `while` loop on least history chunk
                if len(history) < self.wrapper.size:
                    break

                # Get next data chunk
                time.sleep(1)
                history = self.wrapper.get_trades(from_date=op_date)

            # At the end, write remaining line
            if aggregated_line['order_id']:
                log.info(SELL_LOG_TEMPLATE.format(**aggregated_line))
                fd.write(LINE_TEMPLATE.format(**aggregated_line))

    def fetch_settlements_in_gs_state(self):
        dtime, last_op_id = get_continuation_point(self.global_settlements_file)
        if not (dtime and last_op_id):
            with open(self.global_settlements_file, 'w') as fd:
                fd.write(HEADER)

        with open(self.global_settlements_file, "a") as fd:
            history = self.wrapper.get_global_settlements(from_date=dtime)
            while history:
                for entry in history:
                    op_id = entry['account_history']['operation_id']
                    op_date = entry['block_data']['block_time']
                    # Skip entries until last_op_id found
                    if last_op_id and op_id != last_op_id:
                        log.debug('skipping entry {}'.format(entry))
                        continue
                    elif last_op_id and op_id == last_op_id:
                        # Ok, last_op_id found, let's start to write entries from the next one
                        last_op_id = None
                        log.debug('skipping entry {}'.format(entry))
                        continue

                    try:
                        parsed_data = self.parser.parse_settle_entry(entry)
                    except UnsupportedSettleEntry:
                        continue
                    fd.write(LINE_TEMPLATE.format(**parsed_data))

                # Remember last op id for the next chunk
                last_op_id = op_id

                # Break `while` loop on least history chunk
                if len(history) < self.wrapper.size:
                    break

                # Get next data chunk
                history = self.wrapper.get_global_settlements(from_date=op_date)
