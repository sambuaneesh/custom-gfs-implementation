import socket
import threading
import time
import toml
from typing import Dict
from .file_manager import FileManager
from .utils import send_message, receive_message
from .logger import GFSLogger
import random

class MasterServer:
    def __init__(self, config_path: str):
        self.logger = GFSLogger.get_logger('master')
        self.logger.info(f"Initializing Master Server with config from {config_path}")
        
        self.config = toml.load(config_path)
        self.logger.debug(f"Loaded configuration: {self.config}")
        
        self.file_manager = FileManager("data/metadata")
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
                    self._handle_heartbeat(message['address'])
                elif command == 'register_chunk_server':
                    self._handle_register_chunk_server(message['address'])
                elif command == 'get_chunk_locations':
                    self._handle_get_chunk_locations(client_socket, message)
                elif command == 'update_chunk_locations':
                    self._handle_update_chunk_locations(message)
                elif command == 'list_files':
                    self._handle_list_files(client_socket)
                elif command == 'get_file_metadata':
                    self._handle_get_file_metadata(client_socket, message)
                elif command == 'get_chunk_servers':
                    self._handle_get_chunk_servers(client_socket)
                elif command == 'add_file':
                    self._handle_add_file(client_socket, message)
                elif command == 'get_replica_locations':
                    self._handle_get_replica_locations(client_socket, message)

        except Exception as e:
            self.logger.error(f"Error handling client {address}: {e}", exc_info=True)
        finally:
            client_socket.close()
            self.logger.debug(f"Closed connection with {address}")

    def _handle_heartbeat(self, address: str):
        """Handle heartbeat from chunk server."""
        with self.chunk_server_lock:
            self.chunk_servers[address] = time.time()
            self.logger.debug(f"Received heartbeat from chunk server {address}")

    def _handle_register_chunk_server(self, address: str):
        """Handle chunk server registration."""
        with self.chunk_server_lock:
            self.chunk_servers[address] = time.time()
            self.logger.info(f"Registered new chunk server at {address}")

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

    def _handle_get_chunk_servers(self, client_socket: socket.socket):
        """Handle request for available chunk servers."""
        with self.chunk_server_lock:
            active_servers = list(self.chunk_servers.keys())
            self.logger.debug(f"Returning active chunk servers: {active_servers}")
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
        """Handle request for replica locations."""
        with self.chunk_server_lock:
            available_servers = list(self.chunk_servers.keys())
            # Remove the requesting server from available servers
            if message['excluding'] in available_servers:
                available_servers.remove(message['excluding'])
            
            # Select servers for replication
            num_replicas = min(
                self.config['master']['replication_factor'] - 1,  # -1 because one copy is already on primary
                len(available_servers)
            )
            selected_servers = random.sample(available_servers, num_replicas)
            
            self.logger.debug(f"Selected replica servers: {selected_servers}")
            send_message(client_socket, {
                'status': 'ok',
                'locations': selected_servers
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