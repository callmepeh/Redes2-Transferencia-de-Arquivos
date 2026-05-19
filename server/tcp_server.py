import socket 

HOST = '0.0.0.0'
PORT = 5000

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


server.bind((HOST, PORT))
server.listen(1)

print(f"Servidro TCP ouvindo em {PORT}")

conn, addr = server.accept()

print(f"Conexão recebida de {addr}")


with open("recebido.txt", "wb") as f:
    while True:
        data = conn.recv(1024)

        if not data:
            break

        f.write(data)

print("Arquivo recebido com sucesso!")

conn.close()
server.close()  