---
title: File Manager
description: File and metadata management component
sidebar:
  order: 4
---

The File Manager is responsible for managing file metadata, chunk mappings, and replication status in the GFS system. It provides a persistent layer for file system metadata and handles file operations coordination.

## Core Components

### File Metadata Structure

```python
@dataclass
class FileMetadata:
    file_path: str
    total_size: int
    chunk_ids: List[str]
    chunk_locations: Dict[str, List[str]]  # chunk_id -> list of chunk server addresses
    chunk_offsets: Dict[str, int]  # chunk_id -> offset within chunk
    last_chunk_id: str  # ID of the last chunk for appends
    last_chunk_offset: int  # Current offset in the last chunk
    pending_replication: Dict[str, int] = None  # chunk_id -> required additional replicas
```

Key attributes:
- File path and size tracking
- Chunk mapping and locations
- Offset management for appends
- Replication status tracking

### File Manager Implementation

```python
class FileManager:
    def __init__(self, metadata_dir: str, config: Dict):
        self.metadata_dir = metadata_dir
        self.metadata_lock = threading.Lock()
        self.files: Dict[str, FileMetadata] = {}
```

## Core Functionality

### Metadata Persistence

1. **Loading Metadata**
```python
def _load_metadata(self):
    """Load metadata from disk."""
    metadata_file = os.path.join(self.metadata_dir, 'metadata.json')
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as f:
            data = json.load(f)
            self.files = {
                path: FileMetadata(**metadata)
                for path, metadata in data.items()
            }
```

2. **Saving Metadata**
```python
def _save_metadata(self):
    """Save metadata to disk."""
    metadata_file = os.path.join(self.metadata_dir, 'metadata.json')
    with open(metadata_file, 'w') as f:
        json.dump({
            path: asdict(metadata)
            for path, metadata in self.files.items()
        }, f, indent=2)
```

### File Operations

1. **Adding Files**
```python
def add_file(self, file_path: str, total_size: int, chunk_ids: List[str]):
    """Add a new file to the metadata."""
    with self.metadata_lock:
        self.files[file_path] = FileMetadata(
            file_path=file_path,
            total_size=total_size,
            chunk_ids=chunk_ids,
            chunk_locations={},
            chunk_offsets={chunk_id: 0 for chunk_id in chunk_ids},
            last_chunk_id=chunk_ids[-1] if chunk_ids else None,
            last_chunk_offset=total_size % self.config['master']['chunk_size']
        )
```

2. **Updating Metadata**
```python
def update_file_metadata(self, file_path: str, chunk_id: str, 
                        locations: List[str], size: int):
    """Update file metadata with new chunk information."""
    with self.metadata_lock:
        if file_path not in self.files:
            self.add_file(file_path, size, [chunk_id])
        else:
            metadata = self.files[file_path]
            if chunk_id not in metadata.chunk_ids:
                metadata.chunk_ids.append(chunk_id)
            metadata.chunk_locations[chunk_id] = locations
            metadata.total_size += size
```

### Chunk Management

1. **Location Tracking**
```python
def update_chunk_locations(self, file_path: str, chunk_id: str, 
                         locations: List[str]):
    """Update the locations of a chunk."""
    with self.metadata_lock:
        if file_path in self.files:
            self.files[file_path].chunk_locations[chunk_id] = locations
```

2. **Offset Management**
```python
def update_chunk_offset(self, file_path: str, chunk_id: str, offset: int):
    """Update the offset of a chunk."""
    with self.metadata_lock:
        if file_path in self.files:
            metadata = self.files[file_path]
            metadata.chunk_offsets[chunk_id] = offset
            if chunk_id == metadata.last_chunk_id:
                metadata.last_chunk_offset = offset
```

## Replication Management

1. **Pending Replications**
```python
def get_pending_replications(self, file_path: str) -> Dict[str, int]:
    """Get chunks that need additional replicas."""
    metadata = self.get_file_metadata(file_path)
    if metadata and metadata.pending_replication:
        return metadata.pending_replication
    return {}
```

2. **Replication Status**
```python
def update_replication_status(self, file_path: str, chunk_id: str, 
                            needed_replicas: int):
    """Update the replication status of a chunk."""
    with self.metadata_lock:
        metadata = self.files.get(file_path)
        if metadata:
            metadata.pending_replication[chunk_id] = needed_replicas
```

## Error Handling

1. **Metadata Operations**
```python
try:
    self._save_metadata()
except IOError as e:
    self.logger.error(f"Failed to save metadata: {e}")
```

2. **File Operations**
```python
if file_path not in self.files:
    self.logger.warning(f"Attempted to update non-existent file: {file_path}")
```

## Best Practices

1. **Metadata Management**
   - Regular backups
   - Atomic updates
   - Lock-based synchronization

2. **Performance Optimization**
   - In-memory caching
   - Batch updates
   - Periodic persistence

3. **Data Integrity**
   - Validate metadata
   - Check file consistency
   - Handle corruption

## Related Components
- [Master Server](master)
- [Chunk](chunk)