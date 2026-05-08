---
description: Generate a hard ordered Vivado workflow instead of hand-writing Tcl
---

Use the Vivado Automation Skill hard workflow. Do not hand-write full-flow Tcl.

Steps:

1. Run `python scripts/vivado_assistant.py doctor` for any pasted Vivado path.
2. Run the workflow with `python scripts/vivado_assistant.py run-rtl-workflow ... --run`.
3. If running in Linux/remote Claude Code with Windows Vivado paths, stop and tell the user to run Claude Code from the Windows environment that owns Vivado.
4. Use single-stage commands only for diagnosis.
5. Do not produce `run_workflow.bat` or ask the user to run Tcl/bat manually.

User request:

$ARGUMENTS
