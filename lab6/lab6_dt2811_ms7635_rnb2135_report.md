# Lab 6: Cloud, Zero-Shot and Few-Shot Human Activity Recognition

EECS E4764 · Fall 2026 | dt2811, ms7635, rnb2135

## Task 2 — LLM prompts

We queried gemini-3.5-flash-lite at temperature 0 for ten test windows selected without replacement using seed 4764. Each pair contains identical device, waist placement, setting, six candidate activities, units, sampling metadata, and six channel arrays. Only the answer instruction changes: step-by-step reasoning followed by LABEL, or one activity label. Call order alternates by sample. Ground-truth labels are used for scoring and are absent from the prompts.

| Test index | Actual activity | CoT | Direct |
| --- | --- | --- | --- |
| 2302 | LAYING | SITTING | WALKING |
| 2505 | WALKING | WALKING | WALKING |
| 212 | LAYING | STANDING | SITTING |
| 1999 | WALKING_DOWNSTAIRS | WALKING | WALKING |
| 2529 | WALKING_DOWNSTAIRS | WALKING | WALKING |
| 2522 | WALKING_DOWNSTAIRS | WALKING | WALKING |
| 1081 | SITTING | STANDING | STANDING |
| 1508 | WALKING_UPSTAIRS | WALKING | WALKING |
| 1412 | SITTING | WALKING | WALKING |
| 452 | WALKING_UPSTAIRS | WALKING | WALKING |

| Six-channel result | CoT | Direct |
| --- | --- | --- |
| Correct / evaluated | 1 / 10 | 1 / 10 |
| Accuracy | 10% | 10% |

The styles agree on 8/10 labels (80%), yet each is correct only once. Both correctly identify walking at test index 2505; they often label stair motion as WALKING and confuse static postures. CoT provides more explanation but does not improve accuracy in this run. Agreement measures consistency between styles, not correctness or repeat-run stability; ten windows and one generation per style cannot establish a general advantage.

<!-- PDF page break -->

## Task 2 — Examples of actual model outputs

The following three paired examples come from the six-channel evaluation. CoT excerpts reproduce each saved response's final reasoning section and final label; full prompts and unabridged outputs are retained in results/llm_uci.json. These explanations are model outputs, not independently established interpretations of the signals.

### Test index 2302 — actual activity: LAYING

```text
CoT output (final section, verbatim):
3. **Conclusion:**
   - The lack of locomotion signatures (no periodic peaks in acceleration or gyro) eliminates WALKING, WALKING_UPSTAIRS, and WALKING_DOWNSTAIRS.
   - The steady signals and lack of high variance point toward a stationary posture, consistent with **SITTING**.

LABEL: SITTING
```

```text
Direct output: WALKING
```

Evaluation: CoT incorrect; direct incorrect; labels disagree.

### Test index 2505 — actual activity: WALKING

```text
CoT output (final section, verbatim):
3. **Conclusion**:
   - The periodic peaks across all axes strongly indicate regular bipedal locomotion, specifically level walking.

LABEL: WALKING
```

```text
Direct output: WALKING
```

Evaluation: CoT correct; direct correct; labels agree.

### Test index 212 — actual activity: LAYING

```text
CoT output (final section, verbatim):
3. **Comparison with Stationary States (`SITTING`, `STANDING`, `LAYING`):**
   - The orientation components (`acc_y` ~ $0.75\text{g}$ and `acc_z` ~ $0.66\text{g}$) reflect a specific orientation of the waist relative to gravity. When a person is standing upright or sitting, the device orientation and lack of dynamic acceleration signatures point toward a posture-based stationary state. Specifically, the steady-state acceleration values without walking cycles strongly support a static posture like standing.

Therefore, the subject is stationary in a standing position.

LABEL: STANDING
```

```text
Direct output: SITTING
```

Evaluation: CoT incorrect; direct incorrect; labels disagree.

Indices 2302 and 212 illustrate that a detailed explanation can still select the wrong static posture. Index 2505 illustrates agreement on a correct walking label. In this small evaluation, longer explanations do not resolve the classification errors seen with direct answers.

<!-- PDF page break -->

## Task 3 — ESP32 + LLM

