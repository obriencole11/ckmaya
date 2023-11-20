""" Tool for importing animations. """

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
    replaceFileDialog, getFilesDialog, errorDecorator
from ..thirdparty.Qt import QtWidgets, QtGui, QtCore


class AnimationImporter(ProjectWindow):
    """ The animation import window. """

    def __init__(self):
        super(AnimationImporter, self).__init__()
        self.setWindowTitle('Animation Importer')
        self.getContentLayout().setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)
        self.setMinimumWidth(300)

        # Settings
        settingGroup = QtWidgets.QGroupBox('Settings', self)
        self.getContentLayout().addWidget(settingGroup)
        settingLayout = QtWidgets.QVBoxLayout()
        settingGroup.setLayout(settingLayout)

        # Import directory
        settingLayout.addWidget(
            ProjectDataWidget(ckproject.ProjectDataKey.importAnimationDir, self.getModel(), parent=self)
        )
        settingLayout.addWidget(
            ProjectDataWidget(ckproject.ProjectDataKey.animationSceneDir, self.getModel(), parent=self)
        )
        settingLayout.addWidget(
            ProjectDataWidget(ckproject.ProjectDataKey.controlJointMapping, self.getModel(), parent=self)
        )
        settingLayout.addWidget(
            ProjectDataWidget(ckproject.ProjectDataKey.importJointName, self.getModel(), parent=self)
        )

        # Animation widget
        self.animationList = ProjectDirectoryWidget(
            ckproject.ProjectDataKey.importAnimationDir, self.getModel(), parent=self
        )
        self.getContentLayout().addWidget(self.animationList)

        # Import Animation
        self.importButton = QtWidgets.QPushButton('Import Animation(s)', self)
        self.importButton.setMinimumHeight(32)
        self.importButton.pressed.connect(self.importScene)
        self.getContentLayout().addWidget(self.importButton)

        self.updateProject(force=True)

    @errorDecorator
    def importScene(self):
        """ Imports the selected animations. """

        # Prompt user to save changes first
        if not saveChangesDialog():
            return

        for filepath in self.animationList.getSelectedFiles():
            ckcore.importAnimation(filepath)

        try:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            for filepath in self.animationList.getSelectedFiles():
                ckcore.importAnimation(filepath)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
            self.importButton.setDown(False)


def load():
    AnimationImporter.load()
