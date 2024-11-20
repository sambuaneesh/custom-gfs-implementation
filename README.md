# Google File System (GFS) Implementation

A simplified implementation of the Google File System in Python, featuring a master server, multiple chunk servers, and a web interface for file operations.

## System Architecture

- **Master Server**: Manages metadata and coordinates chunk servers
- **Chunk Servers**: Store and serve file chunks with replication
- **Client Interface**: Web-based interface using Streamlit
- **Configuration**: TOML-based configuration system
- **Logging**: Comprehensive logging system with transaction tracking

## Directory Structure

```
gfs/
├── src/
│   ├── __init__.py
│   ├── master.py
│   ├── chunk_server.py
│   ├── client.py
│   ├── file_manager.py
│   ├── chunk.py
│   ├── utils.py
│   └── logger.py
├── interfaces/
│   └── streamlit_app.py
├── configs/
│   └── config.toml
├── data/
│   ├── chunks/
│   └── metadata/
├── logs/
└── requirements.txt
```

## Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create necessary directories:
   ```bash
   mkdir -p data/chunks data/metadata logs
   ```

## Configuration

The system is configured through `configs/config.toml`:

```toml
[master]
host = "localhost"
port = 5000
chunk_size = 64000000  # 64MB chunks
replication_factor = 3

[chunk_server]
base_port = 5001
data_dir = "data/chunks"
heartbeat_interval = 5  # seconds
server_info_file = "data/chunks/server_info.json"
space_limit_mb = 1024  # Space limit per chunk server in MB

[client]
upload_chunk_size = 64000000
```

## Running the System

### 1. Start the Master Server

```bash
python run_master.py
```

The master server will:
- Start on the configured port (default: 5000)
- Manage chunk server registrations
- Handle client requests
- Monitor chunk server health through heartbeats

### 2. Start Chunk Servers

You can start chunk servers in multiple ways:

1. With a specific ID:
   ```bash
   python run_chunk_server.py --id chunk1
   ```

2. With a custom config:
   ```bash
   python run_chunk_server.py --id chunk1 --config custom_config.toml
   ```

3. Without an ID (will generate timestamp-based ID):
   ```bash
   python run_chunk_server.py
   ```

Each chunk server will:
- Auto-assign a port if not previously configured
- Create its own data directory
- Register with the master server
- Send regular heartbeats
- Persist its configuration for restarts

### 3. Start the Web Interface

```bash
streamlit run interfaces/streamlit_app.py
```

The web interface provides:
- File upload functionality
- File download capability
- File listing
- Error reporting and status messages

## Features

### Chunk Server Management

- Persistent chunk server IDs
- Automatic port assignment
- Heartbeat monitoring
- Server information persistence
- Hot-plug capability (add/remove servers)
- Two-phase commit protocol for data consistency

### File Operations

- Large file handling with chunking
- Configurable chunk size
- Configurable replication factor
- Automatic chunk distribution
- Record append operations
- Fault tolerance

### Transaction Management

- Two-phase commit protocol implementation
- Transaction logging with phases:
  - START: Initial transaction setup
  - PREPARE: Preparation phase
  - COMMIT: Commit phase
  - ROLLBACK: Rollback phase
  - REPLICATE: Replication phase
- Colored console output for different transaction phases
- Detailed transaction history in log files

### Logging System

- Comprehensive logging for all components
- Transaction-specific logging
- Color-coded console output:
  - White: Transaction start
  - Magenta: Prepare phase
  - Blue: Commit phase
  - Red: Rollback/Error messages
  - Yellow: Replication operations
- Separate log files for each component
- Transaction logs in dedicated directory

### Data Consistency

- Two-phase commit protocol ensures:
  - All chunk servers prepare successfully before commit
  - Atomic commits across all replicas
  - Proper rollback on failures
  - Transaction logging for recovery
- Primary-based replication chain
- Sequential consistency for writes

### Monitoring

- Real-time transaction status in console
- Detailed transaction logs
- Component-specific log files
- Server health monitoring through heartbeats

### Background Replication System

The system implements a robust background replication mechanism that ensures data reliability even when there aren't enough chunk servers available initially:

#### Features
- **Dynamic Replication Queue**: Tracks chunks that haven't met their replication factor
- **Space-Aware Replication**: Respects chunk server space limits during replication
- **Automatic Recovery**: Automatically replicates data when new servers become available
- **Persistent Tracking**: Maintains pending replication status across system restarts

#### How it Works

1. **Initial Storage**
   - When a chunk is stored, the system attempts immediate replication
   - If insufficient servers are available, the chunk is added to a replication queue

2. **Background Processing**
   - A dedicated background thread monitors the replication queue
   - Periodically checks for new available servers
   - Attempts to meet replication factor when resources become available

3. **New Server Integration**
   - When new chunk servers join:
     - They register with the master server
     - The background replication system detects them
     - Pending replications are automatically attempted
     - Replication status is updated upon success

4. **Space Management**
   - Checks available space before replication attempts
   - Skips servers with insufficient space
   - Maintains space limits specified during chunk server initialization

#### Configuration

The replication system uses these settings in `config.toml`:

```toml
[master]
replication_factor = 3  # Desired number of replicas per chunk

[chunk_server]
space_limit_mb = 1024  # Space limit per chunk server in MB
```

