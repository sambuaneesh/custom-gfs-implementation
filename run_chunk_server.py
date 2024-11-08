from src.chunk_server import ChunkServer

if __name__ == "__main__":
    server = ChunkServer("configs/config.toml")
    server.run() 