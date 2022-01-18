import os
import shutil
import tempfile

from ckmaya.core import ckcmd
from ckmaya.core import ckproject
import maya.api.OpenMaya as om2
from maya import cmds, mel


IMAGE_MAGICK_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bin', 'imagemagick')


def copyTagAttribiutes(srcRoot, dstRoot):
    """
    Copies animation tag attributes from the source root to the destination root.

    Args:
        srcRoot(str): A source root joint name.
        dstRoot(str): A destination root joint name.
    """
    for srcAttrName in cmds.listAttr(srcRoot, userDefined=True):
        if not cmds.attributeQuery(srcAttrName, node=dstRoot, exists=True):
            sel = om2.MSelectionList()
            sel.add('%s.%s' % (srcRoot, srcAttrName))
            cmd = om2.MFnAttribute(sel.getPlug(0).attribute()).getAddAttrCmd(True)
            cmd = cmd.replace(';', ' %s;' % dstRoot)
            mel.eval(cmd)

        cmds.copyAttr(srcRoot, dstRoot, at=[srcAttrName], v=True)

        # Copy Animation
        if cmds.keyframe(srcRoot, at=[srcAttrName], q=True):
            cmds.copyKey(srcRoot, at=[srcAttrName])
            cmds.pasteKey(dstRoot, at=[srcAttrName])


def bindSkeletons(srcRoot, dstRoot):
    """
    Binds the destination skeleton to the source skeleton.

    Args:
        srcRoot(str): The source root joint.
        dstRoot(st): The destination root joint.

    Returns:
        list: A list of constraints created.
    """
    constraints = []
    constraints.append(cmds.parentConstraint(srcRoot, dstRoot)[0])
    srcChildren = {child.split('|')[-1].split(':')[-1]: child
                   for child in cmds.listRelatives(srcRoot, type='joint', fullPath=True) or []}
    dstChildren = {child.split('|')[-1].split(':')[-1]: child
                   for child in cmds.listRelatives(dstRoot, type='joint', fullPath=True) or []}
    for name in srcChildren:
        if name in dstChildren:
            constraints.extend(bindSkeletons(srcChildren[name], dstChildren[name]))
    return constraints


def bakeSkeleton(root):
    """
    Bakes a skeleton along the current timeline.

    Args:
        root(str): A root joint.
    """
    try:
        cmds.refresh(su=True)
        start = cmds.playbackOptions(minTime=True, q=True)
        end = cmds.playbackOptions(maxTime=True, q=True)
        joints = [root] + cmds.listRelatives(root, type='joint', ad=True, fullPath=True) or []
        cmds.bakeResults(joints, at=['tx', 'ty', 'tz', 'rx', 'ry', 'rz'], t=(start, end), simulation=True)
    finally:
        cmds.refresh(su=False)


def importFbx(filepath, update=False, take=None):
    """
    Imports an fbx file and returns added nodes.

    Args:
        filepath(str): An fbx file path.
        update(bool): Whether to update the scene rather than adding nodes.
        take(bool): The take index to import.

    Returns:
        list: A list of node names.
    """
    if not str(filepath).lower().endswith('.fbx'):
        raise FbxException('"%s" is not an fbx file.' % filepath)
    if not os.path.exists(filepath):
        raise FbxException('Path "%s" does not exist' % filepath)

    mObjects = []

    def addNode(mObject, *args):
        """ A function that stores all added nodes. """
        if mObject.isNull():
            return
        mObjectHandle = om2.MObjectHandle(mObject)
        if not mObjectHandle.isAlive():
            return
        if not mObjectHandle.isValid():
            return
        mObjects.append((mObjectHandle, mObject))

    # Create a callback to listen for new nodes.
    callback = om2.MDGMessage.addNodeAddedCallback(addNode, 'dependNode')
    try:
        # Import the file
        cmds.unloadPlugin('fbxmaya')
        cmds.loadPlugin('fbxmaya')
        mel.eval('FBXImportMode -v %s' % ('exmerge' if update else 'add'))
        mel.eval('FBXImportFillTimeline -v true')
        if take is not None:
            mel.eval('FBXImport -f "%s" -t %s' % (filepath.replace('\\', '/'), take))
        else:
            mel.eval('FBXImport -f "%s"' % filepath.replace('\\', '/'))
    finally:
        # Always remove the callback
        om2.MMessage.removeCallback(callback)

    # Convert mObjects to node names
    nodes = set()
    for mObjectHandle, mObject in mObjects:
        if mObject.isNull():
            continue
        if not mObjectHandle.isAlive():
            continue
        if not mObjectHandle.isValid():
            continue
        if mObject.hasFn(om2.MFn.kDagNode):
            name = om2.MFnDagNode(mObject).fullPathName()
        else:
            name = om2.MFnDependencyNode(mObject).name()
        if cmds.objExists(name):
            nodes.add(name)

    return list(nodes)


