""" A tool for creating CK physics objects. """

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


class CreateRigidBodyWidget(QtWidgets.QGroupBox):
    """ A widget for creating rigid bodies """

    def __init__(self, parent=None):
        super(CreateRigidBodyWidget, self).__init__('Create', parent=parent)

        # Layout
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Create button
        self._create_button = QtWidgets.QPushButton('Create Capsule', parent=self)
        self._create_button.released.connect(self.createCapsule)
        layout.addWidget(self._create_button)

        # Delete button
        self._delete_button = QtWidgets.QPushButton('Delete Capsule', parent=self)
        self._delete_button.released.connect(self.deleteCapsule)
        layout.addWidget(self._delete_button)

    def createCapsule(self):
        try:
            with undo():
                # Find a selected joint
                joints = cmds.ls(type='joint') or []
                if len(joints) == 0:
                    return cmds.warning('No joints selected.')

                # Create a capsule for each joint
                for joint in joints:
                    name = joint.split('|')[-1]
                    radius = cmds.getAttr(f'{joint}.radius')
                    rb_joint = ckphysics.createRigidBody(name, radius=radius)
                    cmds.parent(rb_joint, joint)
                    cmds.xform(rb_joint, m=cmds.xform(joint, m=True, ws=True, q=True), ws=True)
        finally:
            self._create_button.setDown(False)

    def deleteCapsule(self):
        try:
            with undo():
                joint = ckphysics.getSelectedRigidBody()
                if joint is not None:
                    cmds.delete(joint)
        finally:
            self._create_button.setDown(False)


class EditRigidBodyWidget(QtWidgets.QGroupBox):
    """ A widget for editing rigid bodies """

    def __init__(self, parent=None):
        super(EditRigidBodyWidget, self).__init__('Edit', parent=parent)
        self._rigidBody = None

        # Layout
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Add Selection Label
        self._label = QtWidgets.QLabel(parent=self)
        layout.addWidget(self._label)

        # Setting Layout
        settingLayout = QtWidgets.QFormLayout()
        layout.addLayout(settingLayout)

        # Float validator
        validator = QtGui.QDoubleValidator(parent=self)
        validator.setBottom(0.0)
        validator.setDecimals(3)

        # Height Box
        self._heightBox = QtWidgets.QLineEdit(parent=self)
        self._heightBox.setValidator(validator)
        self._heightBox.editingFinished.connect(self._onHeightChanged)
        settingLayout.addRow('Height', self._heightBox)

        # Radius Box
        self._radiusBox = QtWidgets.QLineEdit(parent=self)
        self._radiusBox.setValidator(validator)
        self._radiusBox.editingFinished.connect(self._onRadiusChanged)
        settingLayout.addRow('Radius', self._radiusBox)

        # Aim Button
        self._aimButton = QtWidgets.QPushButton('Aim Capsule', parent=self)
        self._aimButton.pressed.connect(self.aimCapsule)
        layout.addWidget(self._aimButton)

        # Node Callback
        self._callbacks = []
        self._waiting = False

    def removeCallbacks(self):
        if len(self._callbacks) > 0:
            om2.MMessage.removeCallbacks(self._callbacks)
        self._callbacks = []

    def aimCapsule(self):

        # Get the selected transforms
        selection = cmds.ls(type='transform') or []
        if len(selection) == 0:
            return cmds.warning('No valid targets selected.')

        # Prune transforms at the same position as the rigid body joint
        rigidBodyPosition = om2.MVector(cmds.xform(self._rigidBody, t=True, q=True, ws=True))
        target = None
        for node in selection:
            targetPosition = om2.MVector(cmds.xform(node, t=True, q=True, ws=True))
            if (targetPosition - rigidBodyPosition).length() > 0.01:
                target = node
                break
        if target is None:
            return cmds.warning('No valid targets selected.')

        # Aim the capsule
        with undo():
            ckphysics.aimCapsule(ckphysics.getCapsule(self._rigidBody), target)

    def _onMeshChanged(self, messageType, plug, otherPlug, _):
        if messageType & om2.MNodeMessage.kAttributeEval:
            if 'outMesh' in plug.name() and not self._waiting:
                cmds.evalDeferred(self.updateRigidBody)
                self._waiting = True

    def _onHeightChanged(self):
        if self._rigidBody is None or not cmds.objExists(self._rigidBody):
            return
        with undo():
            ckphysics.updateCapsule(
                ckphysics.getCapsule(self._rigidBody),
                radius=float(self._radiusBox.text()),
                height=float(self._heightBox.text())
            )
        self.updateRigidBody()

    def _onRadiusChanged(self):
        if self._rigidBody is None or not cmds.objExists(self._rigidBody):
            return
        with undo():
            ckphysics.updateCapsule(
                ckphysics.getCapsule(self._rigidBody),
                radius=float(self._radiusBox.text())
            )
        self.updateRigidBody()

    def updateRigidBody(self):
        """ Updates the UI with a new rigidbody. """
        self._waiting = False
        self.removeCallbacks()
        self._rigidBody = ckphysics.getSelectedRigidBody()
        self._label.setText('<b>Rigid Body:</b> %s' % str(self._rigidBody).split('|')[-1])

        if self._rigidBody is None:
            self._heightBox.setText('0.0')
            self._heightBox.setEnabled(False)
            self._radiusBox.setText('0.0')
            self._radiusBox.setEnabled(False)
        else:
            self._heightBox.setText(str(round(ckphysics.getCapsuleHeight(self._rigidBody), 3)))
            self._heightBox.setEnabled(True)
            self._radiusBox.setText(str(round(ckphysics.getCapsuleRadius(self._rigidBody), 3)))
            self._radiusBox.setEnabled(True)

            for node in cmds.listRelatives(ckphysics.getCapsule(self._rigidBody), fullPath=True, type='mesh') or []:
                sel = om2.MSelectionList()
                sel.add(node)
                node = sel.getDependNode(0)
                self._callbacks.append(om2.MNodeMessage.addAttributeChangedCallback(
                    node, self._onMeshChanged
                ))


class PhysicsWindow(MayaWindow):
    """ The main physics tool window. """

    def __init__(self):
        super(PhysicsWindow, self).__init__()
        self.setWindowTitle('Physics Tool')

        # Create widget
        self._createWidget = CreateRigidBodyWidget(parent=self)
        self.getMainLayout().addWidget(self._createWidget)

        # Edit widget
        self._editWidget = EditRigidBodyWidget(parent=self)
        self.getMainLayout().addWidget(self._editWidget)

        # Create a call back listening to the selection
        self._editWidget.updateRigidBody()
        self._callback = om2.MEventMessage.addEventCallback('SelectionChanged', self.onSelectionChanged)

    def onSelectionChanged(self, *args):
        cmds.evalDeferred(self._editWidget.updateRigidBody)

    def closeEvent(self, event):
        om2.MMessage.removeCallback(self._callback)
        self._editWidget.removeCallbacks()
        return super(PhysicsWindow, self).closeEvent(event)


def load():
    PhysicsWindow.load()