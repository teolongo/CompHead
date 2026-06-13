"""Knowledge graph builder from Al Dente mock API data."""

from __future__ import annotations

import threading
import time
from typing import Any

from services.api_client import get_client

_CACHE: dict[str, Any] | None = None
_CACHE_AT: float = 0.0
_CACHE_TTL_SECONDS = 300.0
_LOCK = threading.Lock()

MAX_CUSTOMERS = 40
MAX_FINISHED_SKUS = 20
MAX_BOM_SKUS = 12


def _node(node_id: str, label: str, kind: str, **meta: Any) -> dict[str, Any]:
    return {"id": node_id, "label": label, "kind": kind, **meta}


def _edge(source: str, target: str, relation: str) -> dict[str, Any]:
    return {"source": source, "target": target, "relation": relation}


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

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "meta": {
            "customers": len(customers),
            "products": len(finished_skus),
            "suppliers": len(supplier_nodes),
            "materials": sum(1 for n in nodes.values() if n["kind"] == "material"),
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
