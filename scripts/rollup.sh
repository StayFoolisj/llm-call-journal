#!/usr/bin/env bash
# Run the rollup from any directory. The default input is the fixture.
#
#   ./scripts/rollup.sh
#   ./scripts/rollup.sh /path/to/journal.jsonl

set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

exec python3 rollup.py "${1:-fixtures/sample_journal.jsonl}"
