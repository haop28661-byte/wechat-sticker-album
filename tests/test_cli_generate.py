from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "cli.py"


def png_base64() -> str:
    buffer = BytesIO()
    Image.new("RGB", (32, 32), "#e64b3c").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


class Handler(BaseHTTPRequestHandler):
    payload = ""
    requests = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        self.__class__.requests.append((self.path, body))
        response = json.dumps({"data": [{"b64_json": self.__class__.payload}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, *_args):
        pass


def test_openai_compatible_generate_and_edit(tmp_path):
    Handler.payload = png_base64()
    Handler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        config = tmp_path / ".wechat-sticker-album" / "config.json"
        config.parent.mkdir(parents=True)
        config.write_text(
            json.dumps(
                {
                    "default_profile": "main",
                    "profiles": {
                        "main": {
                            "provider": "openai-compatible",
                            "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                            "model": "fake-model",
                            "api_key_env": "TEST_IMAGE_KEY",
                            "capabilities": {
                                "supports_reference_images": True,
                                "supports_transparent_background": False,
                            },
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        ref = tmp_path / "ref.png"
        Image.new("RGB", (32, 32), "#00ffff").save(ref)
        env = os.environ.copy()
        env["TEST_IMAGE_KEY"] = "secret"
        output = tmp_path / "generated.png"
        completed = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "generate",
                "--config",
                str(config),
                "--prompt",
                "test prompt",
                "--size",
                "64x64",
                "--output",
                str(output),
            ],
            cwd=tmp_path,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        assert output.is_file()
        assert Handler.requests[-1][0] == "/v1/images/generations"

        edit_output = tmp_path / "edited.png"
        completed = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "generate",
                "--config",
                str(config),
                "--prompt",
                "edit prompt",
                "--reference",
                str(ref),
                "--size",
                "64x64",
                "--output",
                str(edit_output),
            ],
            cwd=tmp_path,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        assert edit_output.is_file()
        path, body = Handler.requests[-1]
        assert path == "/v1/images/edits"
        assert b'name="image"' in body
        assert b"fake-model" in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
