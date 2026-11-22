"""Checkpoint 4: automatically execute Whisper/Gemini commands on the ESP32."""
import asyncio
import json
import socket

from lab5_dt2811_ms7635_rnb2135_check3 import (
    get_current_time, parse_command,
    process_input as interpret_audio, process_text as interpret_text,
)


class SmartwatchClient:
    """Send newline-delimited JSON over TCP; one command per connection."""

    def __init__(self, host, port=8080, timeout=30):
        self.host = host.strip()
        self.port = int(port)
        self.timeout = timeout
        if not self.host or not 1 <= self.port <= 65535:
            raise ValueError("Enter the ESP32 IP address and a valid port")

    def send_command(self, name, args):
        return self.send_json({"name": name, "args": args})

    def send_json(self, command):
        if not isinstance(command, dict) or set(command) != {"name", "args"}:
            raise ValueError('Use {"name": "function_name", "args": [...]}')
        if not isinstance(command["name"], str) or not isinstance(command["args"], list):
            raise ValueError("name must be a string and args must be a list")
        payload = (json.dumps(command, ensure_ascii=True) + "\n").encode("utf-8")
        if len(payload) > 2048:
            raise ValueError("Command exceeds 2048 bytes")
        with socket.create_connection((self.host, self.port), self.timeout) as connection:
            connection.sendall(payload)
            with connection.makefile("rb") as stream:
                reply = stream.readline(4097)
        if not reply.endswith(b"\n") or len(reply) > 4096:
            raise RuntimeError("Incomplete or oversized ESP32 response")
        response = json.loads(reply)
        if not isinstance(response, dict) or type(response.get("ok")) is not bool:
            raise RuntimeError("Invalid ESP32 response")
        if not response["ok"]:
            raise RuntimeError(response.get("error", "Smartwatch command failed"))
        return response["result"]

    def screen_on(self):
        return self.send_command("screen_on", [])

    def screen_off(self):
        return self.send_command("screen_off", [])

    def display_time(self):
        return self.send_command("display_time", [])

    def display_text(self, text):
        return self.send_command("display_text", [text])

    def set_alarm(self, hour, minute, second):
        return self.send_command("set_alarm", [hour, minute, second])

    def display_location(self):
        return self.send_command("display_location", [])

    def display_weather(self):
        return self.send_command("display_weather", [])

    def sync_time(self):
        now = get_current_time()
        return self.send_command("set_time", [now.year, now.month, now.day,
                                              now.hour, now.minute, now.second])

    def stop_alarm(self):
        return self.send_command("stop_alarm", [])


def send_from_ui(host, port, command_text):
    try:
        result = SmartwatchClient(host, port).send_json(json.loads(command_text))
        return result
    except (ValueError, OSError, RuntimeError, KeyError) as error:
        return "Error: " + str(error)


def sync_from_ui(host, port):
    try:
        return SmartwatchClient(host, port).sync_time()
    except (ValueError, OSError, RuntimeError, KeyError) as error:
        return "Error: " + str(error)


def send_generated_command(host, port, command_text):
    try:
        command = parse_command(command_text)
        return SmartwatchClient(host, port).send_json(command)
    except (ValueError, OSError, RuntimeError, KeyError) as error:
        return "Error: " + str(error)


async def execute_interpretation(result, host, port):
    transcription, command_json, status = result
    if not command_json:
        return transcription, "", status
    # The interpreter already validates JSON; validate again at the send boundary.
    response = await asyncio.to_thread(send_generated_command, host, port, command_json)
    return transcription, command_json, response


async def process_input(audio, host, port):
    return await execute_interpretation(await interpret_audio(audio), host, port)


async def process_text(text, host, port):
    return await execute_interpretation(await interpret_text(text), host, port)


def build_ui():
    import gradio as gr
    with gr.Blocks(title="Lab 5: Voice-Controlled Smartwatch") as ui:
        gr.Markdown("# Lab 5 — Checkpoint 4\nRecord speech or type a request to control your smartwatch.")
        with gr.Row():
            host = gr.Textbox(label="ESP32 IP address", placeholder="192.168.1.100")
            port = gr.Number(label="TCP port", value=8080, precision=0)
        sync = gr.Button("Sync clock to app local time")
        with gr.Tab("Voice input"):
            audio = gr.Audio(sources=["microphone"], type="filepath", label="Voice Input")
            submit_voice = gr.Button("Run voice command", variant="primary")
        with gr.Tab("Text input"):
            text = gr.Textbox(label="Request", placeholder="Set an alarm in five minutes")
            submit_text = gr.Button("Run text command", variant="primary")
        transcription = gr.Textbox(label="Transcription/Input")
        command = gr.Textbox(label="LLM Response JSON", lines=6, interactive=False)
        response = gr.Textbox(label="Smartwatch Response")
        submit_voice.click(process_input, [audio, host, port], [transcription, command, response],
                           concurrency_limit=1)
        submit_text.click(process_text, [text, host, port], [transcription, command, response])
        sync.click(sync_from_ui, [host, port], response)
    return ui


if __name__ == "__main__":
    build_ui().launch(debug=False, share=True)
