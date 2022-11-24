import random
from typing import Dict

from models.torrent import Torrent
from torrent.client import PeerClient
from torrent.seeding.server import PeerServer
import asyncio


class Seeder:
    def __init__(self, torrent: Torrent, peer_clients: Dict[bytes, PeerClient]):
        self.torrent = torrent
        self.peer_clients = peer_clients
        self._self_peer_id = random.Random.randint(0, 1000)
        self._server = PeerServer(self._our_peer_id, None)
        # TODO: do we need to pass the event loop to the seeder? or this would work?
        self._loop = asyncio.get_event_loop()

    async def start(self):
        await self._loop.run_until_complete(self,self._server.start())
        # await self._server.start()


