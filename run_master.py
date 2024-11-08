from src.master import MasterServer

if __name__ == "__main__":
    master = MasterServer("configs/config.toml")
    master.run() 