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

    # Sidebar for operations
    operation = st.sidebar.selectbox(
        "Select Operation",
        ["Upload File", "Download File", "List Files", "Append to File", "Network Graph"]
    )
    logger.debug(f"Selected operation: {operation}")

    # Add auto-refresh checkbox in sidebar
    auto_refresh = st.sidebar.checkbox("Auto-refresh Network Graph", value=False)
    
    if operation == "Network Graph":
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