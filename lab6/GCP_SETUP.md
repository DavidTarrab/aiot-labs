# Compute Engine setup

The handout requires Tasks 4–5 on a Compute Engine VM. No homebase files or settings were accessed or changed.

## Instance

Create a Linux VM with Ubuntu 24.04 LTS, an external IPv4 address, at least 16 GB RAM and a 50 GB boot disk. `e2-standard-4` is the handout's CPU option. A GPU instance with one NVIDIA L4 is optional; use a compatible GPU machine configuration and installed NVIDIA drivers. Give the instance the network tag `lab6-har`.

When it is ready, share the instance name, project ID, zone, and your preferred SSH connection method so the remaining experiments can be run. An external IP alone does not grant SSH access.

Google's references: [create an instance](https://docs.cloud.google.com/compute/docs/instances/create-start-instance), [VPC firewall rules](https://docs.cloud.google.com/firewall/docs/using-firewalls).

For the direct ESP32 demo, add an ingress rule allowing TCP 5000 to the `lab6-har` tag. Use the ESP32 network's public egress IP range as the source when available. The board's `10.206.190.234` address is private and is not the firewall source seen by GCP. If using `gcloud`, substitute your values:

```sh
gcloud compute firewall-rules create lab6-har-5000 \
  --network=default --direction=INGRESS --action=ALLOW \
  --rules=tcp:5000 --source-ranges=YOUR_PUBLIC_EGRESS_IP/32 \
  --target-tags=lab6-har
```

## Upload

Generate the code ZIP on the Mac (see README), then upload it using the Console SSH file upload or the command below. Until all evidence is collected, the packager produces `lab6_dt2811_ms7635_rnb2135_draft.zip`; substitute that filename when deploying an incomplete lab:

```sh
gcloud compute scp lab6_dt2811_ms7635_rnb2135.zip INSTANCE:~/ --zone=ZONE
gcloud compute ssh INSTANCE --zone=ZONE
```

On the VM:

```sh
sudo apt-get update
sudo apt-get install -y python3-venv unzip screen
mkdir -p ~/aiot
unzip -o ~/lab6_dt2811_ms7635_rnb2135.zip -d ~/aiot
cd ~/aiot/lab6
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

CPU installation:

```sh
python -m pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-cloud.txt
```

For GPU installation, first verify `nvidia-smi`, then use the matching torch/torchaudio/torchvision command from the [official PyTorch installer](https://pytorch.org/get-started/locally/). Verify `python -c 'import torch; print(torch.cuda.is_available())'` prints `True`. Use `--device cuda` in the experiment and server commands below. CPU uses `--device cpu`.

## Checkpoint 3: receive and persist

```sh
screen -S lab6-storage
python lab6_dt2811_ms7635_rnb2135_server.py
```

Detach with Ctrl-A then D. Reattach with `screen -r lab6-storage`. Open `http://VM_EXTERNAL_IP:5000/` in the browser; it should return `status: ok` and `prediction_ready: false`.

Set `CLOUD_URL` in `lab6_dt2811_ms7635_rnb2135_check3_esp32.py`, upload it plus the shared firmware files, and run it. Press button A. Inspect the persisted file on the VM:

```sh
tail -n 1 results/cloud_samples.jsonl
```

It must contain the received UUID, timestamp and three arrays of 128 numbers. Keep that log for the report. Restart the server and confirm the earlier record is still present.

## Task 5: source, checkpoints, zero-shot and probe

```sh
python setup_normwear.py
python download_data.py
python har_dataset.py 'data/UCI HAR Dataset'
python task5_zero_shot.py 'data/UCI HAR Dataset' \
  --repo-parent vendor --weights weights/normwear_pretrain_ckpt.pth \
  --fusion-weights weights/normwear_msitf_zeroshot_last_checkpoint-5.pth \
  --device cpu
python task5_linear_probe.py 'data/UCI HAR Dataset' \
  --repo-parent vendor --weights weights/normwear_pretrain_ckpt.pth \
  --device cpu --shots 10 --epochs 100
```

