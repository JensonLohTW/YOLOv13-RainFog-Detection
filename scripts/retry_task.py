"""Retry the existing detection task and print the result."""
import json
import sys
import urllib.request

BASE = "http://localhost:8000"

data = json.dumps({"username": "admin", "password": "admin123"}).encode()
req = urllib.request.Request(BASE + "/api/v1/auth/login", data=data, headers={"Content-Type": "application/json"})
token = json.loads(urllib.request.urlopen(req).read())["data"]["token"]
AUTH = {"Authorization": "Token " + token, "Content-Type": "application/json"}

print("Logged in OK")

req = urllib.request.Request(
    BASE + "/api/v1/detection/tasks/DT202603311045264AB116/retry",
    data=b"{}",
    headers=AUTH,
)
try:
    result = json.loads(urllib.request.urlopen(req).read())
    rec = result["data"].get("latest_record", {})
    print("status:", result["data"]["status"])
    print("is_mock:", rec.get("is_mock"))
    print("engine_type:", rec.get("engine_type"))
    print("result_image_url:", rec.get("result_image_url"))
    print("object_count:", rec.get("object_count"))
except urllib.error.HTTPError as e:
    body = e.read().decode()[:800]
    print("HTTP Error", e.code, body, file=sys.stderr)
    sys.exit(1)
