import asyncio
import random
import struct
from abc import ABC, abstractmethod
from asyncio import DatagramProtocol, BaseTransport, BaseProtocol
from asyncio.exceptions import TimeoutError
from struct import unpack
from typing import Tuple
from urllib.parse import urlencode
from urllib.parse import urlparse

import aiohttp
import bencodepy
from yarl import URL

from const import CHUNK_SIZE, ActionType
from log import get_logger
from models import peer
from models.torrent import Torrent

logger = get_logger(__name__)


class TrackerResponse:
    """
    The response from the tracker after a successful connection to the
    trackers announce URL.

    Even though the connection was successful from a network point of view,
    the tracker might have returned an error (stated in the `failure`
    property).
    """

    def __init__(self, response: dict):
        self.response = response

    @property
    def failure(self):
        """
        If this response was a failed response, this is the error message to
        why the tracker request failed.

        If no error occurred this will be None
        """
        if b'failure reason' in self.response:
            return self.response[b'failure reason'].decode('utf-8')
        return None

    @property
    def interval(self) -> int:
        """
        Interval in seconds that the client should wait between sending
        periodic requests to the tracker.
        """
        return self.response.get(b'interval', 0)

    @property
    def complete(self) -> int:
        """
        Number of peers with the entire file, i.e. seeders.
        """
        return self.response.get(b'complete', 0)

    @property
    def incomplete(self) -> int:
        """
        Number of non-seeder peers, aka "leechers".
        """
        return self.response.get(b'incomplete', 0)

    @property
    def peers(self):
        """
        A list of tuples for each peer structured as (ip, port)
        """
        # The BitTorrent specification specifies two types of responses. One
        # where the peers field is a list of dictionaries and one where all
        # the peers are encoded in a single string
        peers = self.response[b'peers']
        if type(peers) == list:
            logger.debug('List of peers returned by tracker')
            peers = peer.from_dict(peers)
        else:
            logger.debug('Binary model peers are returned by tracker')
            peers = peer.from_bytes(peers)
        return peers

    # def __str__(self):
    #     return "incomplete: {incomplete}\n" \
    #            "complete: {complete}\n" \
    #            "interval: {interval}\n" \
    #            "peers: {peers}\n".format(
    #                incomplete=self.incomplete,
    #                complete=self.complete,
    #                interval=self.interval,
    #                peers=", ".join([x for (x, _) in self.peers]))


class BaseTracker(ABC):
    @abstractmethod
    async def announce(self) -> TrackerResponse:
        pass


class HttpTracker(BaseTracker):
    def __init__(self, torrent: Torrent):
        self.torrent = torrent

    async def announce(self) -> TrackerResponse:
        params = {
            'uploaded': 0,
            'peer_id': self.torrent.peer_id,
            'downloaded': 0,
            'left': self.torrent.piece_length,
            'port': 10000,
            'info_hash': self.torrent.info_hash
        }
        params_str = urlencode(params, safe='%')

        async with aiohttp.ClientSession() as session:
            url = f'{self.torrent.announce}?{params_str}'
            async with session.get(URL(url, encoded=True)) as r:
                announce_response = b''
                while True:
                    chunk = await r.content.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    announce_response += chunk
                response = TrackerResponse(bencodepy.decode(announce_response))
                return response


class UdpTracker(DatagramProtocol, BaseTracker):
    def __init__(self, torrent: Torrent):
        self.torrent = torrent

        self.received_message = None

        self.loop = asyncio.get_event_loop()
        self.delivery_tracker = {}
        self.transport = None

    MAGIC_CONNECTION_ID = 0x41727101980

    RESPONSE_HEADER_FMT = '!II'
    RESPONSE_HEADER_LEN = struct.calcsize(RESPONSE_HEADER_FMT)

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        logger.info(f'Data received from {addr=}, yay!!!')
        action, tid = struct.unpack('!II', data[:8])
        self.received_message = data
        if tid in self.delivery_tracker:
            self.delivery_tracker[tid].set()
        else:
            logger.warning('Invalid transaction ID received.')

    async def announce(self):
        tid = random.randint(0, 2 ** 32 - 1)
        self.delivery_tracker[tid] = asyncio.Event()
        request = pack(
            'Q', UdpTracker.MAGIC_CONNECTION_ID,
            'I', 0,
            'I', tid,
        )
        logger.info(f'Sending UDP connect request, {tid=}.')
        try:
            self.transport.sendto(request)
            await asyncio.wait_for(self.delivery_tracker[tid].wait(), timeout=5)
            del self.delivery_tracker[tid]
        except TimeoutError as e:
            logger.error('UDP connection timed out while waiting for reply!')
            raise e
        logger.info(f'UDP connection successful for {tid=}')

        (connection_id,) = struct.unpack_from('!Q', self.received_message, UdpTracker.RESPONSE_HEADER_LEN)
        request = pack(
            'Q', connection_id,
            'I', ActionType.announce.value,
            'I', tid,
            '20s', self.torrent.info_hash,
            '20s', self.torrent.peer_id.encode('utf-8'),
            'Q', 0,
            'Q', self.torrent.piece_length,
            'Q', 0,
            'I', 2,  # event.value,
            'I', 0,  # IP address: default
            'I', random.randint(0, 2 ** 32 - 1),  # Key
            'i', -1,  # numwant: default
            'H', 10000,
        )
        self.delivery_tracker[tid] = asyncio.Event()
        self.transport.sendto(request)
        await asyncio.wait_for(self.delivery_tracker[tid].wait(), timeout=500)
        del self.delivery_tracker[tid]
        logger.info(f'UDP announce successful for {tid=}')

        fmt = '!3I'
        interval, leech_count, seed_count = struct.unpack_from(fmt, self.received_message,
                                                               UdpTracker.RESPONSE_HEADER_LEN)
        compact_peer_list = self.received_message[UdpTracker.RESPONSE_HEADER_LEN + struct.calcsize(fmt):]
        return TrackerResponse({
            b'interval': interval,
            b'complete': seed_count,
            b'incomplete': leech_count,
            b'peers': compact_peer_list
        })


async def start_udp_tracker(torrent: Torrent) -> Tuple[BaseTransport, BaseProtocol]:
    if torrent.announce_list:
        url = random.choice(torrent.announce_list)
        # so that we don't hit a bad tracker twice
        torrent.announce_list.remove(url)
    else:
        url = torrent.announce
    host, port = parse_url(url)
    logger.info(f'Attempting UDP connection with {host=} {port=}.')
    loop = asyncio.get_event_loop()
    transport, proto = await loop.create_datagram_endpoint(lambda: UdpTracker(torrent), remote_addr=(host, port))
    return transport, proto


class TrackerClient:
    def __init__(self, torrent: Torrent):
        self.torrent = torrent
        self.loop = asyncio.get_event_loop()

    async def announce(self) -> TrackerResponse:
        torrent = self.torrent
        if torrent.announce.startswith('udp'):
            while True:
                transport, proto = await asyncio.create_task(start_udp_tracker(torrent))
                logger.info('Started UDP tracker client.')
                try:
                    return await proto.announce()
                except TimeoutError:
                    pass
        else:
            return await HttpTracker(torrent).announce()


def parse_url(url: str) -> Tuple[str, int]:
    parsed_url = urlparse(url)
    host, port = parsed_url.netloc.split(':')
    return host, int(port)


def _decode_port(port):
    return unpack(">H", port)[0]


def pack(*data) -> bytes:
    assert len(data) % 2 == 0

    common_format = '!' + ''.join(fmt for fmt in data[::2])
    values = [elem for elem in data[1::2]]
    return struct.pack(common_format, *values)
