# Vivado 2020.2 to 2021.1 Clean Migration Design

## Problem

Vivado projects contain many generated artifacts. Directly copying a 2020.2 project folder into 2021.1 can carry stale generated BD products, IP cache entries, run metadata, and simulator/build state. These often produce errors that are unrelated to the real user source files.

## Clean Rebuild Strategy

The automation uses the source Vivado version only for export and the target Vivado version only for rebuild.

### Source Vivado Step

Run `01_export_bd_from_source_vivado.tcl` in Vivado 2020.2:

- Open the original `.xpr`.
- Find all block design files.
- Open and validate each BD.
- Export each BD to Tcl.
- Write source IP status report.
- Close the project.

### Target Vivado Step

Run `02_rebuild_project_in_target_vivado.tcl` in Vivado 2021.1:

- Create a new project.
- Add HDL and XDC files.
- Add XCI files when present.
- Source exported BD Tcl files to recreate `.bd`.
- Validate and save BD.
- Generate HDL wrappers.
- Upgrade IP and regenerate output products.
- Save the new clean project.

## Included File Types

- HDL: `.v`, `.sv`, `.vhd`, `.vhdl`
- Constraints: `.xdc`
- IP config: `.xci`
- App/source support: `.c`, `.cc`, `.cpp`, `.h`, `.hpp`, `.ld`, `.s`, `.S`

## Excluded Generated Paths

- `.Xil`
- `.cache`
- `.gen`
- `.hw`
- `.ip_user_files`
- `.runs`
- `.sim`
- `ipcache`
- `xsim.dir`

## Common Follow-Up Fixes

- Add missing custom IP repositories with `set_property ip_repo_paths`.
- Reapply board part settings if the old project depended on a board preset.
- Review `ip_status_before_upgrade.rpt` and `ip_status_after_upgrade.rpt`.
- Regenerate Vitis platform/app only after hardware export succeeds.
- Patch Vitis 2021.1 BSP Makefile before building affected apps.
