"""Write one JSON record per LLM call.

The journal is a JSONL file. One line holds one call. A record carries the call
site, the prompt version, the provider, the model, the latency, the token
counts, both prompts, and the reply.

Example:

    from journal import log_call

    log_call(
        call_site="classify_ticket",
        prompt_version="v2",
        provider="openai",
        model="gpt-4o-mini",
        system_prompt="You label support tickets with one word.",
        user_prompt="My card was charged twice.",
        response="billing",
        latency_ms=412,
        input_tokens=38,
        output_tokens=2,
    )

The write path is one open, one write, and one flush per call. A record that
the caller sees returned is on disk. A fire-and-forget task can lose records
when the process exits early, so this module does not use one.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path("journal.jsonl")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Timer:
    """Measure wall time in milliseconds.

    with Timer() as t:
        reply = model(system_prompt, user_prompt)
    print(t.ms)
    """

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        self.ms = 0
        return self

    def __exit__(self, *exc_info: Any) -> bool:
        self.ms = int((time.perf_counter() - self._start) * 1000)
        return False


def build_record(
    *,
    call_site: str,
    provider: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    response: str,
    latency_ms: int,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    prompt_version: str | None = None,
    max_tokens: int | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one record. The key order stays stable, so a diff reads cleanly."""
    return {
        "id": uuid.uuid4().hex[:6],
        "timestamp": _utc_stamp(),
        "call_site": call_site,
        "prompt_version": prompt_version,
        "provider": provider,
        "model": model,
        "latency_ms": int(latency_ms),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "max_tokens": max_tokens,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "response": response,
        "context": context,
    }


def log_call(
    *,
    call_site: str,
    provider: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    response: str,
    latency_ms: int,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    prompt_version: str | None = None,
    max_tokens: int | None = None,
    context: dict[str, Any] | None = None,
    path: str | Path = DEFAULT_PATH,
) -> dict[str, Any]:
    """Append one record to the journal and return it."""
    record = build_record(
        call_site=call_site,
        provider=provider,
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response=response,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        prompt_version=prompt_version,
        max_tokens=max_tokens,
        context=context,
    )
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return record


# --- demo -------------------------------------------------------------------

_REPLIES = {
    "classify_ticket": "billing",
    "summarize_thread": "The team agreed to split the release into two parts.",
    "extract_invoice_fields": '{"total": "148.00", "currency": "EUR"}',
}


def _stub_model(call_site: str, system_prompt: str, user_prompt: str) -> str:
    """Stand in for a provider. The demo needs no key and no network."""
    time.sleep(0.01)
    return _REPLIES.get(call_site, "ok")


def main() -> None:
    path = Path("journal.jsonl")
    path.unlink(missing_ok=True)
    calls = [
        ("classify_ticket", "v2", "My card was charged twice for one order."),
        ("summarize_thread", "v1", "Six messages about the release date and scope."),
        ("extract_invoice_fields", "v1", "Invoice 44: total 148.00 EUR, due 30 days."),
    ]
    for call_site, version, user_prompt in calls:
        with Timer() as timer:
            reply = _stub_model(call_site, "You are a careful assistant.", user_prompt)
        record = log_call(
            call_site=call_site,
            prompt_version=version,
            provider="stub",
            model="stub-small",
            system_prompt="You are a careful assistant.",
            user_prompt=user_prompt,
            response=reply,
            latency_ms=timer.ms,
            input_tokens=len(user_prompt.split()),
            output_tokens=len(reply.split()),
            max_tokens=256,
            context={"run": "demo"},
            path=path,
        )
        print(f"wrote {record['id']} {call_site}/{version} {record['latency_ms']} ms")
    print(f"\n{len(calls)} records in {path}")


if __name__ == "__main__":
    main()
