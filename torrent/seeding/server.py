import asyncio
import logging
import random
from bitarray import bitarray
import struct


import const
import util
from log import get_logger

log = get_logger(__name__)
from typing import Dict

# from torrent_client import algorithms
# from torrent_client.models import Peer
from torrent.client import PeerClient
from models.peer import Peer



__all__= ['PeerServer']


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class PeerServer:
    def __init__(self, peer_id: bytes, torrents):
        self._torrent_list = torrents
        self._peer_id = peer_id
        self._client_executors = {}
        self._server = None
        self._port = None
        self.client = None

    async def _accept(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info('peername')
        peer = Peer(addr[0], addr[1], util.generate_id())
        log.info(f'Peer info {peer}')
        # client = PeerTCPClient(self._our_peer_id, peer)
        self.client = PeerClient(peer, None)

        try:
            info_hash = await self.client.accept(reader, writer)
            if info_hash not in self._torrent_list:
                raise ValueError('Unknown info_hash')
        except Exception as e:
            if self.client.writer is not None:
                self.client.writer.close()

            if isinstance(e, asyncio.CancelledError):
                raise
            else:
                log.debug("%s wasn't accepted because of %r", peer, e)
        else:
            self.client.torrent = self._torrent_list[info_hash]
            self._client_executors[peer] = asyncio.ensure_future(
                self._execute_peer_client(peer, self.client, need_connect=False))
            # self._torrent_managers[info_hash].accept_client(peer, client)

    PORT_RANGE = range(6881, 6889 + 1)

    async def start(self):
        for port in PeerServer.PORT_RANGE:
            try:
                self._server = await asyncio.start_server(self._accept, port=port)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.debug('exception on starting server on port %s: %r', port, e)
            else:
                self._port = port
                log.info('server started on port %s', port)
                return
        else:
            log.warning('failed to start a server')

    async def _execute_peer_client(self, peer: Peer, client: PeerClient, *, need_connect: bool):
        try:
            self._download_info = client.torrent.download_info
            self._piece_owned = bitarray(self._download_info.piece_count)
            self._piece_owned.setall(False)
            response = struct.pack('>B19s8x20s20s',
                                   const.PROTOCOL_LEN,
                                   const.PROTOCOL,
                                   client.torrent.info_hash,
                                   self._peer_id.encode('utf-8'))
            self.client.writer.write(response)
            self._send_bitfield()
            # self._peer_data[peer] = PeerData(client, asyncio.current_task(), time.time())
            # self._statistics.peer_count += 1
            # self._connected = True
            await client.start()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.debug('%s disconnected because of %r', peer, e)
            # client.close()

            del self._client_executors[peer]
    @property
    def port(self):
        return self._port

    async def stop(self):
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            log.info('server stopped')

    def _send_bitfield(self):
        if self.client.torrent.download_info.piece_count:
            # arr = bitarray([info.is_downloaded for info in self.client.torrent.download_info.pieces], endian='big')
            arr = bitarray([True for info in self.client.torrent.download_info.pieces], endian='big')
            length = len(arr.tobytes()) + 1
            self.client.writer.write(struct.pack('!IB', length, const.PeerMessage.bitfield.value))
            self.client.writer.write(arr.tobytes())
            # self.client.p(const.PeerMessage.bitfield, arr.tobytes())