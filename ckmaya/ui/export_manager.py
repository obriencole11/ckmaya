import os
import shutil
from functools import partial
# Export each scene
from maya import cmds
import maya.api.OpenMaya as om2
from ckmaya.core import ckproject, ckcore
from ckmaya.ui.core import MayaWindow, getDirectoryDialog, getFileDialog, getNameDialog, saveChangesDialog, \
    replaceFileDialog, getFilesDialog
from ckmaya.thirdparty.Qt import QtWidgets, QtGui, QtCore


class StringDataWidget(QtWidgets.QLineEdit):
    """ A widget for accessing string data. """

    def __init__(self, key, model, parent=None):
        super(StringDataWidget, self).__init__(parent)
        self._key = key
        self._model = model
        self._model.dataChanged.connect(self._onDataChanged)
        self.setText(self._model.getData(self._key))
        self.editingFinished.connect(self._onEditingFinished)

    def _onDataChanged(self, key, value):
        if key == self._key:
            self.setText(str(value))

    def _onEditingFinished(self):
        self._model.setData(self._key, self.text())


class BoolDataWidget(QtWidgets.QCheckBox):
    """ A widget for accessing boolean data. """

    def __init__(self, key, model, parent=None):
        super(BoolDataWidget, self).__init__(parent)
        self._key = key
        self._model = model
        self._model.dataChanged.connect(self._onDataChanged)
        self.setChecked(self._model.getData(self._key))
        self.toggled.connect(self._onToggled)

    def _onDataChanged(self, key, value):
        if key == self._key:
            self.setChecked(bool(value))

    def _onToggled(self):
        self._model.setData(self._key, self.checkState())


class ProjectBox(QtWidgets.QWidget):

    def __init__(self, name, key, model, parent=None):
        super(ProjectBox, self).__init__(parent)
        self._key = key
        self._model = model
        self._model.dataChanged.connect(self._onDataChanged)

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setContentsMargins(0,0,0,0)
        self._layout.setSpacing(5)
        self.setLayout(self._layout)

        # Path Label
        self._label = QtWidgets.QLabel(name, self)
        self._label.setMinimumWidth(100)
        self._label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self._layout.addWidget(self._label)

    def _onDataChanged(self, key, value):
        return


class ProjectStringBox(ProjectBox):

    def __init__(self, name, key, model, parent=None):
        super(ProjectStringBox, self).__init__(name, key, model, parent=parent)

        # Path line edit
        self._lineEdit = QtWidgets.QLineEdit(self)
        self._lineEdit.editingFinished.connect(self.dataChanged)
        self._lineEdit.setText(self._model.getData(self._key))
        self._layout.addWidget(self._lineEdit)

    def dataChanged(self):
        self._model.setData(self._key, self._lineEdit.text())

    def _onDataChanged(self, key, value):
        if key == self._key:
            self._lineEdit.setText(str(value))


class ProjectNodeNameBox(ProjectStringBox):
    pass


class ProjectFileBox(ProjectStringBox):
    """ A widget displaying a project file and a button to replace it. """

    def __init__(self, name, key, model, fileTypes=None, parent=None):
        super(ProjectFileBox, self).__init__(name, key, model, parent=parent)
        self._fileTypes = fileTypes

        # Disable line edit
        self._lineEdit.setEnabled(False)

        # Map button
        self._mapButton = QtWidgets.QPushButton(self)
        self._mapButton.setFlat(True)
        self._mapButton.setIcon(QtGui.QIcon('://SP_DirClosedIcon.png'))
        self._mapButton.pressed.connect(self.mapPath)
        self._mapButton.setMaximumWidth(24)
        self._layout.addWidget(self._mapButton)

        if fileTypes is not None:
            if 'ma' in self._fileTypes:
                # Open Scene Button
                self._openButton = QtWidgets.QPushButton(self)
                self._openButton.setFlat(True)
                self._openButton.setMaximumWidth(24)
                self._openButton.setIcon(QtGui.QIcon('://SP_FileDialogStart.png'))
                self._openButton.pressed.connect(self.openScene)
                self._layout.addWidget(self._openButton)

    def openScene(self):
        """ Opens a maya scene. """
        path = ckproject.getProject().getFullPath(self._lineEdit.text())
        if os.path.exists(path):
            if saveChangesDialog():
                cmds.file(path, o=True, force=True, prompt=False)
                self._openButton.setDown(False)

    def mapPath(self):
        """ Maps the file path. """
        try:
            directory = ckproject.getProject().getDirectory()
            if os.path.exists(self._lineEdit.text()):
                directory = os.path.dirname(self._lineEdit.text())
            filepath = getFileDialog(directory, self._fileTypes, existing=False)
            filepath = ckproject.getProject().getProjectPath(filepath)
            self._model.setData(self._key, filepath)
        finally:
            self._mapButton.setDown(False)


