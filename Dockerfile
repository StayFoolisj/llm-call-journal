# Run the rollup in a container. The image holds the fixture only.
#
#   docker build -t llm-call-journal .
#   docker run --rm llm-call-journal
#
# For your own journal, mount the folder and pass the path.
#   docker run --rm -v "$PWD:/data:ro" llm-call-journal python rollup.py /data/journal.jsonl

FROM python:3.12-slim

WORKDIR /app

COPY rollup.py journal.py ./
COPY fixtures ./fixtures

CMD ["python", "rollup.py", "fixtures/sample_journal.jsonl"]
