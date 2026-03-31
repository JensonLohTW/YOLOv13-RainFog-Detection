"""End-to-end test: login → upload image → create detection task → poll result."""
import json
import time
import urllib.request
from pathlib import Path

BASE = "http://localhost:8000"
IMG = Path(r"C:\Users\Administrator\Downloads\YOLOv13-RainFog-Detection\data\demo_output\rain_storm-001\1_original.jpg")


def api(path, data=None, headers=None, method=None):
    h = headers or {}
    body = json.dumps(data).encode() if data and isinstance(data, dict) else data
    if isinstance(body, bytes) and "Content-Type" not in h:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=body, headers=h, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print("HTTP Error", e.code, e.read().decode()[:500])
        raise


# 1. Login
print("=== 1. Login ===")
result = api("/api/v1/auth/login", {"username": "admin", "password": "admin123"})
token = result["data"]["token"]
AUTH = {"Authorization": "Token " + token}
print("OK — token:", token[:20] + "...")

# 2. Upload image
print("\n=== 2. Upload image ===")
boundary = "----TestBoundary12345"
CRLF = b"\r\n"
img_bytes = IMG.read_bytes()
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="image"; filename="{IMG.name}"\r\n'
    f"Content-Type: image/jpeg\r\n\r\n"
).encode() + img_bytes + f"\r\n--{boundary}--\r\n".encode()

headers = dict(AUTH)
headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
result = api("/api/v1/images/upload", data=body, headers=headers)
print("Upload result:", json.dumps(result, indent=2)[:400])
image_id = result["data"]["id"]
print("Image ID:", image_id)

# 3. Create detection task
print("\n=== 3. Create detection task ===")
headers = dict(AUTH)
headers["Content-Type"] = "application/json"
result = api("/api/v1/detection/tasks", {"image_id": image_id}, headers=headers)
print("Task created:", json.dumps(result, indent=2)[:400])
task_no = result["data"]["task_no"]
print("Task No:", task_no)

# 4. Poll until done
print("\n=== 4. Poll task status ===")
for i in range(30):
    time.sleep(3)
    result = api(f"/api/v1/detection/tasks/{task_no}", headers=AUTH)
    status = result["data"]["status"]
    print(f"  [{i+1}] status={status}")
    if status in ("completed", "failed"):
        break

print("\n=== Final result ===")
print(json.dumps(result["data"], indent=2)[:1000])
