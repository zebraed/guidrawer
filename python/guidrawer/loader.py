"""Load custom preset modules under component/.

Preset module convention (no class required):
    NAME (str): Preset name shown in the UI
    COMPONENT_TYPE (str): mGear component type used for drawing
    ORDER (int, optional): Display order. Defaults to 0
    draw_guide(name, side, idx, parent_root, **opt): Draw function
"""
import importlib
import os
import traceback

PRESET_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), "component"
)


def _is_preset_module(mod):
    return hasattr(mod, "NAME") and callable(getattr(mod, "draw_guide", None))


def load_presets(preset_path=None):
    """Load preset modules and return a dict keyed by display name.

    Returns:
        dict[str, module]: {preset name: module}
    """
    if not preset_path:
        preset_path = PRESET_PATH

    mods = []
    for file_name in sorted(os.listdir(preset_path)):
        if not file_name.endswith(".py"):
            continue
        mod_name = os.path.splitext(file_name)[0]
        if mod_name == "__init__":
            continue
        try:
            mod = importlib.import_module(f"guidrawer.component.{mod_name}")
            importlib.reload(mod)
        except Exception:
            print(f"Can not import preset module. : {mod_name}")
            print(traceback.format_exc())
            continue
        if _is_preset_module(mod):
            mods.append(mod)

    mods.sort(key=lambda m: getattr(m, "ORDER", 0))
    return {mod.NAME: mod for mod in mods}
