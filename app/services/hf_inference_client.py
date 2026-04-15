import asyncio
import logging
from typing import List, Optional

import httpx

from config import (
    HF_INFERENCE_URL,
    HF_MAX_CONCURRENCY,
    HF_MAX_RETRIES,
    HF_RETRY_BACKOFF_SECONDS,
    HF_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


class HFInferenceError(RuntimeError):
    def __init__(self, message: str, status_code: Optional[int] = None, retryable: bool = False) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class HFInferenceClient:
    def __init__(
        self,
        url: str = HF_INFERENCE_URL,
        timeout_seconds: float = HF_TIMEOUT_SECONDS,
        max_retries: int = HF_MAX_RETRIES,
        backoff_seconds: float = HF_RETRY_BACKOFF_SECONDS,
        max_concurrency: int = HF_MAX_CONCURRENCY,
    ) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.max_concurrency = max_concurrency
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client:
            return self._client

        timeout = httpx.Timeout(self.timeout_seconds)
        self._client = httpx.AsyncClient(timeout=timeout)
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def predict_batch(self, texts: List[str]) -> List[str]:
        if not texts:
            return []

        payload = {"texts": texts}
        return await self._post_with_retries(payload, expected_len=len(texts))

    async def _post_with_retries(self, payload: dict, expected_len: int) -> List[str]:
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                client = self._get_client()
                response = await client.post(self.url, json=payload)

                if response.status_code in (408, 429) or response.status_code >= 500:
                    raise HFInferenceError(
                        f"HF inference returned {response.status_code}",
                        status_code=response.status_code,
                        retryable=True,
                    )

                if response.status_code != 200:
                    raise HFInferenceError(
                        f"HF inference failed with status {response.status_code}",
                        status_code=response.status_code,
                    )

                try:
                    data = response.json()
                except ValueError as exc:
                    raise HFInferenceError("HF inference returned invalid JSON") from exc

                labels = data.get("data")
                if not isinstance(labels, list):
                    raise HFInferenceError("HF inference response missing data list")

                if expected_len and len(labels) != expected_len:
                    raise HFInferenceError(
                        f"HF inference size mismatch: expected {expected_len}, got {len(labels)}"
                    )

                return [str(label) for label in labels]
            except (httpx.RequestError, httpx.TimeoutException, HFInferenceError) as exc:
                last_error = exc
                retryable = True
                if isinstance(exc, HFInferenceError):
                    retryable = exc.retryable
                if attempt >= self.max_retries or not retryable:
                    break
                wait_seconds = self.backoff_seconds * (2**attempt)
                logger.warning("HF retrying in %s seconds (attempt %s)", wait_seconds, attempt + 1)
                await asyncio.sleep(wait_seconds)

        message = "HF inference failed"
        if last_error:
            message = f"{message}: {last_error}"
        raise HFInferenceError(message)


hf_client = HFInferenceClient()
