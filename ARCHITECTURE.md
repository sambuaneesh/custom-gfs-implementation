# GFS Implementation Architecture

## Component Overview

### Core Components
W
1. **Master Server (`src/master.py`)**
   - Manages metadata for all files
   - Coordinates chunk servers
   - Handles client requests
   - Maintains chunk server health
   - Key classes:
     - `MasterServer`: Main server implementation
     - Key methods: `handle_client`, `_check_heartbeats`

2. **Chunk Server (`src/chunk_server.py`)**
   - Stores and serves chunks
   - Handles replication
   - Sends heartbeats to master
   - Key classes:
     - `ChunkServer`: Chunk server implementation
     - Key methods: `_replicate_chunk`, `_handle_store_chunk`

3. **Client (`src/client.py`)**
   - Interfaces with master and chunk servers
   - Handles file operations
   - Key classes:
     - `GFSClient`: Client implementation
     - Key methods: `upload_file`, `download_file`

### Supporting Components

4. **File Manager (`src/file_manager.py`)**
   - Manages file metadata
   - Handles metadata persistence
   - Key classes:
     - `FileMetadata`: Data structure for file metadata
     - `FileManager`: Metadata management implementation

5. **Chunk Management (`src/chunk.py`)**
   - Defines chunk structure
   - Handles chunk operations
   - Key classes:
     - `ChunkMetadata`: Data structure for chunk metadata
     - `Chunk`: Chunk operations implementation

6. **Utilities (`src/utils.py`)**
   - Common utility functions
   - Network communication helpers
   - Key functions:
     - `send_message`: Socket communication
     - `receive_message`: Message handling
     - `get_chunk_hash`: Chunk identification

7. **Logger (`src/logger.py`)**
   - Centralized logging system
   - Configurable log levels
   - Key classes:
     - `GFSLogger`: Logger implementation

### Interface Components

8. **Web Interface (`interfaces/streamlit_app.py`)**
   - User interface implementation
   - File operation controls
   - Status display
   - Key features:
     - File upload/download
     - File listing
     - Error reporting

### Configuration

9. **Config Management (`configs/config.toml`)**
   - System configuration
   - Server settings
   - Chunk parameters
   - Key sections:
     - Master configuration
     - Chunk server settings
     - Client parameters

## Data Flow

1. **File Upload**
   ```
   Client -> Master (metadata) -> Client -> Chunk Server -> Replication Chain
   ```

2. **File Download**
   ```
   Client -> Master (locations) -> Client -> Chunk Server -> Client
   ```

3. **Chunk Server Management**
   ```
   Chunk Server -> Master (heartbeat) -> Master (health check)
   ```

## Communication Protocols

1. **Master-Client Protocol**
   - Metadata requests
   - Chunk location queries
   - File operations

2. **Master-Chunk Protocol**
   - Registration
   - Heartbeats
   - Chunk management

3. **Client-Chunk Protocol**
   - Chunk transfer
   - Data operations

## File Organization

```
gfs/
├── src/                 # Core implementation
├── interfaces/          # User interfaces
├── configs/            # Configuration files
├── data/               # Runtime data
│   ├── chunks/         # Chunk storage
│   └── metadata/       # Metadata storage
├── logs/               # Log files
└── tests/              # Test suite
``` 