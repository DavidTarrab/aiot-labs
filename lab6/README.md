# Lab 6 — dt2811, ms7635, rnb2135

**Current submission:** [Report PDF](lab6_dt2811_ms7635_rnb2135_report.pdf) · [Editable report](lab6_dt2811_ms7635_rnb2135_report.md) · [Submission ZIP](lab6_dt2811_ms7635_rnb2135.zip). The report follows only the p.14 sections: Tasks 2, 3, 5.1, 5.2, 5.3. The ZIP follows the p.13 code categories and organizes Tasks 1–5 in separate directories, with shared modules, tools, tests, evidence and artifacts. See [the ZIP README source](SUBMISSION_README.md) for its structure and launcher commands; this workspace keeps its working source layout unchanged. A clean extraction passed all 12 tests and reproduced all 2,947 saved-head predictions. Ten real wrist trials cover all six activities, with 6/10 correct. NormWear measured 11.23% zero-shot and 68.51% after the probe.

Code for every task and checkpoint in the supplied Lab 6 handout. The generated PDF distinguishes measured results from pending experiments. Actual activity labels must come from the person performing the activity; synthetic test fixtures never count as lab observations.

## Files and tasks

| Task | Entry point | Supporting files |
| --- | --- | --- |
| 1: raw UCI Dataset/DataLoader | `har_dataset.py` | `download_data.py`, `har_common.py` |
| 2/checkpoint 1: paired Gemini inference | `lab6_dt2811_ms7635_rnb2135_check1.py` | `har_gemini.py` |
| 3/checkpoint 2: ESP32 + Gemini/OLED | `lab6_dt2811_ms7635_rnb2135_check2_app.py`, `lab6_dt2811_ms7635_rnb2135_check2_esp32.py` | `har_client.py`, `har_device.py`, `lab5_watch.py`, `lab5_interpreter.py`, `ssd1306.py` |
| 4/checkpoint 3: persistent cloud storage | `lab6_dt2811_ms7635_rnb2135_server.py`, `lab6_dt2811_ms7635_rnb2135_check3_esp32.py` | `har_common.py` |
| 5.1: zero-shot NormWear | `task5_zero_shot.py` | `setup_normwear.py`, `har_normwear.py` |
| 5.2: frozen encoder + linear probe | `task5_linear_probe.py` | saved embeddings and probe in `artifacts/` |
| 5.3/checkpoint 4: end-to-end cloud HAR | server above, `lab6_dt2811_ms7635_rnb2135_check4_esp32.py` | `har_normwear.py` |
| Report and ZIP | `make_report.py`, `package_submission.py` | `results/` |

The shared Lab 5 watch and interpreter are copied locally so the submission works without the other labs. The interpreter adds `classify_HAR`; clock, alarm, weather, screen and message commands remain available. No earlier lab files were modified. Shared constants/functions and descriptive section comments follow the earlier labs' style.

## Wiring and firmware

| Device | Signal | GPIO / configuration |
| --- | --- | --- |
| SSD1306 OLED | SDA / SCL | 22 / 20, I2C 0, address 0x3C, 128x32 |
| ADXL345 | SCK / MOSI / MISO / CS | 5 / 19 / 21 / 27, SPI 1, mode 3 |
| Buttons A/B/C | active low, pull-ups | 12 / 13 / 14 |
| Piezo | PWM | 32 |

These match labs 3–5. Both peripheral IDs and a 128-sample timed capture were checked on the connected ESP32. Keep the existing power/ground wiring and 3.3 V logic. The full-resolution sensor is configured to +/-16 g at 50 Hz. Each signed reading is multiplied by 0.0039 g/count, preserving gravity rather than subtracting a per-window mean. The last sample occurs about 2.54 seconds after the first, as expected for 128 samples at 50 Hz (window duration 128/50 = 2.56 seconds).