The wearer attached the ADXL345 to the wrist and selected the actual activity before each trial. Each capture records three chronological acceleration channels in g, retaining gravity. The sensor uses full-resolution ±16 g mode, 50 Hz output, and 0.0039 g/count conversion. Scheduled reads occur every 20 ms for 128 samples. The desktop uses the same prompt builder as Task 2, updates device/placement/setting metadata, and states that gyroscope data is unavailable. Every reported trial uses the direct-answer style. The returned label is sent to the OLED through the Lab 5 display_text command.

Timing measured from the saved timestamps spans 50.0005–50.0007 Hz. Window length, sampling rate, units, and channel ordering match the three-channel benchmark comparison.

| Trial | Actual activity | Gemini prediction | Correct? |
| --- | --- | --- | --- |
| 1 | STANDING | STANDING | Yes |
| 2 | WALKING | WALKING | Yes |
| 3 | WALKING_UPSTAIRS | WALKING | No |
| 4 | SITTING | STANDING | No |
| 5 | SITTING | STANDING | No |
| 6 | WALKING | WALKING | Yes |
| 7 | WALKING | WALKING | Yes |
| 8 | STANDING | STANDING | Yes |
| 9 | LAYING | LAYING | Yes |
| 10 | WALKING_DOWNSTAIRS | WALKING | No |

Hardware accuracy: 6/10 = 60.0%; class coverage: 6/6. Ground truth is the wearer's activity selection. Incorrect predictions are retained and count as incorrect.

| Input and prompt | Correct / trials | Accuracy |
| --- | --- | --- |
| UCI, 6 channels, direct | 1 / 10 | 10% |
| UCI, 3 acceleration channels, direct | 2 / 10 | 20% |
| ESP32, 3 acceleration channels, direct | 6 / 10 | 60.0% |

Generalization: the matched three-channel UCI run uses the same ten test indices as the six-channel run; its CoT/direct accuracies are 10%/20%, with 70% agreement. This comparison controls channel availability when comparing with the ADXL345.

The observed hardware direct-answer accuracy differs from the matched UCI result by +40.0 percentage points. This small convenience sample has a different activity mix from the UCI subsample and is not a paired comparison of identical movements. Wrist placement differs from the UCI smartphone's waist placement, changing orientation and arm-motion content. Sensor characteristics and the collection environment also differ. Equal window lengths therefore do not establish equivalent input distributions.

Observed confusions: WALKING_UPSTAIRS → WALKING (1 trial); SITTING → STANDING (2 trials); WALKING_DOWNSTAIRS → WALKING (1 trial). These observations support limited transfer on this sample, rather than reliable recognition of every activity.

Wearer confirmations of displayed Gemini labels are stored in results/oled_confirmations.jsonl. The ten-trial table is generated from completed labeled sensor/Gemini/OLED records in results/esp32_llm.jsonl.

<!-- PDF page break -->

## Task 5.1 — Zero-Shot NormWear

NormWear ran on esp-cloud in GCP project eecs-aiot, us-east4-b: e2-standard-4, four logical CPUs, 16 GB RAM, Debian 13. No GPU was used. The recorded runtime uses Python 3.13.5 and PyTorch 2.9.1+cpu.

Inputs: all 2,947 official UCI test windows, total acceleration X/Y/Z in g, shape [B,3,128], sampling_rate=50. The text task is 'Which physical activity is the person performing?' The six answer options are:

- The person is walking.

- The person is walking upstairs.

- The person is walking downstairs.

- The person is sitting.

- The person is standing.

- The person is lying down.

We used the official pretrained sensor encoder and MSiTF alignment checkpoints from release v1.0.0-alpha, with optimized_cwt=True for PyTorch wavelets. The zero-shot path embeds the task/options and applies signal_encode and inference to the raw signals. No UCI labels are used for fitting or tuning this zero-shot path.

| Zero-shot measurement | Recorded result |
| --- | --- |
| Correct / full test set | 331 / 2947 |
| Accuracy | 11.23% |
| Inference time (CPU) | 2390.28 s (39.84 min) |
| Total startup + evaluation | 2404.78 s |