def exportFbx(nodes, path):
    """
    Exports the given nodes as an fbx file.

    Args:
        nodes(list): A list of nodes to export.
        path(str): The destination fbx file path.

    Returns:
        str: The fbx file path.
    """

    # Determine what nodes we're exporting
    nodes = [node for node in nodes if 'shape' not in cmds.nodeType(node, i=True)]

    try:
        cmds.undoInfo(openChunk=True)

        # Export and restore the original selection
        cmds.select(nodes)
        mel.eval('FBXExport -f "%s" -s' % path.replace('\\', '/'))

    finally:
        cmds.undoInfo(closeChunk=True)
        cmds.undo()
    return path


def bakeAnimation(nodes):
    """
    Bakes animation on the given nodes for the current timeline.

    Args:
        nodes(list): A list of nodes.
    """
    try:
        cmds.refresh(su=True)
        start = cmds.playbackOptions(minTime=True, q=True)
        end = cmds.playbackOptions(maxTime=True, q=True)
        cmds.bakeResults(nodes, at=['tx', 'ty', 'tz', 'rx', 'ry', 'rz'], t=(start, end), simulation=True)
    finally:
        cmds.refresh(su=False)


def importAnimationTags(animation):
    """
    Import animation tags from an fbx file.

    Args:
        animation(str): An animated fbx file.
    """
    project = ckproject.getProject()
    exportJointName = project.getExportJointName()

    # Find the destination export joint
    dstJoint = None
    if cmds.objExists(exportJointName):
        dstJoint = exportJointName
    else:
        for node in cmds.ls('*:%s' % exportJointName) or []:
            dstJoint = node
    if dstJoint is None:
        raise BaseException('Could not fine destination root joint in scene.')

    importNodes = []
    try:
        # Import the animation file
        importNodes = importFbx(animation, update=False)

        # Find the source joint
        srcJoint = None
        for node in importNodes:
            name = node.split('|')[-1]
            if name == exportJointName:
                srcJoint = node
        if srcJoint is None:
            raise BaseException('Could not fine source root joint in imported animation.')

        # Transfer tags
        copyTagAttribiutes(srcJoint, dstJoint)
    finally:
        # Remove imported nodes
        cmds.delete(importNodes)