class ProjectDirectoryBox(ProjectStringBox):
    """ A widget displaying a project file and a button to replace it. """

    def __init__(self, name, key, model, parent=None):
        super(ProjectDirectoryBox, self).__init__(name, key, model, parent=parent)

        # Disable line edit
        self._lineEdit.setEnabled(False)

        # Map button
        self._mapButton = QtWidgets.QPushButton(self)
        self._mapButton.setFlat(True)
        self._mapButton.setIcon(QtGui.QIcon('://SP_DirClosedIcon.png'))
        self._mapButton.pressed.connect(self.mapPath)
        self._layout.addWidget(self._mapButton)

    def mapPath(self):
        """ Maps the directory path. """
        try:
            directory = ckproject.getProject().getDirectory()
            if os.path.exists(self._lineEdit.text()):
                directory = os.path.dirname(self._lineEdit.text())
            filepath = getDirectoryDialog(directory)
            filepath = ckproject.getProject().getProjectPath(filepath)
            self._model.setData(self._key, filepath)
        finally:
            self._mapButton.setDown(False)


class ProjectListBox(ProjectBox):

    def __init__(self, name, key, model, fileTypes=None, parent=None):
        super(ProjectListBox, self).__init__(name, key, model, parent=parent)
        self._fileTypes = fileTypes

        listLayout = QtWidgets.QVBoxLayout()
        listLayout.setContentsMargins(0,0,0,0)
        self._layout.addLayout(listLayout)

        # List View
        self._listView = QtWidgets.QListView(self)
        self._listView.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._listView.doubleClicked.connect(self.onDoubleClick)

        self._listModel = QtWidgets.QFileSystemModel(self)
        self._listModel.setReadOnly(True)
        self._listModel.setFilter(QtCore.QDir.Files)
        self._listView.setModel(self._listModel)

        listLayout.addWidget(self._listView)
        # self._onDataChanged(self._key, self._model.getData(self._key))

    def onDoubleClick(self):
        if len(self._listView.selectedIndexes()) > 0:
            path = self._listModel.filePath(self._listView.selectedIndexes()[-1])
            if saveChangesDialog():
                cmds.file(path, o=True, force=True, prompt=False)

    def _onDataChanged(self, key, value):
        if key == self._key:
            root = self._model.getProject().getFullPath(value)
            self._listModel.setRootPath(root)
            self._listView.setRootIndex(self._listModel.index(root))

    def getSelectedFiles(self):
        paths = []
        for index in self._listView.selectedIndexes():
            paths.append(self._listModel.filePath(index))
        return paths

    def getAllFiles(self):
        paths = []
        rootIndex = self._listModel.index(self._listModel.rootPath())
        for i in range(self._listModel.rowCount(rootIndex)):
            paths.append(self._listModel.filePath(rootIndex.child(i, 0)))
        return paths


