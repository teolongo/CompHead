"""ERP tools for the agent loop."""

from __future__ import annotations

import json
from typing import Any

from services.api_client import get_client

SAMPLE_CAP = 100

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_inventory",
            "description": (
                "Look up ERP inventory with optional filters. Returns pre-computed "
                "below_minimum, on_hand_qty, and minimum_qty for the matched SKU — "
                "use those exact fields; do not compare raw rows yourself."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": "SKU substring filter, e.g. PAS-PEN-500",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["finished_good", "raw_material"],
                        "description": "Filter by inventory item type",
                    },
                    "below_min": {
                        "type": "boolean",
                        "description": "When true, only items below minimum stock",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_bom",
            "description": "List bill of materials for a finished SKU. Returns count and sample rows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Finished product SKU, e.g. PAS-SPA-500",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_suppliers",
            "description": "List ERP suppliers with optional filters. Returns count and sample rows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": "Search supplier name or id",
                    },
                    "category": {
                        "type": "string",
                        "enum": [
                            "semolina",
                            "wheat",
                            "packaging",
                            "labels",
                            "ink",
                            "logistics",
                        ],
                        "description": "Supplier category filter",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_production_orders",
            "description": (
                "List ERP production orders with optional filters. Returns count and sample rows."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Filter by product SKU",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["planned", "in_progress", "done", "blocked"],
                        "description": "Production order status filter",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_shipments",
            "description": "List ERP shipments with optional filters. Returns count and sample rows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Filter by customer id, e.g. CUST-0132",
                    },
                    "order_id": {
                        "type": "string",
                        "description": "Filter by order id, e.g. ORD-2026-0517",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resolve_bom_supplier_stock",
            "description": (
                "Resolve a full BOM/supplier/stock chain in one deterministic call. "
                "Give EITHER a finished SKU (sku) OR a production lot id (lot_id); "
                "when a question contains a LOT-... id, pass lot_id and the tool "
                "resolves it to the finished SKU first. Optionally pass "
                "material_category (e.g. semolina) to select the right BOM row. "
                "Returns lot_id, finished_sku, raw_material_sku, raw_material_name, "
                "supplier_id, supplier_name, and pre-computed below_minimum / "
                "on_hand_qty / minimum_qty for the raw material. Use these exact "
                "fields; do not infer the supplier or recompute the stock comparison."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Finished product SKU, e.g. PAS-SPA-500",
                    },
                    "lot_id": {
                        "type": "string",
                        "description": "Production lot id, e.g. LOT-2026-0876",
                    },
                    "material_category": {
                        "type": "string",
                        "description": (
                            "Raw-material category to select from the BOM, e.g. "
                            "semolina, wheat, packaging, labels, ink"
                        ),
                    },
                },
                "additionalProperties": False,
            },
        },
    },
]


def get_tool_definitions() -> list[dict[str, Any]]:
    return TOOL_DEFINITIONS


def _row_int(row: dict[str, Any], *keys: str) -> int:
    for key in keys:
        if key in row and row[key] is not None:
            return int(row[key])
    return 0


def _compute_inventory_status(row: dict[str, Any]) -> tuple[bool, int, int]:
    on_hand = _row_int(row, "on_hand_qty", "on_hand", "quantity_on_hand")
    minimum = _row_int(row, "minimum_qty", "minimum_stock", "min_qty", "minimum")
    below_minimum = on_hand < minimum if minimum > 0 else False
    return below_minimum, on_hand, minimum


def _find_matching_row(rows: list[dict[str, Any]], search: str | None) -> dict[str, Any] | None:
    if not rows:
        return None
    if not search:
        return rows[0]
    search_upper = search.upper()
    for row in rows:
        sku = str(row.get("sku") or "").upper()
        if sku == search_upper or search_upper in sku:
            return row
    return rows[0]


