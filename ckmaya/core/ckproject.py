""" Core utilities for reading the Skywind project structure. """

import os
import json
import tempfile
import enum
from maya import cmds, mel
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
    path = path.replace('\\\\', '/').replace('\\', '/')
    if path.endswith('/'):
        path = path[:-1]
    return path


# def addRecentProject(directory):
#     """
#     Adds a recent project to the recent project cache.
#
#     Args:
#         directory(directory): A recent project directory.
#
#     Returns:
#         list: The updated recent projects.
#     """
#     projects = getRecentProjects()
#     projects = [path for path in projects if os.path.exists(path) and path != directory][:10]
#     projects.insert(0, directory)
#     with open(RECENT_PROJECT_CACHE, 'w+') as openfile:
#         json.dump(projects, openfile)
#     return projects


# def getRecentProjects():
#     """
#     Gets the current recent projects.
#
#     Returns:
#         list: A list of project directories.
#     """
#     if os.path.exists(RECENT_PROJECT_CACHE):
#         with open(RECENT_PROJECT_CACHE, 'r') as openfile:
#             return json.load(openfile)
#     return []


class ProjectDataType(enum.Enum):
    """ Project data types. """

    Boolean = 'bool'
    Float = 'float'
    String = 'string'
    StringMapping = 'string_mapping'
    HkxFile = '.hkx'
    NifFile = '.nif'
    TxtFile = '.txt'
    MayaFile = '.ma'
    File = 'file'
    Directory = 'directory'
    DirectoryList = 'directory_list'
    NodeName = 'node_name'


class ProjectDataCategory(enum.Enum):
    """ Project data categories. """

    Import = 'Import'
    General = 'General'
    Export = 'Export'

    @property
    def name(self):
        return {}.get(self, str(self.value))