class ProjectTab(QtWidgets.QWidget):
    """ A tab for project metadata. """

    def __init__(self, model, parent=None):
        super(ProjectTab, self).__init__(parent)
        self._model = model

        # Layouts
        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)

        # Scroll Area
        scrollArea = QtWidgets.QScrollArea(self)
        scrollArea.setWidgetResizable(True)
        scrollArea.setFrameStyle(QtWidgets.QFrame.NoFrame)
        scrollWidget = QtWidgets.QWidget(self)
        scrollArea.setWidget(scrollWidget)
        layout.addWidget(scrollArea)
        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setAlignment(QtCore.Qt.AlignTop)
        self._layout.setContentsMargins(0,0,0,0)
        scrollWidget.setLayout(self._layout)

    def addGroupBox(self, name):
        group = QtWidgets.QGroupBox(name, parent=self)
        group.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Maximum)
        self._layout.addWidget(group)
        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.setAlignment(QtCore.Qt.AlignTop)
        group.setLayout(groupLayout)
        return group, groupLayout


class MetadataTab(ProjectTab):
    """ A tab for project metadata. """

    def __init__(self, model, parent=None):
        super(MetadataTab, self).__init__(model, parent)

        # ---- Import Group ---- #
        importGroup, importGroupLayout = self.addGroupBox('Import Files')

        # Import Skeleton Hkx
        self._importSkeletonHkxBox = ProjectFileBox('skeleton.hkx', ckproject.Project.importSkeletonHkx, model,
                                                    fileTypes='hkx', parent=self)
        importGroupLayout.addWidget(self._importSkeletonHkxBox)

        # Import Skeleton Hkx
        self._importSkeletonNifBox = ProjectFileBox('skeleton.nif', ckproject.Project.importSkeletonNif, model,
                                                    fileTypes='nif', parent=self)
        importGroupLayout.addWidget(self._importSkeletonNifBox)

        # Import Animations
        self._importAnimationBox = ProjectDirectoryBox('Animations', ckproject.Project.importAnimationDir, model,
                                                       parent=self)
        importGroupLayout.addWidget(self._importAnimationBox)

        # Import Animations
        self._importBehaviorBox = ProjectDirectoryBox('Behaviors', ckproject.Project.importBehaviorDir, model,
                                                       parent=self)
        importGroupLayout.addWidget(self._importBehaviorBox)

        # Export Cache File
        self._importCacheBox = ProjectFileBox('Cache File', ckproject.Project.importCacheTxt, model,
                                                       fileTypes=['txt'], parent=self)
        importGroupLayout.addWidget(self._importCacheBox)

        # ---- Scene Group ---- #
        sceneGroup, sceneGroupLayout = self.addGroupBox('Scene Files')

        # Scene Skeleton
        self._sceneSkeletonBox = ProjectFileBox('skeleton.ma', ckproject.Project.skeletonSceneFile, model,
                                                  fileTypes=['ma', 'mb'], parent=self)
        sceneGroupLayout.addWidget(self._sceneSkeletonBox)

        # Scene Animations
        self._sceneAnimationBox = ProjectDirectoryBox('Animations', ckproject.Project.animationSceneDir, model,
                                                      parent=self)
        sceneGroupLayout.addWidget(self._sceneAnimationBox)

        # Export Joint
        self._exportJointBox = ProjectNodeNameBox('Export Node', ckproject.Project.exportJointName, model,
                                                parent=self)
        sceneGroupLayout.addWidget(self._exportJointBox)

        # Export Mesh
        self._skinNameBox = ProjectNodeNameBox('Export Mesh', ckproject.Project.exportMeshName, model,
                                               parent=self)
        sceneGroupLayout.addWidget(self._skinNameBox)

        # ---- Export Group ---- #
        exportGroup, exportGroupLayout = self.addGroupBox('Export Files')

        # Export Skeleton Hkx
        self._exportSkeletonHkxBox = ProjectFileBox('skeleton.hkx', ckproject.Project.exportSkeletonHkx, model,
                                                  fileTypes='hkx', parent=self)
        exportGroupLayout.addWidget(self._exportSkeletonHkxBox)

        # Export Skeleton Hkx
        self._exportSkeletonNifBox = ProjectFileBox('skeleton.nif', ckproject.Project.exportSkeletonNif, model,
                                                  fileTypes='nif', parent=self)
        exportGroupLayout.addWidget(self._exportSkeletonNifBox)

        # Export Skin Hkx
        self._exportSkinNifBox = ProjectFileBox('skin.nif', ckproject.Project.exportSkinNif, model,
                                                  fileTypes='nif', parent=self)
        exportGroupLayout.addWidget(self._exportSkinNifBox)

        # Export Animations
        self._exportAnimationBox = ProjectDirectoryBox('animations', ckproject.Project.exportAnimationDir, model,
                                                       parent=self)
        exportGroupLayout.addWidget(self._exportAnimationBox)

        # Export Behaviors
        self._exportBehaviorBox = ProjectDirectoryBox('Behaviors', ckproject.Project.exportBehaviorDir, model,
                                                       parent=self)
        exportGroupLayout.addWidget(self._exportBehaviorBox)

        # Export Cache File
        self._exportCacheBox = ProjectFileBox('Cache File', ckproject.Project.exportCacheTxt, model,
                                                       fileTypes=['txt'], parent=self)
        exportGroupLayout.addWidget(self._exportCacheBox)

        # Animation Data
        self._exportAnimationDataBox = ProjectDirectoryBox('Animation Data',
                                                           ckproject.Project.exportAnimationDataDir, model, parent=self)
        exportGroupLayout.addWidget(self._exportAnimationDataBox)

        # ----- Mesh Group ----- #
        extraGroup, extraGroupLayout = self.addGroupBox('Additional Files')

        self._textureDirectoryBox = ProjectDirectoryBox('Texture Directory',
                                                           ckproject.Project.textureDir, model, parent=self)
        extraGroupLayout.addWidget(self._textureDirectoryBox)


