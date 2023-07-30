""" Utilities for interacting with nif files. """
import os.path

import pyffi
from pyffi.spells.nif import NifSpell
from pyffi.formats.nif import NifFormat

from maya import cmds
import maya.api.OpenMaya as om2

from . import ckcore, ckproject


def loadNif(filepath):
    """
    Loads data from a nif file.

    Args:
        filepath(str): A nif filepath.

    Returns:
        NifFormat.Data: Nif data.
    """
    data = NifFormat.Data()
    with open(filepath, "rb") as openfile:
        data.read(openfile)
    return data


def saveNif(data, filepath):
    """
    Saves nif data to a file.

    Args:
        data(NifFormat.Data): Nif data.
        filepath(str): A nif filepath.
    """
    with open(filepath, 'wb') as openfile:
        data.write(openfile)


def toMayaName(name):
    """
    Converts a name from nif format to maya format using a simple wildcard system.

    Args:
        name(str): A name.

    Returns:
        str: A Maya name.
    """
    name = name.replace(' ', '_s_')
    name = name.replace('[', '_ob_')
    name = name.replace(']', '_cb_')
    return name


def toMayaPosition(point):
    """
    Reorients a point from Skyrims orientation to Mayas.

    Args:
        point: A nif point.

    Returns:
        tuple: A maya point.
    """
    point = list(point)
    return [point[0], point[2], -point[1]]


def getTriangleVertices(triangle):
    """
    Converts a nif triangle to a list of vertex indices.

    Args:
        triangle: A nif triangle.

    Returns:
        list[int]: A list of vertex indices.
    """
    return [triangle.v_1, triangle.v_2, triangle.v_3]


def getNiNodes(data, node_type):
    """
    Gets all nodes from nif data of a given type.

    Args:
        data(NifFormat.Data): Nif data.
        node_type(type): A nif node type.

    Returns:
        list[NifFormat.NiNode]: nodes.
    """
    branches = []
    for branch in data.get_global_iterator():
        if isinstance(branch, node_type):
            branches.append(branch)
    return branches


def findTriShapeByName(mesh, data):
    """
    Finds tri shapes in a nif scene with the same name as a mesh.

    Args:
        mesh(str): A mesh name.
        data(NifFormat.Data): Nif data.

    Returns:
        NifFormat.NiTriShape: Nif tri shapes.
    """
    if cmds.nodeType(mesh) != 'mesh':
        mesh = cmds.listRelatives(mesh, type='mesh', fullPath=True)[0]
    name = mesh.split('|')[-1]

    # Find tri shapes with the same name
    for tri_shape in getNiNodes(data, NifFormat.NiTriShape):
        if name == tri_shape.name.decode():
            return tri_shape

    raise RuntimeError('Failed to find mesh in nif file with name "%s"' % name)


def findTriShapeByPolygons(mesh, data):
    """
    Finds tri shapes in a nif scene with the same polycount as a mesh.

    Args:
        mesh(str): A list of meshes in the current scene.
        data(NifFormat.Data): Nif data.

    Returns:
        NifFormat.NiTriShape: Nif tri shapes.
    """
    # Get vertex counts of each mesh
    sel = om2.MSelectionList()
    sel.add(mesh)
    fnMesh = om2.MFnMesh(sel.getDependNode(0))
    tri_count = fnMesh.numPolygons

    # Find tri shapes with the same counts
    for tri_shape in getNiNodes(data, NifFormat.NiTriShape):
        if tri_count == tri_shape.data.num_triangles:
            return tri_shape
    return None


def findNiNode(data, name):
    """
    Finds a node in a nif scene by name.

    Args:
        data(NifFormat.Data): Nif data.
        name(str): A node name.

    Returns:
        NiNode: A nif node.
    """
    for node in getNiNodes(data, NifFormat.NiNode):
        if toMayaName(node.name.decode()) == name:
            return node
    return None


def setJointPose(data, joint, translate, rotate):
    """
    Sets the world space pose a of joint in a nif scene.

    Args:
        data(NifFormat.Data): Nif data.
        joint(str): A joint name.
        translate(tuple): A translation value.
        rotate(tuple): A rotation value.
    """
    nif_joint = findNiNode(data, joint)
    nif_joint.translation = NifFormat.Vector3(translate)


