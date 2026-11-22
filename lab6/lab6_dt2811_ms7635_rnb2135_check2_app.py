"""Lab 5 voice/text UI extended with the classify_HAR command and labeled capture."""
import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import json
from har_client import SmartwatchClient
from har_common import LABELS, append_jsonl, validate_window
from har_gemini import classify


def classify_HAR(host, port=8080, truth=None, location="waist", style="direct",
                 output="results/esp32_llm.jsonl"):
    client = SmartwatchClient(host, port)
    payload = validate_window(client.send_command("capture_HAR"))
    payload.update(location=location, label=truth or None)
    record = {"captured_at": datetime.now(timezone.utc).isoformat(),
              "truth": truth or None, "window": payload}
    try:
        record.update(classify(payload["data"], style, device=payload["device"],
                               location=location, setting=payload["setting"]))
        if record["label"] is None:
            raise ValueError(record.get("parse_error", "No valid activity label"))
        record["oled_response"] = client.send_command(
            "display_text", [record["label"].replace("_", " ")])
    except Exception as error:
        record["error"] = str(error)
        record.setdefault("label", None)
    # Preserve the actual window and failure evidence as well as successful classifications.
    append_jsonl(output, record)
    return json.dumps(record, indent=2)


async def run_request(text, audio, host, port):
    import lab5_interpreter as interpreter
    if audio:
        text = await asyncio.to_thread(interpreter.transcribe_audio, audio)
    # Lab 5 command interpretation remains available; the new command is explicitly routed.
    if text.strip().lower().replace("_", " ") in (
            "classify har", "classify my activity", "what activity am i doing?",
            "what activity am i doing"):
        result = await asyncio.to_thread(classify_HAR, host, port)
        return text, '{"name":"classify_HAR","args":[]}', result
    command_text = await interpreter.get_llm_response(text)
    command = interpreter.parse_command(command_text)
    if command["name"] == "classify_HAR":
        result = await asyncio.to_thread(classify_HAR, host, port)
        return text, command_text, result
    result = await asyncio.to_thread(SmartwatchClient(host, port).send_command,
                                     command["name"], command["args"])
    return text, command_text, str(result)


def build_ui():
    import gradio as gr
    with gr.Blocks(title="Lab 6: Smartwatch HAR") as ui:
        gr.Markdown("# Lab 6 Smartwatch\nUse classify_HAR to capture and classify your activity.")
        with gr.Row():
            host = gr.Textbox(label="ESP32 IP address")
            port = gr.Number(label="TCP port", value=8080, precision=0)
        with gr.Tab("Activity experiment"):
            truth = gr.Dropdown(choices=list(LABELS), label="Actual activity (set before capture)")
            location = gr.Textbox(label="Sensor placement", value="waist")
            style = gr.Radio(choices=["direct", "cot"], value="direct", label="Prompt style")
            capture = gr.Button("classify_HAR", variant="primary")
            result = gr.Textbox(label="Capture, prediction, OLED result", lines=12)
            capture.click(classify_HAR, [host, port, truth, location, style], result,
                          concurrency_limit=1)
        with gr.Tab("Lab 5 voice and text commands"):
            text = gr.Textbox(label="Request", value="classify_HAR")
            audio = gr.Audio(sources=["microphone"], type="filepath", label="Optional voice request")
            submit = gr.Button("Run request")
            transcription = gr.Textbox(label="Transcription / request")
            command = gr.Textbox(label="Command JSON")
            response = gr.Textbox(label="Response", lines=6)
            submit.click(run_request, [text, audio, host, port],
                         [transcription, command, response], concurrency_limit=1)
            sync = gr.Button("Sync watch clock")
            def sync_clock(host, port):
                from lab5_interpreter import get_current_time
                now = get_current_time()
                return SmartwatchClient(host, port).send_command("set_time", [
                    now.year, now.month, now.day, now.hour, now.minute, now.second])
            sync.click(sync_clock, [host, port], response)
    return ui


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host")
    parser.add_argument("--label", choices=LABELS)
    parser.add_argument("--location", default="waist")
    parser.add_argument("--style", choices=("cot", "direct"), default="direct")
    args = parser.parse_args()
    if args.host:
        print(classify_HAR(args.host, truth=args.label, location=args.location, style=args.style))
    else:
        build_ui().launch(share=False)
