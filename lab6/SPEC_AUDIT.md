# Lab 6 specification audit — November 11, 2026

**Overall status: complete.** All required report evidence is collected. Ten completed wrist-mounted Gemini/OLED trials cover all six classes, with 6/10 correct (60%). Live ESP32 storage/inference and wearer OLED checks are recorded. A fresh five-page PDF and companion Markdown cover all report requirements. The VM remains running at the user's request.

This audit follows the supplied `Lab 6.pdf`; page numbers below refer to that handout. Saved engineering checks and benchmark replays do not count as labeled human activity trials or live ESP32 cloud demonstrations.

| Requirement | Status | Evidence |
| --- | --- | --- |
| Task 1, pp. 3–4: custom train/test PyTorch Dataset; three total-acceleration and three body-gyro channels; `[B,6,128]`; labels 0–5 | Complete | `har_dataset.py`; `logs/cloud_run.log` shows 7,352 train and 2,947 test windows with `[32,6,128]` batches. Raw g/rad/s units are retained. |
| Task 2, pp. 5–7: Gemini prompts with device/placement/setting/candidates/data; CoT and direct outputs for ten random test samples; accuracy and consistency | Complete | `results/llm_uci.json` contains ten paired six-channel prompts, raw responses, parsed labels and ground truth. Both styles scored 1/10; agreement was 8/10. Indices were independently checked against seed 4764, and labels/accuracies were recomputed from the raw responses and original dataset. `results/llm_uci_accel.json` additionally evaluates the same windows with three acceleration channels: CoT 1/10, direct 2/10. |
| Task 3/checkpoint 2, p. 8: 128 samples at 50 Hz, three axes in g; Lab 5 extension; OLED; ten labeled samples and generalization discussion | Complete | `results/esp32_llm.jsonl` has ten completed wrist-mounted Gemini/OLED trials covering all six classes, 6/10 correct. Report p. 3 lists every trial, compares 60% hardware accuracy with the matched three-channel UCI direct-answer result (20%), and explains activity-mix/placement limitations. Wearer OLED confirmations are saved separately. |
| Task 4/checkpoint 3, p. 9: Flask on Compute Engine, external connection, real ESP32 POST and persistent storage | Complete | Real ESP32 Wi-Fi GET returned HTTP 200 through public load balancer `136.82.132.175` to private `esp-cloud:5000`. Device POST `/samples` returned persistent ID `c61888d0c1ea4b16b2cae14587a97aed`. That exact real `[3,128]` window is in VM storage, independently verified by `results/live_cloud_verification.json`. Flask remains in detached screen. The original replay restart check also remains available. |
| Task 5.1, p. 10: official pretrained NormWear, task description/options/signals, PyTorch wavelets, full UCI test set, accuracy and CPU/GPU runtime | Complete | `task5_zero_shot.py` uses the official sensor and MSiTF checkpoints, `optimized_cwt=True`, six answer options, and `signal_encode`. `results/normwear_zero_shot.json` contains all 2,947 predictions and ground-truth labels. Input: total acceleration `[B,3,128]`, g, 50 Hz. Accuracy: **11.2318%**. Inference time: **2,390.28 seconds / 39.84 minutes**, CPU. The handout's approximately 16% accuracy and 10–20 minute runtime are reference estimates, not results that were substituted for measurements. |
| Task 5.2, p. 11: 5–10 train samples per class, frozen `get_embedding`, mean-pool channels/patches to 768, one linear six-class head, cross-entropy, about 100 epochs, full-test evaluation, saved embeddings/labels | Complete | `task5_linear_probe.py` selects ten examples per class from the official training split: 60 total. Encoder parameters are frozen. The only trained module is `Linear(768,6)`; fixed standardization uses the 60 training embeddings only. Training uses cross-entropy for 100 epochs. `artifacts/embeddings.pt` contains `[60,768]` train and `[2947,768]` test features plus labels and train indices. `artifacts/linear_probe.pt` contains the head, scaling and encoder checksum. Full-test accuracy: **68.5103%**, a **57.2786 percentage-point** improvement. |
| Task 5.3/checkpoint 4, p. 12: live ESP32 → VM encoder/probe → OLED | Complete | Device `/predict` returned SITTING in 0.8938 seconds; ID `26f2fe941da4479cb42e9a28877d037e`. Subsequent real device results are in `results/esp32_cloud_demo.jsonl`. A fresh encoder/probe reproduced all verified live labels/probabilities with maximum difference zero. The wearer visually confirmed cloud label WALKING_UPSTAIRS for record `cf9c29e316044804935dbb453bcd8471`. Firmware is configured to the load-balancer endpoint. |
| Submission/report, pp. 13–14 | Complete | Five-page PDF follows only p.14 task sections (2, 3, 5.1, 5.2, 5.3); companion Markdown and a task-organized ZIP include every p.13 code category. Report content: paired CoT/direct examples and accuracy/consistency reflection; ten real ESP32 rows and generalization; NormWear input, accuracy and CPU runtime; before/after probe accuracy; pipeline description and actual persisted input/output evidence. `results/report_requirements.json` confirms all seven content checks with pending=[]. |

## Independent checks supporting the measured results

- `results/cloud_verification.json`: both accuracies independently recomputed from 2,947 predictions; encoder SHA-256 matched the official downloaded checkpoint; ten training examples per class verified; reloading the saved probe reproduced every reported test prediction.
- `results/encoder_cache_audit.json`: a fresh official `get_embedding` call on test window 0 was mean-pooled and compared with the saved test feature. Maximum absolute difference was `9.5367431640625e-07`, within the stated `1e-4` tolerances. Every encoder parameter had `requires_grad=False`.
- `logs/cloud_run.log`: eight offline checks passed on the VM, followed by the real Dataset, pretrained encoder, full zero-shot run and probe training/evaluation.
- `results/cloud_environment.json`: actual execution host, Python/PyTorch versions and installed package versions.

The test embeddings for the probe were cached directly from `NormWearModel.get_embedding` **before** zero-shot text/query fusion. This avoids a duplicate full encoder pass while preserving the 768-dimensional features requested in Task 5.2. Training embeddings were separately computed from the official training split. Test labels were used only for evaluation and cache-order validation.

The pinned official repository was obtained as a source archive rather than a Git checkout. Because the VM initially had no internet route, dependencies and exact pretrained files were downloaded on the Mac and transferred through IAP; all reported NormWear inference and probe training occurred on Compute Engine.

## Current deployment and remaining steps

- Instance: `esp-cloud`, project `eecs-aiot`, zone `us-east4-b`; `RUNNING` was confirmed during this audit.
- Internal address: `10.150.0.2`; no external address. SSH uses IAP.
- Flask health returned `status: ok`, `prediction_ready: true`, `shape: [3,128]`, `sampling_rate: 50`, `units: g`.
- Firewall rule `lab6-har-campus-5000` allows TCP 5000 from the observed ESP32 public egress address `129.236.226.103/32` to tag `lab6-har`.
- The VM stays private. The working public load balancer routes to unmanaged group `lab6-esp-cloud`, named port `http:5000`, using the existing Google proxy/health-check firewall rule; no external-IP exception is required for this route.

Remaining work: none for the requested implementation, measured experiments, and report. Submission to the course system remains the user's action.

The rewritten PDF was rendered and visually inspected; key metrics, ten hardware rows, all six classes, actual cloud record IDs, and exclusion of the interrupted stairwell trial were checked against source data.

The VM must remain running until the user authorizes stopping it. The saved evidence supports all listed lab requirements.
