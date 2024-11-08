from dataclasses import dataclass
from typing import List
import os
from .utils import get_chunk_hash
from .logger import GFSLogger

logger = GFSLogger.get_logger('chunk')

@dataclass
class ChunkMetadata:
    chunk_id: str
    file_path: str
    chunk_index: int
    size: int
    locations: List[str]  # List of chunk server addresses

class Chunk:
    def __init__(self, data: bytes, file_path: str, chunk_index: int):
        logger.debug(f"Creating new chunk for file {file_path}, index {chunk_index}")
        self.data = data
        self.chunk_id = get_chunk_hash(data)
        self.file_path = file_path
        self.chunk_index = chunk_index
        self.size = len(data)
        self.locations = []
        logger.debug(f"Created chunk {self.chunk_id} with size {self.size} bytes")

    def save_to_disk(self, chunk_dir: str):
        """Save chunk data to disk."""
        logger.debug(f"Saving chunk {self.chunk_id} to directory {chunk_dir}")
        chunk_path = os.path.join(chunk_dir, self.chunk_id)
        os.makedirs(chunk_dir, exist_ok=True)
        with open(chunk_path, 'wb') as f:
            f.write(self.data)
        logger.debug(f"Successfully saved chunk to {chunk_path}")

    @staticmethod
    def load_from_disk(chunk_dir: str, chunk_id: str) -> bytes:
        """Load chunk data from disk."""
        logger.debug(f"Loading chunk {chunk_id} from directory {chunk_dir}")
        chunk_path = os.path.join(chunk_dir, chunk_id)
        with open(chunk_path, 'rb') as f:
            data = f.read()
        logger.debug(f"Successfully loaded chunk {chunk_id}, size: {len(data)} bytes")
        return data