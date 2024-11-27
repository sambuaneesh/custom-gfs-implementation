import socket
import threading
import time
import toml
from typing import Dict, List, Set, Tuple
from .file_manager import FileManager
from .utils import send_message, receive_message
from .logger import GFSLogger
import random
import math
from collections import defaultdict
import networkx as nx
import plotly.graph_objects as go
from queue import PriorityQueue
from dataclasses import dataclass

@dataclass
class ServerDistance:
    server_id: str
    distance: float
    space_available: int

class LocationGraph:
    def __init__(self):
        self.nodes = {}  # id -> (x, y) coordinates
        self.distances = defaultdict(dict)  # id -> {other_id -> distance}
        self.node_type = {}  # id -> "client" or "chunk_server"
        self.space_info = {}  # node_id -> {total: int, used: int, available: int}
        self.lock = threading.Lock()

    def add_node(self, node_id: str, location: tuple, node_type: str):
        """Add a node to the graph."""
        with self.lock:
            self.nodes[node_id] = location
            self.node_type[node_id] = node_type
            self._update_distances(node_id)

    def remove_node(self, node_id: str):
        """Remove a node from the graph."""
        with self.lock:
            if node_id in self.nodes:
                del self.nodes[node_id]
                del self.node_type[node_id]
                # Remove all distances involving this node
                del self.distances[node_id]
                for other_id in self.distances:
                    self.distances[other_id].pop(node_id, None)

    def _update_distances(self, node_id: str):
        """Update distances for a node to all other nodes."""
        x1, y1 = self.nodes[node_id]
        for other_id, (x2, y2) in self.nodes.items():
            if other_id != node_id:
                distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                self.distances[node_id][other_id] = distance
                self.distances[other_id][node_id] = distance

    def get_nearest_chunk_servers(self, client_id: str, k: int = 3) -> List[str]:
        """Get k nearest chunk servers to a client."""
        with self.lock:
            if client_id not in self.nodes:
                return []
            
            # Get all chunk servers and their distances to this client
            chunk_servers = [
                (server_id, self.distances[client_id][server_id])
                for server_id in self.nodes
                if self.node_type[server_id] == "chunk_server"
            ]
            
            # Sort by distance and return top k
            chunk_servers.sort(key=lambda x: x[1])
            return [server_id for server_id, _ in chunk_servers[:k]]

    def get_graph_data(self):
        """Get graph data for visualization."""
        with self.lock:
            graph_data = {
                'nodes': [
                    {
                        'id': node_id,
                        'type': self.node_type[node_id],
                        'location': self.nodes[node_id],
                        'space_info': self.space_info.get(node_id, {}) if self.node_type[node_id] == "chunk_server" else None
                    }
                    for node_id in self.nodes
                ],
                'edges': [
                    {
                        'source': source,
                        'target': target,
                        'distance': distance
                    }
                    for source, targets in self.distances.items()
                    for target, distance in targets.items()
                    if source < target  # Avoid duplicate edges
                ],
                'active_clients': [
                    node_id for node_id in self.nodes
                    if self.node_type[node_id] == "client"
                ]
            }
            return graph_data

    def update_space_info(self, node_id: str, total: int, used: int):
        """Update space information for a node."""
        with self.lock:
            self.space_info[node_id] = {
                'total': total,
                'used': used,
                'available': total - used
            }

class ClientServerPriority:
    def __init__(self):
        self.client_priorities: Dict[str, List[ServerDistance]] = {}
        self.lock = threading.Lock()

    def update_priorities(self, client_id: str, client_location: Tuple[float, float], 
                        servers: Dict[str, Tuple[float, float, int]]):
        """Update priority list for a client based on distances to servers."""
        with self.lock:
            distances = []
            for server_id, (x, y, space) in servers.items():
                dx = client_location[0] - x
                dy = client_location[1] - y
                distance = math.sqrt(dx*dx + dy*dy)
                distances.append(ServerDistance(server_id, distance, space))
            
            # Sort by distance
            self.client_priorities[client_id] = sorted(distances, key=lambda x: x.distance)

    def get_priority_servers(self, client_id: str, exclude_servers: Set[str] = None) -> List[str]:
        """Get ordered list of servers by priority for a client."""
        with self.lock:
            if client_id not in self.client_priorities:
                return []
            
            if exclude_servers is None:
                exclude_servers = set()
                
            return [s.server_id for s in self.client_priorities[client_id] 
                   if s.server_id not in exclude_servers]

