import socket

HOST = "127.0.0.1"
PORT = 5000

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


client.bind((HOST, PORT))
client.listen(1)

conn, addr = client.accept()

with open("arquivo.txt", "rb") as f:
    while True:
        chunk = f.read(1024)

        if not chunk:
            break

        conn.sendall(chunk)

print("Arquivo enviado com sucesso!")

conn.close()
client.close()  
