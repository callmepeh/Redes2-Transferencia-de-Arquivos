import socket 

HOST = '0.0.0.0'
PORT = 5000

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Permite reutilizar a porta imediatamente após reiniciar o servidor
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

server.bind((HOST, PORT))
server.listen(1)

print(f"Servidor TCP ouvindo em {PORT}")

try:
    while True:
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
except KeyboardInterrupt:
    print("\nServidor encerrado pelo usuário.")
finally:
    server.close()