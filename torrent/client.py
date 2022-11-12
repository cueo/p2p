import asyncio
import struct
from asyncio import IncompleteReadError
from typing import List

from const import PROTOCOL_LEN, PROTOCOL, PEER_CONNECT_TIMEOUT, PeerMessage
from log import get_logger
from models.peer import Peer

log = get_logger(__name__)


class Client:
    def __init__(self, peers: List[Peer], info_hash: str, peer_id: str):
        self.peers = peers
        self.info_hash = info_hash
        self.peer_id = peer_id

        self.reader = None
        self.writer = None

        self.data_length = 68
        self.state = 'choked'

    async def _connect_to_peer(self, peer: Peer):
        try:
            self.reader, self.writer = await asyncio.wait_for(asyncio.open_connection(peer.ip, peer.port),
                                                              timeout=PEER_CONNECT_TIMEOUT)
            log.info(f'Connection opened to peer={self.peer_id}')
            await self._handshake()
            response = await asyncio.wait_for(self.reader.readexactly(self.data_length),
                                              timeout=PEER_CONNECT_TIMEOUT)
            if response[28:48] != self.info_hash:
                log.error(f"Info hash doesn't match for peer={peer.peer_id}!")
                return
            log.info(f'Verified info hash for peer={peer.peer_id}.')
            await self._interested()

            response = await self._receive_message()
            assert response is not None

        except IncompleteReadError:
            log.warn(f'0 bytes read from peer={self.peer_id}')
        except TimeoutError:
            log.warn(f'peer={self.peer_id} timed out')
        except Exception as e:
            log.error(f'peer={self.peer_id} failed with error: {e}')

    async def _receive_message(self):
        # read length
        response = await asyncio.wait_for(self.reader.readexactly(4), timeout=PEER_CONNECT_TIMEOUT)
        (length,) = struct.unpack('!I', response)

        response = await asyncio.wait_for(self.reader.readexactly(length), timeout=PEER_CONNECT_TIMEOUT)
        try:
            message_id = PeerMessage(response[0])
        except ValueError:
            return

        payload = response[1:]

        log.info('Received and parsed response.')
        return message_id, payload

    async def connect(self):
        """
        Connect to peers.
        """
        log.info(f'Attempting connection to {len(self.peers)} peers.')
        tasks = [self._connect_to_peer(peer) for peer in self.peers[:5]]
        await asyncio.gather(*tasks)

    async def _handshake(self):
        info_hash = self.info_hash
        handshake_bytes = struct.pack('>B19s8x20s20s',
                                      PROTOCOL_LEN,
                                      PROTOCOL,
                                      info_hash,
                                      self.peer_id.encode('utf-8'))
        # handshake_bytes = bytes(PROTOCOL_LEN) + PROTOCOL + (b'\0' * 8)
        log.info(f'Sending message={handshake_bytes}')
        self.data_length = len(handshake_bytes)
        self.writer.write(handshake_bytes)
        log.info('Handshake completed.')

    async def _interested(self):
        self.state = 'interested'
        msg = struct.pack('>Ib', 1, PeerMessage.interested.value)
        self.writer.write(msg)
        log.info('Sent interested message!')
        await self.writer.drain()
