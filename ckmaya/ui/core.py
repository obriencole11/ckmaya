""" Core UI functions. """
import os
from maya import cmds
import maya.api.OpenMaya as om2
from functools import partial
from ..core import ckproject
from ..thirdparty.Qt import QtWidgets, QtCore, QtGui


ICON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'icons', 'skyrim_logo.png')


def getDirectoryDialog(directory=None, title=None):
    """
    Prompts the user for a directory path.

    Args:
        directory(str): An optional starting directory path.

    Returns:
        str: A directory path.
    """
    directories = cmds.fileDialog2(dir=directory, fileMode=2, caption=title) or []
    for directory in directories:
        return directory
    raise FilePathException('No directory selected.')


def getFileDialog(directory=None, fileTypes=None, title=None, existing=True):
    """
    Prompts the user for a file path.

    Args:
        directory(str): An optional starting directory path.
        fileTypes(list): A list of accepted file types.
        existing(bool): Whether to only select existing files.

    Returns:
        str: A file path.
    """
    if fileTypes is not None:
        fileTypes = fileTypes if isinstance(fileTypes, (list, tuple)) else [fileTypes]
        fileTypes = [filetype.split('.')[-1] for filetype in fileTypes]
        fileTypes = ';;'.join(['*.%s' % filetype for filetype in fileTypes])
    files = cmds.fileDialog2(dir=directory, fileMode=1 if existing else 0, fileFilter=fileTypes, caption=title) or []
    for filename in files:
        return filename
    raise FilePathException('No file selected.')


def getFilesDialog(directory=None, fileTypes=None, title=None):
    """
    Prompts the user for list of files.

    Args:
        directory(str): An optional starting directory path.
        fileTypes(list): A list of accepted file types.

    Returns:
        str: A file path.
    """
    if fileTypes is not None:
        fileTypes = fileTypes if isinstance(fileTypes, (list, tuple)) else [fileTypes]
        fileTypes = [filetype.split('.')[-1] for filetype in fileTypes]
        fileTypes = 'Files (%s)' % ' '.join(['*.%s' % filetype for filetype in fileTypes])
    files = cmds.fileDialog2(dir=directory, fileMode=4, fileFilter=fileTypes, caption=title) or []
    if len(files) == 0:
        raise FilePathException('No file selected.')
    return files


def getNameDialog(title='Name Dialog', message='Enter Name', text=''):
    """
    Prompts the user for a name.

    Args:
        title(str): The window title.
        message(str): The message string.
        text(str): The field text.

    Returns:
        str: The name value.
    """
    result = cmds.promptDialog(
                title=title,
                message=message,
                text=text,
                button=['OK', 'Cancel'],
                defaultButton='OK',
                cancelButton='Cancel',
                dismissString='Cancel')
    if result == 'OK':
        return cmds.promptDialog(query=True, text=True)
    raise CancelDialogException('Dialog Cancelled.')


def infoDialog(message, title=None):
    """
    Displays an information dialog message.

    Args:
        message(str): The message.
        title(str): The window title.

    Returns:
        bool: Whether the dialog was confirmed.
    """
    return QtWidgets.QMessageBox.information(
        getMayaMainWindow(),
        title or 'Info',
        message,
        QtWidgets.QMessageBox.Ok,
        QtWidgets.QMessageBox.Cancel
    ) == QtWidgets.QMessageBox.Ok


def warningDialog(message, title=None):
    """
    Displays an warning dialog message.

    Args:
        message(str): The message.
        title(str): The window title.

    Returns:
        bool: Whether the dialog was confirmed.
    """
    return QtWidgets.QMessageBox.warning(
        getMayaMainWindow(),
        title or 'Warning',
        message,
        QtWidgets.QMessageBox.Ok,
        QtWidgets.QMessageBox.Cancel
    ) == QtWidgets.QMessageBox.Ok


def errorDialog(message, title=None):
    """
    Displays an warning error message.

    Args:
        message(str): The message.
        title(str): The window title.

    Returns:
        bool: Whether the dialog was confirmed.
    """
    return QtWidgets.QMessageBox.critical(
        getMayaMainWindow(),
        title or 'Error',
        message,
        QtWidgets.QMessageBox.Ok,
        QtWidgets.QMessageBox.Cancel
    ) == QtWidgets.QMessageBox.Ok


