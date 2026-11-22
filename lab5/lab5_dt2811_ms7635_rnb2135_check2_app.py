"""Desktop app for checkpoints 1 and 2. Run with the lab5 virtual environment.

Voice transcription and manual smartwatch commands are separate until checkpoint 3.
The SmartwatchClient can also be imported for Python/terminal testing.
"""
from datetime import datetime
import json
import socket


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
        now = datetime.now()
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


def build_ui():
    import gradio as gr
    from lab5_dt2811_ms7635_rnb2135_check1 import process_input

    with gr.Blocks(title="Lab 5: Voice and Smartwatch") as ui:
        gr.Markdown("# Lab 5 — Checkpoints 1 and 2")
        with gr.Tab("Voice transcription"):
            audio = gr.Audio(sources=["microphone"], type="filepath", label="Voice Input")
            transcribe = gr.Button("Transcribe")
            transcription = gr.Textbox(label="Transcription/Input")
            transcribe.click(process_input, audio, transcription)
        with gr.Tab("Smartwatch commands"):
            gr.Markdown("Enter the IP printed by the ESP32, then sync its clock before testing.")
            with gr.Row():
                host = gr.Textbox(label="ESP32 IP address", placeholder="192.168.1.100")
                port = gr.Number(label="TCP port", value=8080, precision=0)
            sync = gr.Button("Sync clock to desktop local time")
            command = gr.Textbox(label="JSON command", lines=4,
                                 value='{"name": "display_time", "args": []}')
            gr.Examples(examples=[
                ['{"name": "screen_on", "args": []}'],
                ['{"name": "screen_off", "args": []}'],
                ['{"name": "display_time", "args": []}'],
                ['{"name": "display_text", "args": ["Hello from lab 5!"]}'],
                ['{"name": "set_alarm", "args": [16, 30, 0]}'],
                ['{"name": "display_location", "args": []}'],
                ['{"name": "display_weather", "args": []}'],
                ['{"name": "stop_alarm", "args": []}'],
            ], inputs=[command])
            send = gr.Button("Send command", variant="primary")
            response = gr.Textbox(label="Smartwatch Response")
            send.click(send_from_ui, [host, port, command], response)
            sync.click(sync_from_ui, [host, port], response)
    return ui


if __name__ == "__main__":
    build_ui().launch(debug=False, share=True)
