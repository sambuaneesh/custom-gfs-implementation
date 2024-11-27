---
title: Utils
description: Utility functions and helpers
sidebar:
  order: 6
---

The Utils module provides essential utility functions for network communication, data hashing, and system operations in the GFS implementation.

## Core Functions

### Data Hashing

```python
def get_chunk_hash(data: bytes) -> str:
    """Generate a unique hash for chunk data."""
    hash_value = hashlib.sha256(data).hexdigest()
    return hash_value
```

Features:
- SHA-256 hashing algorithm
- Unique chunk identification
- Data integrity verification
- Binary data handling

### Network Utilities

1. **Port Management**
```python
def find_free_port() -> int:
    """Find a free port to use for a new chunk server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port
```

Features:
- Automatic port discovery
- System port availability check
- Dynamic server allocation

### Message Protocol

1. **Message Sending**
```python
def send_message(sock: socket.socket, message: Any):
    """Send a pickled message over a socket with length prefix."""
    data = pickle.dumps(message)
    length = struct.pack('!I', len(data))
    sock.sendall(length + data)
```

Key aspects:
- Length-prefixed messages
- Pickle serialization
- Network byte order
- Atomic sending

2. **Message Receiving**
```python
def receive_message(sock: socket.socket) -> Any:
    """Receive a pickled message from a socket with length prefix."""
    # Read message length
    length_data = sock.recv(4)
    length = struct.unpack('!I', length_data)[0]
    
    # Read message in chunks
    chunks = []
    bytes_received = 0
    while bytes_received < length:
        chunk = sock.recv(min(length - bytes_received, 4096))
        chunks.append(chunk)
        bytes_received += len(chunk)
    
    return pickle.loads(b''.join(chunks))
```

Features:
- Chunked reading
- Buffer management
- Connection monitoring
- Error handling

## Implementation Details

### Message Format
```
+---------------+------------------+
| Length (4B)   | Pickled Data    |
+---------------+------------------+
```

1. **Length Prefix**
   - 4 bytes (unsigned integer)
   - Network byte order (big-endian)
   - Maximum message size: 4GB

2. **Data Section**
   - Pickle-serialized data
   - Variable length
   - Supports complex Python objects

### Error Handling

1. **Connection Errors**
```python
try:
    peer = sock.getpeername()
    # ... message handling ...
except Exception as e:
    logger.error(f"Error receiving message: {e}", exc_info=True)
    return None
```

2. **Incomplete Messages**
```python
if not chunk:
    logger.warning("Connection closed before receiving complete message")
    return None
```

## Logging Integration

```python
logger = GFSLogger.get_logger('utils')

# Debug logging
logger.debug(f"Generating hash for chunk of size {len(data)} bytes")
logger.debug(f"Found free port: {port}")
logger.debug(f"Sending message to {sock.getpeername()}")
```

Features:
- Component-specific logging
- Debug information
- Error tracking
- Operation monitoring

## Best Practices

1. **Socket Management**
   - Use context managers
   - Handle connection timeouts
   - Clean up resources
   - Monitor connection state

2. **Data Handling**
   - Verify message integrity
   - Handle partial reads
   - Implement timeouts
   - Buffer size management

3. **Error Recovery**
   - Connection retries
   - Graceful degradation
   - Resource cleanup
   - Error logging

## Usage Examples

1. **Message Communication**
```python
# Sending a message
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('localhost', 5000))
send_message(sock, {'command': 'hello', 'data': 'world'})

# Receiving a message
response = receive_message(sock)
print(response)
```

2. **Port Management**
```python
# Find and use a free port
port = find_free_port()
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('localhost', port))
```

3. **Data Hashing**
```python
# Generate chunk hash
data = b"chunk data"
hash_value = get_chunk_hash(data)
print(f"Chunk hash: {hash_value}")
```

## Performance Considerations

1. **Message Chunking**
   - Optimal chunk size (4KB)
   - Memory efficiency
   - Network performance
   - Buffer management

2. **Serialization**
   - Pickle protocol version
   - Data structure optimization
   - Memory usage
   - Security considerations

## Related Components
- [Master Server](master)
- [Chunk Server](chunk-server)
- [Client](client)