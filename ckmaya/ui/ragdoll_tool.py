""" A tool for creating CK ragdolls. """

import os
import math
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


CK_MAYA_DIR = os.path.dirname(os.path.dirname(__file__)).replace('\\', '/')
VLINE_ICON = os.path.join(CK_MAYA_DIR, 'icons', 'stylesheet-vline.png').replace('\\', '/')
BRANCH_MORE_ICON = os.path.join(CK_MAYA_DIR, 'icons', 'stylesheet-branch-more.png').replace('\\', '/')
BRANCH_END_ICON = os.path.join(CK_MAYA_DIR, 'icons', 'stylesheet-branch-end.png').replace('\\', '/')
BRANCH_CLOSED_ICON = os.path.join(CK_MAYA_DIR, 'icons', 'stylesheet-branch-closed.png').replace('\\', '/')
BRANCH_OPEN_ICON = os.path.join(CK_MAYA_DIR, 'icons', 'stylesheet-branch-open.png').replace('\\', '/')


class NodeWidget(QtWidgets.QWidget):

    nodeChanged = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(NodeWidget, self).__init__(parent)
        self._node = None

    def setNode(self, node):
        self._node = node
        self.onNodeChanged(node)
        self.nodeChanged.emit(node)

    def onNodeChanged(self, node):
        return

    def node(self):
        return self._node


class RigidBodyWidget(NodeWidget):

    def __init__(self, parent=None):
        super(RigidBodyWidget, self).__init__(parent)

        layout = QtWidgets.QFormLayout()
        self.setLayout(layout)


class AttachmentWidget(NodeWidget):

    def __init__(self, parent=None):
        super(AttachmentWidget, self).__init__(parent)


class CapsuleWidget(NodeWidget):

    def __init__(self, parent=None):
        super(CapsuleWidget, self).__init__(parent)


class CustomTreeWidget(QtWidgets.QTreeWidget):

    ICON_SIZE = QtCore.QSize(20, 20)
    ANCHOR_SIZE = QtCore.QSize(20, 20)
    BOX_SIZE = QtCore.QSize(7, 7)
    DOT_SIZE = QtCore.QSize(3, 3)
    COLOR = QtGui.QColor(147, 147, 147)

    def drawBranches(self, painter, rect, index):

        def getParents(index):
            parents = []
            if index.parent().isValid():
                parents.append(index.parent())
                parents.extend(getParents(index.parent()))
            return parents

        childCount = index.model().rowCount(index)
        parents = getParents(index)
        hierarchy = [index] + parents
        parentCount = len(parents)
        isExpanded = self.isExpanded(index)
        rect.setLeft(rect.right() - self.ANCHOR_SIZE.width())

        def isLastSibling(index):
            return index.model().rowCount(index.parent()) == index.row() + 1

        if childCount == 0 and parentCount > 0:
            self.drawDot(painter, rect, index)
        elif childCount > 0:
            self.drawBox(painter, rect, index, closed=not isExpanded)

        painter.setPen(self.COLOR)
        for childIndex, parentIndex in zip(hierarchy[:-1], hierarchy[1:]):
            rect.moveLeft(rect.left() - self.ANCHOR_SIZE.width())
            isLast = isLastSibling(childIndex)
            self.drawLines(painter, rect, top=childIndex == index or not isLast,
                           bottom=not isLast, right=childIndex == index)

        return True

    def drawLines(self, painter, rect, top=False, bottom=False, right=False):
        painter.save()
        painter.setPen(self.COLOR)
        if top:
            painter.drawLine(
                QtCore.QPoint(rect.center().x(), rect.top()),
                QtCore.QPoint(rect.center().x(), rect.center().y())
            )
        if bottom:
            painter.drawLine(
                QtCore.QPoint(rect.center().x(), rect.center().y()),
                QtCore.QPoint(rect.center().x(), rect.bottom())
            )
        if right:
            painter.drawLine(
                QtCore.QPoint(rect.center().x(), rect.center().y()),
                QtCore.QPoint(rect.right(), rect.center().y())
            )
        painter.restore()

    def drawBox(self, painter, rect, index, closed=True):

        painter.save()

        painter.setPen(self.COLOR)

        marginV = (self.ANCHOR_SIZE.height() - self.BOX_SIZE.height()) / 2
        marginH = (self.ANCHOR_SIZE.width() - self.BOX_SIZE.width()) / 2
        box = QtCore.QRect(
            QtCore.QPoint(rect.right() - self.BOX_SIZE.width() - marginH, rect.top() + marginV - 1),
            QtCore.QPoint(rect.right() - marginH, rect.top() + self.BOX_SIZE.width() + marginV - 1)
        )

        painter.drawLine(
            QtCore.QPoint(box.left() + 2, box.center().y() + 1),
            QtCore.QPoint(box.right() - 1, box.center().y() + 1)
        )
        if closed:
            painter.drawLine(
                QtCore.QPoint(box.center().x() + 1, box.top() + 2),
                QtCore.QPoint(box.center().x() + 1, box.bottom() - 1)
            )

        painter.drawRect(box)

        if index.parent().isValid():
            painter.drawLine(
                QtCore.QPoint(rect.left(), rect.center().y()),
                QtCore.QPoint(box.left(), rect.center().y())
            )
        if not closed:
            painter.drawLine(
                QtCore.QPoint(rect.center().x(), box.bottom() + 1),
                QtCore.QPoint(rect.center().x(), rect.bottom())
            )

        painter.restore()
        return box

    def drawDot(self, painter, rect, index):
        painter.save()

        marginV = (self.ANCHOR_SIZE.height() - self.DOT_SIZE.height()) / 2
        marginH = (self.ANCHOR_SIZE.width() - self.DOT_SIZE.width()) / 2
        box = QtCore.QRect(
            QtCore.QPoint(rect.right() - self.DOT_SIZE.width() - marginH, rect.top() + marginV - 1),
            QtCore.QPoint(rect.right() - marginH, rect.top() + self.DOT_SIZE.width() + marginV - 1)
        )

        painter.setBrush(self.COLOR)
        painter.setPen(self.COLOR)
        painter.drawEllipse(box)
        painter.restore()

        painter.save()
        painter.setPen(self.COLOR)
        if index.parent().isValid():
            painter.drawLine(
                QtCore.QPoint(rect.left(), rect.center().y()),
                QtCore.QPoint(box.left(), rect.center().y())
            )
        painter.restore()

        return box



