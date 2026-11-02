import urllib.request
import json
import subprocess
import time
import sys

print("Starting Uvicorn backend process...")
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

try:
    time.sleep(2)
    print("Sending GET http://127.0.0.1:8000/health ...")
    req = urllib.request.Request("http://127.0.0.1:8000/health")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
        print(f"Status Code: {resp.status}")
        print(f"Response: {data}")
        assert resp.status == 200
        assert data.get("status") == "healthy"
        print("Backend test PASSED!")
finally:
    proc.terminate()
    proc.wait()
    print("Uvicorn backend stopped.")

