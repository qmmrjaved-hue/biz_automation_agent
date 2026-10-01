"""
transcribe_adapter.py — transcribes an audio file to text using OpenAI Whisper
(local). Ported from Voice2Query's transcribe.py, which proved out the
ffmpeg-on-PATH workaround for Windows WinGet installs.

Public function:
  - transcribe(audio_path, model_size="base", language=None) -> str
"""

import os
import shutil


def _ensure_ffmpeg() -> None:
    """
    Make sure ffmpeg is reachable before Whisper tries to spawn it.

    WinGet installs update the Windows registry but processes launched
    beforehand inherit a stale PATH snapshot; this patches the running
    process's PATH so it can find a newly-installed ffmpeg without a restart.
    """
    if shutil.which("ffmpeg"):
        return

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    winget_pkgs = os.path.join(local_app_data, "Microsoft", "WinGet", "Packages")

    if os.path.isdir(winget_pkgs):
        for root, _dirs, files in os.walk(winget_pkgs):
            if "ffmpeg.exe" in files:
                os.environ["PATH"] = root + os.pathsep + os.environ.get("PATH", "")
                print(f"[transcribe_adapter] Added ffmpeg to PATH from: {root}")
                return


def transcribe(audio_path: str, model_size: str = "base", language: str = None) -> str:
    """
    Transcribe an audio file to a text string using a local Whisper model.

    Args:
        audio_path:  Path to the audio file (WAV, MP3, M4A, FLAC, etc.).
        model_size:  Whisper model variant — "tiny", "base", "small", "medium",
                     or "large". Defaults to "base".
        language:    Optional ISO-639-1 language code to force (e.g. "it", "en").
                     None means auto-detect.

    Returns:
        The transcribed text as a stripped string.

    Raises:
        FileNotFoundError: if audio_path does not exist.
        RuntimeError: if Whisper fails to load the model, ffmpeg is missing,
            or transcription fails.
    """
    import whisper  # imported lazily — heavy dependency, only needed here

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"[transcribe_adapter] Audio file not found: '{audio_path}'")

    try:
        print(f"[transcribe_adapter] Loading Whisper model '{model_size}' ...")
        model = whisper.load_model(model_size)
    except Exception as e:
        raise RuntimeError(f"[transcribe_adapter] Failed to load Whisper model '{model_size}': {e}") from e

    _ensure_ffmpeg()
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "[transcribe_adapter] ffmpeg is not installed or not on PATH. "
            "Install it with: winget install Gyan.FFmpeg  "
            "then restart your terminal."
        )

    try:
        print(f"[transcribe_adapter] Transcribing '{audio_path}' ...")
        options = {"language": language} if language else {}
        result = model.transcribe(audio_path, fp16=False, **options)
        text = result["text"].strip()
        print(f"[transcribe_adapter] Result: {text!r}")
        return text
    except Exception as e:
        raise RuntimeError(f"[transcribe_adapter] Transcription failed for '{audio_path}': {e}") from e
