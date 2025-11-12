import socket
import threading
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox
import json


class ChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("LAN Chat Client")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)

        self.sock = None
        self.running = False
        self.username = ""
        self.room = ""

        # Set color scheme
        self.bg_color = "#f0f0f0"
        self.root.configure(bg=self.bg_color)

        # Create UI
        self.create_widgets()

        # Connect to server
        connected = self.connect_to_server()

        # Handle window close (only if connection was successful)
        if connected:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # Header frame
        header_frame = tk.Frame(self.root, bg="#2c3e50", height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        # Title label
        title_label = tk.Label(
            header_frame,
            text="💬 LAN Chat",
            font=("Arial", 16, "bold"),
            bg="#2c3e50",
            fg="white",
        )
        title_label.pack(side=tk.LEFT, padx=15, pady=10)

        # Info label
        self.info_label = tk.Label(
            header_frame,
            text="Not connected",
            font=("Arial", 10),
            bg="#2c3e50",
            fg="#ecf0f1",
        )
        self.info_label.pack(side=tk.RIGHT, padx=15, pady=10)

        # Main container
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left sidebar for users/rooms
        sidebar_frame = tk.Frame(
            main_frame, bg="white", relief=tk.RAISED, bd=1, width=150
        )
        sidebar_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        sidebar_frame.pack_propagate(False)

        # Users label
        users_label = tk.Label(
            sidebar_frame, text="👥 Users", font=("Arial", 11, "bold"), bg="white"
        )
        users_label.pack(padx=5, pady=(10, 5))

        # Users listbox
        self.users_listbox = tk.Listbox(
            sidebar_frame,
            font=("Arial", 9),
            bg="white",
            selectmode=tk.SINGLE,
            height=10,
        )
        self.users_listbox.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        # Chat display area
        chat_frame = tk.Frame(main_frame, bg="white", relief=tk.RAISED, bd=1)
        chat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        chat_label = tk.Label(
            chat_frame, text="💭 Chat Messages", font=("Arial", 11, "bold"), bg="white"
        )
        chat_label.pack(padx=10, pady=(10, 5))

        self.text_area = scrolledtext.ScrolledText(
            chat_frame,
            state="disabled",
            wrap=tk.WORD,
            font=("Courier", 9),
            bg="#fafafa",
            fg="#2c3e50",
        )
        self.text_area.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        # Configure text tags for different message types
        self.text_area.tag_config(
            "system", foreground="#3498db", font=("Courier", 9, "bold")
        )
        self.text_area.tag_config(
            "private", foreground="#e74c3c", font=("Courier", 9, "bold")
        )
        self.text_area.tag_config(
            "timestamp", foreground="#95a5a6", font=("Courier", 8)
        )
        self.text_area.tag_config(
            "sender", foreground="#27ae60", font=("Courier", 9, "bold")
        )

        # Input frame
        input_frame = tk.Frame(self.root, bg=self.bg_color)
        input_frame.pack(fill=tk.X, padx=10, pady=10)

        # Message entry
        self.entry = tk.Entry(
            input_frame, 
            font=("Arial", 12), 
            bg="white",
            fg="black",
            insertbackground="black",
            relief=tk.SOLID, 
            bd=1
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", self.send_msg)
        self.entry.focus()

        # Send button
        send_btn = tk.Button(
            input_frame,
            text="Send",
            command=self.send_msg,
            font=("Arial", 10),
            padx=15,
            pady=5
        )
        send_btn.pack(side=tk.RIGHT, padx=(10, 0))

        # Command button
        cmd_btn = tk.Button(
            input_frame,
            text="Help",
            command=self.show_help,
            font=("Arial", 10),
            padx=15,
            pady=5
        )
        cmd_btn.pack(side=tk.RIGHT, padx=5)

        # Status bar
        self.status_label = tk.Label(
            self.root,
            text="Initializing...",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            bg="#ecf0f1",
            fg="#2c3e50",
            font=("Arial", 9),
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def connect_to_server(self):
        try:
            # Get connection details
            server_ip = simpledialog.askstring(
                "Server Connection", "Enter server IP address (localhost or 127.0.0.1 for local):"
            )
            if not server_ip:
                self.root.destroy()
                return False

            username = simpledialog.askstring("Username", "Enter your username:")
            if not username:
                self.root.destroy()
                return False

            room = simpledialog.askstring("Room", "Enter room name (default: general):")
            if not room:
                room = "general"

            self.username = username
            self.room = room

            # Connect to server
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((server_ip, 3000))

            # Send initial connection data
            payload = {"username": username, "room": room}
            self.sock.sendall((json.dumps(payload) + "\n").encode())

            # Update status
            self.info_label.config(text=f"👤 {username} | 🏠 {room}")
            self.root.title(f"LAN Chat - {username} @ {room}")
            self.status_label.config(text="✓ Connected to server")

            # Start receiving thread
            self.running = True
            receive_thread = threading.Thread(target=self.receive, daemon=True)
            receive_thread.start()

            # Display welcome message
            self.display_message("─" * 60, "system")
            self.display_message(
                "✓ Connected to server! Type /help for available commands.", "system"
            )
            self.display_message("─" * 60, "system")
            
            return True

        except Exception as e:
            messagebox.showerror(
                "Connection Error", f"Could not connect to server:\n{str(e)}"
            )
            self.root.destroy()
            return False

    def receive(self):
        """Receive messages from server"""
        buffer = ""
        while self.running:
            try:
                data = self.sock.recv(1024).decode()
                if not data:
                    break

                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line.strip():
                        continue

                    try:
                        msg = json.loads(line)
                        self.handle_message(msg)
                    except json.JSONDecodeError:
                        continue

            except Exception as e:
                if self.running:
                    self.display_message(f"⚠ Connection lost: {str(e)}", "system")
                break

        if self.running:
            self.display_message("⚠ Disconnected from server", "system")
            self.status_label.config(text="✗ Disconnected")

    def handle_message(self, msg):
        """Handle different types of messages"""
        if msg["type"] == "msg":
            timestamp = msg.get("time", "")
            sender = msg.get("from", "Unknown")
            text = msg.get("msg", "")
            self.display_message(f"[{timestamp}] ", "timestamp", newline=False)
            self.display_message(f"{sender}: ", "sender", newline=False)
            self.display_message(text)

        elif msg["type"] == "system":
            text = msg.get("msg", "")
            timestamp = msg.get("time", "")
            if timestamp:
                self.display_message(f"[{timestamp}] ℹ {text}", "system")
            else:
                self.display_message(f"ℹ {text}", "system")

        elif msg["type"] == "private":
            timestamp = msg.get("time", "")
            sender = msg.get("from", "Unknown")
            text = msg.get("msg", "")
            self.display_message(
                f"[{timestamp}] 🔒 [PM from {sender}] {text}", "private"
            )

    def display_message(self, message, tag=None, newline=True):
        """Display message in text area"""
        self.text_area.config(state="normal")
        if tag:
            self.text_area.insert("end", message + ("\n" if newline else ""), tag)
        else:
            self.text_area.insert("end", message + ("\n" if newline else ""))
        self.text_area.config(state="disabled")
        self.text_area.see("end")

    def send_msg(self, event=None):
        """Send message to server"""
        msg = self.entry.get().strip()
        if not msg:
            return

        self.entry.delete(0, tk.END)

        try:
            if msg.startswith("/"):
                payload = {"type": "command", "cmd": msg}
            else:
                payload = {"type": "msg", "msg": msg}

            self.sock.sendall((json.dumps(payload) + "\n").encode())
        except Exception as e:
            self.display_message(f"⚠ Error sending message: {str(e)}", "system")

    def show_help(self):
        """Show help dialog with available commands"""
        help_text = """
╔════════════════════════════════════════════════╗
║           Available Commands                   ║
╚════════════════════════════════════════════════╝

/users
  └─ Show all users in current room

/allrooms
  └─ Show all active rooms

/join <room_name>
  └─ Switch to a different room

/pm <username> <message>
  └─ Send a private message to a user

/help
  └─ Display this help message

═══════════════════════════════════════════════════

TIPS:
• Press Enter to send messages
• Type commands starting with /
• Private messages are highlighted in red
• System messages are highlighted in blue
        """
        messagebox.showinfo("LAN Chat - Help", help_text)

    def on_closing(self):
        """Handle window closing"""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    ChatClient(root)
    root.mainloop()


if __name__ == "__main__":
    main()
