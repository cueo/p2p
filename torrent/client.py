import asyncio
import os.path
import struct
from asyncio import IncompleteReadError
from typing import List

import math
from aiofile import async_open
from bitarray import bitarray

from const import PROTOCOL_LEN, PROTOCOL, PEER_CONNECT_TIMEOUT, PeerMessage, BLOCK_SIZE, DOWNLOAD_PATH
from log import get_logger
from models.peer import Peer
from models.piece import Block
from models.request import BlockRequest
from models.torrent import Torrent

log = get_logger(__name__)


class Client:
    def __init__(self, peers: List[Peer], torrent: Torrent):
        self.peers = peers
        self.torrent = torrent

        self.peer_connections = None
        self.init_blocks()

        self.fd = None

    async def connect(self):
        """
        Connect to peers.
        """
        log.info(f'Attempting connection to {len(self.peers)} peers.')
        self.peer_connections = {peer.peer_id: PeerClient(peer, self.torrent) for peer in self.peers}
        tasks = [self.peer_connections[peer.peer_id].connect() for peer in self.peers]
        await asyncio.gather(*tasks)
        log.info('Successfully connected to all the peers!')

    def init_blocks(self):
        self._create_file()
        for index, piece in enumerate(self.torrent.pieces):
            n_blocks = math.ceil(self.torrent.piece_length / BLOCK_SIZE)
            piece.blocks = [Block(index, offset * BLOCK_SIZE, BLOCK_SIZE) for offset in range(n_blocks)]
        if self.torrent.piece_length % BLOCK_SIZE != 0:
            self.torrent.pieces[-1].blocks[-1].length = self.torrent.piece_length % BLOCK_SIZE
        log.info('Successfully initialized blocks.')

    def _create_file(self):
        if not os.path.exists(DOWNLOAD_PATH):
            os.mkdir(DOWNLOAD_PATH)
        if self.torrent.files is None:
            path = os.path.join(DOWNLOAD_PATH, self.torrent.filename)
            if not os.path.exists(path):
                with open(path, 'w') as _:
                    pass
        else:
            for file in self.torrent.files:
                path = os.path.join(DOWNLOAD_PATH, file.path)
                if not os.path.exists(path):
                    with open(path, 'w') as _:
                        pass

    async def download(self):
        for i, piece in enumerate(self.torrent.download_info.pieces):
            # peer = piece.owners.pop()
            peer = list(piece.owners)[0]
            await self.peer_connections[peer.peer_id].download(i)

    async def upload(self, peer_id, piece_index, block_index):

        await self.peer_connections[peer.peer_id].download(i)



