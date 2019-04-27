import requests


class Wrapper:
    """ Wrapper for querying bitshares elasticsearch wrapper
    """

    def __init__(self, url, account_id):
        self.url = url
        self.account_id = account_id
        self.size = 200

    def _query(self, params, *args, **kwargs):
        url = self.url + 'get_account_history'
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

        r = requests.get(url, params=payload)
        r.raise_for_status()
        return r.json()

    def get_transfers(self, *args, **kwargs):
        params = {}
        params['operation_type'] = 0
        return self._query(params, *args, **kwargs)

    def get_trades(self, *args, **kwargs):
        params = {}
        params['operation_type'] = 4
        return self._query(params, *args, **kwargs)

    def is_alive(self):
        """ Check built-it ES wrapper metric to check whether it's alive
        """
        url = self.url + 'is_alive'
        r = requests.get(url)

        if r.status_code == requests.codes.ok:
            return r.json().get('status') == 'ok'

        return False
