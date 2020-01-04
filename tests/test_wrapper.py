import requests

from bitshares_tradehistory_analyzer.wrapper import Wrapper


class MockResponseGood:

    # @staticmethod
    def raise_for_status(self):
        return None

    @staticmethod
    def json():
        return {'foo': 'bar'}


class MockResponseBad:
    def raise_for_status(self):
        self.status_code = 404
        raise requests.exceptions.HTTPError('error', response=self)


def test_init(monkeypatch):
    def good(*args, **kwargs):
        return MockResponseGood()

    def bad(*args, **kwargs):
        return MockResponseBad()

    monkeypatch.setattr(requests, 'get', good)
    w = Wrapper('https://example.com', '1.2.222')
    assert w.version == 1

    monkeypatch.setattr(requests, 'get', bad)
    w = Wrapper('https://example.com', '1.2.222')
    assert w.version == 2
