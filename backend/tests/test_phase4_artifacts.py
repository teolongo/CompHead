"""Offline tests for artifact preflight (HTML deck + PDF)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from agent import artifacts


def test_is_html_deck_question() -> None:
    assert artifacts._is_html_deck_question(
        "Generate a 4-slide HTML deck for CUST-0132"
    )
    assert not artifacts._is_html_deck_question("How many open opportunities?")


def test_build_html_deck_has_four_slides() -> None:
    customer = {
        "name": "Primato Supermercati S.p.A.",
        "channel": "GDO",
        "region": "North",
    }
    with patch.object(artifacts, "_open_opportunities", return_value=([], 0.0)):
        with patch.object(artifacts, "_orders_summary", return_value="ORD-1 (shipped)"):
            with patch.object(
                artifacts,
                "_complaints_summary",
                return_value="No complaints",
            ):
                html = artifacts._build_html_deck(customer, "CUST-0132")
    assert html.count('<section class="slide"') == 4
    assert "Primato" in html


def test_pdf_report_creates_file_and_url(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.render.com")
    monkeypatch.setattr(artifacts, "_FILES_DIR", tmp_path)

    mock_client = MagicMock()
    mock_client.get.return_value = {
        "data": [
            {
                "sku": "PAS-SPA-500",
                "name": "Spaghetti 500g",
                "on_hand_qty": 1200,
                "minimum_qty": 500,
                "below_minimum": False,
            }
        ]
    }
    with patch.object(artifacts, "get_client", return_value=mock_client):
        answer, url = artifacts._build_pdf_report(
            "Generate a PDF report for PAS-SPA-500 inventory"
        )

    assert url.startswith("https://example.render.com/files/report-")
    assert url.endswith(".pdf")
    filename = url.split("/")[-1]
    assert (tmp_path / filename).is_file()
    assert "PAS-SPA-500" in answer


def test_artifact_preflight_html_deck() -> None:
    customer = {"name": "Primato", "channel": "GDO", "region": "North"}
    with patch.object(artifacts, "_customer_row", return_value=customer):
        with patch.object(artifacts, "_open_opportunities", return_value=([], 0.0)):
            with patch.object(artifacts, "_orders_summary", return_value="none"):
                with patch.object(
                    artifacts, "_complaints_summary", return_value="none"
                ):
                    result = artifacts.try_answer_artifact_preflight(
                        "Generate a 4-slide HTML deck for CUST-0132"
                    )
    assert result is not None
    assert result["artifact_url"] is None
    assert result["verticale"] == "crm"
    assert '<section class="slide"' in result["answer"]
    assert "crm/customers" in result["sources"]


def test_find_customer_id_by_name() -> None:
    with patch.object(artifacts, "get_client") as mock_get:
        mock_get.return_value.get.return_value = {
            "data": [{"customer_id": "CUST-0132", "name": "Primato Supermercati"}]
        }
        cid = artifacts._find_customer_id(
            "Generate a deck for Primato Supermercati visiting tomorrow"
        )
    assert cid == "CUST-0132"
