import unittest

from models.torrent import Torrent
from torrent.tracker import TrackerClient


class TrackerTests(unittest.IsolatedAsyncioTestCase):
    async def test_announce(self):
        torrent = Torrent('data/bbb.torrent')
        response = await TrackerClient(torrent).announce()
        assert response.peers is not None


if __name__ == '__main__':
    unittest.main()
