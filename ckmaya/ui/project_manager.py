""" Tool for creating exporting skins. """

import os
import shutil
from functools import partial
# Export each scene
import contextlib
from maya import cmds
import maya.api.OpenMaya as om2
from ..core import ckproject, ckcore, ckphysics
from ..core.ckproject import ProjectDataKey
from ..ui.core import MayaWindow, getDirectoryDialog, getFileDialog, getNameDialog, saveChangesDialog, \
    replaceFileDialog, getFilesDialog, ProjectDataWidget, ProjectModel, ProjectWindow
from ..thirdparty.Qt import QtWidgets, QtGui, QtCore


class ProjectManager(ProjectWindow):
    """ The main export rig tool window. """

    def __init__(self):
        super(ProjectManager, self).__init__()
        self.setWindowTitle('Project Window')
        self.getContentLayout().setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)

        # Project model
        # self._model = ProjectModel(self)

        # Add the menu bar
        # menu = QtWidgets.QMenuBar(self)
        # self.setMenuBar(menu)
        # fileMenu = menu.addMenu('File')
        # newAction = fileMenu.addAction('New Project')
        # newAction.triggered.connect(self.newProject)
        # openAction = fileMenu.addAction('Open Project...')
        # openAction.triggered.connect(self.openProject)
        # self._openRecentMenu = fileMenu.addMenu('Recent Projects')
        # fileMenu.aboutToShow.connect(self.updateRecentProjects)
        # exploreAction = fileMenu.addAction('Show in Explorer')
        # exploreAction.triggered.connect(self.openExplorer)

        # Add current project text
        # self._projectText = QtWidgets.QLabel('Current Project:')
        # self.getMainLayout().addWidget(self._projectText)

        # Frame
        self._settingWidget = QtWidgets.QWidget(parent=self)
        frameLayout = QtWidgets.QVBoxLayout()
        self._settingWidget.setLayout(frameLayout)

        # Scroll Area
        scrollArea = QtWidgets.QScrollArea(parent=self)
        scrollArea.setWidgetResizable(True)
        scrollArea.setFocusPolicy(QtCore.Qt.NoFocus)
        scrollArea.setFrameStyle(QtWidgets.QFrame.NoFrame)
        scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scrollArea.setWidget(self._settingWidget)
        self.getContentLayout().addWidget(scrollArea)

        # Category groups
        categoryLayouts = {}
        for category in ckproject.ProjectDataCategory:
            group = QtWidgets.QGroupBox(category.name, parent=self)
            frameLayout.addWidget(group)
            layout = QtWidgets.QVBoxLayout()
            group.setLayout(layout)
            categoryLayouts[category] = layout

        # Add a widget for every data key
        for key in ckproject.ProjectDataKey:
            widget = ProjectDataWidget(key, self._model)
            widget.setMargin(150)
            categoryLayouts[key.category].addWidget(widget)

        # Updates the window with the current project
        self.updateProject(force=True)
        # self.projectChanged.connect(self.updateSettings)

    # def updateRecentProjects(self):
    #     """ Updates the recent project menu action. """
    #     self._openRecentMenu.clear()
    #     for directory in ckproject.getRecentProjects():
    #         action = self._openRecentMenu.addAction(directory)
    #         action.triggered.connect(partial(self.openProject, directory))
    #
    # def newProject(self):
    #     """ Creates a new project. """
    #     name = getNameDialog()
    #     directory = getDirectoryDialog(ckproject.getSceneName() or '')
    #     ckproject.createProject(directory, name)
    #     self.updateProject()
    #
    # def openProject(self, directory=None):
    #     """
    #     Opens a project directory.
    #     If not directory is given a dialog will prompt the user to select one.
    #
    #     Args:
    #         directory(str): A directory to open.
    #     """
    #     directory = directory or getDirectoryDialog(ckproject.getProject() or '')
    #     ckproject.setProject(directory)
    #     self.updateProject()
    #
    # def openExplorer(self):
    #     """
    #     Opens the current project in explorer.
    #     """
    #     os.startfile(ckproject.getProject().getDirectory())
    #     # subprocess.Popen(r'explorer /select,"%s"' % ckproject.getProject())
    #
    # def setProjectText(self, directory):
    #     """ Updates the current project text. """
    #     self._projectText.setText('<b>Active Project:</b> %s' % directory)

    # def updateSettings(self):
    #     """ Updates the interface. """
    #     project = ckproject.getProject()
    #     if project is not None:
    #         self._settingWidget.show()
    #         self._model.setProject(project)
    #     else:
    #         self.setProjectText('None')
    #         self._settingWidget.hide()


def load():
    ProjectManager.load()
