import os
from enum import Enum

CLIENT_ID = 'PP'
VERSION = '0001'

PIECE_SHA_LENGTH = 20
CHUNK_SIZE = 8192

PROTOCOL = b'BitTorrent protocol'
PROTOCOL_LEN = len(PROTOCOL)
PEER_CONNECT_TIMEOUT = 50

BLOCK_SIZE = 2 ** 14

DOWNLOAD_PATH = f'{os.getenv("HOME")}/Downloads/p2p'


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


class ActionType(Enum):
    connect = 0
    announce = 1
