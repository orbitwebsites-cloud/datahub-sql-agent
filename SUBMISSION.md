# Devpost Submission Draft

Paste-ready text for https://datahub.devpost.com (registered account: rrus3676@gmail.com).
Not submitted automatically — paste this in once logged into Devpost.

---

## Project title

**Metadata-Aware SQL Agent** *(alt: "Catalog-Grounded SQL Agent" / "Ask Your Data, Trust the Answer")*

## Tagline (short description field, ~1 sentence)

An AI agent that turns business questions into SQL, explains data lineage in plain
English via a DataHub-shaped catalog, and flags query results that look statistically
inconsistent with historical patterns — no paid API keys required.

## Description (long form, ~2 paragraphs)

Analysts get asked the same three questions over and over: "what's the number,"
"where did it come from," and "can I trust it." Most NL-to-SQL tools answer the
first and ignore the other two — so a business user gets a confident-looking number
with no way to tell if it's grounded in the right tables or if it's a fluke. This
project treats metadata as a first-class input, not an afterthought: every question
is answered with (1) the generated SQL, (2) a plain-English explanation of exactly
which tables the query touched and how they're related — upstream lineage, glossary
terms like PII flags — pulled from a DataHub-shaped metadata catalog, and (3) a
statistical sanity check that compares the result against the same metric's
historical distribution and flags it when it's an outlier, before the user ever
reports the number.

The whole pipeline runs with zero paid API keys: the natural-language-to-SQL layer
is a fast, fully local template-matching engine (with a documented drop-in point for
a free local LLM via Ollama if you want open-ended phrasing), the sample business
dataset is a small SQLite e-commerce schema with over a year of order history and a
deliberately planted demand-spike anomaly to demonstrate the flagging logic, and the
metadata catalog is authored in DataHub's real entity shape — dataset urns, schema
fields, upstream lineage edges, glossary terms — so it can be pushed into a real,
self-hosted, open-source DataHub instance (`datahub docker quickstart`) with one
included ingestion script, with no code changes to the agent itself.

## Built With

`python` `sqlite` `datahub` `nl2sql` `data-lineage` `data-catalog` `ollama`
`open-source` `agent` `cli` `unittest`

## Links

- GitHub repo: *(paste repo URL once pushed)*
- Demo video: *(paste video URL once recorded — see DEMO.md for the script)*

## Notes for future me before submitting

- [ ] Push this repo to GitHub (currently only local git init'd in
      D:\Hackathons2026\datahub-sql-agent)
- [ ] Record the demo video following DEMO.md
- [ ] Double check hackathon rules for any required team info / eligibility fields
- [ ] Confirm the exact category/track this should be submitted under on Devpost
