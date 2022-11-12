from enum import Enum

CLIENT_ID = 'PP'
VERSION = '0001'

CHUNK_SIZE = 8192

PROTOCOL = b'BitTorrent protocol'
PROTOCOL_LEN = len(PROTOCOL)
PEER_CONNECT_TIMEOUT = 50


class PeerMessage(Enum):
    choke = 0
    unchoke = 1
    interested = 2
    not_interested = 3
    have = 4
    bitfield = 5
    request = 6
    piece = 7
    cancel = 8
    port = 9
