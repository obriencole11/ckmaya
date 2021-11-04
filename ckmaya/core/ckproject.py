""" Core utilities for reading the Skywind project structure. """

import os
import json
import tempfile
from maya import cmds
from maya import OpenMaya as om


RECENT_PROJECT_CACHE = os.path.join(tempfile.gettempdir(), 'ckprojects.json')


def santizePath(path):
    """
    Standardizes the given path.

    Args:
        path(str): A path string.

    Returns:
        str: A sanitized path.
    """
    return path.replace('\\\\', '/').replace('\\', '/')


def addRecentProject(directory):
    """
    Adds a recent project to the recent project cache.

    Args:
        directory(directory): A recent project directory.

    Returns:
        list: The updated recent projects.
    """
    projects = getRecentProjects()
    projects = [path for path in projects if os.path.exists(path) and path != directory][:10]
    projects.insert(0, directory)
    with open(RECENT_PROJECT_CACHE, 'w+') as openfile:
        json.dump(projects, openfile)
    return projects


def getRecentProjects():
    """
    Gets the current recent projects.

    Returns:
        list: A list of project directories.
    """
    if os.path.exists(RECENT_PROJECT_CACHE):
        with open(RECENT_PROJECT_CACHE, 'r') as openfile:
            return json.load(openfile)
    return []


