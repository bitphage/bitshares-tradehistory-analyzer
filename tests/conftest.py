import pytest

from bitshares import BitShares


@pytest.fixture(scope='session')
def bitshares():
    """ Initialize BitShares instance
    """
    bitshares = BitShares()

    return bitshares
