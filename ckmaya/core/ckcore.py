import os
import shutil
import tempfile

from . import ckcmd, cknif
from . import ckproject
import maya.api.OpenMaya as om2
import maya.api.OpenMayaAnim as oma2
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


def getDefaultTimeRange():
    """
    Gets the default start and end time.

    Returns:
        float, float: The start and end time.
    """
    return cmds.playbackOptions(minTime=True, q=True), cmds.playbackOptions(maxTime=True, q=True)


def getSkeleton(root):
    """
    Gets the entire skeletal hierarchy given a root joint.

    Args:
        root(str): A root joint name.

    Returns:
        list: A list of joint names.
    """
    return [root] + cmds.listRelatives(root, type='joint', ad=True, fullPath=True) or []


def getRootJoint(nodes=None, namespace=None):
    """
    Attempts to find a root joint in the current scene using the export joint name project setting.

    Args:
        nodes(list): An optional list of nodes to search.
        namespace(str): An optional namespace to use.

    Returns:
        str: The export joint name.
    """
    # Get the export joint name
    project = ckproject.getProject()
    exportJointName = project.getExportJointName()

    if nodes is None:
        # If an exact match exists, return that
        if cmds.objExists(exportJointName):
            return exportJointName

        # Otherwise search for another match
        exportJoints = cmds.ls('*:%s' % exportJointName, type='joint') or []
        if len(exportJoints) == 1:
            return exportJoints[0]

        raise Exception('Could not find unique root joint with name "%s".' % exportJointName)

    else:
        # Otherwise search the nodes for the joint
        for node in nodes:
            if node.split('|')[-1].split(':')[-1] == exportJointName:
                return node
        raise Exception('Could not find root joint in nodes with name "%s"' % exportJointName)


def bakeSkeleton(root, time=None):
    """
    Bakes a skeleton along the current timeline.

    Args:
        root(str): A root joint.
        time(tuple): The start and end times.
    """
    try:
        cmds.refresh(su=True)
        time = time or getDefaultTimeRange()
        joints = getSkeleton(root)
        cmds.bakeResults(joints, at=['tx', 'ty', 'tz', 'rx', 'ry', 'rz'], t=time, simulation=True)
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

        # Ensure joints are set to export as joints
        for node in nodes:
            if cmds.nodeType(node) == 'joint' and node.endswith('_rb'):
                if cmds.attributeQuery('filmboxTypeID', node=node, exists=True):
                    cmds.setAttr('%s.filmboxTypeID' % node, 2)

        # Export and restore the original selection
        cmds.select(nodes)
        command = 'FBXExport -f "%s" -s' % path.replace('\\', '/')
        try:
            mel.eval(command)
        except RuntimeError:
            raise RuntimeError('Error occurred during mel script: %s' % command)

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
    # Find the destination export joint
    dstJoint = getRootJoint()

    importNodes = []
    try:
        # Import the animation file
        importNodes = importFbx(animation, update=False)

        # Find the source joint
        srcJoint = getRootJoint(nodes=importNodes)

        # Transfer tags
        copyTagAttribiutes(srcJoint, dstJoint)
    finally:
        # Remove imported nodes
        cmds.delete(importNodes)


def testImportMapping():
    """
    Creates a new scene to test the project import mapping.
    """
    project = ckproject.getProject()
    skeletonScene = project.getSkeletonScene()
    exportJointName = project.getExportJointName()

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
    if cmds.listRelatives(dupRoot, parent=True) is not None:
        dupRoot = cmds.parent(dupRoot, world=True)[0]
    joints = [referenceRoot] + cmds.listRelatives(referenceRoot, type='joint', ad=True, fullPath=True) or []
    dupSkeleton = [dupRoot] + cmds.listRelatives(dupRoot, type='joint', ad=True, fullPath=True) or []

    # Ensure joints are in the same pose
    for dupJoint in dupSkeleton:
        for joint in joints:
            jointName = joint.split('|')[-1].split(':')[-1]
            dupJointName = dupJoint.split('|')[-1].split(':')[-1]
            if jointName != dupJointName:
                continue
            for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz']:
                cmds.setAttr('%s.%s' % (dupJoint, attr), cmds.getAttr('%s.%s' % (joint, attr)))

    # Bind Rig to joints
    controls = []
    for joint in dupSkeleton:
        jointName = joint.split('|')[-1]
        jointControls = project.getJointControls(jointName)

        # If no controls are mapped to the joint, skip it
        if len(jointControls) == 0:
            continue
            # jointControls = [jointName]

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


