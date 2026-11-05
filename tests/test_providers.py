from __future__ import annotations

import base64
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from config import ProviderProfile  # noqa: E402
from providers.custom_http import CustomHttpProvider, _path_get, _render  # noqa: E402


def test_custom_template_mapping():
    context = {
        "model": "model-a",
        "prompt": "hello",
        "size": "1024x1024",
        "images": [{"base64": "abc"}],
        "image_base64": "abc",
    }
    rendered = _render(
        {
            "model": "{{model}}",
            "prompt": "Prompt: {{prompt}}",
            "images": "{{images}}",
            "resolution": "{{size}}",
        },
        context,
    )
    assert rendered["model"] == "model-a"
    assert rendered["prompt"] == "Prompt: hello"
    assert rendered["images"] == context["images"]
    assert rendered["resolution"] == "1024x1024"


def test_response_path_mapping():
    payload = {"result": {"images": [{"data": "abc"}]}}
    assert _path_get(payload, "result.images.0.data") == "abc"


class CustomHandler(BaseHTTPRequestHandler):
    payload = ""
    request_body = None

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        self.__class__.request_body = json.loads(self.rfile.read(length))
        response = json.dumps({"result": {"image": self.__class__.payload}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, *_args):
        pass


def test_custom_http_provider_round_trip():
    buffer = BytesIO()
    Image.new("RGB", (16, 16), "#123456").save(buffer, format="PNG")
    CustomHandler.payload = base64.b64encode(buffer.getvalue()).decode("ascii")
    server = ThreadingHTTPServer(("127.0.0.1", 0), CustomHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        profile = ProviderProfile(
            name="custom",
            provider="custom-http",
            base_url=f"http://127.0.0.1:{server.server_port}",
            model="custom-model",
            custom_request={
                "method": "POST",
                "url": f"http://127.0.0.1:{server.server_port}/generate",
                "body": {
                    "model": "{{model}}",
                    "prompt": "{{prompt}}",
                    "size": "{{size}}",
                },
            },
            custom_response={"image_base64_path": "result.image"},
        )
        result = CustomHttpProvider(profile).generate("hello", "64x64", "png")
        assert result.image.data.startswith(b"\x89PNG")
        assert CustomHandler.request_body == {
            "model": "custom-model",
            "prompt": "hello",
            "size": "64x64",
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
