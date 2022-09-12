from unittest.mock import MagicMock

import pytest
import requests

from bitshares_tradehistory_analyzer.wrapper import Wrapper


@pytest.fixture()
def working_es_url():
    return "https://api.bitshares.ws/openexplorer/es/"


class MockResponseGood:
    @staticmethod
    def json():
        return {'foo': 'bar'}

    def raise_for_status(self):
        return None


class MockResponseBad:
    def raise_for_status(self):
        self.status_code = 404
        raise requests.exceptions.HTTPError('error', response=self)


def test_version_autodetect_1(monkeypatch):
    monkeypatch.setattr(requests, 'get', MagicMock(return_value=MockResponseGood()))
    wrapper = Wrapper('https://example.com', '1.2.222')
    assert wrapper.version == 1


def test_version_autodetect_2(monkeypatch):
    monkeypatch.setattr(requests, 'get', MagicMock(return_value=MockResponseBad()))
    wrapper = Wrapper('https://example.com', '1.2.222')
    assert wrapper.version == 2


@pytest.mark.vcr()
def test_is_alive_wrapper_ok():
    assert Wrapper.is_alive_v2("https://api.bitshares.ws/") is True


@pytest.mark.vcr()
def test_detect_version(working_es_url):
    wrapper = Wrapper(working_es_url, "1.2.222")
    wrapper.detect_version()
    assert wrapper.version == 2


@pytest.mark.vcr()
def test_get_transfers(working_es_url):
    wrapper = Wrapper(working_es_url, "1.2.1607166", size=5)
    transfers = wrapper.get_transfers()
    assert transfers is not None
    assert len(transfers) == 5


@pytest.mark.vcr()
def test_get_transfers_from_date(working_es_url):
    wrapper = Wrapper(working_es_url, "1.2.1607166", size=5)
    transfers = wrapper.get_transfers(from_date="2019-05-23T06:13:54")
    assert transfers is not None
    assert len(transfers) == 5


@pytest.mark.vcr()
def test_get_trades(working_es_url):
    wrapper = Wrapper(working_es_url, "1.2.1607166", size=5)
    trades = wrapper.get_trades()
    assert trades is not None
    assert len(trades) == 5


@pytest.mark.vcr()
def test_get_global_settlements(working_es_url):
    wrapper = Wrapper(working_es_url, "1.2.12376", size=5)  # abit
    settlements = wrapper.get_global_settlements()
    assert settlements is not None
    assert len(settlements) == 5