def _thin_list_result(
    rows: list[dict[str, Any]], sample_key: str
) -> dict[str, Any]:
    return {
        "count": len(rows),
        sample_key: rows[:SAMPLE_CAP],
    }


def _run_get_inventory(arguments: dict[str, Any]) -> tuple[str, str]:
    params: dict[str, str] = {}
    if search := arguments.get("search"):
        params["search"] = search
    if item_type := arguments.get("type"):
        params["type"] = item_type
    if arguments.get("below_min") is True:
        params["below_min"] = "true"

    payload = get_client().get("/erp/inventory", params=params or None)
    rows = payload.get("data") or []
    matched = _find_matching_row(rows, arguments.get("search"))

    if not matched:
        result = {
            "sku": arguments.get("search"),
            "below_minimum": None,
            "on_hand_qty": None,
            "minimum_qty": None,
            "inventory_sample": [],
            "note": "No inventory row matched the filters.",
        }
        return json.dumps(result), "erp/inventory"

    below_minimum, on_hand, minimum = _compute_inventory_status(matched)
    result = {
        "sku": matched.get("sku"),
        "below_minimum": below_minimum,
        "on_hand_qty": on_hand,
        "minimum_qty": minimum,
        "inventory_sample": rows[:SAMPLE_CAP],
    }
    return json.dumps(result), "erp/inventory"


def _run_list_bom(arguments: dict[str, Any]) -> tuple[str, str]:
    params: dict[str, str] = {}
    if sku := arguments.get("sku"):
        params["sku"] = sku
    payload = get_client().get("/erp/bom", params=params or None)
    rows = payload.get("data") or []
    result = _thin_list_result(rows, "bom_sample")
    return json.dumps(result), "erp/bom"


def _run_list_suppliers(arguments: dict[str, Any]) -> tuple[str, str]:
    params: dict[str, str] = {}
    if search := arguments.get("search"):
        params["search"] = search
    if category := arguments.get("category"):
        params["category"] = category
    payload = get_client().get("/erp/suppliers", params=params or None)
    rows = payload.get("data") or []
    result = _thin_list_result(rows, "suppliers_sample")
    return json.dumps(result), "erp/suppliers"


def _run_list_production_orders(arguments: dict[str, Any]) -> tuple[str, str]:
    params: dict[str, str] = {}
    if sku := arguments.get("sku"):
        params["sku"] = sku
    if status := arguments.get("status"):
        params["status"] = status
    payload = get_client().get("/erp/production-orders", params=params or None)
    rows = payload.get("data") or []
    result = _thin_list_result(rows, "production_orders_sample")
    return json.dumps(result), "erp/production-orders"


def _run_list_shipments(arguments: dict[str, Any]) -> tuple[str, str]:
    params: dict[str, str] = {}
    if customer_id := arguments.get("customer_id"):
        params["customer_id"] = customer_id
    if order_id := arguments.get("order_id"):
        params["order_id"] = order_id
    payload = get_client().get("/erp/shipments", params=params or None)
    rows = payload.get("data") or []
    result = _thin_list_result(rows, "shipments_sample")
    return json.dumps(result), "erp/shipments"


_LOT_FIELDS = ("lot_id", "production_lot", "lot", "lot_number", "lot_code")
_SKU_FIELDS = ("finished_sku", "sku", "product_sku", "sku_code", "product")
_COMPONENT_SKU_FIELDS = (
    "component_sku",
    "raw_material_sku",
    "material_sku",
    "component",
    "sku",
)
_COMPONENT_NAME_FIELDS = (
    "component_name",
    "raw_material_name",
    "material_name",
    "name",
    "description",
)
_SUPPLIER_ID_FIELDS = ("supplier_id", "supplier_code", "vendor_id")
# Strict fields for rows that are NOT supplier records (BOM / inventory): a bare
# "name" there is the material name, never the supplier.
_SUPPLIER_NAME_FIELDS = ("supplier_name", "supplier", "vendor_name", "vendor")
# Supplier-endpoint rows: a bare "name" is the supplier name.
_SUPPLIER_ROW_NAME_FIELDS = ("supplier_name", "name", "vendor_name", "vendor")
_VALID_CATEGORIES = ("semolina", "wheat", "packaging", "labels", "ink", "logistics")


