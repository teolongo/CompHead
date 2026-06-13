"""Knowledge graph builder from Al Dente mock API data."""

from __future__ import annotations

import re
import threading
import time
from pathlib import Path
from typing import Any, Callable

from services.api_client import get_client

_CACHE: dict[str, Any] | None = None
_CACHE_AT: float = 0.0
_CACHE_TTL_SECONDS = 300.0
_LOCK = threading.Lock()

MAX_CUSTOMERS = 40
MAX_FINISHED_SKUS = 20
MAX_BOM_SKUS = 12

_KB_DIR = Path(__file__).resolve().parent.parent / "data" / "kb"

# Category super-nodes and their document IDs (all 35 KB files).
_KB_CATEGORIES: dict[str, dict[str, Any]] = {
    "kb:product-specs": {
        "label": "Product specifications",
        "docs": [
            f"DOC-{n:03d}"
            for n in (
                *range(1, 11),
                *range(18, 26),
                31,
            )
        ],
    },
    "kb:quality-compliance": {
        "label": "Quality & compliance",
        "docs": [
            f"DOC-{n:03d}"
            for n in (11, 12, 13, 16, 17, 26, 28, 29, 32, 33)
        ],
    },
    "kb:price-policy": {
        "label": "Pricing",
        "docs": ["DOC-015"],
    },
    "kb:supplier-agreements": {
        "label": "Supplier agreements",
        "docs": ["DOC-027"],
    },
    "kb:logistics-trade": {
        "label": "Logistics & trade",
        "docs": ["DOC-014", "DOC-030", "DOC-034", "DOC-035"],
    },
}

# Product spec doc -> SKU (from KB markdown tables).
_DOC_PRODUCT_SKU: dict[str, str] = {
    "DOC-001": "PAS-SPA-500",
    "DOC-002": "PAS-PEN-500",
    "DOC-003": "PAS-FUS-500",
    "DOC-004": "PAS-RIG-500",
    "DOC-005": "PAS-LIN-500",
    "DOC-006": "PAS-FAR-500",
    "DOC-007": "PAS-TAG-500",
    "DOC-008": "PAS-CON-500",
    "DOC-009": "PAS-ORE-500",
    "DOC-010": "PAS-BUC-500",
    "DOC-018": "PAS-SPA-BIO-500",
    "DOC-019": "PAS-PEN-BIO-500",
    "DOC-020": "PAS-FUS-BIO-500",
    "DOC-021": "PAS-RIG-BIO-500",
    "DOC-022": "PAS-LIN-BIO-500",
    "DOC-023": "PAS-SPA-250",
    "DOC-024": "PAS-PEN-250",
    "DOC-025": "PAS-FUS-250",
}

_SKU_RE = re.compile(r"\bPAS-[A-Z0-9-]+\b")


def _node(node_id: str, label: str, kind: str, **meta: Any) -> dict[str, Any]:
    return {"id": node_id, "label": label, "kind": kind, **meta}


def _edge(source: str, target: str, relation: str) -> dict[str, Any]:
    return {"source": source, "target": target, "relation": relation}


def _kb_doc_title(doc_id: str) -> str:
    path = _KB_DIR / f"{doc_id}.md"
    if not path.is_file():
        return doc_id
    first_line = path.read_text(encoding="utf-8").splitlines()[0].strip()
    if first_line.startswith("# "):
        return first_line[2:].strip()[:56]
    return doc_id


def _infer_doc_sku(doc_id: str) -> str | None:
    if doc_id in _DOC_PRODUCT_SKU:
        return _DOC_PRODUCT_SKU[doc_id]
    path = _KB_DIR / f"{doc_id}.md"
    if not path.is_file():
        return None
    match = _SKU_RE.search(path.read_text(encoding="utf-8"))
    return match.group(0).upper() if match else None


