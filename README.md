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
2. Call the show functions: `guidrawer.ui.show()`


To use Guidrawer in your scripts on Maya, follow these steps:

1. Import the module: `import guidrawer.drawer as drawer`
2. Initialize the Guidrawer object: `gd = drawer.Guidrawer()`
3. Load Component:`gd.load_component(componentType=COMPONENT_NAME)`
4. Call the drawing functions with args: `gd.create_guide(name, side, parentRoot, idx, **opt)`
