"""A private LFX HTTP process owned by this Streamlit deployment."""

from __future__ import annotations

import atexit
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time

import requests


class FlowRuntime:
    def __init__(self, flow_path: Path, openai_api_key: str):
        self.api_key = secrets.token_urlsafe(32)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.base_url = f"http://127.0.0.1:{port}"
        self.flow_id = json.loads(flow_path.read_text())["id"]
        self.log = tempfile.TemporaryFile(mode="w+")
        env = os.environ.copy()
        env.update({
            "LANGFLOW_API_KEY": self.api_key,
            "OPENAI_API_KEY": openai_api_key,
            "LANGFLOW_FALLBACK_TO_ENV_VAR": "true",
            "LANGFLOW_DO_NOT_TRACK": "true",
            "DO_NOT_TRACK": "1",
        })
        command = [
            shutil.which("lfx") or str(Path(sys.executable).with_name("lfx")),
            "serve", str(flow_path.resolve()),
            "--host", "127.0.0.1", "--port", str(port),
            "--log-level", "error",
        ]
        self.process = subprocess.Popen(command, env=env, stdout=self.log, stderr=self.log)
        atexit.register(self.close)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                self.log.seek(0)
                detail = self.log.read()[-2500:].replace(openai_api_key, "[redacted]")
                raise RuntimeError(f"LFX could not start. {detail}")
            try:
                response = requests.get(f"{self.base_url}/health", timeout=2)
                if response.ok:
                    return
            except requests.RequestException:
                pass
            time.sleep(0.4)
        self.close()
        raise RuntimeError("LFX did not become ready within two minutes.")

    def ask(self, question: str) -> dict:
        if self.process.poll() is not None:
            raise RuntimeError("The flow runtime stopped. Reboot the app to restart it.")
        response = requests.post(
            f"{self.base_url}/flows/{self.flow_id}/run",
            headers={"x-api-key": self.api_key},
            json={"input_value": question},
            timeout=120,
        )
        response.raise_for_status()
        return response.json()

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if not self.log.closed:
            self.log.close()


def answer_text(payload: dict) -> str:
    """Select Chat Output's text from the LFX run response."""
    for result in payload.get("outputs", []):
        for output in result.get("outputs", []):
            message = output.get("results", {}).get("message", {})
            if isinstance(message, dict) and message.get("text"):
                return message["text"]
    # LFX standalone versions also expose a simplified result envelope.
    result = payload.get("result")
    if isinstance(result, str) and result.strip():
        return result
    raise ValueError("The flow finished without a text answer. Check its Chat Output.")
