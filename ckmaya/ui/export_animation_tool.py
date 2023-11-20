""" Tool for exporting animations. """

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
    replaceFileDialog, getFilesDialog, EditableTableWidget, ProjectWindow, errorDecorator
from ..thirdparty.Qt import QtWidgets, QtGui, QtCore


class FloatItemDelegate(QtWidgets.QStyledItemDelegate):
    """ A delegate that accepts only floats. """
    WIDTH = 60

    def createEditor(self, widget, option, index):
        if not index.isValid():
            return 0
        editor = super(FloatItemDelegate, self).createEditor(widget, option, index)
        validator = QtGui.QDoubleValidator(editor)
        editor.setValidator(validator)
        return editor

    def sizeHint(self, option, index):
        size = super(FloatItemDelegate, self).sizeHint(option, index)
        size.setWidth(self.WIDTH)
        return size


class ExportAnimationWindow(ProjectWindow):
    """ The export animation window. """

    def __init__(self):
        super(ExportAnimationWindow, self).__init__()
        self.setWindowTitle('Animation Exporter')
        self.getContentLayout().setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)
        self.setMinimumWidth(300)

        # Settings
        settingGroup = QtWidgets.QGroupBox('Settings', self)
        self.getContentLayout().addWidget(settingGroup)
        settingLayout = QtWidgets.QVBoxLayout()
        settingGroup.setLayout(settingLayout)

        # Export directory
        settingLayout.addWidget(
            ProjectDataWidget(ckproject.ProjectDataKey.exportAnimationDir, self.getModel(), parent=self)
        )

        # Animation List
        self.animationList = EditableTableWidget(parent=self)
        self.animationList.setColumns(['Name', 'Start', 'End'])
        self.animationList.addPressed.connect(self.addItem)
        self.animationList.removePressed.connect(self.removeItem)
        self.animationList.dataChanged.connect(self.saveAnimationData)
        self.animationList.view().setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.animationList.view().setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.animationList.view().setItemDelegateForColumn(1, FloatItemDelegate(self))
        self.animationList.view().setItemDelegateForColumn(2, FloatItemDelegate(self))
        self.animationList.view().horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.animationList.view().horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.animationList.view().horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        # refreshButton = self.animationList.addButton(icon='://UVEditorSnapshot.png')
        refreshButton = self.animationList.addButton('://refresh.png')
        refreshButton.pressed.connect(self.refreshSelected)
        showButton = self.animationList.addButton('://RS_visible.png')
        showButton.pressed.connect(self.showSelected)
        self.getContentLayout().addWidget(self.animationList)

        # Export List
        previewGroup = QtWidgets.QGroupBox('Preview', self)
        self.getContentLayout().addWidget(previewGroup)
        previewLayout = QtWidgets.QVBoxLayout()
        previewGroup.setLayout(previewLayout)
        self.previewLabel = QtWidgets.QLabel(self)
        previewLayout.addWidget(self.previewLabel)

        # Buttons
        buttonLayout = QtWidgets.QHBoxLayout()
        self.getContentLayout().addLayout(buttonLayout)

        # Format Setting
        self.formatBox = QtWidgets.QComboBox(self)
        self.formatBox.addItems(['hkx', 'fbx'])
        self.formatBox.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        self.formatBox.currentIndexChanged.connect(self.updatePreview)
        buttonLayout.addWidget(self.formatBox)

        # Export Buttons
        # self.exportSelectedButton = QtWidgets.QPushButton('Export Selected', self)
        # self.exportSelectedButton.setMinimumHeight(32)
        # buttonLayout.addWidget(self.exportSelectedButton)
        self.exportAllButton = QtWidgets.QPushButton('Export', self)
        self.exportAllButton.setMinimumHeight(32)
        self.exportAllButton.pressed.connect(self.exportAll)
        buttonLayout.addWidget(self.exportAllButton)

        # Connect callback
        self.projectChanged.connect(self.loadAnimationData)
        self.sceneChanged.connect(self.loadAnimationData)

        # Update UI
        self.loadAnimationData()
        self.updatePreview()

    @errorDecorator
    def exportAll(self):
        try:
            ckcore.exportSceneAnimation(self.getFormat())
        finally:
            self.exportAllButton.setDown(False)

    def selectedRow(self):
        """ Gets the currently selected row. """
        for index in self.animationList.view().selectedIndexes():
            return index.row()
        return None

    def refreshSelected(self):
        """
        Updates the start and end time of the currently selected row.
        """
        row = self.selectedRow()
        if row is not None:
            data = ckcore.getAnimationExportData()
            start, end = ckcore.getDefaultTimeRange()
            data[row]['start'] = start
            data[row]['end'] = end
            ckcore.setAnimationExportData(data)
            self.loadAnimationData()

    def showSelected(self):
        """
        Sets the current time range to the currently selected row.
        """
        row = self.selectedRow()
        if row is not None:
            data = ckcore.getAnimationExportData()
            start = data[row]['start']
            end = data[row]['end']
            cmds.playbackOptions(minTime=start)
            cmds.playbackOptions(maxTime=end)

    def addItem(self):
        """
        Adds a new row of export data to the scene.
        """
        start, end = ckcore.getDefaultTimeRange()
        self.animationList.addItem(['unnamed', start, end])
        self.saveAnimationData()

    def removeItem(self):
        """
        Removes the currently selected item.
        """
        self.animationList.removeSelected()
        self.saveAnimationData()

    def getFormat(self):
        """
        Gets the export format.

        Returns:
            str: The export format.
        """
        return self.formatBox.currentText()

    def loadAnimationData(self):
        """
        Fills the animation list with data from the current scene.
        """
        self.animationList.clear()
        data = ckcore.getAnimationExportData()
        for item in data:
            self.animationList.addItem([item['name'], str(item['start']), str(item['end'])])

    def updatePreview(self, *args):
        """ Updates the asset preview. """
        names = [item[0] for item in self.animationList.getItems()]
        assets = []
        directory = os.path.normpath(ckproject.getProject().getExportAnimationDirectory())
        for name in names:
            assets.append('%s.%s' % (os.path.join(directory, name), self.getFormat()))
        self.previewLabel.setText('\n'.join(assets))

    def saveAnimationData(self):
        """
        Updates scene data with the current contents of the list.
        """
        data = []
        for name, start, end in self.animationList.getItems():
            data.append({'start': start, 'end': end, 'name': name})
        ckcore.setAnimationExportData(data)
        self.updatePreview()


def load():
    ExportAnimationWindow.load()