def importAnimation(animation, animationTags=None):
    """
    Exports the given scene animation onto the projects rig.

    Args:
        animation(str): An fbx or hkx animation file to import.
        animationTags(str): An optional fbx file to import animation tags from.
    """
    project = ckproject.getProject()
    skeletonScene = project.getSkeletonScene()
    animationDir = project.getAnimationSceneDirectory()
    exportJointName = project.getExportJointName()
    jointMapping = project.getControlJointMapping()

    # Convert HKX animations
    if animation.lower().endswith('.hkx'):
        skeletonHkx = project.getImportSkeletonHkx()
        skeletonNif = project.getImportSkeletonNif()
        cacheFile = project.getImportCacheFile()

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
    joints = [referenceRoot] + cmds.listRelatives(referenceRoot, type='joint', ad=True, fullPath=True) or []
    dupSkeleton = [dupRoot] + cmds.listRelatives(dupRoot, type='joint', ad=True, fullPath=True) or []

    # Ensure joints are in the same pose
    for dupJoint in dupSkeleton:
        for joint in joints:
            jointName = joint.split('|')[-1].split(':')[-1]
            dupJointName = dupJoint.split('|')[-1].split(':')[-1]
            if jointName != dupJointName:
                continue
            for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz']:
                cmds.setAttr('%s.%s' % (dupJoint, attr), cmds.getAttr('%s.%s' % (joint, attr)))

    # Bind Rig to joints
    controls = []
    for joint in dupSkeleton:
        jointName = joint.split('|')[-1]
        jointControls = project.getJointControls(jointName)

        # If no controls are mapped to the joint, skip it
        if len(jointControls) == 0:
            continue
            # jointControls = [jointName]

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


def moveSkeletonAnimation(root, oldTime, newTime):
    """
    Moves keyframes for a skeleton.

    Args:
        root(str): A root joint.
        oldTime(tuple): The old start and end times.
        newTime(tuple): The new start and end times.
    """
    joints = getSkeleton(root)
    for joint in joints:
        for attribute in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz']:
            cmds.keyframe('%s.%s' % (joint, attribute), relative=True, timeChange=newTime[0] - oldTime[0], e=True)


def exportAnimation(name=None, time=None, format=None):
    """
    Exports the current scene animation.

    Args:
        name(str): The export animation name.
        time(tuple): The start and end time range to export.
        format(str): The export file format. Currently either 'hkx' or 'fbx'. Defaults to 'hkx'.
    """
    format = format or 'hkx'
    _start, _end = getDefaultTimeRange()
    start, end = time if time is not None else getDefaultTimeRange()
    project = ckproject.getProject()
    # exportSkeletonHkxFile = project.getExportSkeletonHkx()
    exportSkeletonHkxFile = project.getExportAnimationSkeletonHkx()
    exportBehaviorDir = project.getExportBehaviorDirectory()
    exportCacheFile = project.getExportCacheFile()

    # Get the export animation file
    exportAnimationDir = project.getExportAnimationDirectory()
    animationName = name or os.path.basename(ckproject.getSceneName()).split('.')[0]
    exportAnimationFbxFile = os.path.join(exportAnimationDir, '%s.fbx' % animationName)
    exportAnimationHkxFile = os.path.join(exportAnimationDir, '%s.hkx' % animationName)

    # Get the export joint name
    exportJointName = project.getExportJointName()

    # Get the export joint
    if exportJointName == '':
        raise ValueError('Invalid export node name "%s"' % exportJointName)
    exportJoints = set()
    for joint in cmds.ls('*:%s' % exportJointName, long=True) or []:
        exportJoints.add(joint)
    for joint in cmds.ls(exportJointName, long=True) or []:
        exportJoints.add(joint)
    if len(exportJoints) == 0:
        raise ValueError('Export node "%s" does not exist.' % exportJointName)
    if len(exportJoints) > 1:
        raise ValueError('Multiple export nodes found with name "%s"' % exportJointName)
    exportJoint = list(exportJoints)[0]

    try:
        cmds.undoInfo(openChunk=True)

        # Create a duplicate root joint
        dupExportJoint = cmds.duplicate(exportJoint)[0]
        cmds.rename(dupExportJoint, exportJoint.split('|')[-1].split(':')[-1])

        # Copy animation tags
        copyTagAttribiutes(exportJoint, dupExportJoint)

        # Bind and Bake skeletons
        constraints = bindSkeletons(exportJoint, dupExportJoint)
        bakeSkeleton(dupExportJoint, time=(start, end))
        cmds.delete(constraints)

        # Apply euler filter
        for joint in cmds.listRelatives(dupExportJoint, ad=True, type='joint') or []:
            cmds.filterCurve(joint)

        # Move Keys to start at frame 0
        exportStart, exportEnd = 0, end - start
        moveSkeletonAnimation(dupExportJoint, (start, end), (exportStart, exportEnd))

        # Export animation
        cmds.playbackOptions(minTime=exportStart, maxTime=exportEnd)
        exportFbx([dupExportJoint], exportAnimationFbxFile)

        # Copy Animation Data Files To Root
        animationDataDir = project.getExportAnimationDataDirectory()
        animationDataFiles = []
        # for filename in os.listdir(animationDataDir):
        #     srcPath = os.path.join(animationDataDir, filename)
        #     dstPath = os.path.join(project.getDirectory(), filename)
        #     animationDataFiles.append((srcPath, dstPath))
        #     shutil.copyfile(srcPath, dstPath)

        # Run ckcmd on the fbx file
        if format == 'hkx':
            # ckcmd.importanimation(
            #     exportSkeletonHkxFile, exportAnimationFbxFile,
            #     exportAnimationDir, cache_txt=exportCacheFile, behavior_directory=exportBehaviorDir
            # )
            ckcmd.importanimation(
                exportSkeletonHkxFile, exportAnimationFbxFile,
                exportAnimationDir, cache_txt=exportCacheFile
            )

            # Move legacy files to their own directory
            legacyPath = exportAnimationHkxFile.replace('.hkx', '_le.hkx')
            if os.path.exists(legacyPath):
                legacyDir = os.path.join(os.path.dirname(legacyPath), 'le')
                if not os.path.exists(legacyDir):
                    os.makedirs(legacyDir)
                shutil.move(legacyPath, os.path.join(legacyDir, os.path.basename(legacyPath)))

            # Copy Data Files Back
            for srcPath, dstPath in animationDataFiles:
                shutil.copyfile(dstPath, srcPath)
                os.remove(dstPath)

    finally:
        cmds.undoInfo(closeChunk=True)
        cmds.undo()
        cmds.playbackOptions(minTime=_start, maxTime=_end)


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


