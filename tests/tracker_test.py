import unittest

from torrent import tracker
from models.torrent import Torrent


class TrackerTests(unittest.TestCase):
    def test_announce(self):
        torrent = Torrent('data/ubuntu.torrent')
        response = tracker.announce(torrent)
        assert response is not None
        assert response.peers is not None


if __name__ == '__main__':
    unittest.main()