def saveChangesDialog():
    """
    Prompts the user to save changes to the current scene.

    Returns:
        bool: Whether to continue or not.
    """
    result = cmds.confirmDialog(
        title='Save Changes',
        message='Save changes to %s?' % cmds.file(sn=True, q=True),
        button=["Save", "Don't Save", "Cancel"],
        defaultButton='Save',
        cancelButton='Cancel'
    )
    if result == 'Cancel':
        return False
    if result == 'Save':
        cmds.file(save=True, force=True)
    return True


def replaceFileDialog(filepath):
    """
    Prompts the user to replace an existing file dialog.
    If the filepath does not exist, the prompt will not appear.

    Returns:
        bool: Whether to continue or not.
    """
    if not os.path.exists(filepath):
        return True
    result = cmds.confirmDialog(
        title='Replace File Dialog',
        message='The file "%s" already exists. Do you want to replace it?' % filepath,
        button=["Replace", "Cancel"],
        defaultButton='Replace',
        cancelButton='Cancel'
    )
    if result == 'Cancel':
        return False
    return True


def getMayaMainWindow():
    """
    Wraps the maya main window as a Qt object.

    Returns:
        py:class:`QtWidgets.QWidget`: The main window widget.
    """
    return [obj for obj in QtWidgets.QApplication.topLevelWidgets() if obj.objectName() == 'MayaWindow'][0]


class MayaWindow(QtWidgets.QMainWindow):
    """
    A MainWindow wrapper that automatically sets the parent to be Maya's main window.
    Additionally this class will ensure one instance of the window is loaded at a single time.
    """

    _instances = set()
    closed = QtCore.Signal()

    @classmethod
    def load(cls):
        instance = cls()
        instance.show()
        return instance

    def __init__(self):
        super(MayaWindow, self).__init__(parent=getMayaMainWindow())
        self.settings = QtCore.QSettings('Skywind', self.__class__.__name__)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowIcon(QtGui.QIcon(ICON_PATH))

        # Add a central widget and layout
        self._mainWidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self._mainWidget)
        self._mainLayout = QtWidgets.QVBoxLayout()
        self._mainWidget.setLayout(self._mainLayout)
        self._mainLayout.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

    def getMainLayout(self):
        return self._mainLayout

    def show(self):
        # Close existing instances
        for window in list(self._instances):
            if window.__class__.__name__ == self.__class__.__name__:
                window.close()
        self._instances.add(self)

        # Load saved geometry
        geometry = self.settings.value('geometry', None)
        if geometry:
            self.restoreGeometry(geometry)

        return super(MayaWindow, self).show()

    def closeEvent(self, event):
        # Remove the window instance
        if self in self._instances:
            self._instances.remove(self)

        # Emit the close signal
        self.closed.emit()

        # Save the window geometry
        geometry = self.saveGeometry()
        self.settings.setValue('geometry', geometry)

        return super(MayaWindow, self).closeEvent(event)


class FilePathException(BaseException):
    """ Raised to indicate an invalid file path. """


class CancelDialogException(BaseException):
    """ Raised when a dialog is cancelled. """


class EditableListWidget(QtWidgets.QWidget):
    """ List widget with add/remove buttons. """

    addPressed = QtCore.Signal()
    removePressed = QtCore.Signal()
    textDoubleClicked = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(EditableListWidget, self).__init__(parent)

        # List box
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        self.setLayout(layout)

        # Button Layout
        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0,0,0,0)
        buttonLayout.setAlignment(QtCore.Qt.AlignRight)
        layout.addLayout(buttonLayout)

        # Add Button
        self.addButton = QtWidgets.QPushButton(icon=QtGui.QIcon('://addCreateGeneric.png'), parent=self)
        self.addButton.setFlat(True)
        self.addButton.pressed.connect(self.addPressed)
        buttonLayout.addWidget(self.addButton)

        # Remove Button
        removeButton = QtWidgets.QPushButton(icon=QtGui.QIcon('://delete.png'), parent=self)
        removeButton.setFlat(True)
        removeButton.pressed.connect(self.removePressed)
        buttonLayout.addWidget(removeButton)

        # List
        self._list = QtWidgets.QListWidget(self)
        self._list.itemDoubleClicked.connect(self.itemDoubleClicked)
        layout.addWidget(self._list)

    def itemDoubleClicked(self, item):
        """
        Emits a signal when an item is double clicked.
        """
        self.textDoubleClicked.emit(item.text())

    def removeSelected(self):
        """
        Removes the selected items from the list.
        """
        for item in reversed(self._list.selectedItems()):
            self._list.takeItem(self._list.row(item))

    def addItem(self, text):
        """
        Adds an item to the widget with the given text.

        Args:
            text(str): The text to add.
        """
        self._list.addItem(text)

    def addItems(self, texts):
        """
        Adds item text to the widget.

        Args:
            texts(list[str]): A list of items to add.
        """
        for text in texts:
            self.addItem(text)

    def getItems(self):
        """
        Gets all text in the list.

        Returns:
            list[str]: A list of text.
        """
        items = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            items.append(item.text())
        return items

    def resetButtons(self):
        """
        Resets all buttons.
        """
        self.addButton.setDown(False)