Upload `ssd1306.py`, `lab5_watch.py`, `har_device.py`, and the chosen checkpoint ESP32 entry point with Arduino Lab for MicroPython. Run that entry point. The firmware connects to the same open `Columbia University` network as lab 5 and prints its IP; the verified address was `10.206.190.234` but DHCP may change it. Read the new address after reconnecting. The desktop and ESP32 must be reachable over TCP 8080.

Alternatively, from the project root:

```sh
.venv/bin/python lab6/usb_tool.py --port /dev/cu.usbserial-5B8E6153341 \
  --upload lab6/lab5_watch.py lab6/har_device.py lab6/lab6_dt2811_ms7635_rnb2135_check2_esp32.py
.venv/bin/python lab6/usb_tool.py --port /dev/cu.usbserial-5B8E6153341 \
  --start lab6_dt2811_ms7635_rnb2135_check2_esp32.py
```

`usb_tool.py` interrupts a running script to use the REPL. Close other serial monitors first. Uploads overwrite only the filenames explicitly listed; it does not replace `boot.py` or configure automatic boot. Copy the selected entry point to `main.py` yourself if automatic boot is wanted.

## Desktop setup

### Live checkpoint dashboard

If the OLED becomes blank, use **Restore OLED display** in the dashboard. This reapplies the SSD1306 controller configuration and redraws the current content. On November 11, a simple display-on command failed to restore a blank screen, but full reinitialization succeeded at both 100 kHz and the normal 400 kHz. The wearer confirmed the restored firmware's test text. The initiating cause remains undetermined; no pin or bus-speed change was needed. Diagnostic evidence is in `results/oled_diagnostics.json`.

From the project root, run:

```sh
lab5/.venv/bin/python lab6/dashboard.py --host 10.206.67.177
```

Open **http://127.0.0.1:8766**. Each checkpoint has separate controls, progress, and saved results; run them in any order. Checkpoint 1 uses the local UCI test split and Gemini, without the ESP32 or VM. Checkpoint 2 captures a fresh ESP32 window and sends it to Gemini and the OLED, without using the VM. Checkpoint 3 sends a fresh window to Flask `/samples`, without Gemini or the encoder/head. Checkpoint 4 sends a fresh window to `/predict`, without Gemini or a prior checkpoint 3 request. Checkpoints 2–4 serialize access to the physical watch; checkpoint 1 can run alongside them.

The activity table retains completed labeled trials across restarts. Set the actual activity before capture; current confirmed placement is **wrist**. Collect all six classes and ten completed captures total. Incorrect predictions remain valid observations. OLED confirmation buttons separately record the wearer's visual checks for checkpoints 2 and 4.

Checkpoint 1 dashboard trials use `results/checkpoint1_demo.jsonl`, preserving the original ten-window evaluation. Hardware Gemini trials use `results/esp32_llm.jsonl`; real cloud receipts use `results/esp32_cloud_demo.jsonl`. `python -m unittest -v test_dashboard` checks checkpoint independence with isolated fixtures that never enter experiment results.

The deployed endpoint is **http://136.82.132.175**, a Google Cloud load balancer routing to private `esp-cloud:5000`. Group `lab6-esp-cloud` has named port `http:5000`; the health check uses port 5000. Real ESP32 storage/prediction requests succeeded on November 11. `results/live_cloud_verification.json` checks persisted windows and reproduces live predictions with a fresh encoder/probe, with zero probability differences. The VM itself does not require an external IP for this route.

From `lab6/`, create a Python environment and install:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The existing `../lab5/.venv/bin/python` already has torch, NumPy, Gemini, Gradio, Whisper and truststore and was used for initial experiments. Flask and ReportLab are additional requirements. MicroPython firmware runs on the ESP32, not desktop Python. Voice input requires FFmpeg, as in lab 5.

Set `GEMINI_API_KEY`, or reuse the existing private `../lab5/.gemini_api_key`. The submission excludes private keys. `GEMINI_MODEL` defaults to the handout's `gemini-3.5-flash-lite`; set it to another available model only if you also report the change. A 429 quota response is retried up to twice, waiting 55 seconds each time. Failed calls remain errors in the saved experiment rather than receiving invented predictions.

