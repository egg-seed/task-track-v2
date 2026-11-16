"""Independent external API client: mockable without network access."""

import httpx
from pydantic import BaseModel


class RemoteTask(BaseModel):
    id: int
    title: str


class UpstreamError(Exception):
    """An upstream failure to be handled by the caller."""


async def fetch_task(client: httpx.AsyncClient, task_id: int) -> RemoteTask:
    try:
        response = await client.get(f"/tasks/{task_id}")
        response.raise_for_status()
        return RemoteTask.model_validate(response.json())
    # TransportError covers timeouts, connection and protocol failures.
    except (httpx.TransportError, httpx.HTTPStatusError) as exc:
        raise UpstreamError("External API request failed") from exc
    # Both json.JSONDecodeError and pydantic.ValidationError are ValueError subclasses.
    except ValueError as exc:
        raise UpstreamError("External API response was invalid") from exc
