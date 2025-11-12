import socket
import threading
import json
import datetime
import os

HOST = "0.0.0.0"  # Listen on all network interfaces
PORT = 3000

clients = {}
banned_ips = set()

os.makedirs("chat_logs", exist_ok=True)


def timestamp():
    return datetime.datetime.now().strftime("%H:%M:%S")


def log(room, message):
    """Log messages to room-specific files"""
    filename = f"chat_logs/{room}.txt"
    with open(filename, "a", encoding="utf-8") as f:
        f.write(message + "\n")


def log_global(message):
    """Log global server events"""
    filename = "chat_logs/global.txt"
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp()}] {message}\n")


def broadcast(room, message):
    """Send message to all clients in a specific room"""
    for client, info in list(clients.items()):
        if info["room"] == room:
            try:
                client.sendall((json.dumps(message) + "\n").encode())
            except Exception as e:
                print(f"Error broadcasting to {info['username']}: {e}")


def send_private(sender_sock, target_user, message):
    """Send private message to a specific user"""
    for client, info in list(clients.items()):
        if info["username"] == target_user:
            payload = {
                "type": "private",
                "from": clients[sender_sock]["username"],
                "msg": message,
                "time": timestamp(),
            }
            try:
                client.sendall((json.dumps(payload) + "\n").encode())
                return True
            except:
                return False
    return False


def handle_client(sock, addr):
    username = None
    room = None

    try:
        # Receive initial connection data
        data = sock.recv(1024).decode().strip()
        hello = json.loads(data)
        username = hello["username"]
        room = hello["room"]

        # Register client
        clients[sock] = {"username": username, "room": room, "addr": addr}

        log(room, f"[{timestamp()}] {username} joined {room}")
        log_global(f"{username} ({addr[0]}) joined {room}")
        broadcast(
            room,
            {
                "type": "system",
                "msg": f"{username} joined the room",
                "time": timestamp(),
            },
        )

        # Main message loop
        while True:
            raw = sock.recv(1024).decode().strip()
            if not raw:
                break

            for line in raw.split("\n"):
                if not line.strip():
                    continue

                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if msg["type"] == "msg":
                    final = {
                        "type": "msg",
                        "from": username,
                        "msg": msg["msg"],
                        "time": timestamp(),
                    }
                    broadcast(room, final)
                    log(room, f"[{final['time']}] {username}: {msg['msg']}")

                elif msg["type"] == "command":
                    parts = msg["cmd"].split()

                    if not parts:
                        continue

                    if parts[0] == "/users":
                        # List all users in current room
                        names = [
                            info["username"]
                            for client, info in clients.items()
                            if info["room"] == room
                        ]
                        sock.sendall(
                            (
                                json.dumps(
                                    {
                                        "type": "system",
                                        "msg": f"Users in {room}: {', '.join(names)}",
                                        "time": timestamp(),
                                    }
                                )
                                + "\n"
                            ).encode()
                        )

                    elif parts[0] == "/allrooms":
                        # List all active rooms
                        rooms_list = list(
                            set([info["room"] for info in clients.values()])
                        )
                        sock.sendall(
                            (
                                json.dumps(
                                    {
                                        "type": "system",
                                        "msg": f"Active rooms: {', '.join(rooms_list)}",
                                        "time": timestamp(),
                                    }
                                )
                                + "\n"
                            ).encode()
                        )

                    elif parts[0] == "/pm" and len(parts) >= 3:
                        target = parts[1]
                        text = " ".join(parts[2:])
                        if send_private(sock, target, text):
                            sock.sendall(
                                (
                                    json.dumps(
                                        {
                                            "type": "system",
                                            "msg": f"PM sent to {target}",
                                            "time": timestamp(),
                                        }
                                    )
                                    + "\n"
                                ).encode()
                            )
                        else:
                            sock.sendall(
                                (
                                    json.dumps(
                                        {
                                            "type": "system",
                                            "msg": f"User {target} not found",
                                            "time": timestamp(),
                                        }
                                    )
                                    + "\n"
                                ).encode()
                            )

                    elif parts[0] == "/join" and len(parts) >= 2:
                        old_room = room
                        new_room = parts[1]

                        # Notify old room
                        broadcast(
                            old_room,
                            {
                                "type": "system",
                                "msg": f"{username} left the room",
                                "time": timestamp(),
                            },
                        )

                        # Update room
                        clients[sock]["room"] = new_room
                        room = new_room

                        # Notify new room
                        broadcast(
                            new_room,
                            {
                                "type": "system",
                                "msg": f"{username} joined the room",
                                "time": timestamp(),
                            },
                        )
                        sock.sendall(
                            (
                                json.dumps(
                                    {
                                        "type": "system",
                                        "msg": f"Joined room: {new_room}",
                                        "time": timestamp(),
                                    }
                                )
                                + "\n"
                            ).encode()
                        )

                        log(old_room, f"[{timestamp()}] {username} left for {new_room}")
                        log(
                            new_room,
                            f"[{timestamp()}] {username} joined from {old_room}",
                        )

                    elif parts[0] == "/help":
                        help_text = "Commands: /users, /allrooms, /pm <user> <msg>, /join <room>, /help"
                        sock.sendall(
                            (
                                json.dumps(
                                    {
                                        "type": "system",
                                        "msg": help_text,
                                        "time": timestamp(),
                                    }
                                )
                                + "\n"
                            ).encode()
                        )

    except Exception as e:
        print(f"Error handling client {username or addr}: {e}")

    finally:
        # Clean up on disconnect
        if sock in clients:
            username = clients[sock]["username"]
            room = clients[sock]["room"]
            del clients[sock]
            broadcast(
                room,
                {
                    "type": "system",
                    "msg": f"{username} left the room",
                    "time": timestamp(),
                },
            )
            log(room, f"[{timestamp()}] {username} left {room}")
            log_global(f"{username} disconnected")

        try:
            sock.close()
        except:
            pass


def start_server():
    print(f"Starting LAN Chat Server on {HOST}:{PORT}")
    log_global("Server started")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(100)

    print("Server is running. Waiting for connections...")
    print(
        f"Clients should connect to: {socket.gethostbyname(socket.gethostname())}:{PORT}"
    )

    try:
        while True:
            client_sock, addr = server.accept()
            print(f"New connection from {addr[0]}:{addr[1]}")

            # Check if IP is banned
            if addr[0] in banned_ips:
                try:
                    client_sock.sendall(
                        (
                            json.dumps(
                                {
                                    "type": "system",
                                    "msg": "Your IP is banned.",
                                    "time": timestamp(),
                                }
                            )
                            + "\n"
                        ).encode()
                    )
                    client_sock.close()
                except:
                    pass
                continue

            # Start new thread for client
            t = threading.Thread(
                target=handle_client, args=(client_sock, addr), daemon=True
            )
            t.start()

    except KeyboardInterrupt:
        print("\nShutting down server...")
        log_global("Server stopped")
    finally:
        server.close()


if __name__ == "__main__":
    start_server()
