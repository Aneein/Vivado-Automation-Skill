---
name: vivado-assistant-automation
description: "Script-first Vivado/Vitis automation for project migration between Vivado 2020.2 and 2021.1, clean project rebuilds from user sources, BD Tcl export/recreate flows, and Vitis 2021.1 BSP Makefile patching."
---

# Vivado Assistant Automation

You are a script-first Vivado/Vitis automation assistant. Prefer running or generating scripts from `scripts/vivado_assistant.py` over writing ad hoc Tcl snippets in chat.

## Core Rule

When the user asks for Vivado project creation, source insertion, BD creation, output product generation, synthesis, implementation, bitstream, or hardware export, do not hand-write Tcl. Use the hard workflow command first:

```bash
python scripts/vivado_assistant.py run-rtl-workflow ... --run
```

This is an execution command. It must include `--run` for normal automation. The Python CLI calls Vivado itself, streams logs, and writes `vivado_run.log`, per-phase logs under `stage_logs/`, `last_phase.txt`, and `debug_summary.txt` under the external automation directory. It enforces:

1. resolve/validate Vivado launcher
2. create project
3. add HDL/XDC/sim files only after the project exists
4. create BD/wrapper only after the project exists
5. generate output products
6. run synthesis
7. run implementation to bitstream
8. write bit/bin/XSA outputs into stable project-root folders

Only use the older commands (`create-project`, `create-bd`, `run-synthesis`, etc.) for manual diagnosis or when the user explicitly asks for a single stage.

Do not stop after generating Tcl, do not generate `run_workflow.bat`, and do not ask the user to execute Tcl/bat manually. Use `--plan-only` only when the user explicitly asks not to run Vivado. If a stage fails, read `debug_summary.txt`, `last_phase.txt`, and the matching `stage_logs/<phase>.log` before editing anything.

## Design Intent Closure

Before writing HDL or BD Tcl, translate the user's natural-language goal into a short design checklist. Keep it task-specific:

- user-visible behavior: LEDs, UART text, buttons, DMA transfer, interrupt, memory map, clock rate
- required design elements: top ports, IP blocks, PS UART, AXI GPIO, reset blocks, clocks, address segments, external interfaces
- required files: HDL, simulation sources, XDC, BD wrapper, exported XSA, Vitis `main.c`
- success checks after each design step

Then enforce the checklist after each design step, before moving on:

1. **After Verilog/VHDL generation:** verify top module/entity exists, intended ports exist, state machines/counters/resets match the behavior, and required XDC port names match the HDL ports.
2. **After adding BD IP:** verify every required IP cell exists. Do not assume `apply_bd_automation` configured intent-specific peripherals.
3. **After BD wiring:** verify clocks, resets, AXI interfaces, external ports, interrupts, UART, and address segments required by the goal are connected/configured. Then run `validate_bd_design`.
4. **After wrapper generation:** verify the wrapper is the project top.
5. **After synthesis/implementation:** read run status, DRC, timing summary, and bit/XSA location.
6. **After hardware export:** inspect the XSA archive itself. A Vitis-ready exported hardware platform must contain at least one `.bit` and one `.hwh`; do not trust `write_hw_platform` completion alone.

For serial-print PS designs, explicitly choose the PS UART required by the board, for example `--ps-uart uart1` for the common PYNQ-Z2 USB-UART mapping. The tool must assert the UART is enabled and has MIO assigned. This is one example of the general rule: if the user's goal depends on a peripheral or interface, configure and assert that peripheral or interface explicitly.

For Zynq board designs, especially PYNQ-Z2, do not rely on a bare part-only project when the board part is known. Pass `--board-part`, for example:

```bash
--part xc7z020clg400-1 --board-part tul.com.tw:pynq-z2:part0:1.0
```

The workflow must set and assert `board_part` immediately after `create_project`, before creating the BD. A missing board part leaves `BoardPart` empty in the `.xpr`; PS7 automation may then miss board-specific initialization/preset details, which can surface later in Vitis/JTAG as errors such as PS debug/APB memory access being disabled.

## Required Pipelines

Use one of these two normal Vivado pipelines. Each step must complete before the next starts; if one step fails, stop and debug that stage.

### PL RTL Pipeline

1. Create the Vivado project.
2. Add Verilog/SystemVerilog/VHDL sources.
3. Run the PL design review: top selected, intended ports present, constraints match ports.
4. Add XDC constraints to `constrs_1`.
5. Run synthesis.
6. Run implementation to `write_bitstream`.
7. Locate the `.bit` in Vivado's standard `impl_1` run directory.
8. If hardware export is requested, run `write_hw_platform -include_bit`.

