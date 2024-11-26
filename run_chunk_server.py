import argparse
from src.chunk_server import ChunkServer

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a chunk server")
    parser.add_argument("config_path", type=str, help="Path to the configuration file")
    parser.add_argument("--server_id", type=str, help="Server ID")
    parser.add_argument("--x", type=float, default=0.0, help="X coordinate of server location")
    parser.add_argument("--y", type=float, default=0.0, help="Y coordinate of server location")
    args = parser.parse_args()
    
    server = ChunkServer(args.config_path, args.server_id, x=args.x, y=args.y)
    server.run() 