def exportTexture(filepath):
    """
    Exports a texture to the texture directory and converts it to .dds if necessary.

    Args:
        filepath(str): A texture filepath.

    Returns:
        str: The export texture filepath.
    """

    # Convert to dds
    if not filepath.endswith('.dds'):
        filepath = convertTexture(filepath)

    # Copy to export filepath
    exportfilepath = os.path.join(ckproject.getProject().getExportTextureDirectory(), os.path.basename(filepath))
    if os.path.normpath(filepath) != os.path.normpath(exportfilepath):
        shutil.copyfile(
            filepath, exportfilepath
        )
    return exportfilepath


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
    command = '%s  -auto-orient "%s" "%s"' % (os.path.join(IMAGE_MAGICK_DIR, 'convert.exe'), filepath, outpath)
    ckcmd.run_command(command, directory=os.path.dirname(filepath))
    return outpath


def getMaterial(mesh):
    """
    Gets a blinn material assigned to a mesh.

    Args:
        mesh(str): A mesh name.

    Returns:
        str: A material name.
    """
    material = None
    for shadingGroup in cmds.listConnections(mesh, type='shadingEngine') or []:
        for blinn in cmds.listConnections(shadingGroup, type='blinn') or []:
            material = blinn
    return material


def setTextures(mesh, albedo=None, normal=None, emissive=None, cubemap=None, metallic=None, subsurface=None,
                ambientColor=None, name='skywind'):
    """
    Imports textures into the current project and assigns them to selected meshes.

    Args:
        mesh(str): A mesh to assign textures to.
        albedo(str): An albedo texture filepath.
        normal(str): A normal map filepath.
        emissive(str): An emissive map filepath.
        cubemap(str): A cube map filepath.
        metallic(str): A metallic map filepath.
        subsurface(str): A subsurface map filepath.
        ambientColor(tuple): An ambient color.
        name(str): A prefix for each shader node.
    """

    # Copy textures to texture directory
    # textureDirectory = ckproject.getProject().getTextureDirectory()
    # if textureDirectory not in albedo:
    #     newpath = os.path.join(textureDirectory, os.path.basename(albedo))
    #     shutil.copyfile(albedo, newpath)
    #     albedo = newpath
    # if textureDirectory not in normal:
    #     newpath = os.path.join(textureDirectory, os.path.basename(normal))
    #     shutil.copyfile(normal, newpath)
    #     normal = newpath
    #
    # # Convert textures from dds
    # if albedo.endswith('.dds'):
    #     albedo = convertTexture(albedo, 'png')
    # if normal.endswith('.dds'):
    #     normal = convertTexture(normal, 'png')

    # Find an existing shader
    material = getMaterial(mesh)

    # Create shader
    if material is None:
        material = cmds.shadingNode('blinn', name='%s_blinn' % name, asShader=True)
        shadingGroup = cmds.sets(name='%sSG' % material, empty=True, renderable=True, noSurfaceShader=True)
        cmds.connectAttr('%s.outColor' % material, '%s.surfaceShader' % shadingGroup)
        ambientColor = ambientColor or (1,1,1)
        for channelName, channel in zip(['R', 'G', 'B'], ambientColor):
            cmds.setAttr('%s.ambientColor%s' % (material, channelName), channel)
        cmds.setAttr('%s.specularRollOff' % material, 0.3)
        cmds.setAttr('%s.eccentricity' % material, 0.2)
        cmds.sets(mesh, e=True, forceElement=shadingGroup)

    # Albedo Map
    if albedo is not None:
        albedoNode = cmds.shadingNode("file", asTexture=True, n="%s_albedo" % name)
        cmds.setAttr('%s.fileTextureName' % albedoNode, albedo, type="string")
        cmds.connectAttr('%s.outColor' % albedoNode, '%s.color' % material)

    # Normal Map
    if normal is not None:
        normalNode = cmds.shadingNode("file", asTexture=True, n="%s_normal" % name)
        cmds.setAttr('%s.fileTextureName' % normalNode, normal, type="string")
        bumpNode = cmds.createNode('bump2d')
        cmds.connectAttr('%s.outAlpha' % normalNode, '%s.bumpValue' % bumpNode)
        cmds.setAttr('%s.bumpInterp' % bumpNode, 1)
        cmds.connectAttr('%s.outNormal' % bumpNode, '%s.normalCamera' % material)

    # Cube Map
    if cubemap is not None:
        cubeNode = cmds.shadingNode("file", asTexture=True, n="%s_cubemap" % name)
        cmds.setAttr('%s.fileTextureName' % cubeNode, cubemap, type="string")
        cmds.connectAttr('%s.outColor' % cubeNode, '%s.reflectedColor' % material)

    # Emissive Map
    if emissive is not None:
        pass

    # Metallic Map
    if metallic is not None:
        metallicNode = cmds.shadingNode("file", asTexture=True, n="%s_metallic" % name)
        cmds.setAttr('%s.fileTextureName' % metallicNode, metallic, type="string")
        for channel in ['R', 'G', 'B']:
            cmds.connectAttr('%s.outColorR' % metallicNode, '%s.specularColor%s' % (material, channel))

    # Subsurface Map
    if subsurface is not None:
        subsurfaceNode = cmds.shadingNode("file", asTexture=True, n="%s_subsurface" % name)
        cmds.setAttr('%s.fileTextureName' % subsurfaceNode, subsurface, type="string")
        cmds.connectAttr('%s.outAlpha' % subsurfaceNode, '%s.translucence' % material)