def importAnimation(animation, animationTags=None):
    """
    Exports the given scene animation onto the projects rig.

    Args:
        animation(str): An fbx or hkx animation file to import.
        animationTags(str): An optional fbx file to import animation tags from.
    """
    project = ckproject.getProject()
    skeletonScene = project.getFullPath(project.getSkeletonScene())
    animationDir = project.getFullPath(project.getAnimationSceneDirectory())
    exportJointName = project.getExportJointName()
    jointMapping = project.getControlJointMapping()

    # Convert HKX animations
    if animation.lower().endswith('.hkx'):
        skeletonHkx = project.getFullPath(project.getImportSkeletonHkx())
        skeletonNif = project.getFullPath(project.getImportSkeletonNif())
        cacheFile = project.getFullPath((project.getImportCacheFile()))

        # Create a temp directory to import the animation
        # ckcmd operates on directories of animations, so we copy the animation here to avoid over importing
        tempDirectory = os.path.join(tempfile.gettempdir(), 'tempanimations')
        if not os.path.exists(tempDirectory):
            os.makedirs(tempDirectory)
        tempAnimation = os.path.join(tempDirectory, os.path.basename(animation))
        shutil.copyfile(animation, tempAnimation)

        # Export the Animation
        ckcmd.exportrig(skeletonHkx, skeletonNif, tempDirectory,
                        animation_hkx=tempDirectory,
                        cache_txt=cacheFile)

        # Copy the animations back to the original directory
        tempFbxAnimation = tempAnimation.replace('.hkx', '.fbx').replace('.HKX', '.fbx')
        animation = animation.replace('.hkx', '.fbx').replace('.HKX', '.fbx')
        shutil.move(tempFbxAnimation, animation)

        # Export the animation again, this time to get correct animation tags
        # ckcmd.exportanimation(skeletonHkx, tempDirectory, tempDirectory)
        # animationTags = tempFbxAnimation

    # Check if an animation already exists
    newAnimation = os.path.join(animationDir, '.'.join([os.path.basename(animation).split('.')[0], 'ma']))

    # Create a new scene
    cmds.file(new=True, force=True, prompt=False)

    # Reference the animation rig
    rigNodes = cmds.file(skeletonScene, reference=True, namespace='RIG', returnNewNodes=True)

    # Find the referenced root joint
    referenceRoot = None
    for name in rigNodes:
        nodeName = name.split('|')[-1].split(':')[-1]
        if nodeName == exportJointName:
            referenceRoot = name
    if referenceRoot is None:
        raise BaseException('Could not find export joint in referenced skeleton.')

    # Duplicate the root joint
    dupRoot = cmds.duplicate(referenceRoot)[0]
    dupSkeleton = [dupRoot] + cmds.listRelatives(dupRoot, type='joint', ad=True, fullPath=True) or []

    # Bind Rig to joints
    controls = []
    for joint in dupSkeleton:
        jointName = joint.split('|')[-1]
        jointControls = project.getJointControls(jointName)

        # If no controls are mapped to the joint, bind to itself
        if len(jointControls) == 0:
            jointControls = [jointName]

        for control in jointControls:
            control = 'RIG:%s' % control
            if not cmds.objExists(control):
                cmds.warning('Warning: %s does not exist, skipping.' % control)
                continue

            skipTranslate = []
            for attr in ['tx', 'ty', 'tz']:
                if not cmds.getAttr('%s.%s' % (control, attr), settable=True):
                    skipTranslate.append(attr[-1])

            skipRotate = []
            for attr in ['rx', 'ry', 'rz']:
                if not cmds.getAttr('%s.%s' % (control, attr), settable=True):
                    skipRotate.append(attr[-1])

            cmds.parentConstraint(
                joint, control,
                sr=skipRotate,
                st=skipTranslate,
                mo=True
            )
            controls.append(control)

    # Import animation
    importFbx(animation, update=True)

    # Bake controls animation
    if len(controls) > 0:
        bakeAnimation(controls)

    # Delete import skeleton
    cmds.delete(dupRoot)

    # If an tag file exists, import tags
    # if animationTags is not None:
    #     importAnimationTags(animationTags)

    # Save scene
    cmds.file(rename=newAnimation)
    cmds.file(save=True, type="mayaAscii")


