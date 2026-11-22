from functools import lru_cache
import shutil

import truststore

# Use the operating system's trusted certificates for HTTPS model downloads.
truststore.inject_into_ssl()

import gradio as gr
import whisper


@lru_cache(maxsize=1)
def get_whisper_model():
    return whisper.load_model("tiny.en")


def process_input(audio):
    if not audio:
        return ""
    if shutil.which("ffmpeg") is None:
        raise gr.Error("FFmpeg is required. Install the ffmpeg command-line tool and restart the app.")
    whisper_model = get_whisper_model()
    return whisper_model.transcribe(audio, fp16=False)["text"].strip()


ui = gr.Interface(
    inputs=[
        gr.Audio(sources=["microphone"], type="filepath", label="Voice Input"),
    ],
    fn=process_input,
    outputs=[
        gr.Textbox(label="Transcription/Input"),
    ],
    title="Whisper Voice Recognition",
    description="Record your voice, then click Submit to transcribe it. The first transcription downloads the tiny.en model if needed.",
    flagging_mode="never"
)

if __name__ == "__main__":
    ui.launch(debug=False, share=True)
