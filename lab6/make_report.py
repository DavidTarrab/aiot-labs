"""Build a fresh, evidence-based PDF and Markdown report matching Lab 6 pp. 7–14."""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate,
                               Spacer, Table, TableStyle)

from har_common import LABELS, validate_window, write_json
from lab_status import completed_hardware, lines, load, pending_evidence

NAME = "lab6_dt2811_ms7635_rnb2135_report"


def accuracy(result):
    hits = sum(p == y for p, y in zip(result["predictions"], result["truths"]))
    count = len(result["truths"])
    assert len(result["predictions"]) == count == 2947
    assert abs(hits / count - result["accuracy"]) < 1e-6
    return hits, count, hits / count


def conclusion_excerpt(text):
    # Quote the saved response's final reasoning section, rather than inventing a summary.
    match = re.search(r"(?m)^3\.\s", text)
    excerpt = text[match.start():] if match else text
    return excerpt.strip()


def build_sections(root):
    results = root / "results"
    llm = load(results / "llm_uci.json")
    accel = load(results / "llm_uci_accel.json")
    zero = load(results / "normwear_zero_shot.json")
    probe = load(results / "linear_probe.json")
    environment = load(results / "cloud_environment.json")
    hardware = completed_hardware(root)
    demos = lines(results / "esp32_cloud_demo.jsonl")
    cloud_records = {r["id"]: r for r in lines(results / "cloud_samples.jsonl")}
    confirmations = lines(results / "oled_confirmations.jsonl")
    pending = pending_evidence(root)
    zero_hits, test_count, zero_acc = accuracy(zero)
    probe_hits, _, probe_acc = accuracy(probe)
    assert zero["truths"] == probe["truths"]
    assert llm["completed"] == len(llm["records"]) == 10
    for style in ("cot", "direct"):
        assert sum(r[style]["label"] == r["truth"] for r in llm["records"]) / 10 == llm[style + "_accuracy"]
    coverage = Counter(r["truth"] for r in hardware)
    hardware_hits = sum(r["truth"] == r["label"] for r in hardware)
    hardware_acc = hardware_hits / len(hardware) if hardware else None
    model = llm["records"][0]["direct"].get("model", "not recorded")
    blocks = []
    def add(kind, value):
        blocks.append((kind, value))
    def p(value):
        add("p", value)
    def h(value):
        add("h2", value)
    def table(value):
        add("table", value)

    add("title", "Lab 6: Cloud, Zero-Shot and Few-Shot Human Activity Recognition")
    p("EECS E4764 · Fall 2026 | dt2811, ms7635, rnb2135")
    if pending:
        add("note", "DRAFT — awaiting: " + "; ".join(pending) + ". All reported measurements below are recorded observations.")
    h("Task 2 — LLM prompts")
    p(f"We queried {model} at temperature 0 for ten test windows selected without replacement using seed {llm['seed']}. "
      "Each pair contains identical device, waist placement, setting, six candidate activities, units, sampling metadata, "
      "and six channel arrays. Only the answer instruction changes: step-by-step reasoning followed by LABEL, or one activity label. "
      "Call order alternates by sample. Ground-truth labels are used for scoring and are absent from the prompts.")
    table([["Test index", "Actual activity", "CoT", "Direct"]] +
          [[r["index"], r["truth"], r["cot"]["label"], r["direct"]["label"]] for r in llm["records"]])
    table([["Six-channel result", "CoT", "Direct"],
           ["Correct / evaluated", "1 / 10", "1 / 10"],
           ["Accuracy", f"{llm['cot_accuracy']:.0%}", f"{llm['direct_accuracy']:.0%}"]])
    p(f"The styles agree on {round(10 * llm['agreement'])}/10 labels ({llm['agreement']:.0%}), yet each is correct only once. "
      "Both correctly identify walking at test index 2505; they often label stair motion as WALKING and confuse static postures. "
      "CoT provides more explanation but does not improve accuracy in this run. Agreement measures consistency between styles, "
      "not correctness or repeat-run stability; ten windows and one generation per style cannot establish a general advantage.")

    add("page", None)
    h("Task 2 — Examples of actual model outputs")
    p("The following three paired examples come from the six-channel evaluation. CoT excerpts reproduce each saved response's "
      "final reasoning section and final label; full prompts and unabridged outputs are retained in results/llm_uci.json. "
      "These explanations are model outputs, not independently established interpretations of the signals.")
    for index in (2302, 2505, 212):
        record = next(r for r in llm["records"] if r["index"] == index)
        add("h3", f"Test index {index} — actual activity: {record['truth']}")
        add("quote", "CoT output (final section, verbatim):\n" + conclusion_excerpt(record["cot"]["output"]))
        add("code", "Direct output: " + record["direct"]["output"].strip())
        p("Evaluation: CoT " + ("correct" if record["cot"]["label"] == record["truth"] else "incorrect") +
          "; direct " + ("correct" if record["direct"]["label"] == record["truth"] else "incorrect") +
          "; labels " + ("agree." if record["cot"]["label"] == record["direct"]["label"] else "disagree."))
    p("Indices 2302 and 212 illustrate that a detailed explanation can still select the wrong static posture. "
      "Index 2505 illustrates agreement on a correct walking label. In this small evaluation, longer explanations "
      "do not resolve the classification errors seen with direct answers.")

    add("page", None)
    h("Task 3 — ESP32 + LLM")
    p("The wearer attached the ADXL345 to the wrist and selected the actual activity before each trial. "
      "Each capture records three chronological acceleration channels in g, retaining gravity. The sensor uses "
      "full-resolution ±16 g mode, 50 Hz output, and 0.0039 g/count conversion. Scheduled reads occur every 20 ms "
      "for 128 samples. The desktop uses the same prompt builder as Task 2, updates device/placement/setting metadata, "
      "and states that gyroscope data is unavailable. Every reported trial uses the direct-answer style. "
      "The returned label is sent to the OLED through the Lab 5 display_text command.")
    rates = []
    for r in hardware:
        validate_window(r["window"])
        stamps = r["window"]["timestamps_us"]
        rates.append(127000000 / (stamps[-1] - stamps[0]))
    if rates:
        p(f"Timing measured from the saved timestamps spans {min(rates):.4f}–{max(rates):.4f} Hz. "
          "Window length, sampling rate, units, and channel ordering match the three-channel benchmark comparison.")
    rows = [["Trial", "Actual activity", "Gemini prediction", "Correct?"]]
    for i, r in enumerate(hardware, 1):
        rows.append([i, r["truth"], r["label"], "Yes" if r["truth"] == r["label"] else "No"])
    missing = [label for label in LABELS if label not in coverage]
    for i in range(len(hardware), 10):
        label = missing[i - len(hardware)] if i - len(hardware) < len(missing) else "Additional trial"
        rows.append([i + 1, label, "PENDING", "Not collected"])
    table(rows)
    if hardware:
        p(f"Hardware accuracy: {hardware_hits}/{len(hardware)} = {hardware_acc:.1%}; class coverage: {len(coverage)}/6. "
          "Ground truth is the wearer's activity selection. Incorrect predictions are retained and count as incorrect.")
    if missing:
        add("note", "Still required for the ten-sample experiment: " + ", ".join(missing) + ".")
    table([["Input and prompt", "Correct / trials", "Accuracy"],
           ["UCI, 6 channels, direct", "1 / 10", f"{llm['direct_accuracy']:.0%}"],
           ["UCI, 3 acceleration channels, direct", "2 / 10", f"{accel['direct_accuracy']:.0%}"],
           ["ESP32, 3 acceleration channels, direct", f"{hardware_hits} / {len(hardware)}",
            f"{hardware_acc:.1%}" if hardware else "Pending"]])
    p("Generalization: the matched three-channel UCI run uses the same ten test indices as the six-channel run; "
      f"its CoT/direct accuracies are {accel['cot_accuracy']:.0%}/{accel['direct_accuracy']:.0%}, with {accel['agreement']:.0%} "
      "agreement. This comparison controls channel availability when comparing with the ADXL345.")
    if hardware:
        p(f"The observed hardware direct-answer accuracy differs from the matched UCI result by "
          f"{100 * (hardware_acc - accel['direct_accuracy']):+.1f} percentage points. "
          "This small convenience sample has a different activity mix from the UCI subsample and is not a paired comparison of identical movements. "
          "Wrist placement differs from the UCI smartphone's waist placement, changing orientation and arm-motion content. "
          "Sensor characteristics and the collection environment also differ. Equal window lengths therefore do not establish equivalent input distributions.")
        errors = Counter((r["truth"], r["label"]) for r in hardware if r["truth"] != r["label"])
        if errors:
            p("Observed confusions: " + "; ".join(f"{a} → {b} ({n} trial{'s' if n != 1 else ''})" for (a,b),n in errors.items()) +
              ". These observations support limited transfer on this sample, rather than reliable recognition of every activity.")
    p("Wearer confirmations of displayed Gemini labels are stored in results/oled_confirmations.jsonl. "
      "The ten-trial table is generated from completed labeled sensor/Gemini/OLED records in results/esp32_llm.jsonl.")

    add("page", None)
    h("Task 5.1 — Zero-Shot NormWear")
    p("NormWear ran on esp-cloud in GCP project eecs-aiot, us-east4-b: e2-standard-4, four logical CPUs, "
      "16 GB RAM, Debian 13. No GPU was used. The recorded runtime uses Python " + environment["python"] +
      " and PyTorch " + environment["packages"].get("torch", "unknown") + ".")
    p("Inputs: all 2,947 official UCI test windows, total acceleration X/Y/Z in g, shape [B,3,128], "
      "sampling_rate=50. The text task is 'Which physical activity is the person performing?' The six answer options are:")
    for option in zero["options"]:
        add("bullet", option)
    p("We used the official pretrained sensor encoder and MSiTF alignment checkpoints from release v1.0.0-alpha, "
      "with optimized_cwt=True for PyTorch wavelets. The zero-shot path embeds the task/options and applies "
      "signal_encode and inference to the raw signals. No UCI labels are used for fitting or tuning this zero-shot path.")
    table([["Zero-shot measurement", "Recorded result"],
           ["Correct / full test set", f"{zero_hits} / {test_count}"],
           ["Accuracy", f"{zero_acc:.2%}"],
           ["Inference time (CPU)", f"{zero['inference_seconds']:.2f} s ({zero['inference_seconds']/60:.2f} min)"],
           ["Total startup + evaluation", f"{zero['total_seconds']:.2f} s"]])
    p("The handout's approximate 16% accuracy and 10–20 minute CPU time are references, not acceptance thresholds. "
      "Our measured result was lower and slower. In the saved confusion results, zero-shot predictions correctly identify "
      "some sitting and downstairs windows, but no correct examples of the other four classes; this indicates limited "
      "zero-shot transfer in this configuration. The experiment does not isolate a single cause.")
    add("page", None)
    h("Task 5.2 — Few-Shot Fine-Tuning")
    p(f"We selected {probe['shots']} windows per class from the official training split using seed {probe['seed']} "
      f"({probe['train_count']} windows total). The frozen encoder's get_embedding output [B,C,P,768] is averaged over "
      "channels and patches to [B,768]. Saved embeddings include [60,768] train and [2947,768] test features plus labels. "
      "Test features computed from the same frozen encoder during Task 5.1 were reused before text/query fusion. "
      "A fresh encoder call matched a cached feature within 1e-4 tolerance.")
    p("Only one Linear(768,6) head is trained for 100 full-batch epochs, with cross-entropy loss and AdamW "
      "(learning rate 0.001, weight decay 0.01). Fixed feature standardization is estimated from the 60 selected training "
      "examples only. Encoder weights remain frozen; test labels are used only for evaluation and cache-order checks.")
    table([["Evaluation on the same 2,947 test windows", "Correct", "Accuracy"],
           ["Pretrained zero-shot model", zero_hits, f"{zero_acc:.2%}"],
           ["Frozen encoder + trained linear head", probe_hits, f"{probe_acc:.2%}"],
           ["Absolute improvement", "", f"+{100*(probe_acc-zero_acc):.2f} percentage points"]])
    p("The small supervised head substantially improves this benchmark result while retaining the pretrained encoder. "
      "The saved head reproduces all 2,947 reported predictions when reloaded. Artifacts are artifacts/embeddings.pt "
      "and artifacts/linear_probe.pt. The 58.37 s probe workflow reused test embeddings, so it is not a fresh full-test encoder runtime.")

    h("Task 5.3 — End-to-End Pipeline")
    table([["Stage", "Operation"],
           ["1. ESP32", "ADXL345 captures 3 × 128 total-acceleration readings at 50 Hz in g."],
           ["2. Network", "ESP32 directly POSTs to /predict through the public load balancer."],
           ["3. VM encoder", "Convert to float32 [1,3,128]; frozen NormWear get_embedding; mean over channels/patches → [1,768]."],
           ["4. VM classifier", "Apply saved training-only scaling, Linear(768,6), and softmax; persist input and prediction."],
           ["5. ESP32 OLED", "Receive label/probabilities/record ID, validate label, and display the label. Gemini is not used."]])
    predictions = [r for r in demos if r.get("ok") and r.get("stage") == "prediction" and r["result"]["id"] in cloud_records]
    # Prefer an input whose displayed cloud label the wearer explicitly confirmed.
    confirmed_ids = {r.get("record_id") for r in confirmations if r.get("source") == "cloud"}
    chosen = next((r for r in reversed(predictions) if r["result"]["id"] in confirmed_ids), predictions[-1] if predictions else None)
    used_ids = []
    if chosen:
        identifier = chosen["result"]["id"]
        stored = cloud_records[identifier]
        payload = validate_window(stored["window"])
        prediction = stored["prediction"]
        assert prediction["label"] == chosen["result"]["label"]
        used_ids.append(identifier)
        p("Recorded live example — input excerpt (first five chronological samples per axis; the actual request contains all 128):")
        add("code", "sampling_rate: 50 Hz | units: g | shape: [3,128]\n" +
            "\n".join(f"acc_{axis}: {channel[:5]} ..." for axis,channel in zip("xyz",payload["data"])))
        p(f"Returned label: {prediction['label']}; server processing time: {prediction['seconds']:.3f} s. "
          "This is server inference latency, not capture time plus network round-trip time. " +
          ("The wearer visually confirmed this returned label on the OLED." if identifier in confirmed_ids else "The firmware acknowledged the display command."))
        add("code", "record_id: " + identifier + "\nprobabilities (label order WALKING, UPSTAIRS, DOWNSTAIRS, SITTING, STANDING, LAYING):\n" +
            ", ".join(f"{v:.6f}" for v in prediction["probabilities"]))
    latest_storage = next((r for r in reversed(demos) if r.get("ok") and r["stage"] == "storage" and r["result"]["id"] in cloud_records), None)
    if latest_storage:
        used_ids.append(latest_storage["result"]["id"])
        p("Example persistent storage receipt: " + latest_storage["result"]["id"] + " (stored=true).")
    p("Evidence: results/esp32_cloud_demo.jsonl records device commands/receipts; results/cloud_samples.jsonl stores the "
      "matching raw inputs/predictions downloaded from the VM; results/oled_confirmations.jsonl records wearer checks. "
      "Independent re-encoding of the previously verified live windows reproduced their labels and probabilities exactly. "
      "The live cloud demos were unlabeled, so they demonstrate the pipeline and are not a cloud hardware-accuracy test.")
    add("h3", "References and reproducibility")
    p("[1] EECS E4764 Lab 6 handout, Fall 2026, pp. 7–14. [2] Anguita et al., UCI HAR, ESANN 2013. "
      "[3] Ji et al., HARGPT, arXiv:2403.02727. [4] Luo et al., NormWear, arXiv:2412.09758; official source "
      "revision 07517fcb13def8c89cb586128359cec02f86ec8d, release v1.0.0-alpha. Checkpoints and environment: "
      "results/normwear_setup.json and results/cloud_environment.json.")
    manifest = {"generated_at": datetime.now(ZoneInfo("America/New_York")).isoformat(),
                "hardware_count": len(hardware), "hardware_correct": hardware_hits, "hardware_coverage": dict(coverage),
                "hardware_accuracy": hardware_acc, "pending": pending, "example_cloud_ids": used_ids,
                "requirements": {"Task 2 paired output examples": True, "Task 2 ten-window accuracy and consistency": True,
                                 "Task 3 ten samples covering all classes": len(hardware) >= 10 and len(coverage) == 6,
                                 "Task 3 measured generalization discussion": bool(hardware),
                                 "Task 5.1 input, accuracy, CPU runtime": True,
                                 "Task 5.2 before/after accuracy": True,
                                 "Task 5.3 pipeline and real input/output evidence": bool(chosen)}}
    return blocks, manifest


