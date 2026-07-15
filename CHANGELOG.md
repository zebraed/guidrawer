# Changelog

## [2026-07-16] - Version 3.1.2

- Vanilla Build: build selected guide component subtree; Settings opens Guide Top when nothing is selected

## [2026-07-14] - Version 3.1.1

- Full Build: skip restoring guide custom-step flags when Post custom steps delete the guide
- Full Build: suppress mGear script editor log by default; right-click to build with log

## [2026-07-12] - Version 3.1.0

- Draw without selection: place at guide model default, at parent-space origin when parent is set, or under selected guide when parent field is empty
- When parent field is empty, use selected guide (or its component root) as draw parent
- Added **Auto Side Label**: optional L/R/C from parent world X or placement world X (X=0 → C); index resolved per draw side
- UI settings persisted via Maya `optionVar` (JSON); removed `QSettings` / `.ini` — base name, parent guide, side, index, component type, Auto Side state, window geometry
- Added **Controller Shape Tools**: Sel Shape, Scale Shape (±0.1 in object space), Edit (object/component mode toggle), Replace / Mirror Shape (rigbits), Extr. Ctrl moved from Guide Tools
- **Extr. Ctrl**: extract all rig controls when nothing is selected or when rig root is selected (`isCtl` under `is_rig`)
- Added **Align Crv** (Placement Tools): distribute guide placement locs along a non-guide NURBS curve; chain components use chain locs; curve vs guide distinguished by component membership
- Guide Tools: **Update Component**, **Guide Symmetry**, **Component Type Lister**, **Chain Utils**
- Added **Unbuild**

## [2026-07-05] - Version 3.0.0

- Added guide alignment tools (`guide_align`): Fit/Mid Pos, Fit Nearest (mesh / nurbsCurve / nurbsSurface), Align/Mid/Nearest Rot, Aim X/Y/Z, and 90° axis rotation
- Added Solo Move toggle to sync Preserve Children on Move / Rotate / Scale manipulators
- Added guide operations via `shifter_bridge`: Duplicate, Mirror, Delete (keep children), Extract Controls, component Settings
- Added Pre Settings workflow: open settings before draw, cache values, and apply on creation; Reset Settings button
- Added Vanilla Build and Full Build (pre/post custom steps when present)

## [2026-07-02] - Version 2.0.0

- Refactored mGear integration via `shifter_bridge`; any registered component type can be drawn without custom code
- Replaced class-based components with function-based preset modules in `component/`
- Updated UI: component list ordering (mGear types, then presets) and index SpinBox using mGear `setIndex`
- Python 3 support; removed `base.py` and legacy `control_01` / `chain_spring_01` classes
- PySide 6 support

## [2024-03-31] - Version 1.0.0

- Initial release: GUI and script API for drawing mGear guide components at the selected position

## [2022-12-10] - Version 0.0.1

- Implementation test