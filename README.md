# Guidrawer

Guidrawer is a utility tool for the rigging framework [mGear](https://github.com/mgear-dev/mgear). It is designed to assist "custom" guide drawing during rigging operations on Maya.

### Draw guide at selected position
control_01
![bf441815959d5b3d35d73c9be94f0be4](https://github.com/zebraed/guidrawer_dev/assets/30438415/65032504-d8ad-4455-a9b7-7ef54795ec40)

chain_spring_01
![046eab1354ef8295dccb37dcfc44ca07](https://github.com/zebraed/guidrawer_dev/assets/30438415/fb97e16c-70a9-4227-a1da-c3efab24df8a)

## Installation

To install Guidrawer, follow these steps:

1. Clone the repository: `$ git clone https://github.com/zebraed/guidrawer.git`
2. Navigate to the project directory: `$ cd guidrawer`
3. Place the "guidrawer" directory under the PYTHONPATH of Maya.

## Usage

To use Guidrawer as GUI on Maya, follow these steps:

1. Import the module: `import guidrawer.ui`
2. Call the show functions: `guidrawer.showUI()` or `guidrawer.ui.showUI()`


Any component type registered in mGear (classic / EPIC / custom via
`MGEAR_SHIFTER_COMPONENT_PATH`) can be drawn without writing extra code.

To customize the drawing process, add a preset module under
`guidrawer/component/`. A preset is a plain module (no class required)
that defines:

```python
NAME = "my_preset"            # display name in UI
COMPONENT_TYPE = "control_01" # mGear component type to draw
ORDER = 0                     # optional, sort order in UI

def draw_guide(name, side, idx, parent_root, **opt):
    ...
```

See `guidrawer/component/two_control_01.py` for a working example.
