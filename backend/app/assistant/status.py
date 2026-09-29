"""Turn agent and tool events into progress lines and analyst-facing status messages."""

from app.assistant.deps import DocumentAgentDeps
from app.assistant.progress import report_progress


def emit_agent_start(deps: DocumentAgentDeps, *, model: str, request_limit: int) -> None:
    report_progress(f"agent start model={model} request_limit={request_limit}")
    deps.emit_status("analyzing", "Analyzing your question…")


def emit_agent_done(
    deps: DocumentAgentDeps,
    *,
    requests: int,
    tool_calls: int,
    input_tokens: int,
    output_tokens: int,
) -> None:
    report_progress(
        f"agent done requests={requests} tool_calls={tool_calls} "
        f"input_tokens={input_tokens} output_tokens={output_tokens}"
    )
    deps.emit_status("verifying", "Verifying citations…")


def emit_tool_start(deps: DocumentAgentDeps, name: str, detail: str) -> None:
    report_progress(f"tool {name} start {detail}")
    deps.emit_status(*_tool_status(name, detail))


def _tool_status(name: str, detail: str) -> tuple[str, str]:
    if name == "search_filings":
        return "searching", f"Searching SEC filings… ({detail})" if detail else "Searching SEC filings…"
    if name == "read_surrounding_chunks":
        return "reading", "Reading surrounding context…"
    return "reading", "Reading source passages…"
