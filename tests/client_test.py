import unittest

import util
from log import get_logger
from models.peer import Peer
from models.torrent import Torrent
from torrent.client import Client
from torrent.tracker import TrackerClient

log = get_logger(__name__)


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_peer_connect(self):
        torrent = Torrent('../data/torrents/test.torrent')

        # response = await TrackerClient(torrent).announce()
        # peers = [Peer('10.0.0.98', 55251, b'001')]
        peers = [Peer('10.0.0.98', 6881, util.generate_id())]
        # client = Client(response.peers, torrent)
        client = Client(peers, torrent)
        await client.connect()
        await client.download()


if __name__ == '__main__':
    unittest.main()