def render_markdown(blocks):
    output = []
    for kind, value in blocks:
        if kind in ("title", "h2", "h3"):
            output.append({"title": "# ", "h2": "## ", "h3": "### "}[kind] + value)
        elif kind == "table":
            output.append("\n".join("| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |"
                                    for row in [value[0], ["---"] * len(value[0]), *value[1:]]))
        elif kind in ("quote", "code"):
            output.append("```text\n" + value + "\n```")
        elif kind == "bullet":
            output.append("- " + value)
        elif kind == "page":
            output.append("<!-- PDF page break -->")
        else:
            output.append(value)
    return "\n\n".join(output) + "\n"


def render_pdf(blocks, destination):
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportBody", fontName="Helvetica", fontSize=9, leading=12,
                              spaceAfter=6, textColor=colors.HexColor("#172338")))
    styles.add(ParagraphStyle(name="ReportQuote", parent=styles["ReportBody"], fontSize=8.6, leading=11.3,
                              leftIndent=10, borderPadding=9, backColor=colors.HexColor("#f2f5fa")))
    styles.add(ParagraphStyle(name="ReportCode", parent=styles["ReportBody"], fontName="Courier",
                              fontSize=7.6, leading=10, backColor=colors.HexColor("#f2f5fa"), borderPadding=7))
    styles.add(ParagraphStyle(name="ReportCell", parent=styles["ReportBody"], fontSize=8, leading=10.2, spaceAfter=0))
    styles["Title"].fontSize, styles["Title"].leading, styles["Title"].alignment = 18, 22, TA_LEFT
    styles["Heading2"].fontSize, styles["Heading2"].leading = 12, 16
    styles["Heading3"].fontSize, styles["Heading3"].leading = 10, 13
    story = []
    def paragraph(text, style):
        return Paragraph(escape(str(text)).replace("\n", "<br/>"), styles[style])
    for kind, value in blocks:
        if kind == "page":
            story.append(PageBreak())
        elif kind == "table":
            count = len(value[0])
            if count == 4:
                widths = [50, 157, 157, 160] if value[0][0] == "Test index" else [45, 168, 168, 143]
            elif count == 3:
                widths = [310, 100, 114]
            else:
                widths = [150, 374]
            cells = [[paragraph(c, "ReportCell") for c in row] for row in value]
            t = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
            t.setStyle(TableStyle([("BACKGROUND", (0,0),(-1,0),colors.HexColor("#e3ebf8")),
                                   ("VALIGN",(0,0),(-1,-1),"TOP"),
                                   ("LINEBELOW",(0,0),(-1,0),0.7,colors.HexColor("#b0c0da")),
                                   ("LINEBELOW",(0,1),(-1,-1),0.25,colors.HexColor("#d6deeb")),
                                   ("TOPPADDING",(0,0),(-1,-1),5), ("BOTTOMPADDING",(0,0),(-1,-1),5)]))
            story.extend([t, Spacer(1,8)])
        else:
            style = {"title":"Title", "h2":"Heading2", "h3":"Heading3", "quote":"ReportQuote",
                     "code":"ReportCode", "note":"ReportQuote"}.get(kind,"ReportBody")
            story.append(paragraph(("• " if kind == "bullet" else "") + value, style))
    def footer(canvas, document):
        canvas.setStrokeColor(colors.HexColor("#d6deeb"))
        canvas.line(44,39,568,39)
        canvas.setFont("Helvetica",8)
        canvas.drawString(44,26,"Lab 6 | dt2811 · ms7635 · rnb2135")
        canvas.drawRightString(568,26,str(document.page))
    SimpleDocTemplate(str(destination), pagesize=(612,792), leftMargin=44,rightMargin=44,
                      topMargin=38,bottomMargin=50,title="Lab 6: Human Activity Recognition",
                      author="dt2811, ms7635, rnb2135").build(story,onFirstPage=footer,onLaterPages=footer)


def make_report(root, destination=None, markdown=None):
    root = Path(root).resolve()
    destination = Path(destination) if destination else root / (NAME + ".pdf")
    markdown = Path(markdown) if markdown else root / (NAME + ".md")
    blocks, manifest = build_sections(root)
    destination.parent.mkdir(parents=True,exist_ok=True)
    markdown.write_text(render_markdown(blocks))
    render_pdf(blocks,destination)
    write_json(root / "results/report_requirements.json",manifest)
    print("Report:",destination)
    print("Editable text:",markdown)
    print("Pending:",manifest["pending"])
    return manifest


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",default=".")
    parser.add_argument("--output")
    parser.add_argument("--markdown")
    args=parser.parse_args()
    make_report(args.root,args.output,args.markdown)
