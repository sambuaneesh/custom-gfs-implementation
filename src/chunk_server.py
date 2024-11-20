import socket
import threading
import time
import os
import toml
from typing import Dict, List, Optional
from .utils import send_message, receive_message, find_free_port
from .chunk import Chunk
from .logger import GFSLogger
import argparse
import json
import shutil

class ChunkServer:
    def __init__(self, config_path: str, server_id: str = None, space_limit_mb: int = 1024):
        self.logger = GFSLogger.get_logger('chunk_server')
        self.transaction_logger = GFSLogger.get_transaction_logger('chunk_server')
        self.logger.info(f"Initializing Chunk Server with config from {config_path}")
        
        self.config = toml.load(config_path)
        self.logger.debug(f"Loaded configuration: {self.config}")
        
        self.server_id = server_id or f"chunk_server_{int(time.time())}"
        self.space_limit = space_limit_mb * 1024 * 1024  # Convert MB to bytes
        self.logger.info(f"Space limit set to {space_limit_mb}MB")
        
        self.port = self._get_or_create_port()
        self.host = "localhost"
        self.address = f"{self.host}:{self.port}"
        self.logger.info(f"Chunk server {self.server_id} will run on {self.address}")
        
        self.master_host = self.config['master']['host']
        self.master_port = self.config['master']['port']
        self.logger.debug(f"Master server address: {self.master_host}:{self.master_port}")
        
        self.data_dir = os.path.join(
            self.config['chunk_server']['data_dir'],
            self.server_id
        )
        os.makedirs(self.data_dir, exist_ok=True)
        self.logger.info(f"Created data directory at {self.data_dir}")
        
        self._save_server_info()
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.logger.info("Server socket initialized and listening")
        
        self.heartbeat_thread = threading.Thread(target=self._send_heartbeat)
        self.heartbeat_thread.daemon = True
        self.logger.debug("Created heartbeat thread")
        
        self._register_with_master()

    def _get_or_create_port(self) -> int:
        """Get existing port for server ID or create new one."""
        server_info_file = os.path.join(
            self.config['chunk_server']['data_dir'],
            'server_info.json'
        )
        
        if os.path.exists(server_info_file):
            with open(server_info_file, 'r') as f:
                server_info = json.load(f)
                if self.server_id in server_info:
                    port = server_info[self.server_id]['port']
                    self.logger.info(f"Found existing port {port} for server {self.server_id}")
                    return port
        
        port = find_free_port()
        self.logger.info(f"Assigned new port {port} for server {self.server_id}")
        return port

    def _save_server_info(self):
        """Save server information to disk."""
        server_info_file = os.path.join(
            self.config['chunk_server']['data_dir'],
            'server_info.json'
        )
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(server_info_file), exist_ok=True)
        
        # Load existing info or create new
        if os.path.exists(server_info_file):
            with open(server_info_file, 'r') as f:
                server_info = json.load(f)
        else:
            server_info = {}
        
        # Update server info
        server_info[self.server_id] = {
            'port': self.port,
            'data_dir': self.data_dir,
            'last_start': time.time()
        }
        
        # Save updated info
        with open(server_info_file, 'w') as f:
            json.dump(server_info, f, indent=2)
        
        self.logger.debug(f"Saved server info for {self.server_id}")

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
                elif command == 'replicate_chunk':
                    self._handle_store_chunk(client_socket, message)
                elif command == 'prepare_chunk':
                    self._handle_prepare_chunk(client_socket, message)
                elif command == 'commit_chunk':
                    self._handle_commit_chunk(client_socket, message)
                elif command == 'rollback_chunk':
                    self._handle_rollback_chunk(client_socket, message)
                elif command == 'append_chunk':
                    self._handle_append_chunk(client_socket, message)
                elif command == 'prepare_append':
                    self._handle_prepare_append(client_socket, message)
                elif command == 'commit_append':
                    self._handle_commit_append(client_socket, message)
                elif command == 'rollback_append':
                    self._handle_rollback_append(client_socket, message)
                elif command == 'check_space':
                    self._handle_check_space(client_socket, message)

        except Exception as e:
            self.logger.error(f"Error handling client {address}: {e}", exc_info=True)
        finally:
            client_socket.close()
            self.logger.debug(f"Closed connection with {address}")

    def _replicate_chunk(self, chunk_data: bytes, file_path: str, chunk_index: int, 
                        replica_servers: List[str], current_replica: int = 0):
        """Handle chunk replication to other servers in the chain."""
        self.logger.info(f"Handling replication {current_replica + 1} of chunk for {file_path}")
        
        # Store the chunk locally first
        chunk = Chunk(chunk_data, file_path, chunk_index)
        chunk.save_to_disk(self.data_dir)
        
        # If there are more servers in the chain, forward to the next one
        if current_replica < len(replica_servers) - 1:
            next_server = replica_servers[current_replica + 1]
            try:
                with self._connect_to_chunk_server(next_server) as next_sock:
                    self.logger.debug(f"Forwarding chunk to next server: {next_server}")
                    send_message(next_sock, {
                        'command': 'replicate_chunk',
                        'data': chunk_data,
                        'file_path': file_path,
                        'chunk_index': chunk_index,
                        'replica_servers': replica_servers,
                        'current_replica': current_replica + 1
                    })
                    response = receive_message(next_sock)
                    if response['status'] != 'ok':
                        raise Exception(f"Replication failed at {next_server}")
            except Exception as e:
                self.logger.error(f"Failed to forward chunk to {next_server}: {e}")
                raise
        
        return chunk.chunk_id

    def get_available_space(self) -> int:
        """Get available space in bytes."""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(self.data_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return self.space_limit - total_size

    def can_store_chunk(self, chunk_size: int) -> bool:
        """Check if there's enough space to store a chunk."""
        return self.get_available_space() >= chunk_size

    def _handle_store_chunk(self, client_socket: socket.socket, message: Dict):
        """Handle storing a chunk and initiating replication if needed."""
        try:
            chunk_id = message.get('chunk_id')
            file_path = message['file_path']
            data = message['data']
            chunk_size = len(data)
            transaction_id = str(int(time.time() * 1000))

            # Check available space
            if not self.can_store_chunk(chunk_size):
                self.logger.warning(f"Not enough space to store chunk {chunk_id} ({chunk_size} bytes)")
                send_message(client_socket, {
                    'status': 'error',
                    'message': 'insufficient_space',
                    'available_space': self.get_available_space()
                })
                return

            GFSLogger.log_transaction(
                self.transaction_logger,
                transaction_id,
                "START",
                f"Primary received store request for chunk {chunk_id} of {file_path}"
            )

            # If this is the primary server (not part of replication chain)
            if 'replica_servers' not in message:
                # Get replica locations from master
                available_replicas = []
                with self._connect_to_master() as master_sock:
                    send_message(master_sock, {
                        'command': 'get_replica_locations',
                        'excluding': self.address
                    })
                    response = receive_message(master_sock)
                    potential_replicas = response['locations']
                    
                    # Check space on each potential replica
                    for replica in potential_replicas:
                        try:
                            with self._connect_to_chunk_server(replica) as replica_sock:
                                send_message(replica_sock, {
                                    'command': 'check_space',
                                    'size': chunk_size
                                })
                                response = receive_message(replica_sock)
                                if response['status'] == 'ok':
                                    available_replicas.append(replica)
                        except Exception as e:
                            self.logger.warning(f"Failed to check space on {replica}: {e}")

                GFSLogger.log_transaction(
                    self.transaction_logger,
                    transaction_id,
                    "PREPARE",
                    f"Found {len(available_replicas)} replicas with sufficient space"
                )

                # Store locally first
                temp_path = os.path.join(self.data_dir, f"{chunk_id}.{transaction_id}.temp")
                final_path = os.path.join(self.data_dir, chunk_id)
                
                try:
                    # Write to temporary file first
                    with open(temp_path, 'wb') as f:
                        f.write(data)
                    
                    # Try to replicate to available servers
                    successful_replicas = []
                    for replica in available_replicas:
                        try:
                            with self._connect_to_chunk_server(replica) as replica_sock:
                                send_message(replica_sock, {
                                    'command': 'store_chunk',
                                    'data': data,
                                    'file_path': file_path,
                                    'chunk_id': chunk_id,
                                    'replica_servers': True
                                })
                                response = receive_message(replica_sock)
                                if response['status'] == 'ok':
                                    successful_replicas.append(replica)
                        except Exception as e:
                            self.logger.error(f"Failed to replicate to {replica}: {e}")

                    # Move temporary file to final location
                    os.replace(temp_path, final_path)
                    successful_servers = [self.address] + successful_replicas

                    # Update master with actual locations
                    with self._connect_to_master() as master_sock:
                        send_message(master_sock, {
                            'command': 'update_file_metadata',
                            'file_path': file_path,
                            'chunk_id': chunk_id,
                            'chunk_locations': successful_servers,
                            'chunk_size': chunk_size,
                            'pending_replication': len(successful_servers) < self.config['master']['replication_factor']
                        })

                    GFSLogger.log_transaction(
                        self.transaction_logger,
                        transaction_id,
                        "SUCCESS",
                        f"Stored chunk with {len(successful_replicas)} replicas"
                    )

                    send_message(client_socket, {
                        'status': 'ok',
                        'chunk_id': chunk_id,
                        'replicas': len(successful_replicas)
                    })

                except Exception as e:
                    # Cleanup on failure
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    if os.path.exists(final_path):
                        os.remove(final_path)
                    raise

            else:
                # We are a replica
                chunk = Chunk(data, file_path, message.get('chunk_index', 0))
                chunk.save_to_disk(self.data_dir)
                send_message(client_socket, {
                    'status': 'ok',
                    'chunk_id': chunk.chunk_id
                })

        except Exception as e:
            self.logger.error(f"Failed to store/replicate chunk: {e}", exc_info=True)
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

    def _handle_append_chunk(self, client_socket: socket.socket, message: Dict):
        """Handle appending data to a chunk."""
        try:
            chunk_id = message['chunk_id']
            data = message['data']
            offset = message['offset']
            file_path = message['file_path']
            
            self.logger.info(f"Appending to chunk {chunk_id} at offset {offset}")
            
            # Load existing chunk
            chunk_path = os.path.join(self.data_dir, chunk_id)
            
            # If the file doesn't exist, create it with the data
            if not os.path.exists(chunk_path):
                self.logger.debug(f"Chunk file doesn't exist, creating new file")
                with open(chunk_path, 'wb') as f:
                    f.write(data)
                new_offset = len(data)
            else:
                # Append to existing file
                with open(chunk_path, 'rb+') as f:
                    # Get current file size
                    f.seek(0, 2)  # Seek to end
                    current_size = f.tell()
                    
                    # Verify offset
                    if offset != current_size:
                        self.logger.warning(f"Offset mismatch: expected {current_size}, got {offset}")
                    
                    # Write new data at the end
                    f.write(data)
                    new_offset = f.tell()
            
            self.logger.debug(f"New offset after append: {new_offset}")
            
            # If this is the primary, propagate to replicas
            if 'replica_servers' not in message:
                # Get replica locations from master
                with self._connect_to_master() as master_sock:
                    send_message(master_sock, {
                        'command': 'get_replica_locations',
                        'excluding': self.address
                    })
                    response = receive_message(master_sock)
                    replica_servers = response['locations']
                
                # Forward append to replicas
                for replica in replica_servers:
                    try:
                        with self._connect_to_chunk_server(replica) as replica_sock:
                            send_message(replica_sock, {
                                'command': 'append_chunk',
                                'chunk_id': chunk_id,
                                'data': data,
                                'offset': offset,
                                'file_path': file_path,
                                'replica_servers': True  # Mark as replica operation
                            })
                            response = receive_message(replica_sock)
                            if response['status'] != 'ok':
                                raise Exception(f"Replica append failed at {replica}")
                    except Exception as e:
                        self.logger.error(f"Failed to propagate append to replica {replica}: {e}")
            
            send_message(client_socket, {
                'status': 'ok',
                'new_offset': new_offset
            })
            
        except Exception as e:
            self.logger.error(f"Failed to append to chunk: {e}", exc_info=True)
            send_message(client_socket, {
                'status': 'error',
                'message': str(e)
            })

    def _handle_prepare_append(self, client_socket: socket.socket, message: Dict):
        """Handle preparation phase of append operation."""
        try:
            chunk_id = message['chunk_id']
            transaction_id = message.get('transaction_id')
            
            GFSLogger.log_transaction(
                self.transaction_logger,
                transaction_id,
                "PREPARE",
                f"Received prepare request for chunk {chunk_id}"
            )
            
            temp_path = os.path.join(self.data_dir, f"{chunk_id}.{transaction_id}.temp")
            chunk_path = os.path.join(self.data_dir, chunk_id)
            
            GFSLogger.log_transaction(
                self.transaction_logger,
                transaction_id,
                "PREPARE",
                f"Creating temporary file at {temp_path}"
            )
            
            try:
                if os.path.exists(chunk_path):
                    GFSLogger.log_transaction(
                        self.transaction_logger,
                        transaction_id,
                        "PREPARE",
                        f"Copying existing data from {chunk_path}"
                    )
                    with open(chunk_path, 'rb') as src, open(temp_path, 'wb') as dst:
                        dst.write(src.read())
                        dst.seek(message['offset'])
                        dst.write(message['data'])
                else:
                    GFSLogger.log_transaction(
                        self.transaction_logger,
                        transaction_id,
                        "PREPARE",
                        "Creating new chunk file"
                    )
                    with open(temp_path, 'wb') as f:
                        f.write(message['data'])
                
                GFSLogger.log_transaction(
                    self.transaction_logger,
                    transaction_id,
                    "PREPARE",
                    "Prepare phase completed successfully"
                )
                send_message(client_socket, {
                    'status': 'ok',
                    'message': 'prepared'
                })
                
            except Exception as e:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise
                
        except Exception as e:
            GFSLogger.log_transaction(
                self.transaction_logger,
                transaction_id,
                "PREPARE",
                f"Prepare phase failed: {str(e)}"
            )
            send_message(client_socket, {
                'status': 'error',
                'message': str(e)
            })

    def _handle_commit_append(self, client_socket: socket.socket, message: Dict):
        """Handle commit phase of append operation."""
        try:
            chunk_id = message['chunk_id']
            transaction_id = message['transaction_id']
            
            GFSLogger.log_transaction(
                self.transaction_logger,
                transaction_id,
                "COMMIT",
                f"Received commit request for chunk {chunk_id}"
            )
            
            temp_path = os.path.join(self.data_dir, f"{chunk_id}.{transaction_id}.temp")
            chunk_path = os.path.join(self.data_dir, chunk_id)
            
            if not os.path.exists(temp_path):
                raise Exception("No prepared data found for commit")
            
            GFSLogger.log_transaction(
                self.transaction_logger,
                transaction_id,
                "COMMIT",
                f"Committing changes from {temp_path} to {chunk_path}"
            )
            os.replace(temp_path, chunk_path)
            
            GFSLogger.log_transaction(
                self.transaction_logger,
                transaction_id,
                "COMMIT",
                "Commit completed successfully"
            )
            send_message(client_socket, {
                'status': 'ok',
                'message': 'committed'
            })
            
        except Exception as e:
            GFSLogger.log_transaction(
                self.transaction_logger,
                transaction_id,
                "COMMIT",
                f"Commit failed: {str(e)}"
            )
            send_message(client_socket, {
                'status': 'error',
                'message': str(e)
            })

    def _handle_rollback_append(self, client_socket: socket.socket, message: Dict):
        """Handle rollback of append operation."""
        try:
            chunk_id = message['chunk_id']
            transaction_id = message['transaction_id']
            
            self.logger.info(f"Rolling back append for chunk {chunk_id}, transaction {transaction_id}")
            
            temp_path = os.path.join(self.data_dir, f"{chunk_id}.{transaction_id}.temp")
            
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            send_message(client_socket, {
                'status': 'ok',
                'message': 'rolled back'
            })
            self.logger.debug(f"Successfully rolled back append for transaction {transaction_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to rollback append: {e}", exc_info=True)
            send_message(client_socket, {
                'status': 'error',
                'message': str(e)
            })

    def _handle_prepare_chunk(self, client_socket: socket.socket, message: Dict):
        """Handle prepare phase for chunk storage."""
        try:
            chunk_id = message['chunk_id']
            data = message['data']
            chunk_size = len(data)

            # Check available space
            if not self.can_store_chunk(chunk_size):
                self.logger.warning(f"Not enough space to prepare chunk {chunk_id} ({chunk_size} bytes)")
                send_message(client_socket, {
                    'status': 'error',
                    'message': 'insufficient_space',
                    'available_space': self.get_available_space()
                })
                return

            transaction_id = message['transaction_id']
            file_path = message['file_path']
            
            GFSLogger.log_transaction(
                self.transaction_logger,
                transaction_id,
                "PREPARE",
                f"Received prepare request for chunk {chunk_id} from primary"
            )
            
            # Create temporary file
            temp_path = os.path.join(self.data_dir, f"{chunk_id}.{transaction_id}.temp")
            try:
                with open(temp_path, 'wb') as f:
                    f.write(data)
                GFSLogger.log_transaction(
                    self.transaction_logger,
                    transaction_id,
                    "PREPARE",
                    f"✅ Successfully prepared chunk {chunk_id}"
                )
                send_message(client_socket, {
                    'status': 'ok',
                    'message': 'prepared'
                })
            except Exception as e:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise Exception(f"Failed to prepare chunk: {e}")
                
        except Exception as e:
            GFSLogger.log_transaction(
                self.transaction_logger,
                transaction_id,
                "PREPARE",
                f"❌ Failed to prepare chunk: {e}"
            )
            send_message(client_socket, {
                'status': 'error',
                'message': str(e)
            })

    def _handle_commit_chunk(self, client_socket: socket.socket, message: Dict):
        """Handle commit phase for chunk storage."""
        try:
            chunk_id = message['chunk_id']
            transaction_id = message['transaction_id']
            
            GFSLogger.log_transaction(
                self.transaction_logger,
                transaction_id,
                "COMMIT",
                f"Received commit request for chunk {chunk_id}"
            )
            
            temp_path = os.path.join(self.data_dir, f"{chunk_id}.{transaction_id}.temp")
            chunk_path = os.path.join(self.data_dir, chunk_id)
            
            if not os.path.exists(temp_path):
                raise Exception("No prepared data found for commit")
            
            # Atomic rename of temp file to final chunk file
            os.replace(temp_path, chunk_path)
            
            GFSLogger.log_transaction(
                self.transaction_logger,
                transaction_id,
                "COMMIT",
                f"✅ Successfully committed chunk {chunk_id}"
            )
            send_message(client_socket, {
                'status': 'ok',
                'message': 'committed'
            })
            
        except Exception as e:
            GFSLogger.log_transaction(
                self.transaction_logger,
                transaction_id,
                "COMMIT",
                f"❌ Failed to commit chunk: {e}"
            )
            send_message(client_socket, {
                'status': 'error',
                'message': str(e)
            })

    def _handle_rollback_chunk(self, client_socket: socket.socket, message: Dict):
        """Handle rollback for chunk storage."""
        try:
            chunk_id = message['chunk_id']
            transaction_id = message['transaction_id']
            
            GFSLogger.log_transaction(
                self.transaction_logger,
                transaction_id,
                "ROLLBACK",
                f"Received rollback request for chunk {chunk_id}"
            )
            
            temp_path = os.path.join(self.data_dir, f"{chunk_id}.{transaction_id}.temp")
            if os.path.exists(temp_path):
                os.remove(temp_path)
                GFSLogger.log_transaction(
                    self.transaction_logger,
                    transaction_id,
                    "ROLLBACK",
                    f"✅ Successfully rolled back chunk {chunk_id}"
                )
            
            send_message(client_socket, {
                'status': 'ok',
                'message': 'rolled back'
            })
            
        except Exception as e:
            GFSLogger.log_transaction(
                self.transaction_logger,
                transaction_id,
                "ROLLBACK",
                f"❌ Failed to rollback chunk: {e}"
            )
            send_message(client_socket, {
                'status': 'error',
                'message': str(e)
            })

    def _handle_check_space(self, client_socket: socket.socket, message: Dict):
        """Handle space availability check."""
        size = message['size']
        if self.can_store_chunk(size):
            send_message(client_socket, {'status': 'ok'})
        else:
            send_message(client_socket, {
                'status': 'error',
                'message': 'insufficient_space',
                'available_space': self.get_available_space()
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

    def _connect_to_master(self) -> socket.socket:
        """Connect to the master server."""
        self.logger.debug(f"Connecting to master at {self.master_host}:{self.master_port}")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.master_host, self.master_port))
        self.logger.debug("Connected to master server")
        return s

    def _connect_to_chunk_server(self, address: str) -> socket.socket:
        """Connect to another chunk server."""
        host, port = address.split(':')
        self.logger.debug(f"Connecting to chunk server at {address}")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, int(port)))
        self.logger.debug(f"Connected to chunk server at {address}")
        return s

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a chunk server")
    parser.add_argument("config_path", type=str, help="Path to the configuration file")
    parser.add_argument("--server_id", type=str, help="Server ID")
    args = parser.parse_args()
    
    server = ChunkServer(args.config_path, args.server_id)
    server.run() 