#### Monitoring

The replication status can be monitored through:
- Log files showing replication attempts and status
- Transaction logs tracking replication progress
- Metadata showing current replica count per chunk
- Replication queue status in master server logs

## Monitoring

### Log Files

Log files are created in the `logs/` directory:
- `master_YYYY-MM-DD.log`
- `chunk_server_YYYY-MM-DD.log`
- `client_YYYY-MM-DD.log`

### Server Information

Chunk server information is stored in:
`data/chunks/server_info.json`

### Metadata

File metadata is stored in:
`data/metadata/metadata.json`

## Customization

### Adding New Chunk Servers

1. Start a new chunk server with a unique ID:

   ```bash
   python run_chunk_server.py --id custom_name
   ```

2. The server will automatically:
   - Find a free port
   - Create its data directory
   - Register with the master
   - Begin accepting chunks

### Custom Configuration

Create a custom config file based on `config.toml`:
```bash
python run_chunk_server.py --id chunk1 --config custom_config.toml
```

## Troubleshooting

1. **No chunk servers available**
   - Ensure at least one chunk server is running
   - Check chunk server logs for registration issues

2. **Master server connection failed**
   - Verify master server is running
   - Check configured master port

3. **Upload/Download failures**
   - Check available chunk servers
   - Verify file permissions in data directories
   - Check component logs for specific errors

## Development

- Use the logging system for debugging
- Check component logs in the `logs/` directory
- Monitor `server_info.json` for chunk server status
- Review `metadata.json` for file tracking

## Limitations and Missing Features Compared to Real GFS

### Architecture Differences
- **Single-Phase Commit**: Current implementation uses single-phase commit protocol instead of the two-phase commit used in real GFS
- **Single Master**: No master replication or failover (Real GFS has shadow masters)
- **Simplified Chunk Management**: Basic chunk allocation without load balancing
- **Limited Metadata Operations**: No namespace management or snapshot support
- **No Lease Management**: Real GFS uses chunk leases for consistency

### Commit Protocol Differences
1. **Current Implementation (Single-Phase)**
   - Primary chunk server receives data
   - Primary directly writes and forwards to replicas
   - No explicit preparation phase
   - No verification of replica readiness
   - Faster but less reliable

2. **Real GFS (Two-Phase)**
   - Phase 1 (Preparation):
     - Primary sends data to all replicas
     - Replicas acknowledge receipt
     - Replicas prepare but don't commit
   - Phase 2 (Commit):
     - Primary verifies all replicas are ready
     - Primary sends commit command
     - Replicas commit changes
     - Replicas acknowledge commit
   - More reliable but slower

### Missing Features
1. **Consistency Model**
   - Limited consistency guarantees
   - No proper two-phase commit protocol
   - No atomic record append operations across chunks
   - No snapshot functionality

2. **Performance Optimizations**
   - No flow control
   - No intelligent chunk placement
   - No data flow optimization
   - No checksum for data integrity

3. **Security**
   - No authentication/authorization
   - No encryption (in-transit or at-rest)
   - No access control lists

4. **Recovery Mechanisms**
   - Limited chunk re-replication
   - No master state recovery
   - No automatic chunk server recovery

5. **Advanced Operations**
   - No atomic operations
   - No record append functionality
   - No snapshot support
   - No garbage collection

6. **Monitoring and Maintenance**
   - No monitoring interface
   - No diagnostic tools
   - Limited system statistics

## Future Enhancements
1. **High Availability**
   - Implement shadow masters
   - Add master state replication
   - Implement chunk server failover

2. **Data Consistency**
   - Add lease management
   - Implement atomic operations
   - Add snapshot support

3. **Security**
   - Add authentication system
   - Implement encryption
   - Add access control

4. **Performance**
   - Implement intelligent chunk placement
   - Add flow control
   - Optimize data flow

5. **Monitoring**
   - Add monitoring interface
   - Implement diagnostic tools
   - Add system statistics

6. **Consistency Improvements**
   - Implement two-phase commit protocol
   - Add proper lease management
   - Implement atomic operations
   - Add snapshot support

## Implementation Details

### Two-Phase Commit Protocol
1. **Phase 1 (Prepare)**
   - Primary receives store/append request
   - Primary prepares temporary storage
   - Primary coordinates with replicas
   - All replicas prepare temporary storage
   - Success only if all servers prepare successfully

2. **Phase 2 (Commit/Rollback)**
   - If all prepared: Commit changes on all servers
   - If any failed: Rollback all prepared servers
   - Update master metadata on successful commit
   - Clean up temporary files on rollback

### Transaction Logging
1. **Console Output**
   - Color-coded transaction phases
   - Real-time status updates
   - Success/failure indicators
   - Detailed error messages

2. **File Logging**
   - Transaction logs in `logs/transactions/`
   - Component logs in `logs/`
   - Detailed timing information
   - Complete transaction history

### Chunk Management
1. **Primary Operations**
   - Receives client requests
   - Coordinates two-phase commit
   - Manages replication chain
   - Updates master metadata

2. **Replica Operations**
   - Participates in two-phase commit
   - Maintains temporary storage
   - Handles rollbacks
   - Reports status to primary
