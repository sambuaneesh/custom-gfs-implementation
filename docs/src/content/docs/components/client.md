---
title: Client
description: Client interface for interacting with GFS
sidebar:
  order: 3
---

The Client component provides the interface for interacting with the GFS system. It handles file operations, coordinates with the master server, and manages location-aware chunk server selection.

## Core Implementation

### Client Initialization
```python
class GFSClient:
    def __init__(self, config_path: str, client_id: str = None, x: float = 0, y: float = 0):
        self.client_id = client_id or f"client_{int(time.time())}"
        self.location = (x, y)
        self._register_with_master()
```

Key features:
- Geographic location awareness
- Unique client identification
- Master server registration
- Configuration management

### File Operations

1. **File Upload**
```python
def upload_file(self, local_path: str, gfs_path: str):
    """Upload a file to GFS."""
    # Read and split file into chunks
    with open(local_path, 'rb') as f:
        data = f.read()
    
    chunks = []
    for i in range(0, len(data), self.chunk_size):
        chunk_data = data[i:i + self.chunk_size]
        chunk = Chunk(chunk_data, gfs_path, len(chunks))
        chunks.append(chunk)
```

Features:
- Automatic chunking
- Space verification
- Location-aware server selection
- Replication coordination

2. **File Download**
```python
def download_file(self, gfs_path: str, local_path: str):
    """Download a file from GFS."""
    # Get file metadata
    metadata = self._get_file_metadata(gfs_path)
    
    # Download chunks
    chunks_data = []
    for chunk_id in metadata.chunk_ids:
        chunk_data = self._download_chunk(gfs_path, chunk_id)
        chunks_data.append(chunk_data)
```

Features:
- Chunk reassembly
- Nearest server selection
- Error handling
- Progress tracking

### Append Operations

1. **File Append**
```python
def append_to_file(self, gfs_path: str, data: bytes):
    """Append data to a file in GFS."""
    metadata = self._get_file_metadata(gfs_path)
    
    if metadata.last_chunk_offset + len(data) > self.chunk_size:
        # Create new chunk
        self._create_new_chunk(gfs_path, data)
    else:
        # Append to existing chunk
        self._append_to_chunk(gfs_path, metadata.last_chunk_id, data)
```

2. **Two-Phase Commit**
```python
def _two_phase_append(self, file_path: str, chunk_id: str, data: bytes, 
                     offset: int, locations: List[str]) -> bool:
    """Execute two-phase commit for append operation."""
    # Phase 1: Prepare
    prepared_servers = self._prepare_append(chunk_id, data, locations)
    
    # Phase 2: Commit if all prepared
    if len(prepared_servers) == len(locations):
        return self._commit_append(chunk_id, prepared_servers)
    else:
        self._rollback_append(chunk_id, prepared_servers)
        return False
```

### Server Communication

1. **Master Server Connection**
```python
def _connect_to_master(self) -> socket.socket:
    """Connect to the master server."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((self.master_host, self.master_port))
    return s
```

2. **Chunk Server Interaction**
```python
def _store_chunk_with_fallback(self, chunk: Chunk, available_servers: List[str]) -> Optional[str]:
    """Try to store chunk on available servers."""
    for server in available_servers:
        try:
            with self._connect_to_chunk_server(server) as chunk_sock:
                send_message(chunk_sock, {
                    'command': 'store_chunk',
                    'data': chunk.data,
                    'file_path': chunk.file_path,
                    'chunk_id': chunk.chunk_id,
                    'client_id': self.client_id
                })
                response = receive_message(chunk_sock)
                if response['status'] == 'ok':
                    return server
        except Exception:
            continue
    return None
```

## Location Awareness

1. **Server Selection**
```python
def _get_available_chunk_servers(self) -> List[str]:
    """Get list of available chunk servers from master."""
    with self._connect_to_master() as master_sock:
        send_message(master_sock, {
            'command': 'get_chunk_servers',
            'client_id': self.client_id  # Used for location-based selection
        })
        response = receive_message(master_sock)
        return response.get('servers', [])
```

2. **Location Updates**
```python
def _send_heartbeat(self):
    """Send periodic heartbeats with location info."""
    while True:
        with self._connect_to_master() as master_sock:
            send_message(master_sock, {
                'command': 'client_heartbeat',
                'client_id': self.client_id,
                'location': self.location
            })
        time.sleep(30)
```

## Error Handling

1. **Operation Retries**
```python
def _retry_operation(self, operation, max_retries=3):
    """Retry an operation with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return operation()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
```

2. **Space Management**
```python
def _handle_insufficient_space(self, chunk: Chunk, servers: List[str]):
    """Handle insufficient space errors."""
    for server in servers:
        try:
            # Try next server
            success = self._store_chunk(chunk, server)
            if success:
                return server
        except Exception:
            continue
    raise Exception("No servers with sufficient space")
```

## Configuration

```toml
[client]
upload_chunk_size = 64000000  # 64MB
heartbeat_interval = 30
retry_attempts = 3
```

## Usage Examples

1. **File Operations**
```python
# Create client with location
client = GFSClient("config.toml", "client1", x=10, y=20)

# Upload file
client.upload_file("local_file.txt", "/gfs/remote_file.txt")

# Download file
client.download_file("/gfs/remote_file.txt", "downloaded_file.txt")

# Append to file
with open("append_data.txt", "rb") as f:
    client.append_to_file("/gfs/remote_file.txt", f.read())
```

## Best Practices

1. **Operation Management**
   - Implement retries
   - Handle timeouts
   - Verify operations

2. **Resource Management**
   - Close connections
   - Clean up temporary files
   - Handle errors gracefully

3. **Performance**
   - Use appropriate chunk sizes
   - Implement parallel operations
   - Monitor network conditions

## Related Components
- [Master Server](master)
- [Chunk Server](chunk-server)
- [File Manager](file-manager)