## Dataset and checkpoint 1

```sh
python download_data.py
python har_dataset.py 'data/UCI HAR Dataset'
python lab6_dt2811_ms7635_rnb2135_check1.py 'data/UCI HAR Dataset'
python lab6_dt2811_ms7635_rnb2135_check1.py 'data/UCI HAR Dataset' \
  --channels 3 --output results/llm_uci_accel.json
```

The official dataset archive and its download hash are recorded locally. The loader stacks total acceleration and body gyroscope to `[N,6,128]`, without unit normalization. The checkpoint uses ten random test indices, seed 4764, identical windows for both prompt styles, and no label information in the prompts. Each output file includes prompts, raw responses, parsed labels, accuracy, errors, and cross-style agreement. The second run retains the same indices while removing gyroscope channels for a fairer hardware comparison.

## Checkpoint 2: collect ten labeled hardware samples

Start checkpoint 2 firmware, then:

```sh
python lab6_dt2811_ms7635_rnb2135_check2_app.py
```

Enter the ESP32 IP. In the activity tab, set the true activity and actual sensor placement **before** clicking `classify_HAR`. Attach the sensor consistently (waist matches UCI); begin the activity before clicking and continue during the 2.56-second capture. Keep movements representative and orientation consistent. The app requests `capture_HAR`, sends the three measured channels to Gemini, then returns the predicted label through `display_text`. It logs the raw input, prompt, output, ground truth and OLED response to `results/esp32_llm.jsonl`. Do not count unlabeled smoke captures in accuracy.

Collect at least one of every class and ten total, for example WALKING, WALKING_UPSTAIRS, WALKING_DOWNSTAIRS, SITTING, STANDING, LAYING, then four additional captures of your choice. Record which attachment location you actually use. For CLI capture:

```sh
python lab6_dt2811_ms7635_rnb2135_check2_app.py \
  --host ESP32_IP --label WALKING --location waist --style direct
```

The Lab 5 tab accepts voice/text smartwatch commands, including `classify_HAR` and natural-language activity requests. Use clock sync before alarms. Requests on the same watch should be serialized; sensing/network operations pause the existing watch event loop briefly, so avoid an active alarm during a HAR demo.

For a guided session covering all six activities and ten windows total, start the checkpoint 2 firmware and run:

```sh
python collect_activities.py --host ESP32_IP --location waist
```

Use your actual placement. The script waits for you to confirm each activity, counts down three seconds, then captures and queries Gemini. Failed requests are retained in the log and repeated; incorrect predictions remain valid experimental results and are not retried merely to improve accuracy.

## Cloud and NormWear

Follow [GCP_SETUP.md](GCP_SETUP.md). The three-channel model intentionally matches the ADXL345. It uses `get_embedding` for probe features, `signal_encode` for zero-shot inference, PyTorch CWT for modern SciPy compatibility, and a strict load of the fusion checkpoint. The encoder stays frozen. Only the single linear layer is trained; scaling statistics come only from the selected few-shot training windows. Probe serving verifies the encoder checksum and applies identical feature pooling/scaling.

Cloud payload:

```json
{"data": [[128 numbers], [128 numbers], [128 numbers]], "sampling_rate": 50, "units": "g"}
```

This is schematic JSON: replace each `[128 numbers]` with a numeric array. Optional `label` uses one of the six canonical uppercase labels. `/samples` returns HTTP 201 plus a persistent record ID; `/predict` returns HTTP 200 with label, six probabilities and record ID. It returns HTTP 503 when a probe has not been loaded. Invalid dimensions/units/non-finite values are rejected before writing. Persistence uses JSONL, a process/thread lock, flush and fsync. Flask binds to `0.0.0.0:5000` as required by the lab.

## Validate, report, submit

