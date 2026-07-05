# Changelog

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