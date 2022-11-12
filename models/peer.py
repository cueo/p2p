from collections import OrderedDict


class Peer:
    def __init__(self, ip: str, port: int, peer_id: bytes = None, url: str = None):
        self.ip = ip
        self.port = port
        self.peer_id = peer_id
        self.url = url

    def __repr__(self):
        return f'Peer(ip={self.ip}, port={self.port} peer_id={self.peer_id})'


def from_dict(peer_info: OrderedDict):
    ip = peer_info[b'ip'].decode()
    port = peer_info[b'port']
    url = f'http://[{ip}]:{port}'
    return Peer(ip=ip, port=port, peer_id=peer_info.get(b'peer id'), url=url)
