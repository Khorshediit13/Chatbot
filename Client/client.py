import socket
import threading
import sys

# --- Configuration ---
HOST = 'localhost'
PORT = 12345
BUFFER_SIZE = 1024

def receive_messages(sock):
    """
    This function runs in a separate thread and continuously
    listens for messages from the server.
    """
    while True:
        try:
            # Receive a message from the server
            response = sock.recv(BUFFER_SIZE).decode()
            
            if not response:
                # Server has disconnected
                print("\n[Connection to server lost. Press Enter to exit.]")
                break
            
            # Print the server's message.
            # We use \r to move the cursor to the start of the line
            # and 'end=""' to prevent an extra newline.
            # This makes the incoming message appear *above* the "You: " prompt.
            print(f"\r{response}\nYou: ", end="")

        except (ConnectionResetError, ConnectionAbortedError):
            print("\n[Disconnected from server.]")
            break
        except Exception as e:
            print(f"\n[An error occurred: {e}. Closing connection.]")
            break
    sock.close()

def start_client():
    """
    Initializes and starts the client.
    """
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        client.connect((HOST, PORT))
        print(f"Connected to the server at {HOST}:{PORT}.")
    except socket.error as e:
        print(f"Failed to connect to server: {e}")
        return

    # --- Feature: Username ---
    # Immediately after connecting, ask for and send the username.
    while True:
        username = input("Enter your username: ").strip()
        if username:
             # Send username as the first message
            client.sendall(username.encode())
            break
        print("Username cannot be empty.")

    print("--- Chat Joined. Type 'exit' to quit. ---")

    # Start a separate thread to handle *receiving* messages
    recv_thread = threading.Thread(target=receive_messages, args=(client,))
    recv_thread.daemon = True
    recv_thread.start()

    # This is the *main* thread, handling *sending* messages
    try:
        while True:
            # Wait for the user to type a message
            msg = input("You: ")
            
            if not client.fileno() == -1: # Check if socket is still open
                 client.sendall(msg.encode())
            else:
                 break
            
            # If the user types 'exit', break the loop
            if msg.lower() == 'exit':
                break
                
    except KeyboardInterrupt:
        print("\n[Disconnecting by user request...]")
    except BrokenPipeError:
         print("\n[Server closed connection]")
    except Exception as e:
        print(f"\n[An error occurred while sending: {e}]")
    finally:
        client.close()
        print("Exited.")

# --- Main Execution ---
if __name__ == "__main__":
    start_client()