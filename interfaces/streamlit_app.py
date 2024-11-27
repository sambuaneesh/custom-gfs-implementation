import streamlit as st
import os
import sys
import networkx as nx
import plotly.graph_objects as go
import time
from typing import Dict, Any

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.client import GFSClient
from src.logger import GFSLogger
from src.utils import send_message, receive_message

logger = GFSLogger.get_logger('streamlit_app')

def create_network_graph(graph_data: Dict[str, Any], show_space_usage: bool = False) -> go.Figure:
    """Create a network graph visualization using plotly."""
    # Create networkx graph
    G = nx.Graph()
    
    # Add nodes
    node_colors = []
    node_symbols = []
    node_sizes = []
    node_texts = []
    node_labels = []
    
    # First add chunk servers
    chunk_server_nodes = [
        node for node in graph_data['nodes'] 
        if node['type'] == 'chunk_server'
    ]
    for node in chunk_server_nodes:
        G.add_node(node['id'], pos=node['location'])
        
        if show_space_usage and node['space_info']:
            # Calculate space utilization and color when space usage is enabled
            used_percent = (node['space_info']['used'] / node['space_info']['total']) * 100
            # Color gradient from green (0%) to yellow (50%) to red (100%)
            if used_percent <= 50:
                color = f'rgb(0, {255 - (used_percent * 2)}, 0)'  # Green to Yellow
            else:
                color = f'rgb({min(255, (used_percent - 50) * 5.1)}, {max(0, 255 - (used_percent - 50) * 5.1)}, 0)'  # Yellow to Red
            
            # Format space information
            space_info = f"""<b>Server: {node['id']}</b><br>
                           Location: {node['location']}<br>
                           Space Used: {used_percent:.1f}%<br>
                           Available: {node['space_info']['available'] / (1024*1024):.1f} MB<br>
                           Total: {node['space_info']['total'] / (1024*1024):.1f} MB"""
        else:
            # Default visualization without space usage
            color = '#FF4B4B'  # Default red
            space_info = f"<b>Server: {node['id']}</b><br>Location: {node['location']}"

        node_colors.append(color)
        node_symbols.append('square')
        node_sizes.append(30)
        node_texts.append(space_info)
        node_labels.append('')

    # Then add active clients (don't add edges for clients)
    client_nodes = [
        node for node in graph_data['nodes'] 
        if node['type'] == 'client' and node['id'] in graph_data.get('active_clients', [])
    ]
    for node in client_nodes:
        G.add_node(node['id'], pos=node['location'])
        node_colors.append('#4B8BFF')  # Bright blue
        node_symbols.append('circle')
        node_sizes.append(25)
        node_texts.append(f"<b>Client: {node['id']}</b><br>Location: {node['location']}")
        node_labels.append('')
    
    # Add edges only between chunk servers
    edge_traces = []
    for edge in graph_data['edges']:
        # Only create edges if both nodes are chunk servers
        if (edge['source'] in [n['id'] for n in chunk_server_nodes] and 
            edge['target'] in [n['id'] for n in chunk_server_nodes]):
            source_pos = G.nodes[edge['source']]['pos']
            target_pos = G.nodes[edge['target']]['pos']
            
            # Calculate curve parameters
            mid_x = (source_pos[0] + target_pos[0]) / 2
            mid_y = (source_pos[1] + target_pos[1]) / 2
            control_x = mid_x + (target_pos[1] - source_pos[1]) * 0.1
            control_y = mid_y - (target_pos[0] - source_pos[0]) * 0.1
            
            # Create curved path
            path_x = [source_pos[0], control_x, target_pos[0]]
            path_y = [source_pos[1], control_y, target_pos[1]]
            
            edge_trace = go.Scatter(
                x=path_x,
                y=path_y,
                mode='lines',
                line=dict(
                    width=1,
                    color='rgba(150,150,150,0.4)',
                    shape='spline'
                ),
                hoverinfo='text',
                text=f"Distance: {edge['distance']:.2f} units",
                showlegend=False
            )
            edge_traces.append(edge_trace)
    
    # Add priority information to hover text for chunk servers
    if 'server_priorities' in graph_data:
        priorities = graph_data['server_priorities']
        for node in chunk_server_nodes:
            if node['id'] in priorities:
                priority_info = f"<br>Priority: {priorities[node['id']]}"
                node_texts[-1] += priority_info
    
    # Create node trace
    node_trace = go.Scatter(
        x=[G.nodes[node]['pos'][0] for node in G.nodes()],
        y=[G.nodes[node]['pos'][1] for node in G.nodes()],
        mode='markers+text',
        hoverinfo='text',
        text=node_texts,
        textposition="top center",
        textfont=dict(
            family="Arial",
            size=12,
            color='#2E2E2E'
        ),
        marker=dict(
            size=node_sizes,
            color=node_colors,
            symbol=node_symbols,
            line=dict(width=2, color='#FFFFFF'),
            opacity=0.9
        ),
        showlegend=False
    )
    
    # Create figure
    fig = go.Figure(data=[*edge_traces, node_trace])
    
    # Update layout
    fig.update_layout(
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=40),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            showline=False
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            showline=False
        ),
        plot_bgcolor='#FFFFFF',
        paper_bgcolor='#FFFFFF'
    )
    
    # Add a subtle grid in the background
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.1)')
    
    # Add color scale legend only when space usage is enabled
    # if show_space_usage:
    #     fig.add_trace(go.Scatter(
    #         x=[None],
    #         y=[None],
    #         mode='markers',
    #         marker=dict(
    #             colorscale=[
    #                 [0, 'green'],
    #                 [0.5, 'yellow'],
    #                 [1, 'red']
    #             ],
    #             showscale=True,
    #             colorbar=dict(
    #                 title='Space Usage',
    #                 ticksuffix='%',
    #                 tickmode='array',
    #                 ticktext=['0%', '50%', '100%'],
    #                 tickvals=[0, 50, 100],
    #             ),
    #         ),
    #         showlegend=False,
    #     ))
    
    return fig

