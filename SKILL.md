---
name: vivado-assistant-automation
description: "Script-first Vivado/Vitis automation for project migration between Vivado 2020.2 and 2021.1, clean project rebuilds from user sources, BD Tcl export/recreate flows, and Vitis 2021.1 BSP Makefile patching."
---

# Vivado Assistant Automation

You are a script-first Vivado/Vitis automation assistant. Prefer running or generating scripts from `scripts/vivado_assistant.py` over writing ad hoc Tcl snippets in chat.

## Core Rule

When the user asks for Vivado project creation, version migration, BD recreation, IP output generation, synthesis, implementation, bitstream, or Vitis BSP Makefile repair, first identify whether an existing command in `scripts/vivado_assistant.py` can do the job. If yes, use that command and only generate extra Tcl when the CLI emits a migration workspace.

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

This writes `vivado_assistant_config.json` in the current working directory by default. The user may choose the default executable with `--default-version 2020.2` or `--default-version 2021.1`.

After initialization:

- Normal project/build commands use the configured default Vivado. If only one Vivado is configured, they use that one.
- `migrate-project` should use the source and target versions chosen by the user, for example `--source-version 2020.2 --target-version 2021.1`.
- A specific command may still override the executable with `--vivado`, `--source-vivado`, or `--target-vivado`.

## Supported Commands

### 0. Basic Vivado Automation Commands

Use these commands for the normal FPGA flow:

| User intent | CLI command |
| --- | --- |
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
