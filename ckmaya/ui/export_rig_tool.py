""" Tool for creating exporting skins. """

import os
import shutil
from functools import partial
# Export each scene
import contextlib
from maya import cmds
import maya.api.OpenMaya as om2
from .core import ProjectModel, ProjectDataWidget
from ..core import ckproject, ckcore, ckphysics
from ..core.ckproject import ProjectDataKey
from ..ui.core import MayaWindow, getDirectoryDialog, getFileDialog, getNameDialog, saveChangesDialog, \
    replaceFileDialog, getFilesDialog, errorDecorator
from ..thirdparty.Qt import QtWidgets, QtGui, QtCore


class ExportRigWindow(MayaWindow):
    """ The export skin window. """

    def __init__(self):
        super(ExportRigWindow, self).__init__()
        self.setWindowTitle('Export Rig Tool')
        self.getMainLayout().setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)
        self.setMinimumWidth(300)

        # Project model
        self._model = ProjectModel(self)

        # Settings
        settingGroup = QtWidgets.QGroupBox('Settings', self)
        self.getMainLayout().addWidget(settingGroup)
        settingLayout = QtWidgets.QVBoxLayout()
        settingGroup.setLayout(settingLayout)

        # Export directory
        settingLayout.addWidget(ProjectDataWidget(ckproject.ProjectDataKey.skeletonSceneFile, self._model, parent=self))
        settingLayout.addWidget(ProjectDataWidget(ckproject.ProjectDataKey.exportSkeletonHkx, self._model, parent=self))
        settingLayout.addWidget(ProjectDataWidget(ckproject.ProjectDataKey.exportSkeletonNif, self._model, parent=self))
        settingLayout.addWidget(ProjectDataWidget(ckproject.ProjectDataKey.exportJointName, self._model, parent=self))

        # Export button
        self.exportButton = QtWidgets.QPushButton('Export', parent=self)
        self.exportButton.setFixedHeight(40)
        self.exportButton.pressed.connect(self.exportPressed)
        self.getMainLayout().addWidget(self.exportButton)

    @errorDecorator
    def exportPressed(self):
        """ Exports the project as a package. """
        try:
            ckcore.exportRig()
            ckcore.exportPackage()
        finally:
            self.exportButton.setDown(False)


def load():
    ExportRigWindow.load()