def getTextures(mesh):
    """
    Gets textures from a mesh node.

    Args:
        mesh(str): A mesh name.

    Returns:
        dict[str, str]: A mapping of texture names to filepaths.
    """
    if not cmds.nodeType(mesh) == 'mesh':
        mesh = cmds.listRelatives(mesh, type='mesh')[0]

    # Get meshes material
    material = getMaterial(mesh)
    if material is None:
        return {}

    textures = {}

    # Albedo
    for filenode in cmds.listConnections('%s.color' % material, s=True, d=False, type='file') or []:
        textures['albedo'] = cmds.getAttr('%s.fileTextureName' % filenode)

    # Normal
    for bump in cmds.listConnections('%s.normalCamera' % material, s=True, d=False, type='bump2d') or []:
        for filenode in cmds.listConnections('%s.bumpValue' % bump, s=True, d=False, type='file') or []:
            textures['normal'] = cmds.getAttr('%s.fileTextureName' % filenode)

    # Emissive

    # Metallic
    for filenode in cmds.listConnections('%s.specularColorR' % material, s=True, d=False, type='file') or []:
        textures['metallic'] = cmds.getAttr('%s.fileTextureName' % filenode)

    # Cube Map
    for filenode in cmds.listConnections('%s.reflectedColor' % material, s=True, d=False, type='file') or []:
        textures['cubemap'] = cmds.getAttr('%s.fileTextureName' % filenode)

    # Subsurface
    for filenode in cmds.listConnections('%s.translucence' % material, s=True, d=False, type='file') or []:
        textures['subsurface'] = cmds.getAttr('%s.fileTextureName' % filenode)

    return textures


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


def connectExportJoint(joint, exportJoint):
    """
    Connects an export joint to a rig joint.
    This is used to connect a skyrim-friendly skeleton to a custom rig skeleton.

    Args:
        joint(str): A source joint name.
        exportJoint(str): An export joint name.
    """

    # Match translation
    cmds.xform(exportJoint, t=cmds.xform(joint, t=True, q=True, ws=True), ws=True)

    # Create parent constraint
    constraint = cmds.parentConstraint(exportJoint, q=True)
    if constraint is not None:
        cmds.delete(constraint)
    cmds.parentConstraint(joint, exportJoint, mo=True)

    # Give the joints matching joint labels (these will be used later for transferring skinning)
    label = joint.split('|')[-1]
    for toLabel in [joint, exportJoint]:
        cmds.setAttr(f'{toLabel}.type', 18)
        cmds.setAttr(f'{toLabel}.otherType', label, type='string')


def addBoneOrderAttr(joint):
    """
    Adds a bone order attribute to a joint.

    Args:
        joint(str): A joint name.
    """
    if cmds.attributeQuery('bone_order', node=joint, exists=True):
        return
    boneOrderValue = 0
    for boneOrderAttr in cmds.ls('*.bone_order'):
        value = cmds.getAttr(boneOrderAttr)
        if value > boneOrderValue:
            boneOrderValue = value
    cmds.addAttr(joint, ln='bone_order', at='short', k=True)
    cmds.setAttr('%s.bone_order' % joint, boneOrderValue + 1)


def addExportJointHierarchy(rigJoint, exportJoint):
    """
    Recursively adds export joints for all child joints of a rig joint.

    Args:
        rigJoint(str): The rig joint to copy all children from.
        exportJoint(str): The parent export joint to parent to.
    """
    def _addExportJoints(rigJoint, exportJoint):
        for childRigJoint in cmds.listRelatives(rigJoint, fullPath=True, type='joint') or []:
            if childRigJoint.endswith('_rb'):
                continue
            childExportJoint = addExportJoint(childRigJoint, exportJoint)
            _addExportJoints(childRigJoint, childExportJoint)
    _addExportJoints(rigJoint, exportJoint)


def addExportJoint(joint, exportJointParent):
    """
    Adds an export joint parented to the given export joint and matching the rig joint.

    Args:
        joint(str): A source joint name.
        exportJointParent(str): An export joint name.

    Returns:
        str: The added export joint.
    """

    # Create the export joint
    exportJointName = '%s_cb_' % joint.split('|')[-1]
    exportJoint = cmds.createNode('joint', parent=exportJointParent, name=exportJointName)

    # Match joint radius
    cmds.setAttr('%s.radius' % exportJoint, cmds.getAttr('%s.radius' % exportJointParent))

    # Add bone order attribute
    addBoneOrderAttr(exportJoint)

    # Connect the expoirt joint
    connectExportJoint(joint, exportJoint)

    return exportJoint


