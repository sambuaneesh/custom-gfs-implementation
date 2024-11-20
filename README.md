# Google File System (GFS) Implementation

A simplified implementation of the Google File System in Python, featuring a master server, multiple chunk servers, and a web interface for file operations.

## System Architecture

- **Master Server**: Manages metadata and coordinates chunk servers
- **Chunk Servers**: Store and serve file chunks with replication
- **Client Interface**: Web-based interface using Streamlit
- **Configuration**: TOML-based configuration system
- **Logging**: Comprehensive logging system for all components

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

### File Operations

- Large file handling with chunking
- Configurable chunk size
- Configurable replication factor
- Automatic chunk distribution
- Fault tolerance

### Logging

- Comprehensive logging for all components
- Separate log files for each component
- Debug and info level logging
- Console and file logging

### Data Persistence

- Metadata persistence in JSON format
- Chunk data persistence on disk
- Server configuration persistence
- Automatic recovery after restarts

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
- **Single Master**: No master replication or failover (Real GFS has shadow masters)
- **Simplified Chunk Management**: Basic chunk allocation without load balancing
- **Limited Metadata Operations**: No namespace management or snapshot support
- **No Lease Management**: Real GFS uses chunk leases for consistency

### Missing Features
1. **Consistency Model**
   - No atomic record append operations
   - No snapshot functionality
   - Limited consistency guarantees

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
