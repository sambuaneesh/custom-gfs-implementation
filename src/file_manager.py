import os
from typing import List, Dict, Set
import json
from dataclasses import dataclass, asdict
import threading
from .logger import GFSLogger

@dataclass
class FileMetadata:
    file_path: str
    total_size: int
    chunk_ids: List[str]
    chunk_locations: Dict[str, List[str]]  # chunk_id -> list of chunk server addresses
    chunk_offsets: Dict[str, int]  # chunk_id -> offset within chunk
    last_chunk_id: str  # ID of the last chunk for appends
    last_chunk_offset: int  # Current offset in the last chunk

class FileManager:
    def __init__(self, metadata_dir: str, config: Dict):
        self.logger = GFSLogger.get_logger('file_manager')
        self.logger.info(f"Initializing FileManager with metadata directory: {metadata_dir}")
        
        self.metadata_dir = metadata_dir
        self.metadata_lock = threading.Lock()
        self.files: Dict[str, FileMetadata] = {}
        self.config = config
        self.logger.debug(f"Initialized with config: {config}")
        self._load_metadata()

    def _load_metadata(self):
        """Load metadata from disk."""
        self.logger.info("Loading metadata from disk")
        os.makedirs(self.metadata_dir, exist_ok=True)
        metadata_file = os.path.join(self.metadata_dir, 'metadata.json')
        
        if os.path.exists(metadata_file):
            self.logger.debug(f"Reading metadata from {metadata_file}")
            with open(metadata_file, 'r') as f:
                data = json.load(f)
                self.files = {
                    path: FileMetadata(**metadata)
                    for path, metadata in data.items()
                }
            self.logger.info(f"Loaded metadata for {len(self.files)} files")
        else:
            self.logger.info("No existing metadata file found, starting fresh")

    def _save_metadata(self):
        """Save metadata to disk."""
        self.logger.debug("Saving metadata to disk")
        metadata_file = os.path.join(self.metadata_dir, 'metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump({
                path: asdict(metadata)
                for path, metadata in self.files.items()
            }, f, indent=2)
        self.logger.debug(f"Saved metadata for {len(self.files)} files")

    def add_file(self, file_path: str, total_size: int, chunk_ids: List[str]):
        """Add a new file to the metadata."""
        self.logger.info(f"Adding new file: {file_path}")
        
        with self.metadata_lock:
            self.files[file_path] = FileMetadata(
                file_path=file_path,
                total_size=total_size,
                chunk_ids=chunk_ids,
                chunk_locations={},
                chunk_offsets={chunk_id: 0 for chunk_id in chunk_ids},
                last_chunk_id=chunk_ids[-1] if chunk_ids else None,
                last_chunk_offset=total_size % self.config['master']['chunk_size']
            )
            self._save_metadata()
            self.logger.info(f"Successfully added file {file_path}")

    def update_file_metadata(self, file_path: str, chunk_id: str, locations: List[str], size: int):
        """Update file metadata with new chunk information."""
        with self.metadata_lock:
            if file_path not in self.files:
                self.add_file(file_path, size, [chunk_id])
            else:
                metadata = self.files[file_path]
                if chunk_id not in metadata.chunk_ids:
                    metadata.chunk_ids.append(chunk_id)
                metadata.chunk_locations[chunk_id] = locations
                metadata.total_size += size
                metadata.last_chunk_id = chunk_id
                metadata.last_chunk_offset = size
            self._save_metadata()

    def update_chunk_locations(self, file_path: str, chunk_id: str, locations: List[str]):
        """Update the locations of a chunk."""
        self.logger.debug(f"Updating chunk locations for {file_path}, chunk: {chunk_id}")
        self.logger.debug(f"New locations: {locations}")
        
        with self.metadata_lock:
            if file_path in self.files:
                self.files[file_path].chunk_locations[chunk_id] = locations
                self._save_metadata()
                self.logger.debug("Successfully updated chunk locations")
            else:
                self.logger.warning(f"Attempted to update locations for non-existent file: {file_path}")

    def get_chunk_locations(self, file_path: str, chunk_id: str) -> List[str]:
        """Get the locations of a chunk."""
        self.logger.debug(f"Getting chunk locations for {file_path}, chunk: {chunk_id}")
        with self.metadata_lock:
            if file_path in self.files:
                locations = self.files[file_path].chunk_locations.get(chunk_id, [])
                self.logger.debug(f"Found locations: {locations}")
                return locations
            self.logger.warning(f"Requested locations for non-existent file: {file_path}")
            return []

    def list_files(self) -> List[str]:
        """List all files in the system."""
        self.logger.debug("Listing all files")
        with self.metadata_lock:
            files = list(self.files.keys())
            self.logger.debug(f"Found {len(files)} files: {files}")
            return files

    def get_file_metadata(self, file_path: str) -> FileMetadata:
        """Get metadata for a specific file."""
        self.logger.debug(f"Getting metadata for file: {file_path}")
        with self.metadata_lock:
            metadata = self.files.get(file_path)
            if metadata:
                self.logger.debug(f"Found metadata: {metadata}")
            else:
                self.logger.warning(f"No metadata found for file: {file_path}")
            return metadata

    def update_chunk_offset(self, file_path: str, chunk_id: str, offset: int):
        """Update the offset of a chunk."""
        self.logger.debug(f"Updating offset for chunk {chunk_id} in file {file_path} to {offset}")
        with self.metadata_lock:
            if file_path in self.files:
                # Update the chunk's offset
                self.files[file_path].chunk_offsets[chunk_id] = offset
                
                # If this is the last chunk, update the last_chunk_offset
                if chunk_id == self.files[file_path].last_chunk_id:
                    self.files[file_path].last_chunk_offset = offset
                
                # Update total file size
                chunk_index = self.files[file_path].chunk_ids.index(chunk_id)
                total_size = chunk_index * self.config['master']['chunk_size'] + offset
                self.files[file_path].total_size = total_size
                
                self._save_metadata()
                self.logger.debug(f"Updated offsets and total size for {file_path}")
            else:
                self.logger.warning(f"Attempted to update offset for non-existent file: {file_path}")