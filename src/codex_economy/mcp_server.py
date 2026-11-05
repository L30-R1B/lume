"""Small stdio-only catalog. No network listener or command execution exposed."""

from mcp.server.fastmcp import FastMCP

from .engine import Engine
from .store import Store

mcp = FastMCP("codex-economy")


def engine():
    return Engine(Store())


@mcp.tool()
def evidence_search(project: str, query: str, mode: str = "hybrid", budget: int = 6000) -> dict:
    """Retrieve original evidence under a byte budget; stale indexes require evidence_refresh."""
    return engine().context(project, query, budget, mode)


@mcp.tool()
def evidence_read(project: str, path: str, start: int = 1, end: int = 200, expected_hash: str | None = None) -> dict:
    """Read exact current UTF-8 source lines with optional hash precondition."""
    return engine().read(project, path, start, end, expected_hash)


@mcp.tool()
def evidence_graph(
    project: str, path: str, direction: str = "both", kind: str | None = None, depth: int = 1, limit: int = 30
) -> dict:
    """Bounded file relations with provenance; inferred calls are not semantic proof."""
    return engine().graph(project, path, direction, kind, depth, limit)


@mcp.tool()
def evidence_refresh(project: str) -> dict:
    """Transactionally refresh an already authorized project's index."""
    return engine().index(project)


@mcp.tool()
def evidence_handoff(session: str) -> dict:
    """Load persisted objective, acceptance, decisions and references for one session."""
    from .sessions import Sessions

    return Sessions(Store()).get(session)


@mcp.tool()
def evidence_log(
    run: str,
    start: int = 1,
    end: int = 80,
    stream: str = "stderr",
    encoding: str = "text",
    offset: int = 0,
    length: int = 65536,
) -> dict:
    """Expand redacted output by lines or return a bounded base64-encoded byte range."""
    if encoding == "base64":
        from .runner import log_bytes

        with Store() as store:
            return log_bytes(store, run, stream, offset, length)
    if encoding != "text":
        raise ValueError("encoding must be text or base64")
    if stream not in ("stderr", "stdout") or not 1 <= start <= end or end - start > 1000:
        raise ValueError("Invalid stream or line range")
    rows = Store().rows("SELECT stdout,stderr FROM runs WHERE id=?", (run,))
    if not rows:
        raise ValueError("Run not found")
    lines = rows[0][stream].splitlines(keepends=True)
    return {
        "source": "".join(lines[start - 1 : end]),
        "total_lines": len(lines),
        "start": start,
        "end": min(end, len(lines)),
    }


def serve():
    mcp.run(transport="stdio")
