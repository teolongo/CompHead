"""Al Dente Company Brain - backend entry point.

Your job: implement the agent behind POST /ask. It orchestrates the Al Dente
mock APIs (CRM / ERP / call logs) and a knowledge base you build over data/kb/,
then answers with text or an artifact. Full spec and rules in AGENTS.md.

The /ask contract below is FROZEN - the automated evaluator depends on it.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent.loop import run_agent
from services.graph import get_graph_cached

app = FastAPI(title="Al Dente Company Brain")

_STATIC = Path(__file__).resolve().parent / "static"
_FILES = _STATIC / "files"
_FILES.mkdir(parents=True, exist_ok=True)

# Binary artifacts (docx / pptx / pdf / xlsx) you generate at request time go in
# static/files/ and are served from /files/<name> by this same backend.
# artifact_url must be ABSOLUTE: f"{os.environ['PUBLIC_BASE_URL']}/files/<name>"
app.mount("/files", StaticFiles(directory=_FILES), name="files")


@app.get("/", include_in_schema=False)
def ui() -> FileResponse:
    """Placeholder page. Building a minimal UI is part of the challenge:
    it must exist and work, but it is not graded - replace static/index.html
    (or serve your own frontend)."""
    return FileResponse(_STATIC / "index.html")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    verticale: str  # one of: "crm", "erp", "calls", "kb"
    artifact_url: str | None = None  # only for docx/pptx/pdf/xlsx questions


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/graph")
def graph() -> dict:
    """UI-only knowledge graph from mock CRM/ERP data (not part of frozen /ask)."""
    return get_graph_cached()


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    try:
        result = run_agent(request.question)
        return AskResponse(**result)
    except Exception as exc:
        return AskResponse(
            answer=f"I cannot answer right now because of an error: {exc}",
            sources=[],
            verticale="crm",
            artifact_url=None,
        )
