import unittest

from log import get_logger
from models.torrent import Torrent
from torrent.client import Client
from torrent.tracker import TrackerClient

log = get_logger(__name__)


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_peer_connect(self):
        torrent = Torrent('data/bbb.torrent')
        response = await TrackerClient(torrent).announce()
        client = Client(response.peers, torrent)
        await client.connect()
        await client.download()


if __name__ == '__main__':
    unittest.main()
