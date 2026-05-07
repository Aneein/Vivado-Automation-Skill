# Vivado Assistant Automation

This is a script-first redesign of the Vivado assistant. The old version was mainly a skill template and Tcl snippet library. This version gives the agent concrete automation commands to run.

## What It Solves

- Automates the normal Vivado project flow from scripts rather than chat-only templates.
- Creates projects, block designs, IP, output products, simulations, synthesis, implementation, and bitstreams.
- Rebuild a Vivado 2020.2 project as a clean Vivado 2021.1 project.
- Avoid copying generated Vivado folders that often break after version changes.
- Export old `.bd` files to Tcl with the source Vivado version and recreate clean BD files in the target Vivado version.
- Preserve user-owned HDL/XDC/XCI/app files.
- Patch the known Vitis 2021.1 BSP Makefile issue before app build.

## Directory Layout

```text
vivado-assistant-automation/
  SKILL.md
  README.md
  scripts/
    vivado_assistant.py
  docs/
    version_migration.md
```

## First-Time Initialization

Before running Vivado automation, save the Vivado executable path or paths the user has. One Vivado installation is enough for normal project creation/build flows.

```powershell
python .\scripts\vivado_assistant.py init `
  --vivado-2020-2 "C:\Xilinx\Vivado\2020.2\bin\vivado.bat" `
  --vivado-2021-1 "C:\Xilinx\Vivado\2021.1\bin\vivado.bat" `
  --default-version 2021.1
```

For a single Vivado installation:

```powershell
python .\scripts\vivado_assistant.py init `
  --vivado-2021-1 "C:\Xilinx\Vivado\2021.1\bin\vivado.bat"
```

This creates `vivado_assistant_config.json` in the current directory. Normal commands use the configured default Vivado, or the only configured Vivado when there is just one.

## Claude Code Guard

This repository includes project-level Claude Code guardrails under `.claude/`.

What it does:

- Injects hard workflow instructions when a Vivado/Vitis prompt is submitted.
- Blocks ad-hoc `vivado -mode batch -source some_random.tcl` execution.
- Blocks attempts to execute Windows Vivado/Vitis from Linux/remote Claude Code because automation must run where it can inspect logs directly.
- Requires full workflows to execute with `python scripts/vivado_assistant.py run-rtl-workflow ... --run`; plan-only generation is only for explicit dry planning.

Recommended Claude Code flow:

```powershell
/vivado-workflow create a PYNQ-Z2 project with a Zynq AXI GPIO BD and bitstream
```

Run Claude Code from the same Windows environment that owns Vivado for full automation. The Python CLI should call Vivado directly and inspect logs; do not rely on a user-run batch file as the main path.

## Basic Vivado Flow Commands

### Recommended Hard Workflow

Use this for normal project work instead of asking an agent to hand-write several Tcl files. It fixes the order:

PL RTL flow:

1. create Vivado project
2. add Verilog/SystemVerilog/VHDL sources
3. add XDC to `constrs_1`
4. run synthesis
5. run implementation to bitstream
6. export hardware with included bitstream when requested

BD flow:

1. create Vivado project
2. create BD, add IP, connect, assign addresses
3. validate BD
4. generate output products
5. generate HDL wrapper
6. add XDC to `constrs_1`
7. run synthesis
8. run implementation to bitstream
9. export hardware with included bitstream when requested

```powershell
python .\scripts\vivado_assistant.py doctor `
  --vivado-candidate "G:\Xilinx\Vivado\2020.2\bin\unwrapped\win64.o"
```

```powershell
python .\scripts\vivado_assistant.py run-rtl-workflow `
  --name my_design `
  --root C:\work\my_design `
  --part xc7z020clg400-1 `
  --top top `
  --vivado-version 2020.2 `
  --run
```

For a Zynq PS + AXI GPIO BD:

```powershell
python .\scripts\vivado_assistant.py run-rtl-workflow `
  --name ps_gpio `
  --root C:\work\ps_gpio `
  --part xc7z020clg400-1 `
  --board-part tul.com.tw:pynq-z2:part0:1.0 `
  --bd-mode zynq-axi-gpio `
  --gpio-direction input `
  --gpio-width 1 `
  --gpio-port-name btn0 `
  --export-hw `
  --vivado-version 2020.2 `
  --run
```

