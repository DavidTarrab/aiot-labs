# Resume handoff — November 4, 2026

## Update — November 11, 2026

LATEST CORRECTION: User supplied Lab 6 (1).pdf and clarified report should match p.14 only: Tasks 2,3,5.1,5.2,5.3. Removed standalone Task1/4 report sections and retained no preparation/collection timing line. Code still includes all Task1–5 categories required by p.13. Rewrote package_submission.py with explicit task mapping; ZIP now has report/, task1/, task2/, task3/{desktop,esp32}, task4/esp32, task5/esp32, shared/, tools/, tests/, results/, artifacts/, logs/, run.py and submission_manifest.json. SUBMISSION_README.md becomes ZIP README, submission_run.py becomes ZIP run.py; launcher sets import paths and LAB6_ROOT. Dashboard supports LAB6_ROOT and resolves HTML beside its source. Existing working source layout and running services were not moved/interrupted. A fresh extraction at /private/tmp/aiot-lab6-final-structure/lab6 passed all eight main tests, four independence tests, desktop/cloud CLI import checks, USB CLI with pyserial, and reproduced all 2947 saved-head predictions. Temporary Flask for local tests: /private/tmp/aiot-lab6-submission-tests. Five-page checklist-only PDF rendered/visually inspected; current ZIP is regenerated from explicit mappings, not recursive workspace files.

LATEST: The user requested a report rewritten from scratch after carefully rereading the handout. Replaced make_report.py with a new evidence-based Markdown/PDF generator. Ten completed wrist trials now cover all six classes, 6/10 correct (60%); the user collected laying and downstairs after being asked. Generated a fresh five-page report and companion Markdown, covering all handout p.14 requirements, with three actual paired-output examples, ten real hardware rows, measured generalization, NormWear formats/accuracies/CPU runtime, probe improvement, pipeline table, real persisted input excerpt and wearer-confirmed WALKING output (record f3fd17432c2746629f9d13938da15c67). Latest VM cloud_samples.jsonl downloaded (19 records). All report requirements pass in results/report_requirements.json with pending=[]; PDF rendered to /private/tmp/aiot-lab6-report-preview for visual inspection. Report and package can now be final; old draft archives are historical. Temporary PDF dependencies at /private/tmp/aiot-lab6-report, renderer at /private/tmp/aiot-lab6-render. Do not stop VM without user authorization.

OLED diagnostics later restored a blank panel via full SSD1306 reinitialization. Simple DISPLAY ON/redraw commands had succeeded but left it blank; five I2C scans acknowledged 0x3C, and the wearer confirmed text after full initialization at both 100kHz and normal 400kHz. Updated lab6/lab5_watch.py screen_on to call init_display, and added dashboard Restore OLED display action. Uploaded watch module, soft-restarted checkpoint 4 command server, verified new dashboard recovery action and wearer-confirmed OLED RECOVERED text. No definitive initiating hardware/software cause established. Four independence tests pass after the change. Current dashboard tool session is 41174, same localhost port 8766; hardware IP unchanged. Evidence: results/oled_diagnostics.json. Continue activity trials; do not interrupt running captures.

Latest: real device storage and prediction succeeded; `results/esp32_cloud_demo.jsonl` contains their IDs. `verify_live_cloud.py` ran on the VM and found all checked raw device windows in durable storage, timing near 50 Hz, and reproduced every checked prediction with probability difference zero. `results/live_cloud_verification.json` was downloaded. The wearer confirmed wrist placement and is collecting trials. Four completed Gemini/OLED trials currently cover standing, walking, upstairs, and sitting; downstairs/laying and ten total remain. A wearer-reported stairwell Wi-Fi timeout is excluded from report/trial counts while raw logs remain. `completed_hardware` centralizes that filtering. Eight main tests passed again on VM, saved probe reproduced all 2,947 predictions again.

