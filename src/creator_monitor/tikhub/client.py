from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Callable, Mapping

from creator_monitor.budget import BudgetGuard
from creator_monitor.errors import TikHubAPIError, TikHubTransportError


BASE_URL = "https://api.tikhub.io"
Transport = Callable[[str, dict[str, str], float], dict]


@dataclass(frozen=True)
class Endpoint:
    name: str
    path: str
    cost_usd: Decimal = Decimal("0.01")


class TikHubClient:
    def __init__(
        self,
        *,
        api_key: str,
        budget: BudgetGuard,
        cache_dir: Path,
        transport: Transport | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        timeout_seconds: float = 20,
        max_attempts: int = 3,
    ) -> None:
        self._api_key = api_key
        self._budget = budget
        self._cache_dir = cache_dir
        self._transport = transport or self._default_transport
        self._sleeper = sleeper
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts

    def get(
        self,
        endpoint: Endpoint,
        params: Mapping[str, object],
        *,
        use_cache: bool = True,
    ) -> dict:
        clean_params = {key: str(value) for key, value in params.items() if value is not None}
        query = urllib.parse.urlencode(sorted(clean_params.items()))
        url = f"{BASE_URL}{endpoint.path}"
        if query:
            url = f"{url}?{query}"
        cache_path = self._cache_path(endpoint, clean_params)
        if use_cache and cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
            "User-Agent": "creator-monitor/0.1",
        }
        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            self._budget.reserve(endpoint.name, endpoint.cost_usd)
            try:
                payload = self._transport(url, headers, self._timeout_seconds)
            except (TimeoutError, urllib.error.URLError, TikHubTransportError) as exc:
                last_error = exc
                if attempt == self._max_attempts:
                    break
                self._sleeper(min(2 ** (attempt - 1), 8))
                continue

            code = int(payload.get("code", 0) or 0)
            if code == 200:
                if use_cache:
                    self._write_cache(cache_path, payload)
                return payload
            if code == 429 or code >= 500:
                last_error = TikHubAPIError(
                    f"TikHub retryable response for {endpoint.name}: code={code}"
                )
                if attempt < self._max_attempts:
                    self._sleeper(min(2 ** (attempt - 1), 8))
                    continue
                break
            message = str(payload.get("message") or payload.get("message_zh") or "unknown error")
            raise TikHubAPIError(
                f"TikHub request failed for {endpoint.name}: code={code}, message={message}"
            )

        raise TikHubTransportError(
            f"TikHub request failed after {self._max_attempts} attempts for {endpoint.name}"
        ) from last_error

    def _cache_path(self, endpoint: Endpoint, params: Mapping[str, str]) -> Path:
        material = json.dumps(
            {"endpoint": endpoint.path, "params": dict(sorted(params.items()))},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
        return self._cache_dir / f"{endpoint.name}-{digest}.json"

    def _write_cache(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    @staticmethod
    def _default_transport(url: str, headers: dict[str, str], timeout: float) -> dict:
        request = urllib.request.Request(url=url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                return json.loads(body)
            except json.JSONDecodeError as json_error:
                raise TikHubTransportError(f"TikHub HTTP error: {exc.code}") from json_error