class PeerClient:
    def __init__(self, peer: Peer, torrent: Torrent):
        self.peer = peer
        self.torrent = torrent

        self.reader = None
        self.writer = None

        self.is_choked = True
        self.is_interested = False

        # self.path = os.path.join(DOWNLOAD_PATH, self.torrent.filename)

    async def connect(self):
        try:
            self.reader, self.writer = await asyncio.wait_for(asyncio.open_connection(self.peer.ip, self.peer.port),
                                                              timeout=PEER_CONNECT_TIMEOUT)
            log.info(f'Connection opened to peer={self.torrent.peer_id}')
            await self._handshake()
            response = await asyncio.wait_for(self.reader.readexactly(self.data_length),
                                              timeout=PEER_CONNECT_TIMEOUT)
            if response[28:48] != self.torrent.info_hash:
                log.error(f"Info hash doesn't match for peer={self.peer.peer_id}!")
                return
            log.info(f'Verified info hash for peer={self.peer.peer_id}.')
            await self._interested()

            while True:
                await self._receive_message()
                if not self.is_choked:
                    break

        except TimeoutError:
            log.warn(f'peer={self.torrent.peer_id} timed out')
        except Exception as e:
            log.error(f'peer={self.torrent.peer_id} failed with error: {e}')

    async def _receive_message(self):
        try:
            # read length
            response = await asyncio.wait_for(self.reader.readexactly(4), timeout=PEER_CONNECT_TIMEOUT)
            (length,) = struct.unpack('!I', response)
            log.info(f'Message length={length}')
            response = await asyncio.wait_for(self.reader.readexactly(length), timeout=PEER_CONNECT_TIMEOUT)
            # log.info(f'Message info={response}')
        except IncompleteReadError:
            log.warn(f'0 bytes read from peer={self.torrent.peer_id}')
            return

        if not response:
            log.warn('Received empty response.')
            return
        try:
            message_id = PeerMessage(response[0])
            log.info(f'Received a message.={str(response)}')
        except ValueError:
            return

        payload = response[1:]
        if message_id == PeerMessage.bitfield:
            self._handle_bitfield(payload)
        elif message_id == PeerMessage.unchoke:
            self._handle_unchoke()
        elif message_id == PeerMessage.piece:
            log.info('Received a piece message, yay!')
            await self._handle_piece(payload)
        elif message_id == PeerMessage.request:
            await self._handle_piece(payload)
        else:
            log.info(f'Received a non-bitfield message, type={message_id}')

        log.info('Received and parsed response.')

    async def _handshake(self):
        info_hash = self.torrent.info_hash
        handshake_bytes = struct.pack('>B19s8x20s20s',
                                      PROTOCOL_LEN,
                                      PROTOCOL,
                                      info_hash,
                                      self.torrent.peer_id.encode('utf-8'))
        log.info(f'Sending message={handshake_bytes}')
        self.data_length = len(handshake_bytes)
        self.writer.write(handshake_bytes)
        log.info('Handshake completed.')

    async def _interested(self):
        self.is_interested = True
        msg = struct.pack('>Ib', 1, PeerMessage.interested.value)
        self.writer.write(msg)
        log.info('Sent interested message!')
        await self.writer.drain()

    def _handle_bitfield(self, payload):
        arr = bitarray(endian='big')
        arr.frombytes(payload)
        piece_count = self.torrent.download_info.piece_count
        for i in range(piece_count):
            if arr[i]:
                self._add_owner(i)
        for i in range(piece_count, len(arr)):
            if arr[i]:
                raise ValueError('Spare bits in "bitfield" message must be zero')

    def _add_owner(self, piece_index):
        self.torrent.download_info.pieces[piece_index].owners.add(self.peer)

    def _handle_unchoke(self):
        log.info(f'Received unchoked from peer={self.peer.peer_id}')
        self.is_choked = False

    async def download(self, piece_index: int):
        blocks = self.torrent.pieces[piece_index].blocks
        for block in blocks:
            payload = struct.pack('!3I', piece_index, block.offset, block.length)
            self._send_message(PeerMessage.request, payload)
        log.info(f'Request blocks for piece={piece_index}')
        log.info('Sent message, receiving now...')
        while True:
            await self._receive_message()

    def _send_message(self, message_type: PeerMessage, payload: bytes):
        length = len(payload) + 1
        self.writer.write(struct.pack('!IB', length, message_type.value))
        self.writer.write(payload)

    async def _handle_piece(self, payload: bytes):
        fmt = '!2I'
        piece_index, block_begin = struct.unpack_from(fmt, payload)
        block_index = int(block_begin/BLOCK_SIZE)
        log.info(f'Block Index={block_index}')
        log.info(f'Block Begin={block_begin}')
        log.info(f'No of pieces={len(self.torrent.pieces)}')
        piece = self.torrent.pieces[piece_index]
        log.info(f'No of blocks={len(piece.blocks)}')
        if piece.is_downloaded:
            return
        piece.blocks[block_index].is_downloaded = True
        if all([block.is_downloaded for block in piece.blocks]):
            log.info('Piece is already downloaded.')
            piece.is_downloaded = True

        block_data = payload[struct.calcsize(fmt):]
        await self._write(piece_index * self.torrent.piece_length + block_begin, block_data)

    async def _write(self, offset: int, data: bytes):
        file_index = 0
        length = self.torrent.files[0].length
        while offset > length:
            file_index += 1
            length += self.torrent.files[file_index].length

        file_to_write = self.torrent.files[file_index]
        for i in range(0, file_index):
            offset -= self.torrent.files[i].length
        filepath = os.path.join(DOWNLOAD_PATH, file_to_write.path)
        log.info(f'File Name={file_to_write.path}')
        async with async_open(filepath, 'r+b') as afp:
            afp.seek(offset)
            await afp.write(data)

        # self.fd.seek(offset)
        # self.fd.write(data)
        log.info('Successfully wrote to the file.')

    ###### send a block of code upon receiving a request
    async def _send_block(self, request: BlockRequest):

        # TODO: Read the data from mile here
        block = None
        self._send_message(PeerMessage.piece, struct.pack('!2I', request.piece_index, request.block_begin), block)

        self._uploaded += request.block_length
        self._download_info.session_statistics.add_uploaded(self._peer, request.block_length)

    async def _accept(self):
        return None