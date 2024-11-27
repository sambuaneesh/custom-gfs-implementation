---
title: Quick Start
description: Get started with GFS quickly
sidebar:
  order: 3
---

# Quick Start Guide

## Starting the System

1. **Start Master Server**
```bash
make master
```

2. **Start Chunk Servers**
```bash
# Start chunk servers with different locations and space limits
make chunk chunk1 0 0 1024    # Origin with 1GB
make chunk chunk2 100 0 2048  # East with 2GB
make chunk chunk3 0 100 1024  # North with 1GB
```

3. **Start Client Interface**
```bash
# Start client at specific location
make client client1 50 50  # Center location
```

## Basic Operations

### File Operations

1. **Upload a File**
```python
client = GFSClient("configs/config.toml", "client1", x=10, y=20)
client.upload_file("local_file.txt", "/gfs/remote_file.txt")
```

2. **Download a File**
```python
client.download_file("/gfs/remote_file.txt", "downloaded_file.txt")
```

3. **Append to File**
```python
with open("data.txt", "rb") as f:
    client.append_to_file("/gfs/remote_file.txt", f.read())
```

### Using the Web Interface

1. **Access File Explorer**
   - Navigate to "File Explorer" tab
   - Browse directory structure
   - Upload/download files
   - Create directories

2. **Monitor System**
   - Check "Network Graph" tab
   - View chunk server status
   - Monitor space usage
   - Track client connections

## Location-Aware Features

1. **Server Placement**
```bash
# Strategic server placement
make chunk cs1 0 0 1024     # Center
make chunk cs2 100 100 1024 # Northeast
make chunk cs3 100 0 1024   # East
```

2. **Client Positioning**
```bash
# Position clients near their data
make client client1 25 25   # Near center
make client client2 75 75   # Northeast quadrant
```

## Space Management

1. **Configure Space Limits**
```bash
# Varying space capacities
make chunk chunk1 10 20 2048  # 2GB space
make chunk chunk2 30 40 1024  # 1GB space
```

2. **Monitor Usage**
   - Check space usage in web interface
   - Monitor replication status
   - View space distribution

## System Monitoring

1. **Monitor Logs**
```bash
# Check component logs
tail -f logs/master_*.log
tail -f logs/chunk_server_*.log
```

## Common Operations

### File Management
1. Create directory structure
2. Upload files
3. Download files
4. Append to existing files

### System Administration
1. Monitor server health
2. Check replication status
3. Verify space usage
4. Track client connections

## Best Practices

1. **Server Deployment**
   - Distribute servers geographically
   - Balance space allocation
   - Monitor server health

2. **Client Usage**
   - Position clients strategically
   - Monitor connection quality
   - Track operation success

3. **Data Management**
   - Regular backups
   - Space monitoring
   - Replication verification

## Troubleshooting

1. **Connection Issues**
   - Verify master server is running
   - Check chunk server status
   - Confirm network connectivity

2. **Space Issues**
   - Monitor available space
   - Check replication status
   - Verify chunk distribution

3. **Performance Issues**
   - Check server load
   - Monitor network traffic
   - Verify client positioning

## Next Steps

1. Explore [Advanced Features](../features/location-replication)
2. Learn about [System Components](../components/master)
3. Configure for production use

## Related Resources
- [Master Server Documentation](../components/master)
- [Chunk Server Documentation](../components/chunk-server)
- [Client Documentation](../components/client)