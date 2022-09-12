import pytest

from bitshares_tradehistory_analyzer.history_downloader import HistoryDownloader

BITSHARES_API_NODE_URL = "wss://eu.nodes.bitshares.ws"
ES_WRAPPER_URL = "https://api.bitshares.ws/openexplorer/es/"


def test_get_continuation_point():
    ...


def test_fetch_transfers_from_scratch():
    ...


def test_fetch_transfers_from_previous_point():
    ...


def test_fetch_trades_from_scratch():
    ...


def test_fetch_trades_from_previous_point():
    ...


def test_fetch_trades_from_scratch_no_aggregated():
    ...


@pytest.mark.vcr()
def test_fetch_settlements_in_gs_state_from_scratch():
    hd = HistoryDownloader(
        account="abit", wrapper_url=ES_WRAPPER_URL, api_node=BITSHARES_API_NODE_URL, output_directory="test_fetch"
    )
    hd.fetch_settlements_in_gs_state()


def test_fetch_settlements_in_gs_state_from_previous_point():
    ...