def _kb_nodes_and_edges(
    nodes: dict[str, dict[str, Any]],
    add_edge: Callable[[str, str, str], None],
) -> int:
    """Add KB category/doc nodes and semantic edges. Returns kb doc count."""
    doc_to_category: dict[str, str] = {}
    for cat_id, spec in _KB_CATEGORIES.items():
        label = str(spec["label"])
        nodes[cat_id] = _node(cat_id, label, "kb-category", category_key=cat_id.split(":")[-1])
        for doc_id in spec["docs"]:
            doc_to_category[doc_id] = cat_id

    kb_doc_count = 0
    for doc_id, cat_id in sorted(doc_to_category.items()):
        doc_node_id = f"kb:{doc_id}"
        nodes[doc_node_id] = _node(
            doc_node_id,
            _kb_doc_title(doc_id),
            "kb-doc",
            doc_id=doc_id,
        )
        add_edge(doc_node_id, cat_id, "in-category")
        kb_doc_count += 1

    product_ids = [nid for nid in nodes if nid.startswith("product:")]
    supplier_ids = [
        nid
        for nid, n in nodes.items()
        if n.get("kind") == "supplier" and str(n.get("category") or "").lower() == "semolina"
    ]
    gdo_customer_ids = [
        nid
        for nid, n in nodes.items()
        if n.get("kind") == "customer" and str(n.get("channel") or "") == "GDO"
    ]

    for doc_id, cat_id in doc_to_category.items():
        doc_node_id = f"kb:{doc_id}"
        if cat_id == "kb:product-specs":
            sku = _infer_doc_sku(doc_id)
            if sku:
                product_id = f"product:{sku}"
                if product_id in nodes:
                    add_edge(doc_node_id, product_id, "documented-by")

    for doc_id in _KB_CATEGORIES["kb:quality-compliance"]["docs"]:
        doc_node_id = f"kb:{doc_id}"
        for product_id in product_ids:
            add_edge(doc_node_id, product_id, "governed-by")

    price_doc = f"kb:DOC-015"
    if price_doc in nodes:
        for product_id in product_ids:
            add_edge(price_doc, product_id, "priced-by")

    supplier_doc = f"kb:DOC-027"
    if supplier_doc in nodes:
        for supplier_id in supplier_ids:
            add_edge(supplier_doc, supplier_id, "certified-by")

    for doc_id in _KB_CATEGORIES["kb:logistics-trade"]["docs"]:
        doc_node_id = f"kb:{doc_id}"
        for customer_id in gdo_customer_ids:
            add_edge(doc_node_id, customer_id, "applies-to")

    return kb_doc_count


def _infer_material_category(raw_sku: str | None) -> str | None:
    if not raw_sku:
        return None
    code = raw_sku.upper()
    if code.startswith("RAW-SEM"):
        return "semolina"
    if code.startswith("RAW-WHE"):
        return "wheat"
    if code.startswith(("RAW-PCK", "RAW-PAC", "RAW-BOX", "RAW-FILM", "RAW-CRT")):
        return "packaging"
    if code.startswith("RAW-LBL"):
        return "labels"
    if code.startswith("RAW-INK"):
        return "ink"
    return None


def _flatten_bom_components(row: dict[str, Any]) -> list[dict[str, Any]]:
    finished = row.get("sku") or row.get("finished_sku")
    components = row.get("components")
    if isinstance(components, list) and components:
        flat: list[dict[str, Any]] = []
        for comp in components:
            raw_sku = comp.get("raw_sku") or comp.get("component_sku")
            flat.append(
                {
                    "finished_sku": finished,
                    "component_sku": raw_sku,
                    "component_name": comp.get("description") or comp.get("component_name"),
                    "category": _infer_material_category(str(raw_sku or "")),
                }
            )
        return flat
    if row.get("component_sku") or row.get("raw_material_sku"):
        return [row]
    return []


