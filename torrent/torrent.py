import hashlib
from dataclasses import dataclass
from typing import List, Dict, Any

import bencodepy
import bencoding
import requests

from log import get_logger
from util import bytes_to_str
from torrent.Tracker import TrackerResponse

log = get_logger(__name__)


@dataclass
class File:
    length: int
    path: str


@dataclass
class Torrent:
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
        self.filepath = filepath
        self.decode()
        
    def decode(self):
        with open(self.filepath, 'rb') as f:
            torrent = bencodepy.decode(f.read())
        self.announce = bytes_to_str(torrent[b'announce'])
        info = torrent[b'info']
        self.info_hash = hashlib.sha1(bencoding.bencode(info)).hexdigest()
        self.info_hash = "%"+"%".join(list(self.info_hash[i:i+2] for i in range(0, len(self.info_hash), 2)))
        self.decode_info(info)
        self.connect_tracker()

    def decode_info(self, info: Dict[bytes, Any]):
        self.piece_length = info[b'piece length']
        pieces = info[b'pieces']
        i = 0
        self.pieces = []
        while i < len(pieces):
            self.pieces.append(pieces[i:i+20])
            i += 20
        if b'files' not in info:
            # Single file mode
            log.info('Single file mode...')
            self.filename = bytes_to_str(info[b'name'])

    def connect_tracker(self):
        params = {'uploaded': 0,
                  'peer_id': 'ABDEFGHIJKLMNOPQRSTC',
                  'downloaded': 0,
                  'left': self.piece_length,
                  'port': 10000,
                  'info_hash': self.info_hash
                  }
        url = self.announce + '?'
        for key, value in params.items():
            url += key + '=' + str(value) + '&'
        url = url[:-1]
        with requests.get(url, stream=True) as f:
            f.raise_for_status()
            with open('announce', 'wb') as k:
                for chunk in f.iter_content(chunk_size=8192):
                    k.write(chunk)
                    response = TrackerResponse(bencoding.Decoder(chunk).decode())
                    print(response.peers())



    def __repr__(self):
        torrent_info = f'announce={self.announce} piece_length={self.piece_length}'
        if self.filename:
            torrent_info += f' filename={self.filename}'
        return torrent_info
