import socket
import os
from typing import List, Dict
import toml
from .utils import send_message, receive_message
from .chunk import Chunk
from .logger import GFSLogger
import random

class GFSClient:
    def __init__(self, config_path: str):
        self.logger = GFSLogger.get_logger('client')
        self.logger.info(f"Initializing GFS Client with config from {config_path}")
        
        self.config = toml.load(config_path)
        self.master_host = self.config['master']['host']
        self.master_port = self.config['master']['port']
        self.chunk_size = self.config['client']['upload_chunk_size']
        self.logger.debug(f"Master server at {self.master_host}:{self.master_port}")
        self.logger.debug(f"Chunk size set to {self.chunk_size} bytes")

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

    def upload_file(self, local_path: str, gfs_path: str):
        """Upload a file to GFS."""
        self.logger.info(f"Starting upload of {local_path} to GFS path {gfs_path}")
        
        # Check for available chunk servers first
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

        # First, add file metadata to master
        with self._connect_to_master() as master_sock:
            self.logger.debug("Adding file metadata to master")
            send_message(master_sock, {
                'command': 'add_file',
                'file_path': gfs_path,
                'total_size': total_size,
                'chunk_ids': chunk_ids
            })
            response = receive_message(master_sock)
            if response.get('status') != 'ok':
                raise Exception(f"Failed to add file metadata: {response.get('message')}")

        # Store chunks on primary chunk servers
        for chunk in chunks:
            self.logger.debug(f"Processing chunk {chunk.chunk_id} (index: {chunk.chunk_index})")
            
            # Select primary server for this chunk
            primary_server = random.choice(available_servers)
            self.logger.debug(f"Selected primary server for chunk: {primary_server}")
            
            try:
                # Send chunk to primary server, which will handle replication
                with self._connect_to_chunk_server(primary_server) as chunk_sock:
                    send_message(chunk_sock, {
                        'command': 'store_chunk',
                        'data': chunk.data,
                        'file_path': chunk.file_path,
                        'chunk_index': chunk.chunk_index
                    })
                    response = receive_message(chunk_sock)
                    if response['status'] != 'ok':
                        raise Exception(f"Failed to store chunk: {response.get('message')}")
                    
            except Exception as e:
                self.logger.error(f"Failed to store chunk on {primary_server}: {e}")
                raise Exception(f"Failed to store chunk {chunk.chunk_id}: {str(e)}")
        
        self.logger.info(f"Successfully uploaded {local_path} to GFS path {gfs_path}")

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
            chunk = Chunk(data, gfs_path, 0)
            self._store_chunk(chunk)
            return
        
        # Get last chunk information
        last_chunk_id = metadata.last_chunk_id
        last_chunk_offset = metadata.last_chunk_offset
        
        # Check if we need a new chunk
        if last_chunk_offset + len(data) > self.chunk_size:
            # Create new chunk
            self.logger.debug("Creating new chunk for append")
            chunk = Chunk(data, gfs_path, len(metadata.chunk_ids))
            self._store_chunk(chunk)
        else:
            # Append to existing chunk
            self.logger.debug(f"Appending to existing chunk {last_chunk_id}")
            self._append_to_chunk(gfs_path, last_chunk_id, data, last_chunk_offset)

    def _append_to_chunk(self, file_path: str, chunk_id: str, data: bytes, offset: int):
        """Append data to an existing chunk."""
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
        
        # Send append request to primary chunk server
        primary_server = locations[0]
        try:
            with self._connect_to_chunk_server(primary_server) as chunk_sock:
                self.logger.debug(f"Appending {len(data)} bytes at offset {offset}")
                send_message(chunk_sock, {
                    'command': 'append_chunk',
                    'chunk_id': chunk_id,
                    'data': data,
                    'offset': offset,
                    'file_path': file_path
                })
                response = receive_message(chunk_sock)
                if response['status'] != 'ok':
                    raise Exception(f"Failed to append: {response.get('message')}")
                
                new_offset = response['new_offset']
                self.logger.debug(f"New offset after append: {new_offset}")
                
                # Update master with new offset
                with self._connect_to_master() as master_sock:
                    send_message(master_sock, {
                        'command': 'update_chunk_offset',
                        'file_path': file_path,
                        'chunk_id': chunk_id,
                        'offset': new_offset
                    })
        
        except Exception as e:
            self.logger.error(f"Failed to append to chunk: {e}")
            raise