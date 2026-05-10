import subprocess, time, socket, os, sys

os.chdir("C:/Users/Administrator/Desktop/BiliNote/backend")

proc = subprocess.Popen(
    ["C:/Users/Administrator/.venv/bili/Scripts/python.exe", "main.py"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
)

# Wait for startup
for _ in range(30):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    r = s.connect_ex(("127.0.0.1", 8483))
    s.close()
    if r == 0:
        print("Backend started, PID:", proc.pid)
        break
    time.sleep(1)
else:
    print("Failed to start")
    print(proc.stdout.read()[:500])
