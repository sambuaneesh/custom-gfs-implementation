import hashlib
import socket
import random
import struct
import pickle
from typing import Any, Dict, List, Tuple
from .logger import GFSLogger

logger = GFSLogger.get_logger('utils')

def get_chunk_hash(data: bytes) -> str:
    """Generate a unique hash for chunk data."""
    logger.debug(f"Generating hash for chunk of size {len(data)} bytes")
    hash_value = hashlib.sha256(data).hexdigest()
    logger.debug(f"Generated hash: {hash_value}")
    return hash_value

def find_free_port() -> int:
    """Find a free port to use for a new chunk server."""
    logger.debug("Finding free port")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    logger.debug(f"Found free port: {port}")
    return port

def send_message(sock: socket.socket, message: Any):
    """Send a pickled message over a socket with length prefix."""
    logger.debug(f"Sending message to {sock.getpeername()}")
    data = pickle.dumps(message)
    length = struct.pack('!I', len(data))
    sock.sendall(length + data)
    logger.debug(f"Sent {len(data)} bytes of data")

def receive_message(sock: socket.socket) -> Any:
    """Receive a pickled message from a socket with length prefix."""
    try:
        peer = sock.getpeername()
        logger.debug(f"Receiving message from {peer}")
        
        length_data = sock.recv(4)
        if not length_data:
            logger.warning("Received empty length data")
            return None
        
        length = struct.unpack('!I', length_data)[0]
        logger.debug(f"Expecting message of length {length} bytes")
        
        chunks = []
        bytes_received = 0
        
        while bytes_received < length:
            chunk = sock.recv(min(length - bytes_received, 4096))
            if not chunk:
                logger.warning("Connection closed before receiving complete message")
                return None
            chunks.append(chunk)
            bytes_received += len(chunk)
        
        logger.debug(f"Received complete message ({bytes_received} bytes)")
        return pickle.loads(b''.join(chunks))
    except Exception as e:
        logger.error(f"Error receiving message: {e}", exc_info=True)
        return None