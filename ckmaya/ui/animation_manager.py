""" Tool for managing animations. """

import os
import shutil
from functools import partial
# Export each scene
import contextlib
from maya import cmds
import maya.api.OpenMaya as om2
from .core import ProjectModel, ProjectDataWidget, ProjectDirectoryWidget, ProjectWindow
from ..core import ckproject, ckcore, ckphysics
from ..core.ckproject import ProjectDataKey
from ..ui.core import MayaWindow, getDirectoryDialog, getFileDialog, getNameDialog, saveChangesDialog, \
    replaceFileDialog, getFilesDialog
from ..thirdparty.Qt import QtWidgets, QtGui, QtCore


class AnimationManager(ProjectWindow):
    """ The animation manager window. """

    def __init__(self):
        super(AnimationManager, self).__init__()
        self.setWindowTitle('Animation Manager')
        self.getContentLayout().setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)
        self.setMinimumWidth(300)

        # Settings
        settingGroup = QtWidgets.QGroupBox('Settings', self)
        self.getContentLayout().addWidget(settingGroup)
        settingLayout = QtWidgets.QVBoxLayout()
        settingGroup.setLayout(settingLayout)

        # Export directory
        settingLayout.addWidget(ProjectDataWidget(ckproject.ProjectDataKey.exportAnimationSkeletonHkx,
                                                  self.getModel(), parent=self))
        settingLayout.addWidget(ProjectDataWidget(ckproject.ProjectDataKey.exportAnimationDir, self.getModel(),
                                                  parent=self))
        settingLayout.addWidget(ProjectDataWidget(ckproject.ProjectDataKey.animationSceneDir, self.getModel(), parent=self))

        # Animation widget
        self.animationList = ProjectDirectoryWidget(ckproject.ProjectDataKey.animationSceneDir, self.getModel(), parent=self)
        self.getContentLayout().addWidget(self.animationList)

        # Export Button Layout
        exportButtonLayout = QtWidgets.QHBoxLayout()
        self.getContentLayout().addLayout(exportButtonLayout)

        # Export Selected
        self.exportSelectedButton = QtWidgets.QPushButton('Export Selected', self)
        self.exportSelectedButton.pressed.connect(self.exportSelected)
        exportButtonLayout.addWidget(self.exportSelectedButton)

        # Export All
        self.exportAllButton = QtWidgets.QPushButton('Export All', self)
        self.exportAllButton.pressed.connect(self.exportAll)
        exportButtonLayout.addWidget(self.exportAllButton)

        # Lower Layout
        lowerButtonLayout = QtWidgets.QHBoxLayout()
        self.getContentLayout().addLayout(lowerButtonLayout)

        # Export Current Scene
        self.exportButton = QtWidgets.QPushButton('Export Current Scene', self)
        self.exportButton.setMinimumHeight(32)
        self.exportButton.pressed.connect(self.exportScene)
        lowerButtonLayout.addWidget(self.exportButton)

        self.updateProject(force=True)

    def exportPressed(self):
        """ Exports the project as a package. """
        try:
            ckcore.exportAnimation()
            ckcore.exportPackage()
        finally:
            self.exportButton.setDown(False)

    def exportSelected(self):
        self._export(self.animationList.getSelectedFiles())
        self.exportSelectedButton.setDown(False)

    def exportAll(self):
        try:
            self._export(self.animationList.getAllFiles())
        finally:
            self.exportAllButton.setDown(False)

    def exportScene(self):
        try:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            ckcore.exportAnimation()
            # ckcore.exportAnimation(format=self.formatBox.currentText())
            ckcore.exportPackage()
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
            self.exportButton.setDown(False)

    def _export(self, files):
        if len(files) == 0:
            return

        # Prompt user to save changes first
        if not saveChangesDialog():
            return

        # Export each scene
        for file in files:
            try:
                cmds.file(file, o=True, force=True, prompt=False)
            except:
                pass
            ckcore.exportAnimation()
            # ckcore.exportAnimation(format=self.formatBox.currentText())

        ckcore.exportPackage()



def load():
    AnimationManager.load()