def setMeshTextures(data, mesh, albedo=None, normal=None, emissive=None, cubemap=None, metallic=None, height=None,
                    subsurface=None):
    """
    Sets the textures for a mesh in a nif file.

    Args:
        data(NifFormat.Data): Nif data.
        mesh(str): A mesh name.
        albedo(str): An albedo texture filepath.
        normal(str): A normal map filepath.
        emissive(str): An emissive map filepath.
        cubemap(str): A cube map filepath.
        metallic(str): A metallic map filepath.
        height(str): A height map filepath.
        subsurface(str): A subsurface map filepath.
    """
    tri_shape = findTriShapeByName(mesh, data)
    for property in tri_shape.bs_properties:
        if property is None:
            continue
        texture_set = property.texture_set
        if albedo is not None:
            texture_set.textures[0] = albedo.replace('/', '\\').encode()
        if normal is not None:
            texture_set.textures[1] = normal.replace('/', '\\').encode()
        if emissive is not None:
            texture_set.textures[2] = emissive.replace('/', '\\').encode()
        if height is not None:
            texture_set.textures[3] = height.replace('/', '\\').encode()
        if cubemap is not None:
            texture_set.textures[4] = cubemap.replace('/', '\\').encode()
        if metallic is not None:
            texture_set.textures[5] = metallic.replace('/', '\\').encode()
        if subsurface is not None:
            texture_set.textures[7] = subsurface.replace('/', '\\').encode()


