import os
import asyncio
from typing import Any, Dict, Optional, Tuple

import httpx


def get_base_url() -> str:
    return os.environ.get("FINTRACK_API_URL", "http://localhost:8081").rstrip("/")


def build_url(path_or_url: str) -> str:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    base = get_base_url()
    path = path_or_url if path_or_url.startswith("/") else f"/{path_or_url}"
    return f"{base}{path}"


def _should_retry(status_code: Optional[int]) -> bool:
    if status_code is None:
        return True
    if status_code in (408, 429):
        return True
    return 500 <= status_code <= 599


async def get_json(
    path_or_url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 10.0,
    max_retries: int = 2,
    backoff_factor: float = 0.5,
) -> Tuple[int, Optional[Dict[str, Any]], str]:
    url = build_url(path_or_url)
    hdrs = {"Accept": "application/json"}
    if headers:
        hdrs.update(headers)

    status_code: Optional[int] = None
    text: str = ""
    data: Optional[Dict[str, Any]] = None

    attempt = 0
    while attempt <= max_retries:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, params=params, headers=hdrs)
                status_code = resp.status_code
                text = resp.text
                try:
                    data = resp.json()
                except Exception:
                    data = None
            if not _should_retry(status_code):
                break
        except Exception:
            status_code = None
            text = ""
            data = None
        attempt += 1
        if attempt <= max_retries:
            await asyncio.sleep(backoff_factor * attempt)

    return status_code or 0, data, text


async def post_gzip_json(
    path_or_url: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 10.0,
    max_retries: int = 2,
    backoff_factor: float = 0.5,
) -> Tuple[int, Optional[Dict[str, Any]], str]:
    import gzip, json

    url = build_url(path_or_url)
    payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    gz_bytes = gzip.compress(payload_bytes)

    hdrs = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Content-Encoding": "gzip",
        "Accept-Encoding": "gzip",
    }
    if headers:
        hdrs.update(headers)

    status_code: Optional[int] = None
    text: str = ""
    data: Optional[Dict[str, Any]] = None

    attempt = 0
    while attempt <= max_retries:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, content=gz_bytes, headers=hdrs)
                status_code = resp.status_code
                text = resp.text
                try:
                    data = resp.json()
                except Exception:
                    data = None
            if not _should_retry(status_code):
                break
        except Exception:
            status_code = None
            text = ""
            data = None
        attempt += 1
        if attempt <= max_retries:
            await asyncio.sleep(backoff_factor * attempt)

    return status_code or 0, data, text