class EditableTableWidget(QtWidgets.QWidget):
    """ Table widget with add/remove buttons. """

    addPressed = QtCore.Signal()
    removePressed = QtCore.Signal()
    textDoubleClicked = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(EditableTableWidget, self).__init__(parent)

        # List box
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        self.setLayout(layout)

        # Button Layout
        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0,0,0,0)
        buttonLayout.setAlignment(QtCore.Qt.AlignRight)
        layout.addLayout(buttonLayout)

        # Add Button
        self.addButton = QtWidgets.QPushButton(icon=QtGui.QIcon('://addCreateGeneric.png'), parent=self)
        self.addButton.setFlat(True)
        self.addButton.pressed.connect(self.addPressed)
        buttonLayout.addWidget(self.addButton)

        # Remove Button
        removeButton = QtWidgets.QPushButton(icon=QtGui.QIcon('://delete.png'), parent=self)
        removeButton.setFlat(True)
        removeButton.pressed.connect(self.removePressed)
        buttonLayout.addWidget(removeButton)

        # List
        self._table = QtWidgets.QTableWidget(self)
        self._table.verticalHeader().hide()
        layout.addWidget(self._table)

    def setColumns(self, columns):
        """
        Sets the table with the given column labels.

        Args:
            columns(list[str]): A list of column names.
        """
        self._table.setColumnCount(len(columns))
        self._table.setHorizontalHeaderLabels(columns)
        self._table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

    def table(self):
        """
        Gets the table widget.

        Returns:
            QtWidgets.QTableWidget: The table.
        """
        return self._table

    def removeSelected(self):
        """
        Removes the selected items from the list.
        """
        for index in reversed(self._table.selectedIndexes()):
            self._table.removeRow(index.row())

    def addItem(self, row):
        """
        Adds an item to the widget with the given text.

        Args:
            row(list[str]): A list of text to add.
        """
        index = self._table.rowCount()
        self._table.insertRow(index)
        for col, text in enumerate(row):
            item = QtWidgets.QTableWidgetItem(text)
            self._table.setItem(index, col, item)

    def addItems(self, rows):
        """
        Adds item text to the widget.

        Args:
            rows(list[list[str]]): A list of items to add.
        """
        for row in rows:
            self.addItem(row)

    def getItems(self):
        """
        Gets all text in the list.

        Returns:
            list[str]: A list of text.
        """
        items = []
        for row in range(self._table.rowCount()):
            item = []
            for col in range(self._table.columnCount()):
                item.append(self._table.item(row, col).text())
            items.append(item)
        return items

    def clear(self):
        """ Removes all items. """
        self._table.clearContents()
        self._table.setRowCount(0)

    def resetButtons(self):
        """
        Resets all buttons.
        """
        self.addButton.setDown(False)


class DirectoryListDialog(QtWidgets.QDialog):
    """ An editable list for directories. """

    @classmethod
    def editDirectories(cls, directories):
        """
        Prompts the user to edit directories.

        Returns:
            list[str]: A list of directories or None if the dialog is cancelled.
        """
        dialog = cls(directories, parent=getMayaMainWindow())
        if dialog.exec_():
            return dialog.directories
        return None

    def __init__(self, directories, parent=None):
        super(DirectoryListDialog, self).__init__(parent)
        self.setWindowTitle('Edit Directories Dialog')
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # Directory result
        self.directories = directories

        # Layout
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # List Widget
        self._listWidget = EditableListWidget(self)
        self._listWidget.removePressed.connect(self.removeDirectory)
        self._listWidget.addPressed.connect(self.addDirectory)
        layout.addWidget(self._listWidget)

        # Add directories
        self._listWidget.addItems(directories)

        # Buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.accepted.connect(self.updateResult)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def updateResult(self):
        """ Updates the directories result. """
        self.directories = self._listWidget.getItems()

    def addDirectory(self):
        """ Adds a directory to the list. """
        directory = getDirectoryDialog(ckproject.getProject().getDirectory())
        if directory is not None:
            self._listWidget.addItem(directory)
            self._listWidget.resetButtons()

    def removeDirectory(self):
        """ Removes a directory from the list. """
        self._listWidget.removeSelected()


