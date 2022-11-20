import hashlib
from dataclasses import dataclass
from typing import List, Dict, Any

import bencodepy

from const import PIECE_SHA_LENGTH
from log import get_logger
from models.piece import DownloadInfo, Piece
from util import bytes_to_str, generate_id
import asyncio
log = get_logger(__name__)


@dataclass
class File:
    length: int
    path: str


@dataclass
class Torrent:
    peer_id: str
    length: int
    file_length: int
    announce: str
    announce_list: List[str]
    piece_length: int
    dir: str
    filename: str
    files: List[File]
    info_hash: bytes
    download_info: DownloadInfo
    uploaded: str
    downloaded: str
    left: str
    port: str
    compact: str
    pieces: List[Piece]
    files: List[File]

    def __init__(self, filepath: str):
        self.peer_id = generate_id()
        self.filepath = filepath
        self.length = 0
        self._loop = asyncio.get_event_loop()
        self.decode()

    def decode(self):
        with open(self.filepath, 'rb') as f:
            torrent = bencodepy.decode(f.read())
        self.announce = bytes_to_str(torrent[b'announce'])
        announce_list = []
        if b'announce-list' in torrent:
            for _url in torrent[b'announce-list']:
                # noinspection PyTypeChecker
                url = bytes_to_str(_url[0])
                if url.startswith('udp') or url.startswith('http'):
                    announce_list.append(url)
        self.announce_list = announce_list
        info = torrent[b'info']
        self.info_hash = hashlib.sha1(bencodepy.bencode(info)).digest()
        self.decode_info(info)

    def decode_info(self, info: Dict[bytes, Any]):
        self.piece_length = info[b'piece length']
        self.file_length = info[b'length']
        pieces = info[b'pieces']
        i = 0
        self.pieces = []
        while i < len(pieces):
            self.pieces.append(Piece(pieces[i:i + PIECE_SHA_LENGTH], self.piece_length, set()))
            i += 20
        self.pieces[-1].is_last = True
        piece_count = len(self.pieces)
        self.download_info = DownloadInfo(piece_count, self.pieces)
        if b'files' not in info:
            # Single file mode
            log.info('Single file mode...')
            self.files = [File(info[b'length'], bytes_to_str(info[b'name']))]
            self.length = sum([file.length for file in self.files])
            self.filename = bytes_to_str(info[b'name'])
            log.info(f'Org File Name={self.filename}')
        else:
            log.info('Multiple files mode...')
            self.files = [File(file[b'length'], file[b'path'][-1].decode('utf-8')) for file in info[b'files']]
            self.length = sum([file.length for file in self.files])

    def __repr__(self):
        torrent_info = f'announce={self.announce} piece_length={self.piece_length} piece_count={self.download_info.piece_count}'
        # if self.filename:
        #     torrent_info += f' filename={self.filename}'
        return torrent_info
