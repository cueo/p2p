import log
import socket
from struct import unpack
from urllib.parse import urlencode

import bencodepy
import requests

from const import CHUNK_SIZE
from log import get_logger
from models import peer
from models.peer import Peer
from models.torrent import Torrent
from util import generate_id

log = get_logger(__name__)


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
            log.debug('List of peers returned by tracker')
            peers = [peer.from_dict(p) for p in peers]
        else:
            log.debug('Binary model peers are returned by tracker')

            # Split the string in pieces of length 6 bytes, where the first
            # 4 characters is the IP the last 2 is the TCP port.
            peers = [peers[i:i + 6] for i in range(0, len(peers), 6)]

            # Convert the encoded address to a list of tuples
            peers = [(socket.inet_ntoa(p[:4]), _decode_port(p[4:]))
                     for p in peers]
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


def _decode_port(port):
    return unpack(">H", port)[0]


def announce(torrent: Torrent) -> TrackerResponse:
    params = {
        'uploaded': 0,
        'peer_id': torrent.peer_id,
        'downloaded': 0,
        'left': torrent.piece_length,
        'port': 10000,
        'info_hash': torrent.info_hash
    }
    params_str = urlencode(params, safe='%')

    with requests.get(url=torrent.announce, params=params_str, stream=True) as r:
        r.raise_for_status()
        announce_response = b''
        for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
            announce_response += chunk
        response = TrackerResponse(bencodepy.decode(announce_response))
        return response


def connect(peer: Peer):
    r = requests.get(peer.url)

