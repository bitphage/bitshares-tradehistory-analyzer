import pytest
from bitshares import BitShares


@pytest.fixture(scope='session')
def bitshares():
    """Initialize BitShares instance"""
    # TODO: we need working node because the library can do some queries on it's own
    bitshares = BitShares(node="wss://eu.nodes.bitshares.ws")

    return bitshares
