"""Launch a temporary loopback API and verify real HTTP model integration."""
import os
import socket
import subprocess
import sys
import time

import httpx

from ml.common import ARTIFACTS, ROOT, write_json


def main():
    with socket.socket() as address:
        address.bind(("127.0.0.1",0))
        port = address.getsockname()[1]
    ARTIFACTS.mkdir(exist_ok=True)
    environment = {**os.environ,"ML_PROVIDER":"local","INTENT_PROVIDER":"distilbert"}
    with (ARTIFACTS / "local_api.log").open("w",encoding="utf-8") as log:
        process = subprocess.Popen([sys.executable,"-m","uvicorn","app.main:app","--app-dir","api",
            "--host","127.0.0.1","--port",str(port)],cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT)
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}",timeout=30) as client:
                for _ in range(60):
                    try:
                        response = client.get("/health")
                        if response.status_code==200:
                            break
                    except httpx.ConnectError:
                        pass
                    if process.poll() is not None:
                        raise RuntimeError("API exited; inspect artifacts/local_api.log")
                    time.sleep(0.5)
                else:
                    raise RuntimeError("API did not become ready within 30 seconds")
                chat = client.post("/chat",json={"customer_id":"C-204","question":"Draft a renewal reminder for C-204"})
                chat.raise_for_status()
                assert chat.json()["intent"]=="renewal_draft"
                worklist = client.get("/worklist?limit=10")
                worklist.raise_for_status()
                assert len(worklist.json()["items"])==10
                write_json(ARTIFACTS / "local_api_smoke.json",{"status":"passed","transport":"real loopback HTTP",
                    "intent_provider":"distilbert","radar_provider":"local","chat_intent":chat.json()["intent"],
                    "worklist_count":len(worklist.json()["items"]),"synthetic":True,
                    "scope":"ML integration only; chat answer/citations remain placeholders; not full-product acceptance"})
                print("Real HTTP API smoke passed: DistilBERT intent and 10 Radar entries")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
