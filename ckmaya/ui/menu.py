import os
import json
import tempfile
import maya.api.OpenMaya as om2
from maya import mel, cmds
from ..core import ckproject
from .core import getDirectoryDialog, getNameDialog


SKYRIM_MENU = "ckmayaMenu"
SKYRIM_RECENT_PROJECT_MENU = "ckmayaRecentProjectMenu"


def createProject(directory=None, name=None):
    """
    Creates a project with the given name.

    Args:
        directory(str): A directory path.
        name(str): A project name.

    Returns:
        str: The project path.
    """
    directory = directory or getDirectoryDialog(ckproject.getProject() or '')
    name = name or getNameDialog()
    ckproject.createProject(directory, name)
    return directory


def setProject(directory=None):
    """
    Opens a dialog prompting the user to select a project.
    """
    directory = directory or getDirectoryDialog(ckproject.getProject() or '')

    # Check if the project is valid
    if not ckproject.isProject(directory):
        setProjectResult = 'Select another location'
        newProjectResult = 'Create default workspace'
        cancelResult = 'Cancel'
        result = cmds.confirmDialog(
            title='Invalid Project Dialog',
            message=f'This location "{directory}" is not a valid Skyrim project.\n\nPlease select on of the following options:',
            button=[setProjectResult, newProjectResult, cancelResult]
        )
        if result == setProjectResult:
            return setProject()
        elif result == newProjectResult:
            createProject(directory=directory)
        else:
            return

    # Set the project
    ckproject.setProject(directory)


def updateRecentProjects():
    """
    Updates the recent project menu with Maya's recent projects.
    """
    if not cmds.menu(SKYRIM_RECENT_PROJECT_MENU, exists=True):
        return
    if not cmds.optionVar(exists='RecentProjectsList'):
        return

    # If the amount hasn't changed, return early
    projects = ckproject.getRecentProjects()
    currentSize = len(list(cmds.menu(SKYRIM_RECENT_PROJECT_MENU, itemArray=True, q=True) or []))
    if currentSize == len(projects):
        return

    # Add items to the menu
    cmds.menu(SKYRIM_RECENT_PROJECT_MENU, deleteAllItems=True, e=True)
    for project in reversed(projects):
        cmds.menuItem(
            label=project,
            command=f'from ckmaya.ui import menu;menu.setProject("{project}")',
            parent=SKYRIM_RECENT_PROJECT_MENU
        )


MENU_CALLBACK = None


def addCallback():
    """
    Adds the menu callback.
    """
    removeCallback()
    global MENU_CALLBACK
    MENU_CALLBACK = om2.MEventMessage.addEventCallback('workspaceChanged', updateSkyrimMenu)


def removeCallback():
    """
    Removes the menu callback.
    """
    global MENU_CALLBACK
    if MENU_CALLBACK is not None:
        om2.MMessage.removeCallback(MENU_CALLBACK)
        MENU_CALLBACK = None


def addSkyrimMenu():
    """
    Adds the skyrim menu and a callback to update it when the project changes.
    """
    updateSkyrimMenu()
    addCallback()


