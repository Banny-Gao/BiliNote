import urllib.request, json, time, sys, os

API = "http://localhost:8483"

TASKS = [
    {
        "video_url": "https://www.bilibili.com/cheese/play/ep1851542",
        "platform": "bilibili",
        "quality": "fast",
        "model_name": "deepseek-v4-flash",
        "provider_id": "deepseek",
        "video_understanding": False,
        "screenshot": False,
    },
    {
        "video_url": "https://www.bilibili.com/cheese/play/ep1851543",
        "platform": "bilibili",
        "quality": "fast",
        "model_name": "deepseek-v4-flash",
        "provider_id": "deepseek",
        "video_understanding": False,
        "screenshot": False,
    },
]

def api_post(path, data):
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=30)
    return json.loads(resp.read())

def api_get(path):
    resp = urllib.request.urlopen(f"{API}{path}", timeout=10)
    return json.loads(resp.read())

# Submit tasks
task_ids = []
for t in TASKS:
    result = api_post("/api/generate_note", t)
    tid = result["data"]["task_id"]
    task_ids.append(tid)
    title = t["video_url"].split("/")[-1]
    print(f"Submitted {title}: task_id={tid}")

print(f"\nPolling tasks every 15 seconds...")
start = time.time()

while task_ids:
    completed = []
    for tid in task_ids:
        result = api_get(f"/api/task_status/{tid}")
        data = result.get("data", {})
        status = data.get("status", "UNKNOWN")
        elapsed = int(time.time() - start)
        print(f"  [{elapsed}s] {tid[:8]}... status={status}", end="")
        if data.get("message"):
            print(f" msg={data['message'][:80]}", end="")
        print()
        if status in ("SUCCESS", "FAILED"):
            completed.append(tid)
    for tid in completed:
        task_ids.remove(tid)
    if task_ids:
        time.sleep(15)

print(f"\nAll done in {int(time.time() - start)}s!")