class EditMappingDialog2(QtWidgets.QDialog):

    SPLITTER = ' --> '
    SRCROLE = QtCore.Qt.UserRole + 1
    DSTROLE = QtCore.Qt.UserRole + 2

    def __init__(self, model, parent=None):
        super(EditMappingDialog2, self).__init__(parent)
        self.setWindowTitle('Edit Mapping')
        self.root = model.getData(ckproject.Project.exportJointName)
        self.model = model

        # Main
        mainLayout = QtWidgets.QVBoxLayout()
        self.setLayout(mainLayout)

        # Joint label
        rootLabel = QtWidgets.QLabel('Root Joint: %s' % self.root)
        mainLayout.addWidget(rootLabel)

        # Mapping List
        self.mappingList = QtWidgets.QListWidget(self)
        self.mappingList.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        mainLayout.addWidget(self.mappingList)

        # Buttons
        buttonLayout = QtWidgets.QHBoxLayout()
        mainLayout.addLayout(buttonLayout)
        connectButton = QtWidgets.QPushButton('Map Selected', self)
        connectButton.pressed.connect(self.connectSelected)
        buttonLayout.addWidget(connectButton)
        disconnectButton = QtWidgets.QPushButton('Remove Selected', self)
        disconnectButton.pressed.connect(self.disconnectSelected)
        buttonLayout.addWidget(disconnectButton)

        self.loadMapping()

    def loadMapping(self):
        mappings = self.model.getData(ckproject.Project.controlJointMapping)
        if isinstance(mappings, (list, tuple)):
            self.setMappings(mappings)

    def getMapping(self):
        mappings = []
        for row in range(self.mappingList.count()):
            item = self.mappingList.item(row)
            src = item.data(self.SRCROLE)
            dst = item.data(self.DSTROLE)
            mappings.append((src, dst))
        return mappings

    def setMappings(self, mappings):
        self.mappingList.clear()
        for src, dst in mappings:
            self.addMapping(src, dst)

    def addMapping(self, src, dst):
        item = QtWidgets.QListWidgetItem('%s%s%s' % (src.split('|')[-1], self.SPLITTER, dst.split('|')[-1]))
        item.setData(self.SRCROLE, src)
        item.setData(self.DSTROLE, dst)
        self.mappingList.addItem(item)

    def connectSelected(self):
        src, dst = ckcore.getJointMappingFromSelection(self.root)
        if src is None or dst is None:
            return
        self.addMapping(src, dst)
        self.updateMapping()

    def disconnectSelected(self):
        for index in reversed(self.mappingList.selectedIndexes()):
            self.mappingList.takeItem(index.row())
        self.updateMapping()

    def updateMapping(self):
        self.model.setData(ckproject.Project.controlJointMapping, self.getMapping())