def updateSkyrimMenu(*args):
    """
    Adds the 'Skyrim' menu to the Maya menu bar.

    Args:
        args: Allows the function to be used as a callback.
    """

    # Don't create menu in batch mode
    if cmds.about(batch=True):
        return

    # Delete the menu if it exists
    if cmds.menu(SKYRIM_MENU, exists=True):
        cmds.deleteUI(SKYRIM_MENU)

    if not cmds.menu(SKYRIM_MENU, exists=True):
        parent_menu = cmds.menu(
            SKYRIM_MENU,
            label='Skyrim',
            tearOff=True,
            parent=mel.eval("$retvalue = $gMainWindow;"),
        )

        # Project Label
        projectName = 'unnamed'
        if ckproject.getProject() is not None:
            projectName = ckproject.getProject().getName()
        cmds.menuItem(label=f'Project: {projectName}', divider=True, parent=parent_menu)

        # Create Project Button
        cmds.menuItem(
            label='New Project', parent=parent_menu,
            command='from ckmaya.ui import menu;menu.createProject()'
        )

        # Set Project Button
        cmds.menuItem(
            label='Open Project...', parent=parent_menu,
            command='from ckmaya.ui import menu;menu.setProject()'
        )

        # Recent Projects Menu
        cmds.menuItem(
            SKYRIM_RECENT_PROJECT_MENU, label='Recent Projects', parent=parent_menu,
            subMenu=True, postMenuCommand="from ckmaya.ui import menu;menu.updateRecentProjects();"
        )

        # Add Project Manager
        command = 'from ckmaya.ui import project_manager;project_manager.load()'
        cmds.menuItem(
            label="Project Window",
            parent=parent_menu,
            command=command
        )

        # Add Project Manager
        command = 'from ckmaya.ui import export_package_tool;export_package_tool.load()'
        cmds.menuItem(
            label="Export Package",
            parent=parent_menu,
            command=command
        )

        cmds.menuItem(label='Modelling', divider=True, parent=parent_menu)

        # Add Nif Command
        command = 'from ckmaya.ui import commands;commands.importMesh()'
        cmds.menuItem(
            label="Import Mesh",
            parent=parent_menu,
            command=command
        )
        command = 'from ckmaya.ui import edit_texture_tool;edit_texture_tool.load()'
        cmds.menuItem(
            label="Edit Textures",
            parent=parent_menu,
            command=command
        )
        command = 'from ckmaya.ui import commands;commands.convertTextures()'
        cmds.menuItem(
            label="Convert Textures",
            parent=parent_menu,
            command=command
        )

        cmds.menuItem(label='Rigging', divider=True, parent=parent_menu)

        # Add Open Rig
        command = 'from ckmaya.ui import commands;commands.openRigScene()'
        cmds.menuItem(
            label="Open Rig Scene",
            parent=parent_menu,
            command=command
        )

        # Add Physics Tool
        command = 'from ckmaya.ui import physics_tool;physics_tool.load()'
        cmds.menuItem(
            label="Create Physics",
            parent=parent_menu,
            command=command
        )

        # Add Create Export Rig Tool
        command = 'from ckmaya.ui import create_export_rig_tool;create_export_rig_tool.load()'
        cmds.menuItem(
            label="Create Export Rig",
            parent=parent_menu,
            command=command
        )

        # Add Export Skin Tool
        command = 'from ckmaya.ui import export_skin_tool;export_skin_tool.load()'
        cmds.menuItem(
            label="Export Skin",
            parent=parent_menu,
            command=command
        )

        # Add Export Rig Tool
        command = 'from ckmaya.ui import export_rig_tool;export_rig_tool.load()'
        cmds.menuItem(
            label="Export Rig",
            parent=parent_menu,
            command=command
        )

        # Add Bone Order Tool
        command = 'from ckmaya.ui import commands;commands.addBoneOrderAttr()'
        cmds.menuItem(
            label="Add Bone Order Tags",
            parent=parent_menu,
            command=command
        )

        cmds.menuItem(label='Animation', divider=True, parent=parent_menu)

        # Add Import Tag Tool
        command = 'from ckmaya.ui import import_tag_tool;import_tag_tool.load()'
        cmds.menuItem(
            label="Import Animation Tags",
            parent=parent_menu,
            command=command
        )

        # Add Import Command
        command = 'from ckmaya.ui import import_animation_tool;import_animation_tool.load()'
        cmds.menuItem(
            label="Import Animations",
            parent=parent_menu,
            command=command
        )

        # Add Import Mapping Command
        command = 'from ckmaya.ui import import_mapping_tool;import_mapping_tool.load()'
        cmds.menuItem(
            label="Edit Import Mapping",
            parent=parent_menu,
            command=command
        )

        # Add Export Command
        command = 'from ckmaya.core import ckcore;ckcore.exportAnimation()'
        command = 'from ckmaya.ui import animation_manager;animation_manager.load()'
        cmds.menuItem(
            label="Animation Manager",
            parent=parent_menu,
            command=command
        )