def build_graph() -> dict[str, Any]:
    """Fetch CRM/ERP relationships and return nodes + edges for visualization."""
    client = get_client()
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str]] = set()

    def add_edge(source: str, target: str, relation: str) -> None:
        key = (source, target, relation)
        if key in seen_edges:
            return
        seen_edges.add(key)
        edges.append(_edge(source, target, relation))

    customers = (client.get("/crm/customers", params={"limit": MAX_CUSTOMERS}).get("data") or [])[
        :MAX_CUSTOMERS
    ]
    for row in customers:
        cid = row.get("customer_id") or row.get("id")
        if not cid:
            continue
        name = row.get("name") or cid
        node_id = f"customer:{cid}"
        nodes[node_id] = _node(
            node_id,
            str(name)[:48],
            "customer",
            channel=row.get("channel"),
            region=row.get("region"),
        )

    inventory = client.get(
        "/erp/inventory",
        params={"type": "finished_good", "limit": MAX_FINISHED_SKUS},
    ).get("data") or []
    finished_skus: list[str] = []
    for row in inventory[:MAX_FINISHED_SKUS]:
        sku = row.get("sku")
        if not sku:
            continue
        finished_skus.append(str(sku))
        node_id = f"product:{sku}"
        nodes[node_id] = _node(
            node_id,
            str(row.get("name") or sku)[:48],
            "product",
            sku=sku,
        )

    suppliers = (client.get("/erp/suppliers", params={"limit": 50}).get("data") or [])[:30]
    supplier_nodes: dict[str, str] = {}
    for row in suppliers:
        sid = row.get("supplier_id") or row.get("id")
        if not sid:
            continue
        node_id = f"supplier:{sid}"
        supplier_nodes[str(sid)] = node_id
        nodes[node_id] = _node(
            node_id,
            str(row.get("name") or sid)[:48],
            "supplier",
            category=row.get("category"),
        )

    bom_skus = finished_skus[:MAX_BOM_SKUS]
    for sku in bom_skus:
        payload = client.get("/erp/bom", params={"sku": sku})
        for row in payload.get("data") or []:
            for comp in _flatten_bom_components(row):
                raw_sku = comp.get("component_sku")
                if not raw_sku:
                    continue
                raw_id = f"material:{raw_sku}"
                if raw_id not in nodes:
                    nodes[raw_id] = _node(
                        raw_id,
                        str(comp.get("component_name") or raw_sku)[:48],
                        "material",
                        sku=str(raw_sku),
                        category=comp.get("category"),
                    )
                add_edge(f"product:{sku}", raw_id, "uses")

    raw_inventory = client.get(
        "/erp/inventory",
        params={"type": "raw_material", "limit": 80},
    ).get("data") or []
    for row in raw_inventory:
        raw_sku = row.get("sku")
        if not raw_sku:
            continue
        raw_id = f"material:{raw_sku}"
        if raw_id not in nodes:
            nodes[raw_id] = _node(
                raw_id,
                str(row.get("name") or raw_sku)[:48],
                "material",
                sku=str(raw_sku),
            )
        sid = row.get("supplier_id")
        if sid and str(sid) in supplier_nodes:
            add_edge(supplier_nodes[str(sid)], raw_id, "supplies")

    kb_docs = _kb_nodes_and_edges(nodes, add_edge)

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "meta": {
            "customers": len(customers),
            "products": len(finished_skus),
            "suppliers": len(supplier_nodes),
            "materials": sum(1 for n in nodes.values() if n["kind"] == "material"),
            "kb_docs": kb_docs,
            "kb_categories": len(_KB_CATEGORIES),
        },
    }


def get_graph_cached() -> dict[str, Any]:
    global _CACHE, _CACHE_AT
    now = time.monotonic()
    with _LOCK:
        if _CACHE is not None and (now - _CACHE_AT) < _CACHE_TTL_SECONDS:
            return _CACHE
    try:
        graph = build_graph()
    except Exception as exc:
        return {
            "nodes": [],
            "edges": [],
            "meta": {"error": str(exc)},
        }
    with _LOCK:
        _CACHE = graph
        _CACHE_AT = time.monotonic()
    return graph