class EditMappingDialog(QtWidgets.QDialog):

    SPLITTER = ' --> '
    SRCROLE = QtCore.Qt.UserRole + 1
    DSTROLE = QtCore.Qt.UserRole + 2

    def __init__(self, model, parent=None):
        super(EditMappingDialog, self).__init__(parent)
        self.setWindowTitle('Edit Mapping')
        self.root = model.getData(ckproject.Project.exportJointName)
        self.model = model

        # Main
        mainLayout = QtWidgets.QVBoxLayout()
        self.setLayout(mainLayout)

        # Joint label
        rootLabel = QtWidgets.QLabel('Root Joint: %s' % self.root)
        mainLayout.addWidget(rootLabel)

        # Mapping List
        self.mappingList = QtWidgets.QTableWidget(self)
        self.mappingList.setColumnCount(3)
        self.mappingList.verticalHeader().hide()
        self.mappingList.setHorizontalHeaderLabels(['Control', 'Joint', ''])
        self.mappingList.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.mappingList.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.mappingList.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        mainLayout.addWidget(self.mappingList)

        # Buttons
        buttonLayout = QtWidgets.QHBoxLayout()
        mainLayout.addLayout(buttonLayout)
        mapButton = QtWidgets.QPushButton('Map Selected', self)
        mapButton.pressed.connect(self.mapSelected)
        buttonLayout.addWidget(mapButton)

    def loadMapping(self):
        self.mappingList.clearContents()
        self.mappingList.setRowCount(0)
        for i, (control, joint) in enumerate(ckproject.getProject().getControlJointMapping().items()):
            self.mappingList.insertRow(i)
            self.mappingList.setItem(i, 0, QtWidgets.QTableWidgetItem(control))
            self.mappingList.setItem(i, 1, QtWidgets.QTableWidgetItem(joint))

            deleteButton = QtWidgets.QPushButton(self)
            deleteButton.setIcon(QtGui.QIcon('://delete.png'))
            deleteButton.setFlat(True)
            deleteButton.pressed.connect(partial(self.removeMapping, i))
            self.mappingList.setCellWidget(i, 2, deleteButton)

    def saveMapping(self):
        mapping = {}
        for i in range(self.mappingList.rowCount()):
            control = self.mappingList.item(i, 0).text()
            joint = self.mappingList.item(i, 1).text()
            mapping[control] = joint
        ckproject.getProject().setControlJointMapping(mapping)
        self.loadMapping()

    def removeMapping(self, row):
        self.mappingList.removeRow(row)
        self.saveMapping()

    def mapSelected(self):
        ckcore.createJointControlMapping()
        self.loadMapping()