Dashboard rewritten into four independent checkpoint panels: `dashboard.py` + `dashboard.html`. Active localhost port 8766, tool session 99290. Four isolation tests pass in `test_dashboard.py`; fixture results are in temporary directories only. CP1 saves separate paired UCI demos; CP2 captures real Gemini trials; CP3 does fresh storage; CP4 does fresh cloud inference, requiring no CP3 execution. CP1 can overlap hardware; CP2–4 serialize the shared watch. Dashboard preserves prior records. Firmware at ESP32 IP `10.206.67.177` is running checkpoint 4's shared command server and supports all hardware paths. `usb_tool --start` now soft-resets first to clear cached imports and stale listeners. Do not interrupt it while the wearer collects.

Work resumed. GCP login refreshed. The VM had rebooted and Flask was stopped; restarted the saved server in detached screen. Created unmanaged group `lab6-esp-cloud` containing `esp-cloud`, named port `http:5000`, attached it to `load-balancer-backend`, and changed its HTTP health-check port to 5000. Existing proxy-source firewall already permits traffic; no firewall or security-policy changes were needed. Google reports the lab backend HEALTHY. A real USB-controlled ESP32 Wi-Fi GET to `http://136.82.132.175/` returned HTTP 200 with `prediction_ready:true`; evidence is `results/esp32_cloud_health.json`. Current ESP32 Wi-Fi IP is `10.206.67.177`. Checkpoint 3/4 source URLs now use that public load-balancer endpoint; not yet uploaded. Live storage, inference/OLED, and ten labeled captures remain pending. A request to detach the unrelated unhealthy managed group from the backend was retried after the first attempt reported resource busy; confirm final configuration. Do not delete its VM or group. Earlier pause/network-blocker notes below are historical.

## User instruction at pause

The user said: “stop where you are now and make sure you can pick up exactly here you left off. I need to shut my computer.”

Work is paused. Do not continue until the user resumes. Earlier, the user explicitly instructed **do not stop the VM yet**. A stop approval was rejected; no successful VM stop occurred. Keep that instruction in force. Closing the Mac disconnects local SSH sessions, but the VM and its `screen`-hosted Flask service remain running.

## Overall assignment and completed work

Workspace: `/Users/david/Shared/aiot`; lab source/results under `lab6/`.
Handout: `/Users/david/Downloads/Lab 6.pdf`.

The full assignment is **not complete**. `SPEC_AUDIT.md` maps every requirement to the evidence and missing work. The PDF explicitly says `INCOMPLETE`, and the package is correctly named `lab6_dt2811_ms7635_rnb2135_draft.zip`. Do not describe this as a finished submission.

Completed and measured:

- Task 1: custom UCI HAR Dataset/DataLoader, raw six channels `[N,6,128]`, train/test counts 7,352/2,947, labels remapped to 0–5.
- Task 2: ten seeded paired six-channel Gemini trials. CoT/direct accuracy both 10%; agreement 80%. A matched three-accelerometer-channel run scored CoT 10%, direct 20%, agreement 70%. Raw prompts/responses are saved. Seeded indices, original labels, parsed outputs and accuracy were independently rechecked.
- An unlabeled ESP32 → Gemini → OLED-command smoke check exists from October 28; prediction `STANDING`, acknowledgement `Displaying: STANDING`. This is not part of the ten labeled activity captures and is not a visual screenshot.
- Task 5.1: full 2,947-window NormWear zero-shot evaluation on the real GCP VM: **11.2317611% accuracy**, **2,390.27985 s inference / 39.84 min**, CPU. Inputs: `[B,3,128]` total acceleration, g, sampling_rate=50. Official pretrained sensor and MSiTF checkpoints, optimized PyTorch wavelets, six text options and task question, official `signal_encode` path.
- Task 5.2: 60 official training windows, ten/class, frozen encoder, mean-pool channels/patches to 768, training-only fixed standardization, single `Linear(768,6)`, cross-entropy/AdamW, 100 epochs. Full-test accuracy **68.5103476%**; improvement **57.2785865 percentage points**. Test features were cached directly from the frozen sensor `get_embedding` output before zero-shot fusion, avoiding a second full encoder pass. Probe workflow took 58.37 s with cached test embeddings.
- Verification reloaded the saved head and reproduced all 2,947 test predictions, recomputed accuracies, checked ten train examples/class and official sensor checkpoint SHA-256.
- A fresh official encoder call on test window 0 matched the saved feature: maximum absolute difference `9.5367431640625e-07` (tolerances 1e-4), and all encoder parameters were frozen.
- Eight offline tests passed on the VM.
- Flask storage and prediction work on the VM. Storage survives server restart. A **UCI replay**, explicitly identified as such, returned `STANDING` in 0.8781 s and matched the corresponding offline prediction. This does not satisfy a live ESP32 cloud demo.

