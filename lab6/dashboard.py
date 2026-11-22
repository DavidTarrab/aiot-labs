"""Run the handout's four checkpoints independently in a local dashboard."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import threading
import time
from urllib.request import urlopen

from har_common import LABELS, append_jsonl
from lab_status import completed_hardware, lines, pending_evidence

ROOT = Path(os.environ.get("LAB6_ROOT", Path(__file__).resolve().parent)).resolve()
LOCK = threading.Lock()
DEVICE_LOCK = threading.Lock()
ACTIONS = {"uci": "1", "capture": "2", "storage": "3", "prediction": "4", "restore": "display"}
STATE = {"cloud": None, "checkpoints": {str(i): {"busy": False, "message": "Ready to test"}
                                       for i in range(1, 5)}}
STATE["checkpoints"]["display"] = {"busy": False, "message": "OLED recovery ready"}


def monitor(endpoint):
    while True:
        try:
            with urlopen(endpoint + "/", timeout=8) as response:
                result = json.load(response)
        except Exception as error:
            result = {"error": str(error)}
        with LOCK:
            STATE["cloud"] = result
        time.sleep(10)


def set_message(checkpoint, message):
    with LOCK:
        STATE["checkpoints"][checkpoint]["message"] = message


def run_uci_trial():
    # Lazy imports keep hardware/cloud tests independent of the desktop dataset and torch.
    from har_dataset import UCIHARSignals
    from har_gemini import classify
    dataset = UCIHARSignals(ROOT / "data/UCI HAR Dataset", "test")
    index = secrets.randbelow(len(dataset))
    data, _, truth = dataset[index]
    record = {"at": datetime.now(timezone.utc).isoformat(), "index": index, "truth": truth,
              "source": "UCI HAR official test split", "shape": [6, 128]}
    for style in ("cot", "direct"):
        set_message("1", "UCI window %s: requesting %s answer…" % (index, style))
        try:
            record[style] = classify(data, style)
        except Exception as error:
            record[style] = {"label": None, "error": str(error)}
    append_jsonl(ROOT / "results/checkpoint1_demo.jsonl", record)
    return record


def perform(host, action, truth, location):
    checkpoint = ACTIONS[action]
    try:
        if action == "uci":
            result = run_uci_trial()
            message = "Saved window %s. Truth: %s; CoT: %s; direct: %s." % (
                result["index"], result["truth"], result["cot"]["label"], result["direct"]["label"])
            if not all(result[s].get("label") in LABELS for s in ("cot", "direct")):
                message += " A request failed; inspect the outputs below."
        elif action == "restore":
            from har_client import SmartwatchClient
            SmartwatchClient(host, timeout=10).send_command("screen_on")
            message = "OLED controller reinitialized and current watch content redrawn."
        elif action == "capture":
            from lab6_dt2811_ms7635_rnb2135_check2_app import classify_HAR
            for remaining in (3, 2, 1):
                set_message(checkpoint, "Capturing %s in %s… keep performing the activity" % (truth, remaining))
                time.sleep(1)
            set_message(checkpoint, "Capturing 128 readings → Gemini → OLED…")
            result = json.loads(classify_HAR(host, truth=truth, location=location))
            message = ("Error: " + result["error"] if result.get("error") else
                       "Actual: %s · Gemini: %s · OLED: %s" % (truth, result["label"], result["oled_response"]))
        else:
            from record_cloud_demo import main
            result = main(host, action)
            message = "Saved real ESP32 %s request %s." % (action, result["result"]["id"])
            if action == "prediction":
                message += " OLED label: " + result["result"]["label"]
        set_message(checkpoint, message)
    except Exception as error:
        set_message(checkpoint, "Error: " + str(error))
    finally:
        if action != "uci":
            DEVICE_LOCK.release()
        with LOCK:
            STATE["checkpoints"][checkpoint]["busy"] = False


def confirm_oled(checkpoint):
    if checkpoint == "2":
        records = completed_hardware(ROOT)
        if not records:
            raise ValueError("Run a successful checkpoint 2 capture first")
        latest = records[-1]
        label, identifier, stamp, source = latest["label"], None, latest["captured_at"], "gemini"
    elif checkpoint == "4":
        records = [r for r in lines(ROOT / "results/esp32_cloud_demo.jsonl")
                   if r.get("stage") == "prediction" and r.get("ok")]
        if not records:
            raise ValueError("Run checkpoint 4 first")
        latest = records[-1]
        label, identifier, stamp, source = latest["result"]["label"], latest["result"]["id"], None, "cloud"
    else:
        raise ValueError("OLED label confirmation belongs to checkpoint 2 or 4")
    append_jsonl(ROOT / "results/oled_confirmations.jsonl",
                 {"at": datetime.now(timezone.utc).isoformat(), "confirmed_by": "wearer via local dashboard",
                  "checkpoint": checkpoint, "label": label, "source": source,
                  "record_id": identifier, "capture_at": stamp})
    set_message(checkpoint, "Your visual confirmation of %s was saved." % label)


def snapshot(host, endpoint):
    hardware = completed_hardware(ROOT)
    demos = lines(ROOT / "results/esp32_cloud_demo.jsonl")
    uci = lines(ROOT / "results/checkpoint1_demo.jsonl")
    with LOCK:
        state = {"cloud": STATE["cloud"],
                 "checkpoints": {key: dict(value) for key, value in STATE["checkpoints"].items()}}
    state.update(host=host, endpoint=endpoint, labels=LABELS,
                 coverage=dict(Counter(r["truth"] for r in hardware)),
                 count=len(hardware), correct=sum(r["truth"] == r["label"] for r in hardware),
                 rows=[{"truth": r["truth"], "label": r["label"], "oled_response": r["oled_response"]}
                       for r in hardware], pending=pending_evidence(ROOT))
    state["checkpoints"]["1"].update(latest=uci[-1] if uci else None, count=len(uci))
    state["checkpoints"]["2"].update(latest=hardware[-1] if hardware else None)
    for key, stage in (("3", "storage"), ("4", "prediction")):
        records = [r for r in demos if r.get("stage") == stage and r.get("ok")]
        state["checkpoints"][key].update(latest=records[-1] if records else None, count=len(records))
    return state


def make_handler(host, endpoint):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, data, code=200):
            body = json.dumps(data).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(Path(__file__).with_name("dashboard.html").read_bytes())
            elif self.path == "/status":
                self.reply(snapshot(host, endpoint))
            else:
                self.reply({"error": "Not found"}, 404)

        def do_POST(self):
            if self.path != "/action":
                return self.reply({"error": "Not found"}, 404)
            if self.headers.get("Origin") not in (None, "http://" + self.headers.get("Host", "")):
                return self.reply({"error": "Invalid origin"}, 403)
            try:
                size = int(self.headers.get("Content-Length", 0))
                if not 0 < size <= 4096 or self.headers.get("Content-Type") != "application/json":
                    raise ValueError("Expected a small JSON request")
                payload = json.loads(self.rfile.read(size))
                action = payload.get("action")
                checkpoint = str(payload.get("checkpoint", ACTIONS.get(action, "")))
                if action == "confirm":
                    confirm_oled(checkpoint)
                    return self.reply({"accepted": True})
                if action not in ACTIONS or checkpoint != ACTIONS[action]:
                    raise ValueError("Unknown checkpoint action")
                truth, location = payload.get("truth"), payload.get("location", "wrist")
                if action == "capture" and (truth not in LABELS or not isinstance(location, str)
                                            or not 0 < len(location.strip()) <= 80):
                    raise ValueError("Select the actual activity and placement")
                with LOCK:
                    if STATE["checkpoints"][checkpoint]["busy"]:
                        return self.reply({"error": "This checkpoint is already running"}, 409)
                    if action != "uci" and not DEVICE_LOCK.acquire(blocking=False):
                        return self.reply({"error": "The watch is busy with another hardware test. Wait for it to finish."}, 409)
                    STATE["checkpoints"][checkpoint].update(busy=True, message="Starting checkpoint " + checkpoint + "…")
                threading.Thread(target=perform, args=(host, action, truth, location), daemon=True).start()
                self.reply({"accepted": True, "checkpoint": checkpoint}, 202)
            except (ValueError, TypeError) as error:
                self.reply({"error": str(error)}, 400)

        def log_message(self, *args):
            pass
    return Handler


def main(host, endpoint, port):
    os.chdir(ROOT)
    threading.Thread(target=monitor, args=(endpoint,), daemon=True).start()
    print("Lab dashboard: http://127.0.0.1:%d | ESP32: %s" % (port, host), flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), make_handler(host, endpoint)).serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="10.206.67.177", help="ESP32 IP; unused by checkpoint 1")
    parser.add_argument("--endpoint", default="http://136.82.132.175")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    main(args.host, args.endpoint.rstrip("/"), args.port)
