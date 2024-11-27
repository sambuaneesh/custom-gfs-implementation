---
title: Chunk Server
description: Storage component for file chunks
sidebar:
  order: 2
---

The Chunk Server is responsible for storing and managing file chunks in the GFS system. It handles data storage, replication, and space management while maintaining awareness of its geographical location.

## Core Functionality

### Initialization and Configuration
```python
class ChunkServer:
    def __init__(self, config_path: str, server_id: str = None, space_limit_mb: int = 1024, x: float = 0, y: float = 0):
        self.server_id = server_id or f"chunk_server_{int(time.time())}"
        self.space_limit = space_limit_mb * 1024 * 1024  # Convert MB to bytes
        self.location = (x, y)
```

Key features:
- Configurable space limits
- Geographic location awareness
- Unique server identification
- Automatic port assignment

### Space Management

1. **Space Monitoring**
```python
def get_available_space(self) -> int:
    """Get available space in bytes."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(self.data_dir):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return self.space_limit - total_size
```

2. **Space Verification**
```python
def can_store_chunk(self, chunk_size: int) -> bool:
    """Check if there's enough space to store a chunk."""
    return self.get_available_space() >= chunk_size
```

### Chunk Operations

1. **Chunk Storage**
```python
def _handle_store_chunk(self, client_socket: socket.socket, message: Dict):
```
Features:
- Space availability check
- Two-phase commit protocol
- Replication coordination
- Transaction logging

2. **Chunk Retrieval**
```python
def _handle_retrieve_chunk(self, client_socket: socket.socket, message: Dict):
```
- Efficient data loading
- Error handling
- Socket-based transfer

### Replication System

1. **Primary Server Role**
```python
def _replicate_chunk(self, chunk_data: bytes, file_path: str, chunk_index: int, 
                    replica_servers: List[str], current_replica: int = 0):
```
- Manages replication chain
- Coordinates with replicas
- Handles failures

2. **Replica Role**
```python
def _handle_store_chunk(self, client_socket: socket.socket, message: Dict):
    if 'replica_servers' in message:
        # Handle replica storage
```

### Two-Phase Commit Protocol

1. **Preparation Phase**
```python
def _handle_prepare_chunk(self, client_socket: socket.socket, message: Dict):
```
- Creates temporary files
- Verifies space availability
- Prepares for commit

2. **Commit Phase**
```python
def _handle_commit_chunk(self, client_socket: socket.socket, message: Dict):
```
- Atomic file operations
- Transaction completion
- Error recovery

3. **Rollback**
```python
def _handle_rollback_chunk(self, client_socket: socket.socket, message: Dict):
```
- Cleanup temporary files
- State restoration
- Transaction logging

### Master Communication

1. **Registration**
```python
def _register_with_master(self):
```
- Location information
- Space capacity
- Server identification

2. **Heartbeat System**
```python
def _send_heartbeat(self):
```
Features:
- Regular status updates
- Space usage reporting
- Location confirmation

## Error Handling

1. **Space Management**
```python
if not self.can_store_chunk(chunk_size):
    send_message(client_socket, {
        'status': 'error',
        'message': 'insufficient_space',
        'available_space': self.get_available_space()
    })
```

2. **Transaction Failures**
```python
try:
    # Operation code
except Exception as e:
    if os.path.exists(temp_path):
        os.remove(temp_path)
    raise
```

## Configuration

```toml
[chunk_server]
data_dir = "data/chunks"
heartbeat_interval = 5
server_info_file = "data/chunks/server_info.json"
space_limit_mb = 1024
```

## Usage Examples

1. **Starting a Chunk Server**
```bash
# Start with location and space limit
python run_chunk_server.py --server_id chunk1 --x 10 --y 20 --space 2048
```

2. **Space Management**
```python
# Check available space
available = chunk_server.get_available_space()
print(f"Available space: {available / (1024*1024):.2f} MB")
```

## Best Practices

1. **Space Management**
   - Regular space monitoring
   - Proactive cleanup
   - Space threshold alerts

2. **Replication**
   - Verify replica chain
   - Monitor replication status
   - Handle partial failures

3. **Error Handling**
   - Transaction logging
   - Temporary file cleanup
   - Connection retry logic

## Related Components
- [Master Server](master)
- [Chunk](chunk)