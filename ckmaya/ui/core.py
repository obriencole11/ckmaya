""" Core UI functions. """
import os
from maya import cmds
from ckmaya.thirdparty.Qt import QtWidgets, QtCore


def getDirectoryDialog(directory=None):
    """
    Prompts the user for a directory path.

    Args:
        directory(str): An optional starting directory path.

    Returns:
        str: A directory path.
    """
    directories = cmds.fileDialog2(dir=directory, fileMode=2) or []
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

    @classmethod
    def load(cls):
        instance = cls()
        instance.show()
        return instance

    def __init__(self):
        super(MayaWindow, self).__init__(parent=getMayaMainWindow())
        self.settings = QtCore.QSettings('Skywind', self.__class__.__name__)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

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
        geometry = self.settings.value('geometry', '')
        self.restoreGeometry(geometry)

        return super(MayaWindow, self).show()

    def closeEvent(self, event):
        # Remove the window instance
        if self in self._instances:
            self._instances.remove(self)

        # Save the window geometry
        geometry = self.saveGeometry()
        self.settings.setValue('geometry', geometry)

        return super(MayaWindow, self).closeEvent(event)


class FilePathException(BaseException):
    """ Raised to indicate an invalid file path. """


class CancelDialogException(BaseException):
    """ Raised when a dialog is cancelled. """
