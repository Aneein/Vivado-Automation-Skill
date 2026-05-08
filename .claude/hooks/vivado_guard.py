#!/usr/bin/env python3
"""Claude Code guardrails for Vivado Automation Skill.

This hook makes the fragile parts deterministic:
- On Vivado/Vitis prompts, inject workflow instructions before the model answers.
- Block attempts to execute Windows Vivado/Vitis from Linux/remote Claude Code.
- Block ad-hoc Vivado Tcl execution unless it uses the generated hard workflow.
"""

from __future__ import annotations

import json
import os
import platform
import re
import sys


VIVADO_WORDS = (
    "vivado",
    "vitis",
    "xsct",
    "xilinx",
    "bitstream",
    "synthesis",
    "implementation",
    "block design",
    "bd",
    "xdc",
    "verilog",
    "vhdl",
)


def read_event() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            },
            ensure_ascii=False,
        )
    )


def is_windows_host() -> bool:
    return platform.system().lower().startswith("win")


def is_remote_claude() -> bool:
    return os.environ.get("CLAUDE_CODE_REMOTE", "").lower() == "true"


def prompt_text(event: dict) -> str:
    for key in ("prompt", "user_prompt", "message"):
        value = event.get(key)
        if isinstance(value, str):
            return value
    return json.dumps(event, ensure_ascii=False)


def bash_command(event: dict) -> str:
    tool_input = event.get("tool_input", {})
    if isinstance(tool_input, dict):
        return str(tool_input.get("command", ""))
    return ""


def looks_like_windows_path(command: str) -> bool:
    return bool(re.search(r"[A-Za-z]:[\\/]", command))


def is_vivado_related(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in VIVADO_WORDS)


def prompt_mode(event: dict) -> int:
    text = prompt_text(event)
    if not is_vivado_related(text):
        return 0

    print(
        """
Vivado Automation Guard:
- Do not hand-write ad-hoc Vivado Tcl for full flows.
- First run `python scripts/vivado_assistant.py doctor ...` for pasted Vivado paths.
- For project/BD/synthesis/implementation/bitstream/XSA, use `python scripts/vivado_assistant.py run-rtl-workflow ... --run`.
- Full automation requires Claude Code to run in the same Windows environment that owns Vivado; the CLI must execute Vivado and inspect logs directly.
- Do not run Vitis build/run automation by default. Generate PS C files only; keep `patch-vitis-makefile` for the Vivado/Vitis 2021.1 BSP Makefile issue after the user creates the Vitis application.
""".strip()
    )
    return 0


def bash_mode(event: dict) -> int:
    command = bash_command(event)
    lowered = command.lower()

    if not is_vivado_related(command) and "vivado_assistant.py" not in lowered:
        return 0

    if "vivado_assistant.py" in lowered and "run-rtl-workflow" in lowered:
        if "--run" not in lowered and "--plan-only" not in lowered:
            deny("Full Vivado workflow must execute automatically. Add `--run`; use `--plan-only` only when the user explicitly asks not to run Vivado.")
            return 0
        if "run_workflow.bat" in lowered or "--write-bat" in lowered:
            deny("Batch-file workflow is not allowed as the main path. Use `run-rtl-workflow ... --run` so the CLI executes Vivado and reads logs.")
            return 0
        return 0

    if ("vivado_assistant.py" in lowered and "doctor" in lowered):
        return 0

    if not is_windows_host() or is_remote_claude():
        if any(token in lowered for token in ("vivado", "vitis", "xsct", "hw_server")) or looks_like_windows_path(command):
            deny(
                "Vivado/Vitis appears to be on Windows, but Claude Code is not running in a Windows local shell. "
                "Run Claude Code from the Windows environment that owns Vivado so the CLI can execute Vivado and inspect logs directly."
            )
            return 0

    if re.search(r"vivado(\.bat|\.exe)?\s+.*-mode\s+batch\s+.*-source", lowered):
        normalized = lowered.replace("\\", "/")
        if "vivado_assistant" not in normalized or "run_workflow.tcl" not in normalized:
            deny(
                "Ad-hoc Vivado batch Tcl is blocked. Regenerate and run the hard workflow: `python scripts/vivado_assistant.py run-rtl-workflow ... --run`."
            )
            return 0

    return 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    event = read_event()
    if mode == "prompt":
        return prompt_mode(event)
    if mode == "bash":
        return bash_mode(event)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
