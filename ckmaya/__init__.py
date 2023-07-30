import os
import sys
from . import core, ui
from .ui import menu


def startup():
    """
    Loads ckmaya menu and adds paths.
    """

    # Add python paths
    sys.path.append(os.path.join(os.path.dirname(__file__), 'thirdparty'))
    sys.path.append(os.path.join(os.path.dirname(__file__), 'thirdparty', 'fbxsdk'))

    # Add menus
    menu.addSkyrimMenu()

    
def _unload(pkg):
    """
    Unloads all imports from the given package.

    Args:
        pkg(module): A python module to unload.
    """
    pkg_dir = os.path.abspath(os.path.dirname(pkg.__file__))

    def _is_part_of_pkg(module_):
        mod_path = getattr(module_, "__file__", os.sep)
        if mod_path is None:
            return False
        mod_dir = os.path.abspath(os.path.dirname(mod_path))
        return mod_dir.startswith(pkg_dir)

    to_unload = [name for name, module in sys.modules.items() if _is_part_of_pkg(module)]
    for name in to_unload:
        sys.modules.pop(name)


def unload():
    """
    Unloads all ckmaya modules.
    """

    # Remove callback
    menu.removeCallback()

    # Unload modules
    _unload(core)
    _unload(ui)

    # Add callback
    menu.addCallback()

