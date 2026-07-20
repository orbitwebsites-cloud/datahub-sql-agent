# Metadata-Aware SQL Agent

Built for **"Build with DataHub: The Agent Hackathon"** (Devpost, deadline Aug 10, 2026).

An agent that takes a plain-English business question, writes the SQL to answer it,
explains *where the data came from* in plain English using a DataHub-shaped metadata
catalog, and flags when the result looks statistically inconsistent with historical
patterns.

**Runs with zero paid API keys.** No OpenAI/Anthropic/Gemini key required to run the
demo. DataHub itself is open source; the NL-to-SQL layer is a free, fully-local,
template-based engine (with a documented extension point for a local LLM via Ollama,
if you want open-ended NL2SQL instead).

## What it does

Ask a question like:

```
what was total revenue in electronics in may 2026
```

The agent:

1. **Writes the SQL** — `agent/nlsql.py` matches the question against a set of
   business-question templates (revenue, revenue-by-category, top-N products/customers,
   order counts, average order value, cancellation rate) and fills in a parametrized
   SQL query. No LLM call, no API key, runs instantly offline.
2. **Runs it** against `data/sample.db`, a small SQLite e-commerce dataset
   (customers, products, orders, order_items).
3. **Explains lineage in plain English** — `agent/lineage.py` walks a DataHub-shaped
   metadata graph (`catalog/mock_datahub_catalog.json`) to explain which tables the
   query touched, where each one comes from, and what business meaning its columns
   carry (e.g. flagging `email` as PII via a glossary term).
4. **Flags anomalies** — `agent/anomaly.py` compares the requested month's revenue
   against the mean/stddev of every other month in the dataset (a z-score check) and
   tells you if the number looks unusual before you trust it. The sample dataset has
   a deliberate demand spike planted in May 2026 (Electronics) so this is easy to
   demo.

## Project layout

```
data/seed_db.py                  builds data/sample.db (SQLite, ~14 months of orders)
catalog/mock_datahub_catalog.json  DataHub-shaped metadata: datasets, schema, lineage, glossary
catalog/datahub_client.py        abstraction — reads the mock catalog, or a real DataHub
                                  GMS instance if DATAHUB_GMS_URL is set
agent/nlsql.py                   NL question -> SQL (template-based, free/local)
agent/lineage.py                 catalog graph -> plain-English lineage explanation
agent/anomaly.py                 statistical anomaly check against historical baseline
cli.py                           interactive CLI tying the pipeline together
scripts/ingest_to_datahub.py     optional: push the mock catalog into a real DataHub instance
tests/test_agent.py              unit tests for all three agent modules
```

## Setup & run

Requires only Python 3.9+ (standard library — no dependencies to install for the
core demo).

```bash
git clone <this repo>
cd datahub-sql-agent

python data/seed_db.py        # builds data/sample.db

python cli.py                 # interactive mode
# or:
python cli.py "top 5 products by revenue"
```

Interactive mode example session:

```
> what was total revenue in electronics in may 2026
> top 5 products by revenue
> revenue by category
> how many orders were cancelled
> average order value
> top 3 customers
```

Run the test suite:

```bash
python -m pytest tests/ -v
```

## Using a real DataHub instance (optional)

The demo runs entirely against the bundled mock catalog by default — that's what
makes it runnable with zero setup. If you want to show the metadata living inside a
real DataHub UI:

1. Follow the [DataHub quickstart](https://github.com/datahub-project/datahub) to
   run `datahub docker quickstart` (requires Docker; DataHub itself is open source
   and free — no paid key involved).
2. `pip install acryl-datahub`
3. `python scripts/ingest_to_datahub.py` — pushes the same dataset/schema/lineage/
   ownership metadata from `catalog/mock_datahub_catalog.json` into your local
   DataHub instance via its REST emitter.
4. Set `DATAHUB_GMS_URL=http://localhost:8080` before running `cli.py` — 
   `catalog/datahub_client.py` will then query the real GMS API instead of the
   bundled JSON (falling back to the mock automatically if DataHub isn't reachable).
5. Browse the ingested catalog at `http://localhost:9002`.

This is purely optional — the agent's answers are identical either way, since both
paths return the same shape of metadata.

## Extending the NL-to-SQL layer with a local LLM

`agent/nlsql.py` currently uses keyword + regex template matching, which covers a
fixed set of business-question shapes reliably and instantly, with no dependencies.
If you want open-ended natural language coverage instead, the doc comment at the top
of that file shows the exact drop-in point: point `generate_sql()` at a local model
served by [Ollama](https://ollama.com) (e.g. `ollama run sqlcoder`), which is free,
runs entirely on your machine, and needs no API key. The rest of the pipeline
(lineage explanation, anomaly check) doesn't care how the SQL was generated.

## Constraint notes

- No paid/gated API keys required anywhere in this repo.
- DataHub itself is free and open source (Apache 2.0), self-hosted via Docker.
- The sample business dataset (SQLite) and the mock DataHub catalog are both
  generated/authored locally — no external data pulled at runtime.