class StringMappingDialog(QtWidgets.QDialog):
    """ An editable mapping dialog. """

    @classmethod
    def editMapping(cls, mapping):
        """
        Prompts the user to edit a mapping.

        Args:
            mapping(dict[str, str]): A mapping of strings.

        Returns:
            dict[str, str]: A mapping of strings.
        """
        dialog = cls(mapping, parent=getMayaMainWindow())
        if dialog.exec_():
            return dialog.mapping
        return None

    def __init__(self, mapping, parent=None):
        super(StringMappingDialog, self).__init__(parent)
        self.setWindowTitle('Edit Mapping Dialog')
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.mapping = mapping

        # Layout
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Mapping List
        self.mappingList = EditableTableWidget(self)
        self.mappingList.table().setSortingEnabled(True)
        self.mappingList.addPressed.connect(self.addPressed)
        self.mappingList.removePressed.connect(self.removePressed)
        self.mappingList.setColumns(['Key', 'Value'])
        layout.addWidget(self.mappingList)

        # Buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.accepted.connect(self.updateResult)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Apply mapping
        self.setMapping(mapping)

    def updateResult(self):
        self.mapping = self.getMapping()

    def removePressed(self):
        self.mappingList.removeSelected()

    def addPressed(self):
        self.mappingList.addItem(['', ''])

    def setMapping(self, mapping):
        """
        Updates the UI with a mapping.

        Args:
            mapping(dict[str, str]): A mapping of strings.
        """
        self.mappingList.clear()
        for i, (key, value) in enumerate(mapping.items()):
            self.mappingList.addItem([key, value])
        self.updateResult()

    def getMapping(self):
        """
        Gets the current mapping.

        Returns:
            dict[str, str]: A mapping of strings.
        """
        return {key: value for key, value in self.mappingList.getItems()}


