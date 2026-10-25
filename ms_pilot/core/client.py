import base64
import io
import json
import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional
from PIL import Image


def resolve_mcp_binary() -> str:
    """Resolve the iphone-use-mcp executable path across environments."""
    env_path = os.environ.get("IPHONE_USE_MCP_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    candidates = [
        os.path.expanduser("~/Applications/iPhoneUse.app/Contents/MacOS/iphone-use-mcp"),
        "/Applications/iPhoneUse.app/Contents/MacOS/iphone-use-mcp",
        shutil.which("iphone-use-mcp") or "",
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path

    raise FileNotFoundError(
        "Could not locate 'iphone-use-mcp'. Set IPHONE_USE_MCP_PATH in your environment."
    )


class iPhoneClient:
    """MCP JSON-RPC bridge for physical iPhone control via iphone-use-mcp."""

    def __init__(self, owner: Optional[str] = None, mcp_path: Optional[str] = None):
        self.owner = owner or os.environ.get("IPHONE_USE_OWNER", "ms-agent-pilot")
        self.mcp_path = mcp_path or resolve_mcp_binary()
        env = os.environ.copy()
        env["IPHONE_USE_OWNER"] = self.owner

        self.proc = subprocess.Popen(
            [self.mcp_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        self.req_id = 0
        self._init_session()

    def __enter__(self) -> "iPhoneClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _init_session(self) -> None:
        self._call_raw({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "monster-strike-agent-pilot", "version": "2.0.0"},
            },
        })
        self._send_raw({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        })

    def _next_id(self) -> int:
        self.req_id += 1
        return self.req_id

    def _send_raw(self, msg: Dict[str, Any]) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def _call_raw(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        self._send_raw(msg)
        assert self.proc.stdout is not None
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("iphone-use-mcp process terminated unexpectedly")
            data = json.loads(line)
            if "id" in data and data["id"] == msg.get("id"):
                return data

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }
        res = self._call_raw(req)
        if res.get("error"):
            raise RuntimeError(f"MCP tool error ({name}): {res['error']}")
        result = res.get("result", {})
        content = result.get("content", [])
        if content and content[0].get("type") == "text":
            text = content[0]["text"]
            try:
                return json.loads(text)
            except Exception:
                return text
        return result

    def status(self) -> Dict[str, Any]:
        res = self.call_tool("phone_status")
        return res if isinstance(res, dict) else {"raw": res}

    def ensure_drivable(self) -> Dict[str, Any]:
        """Verify device readiness and automatically reconnect if idle-released."""
        st = self.status()
        if st.get("released") or st.get("device_state") == "released":
            self.call_tool("phone_reconnect")
            st = self.status()
        if st.get("setup_phase") == "lock-wait":
            print("[WARNING] iPhone screen is locked (lock-wait). Please unlock the iPhone.")
        return st

    def elements(self, ocr: str = "force") -> str:
        args = {"ocr": ocr} if ocr else {}
        res = self.call_tool("phone_elements", args)
        return res if isinstance(res, str) else str(res)

    def get_ocr_items(self) -> List[Dict[str, Any]]:
        text = self.elements(ocr="force")
        items: List[Dict[str, Any]] = []
        pattern = re.compile(r'"([^"]*)"\s+x=([\d\.]+)\s+y=([\d\.]+)')
        for match in pattern.finditer(text):
            items.append({
                "text": match.group(1),
                "x": float(match.group(2)),
                "y": float(match.group(3)),
            })
        return items

    def get_screenshot_image(self) -> Optional[Image.Image]:
        """Capture high-res screen image as a PIL.Image object for pixel/CV inspection."""
        res = self.call_tool("phone_screenshot")
        if not isinstance(res, dict):
            return None
        for item in res.get("content", []):
            if item.get("type") == "image" and item.get("data"):
                raw = base64.b64decode(item["data"])
                return Image.open(io.BytesIO(raw))
        return None

    def tap(self, x: float, y: float) -> Any:
        return self.call_tool("phone_tap", {"x": round(x, 4), "y": round(y, 4)})

    def drag(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        hold_ms: int = 120,
        duration_ms: int = 160,
    ) -> Any:
        return self.run_steps([{
            "kind": "drag",
            "x1": round(x1, 4),
            "y1": round(y1, 4),
            "x2": round(x2, 4),
            "y2": round(y2, 4),
            "hold_ms": hold_ms,
            "duration_ms": duration_ms,
        }])

    def run_steps(self, steps: List[Dict[str, Any]]) -> Any:
        return self.call_tool("phone_run_steps", {"steps": steps})

    def release_owner(self) -> Any:
        try:
            return self.call_tool("phone_release_owner")
        except Exception as e:
            print(f"[Client] Warning releasing owner: {e}")
            return None

    def close(self) -> None:
        try:
            self.release_owner()
        finally:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
