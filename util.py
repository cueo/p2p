import random

from const import CLIENT_ID, VERSION
from log import get_logger

log = get_logger(__name__)


def bytes_to_str(b: bytes) -> str:
    return b.decode('utf-8')


def generate_id() -> str:
    """
    Generates an Azureus-style peer_id.
    Concatenates client id, version and a 12 digit random number.

    Returns: new peer_id
    """
    n = 12
    random_num = random.randint(10 ** (n-1), (10 ** n) - 1)
    _id = f'-{CLIENT_ID}{VERSION}-{random_num}'
    log.info(f'Generated {_id=}')
    return _id
