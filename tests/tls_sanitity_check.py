import ssl
import socket

context = ssl.create_default_context()
with socket.create_connection(("a5c9d1ea0e224376ad6285eb8aa83d55.s1.eu.hivemq.cloud", 8883)) as sock:
    with context.wrap_socket(sock, server_hostname="a5c9d1ea0e224376ad6285eb8aa83d55.s1.eu.hivemq.cloud") as ssock:
        print(ssock.version())