The command lets Vivado create and own the project directory. Generated automation files are outside the Vivado project by default, under `%TEMP%\vivado_assistant\<name>\`: `workflow_manifest.json`, `run_workflow.tcl`, `vivado_run.log`, `last_phase.txt`, `debug_summary.txt`, and `stage_logs\*.log`. Do not ask the user to run Tcl or bat files manually.

### Single-Stage Commands

Register a board XDC original path:

```powershell
python .\scripts\vivado_assistant.py register-board-xdc `
  --board-name my-board `
  --xdc <path-to-your-board.xdc> `
  --part xc7z020clg400-1
```

List registered board XDC files:

```powershell
python .\scripts\vivado_assistant.py list-board-xdc
```

Create a project:

```powershell
python .\scripts\vivado_assistant.py create-project `
  --name my_fpga_design `
  --part xc7z020clg400-1 `
  --project-dir C:\work\vivado_project `
  --src-dir C:\work\src\hdl `
  --sim-dir C:\work\src\tb `
  --xdc-dir C:\work\src\xdc `
  --board-name my-board `
  --top top `
  --out C:\work\automation `
  --run
```

Create a baseline Zynq block design for diagnosis only. Prefer `run-rtl-workflow --run` for normal full builds:

```powershell
python .\scripts\vivado_assistant.py create-bd `
  --project C:\work\vivado_project\my_fpga_design.xpr `
  --bd-name design_1 `
  --gpio-width 8 `
  --out C:\work\automation `
  --run
```

Create or edit IP:

```powershell
python .\scripts\vivado_assistant.py ip `
  --ip-action create `
  --project C:\work\vivado_project\my_fpga_design.xpr `
  --ip-name axi_gpio `
  --module-name axi_gpio_0 `
  --version 2.0 `
  --config CONFIG.C_GPIO_WIDTH {8} CONFIG.C_ALL_OUTPUTS {1} `
  --out C:\work\automation `
  --run
```

Generate output products:

```powershell
python .\scripts\vivado_assistant.py generate-output-products `
  --project C:\work\vivado_project\my_fpga_design.xpr `
  --out C:\work\automation `
  --run
```

Run simulation/synthesis/implementation/bitstream:

```powershell
python .\scripts\vivado_assistant.py run-simulation --project C:\work\vivado_project\my_fpga_design.xpr --top tb_top --runtime 10us --out C:\work\automation --run
python .\scripts\vivado_assistant.py run-synthesis --project C:\work\vivado_project\my_fpga_design.xpr --out C:\work\automation --run
python .\scripts\vivado_assistant.py run-implementation --project C:\work\vivado_project\my_fpga_design.xpr --out C:\work\automation --run
python .\scripts\vivado_assistant.py generate-bitstream --project C:\work\vivado_project\my_fpga_design.xpr --name my_fpga_design --out C:\work\automation --run
```

`generate-bitstream` uses `launch_runs impl_1 -to_step write_bitstream` and reports the `.bit` from Vivado's standard `<project>.runs\impl_1` directory. It does not write extra bit/bin files into a custom `bitstreams` folder.

For RTL PL projects, ask after bitstream whether to open hardware and program the board:

```powershell
python .\scripts\vivado_assistant.py generate-bitstream `
  --project C:\work\vivado_project\my_fpga_design.xpr `
  --name my_fpga_design `
  --out C:\work\automation `
  --run `
  --ask-program-device
```

The automation skips non-programmable JTAG devices such as `arm_dap_0` and programs the first device whose `PROGRAM.IS_SUPPORTED` property is true.

Program an existing bitstream directly:

```powershell
python .\scripts\vivado_assistant.py program-device `
  --bit-file C:\work\bitstreams\my_fpga_design.bit `
  --out C:\work\automation `
  --run
```

For natural-language HDL, testbench, or XDC edits, the agent edits the files directly and then invokes the relevant flow command above.

## PS/Vitis C Source Rule

For PS-side Vitis applications, this skill does not default to automating Vitis GUI build/run actions. Vitis workspace registration, Eclipse services, launch configs, and JTAG state are too environment-sensitive.

Generate the requested C/C++ file and place it in the Vitis app source directory when the path is known:

```text
<App_workspace>\<app_name>\src
```

Example:

```text
<App_workspace>\<app_name>\src\main.c
```

If the exact app `src` directory is not known, generate the C file in the project output folder and tell the user to copy it into the app `src` directory.

User-side Vitis flow:

