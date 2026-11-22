# Lab 6 submission — dt2811, ms7635, rnb2135

This archive follows the **code submission list on handout p. 13** and the **PDF report checklist on p. 14**. The handout requires a structured ZIP and the code categories below; it does not prescribe directory names. The PDF's task sections are exactly **2, 3, 5.1, 5.2, 5.3**. Tasks 1 and 4 remain included as required code.

```text
lab6/
  README.md
  run.py                       desktop/cloud launcher
  requirements*.txt            dependencies
  report/                      final PDF and editable Markdown
  task1/                       UCI Dataset/DataLoader and data downloader
  task2/                       Gemini prompts, CoT/direct inference, test evaluation
  task3/
    desktop/                   Lab 5 interface extension and labeled collection
    esp32/                     ADXL345/OLED implementation and checkpoint 2 firmware
  task4/                       Flask storage server and checkpoint 3 ESP32 entry point
  task5/                       zero-shot inference, embeddings/probe training, checkpoint 4
  shared/                      labels, wire format, desktop TCP client, evidence helpers
  tools/                       independent checkpoint dashboard, USB utility, verification
  tests/                       implementation and checkpoint-independence tests
  results/                     measured prompts, windows, predictions, provenance and receipts
  artifacts/                   saved embeddings/labels and trained linear head
  logs/                        cloud experiment and server logs
  submission_manifest.json     source mappings, SHA-256 hashes and required-code checks
```

## Required code mapping

| Handout requirement | Submitted files |
| --- | --- |
| Task 1: Dataset and DataLoader | `task1/har_dataset.py`, `task1/download_data.py` |
| Task 2: prompt generation, both inference styles, formatting and test evaluation | `task2/har_gemini.py`, `task2/lab6_dt2811_ms7635_rnb2135_check1.py`, `shared/har_common.py` |
| Task 3: capture ESP32 acceleration, query LLM, display result; Lab 5 extension | `task3/esp32/har_device.py`, `lab5_watch.py`, `ssd1306.py`, checkpoint 2 entry point; `task3/desktop/` app, interpreter and collection CLI |
| Task 4: Flask receive/store endpoint | `task4/lab6_dt2811_ms7635_rnb2135_server.py`, checkpoint 3 ESP32 entry point |
| Task 5.1: zero-shot NormWear | `task5/task5_zero_shot.py`, `task5/setup_normwear.py`, `task5/har_normwear.py` |
| Task 5.2: embeddings and linear head | `task5/task5_linear_probe.py`, `artifacts/embeddings.pt`, `artifacts/linear_probe.pt` |
| Task 5.3: integrated sensor/cloud/OLED pipeline | `task5/esp32/lab6_dt2811_ms7635_rnb2135_check4_esp32.py`, Task 3 shared firmware, Task 4 server, `task5/har_normwear.py` |

## Running the code

Extract the ZIP and run desktop/cloud commands **from the extracted `lab6/` directory using `run.py`**. The launcher supplies shared-module paths and keeps data/results paths at the archive root. ESP32 files are uploaded with their original basenames, not run with desktop Python.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export GEMINI_API_KEY='your own key'

python run.py task1/download_data.py
python run.py task1/har_dataset.py 'data/UCI HAR Dataset'
python run.py task2/lab6_dt2811_ms7635_rnb2135_check1.py 'data/UCI HAR Dataset'
python run.py tools/dashboard.py --host ESP32_IP
```

The dashboard at http://127.0.0.1:8766 tests each checkpoint independently. Checkpoint 1 uses UCI/Gemini; checkpoint 2 uses ESP32/Gemini/OLED; checkpoint 3 uses ESP32/Flask storage; checkpoint 4 uses ESP32/NormWear/probe/OLED. Hardware tests serialize access to the physical watch. The measured experiment used wrist placement.

Upload `task3/esp32/ssd1306.py`, `lab5_watch.py`, `har_device.py`, and the desired checkpoint entry point. Checkpoint 3's entry point is in `task4/esp32/`; checkpoint 4's is in `task5/esp32/`. They all use the Task 3 shared firmware. For example:

```sh
python run.py tools/usb_tool.py --port SERIAL_PORT --upload \
  task3/esp32/ssd1306.py task3/esp32/lab5_watch.py task3/esp32/har_device.py \
  task5/esp32/lab6_dt2811_ms7635_rnb2135_check4_esp32.py
python run.py tools/usb_tool.py --port SERIAL_PORT \
  --start lab6_dt2811_ms7635_rnb2135_check4_esp32.py
```

Wiring: OLED SDA 22/SCL 20, 128×32 at 0x3C. ADXL345 SPI SCK 5/MOSI 19/MISO 21/CS 27. Buttons 12/13/14; piezo 32. Firmware samples three axes, 128 points, 50 Hz, g. Set the actual sensor placement in `har_device.py` and the desktop form. Checkpoint 3/4 cloud URL is the demonstrated public load-balancer endpoint `http://136.82.132.175`, routing to private `esp-cloud:5000`. Update the URL for another deployment. **Restore OLED display** in the dashboard reapplies the controller configuration if needed.

## Cloud model setup and serving

On Compute Engine with at least 16 GB RAM, install matching PyTorch/torchaudio/torchvision packages and `requirements-cloud.txt`, then obtain the pinned official source/checkpoints:

```sh
python run.py task5/setup_normwear.py
python run.py task5/task5_zero_shot.py 'data/UCI HAR Dataset' \
  --repo-parent vendor --weights weights/normwear_pretrain_ckpt.pth \
  --fusion-weights weights/normwear_msitf_zeroshot_last_checkpoint-5.pth
python run.py task5/task5_linear_probe.py 'data/UCI HAR Dataset' \
  --repo-parent vendor --weights weights/normwear_pretrain_ckpt.pth \
  --test-embeddings artifacts/zero_shot_test_embeddings.pt
python run.py task4/lab6_dt2811_ms7635_rnb2135_server.py \
  --repo-parent vendor --weights weights/normwear_pretrain_ckpt.pth \
  --probe artifacts/linear_probe.pt --device cpu
```

The zero-shot text model downloads through the upstream model loader. `NORMWEAR_TEXT_MODEL` can instead point to the identical locally downloaded model for offline use. The encoder/head artifacts and measured results are already included, so benchmark reruns are optional. Keep Flask running in screen for hardware demos. The actual deployment used a load balancer to reach a private VM; direct-public-IP access is another deployment option when permitted by policy.

## Verification and report

```sh
python run.py tests/test_lab6.py
python run.py tests/test_dashboard.py
python run.py tools/verify_cloud_results.py
python run.py tools/make_report.py --root . \
  --output report/lab6_dt2811_ms7635_rnb2135_report.pdf \
  --markdown report/lab6_dt2811_ms7635_rnb2135_report.md
```

The main eight tests and four checkpoint-isolation tests use synthetic fixtures only in temporary directories. Measured result files contain the real experiments. Saved-model verification reproduces all 2,947 test predictions without rerunning the encoder. Actual hardware Gemini accuracy is 6/10 (60%); full-test NormWear accuracy is 11.23% zero-shot and 68.51% with the few-shot probe. The report provides the required examples, comparisons, runtime and pipeline evidence. API keys, virtual environments, downloaded UCI data and large upstream models are excluded; download/setup scripts and provenance are included.
