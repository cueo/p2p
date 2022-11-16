import struct
from collections import OrderedDict
import socket
from typing import List


class Peer:
    def __init__(self, ip: str, port: int, peer_id: bytes = None):
        self.ip = ip
        self.port = port
        self.peer_id = peer_id

    def __repr__(self):
        return f'Peer(ip={self.ip}, port={self.port} peer_id={self.peer_id})'


def from_dict(peer_info: List[OrderedDict]) -> List[Peer]:
    peers = []
    for peer in peer_info:
        ip = peer[b'ip'].decode()
        port = peer[b'port']
        peers.append(Peer(ip=ip, port=port, peer_id=peer.get(b'peer id')))
    return peers


def from_bytes(peer_info: bytes) -> List[Peer]:
    peers = []

    # Split the string in pieces of length 6 bytes, where the first
    # 4 characters is the IP the last 2 is the TCP port.
    _peers = [peer_info[i:i + 6] for i in range(0, len(peer_info), 6)]
    for i, peer in enumerate(_peers):
        ip, port = struct.unpack('!4sH', peer)
        ip = socket.inet_ntoa(ip)
        peers.append(Peer(ip=ip, port=port, peer_id=i.to_bytes(2, byteorder='big')))
    return peers
