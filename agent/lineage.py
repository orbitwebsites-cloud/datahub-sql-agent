"""
Turns the DataHub-shaped metadata graph (catalog/mock_datahub_catalog.json,
or a live GMS instance if DATAHUB_GMS_URL is set) into a plain-English
lineage explanation for a given table.

This is deliberately template-driven rather than LLM-driven: lineage
correctness matters more than prose variety for a hackathon judge, and a
templated explanation is guaranteed to be grounded in the actual catalog
edges instead of a model's guess.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from catalog.datahub_client import get_catalog, get_dataset  # noqa: E402


def _urn_to_short_name(urn):
    # urn:li:dataset:(urn:li:dataPlatform:sqlite,sample_db.customers,PROD) -> customers
    try:
        inner = urn.split("(")[1].split(")")[0]
        table_part = inner.split(",")[1]
        return table_part.split(".")[-1]
    except IndexError:
        return urn


def explain_lineage(table_name: str, _depth=0, _seen=None) -> str:
    """Returns a plain-English, recursive upstream lineage explanation."""
    if _seen is None:
        _seen = set()
    if table_name in _seen:
        return ""
    _seen.add(table_name)

    ds = get_dataset(table_name)
    if ds is None:
        return f"No catalog entry found for '{table_name}'."

    lines = []
    indent = "  " * _depth
    lines.append(f"{indent}- **{ds['name']}**: {ds['description']}")

    pii_fields = [f["name"] for f in ds.get("schemaFields", []) if "PII.Email" in f.get("glossaryTerms", [])]
    if pii_fields:
        lines.append(f"{indent}  [PII] contains PII columns: {', '.join(pii_fields)} - handle per data-privacy policy.")

    upstreams = ds.get("upstreamLineage", [])
    if not upstreams:
        lines.append(f"{indent}  This is a source table - it has no upstream dependencies in the catalog.")
    else:
        for edge in upstreams:
            upstream_name = _urn_to_short_name(edge["upstreamUrn"])
            rel = edge.get("type", "depends on")
            lines.append(f"{indent}  -> derived from **{upstream_name}** ({rel})")
            nested = explain_lineage(upstream_name, _depth + 2, _seen)
            if nested:
                lines.append(nested)

    return "\n".join(lines)


def explain_lineage_for_tables(table_names) -> str:
    """Explain lineage for every table involved in a generated SQL query."""
    seen = set()
    parts = []
    for t in table_names:
        if t in seen:
            continue
        seen.add(t)
        parts.append(explain_lineage(t, _seen=set()))
    return "\n\n".join(parts)


def tables_used_in_sql(sql: str):
    """Cheap heuristic table extractor for our own generated SQL (FROM/JOIN clauses)."""
    import re
    tables = re.findall(r"(?:FROM|JOIN)\s+(\w+)", sql, flags=re.IGNORECASE)
    return list(dict.fromkeys(tables))  # de-dup, preserve order


def glossary_summary() -> str:
    catalog = get_catalog()
    lines = ["Business glossary terms in this catalog:"]
    for term in catalog["glossaryTerms"]:
        lines.append(f"  - {term['name']}: {term['description']}")
    return "\n".join(lines)
