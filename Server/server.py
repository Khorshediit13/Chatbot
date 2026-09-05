import socket
import threading
import datetime
import os

# --- Configuration ---
HOST = 'localhost'
PORT = 12345
MAX_CLIENTS = 5
BUFFER_SIZE = 1024
# Feature: Chat Log File
LOG_FILE = "chat_history.txt"

# --- Shared Resources ---
# CHANGE: Clients is now a dictionary mapping {socket_connection : username_string}
clients = {}
# A lock to ensure thread-safe access to the clients dictionary
clients_lock = threading.Lock()
# Feature: A lock to ensure thread-safe writing to the log file
file_lock = threading.Lock()

# --- Functions ---

def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_to_console(message):
    """Logs a message to the server console with a timestamp."""
    print(f"[{get_timestamp()}] {message}")

def log_to_file(message):
    """
    Feature: Writes a message to the text file persistently.
    Uses a lock to prevent multiple threads writing simultaneously.
    """
    timestamped_message = f"[{get_timestamp()}] {message}"
    try:
        with file_lock:
            # Open file in 'append' mode ('a'), create if it doesn't exist.
            # Use utf-8 encoding to handle various characters.
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(timestamped_message + "\n")
    except Exception as e:
        log_to_console(f"ERROR writing to log file: {e}")

def broadcast(message, sender_conn=None, is_system_msg=False):
    """
    Broadcasts a message to all clients.
    Also logs the broadcasted message to the file.
    """
    # Feature: Log everything that gets broadcasted to the file
    log_to_file(message)
    
    # If it's a system message (like someone joining), log to console too
    if is_system_msg:
        log_to_console(message)

    with clients_lock:
        # Iterate over the keys (sockets) in the dictionary
        for client_conn in clients.keys():
            # Send to everyone *except* the sender (if a sender exists)
            if client_conn != sender_conn:
                try:
                    client_conn.sendall(message.encode())
                except socket.error:
                    # Client likely disconnected unexpectedly; cleanup happens in handle_client
                    pass

def handle_client(conn, addr):
    """
    This function runs in a separate thread for each client.
    Handles initial username registration and subsequent messaging.
    """
    ip_address = f"{addr[0]}:{addr[1]}"
    log_to_console(f"NEW CONNECTION attempt from: {ip_address}")

    username = None

    try:
        # --- Feature: Username Registration ---
        # The first message received MUST be the username.
        # Set a temporary timeout so a connection doesn't hang forever waiting for a name
        conn.settimeout(10) 
        try:
            initial_msg = conn.recv(BUFFER_SIZE).decode().strip()
            conn.settimeout(None) # Remove timeout after successful receive

            if not initial_msg:
                raise ConnectionResetError("Empty username received")
            
            username = initial_msg
            
            # Add client and username to dictionary thread-safely
            with clients_lock:
                clients[conn] = username

            join_msg = f"[SERVER] {username} has joined the chat."
            # Broadcast join message and log it
            broadcast(join_msg, sender_conn=conn, is_system_msg=True)

        except socket.timeout:
             log_to_console(f"TIMEOUT: {ip_address} did not send a username in time.")
             conn.close()
             return

        # --- Main Chat Loop ---
        while True:
            try:
                msg = conn.recv(BUFFER_SIZE).decode()
            except ConnectionResetError:
                break # Client disconnected abruptly

            if not msg:
                 # Empty message means graceful disconnect
                break
            
            if msg.strip().lower() == 'exit':
                break

            # Log to console who sent a message
            log_to_console(f"Message from {username} ({ip_address}): {msg}")
            
            # Feature: Format message with Username
            formatted_msg = f"<{username}>: {msg}"
            
            # Broadcast to others (this also handles file logging)
            broadcast(formatted_msg, sender_conn=conn)

    except Exception as e:
        log_to_console(f"ERROR with client {ip_address}: {e}")
    
    finally:
        # --- Cleanup ---
        conn.close()
        
        leaving_username = None
        with clients_lock:
            # Check if they successfully registered before trying to remove
            if conn in clients:
                leaving_username = clients[conn]
                del clients[conn]
        
        # Only broadcast departure if they had successfully joined
        if leaving_username:
            leave_msg = f"[SERVER] {leaving_username} has left the chat."
            broadcast(leave_msg, is_system_msg=True)
        else:
             log_to_console(f"DISCONNECT: Unregistered connection {ip_address} closed.")

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((HOST, PORT))
        server.listen(MAX_CLIENTS)
        log_to_console(f"Server started on {HOST}:{PORT}")
        log_to_console(f"Chat history will be saved to: {os.path.abspath(LOG_FILE)}")
    except socket.error as e:
        log_to_console(f"Failed to bind/listen: {e}")
        return

    try:
        while True:
            conn, addr = server.accept()
            # Start thread, passing connection and address
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.daemon = True
            client_thread.start()

    except KeyboardInterrupt:
        log_to_console("\nSERVER SHUTDOWN: Keyboard interrupt.")
    finally:
        log_to_console("Closing server socket...")
        server.close()

if __name__ == "__main__":
    # Create the log file immediately if it doesn't exist
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
             f.write(f"--- Chat Log Started: {get_timestamp()} ---\n")
             
    start_server()