class ProjectDataWidget(QtWidgets.QWidget):
    """ A generic data field for modifying project data. """

    def __init__(self, key, model, parent=None):
        """
        Initializes the box, showing and hiding widgets based on the data type.

        Args:
            key(ProjectDataKey): A project data key.
            model(ProjectModel): The data model.
            parent(QObject): The parent.
        """
        super(ProjectDataWidget, self).__init__(parent)
        self._key = key
        self._dataType = key.dataType
        self._model = model
        self._model.dataChanged.connect(self._onDataChanged)

        # The main layout
        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setAlignment(QtCore.Qt.AlignLeft)
        self._layout.setContentsMargins(0,0,0,0)
        self._layout.setSpacing(5)
        self.setLayout(self._layout)

        # Path Label
        self._label = QtWidgets.QLabel(key.name, self)
        self._label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self._layout.addWidget(self._label)
        if key.name == '':
            self._label.hide()

        # Line Edit
        self._lineEdit = QtWidgets.QLineEdit(self)
        self._lineEdit.hide()
        self._layout.addWidget(self._lineEdit)

        # Map button
        self._mapButton = QtWidgets.QPushButton(self)
        self._mapButton.hide()
        self._mapButton.setIcon(QtGui.QIcon('://SP_DirClosedIcon.png'))
        self._mapButton.setFlat(True)
        self._mapButton.setMaximumWidth(24)
        self._mapButton.pressed.connect(self.mapPressed)
        self._layout.addWidget(self._mapButton)

        # Update button
        self._updateButton = QtWidgets.QPushButton(self)
        self._updateButton.hide()
        self._updateButton.setIcon(QtGui.QIcon('://refresh.png'))
        self._updateButton.setFlat(True)
        self._updateButton.setMaximumWidth(20)
        self._updateButton.pressed.connect(self.updatePressed)
        self._layout.addWidget(self._updateButton)

        # Select button
        self._selectButton = QtWidgets.QPushButton(self)
        self._selectButton.hide()
        self._selectButton.setIcon(QtGui.QIcon('://aselect.png'))
        self._selectButton.setFlat(True)
        self._selectButton.setMaximumWidth(20)
        self._selectButton.pressed.connect(self.selectPressed)
        self._layout.addWidget(self._selectButton)

        # Open scene button
        self._openButton = QtWidgets.QPushButton(self)
        self._openButton.hide()
        self._openButton.setFlat(True)
        self._openButton.setMaximumWidth(24)
        self._openButton.setIcon(QtGui.QIcon('://SP_FileDialogStart.png'))
        self._openButton.pressed.connect(self.openPressed)
        self._layout.addWidget(self._openButton)

        # Edit button
        self._editButton = QtWidgets.QPushButton(self)
        self._editButton.hide()
        self._editButton.setMaximumWidth(24)
        self._editButton.setFlat(True)
        self._editButton.setIcon(QtGui.QIcon('://setEdEditMode.png'))
        self._editButton.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        self._editButton.pressed.connect(self.editPressed)
        self._layout.addWidget(self._editButton)

        # Datatype specific setup
        if self._dataType == ckproject.ProjectDataType.String:
            self._lineEdit.show()
            self._lineEdit.editingFinished.connect(self.dataChanged)
            self._lineEdit.setText(self._model.getData(self._key))
        elif self._dataType == ckproject.ProjectDataType.Float:
            self._lineEdit.show()
            self._lineEdit.editingFinished.connect(self.dataChanged)
            self._lineEdit.setValidator(QtGui.QDoubleValidator(self))
            self._lineEdit.setText(str(self._model.getData(self._key)))
        elif self._dataType == ckproject.ProjectDataType.TxtFile:
            self._lineEdit.show()
            self._lineEdit.setEnabled(False)
            self._lineEdit.setText(self._model.getData(self._key))
            self._mapButton.show()
        elif self._dataType == ckproject.ProjectDataType.NifFile:
            self._lineEdit.show()
            self._lineEdit.setEnabled(False)
            self._lineEdit.setText(self._model.getData(self._key))
            self._mapButton.show()
            self._openButton.show()
        elif self._dataType == ckproject.ProjectDataType.HkxFile:
            self._lineEdit.show()
            self._lineEdit.setEnabled(False)
            self._lineEdit.setText(self._model.getData(self._key))
            self._mapButton.show()
        elif self._dataType == ckproject.ProjectDataType.MayaFile:
            self._lineEdit.show()
            self._lineEdit.setEnabled(False)
            self._lineEdit.setText(self._model.getData(self._key))
            self._mapButton.show()
            self._openButton.show()
        elif self._dataType == ckproject.ProjectDataType.Directory:
            self._lineEdit.show()
            self._lineEdit.setEnabled(False)
            self._lineEdit.setText(self._model.getData(self._key))
            self._mapButton.show()
        elif self._dataType == ckproject.ProjectDataType.DirectoryList:
            self._lineEdit.show()
            self._lineEdit.setEnabled(False)
            self._lineEdit.setText(', '.join(self._model.getData(self._key)))
            self._editButton.show()
        elif self._dataType == ckproject.ProjectDataType.NodeName:
            self._lineEdit.show()
            self._lineEdit.setText(self._model.getData(self._key))
            self._updateButton.show()
            self._selectButton.show()
        elif self._dataType == ckproject.ProjectDataType.StringMapping:
            self._editButton.show()
        else:
            raise NotImplementedError('Datatype "%s" is not implemented.' % self._dataType.value)

        # Apply Tool Tip
        self.setToolTip(self._key.description)

    def setMargin(self, margin):
        """
        Sets the label width of the widget.

        Args:
            margin(int): The width of the label.
        """
        self._label.setFixedWidth(margin)

    def dataChanged(self):
        """
        Updates model data when the widget is modified.
        """
        stringTypes = [
            ckproject.ProjectDataType.String,
            ckproject.ProjectDataType.NifFile,
            ckproject.ProjectDataType.HkxFile,
            ckproject.ProjectDataType.MayaFile,
            ckproject.ProjectDataType.TxtFile,
            ckproject.ProjectDataType.Directory,
        ]
        if self._dataType in stringTypes:
            self._model.setData(self._key, self._lineEdit.text())
        elif self._dataType == ckproject.ProjectDataType.Float:
            self._model.setData(self._key, float(self._lineEdit.text()))

    def _onDataChanged(self, key, value):
        """
        Updates the widget when the project key value changes.

        Args:
            key(ProjectDataKey): The project data key.
            value(Any): The value.
        """

        # Only update when our key changes
        if key != self._key:
            return

        # Update depending on datatype
        stringTypes = [
            ckproject.ProjectDataType.String,
            ckproject.ProjectDataType.NifFile,
            ckproject.ProjectDataType.HkxFile,
            ckproject.ProjectDataType.MayaFile,
            ckproject.ProjectDataType.TxtFile,
            ckproject.ProjectDataType.Directory,
            ckproject.ProjectDataType.NodeName
        ]
        if self._dataType in stringTypes:
            self._lineEdit.setText(str(value))
        elif self._dataType == ckproject.ProjectDataType.Float:
            self._lineEdit.setText(str(value))
        elif self._dataType == ckproject.ProjectDataType.DirectoryList:
            self._lineEdit.setText(', '.join(self._model.getData(self._key)))

    def _currentDirectory(self):
        """
        For file or directory datatypes this will return the line edits current directory.
        Defaults to the project directory.

        Returns:
            str: A directory.
        """
        projectPath = ckproject.getProject().getFullPath(self._lineEdit.text())
        if os.path.exists(projectPath):
            if self._dataType == ckproject.ProjectDataType.Directory:
                return projectPath
            return os.path.dirname(projectPath)
        return ckproject.getProject().getDirectory()

    def openPressed(self):
        """
        Receiving function when the open button is pressed.
        """
        try:
            if self._dataType == ckproject.ProjectDataType.MayaFile:
                path = ckproject.getProject().getFullPath(self._lineEdit.text())
                if os.path.exists(path):
                    if saveChangesDialog():
                        cmds.file(path, o=True, force=True, prompt=False)
                        self._openButton.setDown(False)
            elif self._dataType == ckproject.ProjectDataType.NifFile:
                path = ckproject.getProject().getFullPath(self._lineEdit.text())
                os.startfile(path)
        finally:
            self._openButton.setDown(False)

    def updatePressed(self):
        """
        Receiving function when the update button is pressed.
        """
        try:
            if self._dataType == ckproject.ProjectDataType.NodeName:
                name = ''
                for node in cmds.ls(type='transform', sl=True):
                    name = node.split('|')[-1].split(':')[-1]
                    break
                self._model.setData(self._key, name)
        finally:
            self._openButton.setDown(False)

    def selectPressed(self):
        """
        Receiving function when the select button is pressed.
        """
        try:
            if self._dataType == ckproject.ProjectDataType.NodeName:
                node = self._model.getData(self._key)
                if cmds.objExists(node):
                    cmds.select(node)
        finally:
            self._openButton.setDown(False)

    def editPressed(self):
        """
        Receiving function when the edit button is pressed.
        """
        try:
            if self._dataType == ckproject.ProjectDataType.StringMapping:
                mapping = StringMappingDialog.editMapping(self._model.getData(self._key))
                if mapping is not None:
                    self._model.setData(self._key, mapping)
            elif self._dataType == ckproject.ProjectDataType.DirectoryList:
                directories = DirectoryListDialog.editDirectories(self._model.getData(self._key))
                if directories is not None:
                    self._model.setData(self._key, directories)
        finally:
            self._editButton.setDown(False)

    def mapPressed(self):
        """
        Receiving function when the map button is pressed.
        """
        try:
            if self._dataType == ckproject.ProjectDataType.TxtFile:
                filepath = getFileDialog(self._currentDirectory(), ['txt'], existing=False,
                                         title='Select %s' % self._key.name)
                self._model.setData(self._key, ckproject.getProject().getProjectPath(filepath))
            elif self._dataType == ckproject.ProjectDataType.NifFile:
                filepath = getFileDialog(self._currentDirectory(), ['nif'], existing=False,
                                         title='Select %s' % self._key.name)
                self._model.setData(self._key, ckproject.getProject().getProjectPath(filepath))
            elif self._dataType == ckproject.ProjectDataType.MayaFile:
                filepath = getFileDialog(self._currentDirectory(), ['ma', 'mb'], existing=False,
                                         title='Select %s' % self._key.name)
                self._model.setData(self._key, ckproject.getProject().getProjectPath(filepath))
            elif self._dataType == ckproject.ProjectDataType.HkxFile:
                filepath = getFileDialog(self._currentDirectory(), ['hkx'], existing=False,
                                         title='Select %s' % self._key.name)
                self._model.setData(self._key, ckproject.getProject().getProjectPath(filepath))
            elif self._dataType == ckproject.ProjectDataType.Directory:
                filepath = getDirectoryDialog(self._currentDirectory(),
                                         title='Select %s' % self._key.name)
                self._model.setData(self._key, ckproject.getProject().getProjectPath(filepath))
        finally:
            self._mapButton.setDown(False)


