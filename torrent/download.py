from typing import Dict

from models.torrent import Torrent
from torrent.client import PeerClient


class Downloader:
    def __init__(self, torrent: Torrent, peer_clients: Dict[bytes, PeerClient]):
        self.torrent = torrent
        self.peer_clients = peer_clients

    