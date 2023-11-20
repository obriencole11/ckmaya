""" A tool for batch importing animation tags. """

import contextlib
import os.path

from maya import cmds
from ..core import ckproject, ckcore, ckphysics
from ..ui.core import MayaWindow, getDirectoryDialog, getFileDialog, getNameDialog, saveChangesDialog, \
    replaceFileDialog, getFilesDialog, ProjectDirectoryBox, ProjectListBox, ProjectModel, ProjectWindow, \
    ProjectDataWidget, ProjectDirectoryWidget, errorDecorator
from ..thirdparty.Qt import QtWidgets, QtGui, QtCore


class ImportAnimationTagWindow(ProjectWindow):
    """ The main export rig tool window. """

    def __init__(self):
        super(ImportAnimationTagWindow, self).__init__()
        self.setWindowTitle('Import Animation Tag Tool')
        self.getMainLayout().setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)

        # Animation Tag Directory Box
        directoryBox = ProjectDataWidget(ckproject.ProjectDataKey.animationTagDir, self.getModel(), parent=self)
        self.getContentLayout().addWidget(directoryBox)

        # Root Joint Box
        jointBox = ProjectDataWidget(ckproject.ProjectDataKey.exportJointName, self.getModel(), parent=self)
        self.getContentLayout().addWidget(jointBox)

        # Animation Tag List
        self.tagBox = ProjectDirectoryWidget(ckproject.ProjectDataKey.animationTagDir, self.getModel(), parent=self)
        self.getContentLayout().addWidget(self.tagBox)

        # Button Layout
        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.setSpacing(4)
        self.getContentLayout().addLayout(buttonLayout)

        # Import Selected Button
        self.importSelectedButton = QtWidgets.QPushButton('Import Selected', parent=self)
        self.importSelectedButton.setMinimumHeight(32)
        self.importSelectedButton.pressed.connect(self.importSelectedTags)
        buttonLayout.addWidget(self.importSelectedButton)

        # Import All Button
        self.importAllButton = QtWidgets.QPushButton('Import All', parent=self)
        self.importAllButton.setMinimumHeight(32)
        self.importAllButton.pressed.connect(self.importAllTags)
        buttonLayout.addWidget(self.importAllButton)

        # Settings
        # settingsLayout = QtWidgets.QFormLayout()
        # self.getContentLayout().addLayout(settingsLayout)
        self.exportBox = QtWidgets.QCheckBox('Export', parent=self)
        self.exportBox.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        self.exportBox.setChecked(False)
        buttonLayout.addWidget(self.exportBox)

        # Update the project
        self.updateProject(force=True)

    @errorDecorator
    def _importTags(self, tags):
        """
        Batch imports the given tag files.

        Args:
            tags(list[str]): A list of fbx file paths.
        """
        if len(tags) == 0:
            return

        # Ensure all tags have a corresponding animation file
        tagScenes = []
        project = ckproject.getProject()
        for tag in tags:
            scene = tag.replace(project.getAnimationTagDirectory(), project.getAnimationSceneDirectory())
            scene = scene.replace('.fbx', '.ma')
            if not os.path.exists(scene):
                raise Exception('Failed to find animation scene "%s"' % scene)
            tagScenes.append((tag, scene))

        # Prompt user to save changes first
        if not saveChangesDialog():
            return

        # Export each scene
        for tag, scene in tagScenes:
            try:
                cmds.file(scene, o=True, force=True, prompt=False)
            except:
                pass
            ckcore.importAnimationTags(tag)
            cmds.file(rn=scene)
            cmds.file(save=True)
            if self.exportBox.isChecked():
                ckcore.exportAnimation(format='hkx')

    def importSelectedTags(self):
        """ Batch imports selected tags. """
        try:
            self._importTags(self.tagBox.getSelectedFiles())
        finally:
            self.importSelectedButton.setDown(False)

    def importAllTags(self):
        """ Batch imports all tags. """
        try:
            self._importTags(self.tagBox.getAllFiles())
        finally:
            self.importAllButton.setDown(False)


def load():
    ImportAnimationTagWindow.load()