def exportAnimation():
    """
    Exports the current scene animation.
    """
    project = ckproject.getProject()
    exportSkeletonHkxFile = project.getFullPath(project.getExportSkeletonHkx())
    exportBehaviorDir = project.getFullPath(project.getExportBehaviorDirectory())
    exportCacheFile = project.getFullPath(project.getExportCacheFile())

    # Get the export animation file
    exportAnimationDir = project.getFullPath(project.getExportAnimationDirectory())
    animationName = os.path.basename(ckproject.getSceneName()).split('.')[0]
    exportAnimationFbxFile = os.path.join(exportAnimationDir, '%s.fbx' % animationName)
    exportAnimationHkxFile = os.path.join(exportAnimationDir, '%s.hkx' % animationName)

    # Get the export joint name
    exportJointName = project.getExportJointName()

    # Get the export joint
    if exportJointName == '':
        raise ValueError('Invalid export node name "%s"' % exportJointName)
    exportJoints = []
    for joint in cmds.ls('*:%s' % exportJointName) or []:
        exportJoints.append(joint)
    for joint in cmds.ls(exportJointName) or []:
        exportJoints.append(joint)
    if len(exportJoints) == 0:
        raise ValueError('Export node "%s" does not exist.' % exportJointName)
    if len(exportJoints) > 1:
        raise ValueError('Multiple export nodes found with name "%s"' % exportJointName)
    exportJoint = exportJoints[0]

    try:
        cmds.undoInfo(openChunk=True)

        # Create a duplicate root joint
        dupExportJoint = cmds.duplicate(exportJoint)[0]
        cmds.rename(dupExportJoint, exportJoint.split('|')[-1].split(':')[-1])

        # Copy animation tags
        copyTagAttribiutes(exportJoint, dupExportJoint)

        # Bind and Bake skeletons
        constraints = bindSkeletons(exportJoint, dupExportJoint)
        bakeSkeleton(dupExportJoint)
        cmds.delete(constraints)

        # Export animation
        exportFbx([dupExportJoint], exportAnimationFbxFile)

        # Copy Animation Data Files To Root
        animationDataDir = project.getFullPath(project.getExportAnimationDataDirectory())
        animationDataFiles = []
        for filename in os.listdir(animationDataDir):
            srcPath = os.path.join(animationDataDir, filename)
            dstPath = os.path.join(project.getDirectory(), filename)
            animationDataFiles.append((srcPath, dstPath))
            shutil.copyfile(srcPath, dstPath)

        # Run ckcmd on the fbx file
        ckcmd.importanimation(
            exportSkeletonHkxFile, exportAnimationFbxFile,
            exportAnimationDir, cache_txt=exportCacheFile, behavior_directory=exportBehaviorDir
        )

        # Copy Data Files Back
        for srcPath, dstPath in animationDataFiles:
            shutil.copyfile(dstPath, srcPath)
            os.remove(dstPath)

    finally:
        cmds.undoInfo(closeChunk=True)
        cmds.undo()


def importMesh(filepath):
    """
    Imports a mesh from a nif file.
    """

    # Convert NIF files to fbx
    if filepath.endswith('.nif'):
        ckcmd.exportfbx(filepath, os.path.dirname(filepath))
        filepath = filepath.replace('.nif', '.fbx')

    # Import fbx
    nodes = importFbx(filepath, update=False)

    # Remove rigid bodies
    for node in nodes:
        if node.endswith('_rb'):
            cmds.delete(node)

    return nodes


def convertTexture(filepath, format='dds'):
    """
    Runs imagemagick to convert a texture to the specified format.

    Args:
        filepath(str): A texture filepath.
        format(str): The file extension to convert to.

    Returns:
        str: The output file path.
    """
    outpath = '%s.%s' % (filepath.split('.')[0], format.split('.')[-1])
    command = '%s "%s" "%s"' % (os.path.join(IMAGE_MAGICK_DIR, 'convert.exe'), filepath, outpath)
    ckcmd.run_command(command, directory=os.path.dirname(filepath))
    return outpath


