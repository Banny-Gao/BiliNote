import os, time, subprocess

# Check python process
result = subprocess.run('tasklist //FI "IMAGENAME eq python.exe" //FO CSV', capture_output=True, text=True, timeout=10, shell=True)
print("=== Python processes ===")
print(result.stdout[:800])

# Check log
log_path = os.path.join(os.path.dirname(__file__), "logs", "app.log")
if os.path.exists(log_path):
    size = os.path.getsize(log_path)
    mtime = time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(log_path)))
    print(f"\nLog file: {size} bytes, last modified: {mtime}")
    # tail last 5 lines
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
        for l in lines[-5:]:
            print(l.rstrip())
else:
    print("\nNo log file")

# Check status files
note_dir = os.path.join(os.path.dirname(__file__), "note_results")
for tid in ["a851ef9d-98bd-47da-b992-8b9a2e8c2e1f", "bd01d02e-c503-485c-9147-174f5f6ecde8"]:
    spath = os.path.join(note_dir, f"{tid}.status.json")
    if os.path.exists(spath):
        mtime = time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(spath)))
        with open(spath) as f:
            status = f.read().strip()
        print(f"\n{tid[:8]}... status: {status}, modified: {mtime}")

# Check audio files
data_dir = os.path.join(os.path.dirname(__file__), "data", "data")
for mp3 in ["1851542.mp3", "1851543.mp3"]:
    path = os.path.join(data_dir, mp3)
    if os.path.exists(path):
        mtime = time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(path)))
        size = os.path.getsize(path)
        print(f"{mp3}: {size} bytes, modified: {mtime}")
