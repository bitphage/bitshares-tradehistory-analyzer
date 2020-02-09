import requests
import urllib.parse

from json.decoder import JSONDecodeError


class Wrapper:
    """ Wrapper for querying bitshares elasticsearch wrapper
    """

    def __init__(self, url, account_id):
        self.url = url
        self.account_id = account_id
        self.size = 200
        self.version = 1

        self.detect_version()

    @staticmethod
    def _request(url, payload):
        r = requests.get(url, params=payload)
        # Throw an exception if response was not 200
        r.raise_for_status()
        try:
            result = r.json()
        except JSONDecodeError:
            print(str(r))
            raise
        return result

    def detect_version(self):
        params = {'size': 1, 'account_id': '1.2.22'}
        try:
            self._query(params)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                self.version = 2

    def _query(self, params, *args, **kwargs):
        if self.version == 1:
            url = urllib.parse.urljoin(self.url, 'get_account_history')
        elif self.version == 2:
            url = urllib.parse.urljoin(self.url, 'account_history')

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

    def get_transfers(self, *args, **kwargs):
        params = {}
        params['operation_type'] = 0
        return self._query(params, *args, **kwargs)

    def get_trades(self, *args, **kwargs):
        params = {}
        params['operation_type'] = 4
        return self._query(params, *args, **kwargs)

    @staticmethod
    def is_alive(url):
        """ Check built-it ES wrapper metric to check whether it's alive
        """
        url = urllib.parse.urljoin(url, 'is_alive')
        try:
            r = requests.get(url, timeout=5)
        except requests.exceptions.ConnectionError:
            return False

        if r.status_code == requests.codes.ok:
            try:
                return r.json().get('status') == 'ok'
            except JSONDecodeError:
                print(str(r))
                return False

        return False
