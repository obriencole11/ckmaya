from maya import mel, cmds

def addSkyrimMenu():
    # Don't create menu in batch mode
    if cmds.about(batch=True):
        return

    # Delete the menu if it exists
    if cmds.menu("ckmayaMenu", exists=True):
        cmds.deleteUI("ckmayaMenu")

    if not cmds.menu("ckmayaMenu", exists=True):
        parent_menu = cmds.menu(
            "ckmayaMenu",
            label='Skyrim',
            parent=mel.eval("$retvalue = $gMainWindow;"),
        )

        cmds.menuItem(label='Project', divider=True, parent=parent_menu)

        # Add Export Manager
        command = 'from ckmaya.ui import export_manager;export_manager.ExportManager.load()'
        cmds.menuItem(
            label="Project Manager",
            parent=parent_menu,
            command=command
        )

        cmds.menuItem(label='Props', divider=True, parent=parent_menu)

        # Add Nif Command
        command = 'from ckmaya.ui import commands;commands.importMesh()'
        cmds.menuItem(
            label="Import Mesh",
            parent=parent_menu,
            command=command
        )
        command = 'from ckmaya.ui import commands;commands.importTextures()'
        cmds.menuItem(
            label="Import Textures",
            parent=parent_menu,
            command=command
        )

        cmds.menuItem(label='Animation', divider=True, parent=parent_menu)

        # Add Export Command
        command = 'from ckmaya.core import ckcore;ckcore.exportAnimation()'
        cmds.menuItem(
            label="Export Animation",
            parent=parent_menu,
            command=command
        )
