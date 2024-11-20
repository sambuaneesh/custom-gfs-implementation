import streamlit as st
import os
import sys

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.client import GFSClient
from src.logger import GFSLogger

logger = GFSLogger.get_logger('streamlit_app')

def main():
    logger.info("Starting GFS web interface")
    st.title("Google File System (GFS) Interface")

    # Initialize client
    logger.debug("Initializing GFS client")
    client = GFSClient("configs/config.toml")

    # Sidebar for operations
    operation = st.sidebar.selectbox(
        "Select Operation",
        ["Upload File", "Download File", "List Files", "Append to File"]
    )
    logger.debug(f"Selected operation: {operation}")

    if operation == "Upload File":
        logger.debug("Rendering upload file interface")
        st.header("Upload File")
        uploaded_file = st.file_uploader("Choose a file")
        gfs_path = st.text_input("GFS Path (e.g., /folder/file.txt)")

        if uploaded_file and gfs_path and st.button("Upload"):
            logger.info(f"Starting upload of {uploaded_file.name} to {gfs_path}")
            try:
                # Check if master server is running
                try:
                    client._connect_to_master().close()
                except Exception as e:
                    st.error("Master server is not running. Please start the master server first.")
                    logger.error("Failed to connect to master server", exc_info=True)
                    return

                # Save uploaded file temporarily
                temp_path = f"temp_{uploaded_file.name}"
                logger.debug(f"Saving temporary file to {temp_path}")
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                try:
                    # Upload to GFS
                    logger.debug("Initiating upload to GFS")
                    client.upload_file(temp_path, gfs_path)
                    os.remove(temp_path)
                    logger.info(f"Successfully uploaded {uploaded_file.name}")
                    st.success("File uploaded successfully!")
                except Exception as e:
                    if "No chunk servers available" in str(e):
                        st.error("No chunk servers are running. Please start at least one chunk server.")
                    else:
                        st.error(f"Upload failed: {str(e)}")
                    logger.error("Upload failed", exc_info=True)
            except Exception as e:
                logger.error(f"Upload failed: {e}", exc_info=True)
                st.error(f"Upload failed: {str(e)}")

    elif operation == "Download File":
        logger.debug("Rendering download file interface")
        st.header("Download File")
        files = client.list_files()
        selected_file = st.selectbox("Select File to Download", files if files else ["No files available"])

        if selected_file and selected_file != "No files available" and st.button("Download"):
            logger.info(f"Starting download of {selected_file}")
            try:
                # Download file
                local_path = f"downloaded_{os.path.basename(selected_file)}"
                logger.debug(f"Downloading to temporary path: {local_path}")
                client.download_file(selected_file, local_path)

                # Provide download link
                logger.debug("Creating download button")
                with open(local_path, "rb") as f:
                    st.download_button(
                        label="Click to Download",
                        data=f.read(),
                        file_name=os.path.basename(selected_file)
                    )
                os.remove(local_path)
                logger.info(f"Successfully processed download for {selected_file}")
            except Exception as e:
                logger.error(f"Download failed: {e}", exc_info=True)
                st.error(f"Download failed: {str(e)}")

    elif operation == "List Files":
        logger.debug("Rendering file list interface")
        st.header("Files in GFS")
        files = client.list_files()
        if files:
            logger.info(f"Found {len(files)} files in GFS")
            for file in files:
                st.text(file)
        else:
            logger.info("No files found in GFS")
            st.info("No files found in GFS")

    elif operation == "Append to File":
        logger.debug("Rendering append interface")
        st.header("Append to File")
        
        # Get list of files
        files = client.list_files()
        if not files:
            st.warning("No files available in GFS")
            return

        # File selection
        selected_file = st.selectbox("Select File to Append to", files)
        
        # Text input for append data
        append_data = st.text_area("Enter text to append", "")
        
        # File upload for append
        uploaded_file = st.file_uploader("Or choose a file to append")
        
        if st.button("Append"):
            try:
                # Check if either text or file is provided
                if not append_data and not uploaded_file:
                    st.error("Please provide either text or a file to append")
                    return

                # Get the data to append
                if append_data:
                    data_to_append = append_data.encode('utf-8')
                    logger.debug(f"Appending text data of size {len(data_to_append)} bytes")
                else:
                    data_to_append = uploaded_file.read()
                    logger.debug(f"Appending file data of size {len(data_to_append)} bytes")

                # Perform append operation
                client.append_to_file(selected_file, data_to_append)
                st.success("Successfully appended to file!")
                logger.info(f"Successfully appended to {selected_file}")

            except Exception as e:
                logger.error(f"Append failed: {e}", exc_info=True)
                st.error(f"Append failed: {str(e)}")

if __name__ == "__main__":
    main() 