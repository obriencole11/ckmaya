""" Tool for creating exporting skins. """

from .core import ProjectModel, ProjectDataWidget, EditableListWidget, infoDialog
from ..core import ckproject, ckcore, ckphysics
from ..core.ckproject import ProjectDataKey
from ..ui.core import MayaWindow, getDirectoryDialog, getFileDialog, getNameDialog, saveChangesDialog, \
    replaceFileDialog, getFilesDialog, errorDecorator
from ..thirdparty.Qt import QtWidgets, QtGui, QtCore


class ExportSkinWindow(MayaWindow):
    """ The export skin window. """

    def __init__(self):
        super(ExportSkinWindow, self).__init__()
        self.setWindowTitle('Export Skin Tool')
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
        settingLayout.addWidget(ProjectDataWidget(ckproject.ProjectDataKey.exportTextureDir, self._model, parent=self))
        settingLayout.addWidget(ProjectDataWidget(ckproject.ProjectDataKey.exportMeshName, self._model, parent=self))
        settingLayout.addWidget(ProjectDataWidget(ckproject.ProjectDataKey.exportSkinNif, self._model, parent=self))

        # Export button
        self.exportButton = QtWidgets.QPushButton('Export', parent=self)
        self.exportButton.setFixedHeight(40)
        self.exportButton.pressed.connect(self.exportPressed)
        self.getMainLayout().addWidget(self.exportButton)

    @errorDecorator
    def exportPressed(self):
        """ Exports the project as a package. """
        try:
            ckcore.exportSkin()
            ckcore.exportPackage()
        finally:
            self.exportButton.setDown(False)


def load():
    ExportSkinWindow.load()
