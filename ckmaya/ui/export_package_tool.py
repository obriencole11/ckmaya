""" Tool for creating exporting skins. """

import os
from .core import ProjectModel, ProjectDataWidget, EditableListWidget, infoDialog
from ..core import ckproject, ckcore, ckphysics
from ..core.ckproject import ProjectDataKey
from ..ui.core import MayaWindow, getDirectoryDialog, getFileDialog, getNameDialog, saveChangesDialog, \
    replaceFileDialog, getFilesDialog, errorDecorator
from ..thirdparty.Qt import QtWidgets, QtGui, QtCore


class ExportPackageWindow(MayaWindow):
    """ The main export rig tool window. """

    def __init__(self):
        super(ExportPackageWindow, self).__init__()
        self.setWindowTitle('Export Package Tool')
        self.getMainLayout().setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)

        # Project model
        self._model = ProjectModel(self)

        # Settings
        settingGroup = QtWidgets.QGroupBox('Settings', self)
        self.getMainLayout().addWidget(settingGroup)
        settingLayout = QtWidgets.QVBoxLayout()
        settingGroup.setLayout(settingLayout)

        # Export directory
        settingLayout.addWidget(ProjectDataWidget(ckproject.ProjectDataKey.exportDir, self._model, parent=self))

        # Export package widget
        self.directoryList = EditableListWidget(self)
        self.directoryList.addPressed.connect(self.addDirectory)
        self.directoryList.removePressed.connect(self.removeDirectory)
        self.directoryList.addItems(self._model.getData(ProjectDataKey.exportPackageDirs))
        self.directoryList.textDoubleClicked.connect(self.showInExplorer)
        settingLayout.addWidget(self.directoryList)

        # Export button
        self.exportButton = QtWidgets.QPushButton('Export', parent=self)
        self.exportButton.setFixedHeight(40)
        self.exportButton.pressed.connect(self.exportPressed)
        self.getMainLayout().addWidget(self.exportButton)

        self._model.setProject(ckproject.getProject())

    def showInExplorer(self, filepath):
        """ Opens a filepath in explorer. """
        if os.path.exists(filepath):
            os.startfile(filepath)

    def addDirectory(self):
        """ Adds a directory to the list. """
        directory = getDirectoryDialog(ckproject.getProject().getDirectory())
        if directory is not None:
            self.directoryList.addItem(directory)
            self.directoryList.resetButtons()
            self._model.setData(ProjectDataKey.exportPackageDirs, self.directoryList.getItems())

    def removeDirectory(self):
        """ Removes a directory from the list. """
        self.directoryList.removeSelected()
        self._model.setData(ProjectDataKey.exportPackageDirs, self.directoryList.getItems())

    @errorDecorator
    def exportPressed(self):
        """ Exports the project as a package. """
        try:
            count = ckcore.exportPackage()
            infoDialog('Successfully merged %s assets.' % count, title='Export Successful')
        finally:
            self.exportButton.setDown(False)


def load():
    ExportPackageWindow.load()