class ProjectDirectoryWidget(QtWidgets.QWidget):
    """ A widget displaying a project directory. """

    def __init__(self, key, model, parent=None):
        super(ProjectDirectoryWidget, self).__init__(parent=parent)
        self._key = key
        self._dataType = key.dataType
        self._model = model
        self._model.dataChanged.connect(self._onDataChanged)

        # The main layout
        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setAlignment(QtCore.Qt.AlignLeft)
        self._layout.setContentsMargins(0,0,0,0)
        self._layout.setSpacing(5)
        self.setLayout(self._layout)

        # List Layout
        listLayout = QtWidgets.QVBoxLayout()
        listLayout.setContentsMargins(0,0,0,0)
        self._layout.addLayout(listLayout)

        # List View
        self._listView = QtWidgets.QListView(self)
        self._listView.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._listView.doubleClicked.connect(self.onDoubleClick)

        # List Model
        self._listModel = QtWidgets.QFileSystemModel(self)
        self._listModel.setReadOnly(True)
        self._listModel.setFilter(QtCore.QDir.Files)
        self._listView.setModel(self._listModel)
        listLayout.addWidget(self._listView)

    def onDoubleClick(self):
        """ Double click open file support. """
        if len(self._listView.selectedIndexes()) > 0:
            path = self._listModel.filePath(self._listView.selectedIndexes()[-1])
            if saveChangesDialog():
                cmds.file(path, o=True, force=True, prompt=False)

    def _onDataChanged(self, key, value):
        """
        Updates the widget when project data changes.

        Args:
            key(ProjectData): Project data key.
            value(str): A string value.
        """
        if key == self._key:
            root = self._model.getProject().getFullPath(value)
            self._listModel.setRootPath(root)
            self._listView.setRootIndex(self._listModel.index(root))

    def getSelectedFiles(self):
        """
        Gets all selected file paths.

        Returns:
            list[str]: A list of filepaths.
        """
        paths = []
        for index in self._listView.selectedIndexes():
            paths.append(self._listModel.filePath(index))
        return paths

    def getAllFiles(self):
        """
        Gets all file paths in the model.

        Returns:
            list[str]: A list of filepaths.
        """
        paths = []
        rootIndex = self._listModel.index(self._listModel.rootPath())
        for i in range(self._listModel.rowCount(rootIndex)):
            paths.append(self._listModel.filePath(rootIndex.child(i, 0)))
        return paths


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
        """
        Updates the widget when project data changes.

        Args:
            key(ProjectData): Project data key.
            value(str): A string value.
        """
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
        """
        Updates the widget when project data changes.

        Args:
            key(ProjectData): Project data key.
            value(bool): A boolean value.
        """
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
        if name == '':
            self._label.hide()

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
        """
        Updates the widget when project data changes.

        Args:
            key(ProjectData): Project data key.
            value(str): A string value.
        """
        if key == self._key:
            self._lineEdit.setText(str(value))