def createExportMesh(srcMesh):
    """
    Creates a duplicate mesh skinned to connected joints.

    Args:
        srcMesh(str): A mesh name.
    """

    # Get mesh skin cluster and influences
    srcCluster = cmds.ls(cmds.listHistory(srcMesh), type='skinCluster')[0]
    srcInfluences = cmds.skinCluster(srcCluster, inf=True, q=True)

    # Find the destination influences by finding export joints connected to the source influences
    exportJoint = ckproject.getProject().getExportJointName()
    exportJoints = [exportJoint] + cmds.listRelatives(exportJoint, ad=True, type='joint', fullPath=True) or []
    exportJoints = [joint for joint in exportJoints if not exportJoint.endswith('_rb')]
    dstInfluences = []
    influenceMapping = {}
    for joint in exportJoints:
        constraint = cmds.parentConstraint(joint, q=True)
        if constraint is not None:
            for target in cmds.ls(cmds.listConnections(f'{constraint}.target', s=True, d=False) or [], type='joint'):
                if target in srcInfluences:
                    dstInfluences.append(joint)
                    influenceMapping[joint] = target

    # Check for missing influences
    missingInfluences = []
    for srcInfluence in srcInfluences:
        if srcInfluence not in influenceMapping.values():
            missingInfluences.append(srcInfluence)
    if len(missingInfluences) > 0:
        cmds.warning('Failed to find destination influences for influences:\n%s' % '\n'.join(missingInfluences))
        # raise Exception('Failed to find destination influences for influences:\n%s' %
        #                 '\n'.join(missingInfluences))

    # Create duplicate skinned mesh
    dstMesh = cmds.duplicate(srcMesh, name=srcMesh.split('|')[-1] + 'Export')[0]
    dstCluster = cmds.skinCluster(dstMesh, dstInfluences, tsb=True)[0]

    # For each destination joint with out a source, map it to its closest parent source
    def getParentSource(dstInfluence):
        for parentInfluence in cmds.listRelatives(dstInfluence, parent=True):
            if parentInfluence in influenceMapping:
                return influenceMapping[parentInfluence]
            return getParentSource(parentInfluence)
        return None
    for dstInfluence in dstInfluences:
        if dstInfluence not in influenceMapping:
            influenceMapping[dstInfluence] = getParentSource(dstInfluence)

    # Copy skinning using the joint label
    cmds.copySkinWeights(ss=srcCluster, ds=dstCluster, noMirror=True, influenceAssociation='label')


def scaleAnimation(controls, scale):
    """
    Scales control animation.

    Args:
        controls(list[str]): A list of control names.
        scale(float): The global scale.
    """
    for control in controls:
        cmds.scaleKey(
            control, valueScale=scale, valuePivot=0, attribute=['tx', 'ty', 'tz']
        )


def scaleShapes(controls, scale):
    """
    Scales control curves.

    Args:
        controls(list[str]): A list of controls.
        scale(float): The global scale.
    """
    # Gather all control curves
    curves = []
    for control in controls:
        curves.extend(cmds.listRelatives(control, fullPath=True, type='nurbsCurve') or [])

    # Scale all curves
    for curve in curves:
        count = cmds.getAttr('%s.controlPoints' % curve, size=True)
        points = [cmds.getAttr('%s.controlPoints[%s]' % (curve, index))[0] for index in range(count)]
        scaled = [[x * scale for x in point] for point in points]
        for i, point in enumerate(scaled):
            cmds.setAttr('%s.controlPoints[%s]' % (curve, i), point[0], point[1], point[2])

    # Scale all transforms
    # transforms = cmds.listRelatives(group, ad=True, fullPath=True, type='transform') or []
    # for transform in transforms:
    #     for attr in ['tx', 'ty', 'tz']:
    #         attr = '%s.%s' % (transform, attr)
    #         inputs = cmds.listConnections(attr, s=True, d=False) or []
    #         if len(inputs) > 0:
    #             continue
    #         locked = cmds.getAttr(attr, lock=True)
    #         cmds.setAttr(attr, lock=False)
    #         cmds.setAttr(cmds.getAttr(attr) * scale)
    #         cmds.setAttr(attr, lock=locked)
    #
    # # Scale all constraint offsets
    # constraints = cmds.listRelatives(group, ad=True, fullPath=True, type='parentConstraint') or []
    # for constraint in constraints:
    #     targetCount = cmds.getAttr('%s.target' % constraint, size=True)
    #     for i in range(targetCount):
    #         for axis in ['X', 'Y', 'Z']:
    #             currentTarget = '%s.target[%s].targetOffsetTranslate%s' % (constraint, i, axis)
    #             cmds.setAttr(currentTarget, cmds.getAttr(currentTarget) * scale)


def getMeshShape(mesh):
    """
    Gets a mesh shape node.

    Args:
        mesh(str): A mesh node name.

    Returns:
        str: A mesh shape node name.
    """
    if cmds.nodeType(mesh) == 'mesh':
        return mesh
    return cmds.listRelatives(mesh, type='mesh', fullPath=True)[0]


def getSkinCluster(mesh):
    """
    Gets a mesh skin cluster.

    Args:
        mesh(str): A mesh node name.

    Returns:
        str: A skin cluster node name.
    """
    for cluster in cmds.ls(cmds.listHistory(mesh), type='skinCluster'):
        return cluster
    return None


