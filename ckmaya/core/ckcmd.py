""" A python wrapper around ckcmd.exe """

import os
import sys
import tempfile
import subprocess

# Local location of ckcmd.exe
CKCMD = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bin', 'ck-cmd.exe')
HKXCMD = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bin', 'hkxcmd.exe')
BEHAVIOR_CONVERTER_PATH = os.path.join(os.path.dirname(__file__), 'bin', 'HavokBehaviorPostProcess.exe')


def ispython3():
    """ Determines if we are in a python 3 environment or python 2. """
    return sys.version_info.major == 3


def run_command(command, directory='/'):
    """
    Runs a given command in a separate process. Prints the output and raises any exceptions.

    Args:
        command(str): A command string to run.
        directory(str): A directory to run the command in.
    """
    command = command.replace('\\\\', '\\').replace('\\', '/')
    directory = directory.replace('\\\\', '\\').replace('\\', '/')
    print (command)
    with open(os.path.join(tempfile.gettempdir(), 'test.log'), 'w') as f:
        if ispython3():
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, shell=True, cwd=directory)
        else:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       shell=True, cwd=directory)
        out, err = process.communicate()
        print (out)
        if process.returncode != 0 or 'Exception' in str(err):
            raise CkCmdException('\n%s' % str(err))


def exportanimation(skeleton_hkx, animation_hkx, output_directory):
    """
    Converts a Skyrim animation from hkx to fbx.

    Args:
        skeleton_hkx(str): A skeleton.hkx path.
        animation_hkx(str): Either an animation hkx file or directory containing animation hkx files.
        output_directory(str): The output directory.

    Returns:
        str: The executed command string.
    """
    command = '%s exportanimation "%s" "%s" "%s"' % (CKCMD, skeleton_hkx, animation_hkx, output_directory)
    run_command(command, directory=output_directory)
    return command


def importanimation(skeleton_hkx, animation_fbx, output_directory, cache_txt='', behavior_directory=''):
    """
    Converts an animation from fbx to hkx.

    Args:
        skeleton_hkx(str): A skeleton.hkx path.
        animation_fbx(str): An animation fbx file or directory containing animation fbx files.
        output_directory(str): The output directory.
        cache_txt(str): An optional cache file to contain root motion data.
        behavior_directory(str): An optional behavior directory.

    Returns:
        str: The executed command string.
    """
    command = '%s importanimation "%s" "%s" --c="%s" --b="%s" --e="%s"' % (
        CKCMD, skeleton_hkx, animation_fbx,
        cache_txt, behavior_directory, output_directory
    )
    run_command(command, directory=output_directory)
    return command


def exportrig(skeleton_hkx, skeleton_nif, output_directory,
              animation_hkx='', mesh_nif='', cache_txt='', behavior_directory=''):
    """
    Converts a Skyrim rig from hkx to fbx.

    Args:
        skeleton_hkx(str): A skeleton.hkx path.
        skeleton_nif(str): A skeleton.nif path.
        output_directory(str): The output directory.
        animation_hkx(str): Either an animation hkx file or directory containing animation hkx files.
        mesh_nif(str): An optional nif mesh to load or a directory containing mesh nif files.
        cache_txt(str): An optional cache file to containing root motion data.
        behavior_directory(str): An optional behavior directory.

    Returns:
        str: The executed command string.
    """
    commands = [CKCMD, "exportrig"]
    commands.append('"%s"' % skeleton_hkx)
    commands.append('"%s"' % skeleton_nif)
    commands.append('--e="%s"' % output_directory)
    commands.append('--a="%s"' % animation_hkx)
    commands.append('--n="%s"' % mesh_nif)
    commands.append('--b="%s"' % behavior_directory)
    commands.append('--c="%s"' % cache_txt)
    command = ' '.join(commands)
    run_command(command, directory=output_directory)
    return command


def importrig(skeleton_fbx, output_directory):
    """
    Converts a rig from fbx to hkx.

    Args:
        skeleton_fbx(str): A skeleton fbx file.
        output_directory(str): The output directory.

    Returns:

        str: The executed command string.
    """
    commands = [CKCMD, "importrig"]
    commands.append('"%s"' % skeleton_fbx)
    commands.append('-a "%s"' % '')
    commands.append('-e "%s"' % output_directory)
    command = ' '.join(commands)
    run_command(command, directory=output_directory)
    return command


def importskin(skin_fbx, output_directory):
    """
    Converts a skinned mesh fbx to nif.

    Args:
        skin_fbx(str): A skin fbx file.
        output_directory:
        output_directory(str): The output directory.

    Returns:
        str: The executed command string.
    """
    command = '%s importskin "%s" "%s"' % (CKCMD, skin_fbx, output_directory)
    run_command(command, directory=output_directory)
    return command


def importfbx(fbx, output_directory):
    """
    Converts an fbx model to nif.

    Args:
        fbx(str): An fbx file path.
        output_directory(str): The output directory.

    Returns:
        str: The executed command string.
    """
    command = '%s importfbx "%s" "%s"' % (CKCMD, fbx, output_directory)
    run_command(command, directory=output_directory)
    return command


def exportfbx(nif, output_directory, textures=None):
    """
    Converts a nif model to fbx.

    Args:
        nif(str): A nif file path.
        output_directory(str): The output directory.
        textures(str): A skyrim folder with textures.

    Returns:
        str: The executed command string.
    """
    command = '%s exportfbx "%s" -e "%s"' % (CKCMD, nif, output_directory)
    if textures is not None:
        command += ' -t "%s"' % textures
    run_command(command, directory=output_directory)
    return command


def convertHkx(hkx, xml):
    """
    Converts an hkx file to xml.

    Args:
        hkx(str): An hkx file path.
        xml(str): The output file or directory.

    Returns:
        str: The executed command string.
    """
    output_directory = os.path.dirname(xml)
    command = '%s convert "%s" -o "%s" -v:AMD64 ' % (CKCMD, hkx, xml)
    run_command(command, directory=output_directory)
    return command


def convertXml(xml, hkx):
    """
    Converts an xml file to hkx.

    Args:
        xml(str): An xml file path.
        hkx(str): The output file or directory.

    Returns:
        str: The executed command string.
    """
    output_directory = os.path.dirname(hkx)
    command = '"%s" convert -v:WIN32 "%s" "%s"' % (HKXCMD, xml, hkx)
    run_command(command, directory=output_directory)
    return command


def convertSSE(hkx):
    """
    Converts an oldrim behavior hkx to newrim.

    Args:
        hkx(str): An oldrim hkx file.

    Returns:
        str: A newrim hkx file.
    """

    # Rename the old file
    newhkx = hkx.replace('.hkx', '_new.hkx')

    command = '%s --platformamd64 %s %s' % (BEHAVIOR_CONVERTER_PATH, hkx, newhkx)
    run_command(command)

    return newhkx


class CkCmdException(BaseException):
    """ Raised for ckcmd.exe exceptions. """

