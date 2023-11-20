""" Tool for creating importing textures. """

from maya import cmds
from .core import ProjectModel, ProjectDataWidget, EditableListWidget
from ..core import ckproject, ckcore, ckphysics
from ..core.ckproject import ProjectDataKey
from ..ui.core import MayaWindow, getDirectoryDialog, getFileDialog, getNameDialog, saveChangesDialog, \
    replaceFileDialog, getFilesDialog, errorDecorator
from ..thirdparty.Qt import QtWidgets, QtGui, QtCore


class TextureWidget(QtWidgets.QWidget):
    """ A widget for setting a texture. """

    def __init__(self, name, parent=None):
        super(TextureWidget, self).__init__(parent)

        # The main layout
        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setAlignment(QtCore.Qt.AlignLeft)
        self._layout.setContentsMargins(0,0,0,0)
        self._layout.setSpacing(5)
        self.setLayout(self._layout)

        # Path Label
        self._label = QtWidgets.QLabel(name, self)
        self._label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self._layout.addWidget(self._label)

        # Line Edit
        self._lineEdit = QtWidgets.QLineEdit(self)
        self._layout.addWidget(self._lineEdit)

        # Map button
        self._mapButton = QtWidgets.QPushButton(self)
        self._mapButton.setIcon(QtGui.QIcon('://SP_DirClosedIcon.png'))
        self._mapButton.setFlat(True)
        self._mapButton.setMaximumWidth(24)
        self._mapButton.pressed.connect(self.mapPressed)
        self._layout.addWidget(self._mapButton)

    def setMargin(self, margin):
        self._label.setFixedWidth(margin)

    def getTexture(self):
        texture = self._lineEdit.text()
        if texture == '':
            return None
        return texture

    def setTexture(self, texture):
        self._lineEdit.setText(texture)

    def mapPressed(self):
        """ Set the texture when map is pressed. """
        try:
            texture = getFileDialog(
                ckproject.getProject().getTextureDirectory(),
                fileTypes=['dds', 'png']
            )
            if texture is not None:
                self.setTexture(texture)
        finally:
            self._mapButton.setDown(False)


class NodeWidget(QtWidgets.QWidget):
    """ A widget that stores a reference to a node name. """

    mapPressed = QtCore.Signal()

    def __init__(self, label, parent=None):
        super(NodeWidget, self).__init__(parent=parent)

        # The main layout
        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setAlignment(QtCore.Qt.AlignLeft)
        self._layout.setContentsMargins(0,0,0,0)
        self._layout.setSpacing(5)
        self.setLayout(self._layout)

        # Path Label
        self._label = QtWidgets.QLabel(label, self)
        self._label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self._layout.addWidget(self._label)

        # Line Edit
        self._lineEdit = QtWidgets.QLineEdit(self)
        self._lineEdit.setEnabled(False)
        self._layout.addWidget(self._lineEdit)

        # Map button
        self._mapButton = QtWidgets.QPushButton(self)
        self._mapButton.setIcon(QtGui.QIcon('://refresh.png'))
        self._mapButton.setFlat(True)
        self._mapButton.setMaximumWidth(24)
        self._mapButton.pressed.connect(self.mapPressed)
        self._layout.addWidget(self._mapButton)

    def setNodeName(self, name):
        self._lineEdit.setText(name)

    def getNodeName(self):
        return self._lineEdit.text()


class EditTextureWindow(MayaWindow):
    """ The export skin window. """

    def __init__(self):
        super(EditTextureWindow, self).__init__()
        self.setWindowTitle('Edit Texture Tool')
        self.getMainLayout().setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)
        self.setMinimumWidth(300)

        # Mesh box
        self.meshBox = NodeWidget('Mesh:', parent=self)
        self.meshBox.mapPressed.connect(self.loadMesh)
        self.getMainLayout().addWidget(self.meshBox)

        # Settings
        settingGroup = QtWidgets.QGroupBox('Textures', self)
        self.getMainLayout().addWidget(settingGroup)
        settingLayout = QtWidgets.QVBoxLayout()
        settingGroup.setLayout(settingLayout)

        # Texture widgets
        self._textureWidgets = {}
        for texture in ['albedo', 'normal', 'cubemap', 'emissive', 'metallic', 'subsurface']:
            widget = TextureWidget(texture.title(), parent=self)
            widget.setMargin(60)
            self._textureWidgets[texture] = widget
            settingLayout.addWidget(widget)

        self.getMainLayout().addStretch()

        # Apply Button
        self.importButton = QtWidgets.QPushButton('Apply', parent=self)
        self.importButton.setMinimumHeight(30)
        self.importButton.pressed.connect(self.importPressed)
        self.getMainLayout().addWidget(self.importButton)

        self.loadMesh()

    def loadMesh(self):
        """ Loads a selected mesh. """

        # Clear meshes
        self.meshBox.setNodeName('')
        for name, widget in self._textureWidgets.items():
            widget.setTexture('')
            widget.setEnabled(False)
        self.importButton.setEnabled(False)

        # Load meshes
        for node in cmds.ls(sl=True) or []:
            textures = ckcore.getTextures(node)
            self.meshBox.setNodeName(node)
            for name, widget in self._textureWidgets.items():
                texture = textures.get(name, '')
                self._textureWidgets[name].setTexture(texture)
                self._textureWidgets[name].setEnabled(True)
            self.importButton.setEnabled(True)
            break

    @errorDecorator
    def importPressed(self):
        try:
            ckcore.setTextures(
                self.meshBox.getNodeName(),
                albedo=self._textureWidgets['albedo'].getTexture(),
                normal=self._textureWidgets['normal'].getTexture(),
                cubemap=self._textureWidgets['cubemap'].getTexture(),
                emissive=self._textureWidgets['emissive'].getTexture(),
                metallic=self._textureWidgets['metallic'].getTexture(),
                subsurface=self._textureWidgets['subsurface'].getTexture()
            )
        finally:
            self.importButton.setDown(False)


def load():
    EditTextureWindow.load()
