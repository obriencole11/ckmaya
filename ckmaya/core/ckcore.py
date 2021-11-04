import os
import shutil

from ckmaya.core import ckcmd
from ckmaya.core import ckproject
import maya.api.OpenMaya as om2
from maya import cmds, mel


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