Run long commands inside a screen session. `setup_normwear.py` downloads about 775 MB of encoder/fusion weights, pins the source revision, and records checksums. Zero-shot additionally downloads the upstream TinyLlama clinical text model from Hugging Face. Allow several GB of disk space. A CPU evaluation can take approximately 10–20 minutes per the handout; measured runtimes are saved separately. Both paths use the PyTorch wavelet implementation and three acceleration channels. Fusion weights load strictly so a failed load cannot silently evaluate a random aggregator.

## Checkpoint 4: serve the trained model

Stop the storage-only server with Ctrl-C in its screen session, then:

```sh
python lab6_dt2811_ms7635_rnb2135_server.py \
  --repo-parent vendor --weights weights/normwear_pretrain_ckpt.pth \
  --probe artifacts/linear_probe.pt --device cpu
```

The health endpoint now shows `prediction_ready: true`. Set `CLOUD_URL` in the checkpoint 4 ESP32 script, upload and run it, then press A. The board captures a window, posts it directly to the VM, receives the probe prediction, and displays it. Keep the serial response and a photo of the OLED. The JSONL log includes both the real input and the model output.

Copy the JSON/JSONL results back to the Mac's `lab6/results/` (merge cloud logs if both locations already contain captures). Also copy `artifacts/embeddings.pt` and `artifacts/linear_probe.pt` to the Mac's `lab6/artifacts/` so the ZIP can include the compact trained probe and measured embeddings. Regenerate the report and ZIP. Keep the artifacts on the VM for the demo. The ZIP omits the large pretrained encoder/text weights and redundant zero-shot cache, while including the scripts needed to reproduce them.

Stop the VM when finished, as the handout requests. Stopping the VM does not delete its disk or the stored experiment files.

## Existing instance: esp-cloud

The actual deployment is Debian 13/Python 3.13 on `esp-cloud` in project `eecs-aiot`, zone `us-east4-b`. SSH currently uses IAP because the project organization policy initially rejected external addresses. The runtime, data, official checkpoints, and local text model have been uploaded under `~/aiot/lab6`. The CPU package pins are in `cloud-constraints.txt`, with complete installed versions in the experiment environment JSON.

Connect and monitor the persistent experiment session:

```sh
gcloud compute ssh esp-cloud --project=eecs-aiot --zone=us-east4-b
cd ~/aiot/lab6
tail -n 20 logs/cloud_run.log
screen -r lab6-experiments
```

Detach with Ctrl-A then D. The preliminary diagnostic log is kept separately as `logs/initial_probe_diagnostic.log`; final reported metrics come from the completed experiment JSONs. The efficient run uses `run_cloud_experiments.py`, which performs zero-shot first and reuses its frozen mean-pooled test embeddings for the linear probe.

The VM carries tag `lab6-har`. Firewall rule `lab6-har-campus-5000` allows TCP 5000 from the observed ESP32 public egress address `129.236.226.103/32`. The latest observed board LAN address is `10.206.89.108`; both addresses can change. The external-IP organization-policy exception is still a prerequisite to direct ESP32 access. A browser/SSH connection to the VM does not prove the board can reach Flask.

After stopping the VM between sessions, start it again and launch the saved model server:

```sh
gcloud compute instances start esp-cloud --project=eecs-aiot --zone=us-east4-b
gcloud compute ssh esp-cloud --project=eecs-aiot --zone=us-east4-b
cd ~/aiot/lab6
screen -S lab6-server
NORMWEAR_NUM_THREADS=4 .venv/bin/python lab6_dt2811_ms7635_rnb2135_server.py \
  --repo-parent vendor --weights weights/normwear_pretrain_ckpt.pth \
  --probe artifacts/linear_probe.pt --device cpu
```

Detach with Ctrl-A then D. Training does not need to be repeated. Once an external-IP exception is approved, attach the address, set the firmware `CLOUD_URL`, and run the two device demonstration commands documented in README. If the network's egress IP changed, update the firewall source accordingly.