def getMObject(name):
    """
    Wraps a node name as an MObject.

    Args:
        name(str): A node name.

    Returns:
        MObject: A node object.
    """
    sel = om2.MSelectionList()
    sel.add(name)
    return sel.getDependNode(0)


def getInfluences(skinCluster):
    """
    Lists skin cluster influences in order.

    Args:
        skinCluster(str): A skin cluster name.

    Returns:
        dict[int, str]: A mapping of influence indices to influence names.
    """
    # Get skin cluster influences
    skinClusterFn = oma2.MFnSkinCluster(getMObject(skinCluster))
    influences = skinClusterFn.influenceObjects()
    return {skinClusterFn.indexForInfluenceObject(influence): influence.partialPathName() for influence in influences}


def getSkinWeights(mesh):
    """
    Gets skins weights from a mesh.

    Args:
        mesh(str): A mesh node name.

    Returns:
        dict[int, dict[str, float]]: A dictionary of vertex influence weights.
    """
    mesh = getMeshShape(mesh)
    skinCluster = getSkinCluster(mesh)
    influences = getInfluences(skinCluster)
    weightListPlug = om2.MFnDependencyNode(getMObject(skinCluster)).findPlug('weightList', False)

    # Gather skin cluster weights
    weights = {}
    for vertexId in weightListPlug.getExistingArrayAttributeIndices():
        influenceWeights = {}
        weightPlug = weightListPlug.elementByLogicalIndex(vertexId).child(0)
        for influenceIndex in weightPlug.getExistingArrayAttributeIndices():
            infPlug = weightPlug.elementByLogicalIndex(influenceIndex)
            influenceWeights[influences[influenceIndex]] = infPlug.asDouble()
        weights[vertexId] = influenceWeights

    return weights


def setSkinWeights(mesh, weights):
    """
    Sets mesh skin weights.

    Args:
        mesh(str): A mesh node name.
        weights(dict[int, dict[str, float]]): A dictionary of vertex influence weights.
    """
    mesh = getMeshShape(mesh)
    skinCluster = getSkinCluster(mesh)
    influences = getInfluences(skinCluster)
    influenceIndices = {influence: index for index, influence in influences.items()}

    # Prune existing influences
    cmds.setAttr(f'{skinCluster}.normalizeWeights', False)
    cmds.skinPercent(skinCluster, mesh, nrm=False, prw=100)
    cmds.setAttr(f'{skinCluster}.normalizeWeights', True)

    # Apply new weights
    for vertexId, influenceWeights in weights.items():
        for influence, weight in influenceWeights.items():
            influenceId = influenceIndices[influence]
            cmds.setAttr(f'{skinCluster}.weightList[{vertexId}].weights[{influenceId}]', weight)


def scaleRig(meshes, joints, scale):
    """
    Scales skinned meshes.

    Args:
        meshes(list[str]): A list of skinned mesh names.
        joints(list[str]): A list of joint names.
        scale(float): A global scale to apply.
    """

    # Scale each mesh
    meshInfluenceWeights = []
    for mesh in meshes:

        # Save skin weights
        weights = getSkinWeights(mesh)
        influences = [influence for index, influence in getInfluences(getSkinCluster(mesh)).items()]
        meshInfluenceWeights.append((mesh, influences, weights))
        cmds.delete(mesh, ch=True)

        # Scale the mesh
        cmds.xform(mesh, sp=(0.0, 0.0, 0.0), ws=True)
        cmds.xform(mesh, rp=(0.0, 0.0, 0.0), ws=True)
        cmds.xform(mesh, scale=(scale, scale, scale), ws=True)
        cmds.makeIdentity(mesh, scale=True, apply=True)

    # Disconnect and scale the joints
    toConnect = []
    for joint in joints:
        for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']:
            for inputPlug in cmds.listConnections(f'{joint}.{attr}', s=True, plugs=True) or []:
                toConnect.append((inputPlug, f'{joint}.{attr}'))
                cmds.disconnectAttr(inputPlug, f'{joint}.{attr}')
        for attr in ['tx', 'ty', 'tz']:
            cmds.setAttr(f'{joint}.{attr}', cmds.getAttr(f'{joint}.{attr}') * scale)
        cmds.setAttr(f'{joint}.radius', cmds.getAttr(f'{joint}.radius') * scale)

    # Load skin weights
    for mesh, influences, weights in meshInfluenceWeights:
        cmds.skinCluster(mesh, influences)
        setSkinWeights(mesh, weights)

    # Reconnect
    for srcPlug, dstPlug in toConnect:
        cmds.connectAttr(srcPlug, dstPlug)