class ProjectDataKey(enum.Enum):
    """ Project data key names. """

    # Name
    projectName = 'projectname'

    # Import Files
    importSkeletonHkx = 'importskeleton.hkx'
    importSkeletonNif = 'importskeleton.nif'
    importCacheTxt = 'importcache.txt'
    importAnimationDir = 'importanimations'
    importBehaviorDir = 'importbehaviors'
    controlJointMapping = 'controlJointMapping'

    # Scene Files
    skeletonSceneFile = 'skeleton.ma'
    animationSceneDir = 'animations'

    # Textures
    textureDir = 'textures'
    animationTagDir = 'animationTags'

    # Export Files
    exportPackageDirs = 'exportpackagedirs'
    exportDir = 'exportdirectory'
    exportJointName = 'exportjointname'
    exportMeshName = 'exportskinname'
    exportSkeletonHkx = 'exportskeleton.hkx'
    exportSkeletonNif = 'exportskeleton.nif'
    exportSkinNif = 'exportskin.nif'
    exportCacheTxt = 'exportcache.txt'
    exportAnimationDir = 'exportanimations'
    exportBehaviorDir = 'exportbehaviors'
    exportAnimationDataDir = 'exportanimationdata'
    exportScale = 'exportscale'
    exportTextureDir = 'exporttexturedir'
    exportAnimationSkeletonHkx = 'exportanimationskeleton.hkx'

    @property
    def defaultValue(self):
        return {
            ProjectDataKey.controlJointMapping: {},
            ProjectDataKey.exportScale: 1.0,
            ProjectDataKey.exportPackageDirs: [],
            ProjectDataKey.projectName: 'unnamed',
        }.get(self, '')

    @property
    def name(self):
        return {
            self.projectName: 'Project Name',
            self.importSkeletonHkx: 'Import Skeleton Hkx',
            self.importSkeletonNif: 'Import Skeleton Nif',
            self.importCacheTxt: 'Import Cache Txt',
            self.importAnimationDir: 'Import Animation Dir',
            self.importBehaviorDir: 'Import Behavior Dir',
            self.exportPackageDirs: 'Export Package Dirs',
            self.exportDir: 'Export Dir',
            self.exportJointName: 'Export Joint Name',
            self.exportMeshName: 'Export Mesh Name',
            self.exportSkeletonHkx: 'Export Skeleton Hkx',
            self.exportSkeletonNif: 'Export Skeleton Nif',
            self.exportSkinNif: 'Export Skin Nif',
            self.exportCacheTxt: 'Export Cache Txt',
            self.exportAnimationDir: 'Export Animation Dir',
            self.exportBehaviorDir: 'Export Behavior Dir',
            self.exportAnimationDataDir: 'Export Animation Data Dir',
            self.exportScale: 'Export Scale',
            self.controlJointMapping: 'Control Joint Mapping',
            self.skeletonSceneFile: 'Skeleton Scene',
            self.animationSceneDir: 'Animation Scene Dir',
            self.textureDir: 'Texture Dir',
            self.animationTagDir: 'Animation Tag Dir',
            self.exportTextureDir: 'Export Texture Dir',
            self.exportAnimationSkeletonHkx: 'Export Animation Skeleton'
        }.get(self, self.value)

    @property
    def category(self):
        return {
            self.projectName: ProjectDataCategory.General,
            self.importSkeletonHkx: ProjectDataCategory.Import,
            self.importSkeletonNif: ProjectDataCategory.Import,
            self.importCacheTxt: ProjectDataCategory.Import,
            self.importAnimationDir: ProjectDataCategory.Import,
            self.importBehaviorDir: ProjectDataCategory.Import,
            self.exportPackageDirs: ProjectDataCategory.Export,
            self.exportDir: ProjectDataCategory.Export,
            self.exportJointName: ProjectDataCategory.Export,
            self.exportMeshName: ProjectDataCategory.Export,
            self.exportSkeletonHkx: ProjectDataCategory.Export,
            self.exportSkeletonNif: ProjectDataCategory.Export,
            self.exportSkinNif: ProjectDataCategory.Export,
            self.exportCacheTxt: ProjectDataCategory.Export,
            self.exportAnimationDir: ProjectDataCategory.Export,
            self.exportBehaviorDir: ProjectDataCategory.Export,
            self.exportAnimationDataDir: ProjectDataCategory.Export,
            self.exportScale: ProjectDataCategory.Export,
            self.exportTextureDir: ProjectDataCategory.Export,
            self.exportAnimationSkeletonHkx: ProjectDataCategory.Export
        }.get(self, ProjectDataCategory.General)

    @property
    def dataType(self):
        return {
            self.projectName: ProjectDataType.String,
            self.importSkeletonHkx: ProjectDataType.HkxFile,
            self.importSkeletonNif: ProjectDataType.NifFile,
            self.importCacheTxt: ProjectDataType.TxtFile,
            self.importAnimationDir: ProjectDataType.Directory,
            self.importBehaviorDir: ProjectDataType.Directory,
            self.controlJointMapping: ProjectDataType.StringMapping,
            self.skeletonSceneFile: ProjectDataType.MayaFile,
            self.animationSceneDir: ProjectDataType.Directory,
            self.textureDir: ProjectDataType.Directory,
            self.animationTagDir: ProjectDataType.Directory,
            self.exportDir: ProjectDataType.Directory,
            self.exportJointName: ProjectDataType.NodeName,
            self.exportMeshName: ProjectDataType.NodeName,
            self.exportSkeletonHkx: ProjectDataType.HkxFile,
            self.exportSkeletonNif: ProjectDataType.NifFile,
            self.exportSkinNif: ProjectDataType.NifFile,
            self.exportCacheTxt: ProjectDataType.TxtFile,
            self.exportAnimationDir: ProjectDataType.Directory,
            self.exportBehaviorDir: ProjectDataType.Directory,
            self.exportAnimationDataDir: ProjectDataType.Directory,
            self.exportScale: ProjectDataType.Float,
            self.exportPackageDirs: ProjectDataType.DirectoryList,
            self.exportTextureDir: ProjectDataType.Directory,
            self.exportAnimationSkeletonHkx: ProjectDataType.HkxFile
        }.get(self, ProjectDataType.String)

    @property
    def description(self):
        return {
            self.exportAnimationSkeletonHkx: 'The legacy skeleton HKX file used for export animations.'
        }.get(self, '')