### BD Pipeline

1. Create the Vivado project.
2. Create the block design.
3. Add IP/BD devices.
4. Connect clocks, resets, AXI, external ports, and addresses.
5. Run the BD design review: required cells exist, required pins/interfaces are connected, addresses exist where needed, board/peripheral-specific settings are explicit.
6. Run `validate_bd_design`; stop if validation fails.
7. Generate output products.
8. Generate HDL wrapper and add it to sources.
9. Add XDC constraints to `constrs_1`.
10. Run synthesis.
11. Run implementation to `write_bitstream`.
12. Locate the `.bit` in Vivado's standard `impl_1` run directory.
13. If hardware export is requested, run `write_hw_platform -include_bit`.
14. Open the generated XSA and verify it contains `.bit` and `.hwh` before telling the user it is ready for Vitis.

These are the only default full-flow sequences. Do not synthesize before wrapper generation in a BD flow. Do not add XDC as an orphan file outside `constrs_1`.

If the agent is running from Linux/WSL and the Vivado path is a Windows path, do not ask the user to copy Tcl errors back and forth. Run the CLI from the Windows environment that owns Vivado so it can execute and inspect logs directly.

Before using a pasted Vivado path, run:

```bash
python scripts/vivado_assistant.py doctor --vivado-candidate "<pasted path>"
```

The doctor command must resolve folders such as `bin/unwrapped/win64.o` back to `<Vivado>/<version>/bin/vivado.bat`; Start Menu folders are not valid launchers.

## Claude Code Guard

This skill repository includes project-level Claude Code hooks in `.claude/settings.json` and `.claude/hooks/vivado_guard.py`.

The hooks are part of the intended workflow:

- `UserPromptSubmit` adds hard workflow guidance for Vivado/Vitis prompts.
- `PreToolUse` for Bash blocks ad-hoc Vivado batch Tcl and blocks Windows Vivado/Vitis execution from Linux/remote Claude Code.
- The project slash command `/vivado-workflow` reminds Claude Code to use `doctor` and `run-rtl-workflow`.

If these hooks block a command, follow the hook message. Do not bypass it by manually writing new Tcl.

## Initialization

Before using Vivado automation for the first time, ask the user which Vivado executable paths they have. One version is enough for normal automation; two versions are only needed when the user wants cross-version migration.

- Vivado 2020.2 executable path
- Vivado 2021.1 executable path

Then run:

```bash
python scripts/vivado_assistant.py init \
  --vivado-2020-2 "C:/Xilinx/Vivado/2020.2/bin/vivado.bat" \
  --vivado-2021-1 "C:/Xilinx/Vivado/2021.1/bin/vivado.bat"
```

For a user with only one Vivado installation, run the same command with only that version:

```bash
python scripts/vivado_assistant.py init \
  --vivado-2021-1 "C:/Xilinx/Vivado/2021.1/bin/vivado.bat"
```

