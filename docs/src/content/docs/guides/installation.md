---
title: Installation
description: How to install and set up GFS
sidebar:
  order: 2
---

# Installation Guide

## Prerequisites

1. **Python Environment**
   - Python 3.8 or higher
   - pip package manager
   - Virtual environment (recommended)

2. **System Requirements**
   - Linux/Unix-based system (recommended)
   - Network connectivity between nodes
   - Sufficient storage space for chunks

## Setup Steps

1. **Clone the Repository**
```bash
git clone https://github.com/sambuaneesh/custom-gfs-implementation.git
cd custom-gfs-implementation
```

2. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Create Required Directories**
```bash
mkdir -p data/chunks data/metadata logs
```

## Configuration

1. **Basic Configuration**
Edit `configs/config.toml`:
```toml
[master]
host = "localhost"
port = 5000
chunk_size = 64000000  # 64MB chunks
replication_factor = 3
distance_weight = 0.6
space_weight = 0.4

[chunk_server]
base_port = 5001
data_dir = "data/chunks"
heartbeat_interval = 5  # seconds
server_info_file = "data/chunks/server_info.json"
space_limit_mb = 1024  # Space limit per chunk server in MB

[client]
upload_chunk_size = 64000000
```

2. **Directory Structure**
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

## Common Installation Issues

1. **Port Conflicts**
   - Ensure default ports (5000, etc.) are available
   - Modify config.toml if needed
   - Check for other running services

2. **Permission Issues**
   - Ensure write permissions for data/ and logs/ directories
   - Check file ownership
   - Verify directory permissions

3. **Network Configuration**
   - Verify network connectivity between nodes
   - Check firewall settings
   - Ensure correct hostname resolution

## Next Steps

After installation:
1. Follow the [Quick Start Guide](quickstart) to run your first GFS cluster
2. Configure your system based on requirements
3. Start implementing your distributed storage solution

## Additional Resources
- [Core Components](../components/master)
- [Feature Documentation](../features/location-replication)
- [GitHub Repository](https://github.com/sambuaneesh/custom-gfs-implementation)