def _row_str(row: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value:
            return str(value)
    return None


def _resolve_lot_to_sku(lot_id: str) -> str | None:
    """Resolve a production lot id to its finished SKU via production orders.

    There is no server-side lot filter, so page the production-order log and
    match the lot id against the common lot fields. Production orders are the
    direct link between a lot and the finished SKU it produced.
    """
    lot_upper = lot_id.upper()
    rows = get_client().get_all_pages("/erp/production-orders", params=None)
    for row in rows:
        row_lot = _row_str(row, *_LOT_FIELDS)
        if row_lot and row_lot.upper() == lot_upper:
            return _row_str(row, *_SKU_FIELDS)
    return None


def _bom_component_fields(row: dict[str, Any]) -> tuple[str | None, str | None]:
    return _row_str(row, *_COMPONENT_SKU_FIELDS), _row_str(row, *_COMPONENT_NAME_FIELDS)


def _select_bom_row(
    rows: list[dict[str, Any]], material_category: str | None
) -> dict[str, Any] | None:
    if not rows:
        return None
    if material_category:
        category = material_category.strip().lower()
        code = category[:3].upper()
        for row in rows:
            sku, name = _bom_component_fields(row)
            row_category = str(row.get("category") or "").lower()
            if row_category == category:
                return row
            if sku and code and code in sku.upper():
                return row
            if name and category in name.lower():
                return row
    # Default: first row that looks like a raw material.
    for row in rows:
        sku, _ = _bom_component_fields(row)
        if sku and sku.upper().startswith("RAW-"):
            return row
    return rows[0]


def _category_for_material(raw_material_sku: str | None, material_category: str | None) -> str | None:
    if material_category and material_category.strip().lower() in _VALID_CATEGORIES:
        return material_category.strip().lower()
    if not raw_material_sku:
        return None
    code = raw_material_sku.upper()
    mapping = {
        "RAW-SEM": "semolina",
        "RAW-WHE": "wheat",
        "RAW-PCK": "packaging",
        "RAW-PAC": "packaging",
        "RAW-BOX": "packaging",
        "RAW-LAB": "labels",
        "RAW-INK": "ink",
    }
    for prefix, category in mapping.items():
        if code.startswith(prefix):
            return category
    return None


def _resolve_supplier(
    bom_row: dict[str, Any],
    inventory_row: dict[str, Any] | None,
    raw_material_sku: str | None,
    material_category: str | None,
) -> tuple[str | None, str | None]:
    # 1. Supplier fields already present on the BOM row.
    sid = _row_str(bom_row, *_SUPPLIER_ID_FIELDS)
    sname = _row_str(bom_row, *_SUPPLIER_NAME_FIELDS)
    if sname:
        return sid, sname
    # 2. Supplier fields on the matched raw-material inventory row.
    if inventory_row:
        sid = _row_str(inventory_row, *_SUPPLIER_ID_FIELDS)
        sname = _row_str(inventory_row, *_SUPPLIER_NAME_FIELDS)
        if sname:
            return sid, sname
    # 3. Targeted supplier lookup, filtered by category when known.
    category = _category_for_material(raw_material_sku, material_category)
    params: dict[str, str] = {}
    if category and category in _VALID_CATEGORIES:
        params["category"] = category
    payload = get_client().get("/erp/suppliers", params=params or None)
    rows = payload.get("data") or []
    if not rows:
        return None, None
    # Prefer a supplier whose row references the raw material; else first match.
    if raw_material_sku:
        target = raw_material_sku.upper()
        for row in rows:
            if target in json.dumps(row).upper():
                return (
                    _row_str(row, *_SUPPLIER_ID_FIELDS),
                    _row_str(row, *_SUPPLIER_ROW_NAME_FIELDS),
                )
    first = rows[0]
    return _row_str(first, *_SUPPLIER_ID_FIELDS), _row_str(first, *_SUPPLIER_ROW_NAME_FIELDS)


def _resolve_raw_material_inventory(raw_material_sku: str) -> dict[str, Any] | None:
    payload = get_client().get(
        "/erp/inventory",
        params={"search": raw_material_sku, "type": "raw_material"},
    )
    rows = payload.get("data") or []
    return _find_matching_row(rows, raw_material_sku)


def _not_found_chain(lot_id: str | None, finished_sku: str | None, note: str) -> tuple[str, str]:
    result = {
        "lot_id": lot_id,
        "finished_sku": finished_sku,
        "raw_material_sku": None,
        "raw_material_name": None,
        "supplier_id": None,
        "supplier_name": None,
        "below_minimum": None,
        "on_hand_qty": None,
        "minimum_qty": None,
        "note": note,
    }
    return json.dumps(result), "erp/bom"


def _run_resolve_bom_supplier_stock(arguments: dict[str, Any]) -> tuple[str, str]:
    sku = arguments.get("sku")
    lot_id = arguments.get("lot_id")
    material_category = arguments.get("material_category")

    if not sku and not lot_id:
        return _not_found_chain(
            None, None, "Provide either a finished SKU or a production lot id."
        )

    finished_sku = sku
    if not finished_sku and lot_id:
        finished_sku = _resolve_lot_to_sku(lot_id)
        if not finished_sku:
            return _not_found_chain(
                lot_id,
                None,
                f"Could not resolve lot {lot_id} to a finished SKU in production orders.",
            )

    bom_payload = get_client().get("/erp/bom", params={"sku": finished_sku})
    bom_rows = bom_payload.get("data") or []
    bom_row = _select_bom_row(bom_rows, material_category)
    if not bom_row:
        return _not_found_chain(
            lot_id, finished_sku, f"No bill of materials rows found for {finished_sku}."
        )

    raw_material_sku, raw_material_name = _bom_component_fields(bom_row)
    if not raw_material_sku:
        return _not_found_chain(
            lot_id, finished_sku, "BOM row did not expose a raw material SKU."
        )

    inventory_row = _resolve_raw_material_inventory(raw_material_sku)
    supplier_id, supplier_name = _resolve_supplier(
        bom_row, inventory_row, raw_material_sku, material_category
    )

    if inventory_row:
        below_minimum, on_hand, minimum = _compute_inventory_status(inventory_row)
        if not raw_material_name:
            raw_material_name = inventory_row.get("name")
    else:
        below_minimum, on_hand, minimum = None, None, None

    result = {
        "lot_id": lot_id,
        "finished_sku": finished_sku,
        "raw_material_sku": raw_material_sku,
        "raw_material_name": raw_material_name,
        "supplier_id": supplier_id,
        "supplier_name": supplier_name,
        "below_minimum": below_minimum,
        "on_hand_qty": on_hand,
        "minimum_qty": minimum,
        "note": "Chain resolved deterministically: lot/SKU -> BOM -> supplier -> raw-material stock.",
    }
    return json.dumps(result), "erp/bom"


def run_erp_tool(name: str, arguments: dict[str, Any]) -> tuple[str, str]:
    dispatch = {
        "get_inventory": _run_get_inventory,
        "list_bom": _run_list_bom,
        "list_suppliers": _run_list_suppliers,
        "list_production_orders": _run_list_production_orders,
        "list_shipments": _run_list_shipments,
        "resolve_bom_supplier_stock": _run_resolve_bom_supplier_stock,
    }
    handler = dispatch.get(name)
    if handler is None:
        raise ValueError(f"Unknown ERP tool: {name}")
    return handler(arguments)
