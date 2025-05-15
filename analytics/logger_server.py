# logger_server.py
from fastapi import FastAPI, Request
from pathlib import Path
import json, uvicorn

BASE = Path(__file__).parent
LOG  = BASE / "logs" / "events.jsonl"
LOG.parent.mkdir(exist_ok=True)

app = FastAPI()

@app.post("/event")
async def ingest(req: Request):
    data = await req.json()
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False) + "\n")
    return {"ok": True}

# optional tiny health-check
@app.get("/ping")
def ping():
    return {"status": "alive"}

if __name__ == "__main__":
    uvicorn.run("logger_server:app", host="127.0.0.1", port=5000, reload=False)
    