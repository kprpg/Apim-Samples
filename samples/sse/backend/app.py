import asyncio
import json
import time
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(title='APIM SSE Backend', version='1.0.0')


def _sse_event(*, data: dict, event: str = 'message', event_id: str | None = None) -> str:
    # SSE format: https://html.spec.whatwg.org/multipage/server-sent-events.html
    # Keep payload small so APIM buffering is easy to observe.
    lines: list[str] = []
    if event_id is not None:
        lines.append(f'id: {event_id}')
    if event:
        lines.append(f'event: {event}')
    lines.append(f'data: {json.dumps(data, separators=(",", ":"), ensure_ascii=False)}')
    return "\n".join(lines) + "\n\n"


@app.get('/health')
def health() -> JSONResponse:
    return JSONResponse({'status': 'ok', 'ts': time.time()})


@app.get('/sse')
async def sse(
    interval_ms: int = Query(200, ge=10, le=60000, description='Delay between events'),
    total_events: int = Query(20, ge=1, le=2000, description='Number of events to emit before closing'),
    heartbeat_ms: int = Query(0, ge=0, le=60000, description='If >0, send SSE comment heartbeats at this interval'),
    initial_delay_ms: int = Query(0, ge=0, le=60000, description='Optional delay before first event'),
) -> StreamingResponse:
    async def gen() -> AsyncGenerator[bytes, None]:
        start = time.time()
        if initial_delay_ms:
            await asyncio.sleep(initial_delay_ms / 1000)

        next_heartbeat = time.time() + (heartbeat_ms / 1000) if heartbeat_ms else None

        for i in range(total_events):
            now = time.time()

            if next_heartbeat is not None and now >= next_heartbeat:
                # Comment heartbeat. Some intermediaries/clients treat this as keepalive.
                yield b': keepalive\n\n'
                next_heartbeat = now + (heartbeat_ms / 1000)

            payload = {
                'i': i,
                't': now,
                'elapsed_ms': int((now - start) * 1000),
            }
            yield _sse_event(data=payload, event='tick', event_id=str(i)).encode('utf-8')
            await asyncio.sleep(interval_ms / 1000)

    headers = {
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        # Transfer-Encoding: chunked is handled by the server/proxy.
    }

    return StreamingResponse(gen(), media_type='text/event-stream', headers=headers)
