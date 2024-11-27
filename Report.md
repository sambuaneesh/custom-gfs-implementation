# GFS - Replicas by Geography

## Overview

This project implements a modified version of the Google File System (GFS) with a focus on geography-aware replica placement. The system introduces a novel approach to chunk server selection and replica placement based on geographical coordinates and server space availability.

### Key Features
1. Location-aware chunk server selection
2. Dynamic priority-based replication
3. Space-aware distribution
4. Real-time visualization and monitoring
5. Hierarchical file system interface

## Design

### System Architecture

The system follows a master-slave architecture with three main components:

1. **Master Server**
   - Coordinates all system operations
   - Maintains metadata and chunk server locations
   - Implements priority-based server selection
   - Manages space allocation and replication

2. **Chunk Servers**
   - Store and serve file chunks
   - Report location and space metrics
   - Handle replication requests
   - Manage local storage

3. **Client Interface**
   - Web-based user interface
   - File system operations
   - Real-time system visualization
   - Location-aware chunk server selection

### Priority System Design

The system implements a weighted priority algorithm that considers:

1. **Geographical Distance (60% weight)**
   ```python
   normalized_distance = actual_distance / MAX_DISTANCE
   distance_score = DISTANCE_WEIGHT * normalized_distance
   ```

2. **Space Availability (40% weight)**
   ```python
   space_score = SPACE_WEIGHT * (1 - available_space/total_space)
   final_score = distance_score + space_score
   ```

### Data Flow
1. Client initiates file operation
2. Master calculates server priorities
3. Chunk servers are selected based on:
   - Geographic proximity
   - Available space
   - Current load
4. Replication follows priority order

## Implementation

### Key Components

1. **Location Graph Management**
```python
class LocationGraph:
    def __init__(self):
        self.nodes = {}  # id -> (x, y) coordinates
        self.distances = defaultdict(dict)
        self.node_type = {}
        self.space_info = {}
```

2. **Priority System**
```python
class ClientServerPriority:
    def __init__(self):
        self.DISTANCE_WEIGHT = 0.6
        self.SPACE_WEIGHT = 0.4
        self.client_priorities = {}
```

3. **Dynamic Replication**
```python
def _handle_replication(self):
    # Calculate priorities
    # Select target servers
    # Manage replication queue
    # Handle space constraints
```

### File System Interface

1. **Directory Structure**
   - Hierarchical navigation
   - Dynamic path management
   - File operations
   - Preview capabilities

2. **Visualization**
   - Network topology
   - Server status
   - Space utilization
   - Priority visualization

## Extended Features

### Eventual Replication System
1. **Background Replication Queue**
   ```python
   class MasterServer:
       def __init__(self):
           self.replication_queue = set()  # (file_path, chunk_id)
           self.replication_queue_lock = threading.Lock()
   ```

2. **New Server Integration**
   - When new chunk server joins:
     ```python
     def _handle_register_chunk_server(self, message):
         address = message['address']
         location = message['location']
         self.chunk_servers[address] = time.time()
         # Trigger replication check
         self._check_pending_replications()
     ```
   - System checks pending replications
   - Attempts replication on new server if space available

### System Resilience
1. **Master Server Recovery**
   - Metadata persistence in `data/metadata/`
   - Chunk servers maintain state
   - Automatic reconnection mechanism
   - Transaction logging for recovery

2. **Chunk Server Dynamics**
   - Dynamic join/leave handling
   - Heartbeat-based health monitoring
   - Automatic dead server removal
   ```python
   def _check_heartbeats(self):
       dead_servers = [
           addr for addr, last_beat in self.chunk_servers.items()
           if current_time - last_beat > TIMEOUT
       ]
       for addr in dead_servers:
           self.remove_server(addr)
   ```

### Configurable Parameters
```toml
[master]
replication_factor = 3  # Adjustable replication
chunk_size = 64000000  # Configurable chunk size
heartbeat_interval = 5

[chunk_server]
space_limit_mb = 1024
```

## Core GFS Features

### Append Operations
1. **Space Management**
   ```python
   def append_to_file(self, file_path: str, data: bytes):
       if current_chunk.remaining_space < len(data):
           # Create new chunk
           new_chunk = self.create_chunk()
           self.write_data(new_chunk, data)
       else:
           # Append to current chunk
           self.append_to_chunk(current_chunk, data)
   ```

2. **Chunk Overflow Handling**
   - Automatic new chunk creation
   - Space verification before append
   - Transaction rollback on failure