class AnimationTab(ProjectTab):
    """ An export tab for animations files. """

    def __init__(self, model, parent=None):
        super(AnimationTab, self).__init__(model, parent=parent)

        importGroup, importGroupLayout = self.addGroupBox('Import Animation')
        importGroup.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        importButtonLayout = QtWidgets.QHBoxLayout()
        importGroupLayout.addLayout(importButtonLayout)

        # Import Animation
        self.importAnimationButton = QtWidgets.QPushButton('Import Animation(s)', self)
        self.importAnimationButton.pressed.connect(self.importAnimation)
        importButtonLayout.addWidget(self.importAnimationButton)
        editMappingButton = QtWidgets.QPushButton('Edit Mapping', self)
        editMappingButton.pressed.connect(self.editMapping)
        editMappingButton.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        importButtonLayout.addWidget(editMappingButton)

        # Import RootMotion
        otherImportButtonLayout = QtWidgets.QHBoxLayout()
        importGroupLayout.addLayout(otherImportButtonLayout)
        importRootMotionButton = QtWidgets.QPushButton('Import Root Motion', self)
        importRootMotionButton.pressed.connect(self.importRootMotion)
        otherImportButtonLayout.addWidget(importRootMotionButton)
        self.importTagsButton = QtWidgets.QPushButton('Import Tags', self)
        self.importTagsButton.pressed.connect(self.importTags)
        otherImportButtonLayout.addWidget(self.importTagsButton)

        exportGroup, exportGroupLayout = self.addGroupBox('Export Animation')
        exportGroup.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        exportAnimationDirBox = ProjectDirectoryBox('Export Directory', ckproject.Project.animationSceneDir, model,
                                                      parent=self)
        exportGroupLayout.addWidget(exportAnimationDirBox)
        self.exportAnimationBox = ProjectListBox('Animations', ckproject.Project.animationSceneDir, model,
                                                 fileTypes=['ma'], parent=self)
        exportGroupLayout.addWidget(self.exportAnimationBox)

        exportButtonLayout = QtWidgets.QHBoxLayout()
        exportGroupLayout.addLayout(exportButtonLayout)
        self.exportSelectedButton = QtWidgets.QPushButton('Export Selected', self)
        self.exportSelectedButton.pressed.connect(self.exportSelected)
        exportButtonLayout.addWidget(self.exportSelectedButton)
        self.exportAllButton = QtWidgets.QPushButton('Export All', self)
        self.exportAllButton.pressed.connect(self.exportAll)
        exportButtonLayout.addWidget(self.exportAllButton)

        lowerButtonLayout = QtWidgets.QHBoxLayout()
        exportGroupLayout.addLayout(lowerButtonLayout)
        self.exportButton = QtWidgets.QPushButton('Export Current Scene', self)
        self.exportButton.setMinimumHeight(32)
        self.exportButton.pressed.connect(self.exportScene)
        lowerButtonLayout.addWidget(self.exportButton)

        self.mappingWindow = EditMappingDialog(model, parent=self)

    def importAnimation(self):
        try:
            if saveChangesDialog():
                project = ckproject.getProject()
                animations = getFilesDialog(
                    directory=project.getDirectory(),
                    title='Import Animation',
                    fileTypes=['fbx', 'hkx']
                )
                for animation in animations:
                    directory = project.getFullPath(project.getAnimationSceneDirectory())
                    newAnimation = os.path.join(directory, '.'.join([os.path.basename(animation).split('.')[0], 'ma']))
                    if replaceFileDialog(newAnimation):
                        ckcore.importAnimation(animation)
        finally:
            self.importAnimationButton.setDown(False)

    def editMapping(self):
        self.mappingWindow.loadMapping()
        self.mappingWindow.show()

    def importRootMotion(self):
        return

    def importTags(self):
        try:
            project = ckproject.getProject()
            animation = getFileDialog(
                directory=project.getDirectory(),
                title='Import Tag Animation',
                fileTypes=['fbx']
            )
            ckcore.importAnimationTags(animation)
        finally:
            self.importTagsButton.setDown(False)

    def exportSelected(self):
        self._export(self.exportAnimationBox.getSelectedFiles())
        self.exportSelectedButton.setDown(False)

    def exportAll(self):
        self._export(self.exportAnimationBox.getAllFiles())
        self.exportAllButton.setDown(False)

    def exportScene(self):
        try:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            ckcore.exportAnimation()
            self.exportButton.setDown(False)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

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


