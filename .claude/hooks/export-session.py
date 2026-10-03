#!/usr/bin/env python3
"""Claude Code hook: export the current session transcript to sessions/<date>-<session-id>.md.

Runs on Stop (after every reply) and SessionEnd. Reads the hook payload from stdin,
keeps only the user's messages and Claude's text replies (no tool calls, tool output,
or thinking), redacts anything that looks like a secret value, and overwrites the
Markdown file so it always reflects the latest turn. The raw JSONL is never copied.
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

TAG_BLOCKS = re.compile(
    r"<(system-reminder|ide_selection|ide_opened_file|command-[a-z-]+|local-command-[a-z-]+)>.*?</\1>",
    re.DOTALL,
)

# key: value / key=value pairs whose key names a secret; `!secret name` references are left alone.
SECRET_KV = re.compile(
    r"""(?ix)
    \b([\w-]*(?:password|passwd|api_key|apikey|encryption_key|token|secret|ota_key|psk)[\w-]*)
    (\s*[:=]\s*)
    (?!!secret\b)
    (["']?)([^\s"',}]{4,})\3
    """
)
# ESPHome API encryption keys and similar 32-byte base64 blobs.
BASE64_KEY = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{43}=(?![A-Za-z0-9+/=])")


def redact(text: str) -> str:
    text = SECRET_KV.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}<redacted>{m.group(3)}", text)
    return BASE64_KEY.sub("<redacted>", text)


def text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n\n".join(b.get("text", "") for b in content if b.get("type") == "text")
    return ""


def main() -> None:
    payload = json.load(sys.stdin)
    transcript = Path(payload.get("transcript_path", ""))
    session_id = payload.get("session_id", "")
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".")
    if not transcript.is_file() or not session_id:
        return

    title = None
    started = None
    turns = []  # list of [role, text]; consecutive assistant chunks are merged

    with transcript.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = entry.get("type")
            if kind == "ai-title":
                title = entry.get("aiTitle") or title
                continue
            if kind not in ("user", "assistant"):
                continue
            if entry.get("isSidechain") or entry.get("isMeta") or entry.get("isCompactSummary"):
                continue
            if started is None and entry.get("timestamp"):
                started = entry["timestamp"]

            text = TAG_BLOCKS.sub("", text_of(entry.get("message", {}).get("content"))).strip()
            if not text:
                continue
            role = "Claude" if kind == "assistant" else "User"
            if turns and turns[-1][0] == role == "Claude":
                turns[-1][1] += "\n\n" + text
            else:
                turns.append([role, text])

    if not turns:
        return

    start = datetime.fromisoformat(started.replace("Z", "+00:00")).astimezone() if started else datetime.now().astimezone()
    out_dir = project_dir / "sessions"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"{start:%Y-%m-%d}-{session_id}.md"

    lines = [
        f"# {title or 'Claude Code session'}",
        "",
        f"- Session: `{session_id}`",
        f"- Started: {start:%Y-%m-%d %H:%M %Z}",
        "",
    ]
    for role, text in turns:
        lines += ["---", "", f"## {role}", "", redact(text), ""]

    out_file.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # never block Claude because an export failed
        print(f"export-session: {exc}", file=sys.stderr)
