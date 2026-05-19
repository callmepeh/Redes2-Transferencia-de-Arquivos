import subprocess

for i in range(10):
    subprocess.run([
        "python3",
        "client/tcp_client.py"
    ])