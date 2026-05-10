import subprocess, time, socket, os, json, urllib.request

API = "http://localhost:8483"
NOTE_DIR = "C:/Users/Administrator/Desktop/BiliNote/backend/note_results"
LOG_PATH = "C:/Users/Administrator/Desktop/BiliNote/backend/logs/app.log"
STDERR_PATH = "C:/Users/Administrator/Desktop/BiliNote/backend/backend_stderr.log"
WORK_DIR = "C:/Users/Administrator/Desktop/BiliNote/backend"

# Clean stale note_result files
for f in os.listdir(NOTE_DIR):
    if f.endswith(".status.json"):
        os.remove(os.path.join(NOTE_DIR, f))

# Start backend fresh
os.chdir(WORK_DIR)
log_f = open(STDERR_PATH, "w", buffering=1)
proc = subprocess.Popen(
    ["C:/Users/Administrator/.venv/bili/Scripts/python.exe", "main.py"],
    stdout=subprocess.DEVNULL, stderr=log_f
)
print(f"Backend PID={proc.pid}")

# Wait for startup
for _ in range(30):
    if proc.poll() is not None:
        with open(STDERR_PATH) as f:
            err = f.read()
        print("Backend CRASHED on startup:")
        print(err[-500:])
        exit(1)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if s.connect_ex(("127.0.0.1", 8483)) == 0:
        s.close()
        break
    s.close()
    time.sleep(1)
else:
    print("Backend failed to start")
    exit(1)
print("Backend ready!\n")

# Submit both tasks
TASKS = [
    {"video_url": "https://www.bilibili.com/cheese/play/ep1851542", "platform": "bilibili",
     "quality": "fast", "model_name": "deepseek-v4-flash", "provider_id": "deepseek",
     "video_understanding": False, "screenshot": False},
    {"video_url": "https://www.bilibili.com/cheese/play/ep1851543", "platform": "bilibili",
     "quality": "fast", "model_name": "deepseek-v4-flash", "provider_id": "deepseek",
     "video_understanding": False, "screenshot": False},
]

task_ids = []
for t in TASKS:
    req = urllib.request.Request(f"{API}/api/generate_note", data=json.dumps(t).encode(),
                                  headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())
    tid = data["data"]["task_id"]
    title = t["video_url"].split("/")[-1]
    task_ids.append(tid)
    print(f"Submitted {title}: {tid}")

# Poll with backend health check
start = time.time()
last_log_size = 0
while task_ids:
    # Check if backend died
    if proc.poll() is not None:
        print(f"\n*** BACKEND DIED (code={proc.returncode}) ***")
        with open(STDERR_PATH) as f:
            err = f.read()
        if err.strip():
            print("STDERR:", err[-300:])
        with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            print("LOG TAIL:")
            for l in lines[-8:]:
                print(" ", l.strip()[:150])
        break

    completed = []
    for tid in task_ids:
        try:
            resp = urllib.request.urlopen(f"{API}/api/task_status/{tid}", timeout=10)
            data = json.loads(resp.read()).get("data", {})
            status = data.get("status", "UNKNOWN")
            elapsed = int(time.time() - start)
            msg = data.get("message", "")
            print(f"  [{elapsed}s] {tid[:8]}... {status}" + (f"  ({msg[:80]})" if msg else ""))
            if status in ("SUCCESS", "FAILED"):
                completed.append(tid)
        except Exception as e:
            print(f"  [{int(time.time()-start)}s] {tid[:8]}... ERROR: {e}")
    for tid in completed:
        task_ids.remove(tid)
    if task_ids:
        time.sleep(15)

total = int(time.time() - start)
print(f"\n{'='*50}")
print(f"Total time: {total}s")
if task_ids:
    print(f"Unfinished: {task_ids}")
print(f"{'='*50}")
