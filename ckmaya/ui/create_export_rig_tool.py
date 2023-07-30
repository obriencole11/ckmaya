""" Tool for creating an export rig. """

import os
import shutil
from functools import partial
# Export each scene
import contextlib
from maya import cmds
import maya.api.OpenMaya as om2
from ..core import ckproject, ckcore, ckphysics
from ..ui.core import MayaWindow, getDirectoryDialog, getFileDialog, getNameDialog, saveChangesDialog, \
    replaceFileDialog, getFilesDialog
from ..thirdparty.Qt import QtWidgets, QtGui, QtCore


@contextlib.contextmanager
def undo():
    try:
        cmds.undoInfo(openChunk=True)
        yield
    finally:
        cmds.undoInfo(closeChunk=True)
        cmds.refresh(force=True)


class ExportRigWindow(MayaWindow):
    """ The main export rig tool window. """

    def __init__(self):
        super(ExportRigWindow, self).__init__()
        self.setWindowTitle('Export Rig Tool')
        self.getMainLayout().setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)

        # Create buttons
        self._addButton = QtWidgets.QPushButton('Add Export Joint', parent=self)
        self._addButton.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self._addButton.setMinimumHeight(32)
        self._addButton.pressed.connect(self.addExportJoint)
        self.getMainLayout().addWidget(self._addButton)

        self._addHierarchyButton = QtWidgets.QPushButton('Add Export Joint Hierarchy', parent=self)
        self._addHierarchyButton.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self._addHierarchyButton.setMinimumHeight(32)
        self._addHierarchyButton.pressed.connect(self.addExportJointHierarchy)
        self.getMainLayout().addWidget(self._addHierarchyButton)

        self._connectButton = QtWidgets.QPushButton('Connect Export Joint', parent=self)
        self._connectButton.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self._connectButton.setMinimumHeight(32)
        self._connectButton.pressed.connect(self.connectExportJoint)
        self.getMainLayout().addWidget(self._connectButton)

        # Edit widget
        self._meshButton = QtWidgets.QPushButton('Create Export Mesh', parent=self)
        self._meshButton.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self._meshButton.setMinimumHeight(32)
        self._meshButton.pressed.connect(self.createExportMesh)
        self.getMainLayout().addWidget(self._meshButton)

    def addExportJointHierarchy(self):
        try:
            with undo():
                # Get selected joints
                joints = cmds.ls(type='joint', sl=True, long=True) or []
                joints = [joint for joint in joints if not joint.endswith('_rb')]
                if len(joints) == 0:
                    return cmds.warning('Not enough joints selected.')

                # Determine which joint is the export joint and which is the rig joint
                rigJoints = []
                exportJoint = None
                exportJointName = ckproject.getProject().getExportJointName()
                for joint in joints:
                    if exportJointName in joint:
                        exportJoint = joint
                    else:
                        rigJoints.append(joint)
                if exportJoint is None:
                    return cmds.warning('Could not find a single export joint for selected joints.')

                # Make the connect
                for rigJoint in rigJoints:
                    ckcore.addExportJointHierarchy(rigJoint, exportJoint)

        finally:
            self._connectButton.setDown(False)

    def addExportJoint(self):
        try:
            with undo():
                # Get selected joints
                joints = cmds.ls(type='joint', sl=True, long=True) or []
                joints = [joint for joint in joints if not joint.endswith('_rb')]
                if len(joints) == 0:
                    return cmds.warning('Not enough joints selected.')

                # Determine which joint is the export joint and which is the rig joint
                rigJoints = []
                exportJoint = None
                exportJointName = ckproject.getProject().getExportJointName()
                for joint in joints:
                    if exportJointName in joint:
                        exportJoint = joint
                    else:
                        rigJoints.append(joint)
                if exportJoint is None:
                    return cmds.warning('Could not find a single export joint for selected joints.')

                # Make the connect
                for rigJoint in rigJoints:
                    ckcore.addExportJoint(rigJoint, exportJoint)

        finally:
            self._connectButton.setDown(False)

    def connectExportJoint(self):
        try:
            with undo():
                # Get selected joints
                joints = cmds.ls(type='joint', sl=True, long=True) or []
                joints = [joint for joint in joints if not joint.endswith('_rb')]
                if len(joints) == 0:
                    return cmds.warning('Not enough joints selected.')
                if len(joints) > 2:
                    return cmds.warning('Too many joints selected.')

                # Determine which joint is the export joint and which is the rig joint
                rigJoint = None
                exportJoint = None
                exportJointName = ckproject.getProject().getExportJointName()
                for joint in joints:
                    if exportJointName in joint:
                        exportJoint = joint
                    else:
                        rigJoint = joint
                if exportJoint is None or rigJoint is None:
                    return cmds.warning('Could not find a single export joint for selected joints.')

                # Make the connect
                ckcore.connectExportJoint(rigJoint, exportJoint)

        finally:
            self._connectButton.setDown(False)

    def createExportMesh(self):
        try:
            with undo():
                meshes = []
                for transform in cmds.ls(sl=True):
                    for mesh in cmds.listRelatives(transform, type='mesh', fullPath=True) or []:
                        meshes.append(transform)
                        break
                if len(meshes) == 0:
                    return cmds.warning('Not enough meshes selected.')
                for mesh in meshes:
                    ckcore.createExportMesh(mesh)
        finally:
            self._connectButton.setDown(False)


def load():
    ExportRigWindow.load()