```sh
python -m unittest -v test_lab6
python make_report.py
python package_submission.py
```

Eight offline checks cover signal ordering/labels/splits, malformed inputs, identical paired prompts, strict output parsing, persistent storage/restart, unavailable inference, pooling, few-shot selection/training and rejection of mismatched embedding caches. Fixture predictions are excluded from all report results. `results/hardware_smoke.json` records the separate USB capture check.

The PDF updates automatically from experiment files in `results/`; missing measurements are marked PENDING. While evidence is missing, the packager appends `_draft` to the ZIP filename and lists unfinished items. A completed-submission filename is generated only after the required evidence exists. The ZIP contains the structured `lab6/` source, documentation, report, measured result JSON/JSONL, compact trained linear probe and saved few-shot/test embeddings when available. It excludes keys, virtual environments, the downloaded UCI data, upstream source/weights, bytecode and the redundant zero-shot embedding cache. Rebuild after copying VM results and artifacts back. This lab remains incomplete until the ten labeled hardware samples, VM experiments and end-to-end demonstration have been collected.

## Deployed VM and reproducible cloud run

The November 4 deployment uses `esp-cloud`, project `eecs-aiot`, zone `us-east4-b`: an `e2-standard-4` CPU instance with Debian 13, Python 3.13.5, 16 GB RAM and a 10 GB disk. The runtime uses torch/torchaudio 2.9.1 CPU and torchvision 0.24.1 CPU. The full installed versions are recorded in `results/cloud_environment.json`. Source and downloaded model weights remain under `~/aiot/lab6`.

Because the VM initially had neither an external address nor internet access, Linux wheels and model files were downloaded on the Mac and uploaded using IAP. `bootstrap_pip.py` installs pip into a `venv --without-pip` environment from a local wheel; dependencies can then be installed with `--no-index --find-links=cloud-wheelhouse` and `cloud-constraints.txt`. The uploaded installers were removed after installation to conserve disk space; originals remain on the Mac. The load balancer now provides the external ESP32 route while the VM remains private.

The efficient experiment sequence is:

```sh
cd ~/aiot/lab6
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export NORMWEAR_TEXT_MODEL="$PWD/text_model"
.venv/bin/python -u run_cloud_experiments.py
```

The runner checks the real encoder, measures CPU throughput, performs zero-shot evaluation, and caches the mean-pooled test embeddings while preserving the official `signal_encode` path. The probe then encodes only its 60 training windows and reuses the validated full-test cache. Test labels never affect fitting. `NORMWEAR_TEXT_MODEL` redirects upstream loading to the identical locally downloaded full-precision text model; it does not replace the model with an approximation.

The November 4 run measured 11.23% zero-shot accuracy and 68.51% probe accuracy on all 2,947 test windows (+57.28 percentage points). Zero-shot inference took 2,390.28 seconds on CPU. `verify_cloud_results.py` independently recomputed the metrics, matched the encoder checksum to the official download, verified ten training examples per class, and reloaded the saved probe to reproduce every reported test prediction. The deployed Flask replay matched the corresponding offline prediction; it is distinct from the pending live ESP32 demonstration.

`cloud_api_smoke.py` tests the deployed Flask service using a UCI replay explicitly marked as an engineering check. This verifies cloud storage/inference but does not count as a live ESP32 demonstration. After configuring the firmware's cloud URL, `record_cloud_demo.py ESP32_IP --stage storage` and `--stage prediction` record actual device-initiated HTTP demonstrations and their returned record IDs. Unlabeled demos do not count toward the ten labeled activity windows.

Sources: [UCI HAR](https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones), [HARGPT](https://arxiv.org/abs/2403.02727), [official NormWear usage](https://github.com/Mobile-Sensing-and-UbiComp-Laboratory/NormWear), [NormWear release](https://github.com/Mobile-Sensing-and-UbiComp-Laboratory/NormWear/releases/tag/v1.0.0-alpha).
