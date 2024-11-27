---
title: Chunk
description: Data chunk handling and management
sidebar:
  order: 5
---

The Chunk component represents the fundamental unit of data storage in the GFS system. It handles data segmentation, storage, and retrieval operations.

## Core Implementation

### Chunk Structure
```python
class Chunk:
    def __init__(self, data: bytes, file_path: str, chunk_index: int):
        self.data = data
        self.file_path = file_path
        self.chunk_index = chunk_index
        self.chunk_id = self._generate_chunk_id()
```

Key attributes:
- `data`: Raw byte content
- `file_path`: Original file path
- `chunk_index`: Position in file
- `chunk_id`: Unique identifier

### Chunk Identification

1. **ID Generation**
```python
def _generate_chunk_id(self) -> str:
    """Generate a unique chunk ID using SHA-256."""
    content = f"{self.file_path}_{self.chunk_index}_{time.time()}"
    return hashlib.sha256(content.encode()).hexdigest()
```
Features:
- Unique identification
- Collision resistance
- Path and index incorporation

### Storage Operations

1. **Saving Chunks**
```python
def save_to_disk(self, directory: str) -> None:
    """Save chunk data to disk."""
    chunk_path = os.path.join(directory, self.chunk_id)
    with open(chunk_path, 'wb') as f:
        f.write(self.data)
```

2. **Loading Chunks**
```python
@staticmethod
def load_from_disk(directory: str, chunk_id: str) -> bytes:
    """Load chunk data from disk."""
    chunk_path = os.path.join(directory, chunk_id)
    with open(chunk_path, 'rb') as f:
        return f.read()
```

### Data Management

1. **Size Calculation**
```python
def get_size(self) -> int:
    """Get chunk size in bytes."""
    return len(self.data)
```

2. **Data Verification**
```python
def verify_data(self) -> bool:
    """Verify chunk data integrity."""
    return len(self.data) > 0
```

## Usage Examples

1. **Creating Chunks**
```python
# Create a new chunk
data = b"Some binary data"
chunk = Chunk(data, "/path/to/file.txt", 0)
```

2. **Storage Operations**
```python
# Save chunk
chunk.save_to_disk("/path/to/chunks")

# Load chunk
data = Chunk.load_from_disk("/path/to/chunks", chunk_id)
```

## Best Practices

1. **Data Handling**
   - Verify data integrity
   - Handle binary data properly
   - Implement size checks

2. **Storage Management**
   - Clean up temporary files
   - Verify disk operations
   - Handle I/O errors

3. **ID Management**
   - Ensure unique IDs
   - Verify ID validity
   - Handle collisions

## Error Handling

1. **Storage Errors**
```python
try:
    chunk.save_to_disk(directory)
except IOError as e:
    logger.error(f"Failed to save chunk: {e}")
```

2. **Loading Errors**
```python
try:
    data = Chunk.load_from_disk(directory, chunk_id)
except FileNotFoundError:
    logger.error(f"Chunk {chunk_id} not found")
```

## Related Components
- [Chunk Server](chunk-server)
- [File Manager](file-manager)