"""Checkpoints 3/4: persist ESP32 windows, optionally run frozen encoder + probe."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
import time
import uuid
from flask import Flask, jsonify, request, abort
from werkzeug.exceptions import BadRequest
from har_common import LABELS, validate_window


def create_app(storage="results/cloud_samples.jsonl", predictor=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 32768
    storage = Path(storage)
    lock = threading.Lock()
    inference_lock = threading.Lock()

    @app.before_request
    def enforce_body_limit():
        if request.content_length and request.content_length > app.config["MAX_CONTENT_LENGTH"]:
            abort(413)

    def persist(payload, prediction=None):
        record = {"id": uuid.uuid4().hex, "received_at": datetime.now(timezone.utc).isoformat(),
                  "window": payload, "prediction": prediction}
        storage.parent.mkdir(parents=True, exist_ok=True)
        # flock protects concurrent processes; Lock also protects threads in one process.
        import fcntl
        with lock, storage.open("a") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            stream.write(json.dumps(record, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        return record["id"]

    def payload():
        if not request.is_json:
            raise ValueError("Use Content-Type: application/json")
        return validate_window(request.get_json())

    @app.errorhandler(ValueError)
    @app.errorhandler(BadRequest)
    def invalid(error):
        return jsonify(error=str(error)), 400

    @app.get("/")
    def health():
        return jsonify(status="ok", prediction_ready=predictor is not None,
                       shape=[3, 128], sampling_rate=50, units="g")

    @app.post("/samples")
    def store():
        data = payload()
        identifier = persist(data)
        return jsonify(id=identifier, stored=True), 201

    @app.post("/predict")
    def predict():
        data = payload()
        if predictor is None:
            return jsonify(error="Start server with encoder weights and trained probe"), 503
        start = time.perf_counter()
        with inference_lock:
            result = predictor(data)
        if result.get("label") not in LABELS:
            raise RuntimeError("Predictor returned invalid activity")
        result["seconds"] = time.perf_counter() - start
        result["id"] = persist(data, dict(result))
        return jsonify(result)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage", default="results/cloud_samples.jsonl")
    parser.add_argument("--repo-parent")
    parser.add_argument("--weights")
    parser.add_argument("--probe")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    supplied = (args.repo_parent, args.weights, args.probe)
    if any(supplied) and not all(supplied):
        parser.error("Supply --repo-parent, --weights and --probe together")
    predictor = None
    if all(supplied):
        from har_normwear import Predictor
        predictor = Predictor(*supplied, device=args.device)
    create_app(args.storage, predictor).run(host="0.0.0.0", port=args.port,
                                          debug=False, threaded=True)