def is_text_file(filename: str) -> bool:
    """Check if a file is likely to be a text file based on extension."""
    text_extensions = {
        '.txt', '.log', '.csv', '.md', '.json', '.xml', '.yaml', '.yml',
        '.py', '.js', '.html', '.css', '.cpp', '.c', '.h', '.java',
        '.sh', '.bash', '.conf', '.ini', '.toml', '.cfg'
    }
    return os.path.splitext(filename)[1].lower() in text_extensions

def create_file_explorer(client: GFSClient, current_path: str = "/") -> None:
    """Create a file explorer interface."""
    st.header("File Explorer")
    
    # Get all files from GFS
    all_files = client.list_files()
    
    # Create directory structure
    dir_structure = {}
    for file_path in all_files:
        parts = file_path.strip('/').split('/')
        current_dict = dir_structure
        for i, part in enumerate(parts):
            if i == len(parts) - 1:  # File
                if 'files' not in current_dict:
                    current_dict['files'] = []
                current_dict['files'].append(file_path)
            else:  # Directory
                if part not in current_dict:
                    current_dict[part] = {}
                current_dict = current_dict[part]
    
    # Navigation bar
    path_parts = current_path.strip('/').split('/')
    if current_path != "/":
        if st.button("📁 ..", key="back"):
            # Go up one directory
            new_path = "/".join(path_parts[:-1])
            st.session_state.current_path = f"/{new_path}" if new_path else "/"
            st.experimental_rerun()
    
    # Show current path
    st.markdown(f"**Current Path:** `{current_path}`")
    
    # Add directory creation and file upload in current directory
    with st.expander("➕ Add New Content", expanded=False):
        col1, col2 = st.columns(2)
        
        # Directory creation
        with col1:
            st.markdown("### Create Directory")
            new_dir_name = st.text_input("Directory Name", key="new_dir_name")
            if st.button("Create Directory"):
                if new_dir_name:
                    new_dir_path = f"{current_path.rstrip('/')}/{new_dir_name}"
                    # Create an empty file to mark directory existence
                    try:
                        client.upload_file_from_bytes(b"", f"{new_dir_path}/.gfs_dir")
                        st.success(f"Created directory: {new_dir_name}")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Failed to create directory: {str(e)}")
        
        # File upload in current directory
        with col2:
            st.markdown("### Upload File")
            uploaded_file = st.file_uploader("Choose a file", key=f"uploader_{current_path}")
            if uploaded_file:
                file_path = f"{current_path.rstrip('/')}/{uploaded_file.name}"
                if st.button("Upload Here"):
                    try:
                        # Save uploaded file temporarily
                        temp_path = f"temp_{uploaded_file.name}"
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                        # Upload to GFS
                        client.upload_file(temp_path, file_path)
                        os.remove(temp_path)
                        st.success("File uploaded successfully!")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Upload failed: {str(e)}")
                        logger.error(f"Upload failed: {e}", exc_info=True)
                    finally:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
    
    # Get current directory content
    current_dir = dir_structure
    for part in path_parts:
        if part:
            current_dir = current_dir.get(part, {})
    
    # Display directories
    dirs = [k for k in current_dir.keys() if k != 'files']
    if dirs:
        st.markdown("### 📁 Directories")
        cols = st.columns(3)
        for i, dir_name in enumerate(sorted(dirs)):
            with cols[i % 3]:
                if st.button(f"📁 {dir_name}", key=f"dir_{dir_name}"):
                    new_path = f"{current_path.rstrip('/')}/{dir_name}"
                    st.session_state.current_path = new_path
                    st.experimental_rerun()
    
    # Display files (excluding .gfs_dir markers)
    files = [f for f in current_dir.get('files', []) if not f.endswith('.gfs_dir')]
    if files:
        st.markdown("### 📄 Files")
        for file_path in sorted(files):
            filename = os.path.basename(file_path)
            
            # Create expandable section for each file
            with st.expander(f"📄 {filename}"):
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    if st.button("⬇️ Download", key=f"download_{file_path}"):
                        try:
                            # Download file
                            local_path = f"downloaded_{filename}"
                            client.download_file(file_path, local_path)
                            
                            # Provide download link
                            with open(local_path, "rb") as f:
                                st.download_button(
                                    label="Click to Save",
                                    data=f.read(),
                                    file_name=filename,
                                    key=f"save_{file_path}"
                                )
                            os.remove(local_path)
                        except Exception as e:
                            st.error(f"Download failed: {str(e)}")
                            logger.error(f"Download failed: {e}", exc_info=True)
                
                # Add preview button for text files
                if is_text_file(filename):
                    with col2:
                        if st.button("👁️ Preview", key=f"preview_{file_path}"):
                            try:
                                # Download file temporarily
                                local_path = f"temp_preview_{filename}"
                                client.download_file(file_path, local_path)
                                
                                # Read and display content
                                with open(local_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    
                                # Display file content in a code block with syntax highlighting
                                extension = os.path.splitext(filename)[1][1:]  # Remove the dot
                                st.code(content, language=extension if extension else None)
                                
                                # Cleanup
                                os.remove(local_path)
                            except UnicodeDecodeError:
                                st.error("Unable to preview: File contains binary content")
                            except Exception as e:
                                st.error(f"Preview failed: {str(e)}")
                                logger.error(f"Preview failed: {e}", exc_info=True)

def main():
    logger.info("Starting GFS web interface")
    st.title("Google File System (GFS) Interface")

    # Initialize client with location coordinates from environment
    client_id = os.environ.get('GFS_CLIENT_ID')
    x = float(os.environ.get('GFS_CLIENT_X', 0.0))
    y = float(os.environ.get('GFS_CLIENT_Y', 0.0))
    
    logger.debug("Initializing GFS client")
    client = GFSClient("configs/config.toml", client_id=client_id, x=x, y=y)
    
    # Display client information
    st.sidebar.markdown(f"""
    **Client Information**
    - ID: {client_id or 'Default'}
    - Location: ({x}, {y})
    """)

    # Initialize session state for current path if not exists
    if 'current_path' not in st.session_state:
        st.session_state.current_path = "/"

    # Sidebar for operations
    operation = st.sidebar.selectbox(
        "Select Operation",
        ["File Explorer", "Upload File", "Append to File", "Network Graph"]
    )
    logger.debug(f"Selected operation: {operation}")

    # Add auto-refresh checkbox in sidebar
    auto_refresh = st.sidebar.checkbox("Auto-refresh Network Graph", value=False)
    
    if operation == "File Explorer":
        create_file_explorer(client, st.session_state.current_path)
        
    elif operation == "Network Graph":
        st.header("GFS Network Graph")
        
        # Add toggle for space usage visualization
        show_space_usage = st.checkbox("Show Space Usage", value=False)
        
        try:
            # Get graph data from master
            with client._connect_to_master() as master_sock:
                send_message(master_sock, {'command': 'get_graph_data'})
                response = receive_message(master_sock)
                
                if response['status'] == 'ok':
                    graph_data = response['graph_data']
                    
                    # Create and display graph with space usage toggle
                    fig = create_network_graph(graph_data, show_space_usage)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Display statistics
                    st.markdown("### Network Statistics")
                    chunk_servers = sum(1 for node in graph_data['nodes'] if node['type'] == 'chunk_server')
                    clients = sum(1 for node in graph_data['nodes'] if node['type'] == 'client')
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            "Active Chunk Servers",
                            chunk_servers,
                            delta=None,
                            delta_color="normal"
                        )
                    with col2:
                        st.metric(
                            "Connected Clients",
                            clients,
                            delta=None,
                            delta_color="normal"
                        )
                    
                    # Auto-refresh
                    if auto_refresh:
                        time.sleep(5)
                        st.experimental_rerun()
                else:
                    st.error(f"Failed to get graph data: {response.get('message')}")
                    
        except Exception as e:
            st.error(f"Failed to connect to master server: {str(e)}")
            logger.error("Failed to get graph data", exc_info=True)

    elif operation == "Upload File":
        st.header("Upload File")
        uploaded_file = st.file_uploader("Choose a file")
        
        # Use current path from file explorer
        current_path = st.session_state.current_path
        gfs_path = st.text_input("GFS Path", 
                                value=f"{current_path.rstrip('/')}/")

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