class Project(object):
    """
    An object that handles project relative paths.
    """

    def __init__(self, directory):
        self._directory = santizePath(directory)

    def __repr__(self):
        """ Formats the project name. """
        return 'Project(%s)' % self.getDirectory()

    def __eq__(self, other):
        """ Adds support for equality checks. """
        if isinstance(other, Project):
            return self._directory == other._directory

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

    def getName(self):
        """
        Gets the name of the project.

        Returns:
            str: A project name.
        """
        return self.getMetadataKey(ProjectDataKey.projectName)

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

    def getMetadataKey(self, key):
        """
        Gets a metadata value for a given key.

        Args:
            key(ProjectDataKey): A dictionary key.

        Returns:
            Any: The dictionary value.
        """
        data = self.getMetadata().get(key.value, key.defaultValue)
        if isinstance(data, str):
            data = santizePath(data)
        return data

    def setMetadataKey(self, key, value):
        """
        Sets the value of the given metadata key.

        Args:
            key(ProjectDataKey): A metadata key.
            value(...): A metadata value.
        """
        data = self.getMetadata()
        if isinstance(value, str):
            value = santizePath(value)
        data[key.value] = value
        self.setMetadata(data)

    def getExportPath(self, path):
        """
        Converts a full path to a project local export path.

        Args:
            path(str): A file or directory path.

        Returns:
            str: The project file or directory path.
        """
        path = santizePath(path)
        if self.getDirectory() in path:
            length = len(self.getExportDirectory().split('/'))
            path = '/'.join(path.split('/')[length:])
        return path

    def getProjectPath(self, path):
        """
        Converts a full path to a project local path.

        Args:
            path(str): A file or directory path.

        Returns:
            str: The project file or directory path.
        """
        path = santizePath(path)
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
        return santizePath(os.path.join(self.getDirectory(), path))

    # ---- Import ---- #

    def getImportSkeletonHkx(self):
        """
        Gets the full path of the import skeleton hkx file.

        Returns:
            str: A file path.
        """
        return self.getFullPath(self.getMetadataKey(ProjectDataKey.importSkeletonHkx))

    def getImportSkeletonNif(self):
        """
        Gets the full path of the import skeleton nif file.

        Returns:
            str: A file path.
        """
        return self.getFullPath(self.getMetadataKey(ProjectDataKey.importSkeletonNif))

    def getImportCacheFile(self):
        """
        Gets the full path of the import cache file.

        Returns:
            str: A file path.
        """
        return self.getFullPath(self.getMetadataKey(ProjectDataKey.importCacheTxt))

    # ---- Scenes ---- #

    def getAnimationSceneDirectory(self):
        """
        Gets the full path of the animation scene directory.

        Returns:
            str: A directory path.
        """
        return self.getFullPath(self.getMetadataKey(ProjectDataKey.animationSceneDir))

    def getSkeletonScene(self):
        """
        Gets the full path of the skeleton scene.

        Returns:
            str: A file path.
        """
        return self.getFullPath(self.getMetadataKey(ProjectDataKey.skeletonSceneFile))

    # ---- Textures ---- #

    def getTextureDirectory(self):
        """
        Gets the full path of the texture directory.

        Returns:
            str: A directory path.
        """
        return self.getFullPath(self.getMetadataKey(ProjectDataKey.textureDir))

    def getAnimationTagDirectory(self):
        """
        Gets the full path of the animation tag directory.

        Returns:
            str: A directory path.
        """
        return self.getFullPath(self.getMetadataKey(ProjectDataKey.animationTagDir))

    # ---- Export ---- #

    def getExportDirectory(self):
        """
        Gets the full path of the root export directory.

        Returns:
            str: A directory path.
        """
        return self.getFullPath(self.getMetadataKey(ProjectDataKey.exportDir))

    def getExportTextureDirectory(self):
        """
        Gets the full path of the export texture directory.

        Returns:
            str: A directory path.
        """
        return self.getFullPath(self.getMetadataKey(ProjectDataKey.exportTextureDir))

    def getExportPackageDirectories(self):
        """
        Gets the full path of all export package directories.

        Returns:
            list[str]: A directory path.
        """
        return self.getMetadataKey(ProjectDataKey.exportPackageDirs)

    def getExportSkeletonHkx(self):
        """
        Gets the full path of the export skeleton hkx file.

        Returns:
            str: A file path.
        """
        return self.getFullPath(self.getMetadataKey(ProjectDataKey.exportSkeletonHkx))

    def getExportSkeletonNif(self):
        """
        Gets the full path of the export skeleton nif file.

        Returns:
            str: A file path.
        """
        return self.getFullPath(self.getMetadataKey(ProjectDataKey.exportSkeletonNif))

    def getExportAnimationSkeletonHkx(self):
        """
        Gets the full path of the export animation skeleton hkx file.

        Returns:
            str: A file path.
        """
        return self.getFullPath(self.getMetadataKey(ProjectDataKey.exportAnimationSkeletonHkx))

    def getExportSkinNif(self):
        """
        Gets the full path of the export skeleton nif file.

        Returns:
            str: A file path.
        """
        return self.getFullPath(self.getMetadataKey(ProjectDataKey.exportSkinNif))

    def getExportAnimationDirectory(self):
        """
        Gets the full path of the export animation directory.

        Returns:
            str: A directory path.
        """
        return self.getFullPath(self.getMetadataKey(ProjectDataKey.exportAnimationDir))

    def getExportJointName(self): return self.getMetadataKey(ProjectDataKey.exportJointName)
    def getExportMeshName(self): return self.getMetadataKey(ProjectDataKey.exportMeshName)

    def getExportBehaviorDirectory(self):
        """
        Gets the full path of the export behavior directory.

        Returns:
            str: A directory path.
        """
        return self.getFullPath(self.getMetadataKey(ProjectDataKey.exportBehaviorDir))

    def getExportCacheFile(self):
        """
        Gets the full path of the export cache file.

        Returns:
            str: A file path.
        """
        return self.getFullPath(self.getMetadataKey(ProjectDataKey.exportCacheTxt))

    def getExportAnimationDataDirectory(self):
        """
        Gets the full path of the export animation data directory.

        Returns:
            str: A directory path.
        """
        return self.getFullPath(self.getMetadataKey(ProjectDataKey.exportAnimationDataDir))

    # ---- Control Joints ---- #
    def getControlJointMapping(self): return self.getMetadataKey(ProjectDataKey.controlJointMapping)
    def setControlJointMapping(self, mapping): self.setMetadataKey(ProjectDataKey.controlJointMapping, mapping)
    def setControlJoint(self, control, joint):
        mapping = self.getControlJointMapping()
        mapping[control] = joint
        self.setControlJointMapping(mapping)
    def getControlJoint(self, control): return self.getControlJointMapping().get(control)
    def getJointControls(self, joint):
        return [control for control, _joint in self.getControlJointMapping().items() if joint == _joint]


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


def getRecentProjects():
    """
    Gets a list of recent Skyrim projects.

    Returns:
        list[str]: A list of project directories.
    """
    maxSize = cmds.optionVar(q='RecentProjectsMaxSize')
    return [directory for directory in cmds.optionVar(q='RecentProjectsList') if isProject(directory)][:maxSize]


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
    directory = project.getDirectory().replace('\\', '/')
    mel.eval(f'setProject "{directory}"')
    # cmds.workspace(project.getDirectory(), o=True)

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
        json.dump({ProjectDataKey.projectName.value: name}, openfile)

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