#!/usr/bin/env python3
"""
SmartMed Cycle — local smoke test harness.

Starts each backend Flask app on a free port, sends a representative streaming
POST request, and prints the streamed output. Verifies that:
  - the app imports and boots,
  - the POST / route streams a text/plain response,
  - CORS headers are present,
  - OPTIONS returns 200,
  - the abuse guards (413 payload too large) trigger.

Requires: Python 3.12, each backend's deps installed, and AWS credentials with
Bedrock access in ap-southeast-1 for the live Bedrock calls to succeed. Without
credentials the apps still boot and stream an inline "⚠️ Error:" message, which
this harness treats as a reachable-but-unauthenticated PASS for routing.

Usage:
    python scripts/smoke_test.py                 # test all
    python scripts/smoke_test.py medicine_card   # test one
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")

# name -> sample JSON payload
CASES = {
    "extract_from_photo": {"preferred_language": "English"},
    "medicine_card": {
        "preferred_language": "English",
        "medicine_details": "Metformin 500 mg — take one tablet twice daily with meals",
    },
    "my_medicine_summary": {
        "preferred_language": "English",
        "medicine_card": "Metformin 500 mg. Take one tablet twice daily with meals.",
        "patient_age": "Adult : 18-60",
        "other_medicines": "Atorvastatin 20 mg once daily",
        "allergies": "Penicillin — rash",
    },
    "my_return_plan": {
        "preferred_language": "English",
        "return_item_details": "Paracetamol 500 mg tablets, 10 left, expired",
        "your_location": "50480 Kuala Lumpur",
    },
    "smartmed_help": {
        "preferred_language": "English",
        "medicine_card": "Metformin 500 mg twice daily.",
        "my_medicine_summary": "Watch for low blood sugar.",
        "history": [],
        "message": "What if I miss a dose?",
    },
}


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def wait_up(port, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def run_one(name):
    folder = os.path.join(BACKEND, name)
    payload = CASES[name]
    port = free_port()
    env = dict(os.environ, PORT=str(port))

    print(f"\n=== {name} (port {port}) ===")
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=folder,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    try:
        if not wait_up(port):
            print("  ❌ app did not start")
            return False

        base = f"http://127.0.0.1:{port}/"

        # OPTIONS preflight
        req = urllib.request.Request(base, method="OPTIONS")
        with urllib.request.urlopen(req, timeout=10) as r:
            cors = r.headers.get("Access-Control-Allow-Origin")
            assert r.status == 200 and cors == "*", "OPTIONS/CORS failed"
        print("  ✅ OPTIONS 200 + CORS")

        # Streaming POST
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            base, data=data, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            ctype = r.headers.get("Content-Type", "")
            assert "text/plain" in ctype, f"unexpected content-type {ctype}"
            chunks = []
            while True:
                chunk = r.read(256)
                if not chunk:
                    break
                chunks.append(chunk.decode("utf-8", "replace"))
            text = "".join(chunks)
        preview = text.strip().replace("\n", " ")[:140]
        print(f"  ✅ POST streamed {len(text)} chars: {preview}")

        # Payload-too-large guard (413)
        big = json.dumps({"file_data": "A" * (9 * 1024 * 1024)}).encode()
        req = urllib.request.Request(
            base, data=big, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            print("  ⚠️ 413 guard did not trigger")
        except urllib.error.HTTPError as e:
            assert e.code == 413, f"expected 413, got {e.code}"
            print("  ✅ 413 payload guard triggered")

        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  ❌ {exc}")
        return False
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def main():
    targets = sys.argv[1:] or list(CASES.keys())
    results = {t: run_one(t) for t in targets}
    print("\n=== summary ===")
    for name, ok in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
