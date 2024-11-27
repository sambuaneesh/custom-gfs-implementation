---
title: Master Server
description: Core coordinator component of the GFS system
sidebar:
  order: 1
---


The Master Server is the central coordinator of the GFS system, managing metadata, chunk servers, and client interactions. It implements location-aware replication and space-based distribution strategies.

## Core Components

### Data Structures

#### ServerDistance
```python
@dataclass
class ServerDistance:
    server_id: str
    distance: float
    space_available: int
```
A data structure that holds:
- `server_id`: Unique identifier for a chunk server
- `distance`: Euclidean distance from a client
- `space_available`: Available storage space in bytes

### Location Graph

The `LocationGraph` class manages the spatial relationships between system components:

```python
class LocationGraph:
    def __init__(self):
        self.nodes = {}  # id -> (x, y) coordinates
        self.distances = defaultdict(dict)  # id -> {other_id -> distance}
        self.node_type = {}  # id -> "client" or "chunk_server"
        self.space_info = {}  # node_id -> {total, used, available}
```

#### Key Methods

1. **Node Management**
   ```python
   def add_node(self, node_id: str, location: tuple, node_type: str)
   def remove_node(self, node_id: str)
   ```
   - Adds/removes nodes from the graph
   - Updates distance calculations automatically
   - Maintains node type information

2. **Distance Calculation**
   ```python
   def _update_distances(self, node_id: str)
   ```
   - Calculates Euclidean distances between nodes
   - Updates bidirectional distance mappings
   - Called automatically when nodes are added

3. **Server Selection**
   ```python
   def get_nearest_chunk_servers(self, client_id: str, k: int = 3)
   ```
   - Returns k-nearest chunk servers to a client
   - Uses pre-calculated distances
   - Filters for active servers only

### Client-Server Priority System

The `ClientServerPriority` class manages server selection priorities:

```python
class ClientServerPriority:
    def __init__(self):
        self.DISTANCE_WEIGHT = 0.6  # 60% weight for distance
        self.SPACE_WEIGHT = 0.4    # 40% weight for space
```

#### Priority Calculation

1. **Score Calculation**
   ```python
   def _calculate_server_score(self, distance: float, space_available: int, total_space: int)
   ```
   Combines two factors:
   - Normalized distance (0-1 scale)
   - Space utilization (percentage available)
   - Lower score = better server choice

2. **Priority Updates**
   ```python
   def update_priorities(self, client_id: str, client_location: Tuple[float, float], 
                        servers: Dict[str, Tuple[float, float, int, int]])
   ```
   - Updates server priorities for each client
   - Considers both location and space
   - Maintains sorted priority list

## Master Server Implementation

### Initialization
```python
def __init__(self, config_path: str):
    # Initialize components
    self.file_manager = FileManager("data/metadata", self.config)
    self.chunk_servers = {}
    self.location_graph = LocationGraph()
    self.client_priorities = ClientServerPriority()
```

### Background Processes

1. **Heartbeat Checker**
   ```python
   def _check_heartbeats(self):
   ```
   - Monitors chunk server health
   - Removes dead servers
   - Updates system state
   - Runs in separate thread

2. **Replication Manager**
   ```python
   def _handle_pending_replications(self):
   ```
   - Manages replication queue
   - Ensures data redundancy
   - Handles server failures

### Command Handlers

1. **Chunk Server Registration**
   ```python
   def _handle_register_chunk_server(self, message: Dict):
   ```
   - Registers new chunk servers
   - Updates location graph
   - Initializes monitoring

2. **Client Operations**
   ```python
   def _handle_get_chunk_servers(self, client_socket: socket.socket, message: Dict):
   ```
   - Returns nearest available servers
   - Considers server priorities
   - Handles space constraints

3. **File Operations**
   ```python
   def _handle_add_file(self, client_socket: socket.socket, message: Dict):
   def _handle_get_file_metadata(self, client_socket: socket.socket, message: Dict):
   ```
   - Manages file metadata
   - Coordinates chunk placement
   - Handles replication

### Space Management

1. **Space Monitoring**
   ```python
   def _handle_heartbeat(self, message: Dict):
   ```
   - Tracks server space usage
   - Updates priorities based on space
   - Triggers replication if needed

2. **Replica Placement**
   ```python
   def _handle_get_replica_locations(self, client_socket: socket.socket, message: Dict):
   ```
   - Selects servers for replication
   - Considers space availability
   - Maintains geographic distribution

## Communication Protocol

### Message Types
1. **Registration Messages**
   - `register_chunk_server`
   - `register_client`

2. **Heartbeat Messages**
   - Regular status updates
   - Space information
   - Location confirmation

3. **Operation Messages**
   - File operations
   - Chunk management
   - Metadata updates

### Error Handling
- Socket connection failures
- Server timeouts
- Space constraints
- Replication failures

## Configuration

```toml
[master]
host = "localhost"
port = 5000
replication_factor = 3
distance_weight = 0.6
space_weight = 0.4

[chunk_server]
heartbeat_interval = 5
```

## Usage Examples

1. **Starting the Master**
```bash
python run_master.py
```

2. **Monitoring**
```python
# View active servers
print(master.chunk_servers)

# Check client priorities
print(master.client_priorities)
```

## Best Practices
1. Regular configuration backups
2. Monitoring heartbeat intervals
3. Space threshold management
4. Priority weight tuning

## Related Components
- [Chunk Server](chunk-server)
- [File Manager](file-manager)
- [Client](client)