def fixNifMeshes(data, meshes):
    """
    Fixes meshes in a nif file.
    Currently this will patch the skin weights and assign mesh names.

    Args:
        data(NifFormat.Data): Nif data.
        meshes(list[str]): A list of mesh names in the current scene.
    """

    # Update texture paths)
    for texture_set in getNiNodes(data, NifFormat.BSShaderTextureSet):
        for i, texture in enumerate(texture_set.textures):
            path = texture.decode()
            path = path.replace('/', '\\')
            texture_set.textures[i] = path.encode()

    # Iterate all meshes in the nif scene
    for mesh in meshes:
        if not cmds.nodeType(mesh) == 'mesh':
            mesh = cmds.listRelatives(mesh, type='mesh')[0]
        meshName = mesh.split('|')[-1]

        # Mesh data
        tri_shape = findTriShapeByPolygons(mesh, data)
        shape_data = tri_shape.data
        maya_weights = ckcore.getSkinWeights(mesh)

        # Update mesh name
        tri_shape.name = meshName.encode()

        # Map maya vertices to nif vertices
        sel = om2.MSelectionList()
        sel.add(mesh)
        fnMesh = om2.MFnMesh(sel.getDependNode(0))
        verts_per_polygon, normal_ids_per_polygon_index = fnMesh.getNormalIds()
        mesh_normals = fnMesh.getNormals()
        mesh_tangents = fnMesh.getTangents()
        mesh_binormals = fnMesh.getBinormals()
        nif_to_maya_vertex_mapping = {}
        maya_to_nif_vertex_mapping = {}
        nif_vertex_data = {}
        for i in range(fnMesh.numPolygons):
            for maya_vertex, nif_vertex in zip(fnMesh.getPolygonVertices(i), getTriangleVertices(shape_data.triangles[i])):
                nif_to_maya_vertex_mapping[nif_vertex] = maya_vertex
                maya_to_nif_vertex_mapping.setdefault(maya_vertex, set())
                maya_to_nif_vertex_mapping[maya_vertex].add(nif_vertex)

                # Get the meshes vertex normals, tangents and binormals
                normal = mesh_normals[normal_ids_per_polygon_index[i]]
                tangent = mesh_tangents[normal_ids_per_polygon_index[i]]
                binormal = mesh_binormals[normal_ids_per_polygon_index[i]]
                nif_vertex_data[nif_vertex] = (normal, tangent, binormal)

        # Apply vertex data
        # Todo remove this, it doesn't work sadly :(
        # for vertex, (normal, tangent, binormal) in nif_vertex_data.items():
        #     tri_shape.data.normals[vertex].x = normal[0]
        #     tri_shape.data.normals[vertex].y = -normal[2]
        #     tri_shape.data.normals[vertex].z = normal[1]
        #     tri_shape.data.tangents[vertex].x = tangent[0]
        #     tri_shape.data.tangents[vertex].y = -tangent[2]
        #     tri_shape.data.tangents[vertex].z = tangent[1]
        #     tri_shape.data.bitangents[vertex].x = binormal[0]
        #     tri_shape.data.bitangents[vertex].y = -binormal[2]
        #     tri_shape.data.bitangents[vertex].z = binormal[1]

        # Get the meshes skin instance
        skin_instance = tri_shape.skin_instance
        skin_instance.__class__ = NifFormat.NiSkinInstance  # Convert NiDismemberSkinInstances to NiSkinInstances
        skin_partition = skin_instance.skin_partition

        # Get the skins bone indices
        bone_names = {}
        bone_indices = {}
        for index, bone in enumerate(skin_instance.bones):
            bone_names[index] = toMayaName(bone.name.decode())
            bone_indices[toMayaName(bone.name.decode())] = index

        # Convert maya weights into nif weights
        nif_weights = {}
        for maya_index, maya_bone_weights in maya_weights.items():
            for nif_index in maya_to_nif_vertex_mapping[maya_index]:
                maya_bone_weights = {bone: weight for bone, weight in maya_bone_weights.items() if weight > 0.001}
                nif_weights[nif_index] = {bone_indices[bone]: weight for bone, weight in maya_bone_weights.items()}

        # Map maya bones to nif bones
        nif_bone_to_maya_bone = {}
        for nif_bone in skin_instance.bones:
            maya_bone = toMayaName(nif_bone.name.decode())
            nif_bone_to_maya_bone[nif_bone] = maya_bone
            maya_to_nif_vertex_mapping[maya_bone] = nif_bone

        # Update skinning for each partition
        for skin_partition_block in skin_partition.skin_partition_blocks:

            # Ensure all skin instance bone indices are in the skin partition
            missing_indices = []
            bone_indices = [i for i in skin_partition_block.bones]
            for index, bone in enumerate(skin_instance.bones):
                if index not in bone_indices:
                    missing_indices.append(index)
            num_bones = skin_partition_block.num_bones
            skin_partition_block.num_bones = num_bones + len(missing_indices)
            skin_partition_block.bones.update_size()
            for i, index in enumerate(missing_indices):
                skin_partition_block.bones[num_bones + i] = index

            # Get a mapping of skin partition bone indices to skin instance bone indices
            partition_bone_indices = {index: i for i, index in enumerate(skin_partition_block.bones)}

            # print (len(skin_partition_block.bone_indices), len(skin_partition_block.vertex_map))
            for partition_vertex, vertex in enumerate(skin_partition_block.vertex_map):
                # Clear existing bone weights
                for i in range(4):
                    skin_partition_block.bone_indices[partition_vertex][i] = skin_partition_block.bones[0]
                    skin_partition_block.vertex_weights[partition_vertex][i] = 0.0

                # Set bone weights
                vertex_bone_weights = {index: weight for index, weight in nif_weights[vertex].items() if weight > 0.001}
                for i, (bone_index, weight) in enumerate(vertex_bone_weights.items()):
                    try:
                        skin_partition_block.bone_indices[partition_vertex]
                    except KeyError:
                        raise KeyError(f'Failed to find partition vertex {partition_vertex} for mesh {meshName}')
                    try:
                        skin_partition_block.bone_indices[partition_vertex][i]
                    except KeyError:
                        raise KeyError(f'Failed to find bone index {i} for partition vertex {partition_vertex} of '
                                       f'mesh {meshName}')
                    try:
                        partition_bone_indices[bone_index]
                    except KeyError:
                        raise KeyError(f'Failed to find bone index {bone_index} for mesh {meshName}')
                    skin_partition_block.bone_indices[partition_vertex][i] = partition_bone_indices[bone_index]
                    skin_partition_block.vertex_weights[partition_vertex][i] = weight