class Project(object):
    """
    An object that handles project relative paths.
    """

    # Import Files
    importSkeletonHkx = 'importskeleton.hkx'
    importSkeletonNif = 'importskeleton.nif'
    importCacheTxt = 'importcache.txt'
    importAnimationDir = 'importanimations'
    importBehaviorDir = 'importbehaviors'

    # Scene Files
    skeletonSceneFile = 'skeleton.ma'
    animationSceneDir = 'animations'

    # Export Files
    exportJointName = 'exportjointname'
    exportSkeletonHkx = 'exportskeleton.hkx'
    exportSkeletonNif = 'exportskeleton.nif'
    exportCacheTxt = 'exportcache.txt'
    exportAnimationDir = 'exportanimations'
    exportBehaviorDir = 'exportbehaviors'
    exportAnimationDataDir = 'exportanimationdata'

    def __init__(self, directory):
        self._directory = directory

    def __repr__(self):
        """ Formats the project name. """
        return 'Project(%s)' % self.getDirectory()

    def _getFile(self, directory, name):
        """
        Gets a file in a given directory if it exists.

        Returns:
            str: A file name.
        """
        if directory is None or name is None:
            return None
        filepath = os.path.join(directory, name)
        if os.path.exists(filepath):
            return filepath
        return None

    def getWorkspace(self):
        """
        Gets the projects workspace.mel file.

        Returns:
            str: The workspace path.
        """
        return os.path.join(self.getDirectory(), 'workspace.mel')

    def getDirectory(self):
        """
        Gets the project root directory.

        Returns:
            str: The project directory path.
        """
        return self._directory

    def getMetadataFile(self):
        """
        Gets the metadata json file.

        Returns:
            str: The metadata file path.
        """
        return os.path.join(self.getDirectory(), 'metadata.json')

    def getMetadata(self):
        """
        Gets metadata dictionary.

        Returns:
            dict: A dictionary of metadata.
        """
        if not os.path.exists(self.getMetadataFile()):
            return {}
        with open(self.getMetadataFile(), 'r') as openfile:
            return json.load(openfile)

    def setMetadata(self, data):
        """
        Sets the project metadata.

        Args:
            data(dict): A dictionary of metadata.
        """
        with open(self.getMetadataFile(), 'w+') as openfile:
            json.dump(data, openfile, indent=4)

    def getMetadataKey(self, key, default=None):
        """
        Gets a metadata value for a given key.

        Args:
            key(str): A dictionary key.
            default(...): The default value to return if the key does not exist.

        Returns:
            (...): The dictionary value.
        """
        return santizePath(self.getMetadata().get(key, default))

    def setMetadataKey(self, key, value):
        """
        Sets the value of the given metadata key.

        Args:
            key(str): A metadata key.
            value(...): A metadata value.
        """
        data = self.getMetadata()
        data[key] = santizePath(value)
        self.setMetadata(data)

    def getProjectPath(self, path):
        """
        Converts a full path to a project local path.

        Args:
            path(str): A file or directory path.

        Returns:
            str: The project file or directory path.
        """
        if self.getDirectory() in path:
            length = len(self.getDirectory().split('/'))
            path = '/'.join(path.split('/')[length:])
        return path

    def getFullPath(self, path):
        """
        Converts a project local path to a full path.

        Args:
            path(str): A file or directory path.

        Returns:
            str: The full file or directory path.
        """
        projectPath = santizePath(os.path.join(self.getDirectory(), path))
        if not os.path.exists(projectPath):
            raise BaseException('%s does not exist.' % projectPath)
        return projectPath

    # ---- Import ---- #

    def getImportSkeletonHkx(self): return self.getMetadataKey(self.importSkeletonHkx, '')
    def getImportSkeletonNif(self): return self.getMetadataKey(self.importSkeletonNif, '')
    def getImportAnimationDirectory(self): return self.getMetadataKey(self.importAnimationDir, '')
    def getImportBehaviorDirectory(self): return self.getMetadataKey(self.importBehaviorDir, '')
    def getImportCacheFile(self): return self.getMetadataKey(self.importCacheTxt, '')

    # ---- Scenes ---- #

    def getAnimationSceneDirectory(self): return self.getMetadataKey(self.animationSceneDir, '')
    def getSkeletonScene(self): return self.getMetadataKey(self.skeletonSceneFile, '')

    # ---- Export ---- #

    def getExportSkeletonHkx(self): return self.getMetadataKey(self.exportSkeletonHkx, '')
    def getExportSkeletonNif(self): return self.getMetadataKey(self.exportSkeletonNif, '')
    def getExportAnimationDirectory(self): return self.getMetadataKey(self.exportAnimationDir, '')
    def getExportJointName(self): return self.getMetadataKey(self.exportJointName, '')
    def getExportBehaviorDirectory(self): return self.getMetadataKey(self.exportBehaviorDir, '')
    def getExportCacheFile(self): return self.getMetadataKey(self.exportCacheTxt, '')
    def getExportAnimationDataDirectory(self): return self.getMetadataKey(self.exportAnimationDataDir, '')


    # --- TODO Remove ----- #

    def getProjectName(self):
        """
        Gets the project name from the metadata.

        Returns:
            str: A project name.
        """
        return self.getMetadataKey('name', None)

    def setProjectName(self, name):
        """
        Sets the project name.

        Args:
            name(str): A project name.
        """
        self.setMetadataKey('name', name)

    def getFirstPerson(self):
        """
        Determines if the project is a first person project.

        Returns:
            bool: Whether first person is enabled.
        """
        return self.getMetadataKey('firstperson', False)

    def setFirstPerson(self, enabled):
        """
        Sets whether first person is enabled for the project.

        Args:
            enabled(bool): Whether first person is enabled.
        """
        self.setMetadataKey('firstperson', enabled)

    def getSceneDirectory(self):
        """
        Gets the Maya scene directory.

        Returns:
            str: A directory path.
        """
        return os.path.join(self.getDirectory(), 'scenes')

    def getAnimationScenes(self):
        """
        Gets all animation scene files.

        Returns:
            list: A list of animation scenes.
        """
        if not os.path.exists(self.getAnimationSceneDirectory()):
            return []
        scenes = []
        for root, dirs, files in os.walk(self.getAnimationSceneDirectory()):
            for file in files:
                if file.endswith('.ma') or file.endswith('.mb'):
                    scenes.append(os.path.join(root, file))
        return scenes

    def getDataDirectory(self):
        """
        Gets the export data directory.

        Returns:
            str: A directory path.
        """
        return os.path.join(self.getDirectory(), 'data')

    def getMeshDirectory(self):
        """
        Gets the meshes directory.

        Returns:
            str: A directory path.
        """
        return os.path.join(self.getDataDirectory(), 'meshes')

    def getCharacterAssetsDirectory(self):
        """
        Gets the character assets directory.

        Returns:
            str: A directory path.
        """
        if self.getProjectName() is None:
            return None
        return os.path.join(self.getMeshDirectory(), 'actors', self.getProjectName(), 'character assets')

    def getSkeletonHkx(self):
        """
        Gets the skeleton hkx file.

        Returns:
            str: A file path.
        """
        return self._getFile(self.getCharacterAssetsDirectory(), 'skeleton.hkx')

    def getSkeletonNif(self):
        """
        Gets the skeleton nif file.

        Returns:
            str: A file path.
        """
        return self._getFile(self.getCharacterAssetsDirectory(), 'skeleton.nif')