def importTextures(meshes, albedo, normal, name='skywind'):
    """
    Imports textures into the current project and assigns them to selected meshes.

    Args:
        meshes(list): A list of meshes to assign textures to.
        albedo(str): An albedo filepath.
        normal(str): An optional normal map filepath.
        name(str): A prefix for each shader node.
    """

    # Sanitize paths
    albedo = ckproject.santizePath(albedo)
    normal = ckproject.santizePath(normal)

    # Copy textures to texture directory
    textureDirectory = ckproject.getProject().getFullPath(ckproject.getProject().getTextureDirectory())
    if textureDirectory not in albedo:
        newpath = os.path.join(textureDirectory, os.path.basename(albedo))
        shutil.copyfile(albedo, newpath)
        albedo = newpath
    if textureDirectory not in normal:
        newpath = os.path.join(textureDirectory, os.path.basename(normal))
        shutil.copyfile(normal, newpath)
        normal = newpath

    # Convert textures from dds
    if albedo.endswith('.dds'):
        albedo = convertTexture(albedo, 'png')
    if normal.endswith('.dds'):
        normal = convertTexture(normal, 'png')

    # Create shader
    shader = cmds.shadingNode('blinn', name='%s_blinn' % name, asShader=True)
    shadingGroup = cmds.sets(name='%sSG' % shader, empty=True, renderable=True, noSurfaceShader=True)
    cmds.connectAttr('%s.outColor' % shader, '%s.surfaceShader' % shadingGroup)
    for channel in ['R', 'G', 'B']:
        cmds.setAttr('%s.ambientColor%s' % (shader, channel), 1)
    cmds.setAttr('%s.specularRollOff' % shader, 0.3)
    cmds.setAttr('%s.eccentricity' % shader, 0.2)

    # Add textures
    albedoNode = cmds.shadingNode("file", asTexture=True, n="%s_albedo" % name)
    cmds.setAttr('%s.fileTextureName' % albedoNode, albedo, type="string")
    cmds.connectAttr('%s.outColor' % albedoNode, '%s.color' % shader)

    normalNode = cmds.shadingNode("file", asTexture=True, n="%s_normal" % name)
    cmds.setAttr('%s.fileTextureName' % normalNode, normal, type="string")
    bumpNode = cmds.createNode('bump2d')
    cmds.connectAttr('%s.outAlpha' % normalNode, '%s.bumpValue' % bumpNode)
    cmds.setAttr('%s.bumpInterp' % bumpNode, 1)
    cmds.connectAttr('%s.outNormal' % bumpNode, '%s.normalCamera' % shader)

    for mesh in meshes:
        cmds.sets(mesh, e=True, forceElement=shadingGroup)


def createJointControlMapping(joint=None, controls=None):
    """
    Maps the specified control to the specified rig joint.
    If a control is not specified a selected transform will be used.
    Additionally, if a joint is not specified a selected rig joint will be used.

    Args:
        joint(str): A joint name.
        controls(list): A list of control names.
    """
    project = ckproject.getProject()

    # Find the project export joint
    root = project.getExportJointName()
    if root is None or not cmds.objExists(root):
        cmds.warning('%s is not a valid root joint node.' % root)
        return None, None

    # Get the current selection
    selectedTransforms = cmds.ls(sl=True, exactType='transform', long=True) or []
    selectedJoints = cmds.ls(sl=True, exactType='joint', long=True) or []

    # Get a joint to map
    if joint is None:
        rigJoints = [joint for joint in selectedJoints if root in joint]
        if len(rigJoints) > 1:
            return cmds.warning('Too many rig joints selected: %s' % rigJoints)
        if len(rigJoints) == 0:
            return cmds.warning('No rig joints selected.')
        joint = rigJoints[0]

    # Get controls to map
    if controls is None:
        controls = selectedTransforms
    if len(controls) == 0:
        return cmds.warning('No controls selected.')

    # Map each control
    for control in controls:
        project.setControlJoint(control.split('|')[-1].split(':')[-1], joint.split('|')[-1].split(':')[-1])


def getJointMappingFromSelection(root):
    """
    Gets a mapping from a source transform to a skeleton joint.
    The order should not matter, the skeleton will be returned second.

    Args:
        root(str): A root joint name.

    Returns:
        str, str: The source transform name and the destination joint name.
    """
    if root is None or not cmds.objExists(root):
        cmds.warning('%s is not a valid root joint node.' % root)
        return None, None

    # Get the current selection
    selection = cmds.ls(sl=True, long=True, type='transform') or []
    if len(selection) <= 1:
        cmds.warning('Not enough nodes selected.')
        return None, None

    # Separate rig joints from transforms
    transforms = []
    joints = []
    for node in selection:
        if cmds.nodeType(node) == 'joint':
            if '|%s|' % root.split('|')[-1] in node:
                joints.append(node)
        else:
            transforms.append(node)
    if len(joints) == 0:
        cmds.warning('Not enough rig joints selected.')
        return None, None
    if len(joints) > 1:
        cmds.warning('Too many rig joints selected.')
        return None, None
    if len(transforms) > 1:
        cmds.warning('Too many sources selected.')
        return None, None

    return transforms[0], joints[0]


class FbxException(BaseException):
    """ Raised to indicate an invalid fbx file. """

