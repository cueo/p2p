import hashlib
from dataclasses import dataclass
from typing import List, Dict, Any

import bencodepy

from log import get_logger
from util import bytes_to_str, generate_id

log = get_logger(__name__)


@dataclass
class File:
    length: int
    path: str


@dataclass
class Torrent:
    peer_id: str
    announce: str
    piece_length: int
    dir: str
    filename: str
    info_hash: bytes
    uploaded: str
    downloaded: str
    left: str
    port: str
    compact: str
    pieces: List[str]
    files: List[File]

    def __init__(self, filepath: str):
        self.peer_id = generate_id()
        self.filepath = filepath
        self.decode()

    def decode(self):
        with open(self.filepath, 'rb') as f:
            torrent = bencodepy.decode(f.read())
        self.announce = bytes_to_str(torrent[b'announce'])
        info = torrent[b'info']
        self.info_hash = hashlib.sha1(bencodepy.bencode(info)).digest()
        self.decode_info(info)

    def decode_info(self, info: Dict[bytes, Any]):
        self.piece_length = info[b'piece length']
        pieces = info[b'pieces']
        i = 0
        self.pieces = []
        while i < len(pieces):
            self.pieces.append(pieces[i:i + 20])
            i += 20
        if b'files' not in info:
            # Single file mode
            log.info('Single file mode...')
            self.filename = bytes_to_str(info[b'name'])

    def __repr__(self):
        torrent_info = f'announce={self.announce} piece_length={self.piece_length}'
        if self.filename:
            torrent_info += f' filename={self.filename}'
        return torrent_info
