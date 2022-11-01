import unittest

from torrent.torrent import Torrent


class TorrentTests(unittest.TestCase):
    def test_decode(self):
        torrent = Torrent('data/ubuntu.torrent')
        print(torrent)


if __name__ == '__main__':
    unittest.main()
