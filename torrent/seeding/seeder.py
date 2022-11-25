import random
from typing import Dict

from models.torrent import Torrent
from torrent.client import PeerClient
from torrent.seeding.server import PeerServer
from util import generate_id
import asyncio
import os
from contextlib import closing

class Seeder:
    def __init__(self, torrent_folder_loc: str, peer_clients: Dict[bytes, PeerClient]):
        self.torrent_folder_loc = torrent_folder_loc

        # All torrent objects available in the 'self.torrent_folder_loc' folder map info_hash -> torrent
        self.torrents = {}
        self.peer_clients = peer_clients
        self._peer_id = generate_id()
        self._server = None
        # TODO: do we need to pass the event loop to the seeder? or this would work?
        self._loop = asyncio.get_event_loop()

    # def run(self):
    #     await self.start()

    async def start(self):
        self._load_torrent_files()
        self._server = PeerServer(self._peer_id, self.torrents)
        await self._server.start()
        # await self._server.start()

    def _load_torrent_files(self):
        dir_list = os.listdir(self.torrent_folder_loc)
        for torrent_file_name in dir_list:
            torrent = Torrent('../../data/' + torrent_file_name)
            self.torrents[torrent.info_hash] = torrent


if __name__ == '__main__':
    seeder = Seeder('/Users/vigneshsomasundaram/Documents/Fall 2022/Networks/Project/p2p/data', None)
    # seeder.start()
    with closing(asyncio.get_event_loop()) as loop:
        loop.run_until_complete(seeder.start())
        loop.run_forever()

