from unittest.mock import MagicMock

import pytest
import requests

from bitshares_tradehistory_analyzer.wrapper import Wrapper


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
