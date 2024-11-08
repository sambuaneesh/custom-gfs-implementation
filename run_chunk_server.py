import argparse
from src.chunk_server import ChunkServer

def main():
    parser = argparse.ArgumentParser(description='Start a GFS chunk server')
    parser.add_argument('--id', type=str, help='Unique identifier for the chunk server')
    parser.add_argument('--config', type=str, default='configs/config.toml',
                       help='Path to config file')
    args = parser.parse_args()

    server = ChunkServer(args.config, args.id)
    server.run()

if __name__ == "__main__":
    main() 