class ProjectFloatBox(ProjectBox):

    def __init__(self, name, key, model, parent=None):
        super(ProjectFloatBox, self).__init__(name, key, model, parent=parent)

        # Path line edit
        self._lineEdit = QtWidgets.QLineEdit(self)
        self._lineEdit.editingFinished.connect(self.dataChanged)
        validator = QtGui.QDoubleValidator(self)
        self._lineEdit.setValidator(validator)
        self._lineEdit.setText(str(self._model.getData(self._key)))
        self._layout.addWidget(self._lineEdit)

    def dataChanged(self):
        self._model.setData(self._key, float(self._lineEdit.text()))

    def _onDataChanged(self, key, value):
        """
        Updates the widget when project data changes.

        Args:
            key(ProjectData): Project data key.
            value(float): A float value.
        """
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
        """
        Updates the widget when project data changes.

        Args:
            key(ProjectData): Project data key.
            value(str): A string value.
        """
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


class ProjectModel(QtCore.QObject):
    """
    The main project data model.
    This object handles all signals for updating model data.
    """

    dataChanged = QtCore.Signal(ckproject.ProjectDataKey, object)  # Called when a data key is changed

    def __init__(self, parent=None):
        """
        Initializes the project data.

        Args:
            parent(QObject): The parent object.
        """
        super(ProjectModel, self).__init__(parent)
        self._project = ckproject.getProject()
        self._data = {key: key.defaultValue for key in ckproject.ProjectDataKey}
        self.loadData()

    def getProject(self):
        """
        Gets the models project.

        Returns:
            Project: A project.
        """
        return self._project

    def setProject(self, project):
        """
        Sets the models project.

        Args:
            project(Project): A project.
        """
        self._project = project
        self._data = {}
        self.loadData()

    def loadData(self):
        """
        Loads data from project.
        """
        if self._project is None:
            return
        for key in ckproject.ProjectDataKey:
            self.setData(key, self._project.getMetadataKey(key))

    def getData(self, key, default=None):
        """
        Gets a given keys value.

        Args:
            key(ProjectData): The data key.
            default(Any): The default data value.

        Returns:
            Any: The data value.
        """
        return self._data.get(key, default)

    def setData(self, key, value):
        """
        Sets a given keys value.

        Args:
            key(ProjectData): The data key.
            value(Any): The data value.
        """
        self._project.setMetadataKey(key, value)
        self._data[key] = value
        self.dataChanged.emit(key, value)


