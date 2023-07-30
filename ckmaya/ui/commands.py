""" Common commands for shelf buttons and menu items. """
import os.path

from maya import cmds
from ..core import ckcore, ckproject
from ..ui import core


def importMesh():
    """
    Imports a mesh file into the scene.
    """
    ckcore.importMesh(core.getFileDialog(
        directory=ckproject.getProject().getDirectory(),
        fileTypes=['nif', 'fbx']
    ))


def openRigScene():
    """ Opens the projects rig scene. """
    scene = ckproject.getProject().getSkeletonScene()
    if not os.path.exists(scene):
        raise RuntimeError('Project scene "%s" does not exist.' % scene)
    if core.saveChangesDialog():
        cmds.file(scene, open=True, force=True)


def addBoneOrderAttr():
    """ Adds a bone order attribute to the selected joints. """
    for joint in cmds.ls(type='joint') or []:
        ckcore.addBoneOrderAttr(joint)


def importTextures():
    """
    Imports texture files and assigns them to selected meshes.
    """
    meshes = cmds.ls(type='transform', sl=True) or []
    if len(meshes) == 0:
        return cmds.warning('No meshes selected.')
    directory = ckproject.getProject().getTextureDirectory()
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
    ckcore.setTextures(meshes, albedo, normal)


def convertTextures():
    """
    Runs imagemagick to convert textures from a file dialog to DDS.
    """
    directory = ckproject.getProject().getTextureDirectory()
    textures = core.getFilesDialog(
        directory=directory,
        fileTypes=['png', 'tga'],
        title='Select Texture Files'
    )
    for texture in textures:
        ckcore.convertTexture(texture)
        print ('Converted %s' % texture)


