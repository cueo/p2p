from dataclasses import dataclass
from enum import Enum
from typing import List


class BlockState(Enum):
    MISSING = 1
    PENDING = 2
    COMPLETED = 3


@dataclass
class Block:
    piece: int
    offset: int
    length: int
    data: bytes = None
    status: BlockState = BlockState.MISSING
    is_downloaded: bool = False


@dataclass
class Piece:
    hash: bytes
    length: int
    owners: set
    blocks: List[Block] = None
    is_last: bool = False
    is_downloaded: bool = False


@dataclass
class DownloadInfo:
    piece_count: int
    pieces: List[Piece]
