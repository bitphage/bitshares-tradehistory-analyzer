import urllib.parse
from json.decoder import JSONDecodeError

import requests


class Wrapper:
    """Wrapper for querying bitshares elasticsearch wrapper"""

    def __init__(self, url, account_id):
        self.url = url
        self.account_id = account_id
        self.size = 200
        self.version = 1

        self.detect_version()

    @staticmethod
    def _request(url, payload):
        response = requests.get(url, params=payload)
        # Throw an exception if response was not 200
        response.raise_for_status()
        try:
            result = response.json()
        except JSONDecodeError:
            print(str(response))
            raise
        return result

    @staticmethod
    def is_alive(url, endpoint="is_alive"):
        """Check built-it ES wrapper metric to check whether it's alive"""
        # Note: not usable for new BitShares Insight API
        url = urllib.parse.urljoin(url, endpoint)
        try:
            response = requests.get(url, timeout=5)
        except requests.exceptions.ConnectionError:
            return False

        if response.status_code == requests.codes.ok:
            try:
                return response.json().get('status') == 'ok'
            except JSONDecodeError:
                print(str(response))
                return False

        return False

    @staticmethod
    def is_alive_v2(url):
        return Wrapper.is_alive(url, endpoint="status")

    def detect_version(self):
        params = {'size': 1, 'account_id': '1.2.22'}
        try:
            self._query(params)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                self.version = 2

    def get_transfers(self, *args, **kwargs):
        params = {'operation_type': 0}
        return self._query(params, *args, **kwargs)

    def get_trades(self, *args, **kwargs):
        params = {'operation_type': 4}
        return self._query(params, *args, **kwargs)

    def get_global_settlements(self, *args, **kwargs):
        """Get settlements performed when asset is in GS.

        Regular settlements are counted as trades, but when asset is globally settled, there is a separate operation.
        """
        params = {'operation_type': 17}
        return self._query(params, *args, **kwargs)

    def _query(self, params, *args, **kwargs):
        if self.version == 1:
            url = urllib.parse.urljoin(self.url, 'get_account_history')
        elif self.version == 2:
            url = urllib.parse.urljoin(self.url, 'account_history')
        else:
            raise ValueError("Unsupported ES wrapper version set")

        payload = {
            'account_id': self.account_id,
            'size': self.size,
            'operation_type': 0,
            'sort_by': 'account_history.sequence',
            'type': 'data',
            'agg_field': 'operation_type',
        }
        payload.update(params)

        if kwargs:
            payload.update(kwargs)

        return self._request(url, payload)