def scaleMesh(mesh, scale):
    """
    Scales a skinned mesh.

    Args:
        mesh(str): A mesh name.
        scale(float): The global scale.
    """
    # Don't scale if the scale is identity
    if scale == 1.0:
        return
    if scale < 0.001:
        raise ValueError('Scale is too small.')

    # Find the skin cluster and influences
    skinCluster = cmds.ls(cmds.listHistory(mesh), type='skinCluster')[0]
    influences = cmds.skinCluster(skinCluster, inf=True, q=True)
    influences = sorted(influences, key=lambda joint: len(cmds.listRelatives(joint, ad=True) or []), reverse=True)
    skeleton = [influences[0]] + cmds.listRelatives(influences[0], ad=True, type='joint') or []
    skeleton = sorted(skeleton, key=lambda joint: len(cmds.listRelatives(joint, ad=True) or []), reverse=True)

    def getMObject(node):
        sel = om2.MSelectionList()
        sel.add(node)
        return sel.getDependNode(0)

    def getDagPath(node):
        sel = om2.MSelectionList()
        sel.add(node)
        return sel.getDagPath(0)

    # Scale each joints matrix
    fnSkinCluster = oma2.MFnSkinCluster(getMObject(skinCluster))
    for joint in skeleton:
        position = om2.MVector(cmds.xform(joint, t=True, os=True, q=True))
        position *= scale
        cmds.xform(joint, t=list(position), os=True)

        # Update scale for visibility sake
        cmds.setAttr(f'{joint}.radius', cmds.getAttr(f'{joint}.radius') * scale)

        # Determine the joint index
        if joint in influences:
            index = fnSkinCluster.indexForInfluenceObject(getDagPath(joint))
            matrix = om2.MMatrix(cmds.xform(joint, m=True, ws=True, q=True))
            cmds.setAttr('%s.bindPreMatrix[%s]' % (skinCluster, index), list(matrix.inverse()), type='matrix')

    # Scale the mesh
    for attr in ['sx', 'sy', 'sz']:
        cmds.setAttr(f'{mesh}.{attr}', lock=False)
        cmds.setAttr(f'{mesh}.{attr}', scale)
        cmds.setAttr(f'{mesh}.{attr}', lock=True)


def fixMissingBoneOrders():
    """
    If a bone order number is missing, ckcmd might error.
    This function ensures all bone order attributes have consecutive values.
    """

    # Get all bone order attrs in the scene
    orders = []
    for attr in cmds.ls('*.bone_order'):
        orders.append((attr, cmds.getAttr(attr)))

    # Sort the orders and set them equal to their index
    orders = sorted(orders, key=lambda attr_order: attr_order[1])
    for i, (attr, order) in enumerate(orders):
        cmds.setAttr(attr, i)


def exportRig():
    """
    Exports the scene export skeleton as an hkx.
    """

    # Get the project
    project = ckproject.getProject()

    # Get destination path
    path = project.getExportSkeletonHkx()
    if path == '':
        raise Exception('Invalid skeleton path "%s"' % path)
    path = path.split('.')[0] + '.fbx'

    # Get the export skeleton
    exportRootJoint = getRootJoint()
    exportSkeleton = getSkeleton(exportRootJoint)

    try:
        cmds.undoInfo(openChunk=True)
        toExport = exportSkeleton

        # Remove all joint constraints
        constraints = cmds.listRelatives(exportRootJoint, ad=True, type='constraint') or []
        if len(constraints) > 0:
            cmds.delete(constraints)

        # Disconnect message connections
        for joint in exportSkeleton:

            # Delete output message connections
            messagePlug = '%s.message' % joint
            for outputPlug in cmds.listConnections(messagePlug, s=False, d=True, plugs=True) or []:
                cmds.disconnectAttr(messagePlug, outputPlug)

            # Delete input message connections
            for dstPlug in cmds.listAttr(joint, userDefined=True) or []:
                dstPlug = '%s.%s' % (joint, dstPlug)
                if cmds.getAttr(dstPlug, type=True) == 'message':
                    for srcPlug in cmds.listConnections(dstPlug, s=True, d=False, plugs=True) or []:
                        cmds.disconnectAttr(srcPlug, dstPlug)

        # Check for gaps in bone orders
        fixMissingBoneOrders()

        # Remove Keyframes
        cmds.cutKey(exportRootJoint, clear=True)

        # Export the mesh as an fbx
        exportFbx(toExport, path=path)

        # Export nif
        ckcmd.importrig(path, os.path.dirname(path))

        # If the export skeleton nif is in a different directory, copy it there
        nifPath = project.getExportSkeletonNif()
        exportNifPath = os.path.join(os.path.dirname(path), 'skeleton.nif')
        if os.path.normpath(exportNifPath) != os.path.normpath(nifPath):
            shutil.copyfile(exportNifPath, nifPath)

    finally:
        if not cmds.undoInfo(undoQueueEmpty=True, q=True):
            cmds.undoInfo(closeChunk=True)
            cmds.undo()
        else:
            cmds.undoInfo(closeChunk=True)