class MasterServer:
    def __init__(self, config_path: str):
        self.logger = GFSLogger.get_logger('master')
        self.logger.info(f"Initializing Master Server with config from {config_path}")
        
        self.config = toml.load(config_path)
        self.logger.debug(f"Loaded configuration: {self.config}")
        
        self.file_manager = FileManager("data/metadata", self.config)
        self.chunk_servers: Dict[str, float] = {}
        self.chunk_server_lock = threading.Lock()
        
        self.host = self.config['master']['host']
        self.port = self.config['master']['port']
        self.logger.info(f"Master server will run on {self.host}:{self.port}")
        
        # Start server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.logger.info("Server socket initialized and listening")
        
        # Start heartbeat checker thread
        self.heartbeat_thread = threading.Thread(target=self._check_heartbeats)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
        self.logger.info("Heartbeat checker thread started")
        
        # Add replication queue and its lock
        self.replication_queue = set()  # Set of (file_path, chunk_id) tuples
        self.replication_queue_lock = threading.Lock()
        
        # Start background replication thread
        self.replication_thread = threading.Thread(target=self._handle_pending_replications)
        self.replication_thread.daemon = True
        self.replication_thread.start()
        self.logger.info("Started background replication thread")
        
        self.location_graph = LocationGraph()
        self.clients = {}  # client_id -> last_heartbeat_time
        self.client_lock = threading.Lock()
        
        # Start client heartbeat checker thread
        self.client_heartbeat_thread = threading.Thread(target=self._check_client_heartbeats)
        self.client_heartbeat_thread.daemon = True
        self.client_heartbeat_thread.start()
        
        self.client_priorities = ClientServerPriority()

    def _check_heartbeats(self):
        """Check for chunk server heartbeats and remove dead servers."""
        self.logger.info("Starting heartbeat checking loop")
        while True:
            current_time = time.time()
            with self.chunk_server_lock:
                dead_servers = [
                    addr for addr, last_beat in self.chunk_servers.items()
                    if current_time - last_beat > self.config['chunk_server']['heartbeat_interval'] * 2
                ]
                for addr in dead_servers:
                    self.logger.warning(f"Chunk server {addr} is dead, removing...")
                    del self.chunk_servers[addr]
                    self.location_graph.remove_node(addr)
                
                self.logger.debug(f"Active chunk servers: {list(self.chunk_servers.keys())}")
            time.sleep(self.config['chunk_server']['heartbeat_interval'])

    def handle_client(self, client_socket: socket.socket, address: str):
        """Handle client connections."""
        self.logger.info(f"New client connection from {address}")
        try:
            while True:
                message = receive_message(client_socket)
                if not message:
                    self.logger.debug(f"Client {address} disconnected")
                    break

                command = message.get('command')
                self.logger.debug(f"Received command '{command}' from {address}")

                if command == 'heartbeat':
                    self._handle_heartbeat(message)
                elif command == 'register_chunk_server':
                    self._handle_register_chunk_server(message)
                elif command == 'get_chunk_locations':
                    self._handle_get_chunk_locations(client_socket, message)
                elif command == 'update_chunk_locations':
                    self._handle_update_chunk_locations(message)
                elif command == 'list_files':
                    self._handle_list_files(client_socket)
                elif command == 'get_file_metadata':
                    self._handle_get_file_metadata(client_socket, message)
                elif command == 'get_chunk_servers':
                    self._handle_get_chunk_servers(client_socket, message)
                elif command == 'add_file':
                    self._handle_add_file(client_socket, message)
                elif command == 'get_replica_locations':
                    self._handle_get_replica_locations(client_socket, message)
                elif command == 'update_chunk_offset':
                    self._handle_update_chunk_offset(client_socket, message)
                elif command == 'add_chunk':
                    self._handle_add_chunk(client_socket, message)
                elif command == 'update_file_metadata':
                    self._handle_update_file_metadata(client_socket, message)
                elif command == 'register_client':
                    self._handle_register_client(client_socket, message)
                elif command == 'client_heartbeat':
                    self._handle_client_heartbeat(message)
                elif command == 'get_graph_data':
                    self._handle_get_graph_data(client_socket, message)

        except Exception as e:
            self.logger.error(f"Error handling client {address}: {e}", exc_info=True)
        finally:
            client_socket.close()
            self.logger.debug(f"Closed connection with {address}")

    def _handle_heartbeat(self, message: Dict):
        """Handle heartbeat from chunk server."""
        address = message['address']
        location = message['location']
        space_info = message.get('space_info', {})
        
        with self.chunk_server_lock:
            self.chunk_servers[address] = time.time()
            self.location_graph.add_node(address, location, "chunk_server")
            if space_info:
                self.location_graph.update_space_info(address, 
                    space_info['total'],
                    space_info['used']
                )
            
            # Update priorities for all clients
            server_info = {}
            for addr, _ in self.chunk_servers.items():
                node = self.location_graph.nodes.get(addr)
                if node:
                    space = self.location_graph.space_info.get(addr, {}).get('available', 0)
                    server_info[addr] = (*node, space)
            
            for client_id in self.clients:
                if client_id in self.location_graph.nodes:
                    self.client_priorities.update_priorities(
                        client_id,
                        self.location_graph.nodes[client_id],
                        server_info
                    )

    def _handle_register_chunk_server(self, message: Dict):
        """Handle chunk server registration with location."""
        address = message['address']
        location = message['location']
        with self.chunk_server_lock:
            self.chunk_servers[address] = time.time()
            self.location_graph.add_node(address, location, "chunk_server")
            self.logger.info(f"Registered chunk server at {address} location {location}")

    def _handle_register_client(self, client_socket: socket.socket, message: Dict):
        """Handle client registration with location."""
        client_id = message['client_id']
        location = message['location']
        with self.client_lock:
            self.clients[client_id] = time.time()
            self.location_graph.add_node(client_id, location, "client")
            self.logger.info(f"Registered client {client_id} at location {location}")
        send_message(client_socket, {'status': 'ok'})

    def _handle_client_heartbeat(self, message: Dict):
        """Handle client heartbeat."""
        client_id = message['client_id']
        with self.client_lock:
            self.clients[client_id] = time.time()

    def _check_client_heartbeats(self):
        """Check for client heartbeats and remove dead clients."""
        while True:
            current_time = time.time()
            with self.client_lock:
                dead_clients = [
                    client_id for client_id, last_beat in self.clients.items()
                    if current_time - last_beat > 60  # Client timeout after 60 seconds
                ]
                for client_id in dead_clients:
                    self.logger.warning(f"Client {client_id} is dead, removing...")
                    del self.clients[client_id]
                    self.location_graph.remove_node(client_id)
            time.sleep(30)

    def _handle_get_chunk_locations(self, client_socket: socket.socket, message: Dict):
        """Handle request for chunk locations."""
        self.logger.debug(f"Getting chunk locations for {message['file_path']}, chunk_id: {message['chunk_id']}")
        locations = self.file_manager.get_chunk_locations(
            message['file_path'],
            message['chunk_id']
        )
        self.logger.debug(f"Found chunk locations: {locations}")
        send_message(client_socket, {
            'status': 'ok',
            'locations': locations
        })

    def _handle_update_chunk_locations(self, message: Dict):
        """Handle chunk location updates."""
        self.logger.debug(
            f"Updating chunk locations for {message['file_path']}, "
            f"chunk_id: {message['chunk_id']}, "
            f"locations: {message['locations']}"
        )
        self.file_manager.update_chunk_locations(
            message['file_path'],
            message['chunk_id'],
            message['locations']
        )

    def _handle_list_files(self, client_socket: socket.socket):
        """Handle request to list files."""
        files = self.file_manager.list_files()
        self.logger.debug(f"Listing files: {files}")
        send_message(client_socket, {
            'status': 'ok',
            'files': files
        })

    def _handle_get_file_metadata(self, client_socket: socket.socket, message: Dict):
        """Handle request for file metadata."""
        self.logger.debug(f"Getting metadata for file: {message['file_path']}")
        metadata = self.file_manager.get_file_metadata(message['file_path'])
        self.logger.debug(f"Retrieved metadata: {metadata}")
        send_message(client_socket, {
            'status': 'ok',
            'metadata': metadata
        })

    def _handle_get_chunk_servers(self, client_socket: socket.socket, message: Dict):
        """Handle request for available chunk servers, now considering location."""
        client_id = message.get('client_id')
        if client_id:
            # Get nearest chunk servers for this client
            with self.chunk_server_lock:
                nearest_servers = self.location_graph.get_nearest_chunk_servers(client_id)
                active_servers = [
                    server for server in nearest_servers
                    if server in self.chunk_servers
                ]
                self.logger.debug(f"Returning nearest active chunk servers for {client_id}: {active_servers}")
                send_message(client_socket, {
                    'status': 'ok',
                    'servers': active_servers
                })
        else:
            # Fallback to original behavior if no client_id provided
            with self.chunk_server_lock:
                active_servers = list(self.chunk_servers.keys())
                send_message(client_socket, {
                    'status': 'ok',
                    'servers': active_servers
                })

    def _handle_add_file(self, client_socket: socket.socket, message: Dict):
        """Handle adding a new file."""
        try:
            self.logger.debug(f"Adding new file: {message['file_path']}")
            self.file_manager.add_file(
                message['file_path'],
                message['total_size'],
                message['chunk_ids']
            )
            send_message(client_socket, {'status': 'ok'})
        except Exception as e:
            self.logger.error(f"Failed to add file: {e}")
            send_message(client_socket, {
                'status': 'error',
                'message': str(e)
            })

    def _handle_get_replica_locations(self, client_socket: socket.socket, message: Dict):
        """Handle request for replica locations with priority."""
        client_id = message.get('client_id')
        excluding = message.get('excluding', set())
        
        if isinstance(excluding, str):
            excluding = {excluding}
        
        with self.chunk_server_lock:
            if client_id:
                # Get priority-ordered servers for this client
                servers = self.client_priorities.get_priority_servers(client_id, excluding)
            else:
                # Fallback to random selection
                servers = [s for s in self.chunk_servers.keys() if s not in excluding]
            
            # Select servers for replication
            num_replicas = min(
                self.config['master']['replication_factor'] - 1,
                len(servers)
            )
            
            # Take the first num_replicas servers from the priority list
            selected_servers = servers[:num_replicas]
            
            send_message(client_socket, {
                'status': 'ok',
                'locations': selected_servers
            })

    def _handle_update_chunk_offset(self, client_socket: socket.socket, message: Dict):
        """Handle updating chunk offset."""
        try:
            self.file_manager.update_chunk_offset(
                message['file_path'],
                message['chunk_id'],
                message['offset']
            )
            send_message(client_socket, {'status': 'ok'})
        except Exception as e:
            self.logger.error(f"Failed to update chunk offset: {e}")
            send_message(client_socket, {
                'status': 'error',
                'message': str(e)
            })

    def _handle_add_chunk(self, client_socket: socket.socket, message: Dict):
        """Handle adding a new chunk to an existing file."""
        try:
            file_path = message['file_path']
            chunk_id = message['chunk_id']
            chunk_index = message['chunk_index']
            size = message['size']
            
            self.logger.debug(f"Adding chunk {chunk_id} to file {file_path}")
            
            with self.chunk_server_lock:
                metadata = self.file_manager.get_file_metadata(file_path)
                if metadata:
                    # Update existing file
                    metadata.chunk_ids.append(chunk_id)
                    metadata.chunk_offsets[chunk_id] = size
                    metadata.last_chunk_id = chunk_id
                    metadata.last_chunk_offset = size
                    metadata.total_size += size
                else:
                    # Create new file
                    self.file_manager.add_file(
                        file_path=file_path,
                        total_size=size,
                        chunk_ids=[chunk_id]
                    )
                
                self.file_manager._save_metadata()
                
            send_message(client_socket, {'status': 'ok'})
            self.logger.info(f"Successfully added chunk {chunk_id} to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to add chunk: {e}")
            send_message(client_socket, {
                'status': 'error',
                'message': str(e)
            })

    def _handle_pending_replications(self):
        """Background thread to handle pending replications."""
        while True:
            try:
                with self.replication_queue_lock:
                    pending_replications = list(self.replication_queue)
                
                for file_path, chunk_id in pending_replications:
                    try:
                        metadata = self.file_manager.get_file_metadata(file_path)
                        if not metadata or chunk_id not in metadata.pending_replication:
                            self.replication_queue.discard((file_path, chunk_id))
                            continue
                            
                        current_replicas = len(metadata.chunk_locations.get(chunk_id, []))
                        needed_replicas = metadata.pending_replication[chunk_id]
                        
                        if current_replicas >= self.config['master']['replication_factor']:
                            # Replication factor met
                            metadata.pending_replication.pop(chunk_id, None)
                            self.replication_queue.discard((file_path, chunk_id))
                            continue
                            
                        # Get current locations
                        current_locations = set(metadata.chunk_locations.get(chunk_id, []))
                        
                        # Get available chunk servers
                        with self.chunk_server_lock:
                            available_servers = set(self.chunk_servers.keys()) - current_locations
                            
                        if not available_servers:
                            continue  # No new servers available
                            
                        # Try to replicate to new servers
                        self._replicate_to_new_servers(
                            file_path,
                            chunk_id,
                            current_locations,
                            available_servers,
                            needed_replicas
                        )
                            
                    except Exception as e:
                        self.logger.error(f"Error handling replication for {file_path}, chunk {chunk_id}: {e}")
                        
            except Exception as e:
                self.logger.error(f"Error in replication thread: {e}")
                
            time.sleep(10)  # Wait before next replication attempt

    def _replicate_to_new_servers(self, file_path: str, chunk_id: str, 
                                current_locations: Set[str], 
                                available_servers: Set[str],
                                needed_replicas: int):
        """Attempt to replicate a chunk to new servers."""
        # Select a source server
        if not current_locations:
            self.logger.error(f"No source locations for chunk {chunk_id}")
            return
            
        source_server = random.choice(list(current_locations))
        
        # Select target servers
        target_servers = random.sample(
            list(available_servers),
            min(needed_replicas, len(available_servers))
        )
        
        for target_server in target_servers:
            try:
                # Connect to source server
                host, port = source_server.split(':')
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as source_sock:
                    source_sock.connect((host, int(port)))
                    
                    # Request chunk data
                    send_message(source_sock, {
                        'command': 'retrieve_chunk',
                        'chunk_id': chunk_id
                    })
                    
                    response = receive_message(source_sock)
                    if response['status'] != 'ok':
                        continue
                        
                    chunk_data = response['data']
                    
                    # Send to target server
                    host, port = target_server.split(':')
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as target_sock:
                        target_sock.connect((host, int(port)))
                        
                        send_message(target_sock, {
                            'command': 'store_chunk',
                            'chunk_id': chunk_id,
                            'file_path': file_path,
                            'data': chunk_data,
                            'replica_servers': True
                        })
                        
                        response = receive_message(target_sock)
                        if response['status'] == 'ok':
                            # Update locations
                            self.file_manager.update_chunk_locations(
                                file_path,
                                chunk_id,
                                list(current_locations | {target_server})
                            )
                            
            except Exception as e:
                self.logger.error(f"Failed to replicate to {target_server}: {e}")

    def _handle_update_file_metadata(self, client_socket: socket.socket, message: Dict):
        """Handle updating file metadata after successful chunk storage."""
        try:
            file_path = message['file_path']
            chunk_id = message['chunk_id']
            chunk_locations = message['chunk_locations']
            chunk_size = message.get('chunk_size', 0)
            pending_replication = message.get('pending_replication', False)

            self.logger.debug(f"Updating metadata for file {file_path}, chunk {chunk_id}")

            # Get existing metadata or create new
            metadata = self.file_manager.get_file_metadata(file_path)
            if metadata:
                # Update existing file metadata
                if chunk_id not in metadata.chunk_ids:
                    metadata.chunk_ids.append(chunk_id)
                metadata.chunk_locations[chunk_id] = chunk_locations
                metadata.total_size += chunk_size
                metadata.last_chunk_id = chunk_id
                metadata.last_chunk_offset = chunk_size
                
                # Handle pending replication
                if pending_replication:
                    needed_replicas = self.config['master']['replication_factor'] - len(chunk_locations)
                    if needed_replicas > 0:
                        metadata.pending_replication[chunk_id] = needed_replicas
                        with self.replication_queue_lock:
                            self.replication_queue.add((file_path, chunk_id))
            else:
                # Create new file metadata
                self.file_manager.add_file(
                    file_path=file_path,
                    total_size=chunk_size,
                    chunk_ids=[chunk_id]
                )
                # Update chunk locations
                self.file_manager.update_chunk_locations(file_path, chunk_id, chunk_locations)
                
                # Handle pending replication for new file
                if pending_replication:
                    needed_replicas = self.config['master']['replication_factor'] - len(chunk_locations)
                    if needed_replicas > 0:
                        metadata = self.file_manager.get_file_metadata(file_path)
                        metadata.pending_replication[chunk_id] = needed_replicas
                        with self.replication_queue_lock:
                            self.replication_queue.add((file_path, chunk_id))

            self.logger.info(f"Successfully updated metadata for {file_path}")
            send_message(client_socket, {'status': 'ok'})

        except Exception as e:
            self.logger.error(f"Failed to update file metadata: {e}")
            send_message(client_socket, {
                'status': 'error',
                'message': str(e)
            })

    def _handle_get_graph_data(self, client_socket: socket.socket, message: Dict):
        """Handle request for graph visualization data."""
        try:
            client_id = message.get('client_id')
            graph_data = self.location_graph.get_graph_data()
            
            # Add client-specific priority information
            if client_id:
                # Get priorities from MasterServer's client_priorities
                graph_data['client_priorities'] = {
                    client_id: self.client_priorities.get_priority_servers(client_id)
                }
            
            send_message(client_socket, {
                'status': 'ok',
                'graph_data': graph_data
            })
        except Exception as e:
            self.logger.error(f"Failed to get graph data: {e}")
            send_message(client_socket, {
                'status': 'error',
                'message': str(e)
            })

    def run(self):
        """Run the master server."""
        self.logger.info(f"Master server running on {self.host}:{self.port}")
        try:
            while True:
                client_socket, address = self.server_socket.accept()
                self.logger.info(f"Accepted connection from {address}")
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
                self.logger.debug(f"Started client handler thread for {address}")
        except KeyboardInterrupt:
            self.logger.info("Shutting down master server...")
            self.server_socket.close()
        except Exception as e:
            self.logger.error(f"Unexpected error in master server: {e}", exc_info=True)
            self.server_socket.close()

if __name__ == "__main__":
    master = MasterServer("configs/config.toml")
    master.run() 