1. Put the generated C/C++ file into `<App_workspace>\<app_name>\src`.
2. Click `Build Application`.
3. Launch with PS initialization enabled so Vitis runs `ps7_init` and `ps7_post_config` before downloading the ELF. Avoid attach-only launches unless the PS has already been initialized; otherwise downloads to DDR, commonly `0x100000`, can fail with `APB Memory access port is disabled`.

The only Vitis automation kept by default is the Vivado/Vitis 2021.1 BSP Makefile patch before build.

## Command: Migrate Vivado Project

Run the migration from the Python command so the tool selects the configured Vivado versions and can validate paths/host execution:

```powershell
python .\scripts\vivado_assistant.py migrate-project `
  --project C:\old_project\old_project.xpr `
  --out C:\migration_work `
  --new-project-dir C:\new_2021_1_project `
  --source-version 2020.2 `
  --target-version 2021.1 `
  --run-export `
  --run-rebuild
```

The source and target versions are chosen by the user. If `--source-version` or `--target-version` is provided, that exact version must be configured by `init`; the tool will not fall back to the default Vivado. If the user wants a custom executable for this one migration, add `--source-vivado` and `--target-vivado`; these paths are normalized and validated like `init` paths.

`migrate-project --run-export --run-rebuild` rebuilds the clean target Vivado project only. It does not run synthesis, implementation, bitstream, or XSA export. After migration succeeds, run a fresh full build flow or open the migrated `.xpr` and build manually.

For advanced/debug use only, generate migration files without running them:

```powershell
python .\scripts\vivado_assistant.py migrate-project `
  --project C:\old_project\old_project.xpr `
  --out C:\migration_work `
  --new-project-dir C:\new_2021_1_project `
  --source-version 2020.2 `
  --target-version 2021.1
```

Manual Vivado `-mode batch -source` execution of the emitted Tcl is a debug fallback, not the normal agent path.

```powershell
python .\scripts\vivado_assistant.py migrate-project `
  --project C:\old_project\old_project.xpr `
  --out C:\migration_work `
  --new-project-dir C:\new_2021_1_project `
  --source-version 2020.2 `
  --target-version 2021.1 `
  --run-export `
  --run-rebuild
```

## Command: Patch Vitis 2021.1 BSP Makefile

Run this only after the user has opened Vitis, selected the workspace, and created the application/platform. The generated BSP Makefile must already exist. Patch before clicking `Build Application`.

Check matched BSP root Makefiles first. If the workspace contains multiple platforms/apps, inspect this list before patching:

```powershell
python .\scripts\vivado_assistant.py patch-vitis-makefile `
  --workspace <App_workspace> `
  --dry-run
```

Patch all matched BSP root Makefiles:

```powershell
python .\scripts\vivado_assistant.py patch-vitis-makefile `
  --workspace <App_workspace> `
  --jobs 30
```

Patch one exact Makefile:

```powershell
python .\scripts\vivado_assistant.py patch-vitis-makefile `
  --workspace <App_workspace> `
  --makefile <App_workspace>\platform_name\zynq_fsbl\zynq_fsbl_bsp\Makefile
```

`--sequential-drivers` is optional. Use it only when some BSP drivers must be built before the parallel driver build step. Values are driver folder names under `ps7_cortexa9_0\libsrc\`, not full paths, for example:

```powershell
python .\scripts\vivado_assistant.py patch-vitis-makefile `
  --workspace <App_workspace> `
  --sequential-drivers xilffs_v4_4,xilpm_v2_9 `
  --jobs 30
```

Each name must correspond to:

```text
<workspace>\<platform>\<bsp>\ps7_cortexa9_0\libsrc\<driver_name>\src\Makefile
```

If you do not know which drivers need sequential builds, omit `--sequential-drivers`.

The script creates `Makefile.bak` the first time it patches a file.

## Migration Principle

Do not migrate by copying a whole Vivado project directory. Copying `.xpr`, `.runs`, `.cache`, `.gen`, `.ip_user_files`, `.sim`, `.hw`, or `ipcache` across Vivado versions commonly causes stale IP, BD, and generated product errors.

The intended flow is:

1. Open the old project with the old Vivado.
2. Export BD Tcl.
3. Create a new project with the target Vivado.
4. Add user-owned HDL/XDC/XCI files.
5. Source the exported BD Tcl.
6. Generate wrappers and output products.
7. Upgrade IP if needed.
8. Build synthesis/implementation/bitstream from the clean target project as a separate step.

