""" Common commands for shelf buttons and menu items. """
import os.path

from maya import cmds
from ckmaya.core import ckcore, ckproject
from ckmaya.ui import core


def importMesh():
    """
    Imports a mesh file into the scene.
    """
    ckcore.importMesh(core.getFileDialog(
        directory=ckproject.getProject().getDirectory(),
        fileTypes=['nif', 'fbx']
    ))


def importTextures():
    """
    Imports texture files and assigns them to selected meshes.
    """
    meshes = cmds.ls(type='transform', sl=True) or []
    if len(meshes) == 0:
        return cmds.warning('No meshes selected.')
    directory = ckproject.getProject().getFullPath(ckproject.getProject().getTextureDirectory())
    albedo = core.getFileDialog(
        directory=directory,
        fileTypes=['dds', 'png', 'tga'],
        title='Select Albedo File'
    )
    normal = core.getFileDialog(
        directory=os.path.dirname(albedo),
        fileTypes=['dds', 'png', 'tga'],
        title='Select Normal Map'
    )
    ckcore.importTextures(meshes, albedo, normal)