class ProjectWindow(MayaWindow):
    """ A maya window that includes a project model. """

    projectChanged = QtCore.Signal()

    def __init__(self):
        super(ProjectWindow, self).__init__()

        # The project model
        self._model = ProjectModel(self)

        # Add the menu bar
        # menu = QtWidgets.QMenuBar(self)
        # self.setMenuBar(menu)
        # fileMenu = menu.addMenu('File')
        # openAction = fileMenu.addAction('Open Project...')
        # openAction.triggered.connect(self.openProject)
        # self._openRecentMenu = fileMenu.addMenu('Recent Projects')
        # fileMenu.aboutToShow.connect(self.updateRecentProjects)

        # The project text
        # self._projectText = QtWidgets.QLabel(parent=self)
        # self.getMainLayout().addWidget(self._projectText)

        # The load project widget
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

        # The window contents
        self._contentWidget = QtWidgets.QWidget(parent=self)
        self.getMainLayout().addWidget(self._contentWidget)
        self._contentLayout = QtWidgets.QVBoxLayout()
        self._contentLayout.setContentsMargins(0, 0, 0, 0)
        self._contentWidget.setLayout(self._contentLayout)

        # Add a callback to update the project when it changes
        self.callbacks = [om2.MEventMessage.addEventCallback('workspaceChanged', self.updateProject)]
        self.closed.connect(self.removeCallbacks)

    def removeCallbacks(self):
        """ Removes all callbacks """
        for callback in self.callbacks:
            om2.MMessage.removeCallback(callback)

    def getModel(self):
        """
        Gets the windows project model.

        Returns:
            ProjectModel: A project model.
        """
        return self._model

    def updateRecentProjects(self):
        """ Updates the recent project menu action. """
        self._openRecentMenu.clear()
        for directory in ckproject.getRecentProjects():
            action = self._openRecentMenu.addAction(directory)
            action.triggered.connect(partial(self.openProject, directory))

    def openProject(self, directory=None):
        """
        Opens a project directory.
        If not directory is given a dialog will prompt the user to select one.

        Args:
            directory(str): A directory to open.
        """
        directory = directory or getDirectoryDialog(ckproject.getProject() or '')
        ckproject.setProject(directory)

    def getContentWidget(self):
        """
        Gets the window content widget.

        Returns:
            QWidget: The content widget.
        """
        return self._contentWidget

    def getContentLayout(self):
        """
        Gets the window content layout.

        Returns:
            QVBoxLayout: The content layout.
        """
        return self._contentLayout

    def updateProjectText(self, project):
        """
        Sets the current project text.

        Args:
            project(Project): A project.
        """
        name = 'None' if project is None else project.getName()
        name = name.replace('_', ' ')
        name = ' '.join([name.capitalize() for name in name.split(' ')])
        # self._projectText.setText('<h2>%s Project</h2>' % (name))
        windowTitle = self.windowTitle().split('(')[0]
        self.setWindowTitle('%s (%s)' % (windowTitle, name))

    def updateProject(self, *args, force=False):
        """
        Updates the window when the project changes.
        """
        project = ckproject.getProject()
        if project == self.getModel().getProject() and not force:
            return
        if project is not None:
            self.updateProjectText(project)
            self.getContentWidget().show()
            self._buttonWidget.hide()
            self._model.setProject(project)
        else:
            self.updateProjectText(project)
            self.getContentWidget().hide()
            self._buttonWidget.show()
        self.projectChanged.emit()

