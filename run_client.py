import argparse
import subprocess
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="Run a GFS client")
    parser.add_argument("--client_id", type=str, help="Client ID")
    parser.add_argument("--x", type=float, default=0.0, help="X coordinate of client location")
    parser.add_argument("--y", type=float, default=0.0, help="Y coordinate of client location")
    args = parser.parse_args()

    # Set environment variables for the Streamlit app to use
    os.environ['GFS_CLIENT_ID'] = args.client_id if args.client_id else ''
    os.environ['GFS_CLIENT_X'] = str(args.x)
    os.environ['GFS_CLIENT_Y'] = str(args.y)

    # Run Streamlit
    streamlit_args = [
        "streamlit", "run", "interfaces/streamlit_app.py",
        "--server.maxUploadSize", "10000"
    ]
    
    subprocess.run(streamlit_args)

if __name__ == "__main__":
    main() 