# Demo script (~3 minutes)

Goal: show the three-part value prop in one pass — write the SQL, explain the
lineage, catch the bad number — without touching any paid API.

## Setup (before recording)

```bash
python data/seed_db.py
```

Confirm it prints `Built .../sample.db - 4277 orders, 8600 order_items.` (or similar).

## Beat 1 — the problem (10s, talking over a blank terminal)

"Business users ask analysts questions like 'what was our revenue in Electronics
last month' — and the two hard parts aren't the SQL, they're knowing whether the
answer can be trusted, and where the numbers actually came from."

## Beat 2 — ask a normal question (30s)

```bash
python cli.py "top 5 products by revenue"
```

Point out on screen:
- The generated SQL (real join across order_items/orders/products).
- The result table.
- The **lineage explanation** underneath — plain English, not a diagram — showing
  order_items is derived from orders + products, and that email is flagged as PII
  in the customers table's glossary terms (mention this even though it's not in
  this exact query — cut to `python cli.py "top 3 customers"` briefly to show it,
  or describe it from the README).

## Beat 3 — the anomaly catch (60s, the money shot)

```bash
python cli.py "what was total revenue in electronics in may 2026"
```

Walk through the output top to bottom:
1. Generated SQL — scoped by category + month + year, all extracted from the
   plain-English question.
2. Result — a big number ($186k vs. a normal month of ~$19k).
3. Lineage — same explanation as before, reinforcing that this isn't a one-off
   feature, it's baked into every answer.
4. **Anomaly check** — the z-score line: `z-score +75.66 ... highly unusual ...
   Investigate before reporting this number.` This is the punchline: the agent
   doesn't just answer, it tells you *not to trust this number blindly*.

Explain: this spike is a real planted scenario in the sample data (a demand surge),
but the same mechanism catches broken ETL, a bad join, or a duplicate-load bug just
as well — anything that makes a month's revenue implausible compared to its own
history.

## Beat 4 — show it's free/local (20s)

"No OpenAI key, no Anthropic key, nothing paid. The NL-to-SQL layer is a
template-matching engine that runs instantly and offline — the extension point for
swapping in a local LLM via Ollama is documented in `agent/nlsql.py` if you want
open-ended phrasing instead of these fixed question shapes. DataHub itself is open
source and runs locally via Docker; we ship a catalog file shaped exactly like
DataHub's real metadata model so the ingestion script (`scripts/ingest_to_datahub.py`)
can push it into a real DataHub instance with one command."

## Beat 5 — close (10s)

```bash
python -m pytest tests/ -v
```

Ten tests passing — NL-to-SQL template matching, lineage traversal, and the
anomaly statistics all covered.

## Optional bonus beat — real DataHub UI

If Docker/DataHub quickstart is already running locally:
```bash
python scripts/ingest_to_datahub.py
```
then flip to `http://localhost:9002` in a browser to show the same metadata living
in the actual DataHub catalog UI — proves the mock catalog isn't a toy shape, it's
DataHub's real entity model.