def exportSkin():
    """
    Exports the project mesh as a skyrim skin fbx.

    Returns:
        str: The exported file path.
    """

    # Get the project
    project = ckproject.getProject()

    # Get mesh to export
    mesh = project.getExportMeshName()
    if not cmds.objExists(mesh):
        raise Exception('Project mesh "%s" is not unique or does not exist' % mesh)

    meshes = cmds.listRelatives(mesh, type='mesh', fullPath=True, ad=True) or []
    meshes = [mesh for mesh in meshes if getSkinCluster(mesh) is not None]
    # meshes = [cmds.listRelatives(mesh, parent=True, fullPath=True)[0] for mesh in meshes]
    meshes = list(set(meshes))

    # Get destination path
    path = project.getExportSkinNif()
    if path == '':
        raise Exception('Invalid skin path "%s"' % path)
    path = path.split('.')[0] + '.fbx'

    # Get the export skeleton
    exportRootJoint = getRootJoint()
    exportSkeleton = getSkeleton(exportRootJoint)

    # Validate meshes
    for mesh in meshes:
        # Check if not triangulated
        sel = om2.MSelectionList()
        sel.add(mesh)
        fnMesh = om2.MFnMesh(sel.getDependNode(0))
        for id in range(fnMesh.numPolygons):
            if len(fnMesh.getPolygonVertices(id)) > 3:
                raise Exception('%s.f[%s] is not triangulated' % (mesh, id))

        # Check the mesh is skinned
        cluster = getSkinCluster(mesh)
        if cluster is None:
            raise Exception('%s is not skinned.' % mesh)

        # Check for skinned rigid body joints
        influences = cmds.skinCluster(cluster, inf=True, q=True)
        rbInfluences = []
        for influence in influences:
            if influence.endswith('_rb'):
                rbInfluences.append(influence)
        if len(rbInfluences) > 0:
            raise Exception('"%s" is skinned to rigid body joints: [%s]' %
                            (mesh.split('|')[-1], ', '.join(rbInfluences)))

        # Check max influences
        vertices = cmds.polyListComponentConversion(mesh, toVertex=True)
        vertices = cmds.filterExpand(vertices, selectionMask=31)  # polygon vertex
        failedVertices = []
        for vert in vertices:
            joints = cmds.skinPercent(cluster, vert, query=True, ignoreBelow=0.000001, transform=None) or []
            if len(joints) > 4:  # Skyrim max influences
                failedVertices.append(vert)
        if len(failedVertices) > 0:
            raise Exception('Vertices have more than 4 influences: %s.' % failedVertices)

    try:
        cmds.undoInfo(openChunk=True)
        toExport = exportSkeleton

        for mesh in meshes:
            toExport.append(cmds.listRelatives(mesh, parent=True, fullPath=True)[0])

            # Remove unused influences
            cluster = getSkinCluster(mesh)
            influences = cmds.skinCluster(cluster, q=True, inf=True)
            weighted = cmds.skinCluster(cluster, q=True, wi=True)
            unused = [inf for inf in influences if inf not in weighted]
            cmds.skinCluster(cluster, e=True, removeInfluence=unused)

            # Set vertex colors to white
            cmds.polyColorPerVertex(mesh, colorRGB=[1, 1, 1], a=1)

            # To fix certain issues with skinning we need to mess with the normals
            # cmds.bakePartialHistory(mesh, prePostDeformers=True)  # Delete Non-deformer history
            # cmds.polyNormalPerVertex(mesh, unFreezeNormal=True)  # Unlock the normals
            # cmds.polySoftEdge(mesh, a=180)  # Soften the normals
            # cmds.bakePartialHistory(mesh, prePostDeformers=True)  # Delete Non-deformer history
            # cmds.polyNormalPerVertex(mesh, freezeNormal=True)  # Lock the normals
            # cmds.polySoftEdge(mesh, a=0)  # Harden the normals
            # cmds.bakePartialHistory(mesh, prePostDeformers=True)  # Delete Non-deformer history

        # Remove all joint constraints
        constraints = cmds.listRelatives(exportRootJoint, ad=True, type='constraint') or []
        if len(constraints) > 0:
            cmds.delete(constraints)

        # Disconnect message connections
        for joint in exportSkeleton:
            messagePlug = '%s.message' % joint
            for outputPlug in cmds.listConnections(messagePlug, s=True, d=False) or []:
                cmds.disconnectAttr(messagePlug, outputPlug)

        # Prune influences below 0.1
        # for mesh in meshes:
        #     cmds.skinPercent(getSkinCluster(mesh), pruneWeights=0.1)

        # Export the mesh as an fbx
        exportFbx(toExport, path=path)

        # Export nif
        ckcmd.importskin(path, os.path.dirname(path))

        # Apply nif patch
        filepath = path.replace('.fbx', '.nif')
        data = cknif.loadNif(filepath)
        cknif.fixNifMeshes(data, meshes)
        for mesh in meshes:
            textures = getTextures(mesh)
            textures = {name: exportTexture(texture) for name, texture in textures.items()}
            textures = {name: ckproject.getProject().getExportPath(texture) for name, texture in textures.items()}
            textures = {name: texture for name, texture in textures.items()}
            cknif.setMeshTextures(data, mesh, **textures)
        cknif.saveNif(data, filepath)

    finally:
        cmds.undoInfo(closeChunk=True)
        cmds.undo()


def exportPackage():
    """
    Copies all export filetypes to each package directory.

    Returns:
        int: The number of files exported.
    """

    # Gather files to export
    exportDirectory = os.path.normpath(ckproject.getProject().getExportDirectory()) + '\\'
    exportFiles = []
    for root, dirs, files in os.walk(exportDirectory):
        for filename in files:
            if any([filename.endswith(extension) for extension in ['.hkx', '.nif', '.esp', '.dds', '.txt']]):
                exportFiles.append(os.path.join(root, filename).replace(exportDirectory, ''))

    # Copy files
    for path in exportFiles:
        srcPath = os.path.join(exportDirectory, path)
        for packagePath in ckproject.getProject().getExportPackageDirectories():
            dstPath = os.path.join(packagePath, path)
            if not os.path.exists(os.path.dirname(dstPath)):
                os.makedirs(os.path.dirname(dstPath))
            shutil.copyfile(srcPath, dstPath)

    return len(exportFiles)


class FbxException(BaseException):
    """ Raised to indicate an invalid fbx file. """

