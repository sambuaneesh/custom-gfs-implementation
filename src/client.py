import socket
import os
from typing import List, Dict, Optional
import toml
from .utils import send_message, receive_message
from .chunk import Chunk
from .logger import GFSLogger
import random
import time

class GFSClient:
    def __init__(self, config_path: str, client_id: str = None, x: float = 0, y: float = 0):
        self.logger = GFSLogger.get_logger('client')
        self.transaction_logger = GFSLogger.get_transaction_logger('client')
        self.logger.info(f"Initializing GFS Client with config from {config_path}")
        
        self.config = toml.load(config_path)
        self.master_host = self.config['master']['host']
        self.master_port = self.config['master']['port']
        self.chunk_size = self.config['client']['upload_chunk_size']
        self.logger.debug(f"Master server at {self.master_host}:{self.master_port}")
        self.logger.debug(f"Chunk size set to {self.chunk_size} bytes")
        
        self.location = (x, y)
        self.client_id = client_id or f"client_{int(time.time())}"
        self.logger.info(f"Client {self.client_id} location set to ({x}, {y})")
        
        # Register with master
        self._register_with_master()

    def _register_with_master(self):
        """Register client with master server."""
        try:
            with self._connect_to_master() as master_sock:
                send_message(master_sock, {
                    'command': 'register_client',
                    'client_id': self.client_id,
                    'location': self.location
                })
                response = receive_message(master_sock)
                if response['status'] != 'ok':
                    raise Exception(f"Failed to register with master: {response.get('message')}")
        except Exception as e:
            self.logger.error(f"Failed to register with master: {e}")
            raise

    def _send_heartbeat(self):
        """Send periodic heartbeats to master."""
        while True:
            try:
                with self._connect_to_master() as master_sock:
                    send_message(master_sock, {
                        'command': 'client_heartbeat',
                        'client_id': self.client_id,
                        'location': self.location
                    })
            except Exception as e:
                self.logger.error(f"Failed to send heartbeat: {e}")
            time.sleep(30)  # Send client heartbeat every 30 seconds

    def _connect_to_master(self) -> socket.socket:
        """Connect to the master server."""
        self.logger.debug(f"Connecting to master at {self.master_host}:{self.master_port}")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.master_host, self.master_port))
        self.logger.debug("Connected to master server")
        return s

    def _connect_to_chunk_server(self, address: str) -> socket.socket:
        """Connect to a chunk server."""
        host, port = address.split(':')
        self.logger.debug(f"Connecting to chunk server at {address}")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, int(port)))
        self.logger.debug(f"Connected to chunk server at {address}")
        return s

    def _get_available_chunk_servers(self) -> List[str]:
        """Get list of available chunk servers from master."""
        self.logger.debug("Getting available chunk servers from master")
        with self._connect_to_master() as master_sock:
            send_message(master_sock, {'command': 'get_chunk_servers'})
            response = receive_message(master_sock)
            servers = response.get('servers', [])
            self.logger.debug(f"Available chunk servers: {servers}")
            if not servers:
                raise Exception("No chunk servers available")
            return servers

    def _store_chunk_with_fallback(self, chunk: Chunk, available_servers: List[str]) -> Optional[str]:
        """Try to store chunk on available servers, handling space constraints."""
        for server in available_servers:
            try:
                with self._connect_to_chunk_server(server) as chunk_sock:
                    send_message(chunk_sock, {
                        'command': 'store_chunk',
                        'data': chunk.data,
                        'file_path': chunk.file_path,
                        'chunk_index': chunk.chunk_index,
                        'chunk_id': chunk.chunk_id,
                        'client_id': self.client_id
                    })
                    response = receive_message(chunk_sock)
                    
                    if response['status'] == 'ok':
                        return server
                    elif response.get('message') == 'insufficient_space':
                        continue
                    else:
                        continue
                    
            except Exception as e:
                continue
                
        return None

    def upload_file(self, local_path: str, gfs_path: str):
        """Upload a file to GFS."""
        self.logger.info(f"Starting upload of {local_path} to GFS path {gfs_path}")
        
        # Check for available chunk servers
        available_servers = self._get_available_chunk_servers()
        self.logger.info(f"Found {len(available_servers)} available chunk servers")
        
        if not available_servers:
            error_msg = "No chunk servers available for upload"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        
        # Read file and split into chunks
        with open(local_path, 'rb') as f:
            data = f.read()
        total_size = len(data)
        self.logger.debug(f"Read {total_size} bytes from {local_path}")
        
        chunks = []
        chunk_ids = []
        for i in range(0, len(data), self.chunk_size):
            chunk_data = data[i:i + self.chunk_size]
            chunk = Chunk(chunk_data, gfs_path, len(chunks))
            chunks.append(chunk)
            chunk_ids.append(chunk.chunk_id)
        self.logger.info(f"Split file into {len(chunks)} chunks")

        # Store chunks through primary servers
        for chunk in chunks:
            # Get all available servers
            available_servers = self._get_available_chunk_servers()
            if not available_servers:
                raise Exception("No chunk servers available")

            # Try to store chunk on any available server
            success_server = self._store_chunk_with_fallback(chunk, available_servers)
            
            if not success_server:
                self.logger.error(f"Failed to store chunk {chunk.chunk_id} on any server")
                raise Exception(f"No servers available with sufficient space for chunk {chunk.chunk_id}")

            self.logger.info(f"Successfully stored chunk {chunk.chunk_id} on server {success_server}")

    def download_file(self, gfs_path: str, local_path: str):
        """Download a file from GFS."""
        self.logger.info(f"Starting download of {gfs_path} to {local_path}")
        
        # Get file metadata from master
        with self._connect_to_master() as master_sock:
            self.logger.debug(f"Requesting metadata for {gfs_path}")
            send_message(master_sock, {
                'command': 'get_file_metadata',
                'file_path': gfs_path
            })
            response = receive_message(master_sock)
            metadata = response['metadata']
            self.logger.debug(f"Received metadata: {metadata}")

        # Download chunks
        chunks_data = []
        for chunk_id in metadata.chunk_ids:
            self.logger.debug(f"Processing chunk {chunk_id}")
            
            # Get chunk locations from master
            with self._connect_to_master() as master_sock:
                self.logger.debug("Requesting chunk locations from master")
                send_message(master_sock, {
                    'command': 'get_chunk_locations',
                    'file_path': gfs_path,
                    'chunk_id': chunk_id
                })
                response = receive_message(master_sock)
                self.logger.debug(f"Received chunk locations: {response['locations']}")

            # Try to download from available locations
            chunk_data = None
            for server_address in response['locations']:
                try:
                    self.logger.debug(f"Attempting to retrieve chunk from {server_address}")
                    with self._connect_to_chunk_server(server_address) as chunk_sock:
                        send_message(chunk_sock, {
                            'command': 'retrieve_chunk',
                            'chunk_id': chunk_id
                        })
                        response = receive_message(chunk_sock)
                        if response['status'] == 'ok':
                            chunk_data = response['data']
                            self.logger.debug(f"Successfully retrieved chunk from {server_address}")
                            break
                except Exception as e:
                    self.logger.error(f"Failed to retrieve chunk from {server_address}: {e}")

            if chunk_data is None:
                error_msg = f"Failed to retrieve chunk {chunk_id}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            chunks_data.append(chunk_data)

        # Write chunks to local file
        self.logger.debug(f"Writing {len(chunks_data)} chunks to {local_path}")
        with open(local_path, 'wb') as f:
            for chunk_data in chunks_data:
                f.write(chunk_data)
        
        self.logger.info(f"Successfully downloaded {gfs_path} to {local_path}")

    def list_files(self) -> List[str]:
        """List all files in GFS."""
        self.logger.info("Listing all files in GFS")
        with self._connect_to_master() as master_sock:
            send_message(master_sock, {'command': 'list_files'})
            response = receive_message(master_sock)
            files = response['files']
            self.logger.debug(f"Retrieved file list: {files}")
            return files

    def append_to_file(self, gfs_path: str, data: bytes):
        """Append data to a file in GFS."""
        self.logger.info(f"Starting append operation to {gfs_path}")
        
        # Get file metadata from master
        with self._connect_to_master() as master_sock:
            send_message(master_sock, {
                'command': 'get_file_metadata',
                'file_path': gfs_path
            })
            response = receive_message(master_sock)
            if response['status'] != 'ok':
                raise Exception(f"Failed to get file metadata: {response.get('message')}")
            
            metadata = response['metadata']
            
        # If file doesn't exist, create it
        if not metadata:
            self.logger.debug(f"File {gfs_path} doesn't exist, creating new file")
            self.upload_file_from_bytes(data, gfs_path)
            return
        
        # Get last chunk information
        last_chunk_id = metadata.last_chunk_id
        last_chunk_offset = metadata.last_chunk_offset
        
        # Check if we need a new chunk
        if last_chunk_offset + len(data) > self.chunk_size:
            self.logger.debug("Data exceeds chunk size, creating new chunk")
            # Create new chunk with the data
            chunk_index = len(metadata.chunk_ids)
            self.upload_file_from_bytes(data, gfs_path, chunk_index)
        else:
            # Append to existing chunk
            self.logger.debug(f"Appending to existing chunk {last_chunk_id}")
            self._append_to_chunk(gfs_path, last_chunk_id, data, last_chunk_offset)

    def _append_to_chunk(self, file_path: str, chunk_id: str, data: bytes, offset: int):
        """Append data to an existing chunk using two-phase commit."""
        # Get chunk locations
        with self._connect_to_master() as master_sock:
            send_message(master_sock, {
                'command': 'get_chunk_locations',
                'file_path': file_path,
                'chunk_id': chunk_id
            })
            response = receive_message(master_sock)
            locations = response['locations']
        
        if not locations:
            raise Exception(f"No locations found for chunk {chunk_id}")
        
        # Execute two-phase commit
        success = self._two_phase_append(file_path, chunk_id, data, offset, locations)
        
        if success:
            # Update master with new offset
            new_offset = offset + len(data)
            with self._connect_to_master() as master_sock:
                send_message(master_sock, {
                    'command': 'update_chunk_offset',
                    'file_path': file_path,
                    'chunk_id': chunk_id,
                    'offset': new_offset
                })
        else:
            raise Exception("Failed to append data: two-phase commit failed")

    def _two_phase_append(self, file_path: str, chunk_id: str, data: bytes, offset: int, 
                         locations: List[str]) -> bool:
        """Execute two-phase commit protocol for append operation."""
        transaction_id = str(int(time.time() * 1000))
        
        GFSLogger.log_transaction(
            self.transaction_logger,
            transaction_id,
            "START",
            f"Starting transaction for chunk {chunk_id}"
        )
        
        primary_server = locations[0]
        replica_servers = locations[1:]
        
        GFSLogger.log_transaction(
            self.transaction_logger,
            transaction_id,
            "PREPARE",
            f"Primary: {primary_server}, Replicas: {replica_servers}"
        )
        
        try:
            # Phase 1: Prepare
            GFSLogger.log_transaction(
                self.transaction_logger,
                transaction_id,
                "PREPARE",
                "📝 PHASE 1: PREPARE - Starting prepare phase"
            )
            prepared_servers = []
            
            # Prepare primary
            try:
                with self._connect_to_chunk_server(primary_server) as primary_sock:
                    GFSLogger.log_transaction(
                        self.transaction_logger,
                        transaction_id,
                        "PREPARE",
                        f"Sending prepare request to primary {primary_server}"
                    )
                    send_message(primary_sock, {
                        'command': 'prepare_append',
                        'chunk_id': chunk_id,
                        'data': data,
                        'offset': offset,
                        'transaction_id': transaction_id
                    })
                    response = receive_message(primary_sock)
                    if response['status'] == 'ok':
                        prepared_servers.append(primary_server)
                        GFSLogger.log_transaction(
                            self.transaction_logger,
                            transaction_id,
                            "PREPARE",
                            f"✅ Primary {primary_server} prepared successfully"
                        )
                    else:
                        GFSLogger.log_transaction(
                            self.transaction_logger,
                            transaction_id,
                            "PREPARE",
                            f"❌ Primary {primary_server} failed to prepare"
                        )
                        raise Exception(f"Primary server failed to prepare: {response.get('message')}")
            except Exception as e:
                GFSLogger.log_transaction(
                    self.transaction_logger,
                    transaction_id,
                    "PREPARE",
                    f"Failed to prepare primary: {e}"
                )
                return False
            
            # Prepare replicas
            for replica in replica_servers:
                try:
                    with self._connect_to_chunk_server(replica) as replica_sock:
                        GFSLogger.log_transaction(
                            self.transaction_logger,
                            transaction_id,
                            "PREPARE",
                            f"Sending prepare request to replica {replica}"
                        )
                        send_message(replica_sock, {
                            'command': 'prepare_append',
                            'chunk_id': chunk_id,
                            'data': data,
                            'offset': offset,
                            'transaction_id': transaction_id
                        })
                        response = receive_message(replica_sock)
                        if response['status'] == 'ok':
                            prepared_servers.append(replica)
                            GFSLogger.log_transaction(
                                self.transaction_logger,
                                transaction_id,
                                "PREPARE",
                                f"✅ Replica {replica} prepared successfully"
                            )
                        else:
                            GFSLogger.log_transaction(
                                self.transaction_logger,
                                transaction_id,
                                "PREPARE",
                                f"❌ Replica {replica} failed to prepare"
                            )
                            raise Exception(f"Replica server failed to prepare: {response.get('message')}")
                except Exception as e:
                    GFSLogger.log_transaction(
                        self.transaction_logger,
                        transaction_id,
                        "PREPARE",
                        f"Failed to prepare replica {replica}: {e}"
                    )
                    break
            
            # Phase 2: Commit or Rollback
            if len(prepared_servers) == len(locations):
                # All servers prepared successfully, commit
                GFSLogger.log_transaction(
                    self.transaction_logger,
                    transaction_id,
                    "COMMIT",
                    "📝 PHASE 2: COMMIT - All servers prepared, starting commit phase"
                )
                committed_servers = []
                
                for server in prepared_servers:
                    try:
                        with self._connect_to_chunk_server(server) as server_sock:
                            GFSLogger.log_transaction(
                                self.transaction_logger,
                                transaction_id,
                                "COMMIT",
                                f"Sending commit request to {server}"
                            )
                            send_message(server_sock, {
                                'command': 'commit_append',
                                'chunk_id': chunk_id,
                                'transaction_id': transaction_id
                            })
                            response = receive_message(server_sock)
                            if response['status'] == 'ok':
                                committed_servers.append(server)
                                GFSLogger.log_transaction(
                                    self.transaction_logger,
                                    transaction_id,
                                    "COMMIT",
                                    f"✅ Server {server} committed successfully"
                                )
                    except Exception as e:
                        GFSLogger.log_transaction(
                            self.transaction_logger,
                            transaction_id,
                            "COMMIT",
                            f"Failed to commit on server {server}: {e}"
                        )
                        break
                
                success = len(committed_servers) == len(locations)
                if success:
                    GFSLogger.log_transaction(
                        self.transaction_logger,
                        transaction_id,
                        "COMMIT",
                        "🎉 Transaction completed successfully"
                    )
                else:
                    GFSLogger.log_transaction(
                        self.transaction_logger,
                        transaction_id,
                        "COMMIT",
                        "❌ Transaction failed during commit phase"
                    )
                return success
                
            else:
                # Not all servers prepared, rollback
                GFSLogger.log_transaction(
                    self.transaction_logger,
                    transaction_id,
                    "ROLLBACK",
                    "⚠️ Not all servers prepared, initiating rollback"
                )
                for server in prepared_servers:
                    try:
                        with self._connect_to_chunk_server(server) as server_sock:
                            GFSLogger.log_transaction(
                                self.transaction_logger,
                                transaction_id,
                                "ROLLBACK",
                                f"Sending rollback request to {server}"
                            )
                            send_message(server_sock, {
                                'command': 'rollback_append',
                                'chunk_id': chunk_id,
                                'transaction_id': transaction_id
                            })
                            GFSLogger.log_transaction(
                                self.transaction_logger,
                                transaction_id,
                                "ROLLBACK",
                                f"✅ Rollback successful on {server}"
                            )
                    except Exception as e:
                        GFSLogger.log_transaction(
                            self.transaction_logger,
                            transaction_id,
                            "ROLLBACK",
                            f"Failed to rollback on server {server}: {e}"
                        )
                
                return False
                
        except Exception as e:
            GFSLogger.log_transaction(
                self.transaction_logger,
                transaction_id,
                "ROLLBACK",
                f"Two-phase commit failed: {e}",
                exc_info=True
            )
            # Attempt rollback
            for server in prepared_servers:
                try:
                    with self._connect_to_chunk_server(server) as server_sock:
                        GFSLogger.log_transaction(
                            self.transaction_logger,
                            transaction_id,
                            "ROLLBACK",
                            f"Sending rollback request to {server}"
                        )
                        send_message(server_sock, {
                            'command': 'rollback_append',
                            'chunk_id': chunk_id,
                            'transaction_id': transaction_id
                        })
                except Exception as rollback_error:
                    GFSLogger.log_transaction(
                        self.transaction_logger,
                        transaction_id,
                        "ROLLBACK",
                        f"Failed to rollback on server {server}: {rollback_error}"
                    )
            return False

    def upload_file_from_bytes(self, data: bytes, gfs_path: str):
        """Upload bytes directly as a file to GFS."""
        self.logger.info(f"Starting upload of bytes to GFS path {gfs_path}")
        
        # Check for available chunk servers
        available_servers = self._get_available_chunk_servers()
        self.logger.info(f"Found {len(available_servers)} available chunk servers")
        
        if not available_servers:
            error_msg = "No chunk servers available for upload"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        
        # Create a single chunk for the data
        chunk = Chunk(data, gfs_path, 0)
        chunk_ids = [chunk.chunk_id]
        
        # Store chunk
        success_server = self._store_chunk_with_fallback(chunk, available_servers)
        
        if not success_server:
            self.logger.error(f"Failed to store chunk {chunk.chunk_id} on any server")
            raise Exception(f"No servers available with sufficient space for chunk {chunk.chunk_id}")

        self.logger.info(f"Successfully stored chunk {chunk.chunk_id} on server {success_server}")