def getSceneName():
    """
    Gets the file path of the current scene.

    Returns:
        str: A scene file path.
    """
    return om.MFileIO.currentFile()


def isProject(path):
    """
    Determines if a path is a valid project directory.

    Args:
        path(str): A file or directory path.

    Returns:
        bool: Whether the path is a project.
    """
    for projectFile in ['workspace.mel', 'metadata.json']:
        if not os.path.exists(os.path.join(path, projectFile)):
            return False
    return True


def getProject(path=None):
    """
    Gets a project given a file or directory path.
    If no path is given, this will return the active project.

    Args:
        path(str): A file or directory path.

    Returns:
        Project: A project object.
    """
    if path is None:
        # Return the current workspace
        workspace = cmds.workspace(rd=True, q=True)
        project = getProject(workspace)
        if project is not None:
            return project

        return None
    elif isinstance(path, Project):
        # If the path is a project object, return it
        return path
    else:
        # If the path itself is a project, return it
        if isProject(path):
            return Project(path)

        # Otherwise search parent directories for a project
        head, tail = os.path.split(path)
        while tail != '':
            if isProject(head):
                return Project(head)
            head, tail = os.path.split(head)

        return None


def setProject(directory=None):
    """
    Sets the current project directory.
    If no directory is given, the current scenes project will be used.

    Args:
        directory(str): A directory path.
    """
    project = getProject(directory)
    if project is None:
        raise ProjectError('%s is not a valid project.' % directory)

    # Set the maya project
    cmds.workspace(project.getDirectory(), o=True)

    return


def createProject(directory, name):
    """
    Creates a new project directory.
    If the directory already contains a partially setup project, it will be updated.

    Args:
        directory(str): A directory path.
        name(str): A name for the project.

    Returns:
        Project: The newly created project.
    """
    def createFolder(path):
        """ Creates a directory if it does not exist. """
        if not os.path.exists(path):
            os.makedirs(path)

    # Create the project directory if it does not exist
    createFolder(directory)

    # Create the project meta data
    with open(os.path.join(directory, 'metadata.json'), 'w+') as openfile:
        json.dump({}, openfile)

    # Create the workspace.mel file manually
    workspaceFile = os.path.join(directory, 'workspace.mel')
    if not os.path.exists(workspaceFile):
        with open(os.path.join(directory, 'workspace.mel'), 'w+') as openfile:
            openfile.write('//Maya %s Project Definition' % cmds.about(v=True))

    # Set the project
    cmds.workspace(directory, o=True)

    # Create File Rules
    for rule in [['mayaAscii', 'scenes'], ['mayaBinary', 'scenes'], ['scene', 'scenes'],
                 ['animation', 'scenes/animations'], ['texture', 'textures']]:
        cmds.workspace(fr=rule)
        createFolder(os.path.join(directory, rule[1]))

    # Create Data Directories
    for folder in [
        'data',
        'data/textures',
        'data/textures/actors',
        'data/textures/actors/%s' % name,
        'data',
        'data/meshes',
        'data/meshes/animationdata',
        'data/meshes/animationdata/boundanims',
        'data/meshes/animationsetdata',
        'data/meshes/animationsetdata/%sprojectdata' % name,
        'data/meshes/actors',
        'data/meshes/actors/%s' % name,
        'data/meshes/actors/%s/animations' % name,
        'data/meshes/actors/%s/behaviors' % name,
        'data/meshes/actors/%s/character assets' % name,
        'data/meshes/actors/%s/characters' % name,
    ]:
        createFolder(os.path.join(directory, folder))

    # Save the project
    cmds.workspace(directory, s=True)

    return Project(directory)


class ProjectError(BaseException):
    """ Raised to indicate an invalid project. """