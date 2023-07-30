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
    replaceFileDialog, getFilesDialog, EditableTableWidget
from ..thirdparty.Qt import QtWidgets, QtGui, QtCore


class ImportMappingEditor(ProjectWindow):
    """ The import mapping editor window. """

    def __init__(self):
        super(ImportMappingEditor, self).__init__()
        self.setWindowTitle('Import Mapping Editor')
        self.getContentLayout().setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)
        self.setMinimumWidth(300)

        # Mapping Table
        self.mappingTable = EditableTableWidget(self)
        self.mappingTable.setColumns(['Control', 'Joint'])
        self.mappingTable.addPressed.connect(self.addMapping)
        self.mappingTable.removePressed.connect(self.removeMapping)
        self.mappingTable.table().setSortingEnabled(True)
        self.getContentLayout().addWidget(self.mappingTable)

        # Test Button
        self.testButton = QtWidgets.QPushButton('Preview Mapping', self)
        self.testButton.setMinimumHeight(32)
        self.testButton.pressed.connect(self.testMapping)
        self.getContentLayout().addWidget(self.testButton)

        self.loadMapping()
        self.getModel().dataChanged.connect(self.loadMapping)

    def testMapping(self):
        try:
            if saveChangesDialog():
                ckcore.testImportMapping()
        finally:
            self.testButton.setDown(False)

    def addMapping(self):
        """ Adds the selection as a mapping. """
        ckcore.createJointControlMapping()
        self.loadMapping()

    def removeMapping(self):
        self.mappingTable.removeSelected()
        self.saveMapping()

    def loadMapping(self):
        """ Loads the mapping when the model changes. """
        self.mappingTable.clear()
        for i, (control, joint) in enumerate(ckproject.getProject().getControlJointMapping().items()):
            self.mappingTable.addItem([control, joint])

    def saveMapping(self):
        """ Saves the mapping when something changes. """
        mapping = {}
        for control, joint in self.mappingTable.getItems():
            mapping[control] = joint
        ckproject.getProject().setControlJointMapping(mapping)
        self.loadMapping()


def load():
    ImportMappingEditor.load()