### Two-Phase Commit Protocol
1. **Phase 1: Preparation**
   ```python
   def prepare_append(self, chunk_id, data):
       # All replicas prepare
       for replica in replicas:
           status = replica.prepare(chunk_id, data)
           if not status.ok():
               return self.abort_transaction()
   ```

2. **Phase 2: Commit**
   ```python
   def commit_append(self, transaction_id):
       # All replicas commit
       for replica in prepared_replicas:
           status = replica.commit(transaction_id)
   ```

3. **Rollback Mechanism**
   - Temporary file creation
   - Atomic commits
   - Error recovery

### Background Replication
1. **Queue Management**
   ```python
   class ReplicationManager:
       def process_queue(self):
           for chunk_id in replication_queue:
               if self.needs_replication(chunk_id):
                   self.replicate_chunk(chunk_id)
   ```

2. **Priority-Based Replication**
   - Space availability check
   - Geographic distribution
   - Server load consideration

### Simplified Leader Mechanism
1. **Primary Selection**
   ```python
   def select_primary(self, chunk_id):
       servers = self.get_chunk_servers(chunk_id)
       return self.select_by_priority(servers)
   ```

2. **Differences from GFS**
   - No lease management
   - Simplified primary selection
   - Direct primary-replica communication

## Communication Architecture

### Coordinate System Implementation
1. **Input Handling**
   ```python
   def start_chunk_server(server_id, x, y, space):
       server = ChunkServer(
           server_id=server_id,
           location=(x, y),
           space_limit=space
       )
   ```

2. **Location Graph**
   ```python
   class LocationGraph:
       def add_node(self, node_id, location, node_type):
           self.nodes[node_id] = location
           self._update_distances(node_id)
   ```

### Priority Tracking System
1. **Master Server**
   ```python
   class ClientServerPriority:
       def update_priorities(self, client_id, location, servers):
           distances = []
           for server_id, (x, y, space) in servers.items():
               distance = self.calculate_distance(location, (x, y))
               score = self.calculate_score(distance, space)
               distances.append((server_id, score))
           return sorted(distances, key=lambda x: x[1])
   ```

2. **Client Integration**
   - Location passed through environment variables
   - Priority updates on heartbeat
   - Dynamic score recalculation

### Message Passing Mechanisms

1. **Socket Communication**
   ```python
   def send_message(sock, message):
       data = json.dumps(message).encode()
       length = len(data)
       sock.sendall(struct.pack('!I', length))
       sock.sendall(data)
   ```

2. **Command Types**
   - Registration: `register_chunk_server`, `register_client`
   - Operations: `store_chunk`, `retrieve_chunk`
   - Metadata: `update_file_metadata`, `get_chunk_locations`
   - Monitoring: `heartbeat`, `get_graph_data`

3. **Heartbeat System**
   ```python
   def _send_heartbeat(self):
       while True:
           send_message(master_sock, {
               'command': 'heartbeat',
               'address': self.address,
               'location': self.location,
               'space_info': self.get_space_info()
           })
           time.sleep(HEARTBEAT_INTERVAL)
   ```

## Algorithm

### Server Selection Algorithm

1. **Priority Calculation**
```python
def calculate_server_score(distance, space_available, total_space):
    normalized_distance = distance / MAX_DISTANCE
    space_score = 1 - (space_available / total_space)
    return (DISTANCE_WEIGHT * normalized_distance + 
            SPACE_WEIGHT * space_score)
```

2. **Replication Strategy**
   - Initial placement based on client location
   - Secondary replicas based on:
     - Geographic distribution
     - Space availability
     - Network topology

### Space Management

1. **Space Monitoring**
   - Real-time space tracking
   - Threshold management
   - Dynamic reallocation

2. **Replication Queue**
   - Priority-based queue
   - Space-aware scheduling
   - Dynamic adjustment

## Performance and Scalability

### Metrics
1. **Geographic Distribution**
   - Average distance to clients
   - Replica spread
   - Server utilization

2. **Space Utilization**
   - Storage efficiency
   - Replication overhead
   - Load balancing

### Optimization Techniques
1. Priority caching
2. Dynamic threshold adjustment
3. Adaptive replication

## Future Enhancements

1. **Advanced Features**
   - Machine learning for prediction
   - Network condition awareness
   - Adaptive weight adjustment

2. **Optimizations**
   - Improved space management
   - Enhanced replication strategies
   - Better visualization tools

## Conclusion

The project successfully implements a geography-aware distributed file system with:
- Intelligent replica placement
- Space-aware distribution
- Real-time monitoring
- User-friendly interface

The system demonstrates effective balance between:
- Geographic proximity
- Space utilization
- System reliability
- User experience

This implementation provides a solid foundation for further development in distributed storage systems with location awareness.