Remaining:

1. Ten user-labeled ESP32/Gemini captures covering all six activities, actual OLED confirmation, hardware results table and measured generalization discussion (Task 3).
2. Reachable cloud endpoint and external/browser verification, followed by a real ESP32 HTTP `/samples` request and proof of persistence (Task 4/checkpoint 3).
3. A real ESP32 HTTP `/predict` request to the cloud encoder/probe and returned label displayed on OLED (Task 5.3/checkpoint 4).
4. Final PDF and ZIP after that evidence is collected.

The user previously chose to finish cloud work first and collect activities later. Do not invent ground truth. `collect_activities.py` is a guided ten-capture CLI; `record_cloud_demo.py` records real device-initiated storage/prediction demos. Current checkpoint 3/4 firmware still has `CLOUD_URL = "http://YOUR_VM_EXTERNAL_IP:5000"` and must be configured only after a working endpoint is confirmed.

## GCP and runtime

- Project `eecs-aiot`, zone `us-east4-b`, instance `esp-cloud`.
- SSH: `gcloud compute ssh esp-cloud --project=eecs-aiot --zone=us-east4-b`.
- Local gcloud executable: `/Users/david/google-cloud-tools/google-cloud-sdk/bin/gcloud`.
- Account used by gcloud: `dt2811@columbia.edu`.
- VM workspace: `/home/david/aiot/lab6` (`~/aiot/lab6`).
- Debian 13, Python 3.13.5, `e2-standard-4`, 16 GB RAM, 10 GB disk, CPU. About 600 MB disk space remained after final artifacts; do not download duplicate large model files.
- VM Python: `~/aiot/lab6/.venv/bin/python`.
- Matched CPU packages: torch/torchaudio 2.9.1+cpu, torchvision 0.24.1+cpu. Full environment is recorded in `results/cloud_environment.json`.
- VM had no internet route. Linux wheels and exact official model files were downloaded on the Mac and uploaded with IAP. The uploaded wheel files were deleted after installation to conserve VM space; originals remain locally in `lab6/cloud-wheelhouse/`.
- Models: `vendor/NormWear/`, `weights/normwear_pretrain_ckpt.pth`, `weights/normwear_msitf_zeroshot_last_checkpoint-5.pth`, `text_model/` (full-precision clinical TinyLlama, about 4.1 GB). **Do not rerun the 40-minute evaluation or training unnecessarily.** All needed artifacts exist.
- NormWear source revision `07517fcb13def8c89cb586128359cec02f86ec8d`, release v1.0.0-alpha. `results/normwear_setup.json` contains checksums.
- Private VM IP `10.150.0.2`; no external access config at the last check. Public IP attachment was rejected twice by `constraints/compute.vmExternalIpAccess`.
- The user initially planned to request an external-IP exception. A read-only policy query failed because the Organization Policy API is disabled; it was not enabled or modified.
- Direct `http://10.150.0.2:5000/` works from inside GCP. The Mac timed out; the Wi-Fi-connected ESP32 also timed out. It is not directly reachable from campus.
- VM tag `lab6-har`; firewall rule `lab6-har-campus-5000` permits TCP 5000 from observed ESP32 egress `129.236.226.103/32` only. This rule is for direct campus traffic, not load-balancer proxies.

