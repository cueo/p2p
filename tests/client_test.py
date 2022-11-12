import asyncio
import unittest

from torrent import tracker
from models.torrent import Torrent
from torrent.client import Client


async def test_peer_connect():
    torrent = Torrent('data/ubuntu.torrent')
    response = tracker.announce(torrent)
    client = Client(response.peers, info_hash=torrent.info_hash, peer_id=torrent.peer_id)
    await client.connect()


if __name__ == '__main__':
    asyncio.run(test_peer_connect())
