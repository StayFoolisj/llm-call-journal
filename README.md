# llm-call-journal

Every production LLM call becomes a record you can audit, replay, cost, and optimise against real outcomes.

A journal is one JSONL file. One line holds one call. Each line carries the call site, the prompt version, the provider, the model, the latency, the token counts, both prompts, and the reply.

No dependencies. Standard library only. Python 3.9 or newer.

## The record

| Field | Example | Why it is there |
|---|---|---|
| `id` | `f00003` | Ties a log line to a record, and to a support ticket later |
| `timestamp` | `2026-02-03T09:12:03Z` | Order, and the way to align a call with an incident |
| `call_site` | `classify_ticket` | The code path that made the call |
| `prompt_version` | `v2` | Which prompt template ran |
| `provider` | `openai` | Who served the request |
| `model` | `gpt-4o-mini` | Which model served the request |
| `latency_ms` | `512` | Wait time, for a p50 and a p95 |
| `input_tokens` | `41` | Cost, and context pressure |
| `output_tokens` | `2` | Cost, and a reply that hit the limit |
| `max_tokens` | `512` | The limit at call time |
| `system_prompt` | `You label a support ticket...` | Replay needs the exact input |
| `user_prompt` | `I cannot log in after...` | Replay needs the exact input |
| `response` | `account` | What the model said |
| `context` | `{"request_id": "req-1002"}` | Your own join keys |

The field order stays stable. A diff of two days reads cleanly.

## Run it

```sh
python journal.py
python rollup.py fixtures/sample_journal.jsonl
```

`journal.py` writes three calls with a stub model, so the demo needs no key and no network. `rollup.py` reads a journal and prints cost, latency, and a breakdown.

Output on the fixture:

```text
records: 13   tokens: 14601 in / 1183 out

cost estimate (USD, placeholder rates)
  total: $0.0081
  unpriced calls: 1 (acme-small-7b)

latency (ms)
  p50: 742   p95: 2410   min: 240   max: 2455

by call_site
                             calls      p50      p95   cost USD
  summarize_thread               3     1965     2096     0.0078
  extract_invoice_fields         3      688      737     0.0002
  classify_ticket                4      462      884     0.0000
  route_question                 1      240      240     0.0000
  code_review_note               2     2418     2451     0.0000

by prompt_version
                             calls      p50      p95   cost USD
  v2                             4     1238     2088     0.0054
  v1                             7      688     1573     0.0027
  v3                             2     2418     2451     0.0000
```

The rate card in `rollup.py` is a placeholder. A model without a rate stays in the counts, and leaves the cost total. That keeps a missing price visible.

## Why the call site and the prompt version matter

A cost total without a call site cannot tell you which feature spends the money. A latency average without a prompt version cannot tell you which edit made the reply slow.

With both, three questions become a query. Which call site costs the most. Which prompt version raised the p95. Which model change moved the cost per call.

The last step is the outcome. Add your own key to `context`, for example a ticket id or a feature flag, and join the journal to your results later. A call that passed the check has an outcome. A call that failed has one too. A prompt optimiser can then score a version by the outcomes it produced, and not by a model that grades its own homework.

## Why the write waits

`log_call` does one open, one write, one flush, and one fsync per call. A record that the caller sees returned is on disk.

A fire-and-forget task is smaller and faster, and it loses the tail of the journal when the process exits. The tail is the part you need after a crash.

## Limits

- The journal holds prompts in clear text. Add a scrubber before you log customer text in production.
- The rate card is a placeholder. Set your own prices before you trust a total.
- One JSONL file grows without bound. Rotate it by day or by size.
- The outcome join is a pattern here, not code. The next file to write is the join.

## Files

```text
journal.py                    writer: build_record, log_call, Timer
rollup.py                     cost, p50 and p95, a breakdown by call_site and prompt_version
fixtures/sample_journal.jsonl 13 synthetic records, neutral prompts
```

## License

MIT. See `LICENSE`.