class RagdollSettings(NodeWidget):

    def __init__(self, parent=None):
        super(RagdollSettings, self).__init__(parent=parent)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.rbWidget = RigidBodyWidget(self)
        self.nodeChanged.connect(self.rbWidget.setNode)
        layout.addWidget(self.rbWidget)
        self.capsuleWidget = CapsuleWidget(self)
        self.nodeChanged.connect(self.capsuleWidget.setNode)
        layout.addWidget(self.capsuleWidget)
        self.attachmentWidget = AttachmentWidget(self)
        self.nodeChanged.connect(self.attachmentWidget.setNode)
        layout.addWidget(self.attachmentWidget)



class RagdollList(QtWidgets.QWidget):
    """ A list of all ragdolls in the scene """

    CYLINDER_ICON = QtGui.QIcon('://out_polyCylinder.png')
    JOINT_ICON = QtGui.QIcon('://out_joint.png')
    MESH_ICON = QtGui.QIcon('://out_mesh.png')
    TRANSFORM_ICON = QtGui.QIcon('://out_transform.png')

    def __init__(self, parent=None):
        super(RagdollList, self).__init__(parent)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.listWidget = CustomTreeWidget(self)
        self.listWidget.header().hide()
        self.listWidget.setIconSize(QtCore.QSize(20, 20))
        layout.addWidget(self.listWidget)

        self.updateList()
        self.callbacks = []

    def updateList(self):
        """ Updates list with ragdolls in the scene. """
        self.listWidget.clear()

        attached = set()
        for rigidbody in ckphysics.getSceneRigidbodies():
            for attachment in ckphysics.getAttachments(rigidbody):
                attached.add(ckphysics.getAttachmentDestination(attachment))

        for rigidbody in ckphysics.getSceneRigidbodies():
            if rigidbody not in attached:
                self.addRigidBodyItem(rigidbody)

    def addRigidBodyItem(self, rigidbody, parent=None):

        rbItem = self.addItem(ckphysics.toCkName(rigidbody), node=rigidbody, icon=self.JOINT_ICON, parent=parent)

        capsule = ckphysics.getCapsule(rigidbody)
        if capsule is not None:
            self.addItem(ckphysics.toCkName(capsule), node=capsule, icon=self.MESH_ICON, parent=rbItem)

        for attachment in ckphysics.getAttachments(rigidbody):
            attachmentItem = self.addItem(
                ckphysics.toCkName(attachment), node=attachment, icon=self.TRANSFORM_ICON,
                color=None if ckphysics.isValidAttachment(attachment) else QtGui.QColor(200, 72, 72), parent=rbItem
            )
            if ckphysics.isValidAttachment(attachment):
                self.addRigidBodyItem(ckphysics.getAttachmentDestination(attachment), parent=attachmentItem)

    def addItem(self, name, node=None, icon=None, color=None, parent=None):
        item = QtWidgets.QTreeWidgetItem(parent or self.listWidget)
        item.setText(0, name)
        if node is not None:
            item.setData(0, QtCore.Qt.UserRole, node)
        if icon is not None:
            item.setIcon(0, icon)
        item.setSizeHint(0, QtCore.QSize(0, 20))
        if color:
            item.setData(0, QtCore.Qt.ForegroundRole, QtGui.QBrush(color))
        return item

    def removeCallbacks(self):
        om2.MMessage.removeCallbacks(self.callbacks)


class RagdollWindow(MayaWindow):
    """ The main ragdoll tool window. """

    def __init__(self):
        super(RagdollWindow, self).__init__()
        self.setWindowTitle('Ragdoll Tool')

        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Vertical)
        self.getMainLayout().addWidget(splitter)

        self.ragdollList = RagdollList(self)
        splitter.addWidget(self.ragdollList)

    def closeEvent(self, event):
        self.ragdollList.removeCallbacks()
        return super(RagdollWindow, self).closeEvent(event)


def load():
    RagdollWindow.load()