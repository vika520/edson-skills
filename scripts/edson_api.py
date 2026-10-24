#!/usr/bin/env python3
"""Edson Shop 对外 API 零依赖客户端（标准库 only）。

用法（agent / 脚本通用）：
    from edson_api import EdsonClient
    client = EdsonClient()                      # 读 EDSON_API_KEY / EDSON_API_BASE
    file_id = client.upload("product.jpg")
    task = client.cutout(file_ids=[file_id])    # 同步模式，直接返回终态
    client.download(task, out_dir="out")        # 下载结果到本地

    task = client.edit(prompt="...", image_urls=["https://.../x.jpg"], mode="async")
    task = client.poll(task["task_id"])

命令行：
    python edson_api.py models
    python edson_api.py upload product.jpg
    python edson_api.py cutout file_xxx [file_yyy]
    python edson_api.py account
"""
from __future__ import annotations

import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = (os.environ.get("EDSON_API_BASE") or "https://www.edsonshop.com").rstrip("/")
API_KEY = os.environ.get("EDSON_API_KEY") or ""
AGENT = API_BASE + "/api/v1/agent/v1"


class EdsonAPIError(Exception):
    """带 HTTP 状态与错误码的 API 异常。402 = 余额不足（提示充值，勿重试）。"""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(f"HTTP {status} {code}: {message}")
        self.status = status
        self.code = code
        self.message = message


class EdsonClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, timeout: int = 300):
        self.key = (api_key or API_KEY).strip()
        self.base = (base_url or API_BASE).rstrip("/")
        self.agent = self.base + "/api/v1/agent/v1"
        self.timeout = timeout
        if not self.key:
            raise SystemExit("缺少 EDSON_API_KEY 环境变量（到 /api-access 创建）")

    # ---------- 基础 ----------
    def _request(self, method: str, path: str, body: dict | None = None, retry: int = 2) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": "Bearer " + self.key}
        if data is not None:
            headers["Content-Type"] = "application/json"
        last_error: Exception | None = None
        for attempt in range(retry + 1):
            req = urllib.request.Request(self.agent + path, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode("utf-8", "replace")
                    return json.loads(raw).get("data") if raw.strip().startswith("{") else raw
            except urllib.error.HTTPError as e:
                raw = e.read().decode("utf-8", "replace")
                try:
                    payload = json.loads(raw)
                except ValueError:
                    payload = {"errorMsg": raw, "errorCode": "unknown"}
                # 402（余额不足/未配价）与 401（密钥无效）不可重试。
                if e.code in (401, 402, 400):
                    raise EdsonAPIError(e.code, str(payload.get("errorCode") or ""), str(payload.get("errorMsg") or raw))
                last_error = EdsonAPIError(e.code, str(payload.get("errorCode") or ""), str(payload.get("errorMsg") or raw))
            except Exception as e:  # noqa: BLE001
                last_error = e
            if attempt < retry:
                time.sleep(2 ** attempt)
        raise last_error or EdsonAPIError(0, "network", "request failed")

    # ---------- 文件 ----------
    def upload(self, path: str | Path) -> dict:
        path = Path(path)
        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        boundary = "----edson" + os.urandom(8).hex()
        with open(path, "rb") as f:
            content = f.read()
        body = b"".join([
            ('--%s\r\nContent-Disposition: form-data; name="file"; filename="%s"\r\n'
             'Content-Type: %s\r\n\r\n' % (boundary, path.name.replace('"', ""), mime)).encode(),
            content,
            ("\r\n--%s--\r\n" % boundary).encode(),
        ])
        req = urllib.request.Request(
            self.agent + "/files", data=body,
            headers={
                "Authorization": "Bearer " + self.key,
                "Content-Type": "multipart/form-data; boundary=" + boundary,
            }, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode()).get("data")

    # ---------- 图片任务 ----------
    def generate(self, prompt: str, model: str = "gpt-image-2", n: int = 1, options: dict | None = None, mode: str = "sync") -> dict:
        return self._request("POST", "/images/generations", {
            "prompt": prompt, "model": model, "n": n, "options": options or {}, "mode": mode})

    def edit(self, prompt: str, file_ids: list[str] | None = None, image_urls: list[str] | None = None,
             model: str = "gpt-image-2", options: dict | None = None, mode: str = "sync") -> dict:
        body: dict = {"prompt": prompt, "model": model, "mode": mode, "options": options or {}}
        if file_ids:
            body["file_ids"] = file_ids
        if image_urls:
            body["image_urls"] = image_urls
        return self._request("POST", "/images/edits", body)

    def cutout(self, file_ids: list[str] | None = None, image_urls: list[str] | None = None,
               model: str = "", mode: str = "sync") -> dict:
        """智能抠图：透明底 PNG。model 可省略（取服务端默认白名单模型）。"""
        body: dict = {"mode": mode}
        if model:
            body["model"] = model
        if file_ids:
            body["file_ids"] = file_ids
        if image_urls:
            body["image_urls"] = image_urls
        return self._request("POST", "/images/cutout", body)

    def poll(self, task_id: str, interval: int = 5, timeout: int = 600) -> dict:
        """轮询异步任务直到终态。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            task = self._request("GET", "/tasks/" + task_id)
            if task.get("status") in ("succeeded", "failed"):
                return task
            time.sleep(interval)
        raise EdsonAPIError(0, "timeout", f"task {task_id} not finished in {timeout}s")

    # ---------- 下载 ----------
    def download(self, task: dict, out_dir: str | Path = "out", prefix: str = "") -> list[Path]:
        """下载任务结果（签名 URL 约 1 小时有效，拿到即下载）。"""
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        saved = []
        for i, item in enumerate(task.get("results") or []):
            url = item.get("url")
            if not url:
                continue
            name = item.get("file_name") or f"{prefix or 'edson'}-{i+1}.png"
            target = out / name
            req = urllib.request.Request(url, headers={"Authorization": ""})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp, open(target, "wb") as f:
                f.write(resp.read())
            saved.append(target)
        return saved

    # ---------- 元信息 ----------
    def models(self) -> list:
        return self._request("GET", "/models").get("models") or []

    def account(self) -> dict:
        return self._request("GET", "/account")

    def usage(self, page: int = 1, page_size: int = 20) -> dict:
        return self._request("GET", f"/usage?page={page}&page_size={page_size}")


def _cli() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    client = EdsonClient()
    cmd = sys.argv[1]
    if cmd == "models":
        print(json.dumps(client.models(), ensure_ascii=False, indent=2))
    elif cmd == "account":
        print(json.dumps(client.account(), ensure_ascii=False, indent=2))
    elif cmd == "upload" and len(sys.argv) > 2:
        print(json.dumps(client.upload(sys.argv[2]), ensure_ascii=False, indent=2))
    elif cmd == "cutout" and len(sys.argv) > 2:
        task = client.cutout(file_ids=sys.argv[2:])
        print(json.dumps(task, ensure_ascii=False, indent=2))
        client.download(task)
    elif cmd == "generate" and len(sys.argv) > 2:
        task = client.generate(prompt=" ".join(sys.argv[2:]))
        print(json.dumps(task, ensure_ascii=False, indent=2))
        client.download(task)
    else:
        print(__doc__)


if __name__ == "__main__":
    _cli()