Flask runs in detached screen session `4485.lab6-server` (numeric PID can change). It is loaded with the trained probe and health returns:

```json
{"prediction_ready":true,"sampling_rate":50,"shape":[3,128],"status":"ok","units":"g"}
```

Its command is equivalent to:

```sh
cd ~/aiot/lab6
NORMWEAR_NUM_THREADS=4 .venv/bin/python -u lab6_dt2811_ms7635_rnb2135_server.py \
  --repo-parent vendor --weights weights/normwear_pretrain_ckpt.pth \
  --probe artifacts/linear_probe.pt --device cpu
```

Logs are under `logs/`. Completed experiments are no longer running; only the server needs to remain active. A local tool SSH `tail -F` monitor existed, but it is not required and will disconnect when the Mac shuts down.

## Exact stopping point: newly configured load balancer

Latest request before pause: “try 136.82.132.175. I configured a load balancer to route traffic to the VM”.

We performed **read-only diagnostics only**. No load-balancer repairs or firmware URL changes have been made.

Observed from the Mac:

- `http://136.82.132.175/`: connection reset.
- `http://136.82.132.175:5000/`: connection reset.
- `https://136.82.132.175/`: TLS unexpected EOF.

Observed directly from ESP32 (connected to Wi-Fi): both HTTP port 80 and 5000 returned `ValueError HTTP error: BadStatusLine: []`, not valid Flask responses.

GCP read-only inspection found:

1. Global reserved address `load-balancer`: **136.82.132.175**, PREMIUM IPv4, status **RESERVED**, no users/forwarding-rule attachment.
2. `gcloud compute forwarding-rules list --project=eecs-aiot` returned **no rules**. No active frontend was listed.
3. Global backend service `load-balancer-backend` exists:
   - `EXTERNAL_MANAGED`, protocol HTTP, `portName: http`, service `port: 80`, timeout 30.
   - Backend group: `projects/eecs-aiot/zones/us-east4-b/instanceGroups/instance-group-1`.
   - Health check: `projects/eecs-aiot/global/healthChecks/health-check-load-balancer`.
   - `enableCDN: true`.
   - Cloud Armor policy `default-security-policy-for-load-balancer-backend`. Do not disable security policies as a shortcut.
4. Group `instance-group-1` is **managed**, size 1, controlled by instance group manager `instance-group-1`, despite being successfully described through the unmanaged-describe command.
   - Named port **http:27**.
   - Health points to **instance-group-1-mj0x, 10.150.0.3, port 27, UNHEALTHY**.
   - This is **not** the trained `esp-cloud` VM (`10.150.0.2:5000`). Do not delete/stop this separately created VM or managed group without authorization.

Thus the observed setup has three concrete problems: no attached frontend forwarding rule, the backend selects a different VM, and its named port is 27 rather than Flask's 5000.

### Next steps when explicitly resumed

Recheck first: the user may have completed more console configuration while paused.

- Read forwarding rules/address status, URL maps and target HTTP/HTTPS proxies to find any newly completed frontend.
- Inspect `health-check-load-balancer`, relevant firewall rules and current backend health.
- Determine the least disruptive repair that routes the intended frontend to **esp-cloud:5000**. A dedicated unmanaged instance group containing the existing trained VM, with named port `http:5000`, may be appropriate; do not attempt to add the existing VM into the user's managed group or delete the new managed VM.
- Reuse the user's intended address and existing suitable frontend resources; avoid duplicate load balancers. No frontend resources, URL maps or proxies have been inspected yet.
- Global external Application Load Balancer backends require the Google proxy/health-check ranges to reach the backend port. The campus-only firewall rule is insufficient for this route. Official documentation consulted:
  - https://docs.cloud.google.com/load-balancing/docs/firewall-rules
  - https://docs.cloud.google.com/load-balancing/docs/https
  - https://docs.cloud.google.com/load-balancing/docs/https/setup-global-ext-https-compute
  - Relevant IPv4 GFE/proxy ranges include `35.191.0.0/16` and `130.211.0.0/22`; verify the applicable rule for the actual backend/LB type before changing anything.
