"""DataSentinel as a local HTTP detector, for AgentDojo to call.

Why a sidecar rather than an import. DataSentinel needs peft and bitsandbytes
and is pinned to transformers 4.42; the AgentDojo venv has transformers 4.46
and neither of the other two. Installing into either environment risks the
reconstructions that currently work - and those working reconstructions ARE the
evidence base for RQ6. A process boundary keeps both intact.

Nothing about the defense is reimplemented here. This loads the released LoRA
checkpoint and calls the authors' own `DataSentinelDetector.detect()`
unmodified; the server is only transport.

    python datasentinel_service.py --port 1112
"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, ".")

import OpenPromptInjection as PI
from OpenPromptInjection.utils import open_config

DETECTOR = None


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/detect":
            self.send_error(404)
            return
        n = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(n) or b"{}")
        text = payload.get("text") or ""
        # detect() returns 1 for contaminated, 0 for clean.
        try:
            flagged = bool(DETECTOR.detect(text))
            body = {"contaminated": flagged}
        except Exception as e:  # surfaced to the caller, never silently "clean"
            body = {"error": f"{type(e).__name__}: {e}"}
        raw = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        raw = json.dumps({"ok": DETECTOR is not None}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass  # the detector prints enough on its own


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=1112)
    ap.add_argument("--ft_path", default="./checkpoints/detector_large/checkpoint-5000")
    ap.add_argument("--gpu", default="0")
    args = ap.parse_args()

    global DETECTOR
    cfg = open_config("./configs/model_configs/mistral_config.json")
    cfg["params"]["ft_path"] = args.ft_path
    cfg["params"]["gpus"] = [args.gpu]
    DETECTOR = PI.DataSentinelDetector(cfg)

    # Fail loudly at startup rather than at the first agent step: if the known
    # positive does not flag, the weights are not loaded the way we think.
    #
    # The probe MUST be the paper's own CombineAttacker construction. A
    # hand-written "ignore previous instructions" string does not reliably
    # hijack this detector - detection here is a behavioural test (does the data
    # stop the model repeating a secret key), not a pattern match - so an
    # ad-hoc probe reads 0 on a working detector and would send us chasing a
    # non-existent loading bug.
    from OpenPromptInjection.attackers.CombineAttacker import CombineAttacker
    target = PI.create_task(open_config("./configs/task_configs/sst2_config.json"), 1)
    inject = PI.create_task(open_config("./configs/task_configs/sms_spam_config.json"),
                            1, for_injection=True)
    clean_text = target[0][0]
    poisoned = CombineAttacker(None, inject).inject(clean_text, 0, target_task="sentiment_analysis")
    neg, pos = DETECTOR.detect(clean_text), DETECTOR.detect(poisoned)
    print(f"startup probe: clean={neg} (expect 0), paper_attack={pos} (expect 1)", flush=True)
    if not (neg == 0 and pos == 1):
        raise SystemExit("DataSentinel probe failed - refusing to serve a detector "
                         "whose controls do not reproduce")

    print(f"DataSentinel listening on :{args.port}", flush=True)
    HTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
