import socket
import threading
import time
import os
import toml
from typing import Dict
from .utils import send_message, receive_message, find_free_port
from .chunk import Chunk
from .logger import GFSLogger

class ChunkServer:
    def __init__(self, config_path: str):
        self.logger = GFSLogger.get_logger('chunk_server')
        self.logger.info(f"Initializing Chunk Server with config from {config_path}")
        
        self.config = toml.load(config_path)
        self.logger.debug(f"Loaded configuration: {self.config}")
        
        self.port = find_free_port()
        self.host = "localhost"
        self.address = f"{self.host}:{self.port}"
        self.logger.info(f"Chunk server will run on {self.address}")
        
        self.master_host = self.config['master']['host']
        self.master_port = self.config['master']['port']
        self.logger.debug(f"Master server address: {self.master_host}:{self.master_port}")
        
        self.data_dir = os.path.join(
            self.config['chunk_server']['data_dir'],
            f"chunk_server_{self.port}"
        )
        os.makedirs(self.data_dir, exist_ok=True)
        self.logger.info(f"Created data directory at {self.data_dir}")
        
        # Start server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.logger.info("Server socket initialized and listening")
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._send_heartbeat)
        self.heartbeat_thread.daemon = True
        self.logger.debug("Created heartbeat thread")
        
        # Register with master
        self._register_with_master()

    def _register_with_master(self):
        """Register this chunk server with the master."""
        self.logger.info("Attempting to register with master server")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.master_host, self.master_port))
                self.logger.debug("Connected to master server")
                send_message(s, {
                    'command': 'register_chunk_server',
                    'address': self.address
                })
            self.logger.info(f"Successfully registered with master at {self.master_host}:{self.master_port}")
        except Exception as e:
            self.logger.error(f"Failed to register with master: {e}", exc_info=True)
            exit(1)

    def _send_heartbeat(self):
        """Send periodic heartbeats to master."""
        self.logger.info("Starting heartbeat loop")
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((self.master_host, self.master_port))
                    send_message(s, {
                        'command': 'heartbeat',
                        'address': self.address
                    })
                    self.logger.debug(f"Sent heartbeat to master")
            except Exception as e:
                self.logger.error(f"Failed to send heartbeat: {e}")
            
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

                if command == 'store_chunk':
                    self._handle_store_chunk(client_socket, message)
                elif command == 'retrieve_chunk':
                    self._handle_retrieve_chunk(client_socket, message)
                elif command == 'delete_chunk':
                    self._handle_delete_chunk(client_socket, message)

        except Exception as e:
            self.logger.error(f"Error handling client {address}: {e}", exc_info=True)
        finally:
            client_socket.close()
            self.logger.debug(f"Closed connection with {address}")

    def _handle_store_chunk(self, client_socket: socket.socket, message: Dict):
        """Handle storing a chunk."""
        try:
            self.logger.info(f"Storing chunk for file {message['file_path']}")
            chunk = Chunk(
                message['data'],
                message['file_path'],
                message['chunk_index']
            )
            self.logger.debug(f"Created chunk with ID: {chunk.chunk_id}")
            
            chunk.save_to_disk(self.data_dir)
            self.logger.debug(f"Saved chunk to disk at {self.data_dir}")
            
            send_message(client_socket, {
                'status': 'ok',
                'chunk_id': chunk.chunk_id
            })
            self.logger.info(f"Successfully stored chunk {chunk.chunk_id}")
        except Exception as e:
            self.logger.error(f"Failed to store chunk: {e}", exc_info=True)
            send_message(client_socket, {
                'status': 'error',
                'message': str(e)
            })

    def _handle_retrieve_chunk(self, client_socket: socket.socket, message: Dict):
        """Handle retrieving a chunk."""
        try:
            chunk_id = message['chunk_id']
            self.logger.info(f"Retrieving chunk: {chunk_id}")
            
            data = Chunk.load_from_disk(self.data_dir, chunk_id)
            self.logger.debug(f"Loaded chunk {chunk_id} from disk, size: {len(data)} bytes")
            
            send_message(client_socket, {
                'status': 'ok',
                'data': data
            })
            self.logger.info(f"Successfully sent chunk {chunk_id} to client")
        except Exception as e:
            self.logger.error(f"Failed to retrieve chunk: {e}", exc_info=True)
            send_message(client_socket, {
                'status': 'error',
                'message': str(e)
            })

    def _handle_delete_chunk(self, client_socket: socket.socket, message: Dict):
        """Handle deleting a chunk."""
        try:
            chunk_id = message['chunk_id']
            self.logger.info(f"Deleting chunk: {chunk_id}")
            
            chunk_path = os.path.join(self.data_dir, chunk_id)
            if os.path.exists(chunk_path):
                os.remove(chunk_path)
                self.logger.debug(f"Deleted chunk file: {chunk_path}")
            else:
                self.logger.warning(f"Chunk file not found: {chunk_path}")
            
            send_message(client_socket, {'status': 'ok'})
            self.logger.info(f"Successfully processed delete request for chunk {chunk_id}")
        except Exception as e:
            self.logger.error(f"Failed to delete chunk: {e}", exc_info=True)
            send_message(client_socket, {
                'status': 'error',
                'message': str(e)
            })

    def run(self):
        """Run the chunk server."""
        self.logger.info(f"Starting chunk server on {self.host}:{self.port}")
        self.heartbeat_thread.start()
        
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
            self.logger.info("Shutting down chunk server...")
            self.server_socket.close()
        except Exception as e:
            self.logger.error(f"Unexpected error in chunk server: {e}", exc_info=True)
            self.server_socket.close()

if __name__ == "__main__":
    server = ChunkServer("configs/config.toml")
    server.run() 