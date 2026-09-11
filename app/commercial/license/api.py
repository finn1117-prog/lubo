from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import httpx

from .errors import LicenseNetworkError, LicenseServerError


class LicenseApiClient:
    """Async client for the public license endpoints."""

    def __init__(
        self,
        base_url: str,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
    ) -> None:
        parsed_url = urlparse(base_url)
        local_http = parsed_url.scheme == "http" and parsed_url.hostname in {"localhost", "127.0.0.1"}
        if parsed_url.scheme != "https" and not local_http:
            raise ValueError("license service base_url must use HTTPS (HTTP is allowed only for localhost)")
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout)

    async def activate(self, activation_code: str, installation_id: str, device_fingerprint: str) -> Mapping[str, Any]:
        return await self._post(
            "/v1/license/activate",
            {
                "activationCode": activation_code,
                "installationId": installation_id,
                "deviceFingerprint": device_fingerprint,
            },
        )

    async def validate(self, signed_license: Mapping[str, Any], installation_id: str, device_fingerprint: str):
        return await self._post(
            "/v1/license/validate",
            {
                "license": dict(signed_license),
                "installationId": installation_id,
                "deviceFingerprint": device_fingerprint,
            },
        )

    async def deactivate(self, signed_license: Mapping[str, Any], installation_id: str, device_fingerprint: str):
        return await self._post(
            "/v1/license/deactivate",
            {
                "license": dict(signed_license),
                "installationId": installation_id,
                "deviceFingerprint": device_fingerprint,
            },
        )

    async def _post(self, path: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            response = await self._client.post(path, json=payload)
        except httpx.RequestError as exc:
            raise LicenseNetworkError("unable to reach the license service") from exc
        if response.status_code >= 400:
            message = "license service rejected the request"
            try:
                body = response.json()
                if isinstance(body, dict) and isinstance(body.get("message"), str):
                    message = body["message"]
            except ValueError:
                pass
            raise LicenseServerError(message)
        try:
            body = response.json()
        except ValueError as exc:
            raise LicenseServerError("license service returned invalid JSON") from exc
        if not isinstance(body, dict):
            raise LicenseServerError("license service returned an invalid response")
        return body

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.aclose()