The handout's approximate 16% accuracy and 10–20 minute CPU time are references, not acceptance thresholds. Our measured result was lower and slower. In the saved confusion results, zero-shot predictions correctly identify some sitting and downstairs windows, but no correct examples of the other four classes; this indicates limited zero-shot transfer in this configuration. The experiment does not isolate a single cause.

<!-- PDF page break -->

## Task 5.2 — Few-Shot Fine-Tuning

We selected 10 windows per class from the official training split using seed 4764 (60 windows total). The frozen encoder's get_embedding output [B,C,P,768] is averaged over channels and patches to [B,768]. Saved embeddings include [60,768] train and [2947,768] test features plus labels. Test features computed from the same frozen encoder during Task 5.1 were reused before text/query fusion. A fresh encoder call matched a cached feature within 1e-4 tolerance.

Only one Linear(768,6) head is trained for 100 full-batch epochs, with cross-entropy loss and AdamW (learning rate 0.001, weight decay 0.01). Fixed feature standardization is estimated from the 60 selected training examples only. Encoder weights remain frozen; test labels are used only for evaluation and cache-order checks.

| Evaluation on the same 2,947 test windows | Correct | Accuracy |
| --- | --- | --- |
| Pretrained zero-shot model | 331 | 11.23% |
| Frozen encoder + trained linear head | 2019 | 68.51% |
| Absolute improvement |  | +57.28 percentage points |

The small supervised head substantially improves this benchmark result while retaining the pretrained encoder. The saved head reproduces all 2,947 reported predictions when reloaded. Artifacts are artifacts/embeddings.pt and artifacts/linear_probe.pt. The 58.37 s probe workflow reused test embeddings, so it is not a fresh full-test encoder runtime.

## Task 5.3 — End-to-End Pipeline

| Stage | Operation |
| --- | --- |
| 1. ESP32 | ADXL345 captures 3 × 128 total-acceleration readings at 50 Hz in g. |
| 2. Network | ESP32 directly POSTs to /predict through the public load balancer. |
| 3. VM encoder | Convert to float32 [1,3,128]; frozen NormWear get_embedding; mean over channels/patches → [1,768]. |
| 4. VM classifier | Apply saved training-only scaling, Linear(768,6), and softmax; persist input and prediction. |
| 5. ESP32 OLED | Receive label/probabilities/record ID, validate label, and display the label. Gemini is not used. |

Recorded live example — input excerpt (first five chronological samples per axis; the actual request contains all 128):

```text
sampling_rate: 50 Hz | units: g | shape: [3,128]
acc_x: [0.7566, 0.7722, 0.8775, 0.8463, 0.7605] ...
acc_y: [-0.3198, -0.1794, -0.1326, -0.2223, -0.3744] ...
acc_z: [0.5187, 0.3705, 0.1833, 0.2184, 0.4446] ...
```

Returned label: WALKING; server processing time: 0.776 s. This is server inference latency, not capture time plus network round-trip time. The wearer visually confirmed this returned label on the OLED.

```text
record_id: f3fd17432c2746629f9d13938da15c67
probabilities (label order WALKING, UPSTAIRS, DOWNSTAIRS, SITTING, STANDING, LAYING):
0.995073, 0.002413, 0.000529, 0.001980, 0.000000, 0.000004
```

Example persistent storage receipt: a67cdffce2c941b1a86ecb5745fa2442 (stored=true).

Evidence: results/esp32_cloud_demo.jsonl records device commands/receipts; results/cloud_samples.jsonl stores the matching raw inputs/predictions downloaded from the VM; results/oled_confirmations.jsonl records wearer checks. Independent re-encoding of the previously verified live windows reproduced their labels and probabilities exactly. The live cloud demos were unlabeled, so they demonstrate the pipeline and are not a cloud hardware-accuracy test.

### References and reproducibility

[1] EECS E4764 Lab 6 handout, Fall 2026, pp. 7–14. [2] Anguita et al., UCI HAR, ESANN 2013. [3] Ji et al., HARGPT, arXiv:2403.02727. [4] Luo et al., NormWear, arXiv:2412.09758; official source revision 07517fcb13def8c89cb586128359cec02f86ec8d, release v1.0.0-alpha. Checkpoints and environment: results/normwear_setup.json and results/cloud_environment.json.
