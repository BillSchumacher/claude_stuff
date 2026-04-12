"""Minimal web UI for browsing evaluation results and managing runs. Stdlib only."""

import html
import json
import os
import sys
import tomllib
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from src.config import EVALS_DIR
from src import results
from src import run_manager


def _page(title: str, body: str, breadcrumbs: str = "") -> str:
    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>{title} — Skill Eval</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #0d1117; color: #c9d1d9; }}
  a {{ color: #58a6ff; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  h1, h2, h3 {{ color: #f0f6fc; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ border: 1px solid #30363d; padding: 0.5rem 0.75rem; text-align: left; }}
  th {{ background: #161b22; }}
  tr:nth-child(even) {{ background: #161b22; }}
  tr:hover {{ background: #1c2333 !important; }}
  .pass {{ color: #3fb950; font-weight: bold; }}
  .fail {{ color: #f85149; font-weight: bold; }}
  .positive {{ color: #3fb950; }}
  .negative {{ color: #f85149; }}
  .neutral {{ color: #8b949e; }}
  .breadcrumbs {{ color: #8b949e; margin-bottom: 1rem; }}
  .badge {{ display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.85rem; }}
  .badge-pass {{ background: #238636; color: #fff; }}
  .badge-fail {{ background: #da3633; color: #fff; }}
  pre {{ background: #161b22; padding: 1rem; border-radius: 6px; overflow-x: auto; font-size: 0.85rem; }}
  .summary {{ background: #161b22; padding: 1rem; border-radius: 6px; margin: 1rem 0; white-space: pre-wrap; }}
  button {{ padding: 0.5rem 1rem; border: 1px solid #30363d; border-radius: 6px; cursor: pointer; font-size: 0.9rem; }}
  .btn-primary {{ background: #238636; color: #fff; border-color: #238636; }}
  .btn-danger {{ background: #da3633; color: #fff; border-color: #da3633; }}
  .btn-secondary {{ background: #21262d; color: #c9d1d9; }}
  input, select {{ padding: 0.4rem 0.6rem; background: #161b22; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px; }}
  .run-panel {{ background: #161b22; padding: 1rem; border-radius: 6px; margin: 1rem 0; }}
  .live-log {{ background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 1rem;
               max-height: 500px; overflow-y: auto; font-family: monospace; font-size: 0.85rem; white-space: pre-wrap; }}
  .progress {{ background: #21262d; border-radius: 4px; height: 8px; margin: 0.5rem 0; }}
  .progress-bar {{ background: #238636; height: 100%; border-radius: 4px; transition: width 0.3s; }}
  .status-badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.8rem; font-weight: bold; }}
  .status-idle {{ background: #21262d; color: #8b949e; }}
  .status-running {{ background: #1f6feb33; color: #58a6ff; }}
  .status-completed {{ background: #23863633; color: #3fb950; }}
  .status-cancelled {{ background: #da363333; color: #f85149; }}
  .status-failed {{ background: #da363333; color: #f85149; }}
  .status-cancelling {{ background: #d2992233; color: #d29922; }}
  /* Diff styles */
  .diff {{ font-family: monospace; font-size: 0.85rem; line-height: 1.5; }}
  .diff-add {{ background: #12261e; color: #3fb950; }}
  .diff-del {{ background: #2d1214; color: #f85149; }}
  .diff-hunk {{ color: #58a6ff; font-weight: bold; }}
  .diff-file {{ color: #d29922; font-weight: bold; margin-top: 1rem; }}
  /* Message viewer */
  .msg {{ border: 1px solid #30363d; border-radius: 6px; margin: 0.75rem 0; overflow: hidden; }}
  .msg-header {{ background: #161b22; padding: 0.5rem 0.75rem; font-weight: bold; font-size: 0.85rem; display: flex; justify-content: space-between; }}
  .msg-body {{ padding: 0.75rem; white-space: pre-wrap; font-size: 0.9rem; }}
  .msg-assistant .msg-header {{ border-left: 3px solid #58a6ff; }}
  .msg-tool .msg-header {{ border-left: 3px solid #d29922; }}
  .msg-result .msg-header {{ border-left: 3px solid #3fb950; }}
  .msg-system .msg-header {{ border-left: 3px solid #8b949e; }}
  details {{ margin: 0.25rem 0; }}
  details summary {{ cursor: pointer; color: #8b949e; font-size: 0.8rem; }}
  details pre {{ margin: 0.25rem 0; font-size: 0.8rem; }}
  .tool-name {{ color: #d29922; }}
</style>
</head><body>
<div id="global-status-bar" style="display:none;position:fixed;top:0;left:0;right:0;
  background:#1f6feb33;border-bottom:2px solid #58a6ff;padding:0.5rem 2rem;
  font-size:0.9rem;z-index:1000;backdrop-filter:blur(8px);">
  <div id="global-status-runs"></div>
</div>
<script>
function cancelRunById(rid) {{
  fetch('/api/cancel?run_id=' + encodeURIComponent(rid), {{method:'POST'}});
}}
(function() {{
  let bar = document.getElementById('global-status-bar');
  let container = document.getElementById('global-status-runs');
  function poll() {{
    fetch('/api/active-runs').then(r=>r.json()).then(runs=>{{
      if (runs.length === 0) {{
        bar.style.display = 'none';
        document.body.style.marginTop = '';
        return;
      }}
      bar.style.display = 'block';
      document.body.style.marginTop = (2.2 + runs.length * 1.6) + 'rem';
      const html = runs.map(function(d) {{
        const progress = d.completed_cases + '/' + d.total_cases;
        const model = d.run_id.split('_').pop() || '';
        return '<div style="display:flex;justify-content:space-between;align-items:center;padding:0.2rem 0;">'
          + '<span>'
          + '<span class="status-badge status-' + d.status + '">' + d.status + '</span>'
          + ' <strong>' + model.toUpperCase() + '</strong>'
          + ' <span style="color:#8b949e;">' + (d.current_case || '') + '</span>'
          + ' <span style="color:#8b949e;">' + progress + '</span>'
          + '</span>'
          + '<span>'
          + '<a href="/" style="margin-right:1rem;">Live log</a>'
          + '<button class="btn-danger" style="padding:0.15rem 0.5rem;font-size:0.75rem;" '
          + 'onclick="cancelRunById(\\'' + d.run_id + '\\')">Cancel</button>'
          + '</span>'
          + '</div>';
      }}).join('');
      container.innerHTML = html;
    }}).catch(function() {{}});
  }}
  poll();
  setInterval(poll, 3000);
}})();
</script>
{f'<div class="breadcrumbs">{breadcrumbs}</div>' if breadcrumbs else ''}
<h1>{title}</h1>
{body}
</body></html>"""


_LIVE_SCRIPT = """
<script>
const MAX_LINES = 42;
const runPanels = {};  // run_id -> {log, timer, timerEl, caseStart}
let evtSource = null;

function getOrCreatePanel(runId) {
  if (runPanels[runId]) return runPanels[runId];
  const container = document.getElementById('live-panels');
  const model = runId.split('_').pop() || runId;

  const panel = document.createElement('div');
  panel.style.cssText = 'flex:1;min-width:300px;max-width:50%;display:flex;flex-direction:column;';
  panel.innerHTML =
    '<div style="display:flex;justify-content:space-between;align-items:center;' +
    'background:#161b22;padding:0.4rem 0.75rem;border-radius:6px 6px 0 0;border:1px solid #30363d;border-bottom:none;">' +
      '<span><strong>' + model.toUpperCase() + '</strong> ' +
        '<span class="status-badge status-running" id="status-' + runId + '">running</span>' +
        ' <span id="progress-' + runId + '" style="color:#8b949e;"></span></span>' +
      '<button class="btn-danger" style="padding:0.15rem 0.5rem;font-size:0.75rem;" ' +
        'onclick="fetch(\\'/api/cancel?run_id=' + runId + '\\',{method:\\'POST\\'})">Cancel</button>' +
    '</div>' +
    '<div id="log-' + runId + '" class="live-log" style="border-radius:0 0 6px 6px;flex:1;' +
    'max-height:none;height:400px;"></div>';
  container.appendChild(panel);

  const log = document.getElementById('log-' + runId);
  const state = {log: log, timer: null, timerEl: null, caseStart: null};
  runPanels[runId] = state;
  return state;
}

function appendToRun(runId, text, cls) {
  const p = getOrCreatePanel(runId);
  const line = document.createElement('div');
  if (cls) line.className = cls;
  line.textContent = text;
  p.log.appendChild(line);
  // Trim to MAX_LINES
  while (p.log.childElementCount > MAX_LINES) p.log.removeChild(p.log.firstChild);
  p.log.scrollTop = p.log.scrollHeight;
}

function fmtElapsed(ms) {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return (m > 0 ? m + 'm ' : '') + (s % 60) + 's';
}

function startTimer(runId) {
  const p = getOrCreatePanel(runId);
  stopTimer(runId);
  p.caseStart = Date.now();
  p.timerEl = document.createElement('div');
  p.timerEl.className = 'neutral';
  p.timerEl.textContent = '  Elapsed: 0s...';
  p.log.appendChild(p.timerEl);
  p.timer = setInterval(function() {
    p.timerEl.textContent = '  Elapsed: ' + fmtElapsed(Date.now() - p.caseStart) + '...';
    p.log.scrollTop = p.log.scrollHeight;
  }, 1000);
}

function stopTimer(runId) {
  const p = runPanels[runId];
  if (!p) return;
  if (p.timer) { clearInterval(p.timer); p.timer = null; }
  if (p.timerEl && p.caseStart) {
    p.timerEl.textContent = '  Completed in ' + fmtElapsed(Date.now() - p.caseStart);
    p.timerEl = null;
  }
}

function setRunStatus(runId, status) {
  const el = document.getElementById('status-' + runId);
  if (el) { el.className = 'status-badge status-' + status; el.textContent = status; }
}

function startSSE() {
  if (evtSource) evtSource.close();
  evtSource = new EventSource('/api/events');

  evtSource.addEventListener('run_start', function(e) {
    const d = JSON.parse(e.data);
    const rid = d._run_id || d.run_id;
    getOrCreatePanel(rid);
    appendToRun(rid, 'Run started (' + d.total + ' cases)', 'neutral');
  });

  evtSource.addEventListener('case_start', function(e) {
    const d = JSON.parse(e.data);
    const rid = d._run_id;
    appendToRun(rid, '\\nRunning: ' + d.case + '...');
    startTimer(rid);
  });

  evtSource.addEventListener('case_done', function(e) {
    const d = JSON.parse(e.data);
    const rid = d._run_id;
    stopTimer(rid);
    const delta = d.score_delta;
    const cls = delta.startsWith('+') && delta !== '+0' ? 'positive' : delta.startsWith('-') ? 'negative' : 'neutral';
    appendToRun(rid, '  Score: ' + d.baseline_score + ' -> ' + d.skill_score + ' (' + delta + ')', cls);
    appendToRun(rid, '  Checks: ' + d.baseline_checks + ' -> ' + d.skill_checks);
    if (d.checks) {
      d.checks.forEach(function(c) {
        const p = c.passed ? 'PASS' : 'FAIL';
        const pcls = c.passed ? 'pass' : 'fail';
        appendToRun(rid, '    [' + c.variant.padEnd(10) + '] ' + p + ' ' + c.name + '  ' + c.detail, pcls);
      });
    }
  });

  evtSource.addEventListener('message', function(e) {
    const d = JSON.parse(e.data);
    const rid = d._run_id;
    let vLabel;
    if (d.variant === 'with_skill') vLabel = 'skill';
    else if (d.variant === 'baseline') vLabel = 'base ';
    else if (d.variant && d.variant.startsWith('judge')) vLabel = 'judge';
    else vLabel = d.variant || '?';
    const prefix = '  [' + vLabel + '] ';
    if (d.type === 'text') {
      const text = d.text.length > 500 ? d.text.substring(0, 500) + '...' : d.text;
      const lines = text.split('\\n');
      appendToRun(rid, prefix + lines[0], 'neutral');
      for (let i = 1; i < Math.min(lines.length, 5); i++) {
        if (lines[i].trim()) appendToRun(rid, '          ' + lines[i], 'neutral');
      }
    } else if (d.type === 'tool_use') {
      const cls = d.tool === 'Write' || d.tool === 'Edit' ? 'positive' :
                  d.tool === 'Skill' ? 'pass' : 'neutral';
      appendToRun(rid, prefix + d.tool + '  ' + (d.summary || ''), cls);
    }
  });

  evtSource.addEventListener('case_error', function(e) {
    const d = JSON.parse(e.data);
    const rid = d._run_id;
    stopTimer(rid);
    appendToRun(rid, '  FAILED: ' + d.error, 'fail');
  });

  evtSource.addEventListener('status', function(e) {
    const d = JSON.parse(e.data);
    const rid = d._run_id || d.run_id;
    stopTimer(rid);
    setRunStatus(rid, d.status);
    if (d.status === 'completed') {
      appendToRun(rid, '\\nRun completed.', 'positive');
      if (d.run_id) appendToRun(rid, 'View results: /run/' + d.run_id);
    } else if (d.status === 'cancelled') {
      appendToRun(rid, '\\nRun cancelled.', 'negative');
    } else if (d.status === 'failed') {
      appendToRun(rid, '\\nRun failed: ' + (d.error || 'unknown'), 'negative');
    }
    // Refresh the dashboard stats when any run finishes
    if (d.status === 'completed' || d.status === 'cancelled' || d.status === 'failed') {
      refreshDashboard();
    }
  });

  function refreshDashboard() {
    fetch('/api/dashboard')
      .then(r => r.text())
      .then(html => {
        const container = document.getElementById('dashboard-container');
        if (container) container.innerHTML = html;
      })
      .catch(() => {});
  }

  evtSource.addEventListener('progress', function(e) {
    const d = JSON.parse(e.data);
    const rid = d._run_id;
    const el = document.getElementById('progress-' + rid);
    if (el) el.textContent = d.completed + '/' + d.total;
  });
}

function startRun() {
  const cases = document.getElementById('cases-select').value;
  const model = document.getElementById('model-select').value;
  const body = 'cases=' + encodeURIComponent(cases) + '&model=' + encodeURIComponent(model);
  fetch('/api/run', {method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: body})
    .then(r => r.json())
    .then(d => {
      if (d.error) { alert(d.error); return; }
      startSSE();
    });
}

function cancelRun() {
  fetch('/api/cancel', {method: 'POST'});
}

// Auto-connect SSE and create panels for active runs
fetch('/api/active-runs').then(r => r.json()).then(runs => {
  if (runs.length > 0) {
    runs.forEach(function(r) { getOrCreatePanel(r.run_id); });
    startSSE();
  }
});
</script>
"""


def _list_eval_cases() -> list[dict]:
    """Discover all eval TOML cases for the dropdown."""
    cases = []
    for path in sorted(EVALS_DIR.glob("*.toml")):
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
            cases.append({
                "id": data["case"]["id"],
                "name": data["case"].get("name", path.stem),
                "stem": path.stem,
            })
        except Exception:
            continue
    return cases


def _delta_class(delta: int) -> str:
    if delta > 0:
        return "positive"
    if delta < 0:
        return "negative"
    return "neutral"


def _delta_str(delta: int) -> str:
    return f"+{delta}" if delta >= 0 else str(delta)


def _render_diff(raw_diff: str) -> str:
    """Render a unified diff with git-style coloring."""
    if not raw_diff or not raw_diff.strip():
        return '<p class="neutral">No diff available.</p>'
    lines = []
    for line in raw_diff.splitlines():
        escaped = html.escape(line)
        if line.startswith("+++") or line.startswith("---"):
            lines.append(f'<div class="diff-file">{escaped}</div>')
        elif line.startswith("@@"):
            lines.append(f'<div class="diff-hunk">{escaped}</div>')
        elif line.startswith("+"):
            lines.append(f'<div class="diff-add">{escaped}</div>')
        elif line.startswith("-"):
            lines.append(f'<div class="diff-del">{escaped}</div>')
        else:
            lines.append(f'<div>{escaped}</div>')
    return f'<div class="diff">{"".join(lines)}</div>'


def _clean_path(path: str) -> str:
    """Replace temp dir prefixes with $TEMP for readability."""
    import re
    path = path.replace("\\", "/")
    path = re.sub(
        r"(?:C:/Users/[^/]+/AppData/Local/Temp|/tmp)/skill_eval/[^/]+/",
        "$TEMP/", path,
    )
    return path


def _md_to_html(text: str) -> str:
    """Markdown to HTML with proper state tracking for tables and code blocks."""
    import re
    lines = text.split("\n")
    result = []
    in_code = False
    in_table = False
    code_buf = []
    table_header_done = False

    def _close_table():
        nonlocal in_table, table_header_done
        if in_table:
            result.append("</table>")
            in_table = False
            table_header_done = False

    for line in lines:
        # Code blocks
        if line.strip().startswith("```"):
            _close_table()
            if in_code:
                result.append(f'<pre><code>{html.escape(chr(10).join(code_buf))}</code></pre>')
                code_buf = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_buf.append(line)
            continue

        # Table rows: line contains | and starts with |
        stripped = line.strip()
        if "|" in stripped and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            # Separator row (---|---|---)
            if all(re.match(r"^[-:]+$", c) for c in cells if c):
                continue

            if not in_table:
                result.append("<table>")
                in_table = True
                table_header_done = False
                tag = "th"
            elif not table_header_done:
                # Second data row after header — mark header as done
                table_header_done = True
                tag = "td"
            else:
                tag = "td"

            row = "".join(f"<{tag}>{_md_inline(c)}</{tag}>" for c in cells)
            result.append(f"<tr>{row}</tr>")
            continue

        # If we were in a table but this line isn't a table row, close it
        _close_table()

        # Headings
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            result.append(f"<h{level}>{_md_inline(m.group(2))}</h{level}>")
            continue

        # Horizontal rule (--- or *** or ___)
        if re.match(r"^\s*[-*_]{3,}\s*$", line):
            result.append('<hr style="border-color:#30363d;">')
            continue

        # Unordered list
        m = re.match(r"^(\s*)[-*]\s+(.*)", line)
        if m:
            result.append(
                f"<div style='margin-left:{len(m.group(1)) + 1}em'>"
                f"&bull; {_md_inline(m.group(2))}</div>"
            )
            continue

        # Ordered list
        m = re.match(r"^(\s*)\d+\.\s+(.*)", line)
        if m:
            result.append(
                f"<div style='margin-left:{len(m.group(1)) + 1}em'>"
                f"{_md_inline(m.group(2))}</div>"
            )
            continue

        # Blank line
        if not stripped:
            result.append("<br>")
            continue

        # Normal text
        result.append(f"<div>{_md_inline(line)}</div>")

    # Close unclosed blocks
    if in_code and code_buf:
        result.append(f'<pre><code>{html.escape(chr(10).join(code_buf))}</code></pre>')
    _close_table()

    return "\n".join(result)


def _md_inline(text: str) -> str:
    """Convert inline markdown: bold, italic, inline code."""
    import re
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r'<code style="background:#21262d;padding:0.1em 0.3em;border-radius:3px;">\1</code>', text)
    return text


def _render_messages(messages: list[dict]) -> str:
    """Render messages with content shown by default, metadata in expandable sections."""
    parts = []
    for i, msg in enumerate(messages):
        msg_type = msg.get("type", "unknown")

        if msg_type == "assistant":
            contents = msg.get("message", {}).get("content", [])
            text_parts = []
            tool_parts = []
            for c in contents:
                if c.get("type") == "text":
                    text_parts.append(c.get("text", ""))
                elif c.get("type") == "tool_use":
                    tool_parts.append(_render_tool_use(c))

            if text_parts:
                text_body = "\n".join(text_parts)
                rendered = _md_to_html(text_body)
                parts.append(
                    f'<div class="msg msg-assistant">'
                    f'<div class="msg-header">Assistant (#{i})</div>'
                    f'<div class="msg-body">{rendered}</div>'
                    f'<details><summary>Metadata</summary>'
                    f'<pre>{html.escape(_msg_metadata(msg))}</pre></details>'
                    f'</div>'
                )
            parts.extend(tool_parts)

        elif msg_type == "tool_result":
            content = msg.get("content", "")
            if isinstance(content, list):
                content = "\n".join(
                    c.get("text", "") for c in content if c.get("type") == "text"
                )
            content = str(content) if not isinstance(content, str) else content
            parts.append(
                f'<div class="msg msg-tool">'
                f'<div class="msg-header">Tool Result (#{i})</div>'
                f'<div class="msg-body"><pre>{html.escape(content)}</pre></div>'
                f'</div>'
            )

        elif msg_type == "result":
            result_text = msg.get("result", "")
            rendered = _md_to_html(result_text)
            parts.append(
                f'<div class="msg msg-result">'
                f'<div class="msg-header">Result (#{i})</div>'
                f'<div class="msg-body">{rendered}</div>'
                f'<details><summary>Metadata</summary>'
                f'<pre>{html.escape(json.dumps(msg, indent=2, ensure_ascii=False))}</pre></details>'
                f'</div>'
            )

        elif msg_type == "system":
            parts.append(
                f'<div class="msg msg-system">'
                f'<div class="msg-header">System (#{i})</div>'
                f'<details><summary>Details</summary>'
                f'<pre>{html.escape(json.dumps(msg, indent=2, ensure_ascii=False))}</pre></details>'
                f'</div>'
            )

    return "\n".join(parts) if parts else "<p>No messages.</p>"


def _render_tool_use(content: dict) -> str:
    """Render a single tool_use content block."""
    tool_name = content.get("name", "?")
    tool_input = content.get("input", {})

    if tool_name in ("Edit", "Write"):
        path = _clean_path(tool_input.get("file_path", ""))
        file_content = tool_input.get("content", tool_input.get("new_string", ""))
        return (
            f'<div class="msg msg-tool">'
            f'<div class="msg-header"><span class="tool-name">{tool_name}</span> {html.escape(path)}</div>'
            f'<div class="msg-body"><pre>{html.escape(file_content)}</pre></div>'
            f'<details><summary>Full input</summary>'
            f'<pre>{html.escape(json.dumps(tool_input, indent=2))}</pre></details>'
            f'</div>'
        )

    if tool_name == "Read":
        path = _clean_path(tool_input.get("file_path", ""))
        return (
            f'<div class="msg msg-tool">'
            f'<div class="msg-header"><span class="tool-name">{tool_name}</span> {html.escape(path)}</div>'
            f'</div>'
        )

    if tool_name == "Glob":
        pattern = tool_input.get("pattern", "")
        path = _clean_path(tool_input.get("path", "")) if tool_input.get("path") else ""
        label = html.escape(pattern) + (f" in {html.escape(path)}" if path else "")
        return (
            f'<div class="msg msg-tool">'
            f'<div class="msg-header"><span class="tool-name">{tool_name}</span> {label}</div>'
            f'</div>'
        )

    if tool_name == "Grep":
        pattern = tool_input.get("pattern", "")
        path = _clean_path(tool_input.get("path", "")) if tool_input.get("path") else ""
        label = html.escape(f"/{pattern}/") + (f" in {html.escape(path)}" if path else "")
        return (
            f'<div class="msg msg-tool">'
            f'<div class="msg-header"><span class="tool-name">{tool_name}</span> {label}</div>'
            f'</div>'
        )

    if tool_name == "Skill":
        skill = tool_input.get("skill", "")
        return (
            f'<div class="msg msg-tool">'
            f'<div class="msg-header"><span class="tool-name">{tool_name}</span> {html.escape(skill)}</div>'
            f'</div>'
        )

    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        return (
            f'<div class="msg msg-tool">'
            f'<div class="msg-header"><span class="tool-name">{tool_name}</span></div>'
            f'<div class="msg-body"><pre>{html.escape(cmd)}</pre></div>'
            f'</div>'
        )

    # Generic fallback
    return (
        f'<div class="msg msg-tool">'
        f'<div class="msg-header"><span class="tool-name">{tool_name}</span></div>'
        f'<details><summary>Input</summary>'
        f'<pre>{html.escape(json.dumps(tool_input, indent=2))}</pre></details>'
        f'</div>'
    )


def _msg_metadata(msg: dict) -> str:
    """Extract non-content metadata from an assistant message."""
    meta = {}
    inner = msg.get("message", {})
    for key in ("model", "id", "stop_reason", "usage"):
        if key in inner:
            meta[key] = inner[key]
    for key in ("session_id", "uuid"):
        if key in msg:
            meta[key] = msg[key]
    return json.dumps(meta, indent=2, ensure_ascii=False)


# ── Page renderers ────────────────────────────────────────────────────────────


_ALL_MODELS = ["haiku", "sonnet", "opus"]


def _case_stem(case_id: str) -> str:
    """Strip trailing _001 etc to get the TOML filename stem."""
    return "_".join(case_id.rsplit("_", 1)[:-1]) if "_" in case_id else case_id


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def _render_dashboard() -> str:
    """Render latest results per case with all models side by side."""
    latest = results.get_latest_by_case()
    eval_cases = _list_eval_cases()
    usage_by_model = results.get_usage_by_model()

    # Always show all models
    models = _ALL_MODELS

    # Group results by model
    by_model: dict[str, list[dict]] = {}
    for r in latest:
        by_model.setdefault(r["model"], []).append(r)

    # Compute stats per model
    def _model_stats(cases):
        if not cases:
            return None
        total_bl = sum(c["baseline_score"] for c in cases)
        total_sk = sum(c["skill_score"] for c in cases)
        return {
            "count": len(cases),
            "total_bl": total_bl,
            "total_sk": total_sk,
            "delta": total_sk - total_bl,
            "improved": sum(1 for c in cases if c["score_delta"] > 0),
            "degraded": sum(1 for c in cases if c["score_delta"] < 0),
            "unchanged": sum(1 for c in cases if c["score_delta"] == 0),
        }

    stats = {m: _model_stats(by_model.get(m, [])) for m in models}

    # Stat cards side by side
    cards = ""
    for m in models:
        s = stats[m]
        u = usage_by_model.get(m, {})
        usage_html = ""
        if u:
            total_in = (u.get("input_tokens") or 0) + (u.get("cache_read_tokens") or 0) + (u.get("cache_creation_tokens") or 0)
            usage_html = f"""
              <hr style="border-color:#30363d;margin:0.5rem 0;">
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.3rem 1rem;font-size:0.85rem;">
                <span style="color:#8b949e;">Input:</span>
                <span>{_fmt_tokens(total_in)}</span>
                <span style="color:#8b949e;">Output:</span>
                <span>{_fmt_tokens(u.get("output_tokens") or 0)}</span>
                <span style="color:#8b949e;">Cache read:</span>
                <span>{_fmt_tokens(u.get("cache_read_tokens") or 0)}</span>
                <span style="color:#8b949e;">Calls:</span>
                <span>{u.get("call_count") or 0}</span>
                <span style="color:#8b949e;">Cost:</span>
                <span>${(u.get("cost_usd") or 0):.2f}</span>
              </div>"""

        if s:
            dc = _delta_class(s["delta"])
            cards += f"""
            <div style="flex:1;background:#161b22;border-radius:6px;padding:1rem;
                        border:1px solid #30363d;">
              <div style="font-size:1.2rem;font-weight:bold;margin-bottom:0.5rem;">{m.upper()}</div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.3rem 1rem;font-size:0.9rem;">
                <span style="color:#8b949e;">Cases:</span><span>{s["count"]}</span>
                <span style="color:#8b949e;">Score:</span>
                <span>{s["total_bl"]} &rarr; {s["total_sk"]}
                  (<span class="{dc}">{_delta_str(s["delta"])}</span>)</span>
                <span style="color:#8b949e;">Improved:</span>
                <span class="positive">{s["improved"]}</span>
                <span style="color:#8b949e;">Unchanged:</span>
                <span class="neutral">{s["unchanged"]}</span>
                <span style="color:#8b949e;">Degraded:</span>
                <span class="negative">{s["degraded"]}</span>
              </div>
              {usage_html}
            </div>"""
        else:
            cards += f"""
            <div style="flex:1;background:#161b22;border-radius:6px;padding:1rem;
                        border:1px solid #30363d;opacity:0.6;">
              <div style="font-size:1.2rem;font-weight:bold;margin-bottom:0.5rem;">{m.upper()}</div>
              <div style="color:#8b949e;font-size:0.9rem;">No results yet</div>
              {usage_html}
            </div>"""

    # Collect all known case_ids (from results + TOML files)
    result_case_ids = {c["case_id"] for c in latest}
    toml_case_ids = {c["id"] for c in eval_cases}
    all_case_ids = sorted(result_case_ids | toml_case_ids)

    case_by_model: dict[str, dict[str, dict]] = {}
    for r in latest:
        case_by_model.setdefault(r["case_id"], {})[r["model"]] = r

    # Table header
    model_headers = ""
    for m in models:
        model_headers += (
            f'<th colspan="3" style="text-align:center;'
            f'border-bottom:2px solid #58a6ff;">{m.upper()}</th>'
        )

    sub_headers = ""
    for _ in models:
        sub_headers += '<th>BL</th><th>Skill</th><th>Δ</th>'

    rows = ""
    for case_id in all_case_ids:
        stem = _case_stem(case_id)
        cells = ""
        for m in models:
            c = case_by_model.get(case_id, {}).get(m)
            if c:
                delta = c["score_delta"]
                dc = _delta_class(delta)
                sk_checks = c["skill_checks_passed"]
                sk_cls = ""
                if sk_checks != "n/a":
                    passed, total = sk_checks.split("/")
                    sk_cls = " positive" if passed == total else " negative"

                # Token stats subtitle
                total_in = c.get("total_input_tokens") or 0
                total_out = c.get("total_output_tokens") or 0
                total_cost = c.get("total_cost_usd") or 0
                token_html = ""
                if total_in or total_out:
                    token_html = (
                        f'<div style="font-size:0.7rem;color:#8b949e;margin-top:0.2rem;">'
                        f'{_fmt_tokens(total_in)}/{_fmt_tokens(total_out)} '
                        f'&nbsp;${total_cost:.2f}</div>'
                    )

                cells += (
                    f'<td>{c["baseline_score"]}</td>'
                    f'<td>{c["skill_score"]}'
                    f'<span class="{sk_cls}" style="font-size:0.75rem;margin-left:0.3rem;">'
                    f'{sk_checks}</span></td>'
                    f'<td class="{dc}">'
                    f'{_delta_str(delta)} '
                    f'<a href="/case/{c["run_id"]}/{c["case_id"]}" '
                    f'title="View" style="color:#8b949e;text-decoration:none;">&#128065;</a> '
                    f'<a href="#" onclick="runCase(\'{stem}\',\'{m}\');return false;" '
                    f'title="Re-run" style="color:#8b949e;text-decoration:none;">&#10227;</a>'
                    f'{token_html}'
                    f'</td>'
                )
            else:
                cells += (
                    f'<td colspan="3" style="text-align:center;">'
                    f'<button class="btn-secondary" '
                    f'style="padding:0.15rem 0.4rem;font-size:0.75rem;" '
                    f'onclick="runCase(\'{stem}\',\'{m}\')">Run</button>'
                    f'</td>'
                )

        any_result = next(
            (case_by_model[case_id][m] for m in models
             if m in case_by_model.get(case_id, {})),
            None,
        )
        link = f'/case/{any_result["run_id"]}/{case_id}' if any_result else "#"
        rows += f'<tr><td><a href="{link}">{case_id}</a></td>{cells}</tr>\n'

    return f"""
    <h2>Latest Results</h2>
    <div style="display:flex;gap:1rem;margin-bottom:1.5rem;">
      {cards}
    </div>
    <table>
    <tr><th rowspan="2">Case</th>{model_headers}</tr>
    <tr>{sub_headers}</tr>
    {rows}
    </table>
    <script>
    function runCase(stem, model) {{
      const body = 'cases=' + encodeURIComponent(stem) + '&model=' + encodeURIComponent(model);
      fetch('/api/run', {{method:'POST', headers:{{'Content-Type':'application/x-www-form-urlencoded'}}, body:body}})
        .then(r => r.json())
        .then(d => {{
          if (d.run_id) {{ window.scrollTo(0, 0); location.reload(); }}
          else {{ alert(d.error || 'Failed to start'); }}
        }});
    }}
    </script>"""


def page_runs() -> str:
    runs = results.list_runs()
    eval_cases = _list_eval_cases()

    run_rows = ""
    for r in runs:
        rid = r["run_id"]
        run_rows += (
            f'<tr><td><a href="/run/{rid}">{rid}</a></td>'
            f'<td>{r["started_at"] or ""}</td>'
            f'<td>{r["case_count"]}</td></tr>\n'
        )
    runs_table = f"""
    <table>
    <tr><th>Run ID</th><th>Started</th><th>Cases</th></tr>
    {run_rows}
    </table>""" if runs else "<p>No completed runs yet.</p>"

    # Build case dropdown options
    case_options = '<option value="">All cases</option>\n'
    # Group by prefix
    prefixes = {}
    for c in eval_cases:
        prefix = c["stem"].split("_")[0]
        prefixes.setdefault(prefix, []).append(c)
    for prefix in sorted(prefixes):
        case_options += f'<option value="{prefix}_*">All {prefix}_* ({len(prefixes[prefix])})</option>\n'
    for c in eval_cases:
        case_options += f'<option value="{c["stem"]}">{c["id"]} — {c["name"]}</option>\n'

    body = f"""
    <div class="run-panel">
      <h2>Run Evaluations</h2>
      <div style="display:flex;gap:1rem;align-items:center;margin:0.5rem 0;">
        <select id="cases-select" style="width:400px;">
          {case_options}
        </select>
        <select id="model-select">
          <option value="sonnet">Sonnet</option>
          <option value="opus">Opus</option>
          <option value="haiku">Haiku</option>
        </select>
        <button class="btn-primary" onclick="startRun()">Run</button>
      </div>
      <div id="live-panels" style="display:flex;gap:1rem;flex-wrap:wrap;margin-top:0.75rem;"></div>
    </div>

    <div id="dashboard-container">{_render_dashboard()}</div>

    <h2>Past Runs</h2>
    {runs_table}
    {_LIVE_SCRIPT}"""
    return _page("Skill Eval", body)


def page_run(run_id: str) -> str:
    summaries = results.get_summaries(run_id)
    if not summaries:
        return _page("Not Found", f"<p>No results for run {run_id}</p>")

    total_bl = sum(s["baseline_score"] for s in summaries)
    total_sk = sum(s["skill_score"] for s in summaries)
    total_delta = total_sk - total_bl
    improved = sum(1 for s in summaries if s["score_delta"] > 0)
    degraded = sum(1 for s in summaries if s["score_delta"] < 0)
    unchanged = sum(1 for s in summaries if s["score_delta"] == 0)

    stats = f"""
    <div style="display:flex;gap:2rem;margin:1rem 0;">
      <div><strong>Cases:</strong> {len(summaries)}</div>
      <div><strong>Total:</strong> {total_bl} &rarr; {total_sk}
        (<span class="{_delta_class(total_delta)}">{_delta_str(total_delta)}</span>)</div>
      <div class="positive"><strong>Improved:</strong> {improved}</div>
      <div class="neutral"><strong>Unchanged:</strong> {unchanged}</div>
      <div class="negative"><strong>Degraded:</strong> {degraded}</div>
    </div>"""

    rows = ""
    for s in summaries:
        delta = s["score_delta"]
        dc = _delta_class(delta)
        stem = "_".join(s["case_id"].rsplit("_", 1)[:-1]) if "_" in s["case_id"] else s["case_id"]
        rows += (
            f'<tr>'
            f'<td><a href="/case/{run_id}/{s["case_id"]}">{s["case_id"]}</a></td>'
            f'<td>{html.escape(s["skill"] or "")}</td>'
            f'<td>{s["baseline_score"]}</td>'
            f'<td>{s["skill_score"]}</td>'
            f'<td class="{dc}">{_delta_str(delta)}</td>'
            f'<td>{s["baseline_checks_passed"]}</td>'
            f'<td>{s["skill_checks_passed"]}</td>'
            f'<td><button class="btn-secondary" style="padding:0.2rem 0.5rem;font-size:0.8rem;" '
            f'onclick="rerunCases(\'{stem}\')">Re-run</button></td>'
            f'</tr>\n'
        )

    # Collect all case stems for re-run
    all_stems = set()
    for s in summaries:
        # case_id is like "fixture_python_review_001", stem is "fixture_python_review"
        stem = "_".join(s["case_id"].rsplit("_", 1)[:-1]) if "_" in s["case_id"] else s["case_id"]
        all_stems.add(stem)
    rerun_all_value = ",".join(sorted(all_stems))

    body = f"""{stats}
    <div style="margin:1rem 0;">
      <button class="btn-primary" onclick="rerunCases('{html.escape(rerun_all_value)}')">
        Re-run all {len(summaries)} cases
      </button>
    </div>
    <table>
    <tr><th>Case</th><th>Skills</th><th>Baseline</th><th>Skill</th>
        <th>Delta</th><th>BL Checks</th><th>Skill Checks</th><th></th></tr>
    {rows}
    </table>
    <script>
    function rerunCases(pattern) {{
      if (!confirm('Start re-run for: ' + pattern + '?')) return;
      const body = 'cases=' + encodeURIComponent(pattern) + '&model=sonnet';
      fetch('/api/run', {{method: 'POST', headers: {{'Content-Type': 'application/x-www-form-urlencoded'}}, body: body}})
        .then(r => r.json())
        .then(d => {{
          if (d.run_id) {{ window.location.href = '/'; }}
          else {{ alert(d.error || 'Failed to start'); }}
        }});
    }}
    </script>"""

    crumbs = '<a href="/">Runs</a> / ' + run_id
    return _page(f"Run {run_id}", body, crumbs)


def page_case(run_id: str, case_id: str) -> str:
    summaries = results.get_summaries(run_id)
    summary = next((s for s in summaries if s["case_id"] == case_id), None)
    if not summary:
        return _page("Not Found", f"<p>No results for {case_id}</p>")

    delta = summary["score_delta"]

    # Checks
    checks = results.get_checks(run_id, case_id)
    check_rows = ""
    for c in checks:
        p = "pass" if c["passed"] else "fail"
        badge = f'<span class="badge badge-{p}">{p.upper()}</span>'
        check_rows += (
            f'<tr><td>{html.escape(c["variant"])}</td>'
            f'<td>{badge}</td>'
            f'<td>{html.escape(c["check_name"] or "")}</td>'
            f'<td>{html.escape(c["detail"] or "")}</td></tr>\n'
        )
    check_table = f"""
    <h2>Check Results</h2>
    <table>
    <tr><th>Variant</th><th>Result</th><th>Check</th><th>Detail</th></tr>
    {check_rows}
    </table>""" if checks else ""

    # Scores
    scores = results.get_scores(run_id, case_id)
    score_rows = ""
    for s in scores:
        score_rows += (
            f'<tr><td>{html.escape(s["variant"])}</td>'
            f'<td>{html.escape(s["criterion"] or "")}</td>'
            f'<td>{s["score"]}</td>'
            f'<td>{html.escape(s["explanation"] or "")}</td></tr>\n'
        )
    score_table = f"""
    <h2>Rubric Scores</h2>
    <table>
    <tr><th>Variant</th><th>Criterion</th><th>Score</th><th>Explanation</th></tr>
    {score_rows}
    </table>""" if scores else ""

    # Git-style diff
    diff_data = results.get_diff(run_id, case_id)
    diff_html = ""
    if diff_data:
        rendered_diff = _render_diff(diff_data.get("raw_diff", ""))
        ai_summary = diff_data.get("ai_summary", "")
        diff_html = f"""
    <h2>Diff</h2>
    <div class="summary">{html.escape(ai_summary)}</div>
    <details open><summary><strong>Raw Diff</strong></summary>
    {rendered_diff}
    </details>"""

    from urllib.parse import quote as _q
    msg_links = f"""
    <h2>Message Streams</h2>
    <p>
      <strong>Agent:</strong>
      <a href="/messages/{run_id}/{case_id}/baseline">Baseline</a> |
      <a href="/messages/{run_id}/{case_id}/with_skill">With-skill</a>
    </p>
    <p>
      <strong>Judge:</strong>
      <a href="/messages/{run_id}/{case_id}/{_q('judge:score:baseline')}">Score (baseline)</a> |
      <a href="/messages/{run_id}/{case_id}/{_q('judge:score:with_skill')}">Score (with-skill)</a> |
      <a href="/messages/{run_id}/{case_id}/{_q('judge:diff')}">Diff summary</a>
    </p>"""

    # Token usage per variant
    usage_rows = results.get_case_usage(run_id, case_id)
    usage_html = ""
    if usage_rows:
        total_cost = sum(u["cost_usd"] or 0 for u in usage_rows)
        total_in = sum(
            (u["input_tokens"] or 0) + (u["cache_read_tokens"] or 0)
            + (u["cache_creation_tokens"] or 0)
            for u in usage_rows
        )
        total_out = sum(u["output_tokens"] or 0 for u in usage_rows)

        variant_rows = ""
        for u in usage_rows:
            vin = (u["input_tokens"] or 0) + (u["cache_read_tokens"] or 0) + (u["cache_creation_tokens"] or 0)
            variant_rows += (
                f'<tr><td>{html.escape(u["variant"])}</td>'
                f'<td>{_fmt_tokens(u["input_tokens"] or 0)}</td>'
                f'<td>{_fmt_tokens(u["cache_read_tokens"] or 0)}</td>'
                f'<td>{_fmt_tokens(u["cache_creation_tokens"] or 0)}</td>'
                f'<td>{_fmt_tokens(u["output_tokens"] or 0)}</td>'
                f'<td>{_fmt_tokens(vin)}</td>'
                f'<td>${(u["cost_usd"] or 0):.4f}</td></tr>\n'
            )

        usage_html = f"""
    <h2>Token Usage</h2>
    <div style="margin-bottom:0.5rem;color:#8b949e;">
      Total: <strong>{_fmt_tokens(total_in)}</strong> input &middot;
      <strong>{_fmt_tokens(total_out)}</strong> output &middot;
      <strong>${total_cost:.4f}</strong> cost
    </div>
    <table>
    <tr><th>Variant</th><th>Fresh In</th><th>Cache Read</th><th>Cache Create</th>
        <th>Output</th><th>Total In</th><th>Cost</th></tr>
    {variant_rows}
    </table>"""

    # Commands used to run each variant
    bl_result = results.get_case_result(run_id, case_id, "baseline")
    sk_result = results.get_case_result(run_id, case_id, "with_skill")
    cmd_html = ""
    if (bl_result and bl_result.get("command")) or (sk_result and sk_result.get("command")):
        cmd_html = "<h2>Commands</h2>"
        if bl_result and bl_result.get("command"):
            cmd_html += (
                f'<details><summary><strong>Baseline</strong></summary>'
                f'<pre>{html.escape(bl_result["command"])}</pre></details>'
            )
        if sk_result and sk_result.get("command"):
            cmd_html += (
                f'<details><summary><strong>With-skill</strong></summary>'
                f'<pre>{html.escape(sk_result["command"])}</pre></details>'
            )

    body = f"""
    <div style="margin:1rem 0;">
      <strong>Score:</strong> {summary["baseline_score"]} &rarr; {summary["skill_score"]}
      (<span class="{_delta_class(delta)}">{_delta_str(delta)}</span>)
      &nbsp;&nbsp;
      <strong>Checks:</strong> {summary["baseline_checks_passed"]} &rarr; {summary["skill_checks_passed"]}
    </div>
    {check_table}
    {score_table}
    {diff_html}
    {usage_html}
    {msg_links}
    {cmd_html}"""

    crumbs = f'<a href="/">Runs</a> / <a href="/run/{run_id}">{run_id}</a> / {case_id}'
    return _page(case_id, body, crumbs)


def page_messages(run_id: str, case_id: str, variant: str) -> str:
    messages = results.get_case_messages(run_id, case_id, variant)
    if not messages:
        return _page("Not Found", "<p>No messages found.</p>")

    rendered = _render_messages(messages)

    body = f"""
    <div style="margin-bottom:1rem;">
      <strong>{len(messages)}</strong> messages
      &nbsp;|&nbsp;
      <a href="/messages-raw/{run_id}/{case_id}/{variant}">View raw JSON</a>
    </div>
    {rendered}"""

    crumbs = (
        f'<a href="/">Runs</a> / <a href="/run/{run_id}">{run_id}</a> / '
        f'<a href="/case/{run_id}/{case_id}">{case_id}</a> / {variant}'
    )
    return _page(f"{case_id} — {variant}", body, crumbs)


def page_messages_raw(run_id: str, case_id: str, variant: str) -> str:
    messages = results.get_case_messages(run_id, case_id, variant)
    if not messages:
        return _page("Not Found", "<p>No messages found.</p>")

    formatted = json.dumps(messages, indent=2, ensure_ascii=False)
    body = f'<pre>{html.escape(formatted)}</pre>'
    crumbs = (
        f'<a href="/">Runs</a> / <a href="/run/{run_id}">{run_id}</a> / '
        f'<a href="/case/{run_id}/{case_id}">{case_id}</a> / '
        f'<a href="/messages/{run_id}/{case_id}/{variant}">{variant}</a> / raw'
    )
    return _page(f"{case_id} — {variant} (raw)", body, crumbs)


# ── HTTP Handler ──────────────────────────────────────────────────────────────


class Handler(BaseHTTPRequestHandler):

    def handle(self):
        """Suppress connection abort errors from Windows clients."""
        try:
            super().handle()
        except (ConnectionAbortedError, ConnectionResetError,
                BrokenPipeError, OSError):
            pass

    def _send_json(self, data, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, body: str):
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        parts = path.split("/")

        try:
            if path == "/api/status":
                self._send_json(run_manager.get_status())
                return
            if path == "/api/active-runs":
                active = run_manager.get_active_runs()
                self._send_json([
                    {
                        "run_id": r["run_id"],
                        "status": r["status"],
                        "current_case": r["current_case"],
                        "total_cases": r["total_cases"],
                        "completed_cases": r["completed_cases"],
                    }
                    for r in active
                ])
                return

            if path == "/api/dashboard":
                self._send_html(_render_dashboard())
                return

            if path == "/api/events":
                self._handle_sse()
                return

            if path == "/":
                self._send_html(page_runs())
            elif parts[1] == "run" and len(parts) == 3:
                self._send_html(page_run(parts[2]))
            elif parts[1] == "case" and len(parts) == 4:
                self._send_html(page_case(parts[2], parts[3]))
            elif parts[1] == "messages" and len(parts) == 5:
                from urllib.parse import unquote
                self._send_html(page_messages(parts[2], parts[3], unquote(parts[4])))
            elif parts[1] == "messages-raw" and len(parts) == 5:
                from urllib.parse import unquote
                self._send_html(page_messages_raw(parts[2], parts[3], unquote(parts[4])))
            else:
                self.send_error(404)
        except (BrokenPipeError, ConnectionResetError,
                ConnectionAbortedError, OSError):
            pass  # Client disconnected
        except Exception as e:
            try:
                self.send_error(500, str(e))
            except (BrokenPipeError, ConnectionResetError,
                    ConnectionAbortedError, OSError):
                pass

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/run":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8") if length else ""
            params = parse_qs(body)
            cases = params.get("cases", [""])[0] or None
            model = params.get("model", ["sonnet"])[0]
            if cases and "*" not in cases:
                cases = cases + "*"
            run_id = run_manager.start_run(
                cases_pattern=cases, model=model, model_override=True,
            )
            if run_id:
                self._send_json({"run_id": run_id})
            else:
                self._send_json({"error": "No cases matched the pattern"}, 409)
            return

        if path == "/api/cancel":
            params = parse_qs(urlparse(self.path).query)
            cancel_run_id = params.get("run_id", [None])[0]
            cancelled = run_manager.cancel(cancel_run_id)
            self._send_json({"cancelled": cancelled})
            return

        self.send_error(404)

    def _handle_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        import time

        last_event_id = int(self.headers.get("Last-Event-ID", 0))
        # Track runs we've seen so we keep draining events after they complete
        watched_runs: set[str] = set()
        drained_runs: set[str] = set()

        while True:
            # Add currently active runs to the watched set
            for run in run_manager.get_active_runs():
                watched_runs.add(run["run_id"])

            # Poll events from every watched run (even finished ones) until drained
            to_drop = []
            for run_id in watched_runs:
                if run_id in drained_runs:
                    to_drop.append(run_id)
                    continue

                events = run_manager.get_events_since(run_id, last_event_id)
                for evt in events:
                    last_event_id = max(last_event_id, evt["id"])
                    event = evt["event"]
                    data = evt["data"]
                    data["_run_id"] = run_id
                    try:
                        self.wfile.write(
                            f"id: {evt['id']}\n"
                            f"event: {event}\ndata: {json.dumps(data)}\n\n".encode("utf-8")
                        )
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError,
                            ConnectionAbortedError, OSError):
                        return

                    # If we've sent a terminal status event, mark drained after next tick
                    if event == "status" and data.get("status") in (
                        "completed", "cancelled", "failed"
                    ):
                        drained_runs.add(run_id)

            for rid in to_drop:
                watched_runs.discard(rid)

            try:
                self.wfile.write(b": keepalive\n\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError,
                    ConnectionAbortedError, OSError):
                return

            time.sleep(2)

    def log_message(self, format, *args):
        pass


def _watch_and_restart(port: int) -> None:
    """Watch src/*.py for changes and restart the server process."""
    import os
    import subprocess
    import time
    from pathlib import Path

    src_dir = Path(__file__).resolve().parent
    watch_files = list(src_dir.glob("*.py"))

    def _mtimes():
        return {f: f.stat().st_mtime for f in watch_files if f.exists()}

    while True:
        mtimes = _mtimes()
        env = {**os.environ, "EVAL_SERVER_CHILD": "1"}
        print(f"[watcher] Starting server on port {port}...")
        proc = subprocess.Popen(
            [sys.executable, "-m", "src.server", str(port)],
            cwd=str(src_dir.parent),
            env=env,
        )
        try:
            while proc.poll() is None:
                time.sleep(1)
                current = _mtimes()
                changed = [
                    f.name for f in watch_files
                    if f in current and current[f] != mtimes.get(f)
                ]
                if changed:
                    print(f"[watcher] Changed: {', '.join(changed)} — restarting...")
                    proc.terminate()
                    proc.wait(timeout=5)
                    break
            else:
                # Process exited on its own — restart it
                print(f"[watcher] Server exited (code {proc.returncode}), restarting...")
                time.sleep(1)
        except KeyboardInterrupt:
            proc.terminate()
            proc.wait(timeout=5)
            break


def main(port: int = 8000, watch: bool = False):
    if watch and not os.environ.get("EVAL_SERVER_CHILD"):
        _watch_and_restart(port)
        return

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    print(f"Eval viewer: http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        if not os.environ.get("EVAL_SERVER_CHILD"):
            print("\nStopped.")


if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    main(p)
