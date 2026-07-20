"""
OPTIONAL: pushes catalog/mock_datahub_catalog.json into a real, locally
running DataHub instance (e.g. started with `datahub docker quickstart`).

Not required for the demo - cli.py works entirely off the mock catalog
JSON with zero setup. Run this only if you want to show the metadata
actually living inside a real DataHub UI (localhost:9002) during a demo.

Requires: pip install acryl-datahub
Requires: a running DataHub instance (see README.md "Using a real DataHub instance")

Run: python scripts/ingest_to_datahub.py
"""
import json
import os
import sys

CATALOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "catalog", "mock_datahub_catalog.json")
GMS_ENDPOINT = os.environ.get("DATAHUB_GMS_URL", "http://localhost:8080")


def main():
    try:
        from datahub.emitter.rest_emitter import DatahubRestEmitter
        from datahub.metadata.schema_classes import (
            DatasetPropertiesClass,
            SchemaMetadataClass,
            SchemaFieldClass,
            SchemaFieldDataTypeClass,
            StringTypeClass,
            NumberTypeClass,
            DateTypeClass,
            UpstreamLineageClass,
            UpstreamClass,
            DatasetLineageTypeClass,
            OwnershipClass,
            OwnerClass,
            OwnershipTypeClass,
        )
        from datahub.metadata.com.linkedin.pegasus2avro.mxe import MetadataChangeProposal
        from datahub.emitter.mcp import MetadataChangeProposalWrapper
    except ImportError:
        print("acryl-datahub is not installed. Run: pip install acryl-datahub")
        sys.exit(1)

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    emitter = DatahubRestEmitter(gms_server=GMS_ENDPOINT)

    type_map = {"string": StringTypeClass(), "number": NumberTypeClass(), "date": DateTypeClass()}

    for ds in catalog["datasets"]:
        urn = ds["urn"]

        # Dataset properties
        props_mcp = MetadataChangeProposalWrapper(
            entityUrn=urn,
            aspect=DatasetPropertiesClass(description=ds["description"], customProperties={}),
        )
        emitter.emit(props_mcp)

        # Schema
        fields = [
            SchemaFieldClass(
                fieldPath=f["name"],
                type=SchemaFieldDataTypeClass(type=type_map.get(f["type"], StringTypeClass())),
                nativeDataType=f["type"],
                description=f.get("description", ""),
            )
            for f in ds["schemaFields"]
        ]
        schema_mcp = MetadataChangeProposalWrapper(
            entityUrn=urn,
            aspect=SchemaMetadataClass(
                schemaName=ds["name"],
                platform=f"urn:li:dataPlatform:{'sqlite' if 'sqlite' in urn else 'report'}",
                version=0,
                hash="",
                platformSchema=None,
                fields=fields,
            ),
        )
        emitter.emit(schema_mcp)

        # Ownership
        if ds.get("owners"):
            ownership_mcp = MetadataChangeProposalWrapper(
                entityUrn=urn,
                aspect=OwnershipClass(
                    owners=[
                        OwnerClass(owner=f"urn:li:corpGroup:{o}", type=OwnershipTypeClass.DATAOWNER)
                        for o in ds["owners"]
                    ]
                ),
            )
            emitter.emit(ownership_mcp)

        # Upstream lineage
        upstreams = ds.get("upstreamLineage", [])
        if upstreams:
            lineage_mcp = MetadataChangeProposalWrapper(
                entityUrn=urn,
                aspect=UpstreamLineageClass(
                    upstreams=[
                        UpstreamClass(dataset=edge["upstreamUrn"], type=DatasetLineageTypeClass.TRANSFORMED)
                        for edge in upstreams
                    ]
                ),
            )
            emitter.emit(lineage_mcp)

        print(f"Ingested {ds['name']} -> {urn}")

    print(f"\nDone. Open http://localhost:9002 to browse the catalog in the real DataHub UI.")


if __name__ == "__main__":
    main()
