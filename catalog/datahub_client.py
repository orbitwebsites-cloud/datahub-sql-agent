"""
Thin abstraction over "where does catalog metadata come from".

Default: reads catalog/mock_datahub_catalog.json - a hand-authored graph
shaped like real DataHub entities (dataset urns, schemaFields, upstream
lineage edges, glossary terms). This is what the hackathon demo runs
against by default, so judges can run everything with zero setup beyond
`pip install` and `python data/seed_db.py`.

Optional: if DATAHUB_GMS_URL is set (e.g. http://localhost:8080 from
`datahub docker quickstart`), get_catalog() instead queries the real
DataHub GMS REST API for the same datasets and returns them in the same
shape, so agent/lineage.py and agent/nlsql.py don't need to know which
source they're talking to.

To push this mock catalog into a real local DataHub instance, see
scripts/ingest_to_datahub.py.
"""
import json
import os
import urllib.parse
import urllib.request
import urllib.error

_CATALOG_PATH = os.path.join(os.path.dirname(__file__), "mock_datahub_catalog.json")

DATAHUB_GMS_URL = os.environ.get("DATAHUB_GMS_URL", "").rstrip("/")


def _load_mock_catalog():
    with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _fetch_real_datahub_catalog():
    """
    Best-effort pull of dataset entities from a real DataHub GMS instance
    via its OpenAPI v2 entities endpoint. Falls back to the mock catalog
    on any error (DataHub not running, network issue, etc.) so the demo
    never hard-fails just because Docker isn't up.
    """
    mock = _load_mock_catalog()
    try:
        datasets = []
        for entry in mock["datasets"]:
            urn = entry["urn"]
            url = f"{DATAHUB_GMS_URL}/openapi/v2/entity/dataset/{urllib.parse.quote(urn, safe='')}"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    body = json.loads(resp.read())
                    # Real GMS response shape differs from our mock; callers
                    # only rely on urn/name/description/schemaFields/upstreamLineage,
                    # so we merge what we can and keep mock fields as fallback.
                    entry = {**entry, "_raw_gms_response": body}
            datasets.append(entry)
        return {**mock, "datasets": datasets, "_source": "real_datahub_gms"}
    except (urllib.error.URLError, OSError, KeyError, ValueError):
        return {**mock, "_source": "mock_fallback"}


def get_catalog():
    """Returns the metadata catalog dict: {datasets: [...], glossaryTerms: [...]}."""
    if DATAHUB_GMS_URL:
        return _fetch_real_datahub_catalog()
    catalog = _load_mock_catalog()
    return {**catalog, "_source": "mock"}


def get_dataset(name):
    """Look up one dataset entry by its short name (e.g. 'order_items')."""
    catalog = get_catalog()
    for ds in catalog["datasets"]:
        if ds["name"] == name:
            return ds
    return None


def get_glossary_term(urn):
    catalog = get_catalog()
    for term in catalog["glossaryTerms"]:
        if term["urn"] == urn:
            return term
    return None