- Once configured, verify healthy backend, valid HTTP from the Mac **and ESP32**, and a real `/predict` response before updating firmware `CLOUD_URL`.
- Then complete the live device cloud demos and evidence. This public load-balancer endpoint can legitimately front the private VM; the earlier VM external-IP exception may no longer be needed if the LB works. Document the actual architecture rather than claiming the VM itself has a public IP.

## ESP32 and local Python

- Serial `/dev/cu.usbserial-5B8E6153341`, 115200 baud.
- Last Wi-Fi address `10.206.89.108`; network `Columbia University`, gateway `10.206.0.1`.
- Last observed public egress `129.236.226.103` (recheck if networking changes).
- MicroPython 1.26; ADXL345 ID 0xE5; OLED I2C address 0x3C.
- OLED SDA 22/SCL 20, 128x32; ADXL SPI SCK 5/MOSI 19/MISO 21/CS 27; buttons 12/13/14; piezo 32.
- USB diagnostics enter raw REPL and interrupt a running program. At pause, the board was left at REPL after network tests, not running the watch TCP server. Its Wi-Fi connection was active. Restart the appropriate uploaded firmware when needed.
- `lab6/usb_tool.py --code ...`, `--upload ...`, `--start SCRIPT.py` are available. Existing `boot.py` was never replaced; no automatic main.py boot was configured.
- Root `.venv/bin/python` has pyserial. `lab5/.venv/bin/python` has torch/NumPy/Gemini/Gradio/Whisper/truststore and was used for desktop work. A stale `/private/tmp/aiot-pdf-tools` contains unusable namespace remnants; do not rely on it.
- Working PDF reader: `PYTHONPATH=/private/tmp/aiot-final-pdf python3`, with pypdf 6.21.4 (temporary directory might need recreation after reboot).
- Gemini key is read from environment or the existing private `lab5/.gemini_api_key`. Never print, copy into source, upload to VM, or include it in archives.
- For faster IAP copies, previous commands used:
  `CLOUDSDK_PYTHON=/Users/david/Shared/aiot/lab5/.venv/bin/python CLOUDSDK_PYTHON_SITEPACKAGES=1 /Users/david/google-cloud-tools/google-cloud-sdk/bin/gcloud compute scp ... --tunnel-through-iap`

## Durable local evidence and deliverables

- `lab6/results/`: all completed LLM/cloud JSON/JSONL, environment, checkpoint checksums, API/restart evidence and fresh encoder-cache audit.
- `lab6/artifacts/embeddings.pt`: 9,264,187 bytes; train/test embeddings, labels and train indices.
- `lab6/artifacts/linear_probe.pt`: 27,599 bytes; trained head/scaling/checksum.
- `lab6/logs/cloud_run.log` and `server.log`: downloaded VM logs.
- `lab6/lab6_dt2811_ms7635_rnb2135_report.pdf`: five-page **incomplete** report with actual model results.
- `lab6/lab6_dt2811_ms7635_rnb2135_draft.zip`: validated archive, last rebuilt with **59 entries**, including audit/proof, code, report, compact artifacts and logs. Keys, dataset downloads, virtualenvs, vendor models/weights and redundant cache are excluded.
- `lab6/lab6_dt2811_ms7635_rnb2135_initial_draft.zip`: older small initial draft; not the current package.
- `lab6/SPEC_AUDIT.md`, `README.md`, `GCP_SETUP.md`: detailed status and instructions.
- `lab6/results/esp32_llm.jsonl` and `lab6/results/esp32_cloud_demo.jsonl` **do not exist** yet; their absence corresponds to the pending hardware evidence.

VM files also remain under `~/aiot/lab6`, so the source/models/results survive closing the Mac. The latest `SPEC_AUDIT.md` and last local package rebuild may be newer than the VM's copy; synchronize when needed rather than assuming both ZIPs are identical.