class RiggingTab(ProjectTab):
    """ An export tab for animations files. """

    def __init__(self, model, parent=None):
        super(RiggingTab, self).__init__(model, parent=parent)

        exportGroup, exportGroupLayout = self.addGroupBox('Export')
        exportGroup.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        # Export Skin
        self.exportSkinButton = QtWidgets.QPushButton('Export Skin', self)
        self.exportSkinButton.pressed.connect(self.exportSkin)
        exportGroupLayout.addWidget(self.exportSkinButton)

        # Export Rig
        self.exportRigButton = QtWidgets.QPushButton('Export Rig', self)
        self.exportRigButton.pressed.connect(self.exportRig)
        exportGroupLayout.addWidget(self.exportRigButton)

    def exportSkin(self):
        try:
            ckcore.exportSkin()
        finally:
            self.exportSkinButton.setDown(False)

    def exportRig(self):
        pass

    def exportAll(self):
        self._export(self.exportAnimationBox.getAllFiles())
        self.exportAllButton.setDown(False)

    def exportScene(self):
        try:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            ckcore.exportAnimation()
            self.exportButton.setDown(False)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

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


class ProjectModel(QtCore.QObject):
    """
    The main project data model.
    This object handles all signals for updating model data.
    """

    dataChanged = QtCore.Signal(str, object)  # Called when a data key is changed

    def __init__(self, parent=None):
        """
        Initializes the project data.

        Args:
            parent(QObject): The parent object.
        """
        super(ProjectModel, self).__init__(parent)
        self._project = ckproject.getProject()
        self._data = {}
        if self._project is not None:
            self.loadData()

    def getProject(self):
        return self._project

    def setProject(self, project):
        self._project = project
        self._data = {}
        self.loadData()

    def loadData(self):
        """
        Loads data from project.
        """
        if self._project is None:
            return

        # Import
        self.setData(ckproject.Project.importSkeletonHkx, self._project.getImportSkeletonHkx())
        self.setData(ckproject.Project.importSkeletonNif, self._project.getImportSkeletonNif())
        self.setData(ckproject.Project.importAnimationDir, self._project.getImportAnimationDirectory())
        self.setData(ckproject.Project.importBehaviorDir, self._project.getImportBehaviorDirectory())
        self.setData(ckproject.Project.importCacheTxt, self._project.getImportCacheFile())
        self.setData(ckproject.Project.controlJointMapping, self._project.getControlJointMapping())

        # Scenes
        self.setData(ckproject.Project.skeletonSceneFile, self._project.getSkeletonScene())
        self.setData(ckproject.Project.animationSceneDir, self._project.getAnimationSceneDirectory())

        # Export
        self.setData(ckproject.Project.exportSkeletonHkx, self._project.getExportSkeletonHkx())
        self.setData(ckproject.Project.exportSkeletonNif, self._project.getExportSkeletonNif())
        self.setData(ckproject.Project.exportSkinNif, self._project.getExportSkinNif())
        self.setData(ckproject.Project.exportAnimationDir, self._project.getExportAnimationDirectory())
        self.setData(ckproject.Project.exportJointName, self._project.getExportJointName())
        self.setData(ckproject.Project.exportMeshName, self._project.getExportMeshName())
        self.setData(ckproject.Project.exportBehaviorDir, self._project.getExportBehaviorDirectory())
        self.setData(ckproject.Project.exportCacheTxt, self._project.getExportCacheFile())
        self.setData(ckproject.Project.exportAnimationDataDir, self._project.getExportAnimationDataDirectory())

        # Extra
        self.setData(ckproject.Project.textureDir, self._project.getTextureDirectory())

    def getData(self, key, default=None):
        """
        Gets a given keys value.

        Args:
            key(str): The data key.
            default(object): The default data value.

        Returns:
            object: The data value.
        """
        return self._data.get(key, default)

    def setData(self, key, value):
        """
        Sets a given keys value.

        Args:
            key(str): The data key.
            value(object): The data value.
        """
        self._project.setMetadataKey(key, value)
        self._data[key] = value
        self.dataChanged.emit(key, value)


