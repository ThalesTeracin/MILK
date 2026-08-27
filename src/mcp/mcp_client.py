import json
import subprocess
import threading
import queue
import itertools
import os

class MCPClient:
    def __init__(self, name, command, args=None, cwd=None, env=None):
        self.name = name
        self.command = command
        self.args = args or []
        self.cwd = cwd
        self.env = env
        self.proc = None
        self.reader_thread = None
        self.responses = {}
        self.notifications = queue.Queue()
        self.counter = itertools.count(1)
        self.lock = threading.Lock()

    def start(self):
        if self.proc and self.proc.poll() is None:
            return

        creationflags = 0
        startupinfo = None

        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        self.proc = subprocess.Popen(
            [self.command] + self.args,
            cwd=self.cwd,
            env=self.env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=creationflags,
            startupinfo=startupinfo
        )

        self.reader_thread = threading.Thread(target=self._reader, daemon=True)
        self.reader_thread.start()

        self.initialize()

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass

    def _reader(self):
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except Exception:
                continue

            if "id" in msg:
                with self.lock:
                    self.responses[msg["id"]] = msg
            else:
                self.notifications.put(msg)

    def _request(self, method, params=None, timeout=20):
        if not self.proc or self.proc.poll() is not None:
            raise RuntimeError(f"MCP server '{self.name}' não está ativo.")

        req_id = next(self.counter)
        payload = {"jsonrpc":"2.0","id":req_id,"method":method}
        if params is not None:
            payload["params"] = params

        self.proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

        import time
        started = time.time()

        while time.time() - started < timeout:
            with self.lock:
                msg = self.responses.pop(req_id, None)
            if msg is not None:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg.get("result")
            time.sleep(0.05)

        raise TimeoutError(f"Timeout MCP em {method}")

    def _notify(self, method, params=None):
        payload = {"jsonrpc":"2.0","method":method}
        if params is not None:
            payload["params"] = params

        self.proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def initialize(self):
        result = self._request(
            "initialize",
            {
                "protocolVersion":"2025-03-26",
                "capabilities":{},
                "clientInfo":{"name":"MILK","version":"22.1"}
            }
        )
        self._notify("notifications/initialized")
        return result

    def list_tools(self):
        result = self._request("tools/list", {})
        return result.get("tools", []) if isinstance(result, dict) else []

    def call_tool(self, tool_name, arguments=None):
        return self._request(
            "tools/call",
            {"name":tool_name,"arguments":arguments or {}},
            timeout=60
        )
