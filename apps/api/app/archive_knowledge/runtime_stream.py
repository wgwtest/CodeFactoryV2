from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import json
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse

from app.archive_knowledge.runtime_service import ArchiveDocumentRuntimeService


def encode_runtime_sse_event(
    event: str,
    data: object,
    *,
    event_id: str | None = None,
    retry_ms: int | None = None,
) -> str:
    lines: list[str] = []
    if retry_ms is not None:
        lines.append(f"retry: {retry_ms}")
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    for line in payload.splitlines() or [""]:
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"


async def build_document_runtime_stream_response(
    *,
    archive_id: str,
    document_id: str,
    request: Request,
    service: ArchiveDocumentRuntimeService,
    interval_ms: int,
    heartbeat_ms: int,
    max_events: int | None = None,
    document_set_id: str | None = None,
    policy_package_version_id: str | None = None,
) -> StreamingResponse:
    runtime_kwargs: dict[str, Any] = {
        "document_set_id": document_set_id,
        "policy_package_version_id": policy_package_version_id,
        "stream_status": "streaming",
    }
    initial_runtime = await asyncio.to_thread(service.get_document_runtime, archive_id, document_id, **runtime_kwargs)
    if initial_runtime is None:
        raise HTTPException(status_code=404, detail="Archive document runtime not found")

    async def event_stream():
        loop = asyncio.get_running_loop()
        previous_payload = json.dumps(initial_runtime, ensure_ascii=False, separators=(",", ":"))
        last_emit_at = loop.time()
        sequence = 0
        emitted_events = 0

        yield encode_runtime_sse_event(
            "runtime",
            initial_runtime,
            event_id=f"{document_id}:{sequence}",
            retry_ms=interval_ms,
        )
        emitted_events += 1
        if max_events is not None and emitted_events >= max_events:
            return

        while not await request.is_disconnected():
            await asyncio.sleep(interval_ms / 1000)

            runtime = await asyncio.to_thread(service.get_document_runtime, archive_id, document_id, **runtime_kwargs)
            if runtime is None:
                sequence += 1
                yield encode_runtime_sse_event(
                    "error",
                    {"detail": "Archive document runtime not found"},
                    event_id=f"{document_id}:{sequence}",
                    retry_ms=interval_ms,
                )
                emitted_events += 1
                break

            payload = json.dumps(runtime, ensure_ascii=False, separators=(",", ":"))
            now = loop.time()
            should_emit_heartbeat = now - last_emit_at >= heartbeat_ms / 1000

            if payload != previous_payload:
                previous_payload = payload
                sequence += 1
                last_emit_at = now
                yield encode_runtime_sse_event(
                    "runtime",
                    runtime,
                    event_id=f"{document_id}:{sequence}",
                    retry_ms=interval_ms,
                )
                emitted_events += 1
                if max_events is not None and emitted_events >= max_events:
                    return
                continue

            if should_emit_heartbeat:
                sequence += 1
                last_emit_at = now
                yield encode_runtime_sse_event(
                    "heartbeat",
                    {
                        "archive_id": archive_id,
                        "document_id": document_id,
                        "stream_status": "streaming",
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                    event_id=f"{document_id}:heartbeat:{sequence}",
                    retry_ms=interval_ms,
                )
                emitted_events += 1
                if max_events is not None and emitted_events >= max_events:
                    return

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