class ExportManager(MayaWindow):
    """
    The main export manager window.
    """

    def __init__(self):
        super(ExportManager, self).__init__()
        self.setWindowTitle('Project Manager')

        self._model = ProjectModel(self)

        # Add the menu bar
        menu = QtWidgets.QMenuBar(self)
        self.setMenuBar(menu)
        fileMenu = menu.addMenu('File')
        newAction = fileMenu.addAction('New Project')
        newAction.triggered.connect(self.newProject)
        openAction = fileMenu.addAction('Open Project...')
        openAction.triggered.connect(self.openProject)
        self._openRecentMenu = fileMenu.addMenu('Recent Projects')
        fileMenu.aboutToShow.connect(self.updateRecentProjects)
        exploreAction = fileMenu.addAction('Show in Explorer')
        exploreAction.triggered.connect(self.openExplorer)

        # Add current project text
        self._projectText = QtWidgets.QLabel('Current Project:')
        self.getMainLayout().addWidget(self._projectText)

        # Add tab widget
        self._tabWidget = QtWidgets.QTabWidget(self)
        self.getMainLayout().addWidget(self._tabWidget)
        self._metadataTab = MetadataTab(self._model, parent=self)
        self._tabWidget.addTab(self._metadataTab, 'Metadata')
        # self._tabWidget.addTab(DataTab(self), 'Project')

        # Add rigging tab
        self._riggingTab = RiggingTab(self._model, parent=self)
        self._tabWidget.addTab(self._riggingTab, 'Rigging')

        # Add animation tab
        self._animationTab = AnimationTab(self._model, parent=self)
        self._tabWidget.addTab(self._animationTab, 'Animation')

        self._tabWidget.hide()

        # Add button widget
        self._buttonWidget = QtWidgets.QWidget(self)
        self._buttonWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.getMainLayout().addWidget(self._buttonWidget)
        buttonLayout = QtWidgets.QVBoxLayout()
        buttonLayout.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
        self._buttonWidget.setLayout(buttonLayout)
        openProjectButton = QtWidgets.QPushButton('Open Project...')
        openProjectButton.pressed.connect(self.openProject)
        buttonLayout.addWidget(openProjectButton)
        self._buttonWidget.hide()

        # Updates the window with the current project
        self.updateProject()

    def updateRecentProjects(self):
        """ Updates the recent project menu action. """
        self._openRecentMenu.clear()
        for directory in ckproject.getRecentProjects():
            action = self._openRecentMenu.addAction(directory)
            action.triggered.connect(partial(self.openProject, directory))

    def newProject(self):
        """ Creates a new project. """
        name = getNameDialog()
        directory = getDirectoryDialog(ckproject.getSceneName() or '')
        ckproject.createProject(directory, name)
        self.updateProject()

    def openProject(self, directory=None):
        """
        Opens a project directory.
        If not directory is given a dialog will prompt the user to select one.

        Args:
            directory(str): A directory to open.
        """
        directory = directory or getDirectoryDialog(ckproject.getProject() or '')
        ckproject.setProject(directory)
        self.updateProject()

    def openExplorer(self):
        """
        Opens the current project in explorer.
        """
        os.startfile(ckproject.getProject().getDirectory())
        # subprocess.Popen(r'explorer /select,"%s"' % ckproject.getProject())

    def setProjectText(self, directory):
        """ Updates the current project text. """
        self._projectText.setText('<b>Active Project:</b> %s' % directory)

    def setProjectData(self):
        """ Updates the project with tab data. """
        project = ckproject.getProject()
        for i in range(self._tabWidget.count()):
            self._tabWidget.widget(i).setProjectData(project)

    def updateProject(self):
        """ Updates the interface. """
        project = ckproject.getProject()
        if project is not None:
            ckproject.addRecentProject(project.getDirectory())
            self.setProjectText(project.getDirectory())
            self._tabWidget.show()
            self._buttonWidget.hide()
            self._model.setProject(project)
        else:
            self.setProjectText('None')
            self._tabWidget.hide()
            self._buttonWidget.show()