**Path verification rule:** When a user provides a Vivado path, ALWAYS verify that the path points to an actual executable file (not a directory). Use Glob or Read to confirm the file exists and is the correct entry point (`vivado.bat` on Windows). If the user provides a path like `.../bin/unwrapped/win64.o`, check whether it is a directory (Vivado's internal binary folder) and correct it to `.../bin/vivado.bat`. Do not blindly store unverified paths into config.

This writes `vivado_assistant_config.json` in the current working directory by default. The user may choose the default executable with `--default-version 2020.2` or `--default-version 2021.1`.

After initialization:

- Normal project/build commands use the configured default Vivado. If only one Vivado is configured, they use that one.
- `migrate-project` should use the source and target versions chosen by the user, for example `--source-version 2020.2 --target-version 2021.1`.
- A specific command may still override the executable with `--vivado`, `--source-vivado`, or `--target-vivado`.

## Project Structure & Path Rules

Vivado owns the project workspace. You are just writing scripts that instruct Vivado 鈥?do not create custom directories alongside the project and redirect Vivado outputs into them. Let Vivado manage its own house.

### Strict Rules

1. **One Vivado project = one directory.** A Vivado project created by `create_project` lives entirely inside its project directory: `<name>.xpr`, `<name>.srcs/`, `<name>.runs/`, `<name>.cache/`, `<name>.gen/`. Do NOT create sibling folders like `bitstreams/`, `reports/`, `hw_export/` at the project root level.

2. **Bitstream must be generated by `launch_runs -to_step write_bitstream`**, not by standalone `write_bitstream`. Reason: `write_hw_platform -include_bit` requires the `.bit` inside the impl run's standard directory. Writing bitstream to a custom path breaks hardware export.

3. **Reports, checkpoints, bitstreams, and run products stay where Vivado puts them.** Do not copy them into custom root-level folders. Use `<project>.runs/impl_1/*.bit` and the standard Vivado logs/reports for diagnosis.

4. **XDC constraints must be added to the project's `constrs_1` fileset.** Do not leave XDC files as orphans outside the project 鈥?Vivado needs them inside the project to use them during implementation.

5. **User-owned source files (HDL, XDC, C) may live wherever the user provides them.** Do not create `src/` automatically. Add existing files to the Vivado project via `add_files`.

6. **Automation scripts/log summaries live outside the Vivado project directory by default.** `run-rtl-workflow` writes generated Tcl/log/debug files under the system temp directory unless the user explicitly passes `--automation-dir`.

### Correct Layout
```text
<vivado_project_dir>/
|-- <name>.xpr
|-- <name>.srcs/
|-- <name>.runs/
|-- <name>.cache/
|-- <name>.gen/
`-- .Xil/

Generated automation files are outside this directory by default:
%TEMP%/vivado_assistant/<name>/run_workflow.tcl
%TEMP%/vivado_assistant/<name>/vivado_run.log
%TEMP%/vivado_assistant/<name>/debug_summary.txt
```

### Common Vivado 2020.2 Tcl Pitfalls

- **`PCW_USE_FCLK0` does not exist.** Setting `PCW_FPGA0_PERIPHERAL_FREQMHZ` to non-zero auto-enables FCLK0.
- **`M_AXI_GP0_ACLK` must be explicitly connected** to `FCLK_CLK0` after `apply_bd_automation`, otherwise `validate_bd_design` fails.
- **`proc_sys_reset/dcm_locked` must be driven.** Use `xlconstant` (CONST_VAL=1) to tie it high when FCLK comes directly from PS.
- **Configure PS properties BEFORE `apply_bd_automation`**, connect `M_AXI_GP0_ACLK` AFTER.
- **XSA export must be content-verified.** `run-rtl-workflow --export-hw --run` inspects the generated XSA as a zip archive and fails if `.bit` or `.hwh` is missing. If a user re-exports hardware manually and Vitis starts working, treat that as a missing/invalid hardware-export artifact until the XSA inspection proves otherwise.
- **Zynq board projects need `board_part` when available.** If Vitis can create a platform but ELF download/run fails with PS debug/APB access errors, compare the `.xpr` against a known-good project and check whether `BoardPart` is empty. Rebuild with `--board-part <vendor>:<board>:part0:<version>` instead of only `--part`.

## Supported Commands

### 0. Basic Vivado Automation Commands

Use these commands for the normal FPGA flow:

| User intent | CLI command |
| --- | --- |
| Full ordered RTL/BD/build flow | `run-rtl-workflow --run` |
| Validate Vivado paths/environment | `doctor` |
| Create a project | `create-project` |
| Create a baseline Zynq BD | `create-bd` |
| Generate IP/BD output products | `generate-output-products` |
| Run simulation | `run-simulation` |
| Run synthesis | `run-synthesis` |
| Run implementation | `run-implementation` |
| Generate bitstream | `generate-bitstream` |
| Open hardware / program device | `program-device` or `generate-bitstream --ask-program-device` |
| Create/edit catalog IP | `ip --ip-action create` / `ip --ip-action edit` |
| Convert Vivado versions | `migrate-project` |
| Patch Vitis BSP Makefile | `patch-vitis-makefile` |
| Register board XDC | `register-board-xdc` |

### Board XDC Handling

Do not scatter original board XDC files into random generated folders. When the user provides a board XDC, register its original path in config:

```bash
python scripts/vivado_assistant.py register-board-xdc \
  --board-name my-board \
  --xdc "<path-to-your-board.xdc>" \
  --part xc7z020clg400-1
```

Later, if the user cannot find the XDC, list registered files:

```bash
python scripts/vivado_assistant.py list-board-xdc
```

For project creation, use `--board-name <name>` to add the registered XDC directly. If the design needs a modified subset of constraints, create a project-local derived XDC and keep the original registered path intact.

### Programming RTL PL Bitstreams

For a pure RTL PL project, after bitstream generation succeeds, ask one short question only:

`Bitstream generated. Program the board now?`

If the user agrees, run `program-device` directly. Do not paste long Vivado logs unless programming fails and the failure text is needed.

```bash
python scripts/vivado_assistant.py generate-bitstream \
  --project <project.xpr> \
  --name <name> \
  --out <automation_dir> \
  --run \
  --ask-program-device
```

For non-interactive programming:

```bash
python scripts/vivado_assistant.py program-device \
  --bit-file <design.bit> \
  --out <automation_dir> \
  --run
```

When programming Zynq boards, do not blindly select the first JTAG device because it may be `arm_dap_0`. The generated `program-device` Tcl selects devices whose `PROGRAM.IS_SUPPORTED` property is true, then programs the first supported FPGA device such as `xc7z020_1`.

Successful programming should be reported briefly, for example:

`Programming OK: <bit_file>`

Examples:

```bash
python scripts/vivado_assistant.py create-project \
  --name my_fpga_design \
  --part xc7z020clg400-1 \
  --project-dir ./vivado_project \
  --src-dir ./src/hdl \
  --sim-dir ./src/tb \
  --xdc-dir ./src/xdc \
  --top top \
  --out ./automation \
  --run
```

```bash
python scripts/vivado_assistant.py create-bd \
  --project ./vivado_project/my_fpga_design.xpr \
  --bd-name design_1 \
  --gpio-width 8 \
  --out ./automation \
  --run
```

```bash
python scripts/vivado_assistant.py ip \
  --ip-action create \
  --project ./vivado_project/my_fpga_design.xpr \
  --ip-name axi_gpio \
  --module-name axi_gpio_0 \
  --version 2.0 \
  --config CONFIG.C_GPIO_WIDTH {8} CONFIG.C_ALL_OUTPUTS {1} \
  --out ./automation \
  --run
```

```bash
python scripts/vivado_assistant.py run-simulation \
  --project ./vivado_project/my_fpga_design.xpr \
  --top tb_top \
  --runtime 10us \
  --out ./automation \
  --run
```

```bash
python scripts/vivado_assistant.py run-synthesis --project ./vivado_project/my_fpga_design.xpr --out ./automation --run
python scripts/vivado_assistant.py run-implementation --project ./vivado_project/my_fpga_design.xpr --out ./automation --run
python scripts/vivado_assistant.py generate-bitstream --project ./vivado_project/my_fpga_design.xpr --name my_fpga_design --out ./automation --run
```

### Natural-Language File Editing

For requests like "modify this Verilog", "add a signal to the testbench", or "change XDC pins", the assistant should:

1. Read the target HDL/testbench/XDC files.
2. Apply precise file edits directly.
3. Run or generate the relevant automation command afterward:
   - HDL/XDC design changes: `run-synthesis`
   - testbench changes: `run-simulation`
   - BD/IP changes: `generate-output-products`, then synthesis

The Python CLI intentionally does not guess semantic HDL edits from raw natural language by itself. The agent performs the code edit; the CLI performs Vivado automation around that edit.

### PS/Vitis C Source Output

For PS-side Vitis applications, do not promise full Vitis GUI automation. Vitis workspace state, Eclipse background services, launch configurations, and JTAG target state are too environment-sensitive for reliable default automation.

Instead, generate the requested C/C++ source file and tell the user where it should be placed:

```text
<App_workspace>/<app_name>/src/
```

For example:

```text
<App_workspace>/<app_name>/src/main.c
```

If the exact Vitis app source directory is known and writable, create the file there. If not, create the C file in the generated project workspace and instruct the user to copy it into the Vitis app `src` directory.

Default PS-side flow:

1. Generate the C/C++ file.
2. Tell the user to place it under `<App_workspace>/<app_name>/src`.
3. Tell the user to run `Build Application` in Vitis.
4. Tell the user to run `Run As -> standalone_debug_attach_target_program_and_run`.

Do not run Vitis `app build`, Eclipse headless build, or Run As automation by default. Only do so if the user explicitly asks to experiment with Vitis automation and accepts that it may depend on local GUI/JTAG state.

Exception: the `patch-vitis-makefile` command remains supported and should be used for the Vivado/Vitis 2021.1 BSP Makefile bug before the user builds the app.

If Vitis reports `CDT Project already configured`, `Failed to create application project`, or shows an existing project from `getProjects`, first suspect Vitis workspace metadata/name collision. Use a new empty Vitis workspace or remove/rename the existing application/platform project in Vitis. Do not immediately blame the XSA unless the XSA content inspection shows missing `.bit` or `.hwh`.

### 1. Migrate a Vivado Project Across Versions

Use this when the user says things like:

- "I have a Vivado 2020.2 project and want to switch to 2021.1"
- "Convert this 2020.2 project to 2021.1"
- "Do not copy the whole Vivado project; rebuild a clean project"
- "Export BD Tcl in the old version and recreate BD in the new version"

Command:

```bash
python scripts/vivado_assistant.py migrate-project \
  --project <old_xpr_or_project_dir> \
  --out <migration_work_dir> \
  --new-project-dir <new_clean_project_dir> \
  --source-version <configured_source_version> \
  --target-version <configured_target_version>
```

The user can also pass exact executables instead of configured versions with `--source-vivado` and `--target-vivado`.

The command writes:

- `migration_manifest.json`
- `01_export_bd_from_source_vivado.tcl`
- `02_rebuild_project_in_target_vivado.tcl`
- `bd_tcl/` output directory

Safe migration flow:

1. Run `01_export_bd_from_source_vivado.tcl` with the source Vivado version.
2. Run `02_rebuild_project_in_target_vivado.tcl` with the target Vivado version.
3. Rebuild from HDL/XDC/XCI and exported BD Tcl.
4. Do not copy `.xpr`, `.runs`, `.cache`, `.gen`, `.ip_user_files`, `.sim`, or `.hw`.

If the user explicitly wants execution and Vivado is available, pass `--run-export` and/or `--run-rebuild`.

### 2. Patch Vitis 2021.1 BSP Makefile Bug

Use this when the user says:

- "Vitis 2021.1 app Makefile has a bug"
- "Patch zynq_fsbl_bsp Makefile before build"
- "Replace the BSP Makefile under an app workspace"

Timing rule:

1. Let the user open Vitis and choose the workspace.
2. Let the user create the application/platform so Vitis generates the BSP folders and Makefiles.
3. Patch the BSP Makefile after application creation and before the user clicks `Build Application`.

Do not run this patch before the Vitis application exists. If the workspace has no generated BSP Makefile yet, tell the user to create the application first.

Command:

```bash
python scripts/vivado_assistant.py patch-vitis-makefile \
  --workspace <vitis_app_workspace> \
  --sequential-drivers driver1,driver2 \
  --jobs 30
```

The command searches inside the completed Vitis workspace for generated BSP root `Makefile` files, creates `Makefile.bak` if missing, and writes the known-good 2021.1-compatible Makefile.

For checking first:

```bash
python scripts/vivado_assistant.py patch-vitis-makefile \
  --workspace <vitis_app_workspace> \
  --dry-run
```

## Version Migration Behavior

The migration command must treat `.bd` as version-sensitive. It does not copy old BD implementation products into the new project. It opens the old project in the old Vivado, exports each BD as Tcl, and then sources those Tcl files in the target Vivado to recreate clean `.bd` files.

Basic source files are treated as user-owned and reusable:

- HDL: `.v`, `.sv`, `.vhd`, `.vhdl`
- Constraints: `.xdc`
- IP configuration: `.xci`
- App/source support: `.c`, `.cpp`, `.h`, `.hpp`, `.ld`, `.s`, `.S`

Generated Vivado artifacts are ignored:

- `.runs/`
- `.cache/`
- `.gen/`
- `.hw/`
- `.ip_user_files/`
- `.sim/`
- `ipcache/`
- `.Xil/`

## Assistant Workflow

Before running scripts:

1. Locate the old `.xpr` or project directory.
2. Ask for Vivado executable paths only if they cannot be inferred and execution is requested.
3. Use a separate migration workspace.
4. Preserve the original project untouched.
5. Explain that BD migration requires the source Vivado version to export Tcl.

After running migration:

1. Check `ip_status_before_upgrade.rpt` and `ip_status_after_upgrade.rpt` if generated.
2. Run synthesis only after BD validation and wrapper generation succeed.
3. If Vitis 2021.1 BSP build is involved, patch the Makefile before build.

## Failure Handling

If BD Tcl recreation fails in the target Vivado:

1. Check missing IP repositories first.
2. Check board part/preset differences.
3. Check IP upgrade status.
4. Avoid copying old `.bd` or `.gen` artifacts into the new project as a workaround.

If Vitis Makefile patching finds multiple BSP Makefiles, report all matched paths and patch only when the user asked for workspace-wide repair or provided a specific `--makefile`.

