""" Library for creating CK physics objects. """

import math
import enum
from maya import cmds
import maya.api.OpenMaya as om2


BOUNDING_BOX_NAME = 'BoundingBox_box'
RB_MATERIAL_NAME = 'SKY_HAV_MAT_SKIN'

CAPSULE_START_ID = 37
CAPSULE_END_ID = 0
CAPSULE_Z_UP_ID = 19
CAPSULE_Z_DOWN_ID = 22


def updateBoundingBox(box, mesh):
    """
    Updates a rig bounding box to fit the given mesh.

    Args:
        box(str): A bounding box mesh name.
        mesh(str): A mesh name.
    """
    boxShape = cmds.listRelatives(box, type='mesh', fullPath=True)[0]

    def centerPivot(box):
        """ Centers a mesh without modifying the pivot. """
        parent = cmds.listRelatives(box, parent=True, fullPath=True)[0]

        center = om2.MVector()
        vertices = cmds.ls('%s.vtx[*]' % box, fl=True)
        for vert in vertices:
            center += om2.MVector(cmds.xform(vert, q=True, t=True, ws=True))
        center /= float(len(vertices))
        position = om2.MVector(cmds.xform(parent, t=True, q=True, ws=True))
        cmds.xform(parent, t=list(center), ws=True)
        offset = position - center
        for vert in vertices:
            vertPoint = om2.MVector(cmds.xform(vert, t=True, q=True, ws=True))
            cmds.xform(vert, t=list(vertPoint + offset), ws=True)

    def getBoxVerts(box):
        """ Gets the bounding verts of a bounding box mesh. """
        vertices = cmds.ls('%s.vtx[*]' % box, fl=True)
        boxPoints = [(vert, [1 if axis > 0 else -1 for axis in cmds.xform(vert, t=True, os=True, q=True)])
                     for vert in vertices]
        verts = []
        for xSign in [-1, 1]:
            for ySign in [-1, 1]:
                for zSign in [-1, 1]:
                    for vert, point in boxPoints:
                        if point == [xSign, ySign, zSign]:
                            verts.append(vert)
                            break
        return verts

    def flattenBottom(box):
        """ Ensures the given box does not extend below world 0. """
        vertices = cmds.ls('%s.vtx[*]' % box, fl=True)
        for vert in vertices:
            point = cmds.xform(vert, t=True, ws=True, q=True)
            point[1] = max(point[1], 0.0)
            cmds.xform(vert, t=point, ws=True)

    mesh = cmds.geomToBBox(mesh, ko=True)[0]
    mesh = cmds.listRelatives(mesh, type='mesh', fullPath=True)[0]
    meshVerts = getBoxVerts(mesh)
    centerPivot(mesh)
    for i, vert in enumerate(getBoxVerts(boxShape)):
        point = cmds.xform(meshVerts[i], t=True, ws=True, q=True)
        cmds.xform(vert, t=point, ws=True)

    flattenBottom(boxShape)
    cmds.delete(cmds.listRelatives(mesh, parent=True, fullPath=True))


def addRigidBody(joint):
    """
    Adds a rigid body to a joint.

    Args:
        joint(str): A joint name.

    Returns:
        str: The rigid body joint.
    """

    # Get the joint parent and children
    childJoints = [child for child in cmds.listRelatives(joint, type='joint', fullPath=True) or []
                   if not child.endswith('_rb')]

    # Get joint positions
    jointRadius = cmds.getAttr('%s.radius' % joint)
    jointPosition = om2.MVector(cmds.xform(joint, t=True, ws=True, q=True))
    childPositions = [om2.MVector(cmds.xform(child, t=True, ws=True, q=True)) for child in childJoints]

    # Default height and radius is based on joint radius
    height, radius = 0.0, jointRadius
    if len(childJoints) == 1:
        # If there is only one child determine the dimensions based on the distance
        childDistance = (childPositions[0] - jointPosition).length()
        if childDistance > 0.01:
            radius = childDistance / 3.0
            height = max(0, childDistance - (radius * 2.0))

    elif len(childJoints) > 1:
        # If there are multiple children, determine based on longest child distance
        childDistances = [(childPosition - jointPosition).length() for childPosition in childPositions]
        if max(childDistances) > 0.01:
            radius = sum(childDistances) / float(len(childDistances))
            height = max(childDistances) / 2.0 - (radius * 2.0)

    jointName = joint.split('|')[-1]
    rbJoint = createRigidBody(jointName, radius=radius, height=height)
    cmds.setAttr('%s.radius' % rbJoint, cmds.getAttr('%s.radius' % joint) / 2.0)

    # Match joint transformation
    cmds.xform(rbJoint, m=cmds.xform(joint, q=True, m=True, ws=True), ws=True)

    return rbJoint


def getRigidBody(node):
    """
    Gets a rigid body joint from a node.

    Args:
        node(str): A node name.

    Returns:
        str: A rigid body joint name.
    """
    if cmds.nodeType(node) == 'mesh':
        node = cmds.listRelatives(node, parent=True, fullPath=True)[0]
    if node.endswith('_rb'):
        return node
    elif node.endswith('_rb_capsule'):
        return cmds.listRelatives(node, parent=True, fullPath=True)[0]
    return None


def getSceneRigidbodies():
    """
    Gets all rigid body joints in the scene.

    Returns:
        list[str]: A list of joint names.
    """
    rigidbodies = []
    for node in cmds.ls(type='joint'):
        rb = getRigidBody(node)
        if rb is not None:
            rigidbodies.append(rb)
    return rigidbodies


def getSelectedRigidBody():
    """
    Gets the selected rigid body joint.

    Returns:
        str: A joint name.
    """
    for node in cmds.ls(sl=True, type='transform'):
        joint = getRigidBody(node)
        if joint is not None:
            return joint
    return None


def getCapsule(rigidbody):
    """
    Gets a capsule mesh from a rigidbody.

    Args:
        node(str): A rigidbody name.

    Returns:
        str: A capsule mesh name.
    """
    for child in cmds.listRelatives(rigidbody, fullPath=True) or []:
        if child.endswith('_rb_capsule'):
            return child
    return None


def toCkName(name):
    """
    Converts a name to its name in the CK.

    Args:
        name(str): A name.

    Returns:
        str: A converted name.
    """
    name = name.split('|')[-1]
    # name = name.replace('_ob_', '[')
    # name = name.replace('_cb_', ']')
    # name = name.replace('_s_', ' ')
    return name


def getAttachmentSource(attachment):
    """
    Gets the source rigidbody of an attachment.

    Args:
        attachment(str): A node name.

    Returns:
        str: A source node name.
    """
    return attachment.split('_con_')[0]


def getAttachmentDestination(attachment):
    """
    Gets the destination rigidbody of an attachment.

    Args:
        attachment(str): A node name.

    Returns:
        str: A source node name.
    """
    return attachment.split('_con_')[1].replace('_rb_attach_point', '_rb')


def isValidAttachment(attachment):
    """
    Determines if an attachment has a valid destination.

    Args:
        attachment(str): An attachment node.

    Returns:
        bool: Whether the attachment is valid.
    """
    return cmds.objExists(getAttachmentDestination(attachment))


def getCapsuleRigidbody(capsule):
    """
    Gets a rigidbody for a capsule.

    Args:
        capsule(str): A capsule name.

    Returns:
        str: A rigidbody name.
    """
    return capsule.replace('_capsule', '')


def getAttachments(rigidbody):
    """
    Gets attachment meshes from a rigid body.

    Args:
        rigidbody(str): A node name.

    Returns:
        list[str]: A list of attachment node names.
    """
    attachments = []
    for child in cmds.listRelatives(rigidbody, fullPath=True) or []:
        if child.endswith('_rb_attach_point'):
            attachments.append(child)
    return attachments


def getMeshPoints(mesh):
    """
    Gets a list of vertex positions on a mesh.

    Args:
        mesh(str): A mesh name.

    Returns:
        list: A list of MVector points.
    """
    vertices = cmds.ls('%s.vtx[*]' % mesh, fl=True)
    return [om2.MVector(cmds.xform(v, t=True, ws=True, q=True)) for v in vertices]


def getCapsuleHeight(capsule):
    """
    Gets the height of a rigid body capsule.

    Args:
        capsule(str): A mesh name.

    Returns:
        float: The height.
    """
    capsule = getCapsule(capsule)
    points = getMeshPoints(capsule)
    return (points[CAPSULE_END_ID] - points[CAPSULE_START_ID]).length() - (getCapsuleRadius(capsule) * 2.0)


def getCapsuleRadius(capsule):
    """
    Gets the radius of a rigid body capsule.

    Args:
        capsule(str): A mesh name.

    Returns:
        float: The radius.
    """
    capsule = getCapsule(capsule)
    points = getMeshPoints(capsule)
    return (points[CAPSULE_Z_UP_ID] - points[CAPSULE_Z_DOWN_ID]).length() / 2.0


def capsulePoints(height=1.0, radius=1.0):
    """
    Gets the local positions of capsule vertices.

    Args:
        height(float): The capsule height.
        radius(float): The capsule radius.

    Returns:
        list: A list of points.
    """

    return [
        [radius + height + radius, 0.0, 0.0],
        [radius + height + (0.868 * radius), 0.0 * radius, 0.5 * radius],
        [radius + height + (0.868 * radius), -0.433 * radius, 0.25 * radius],
        [radius + height + (0.868 * radius), -0.433 * radius, -0.25 * radius],
        [radius + height + (0.868 * radius), 0.0 * radius, -0.5 * radius],
        [radius + height + (0.868 * radius), 0.433 * radius, -0.25 * radius],
        [radius + height + (0.868 * radius), 0.433 * radius, 0.25 * radius],
        [radius + height + (0.5 * radius), 0.0 * radius, 0.866 * radius],
        [radius + height + (0.5 * radius), -0.75 * radius, 0.433 * radius],
        [radius + height + (0.5 * radius), -0.75 * radius, -0.433 * radius],
        [radius + height + (0.5 * radius), 0.0 * radius, -0.866 * radius],
        [radius + height + (0.5 * radius), 0.75 * radius, -0.433 * radius],
        [radius + height + (0.5 * radius), 0.75 * radius, 0.433 * radius],
        [radius + height, 0.0 * radius, 1.0 * radius],
        [radius + height, -0.866 * radius, 0.5 * radius],
        [radius + height, -0.866 * radius, -0.5 * radius],
        [radius + height, 0.0 * radius, -1.0 * radius],
        [radius + height, 0.866 * radius, -0.5 * radius],
        [radius + height, 0.866 * radius, 0.5 * radius],
        [1.0 * radius, 0.0 * radius, 1.0 * radius],
        [1.0 * radius, -0.866 * radius, 0.5 * radius],
        [1.0 * radius, -0.866 * radius, -0.5 * radius],
        [1.0 * radius, 0.0 * radius, -1.0 * radius],
        [1.0 * radius, 0.866 * radius, -0.5 * radius],
        [1.0 * radius, 0.866 * radius, 0.5 * radius],
        [0.5 * radius, 0.0 * radius, 0.866 * radius],
        [0.5 * radius, -0.75 * radius, 0.433 * radius],
        [0.5 * radius, -0.75 * radius, -0.433 * radius],
        [0.5 * radius, 0.0 * radius, -0.866 * radius],
        [0.5 * radius, 0.75 * radius, -0.433 * radius],
        [0.5 * radius, 0.75 * radius, 0.433 * radius],
        [0.132 * radius, 0.0 * radius, 0.5 * radius],
        [0.132 * radius, -0.433 * radius, 0.25 * radius],
        [0.132 * radius, -0.433 * radius, -0.25 * radius],
        [0.132 * radius, 0.0 * radius, -0.5 * radius],
        [0.132 * radius, 0.433 * radius, -0.25 * radius],
        [0.132 * radius, 0.433 * radius, 0.25 * radius],
        [0.0, 0.0, 0.0]
    ]


def createCapsule(name, height=2.0, radius=1.0, parent=None):
    """
    Generates a capsule mesh.

    Args:
        name(str): A mesh name.
        radius(float): The capsule radius.
        height(float): The capsule height.
        parent(str): An optional parent node.

    Returns:
        The capsule mesh name.
    """

    # Create the parent transform
    parentName = cmds.createNode('transform', parent=parent, ss=True, name=name)

    # Wrap the parent as an MObject
    sel = om2.MSelectionList()
    sel.add(parentName)
    parentObj = sel.getDependNode(0)

    # list of vertex points
    vertices = [om2.MVector(point) for point in capsulePoints(height=height, radius=radius)]

    # Apply pivot
    vertices = [om2.MPoint(point) for point in vertices]

    # list of number of vertices per polygon
    # A cube has 6 faces of 4 vertices each
    polygonFaces = [3] * 72

    # list of vertex indices that make the
    # the polygons in our mesh
    polygonConnects = [
         0, 1, 2, 0, 2, 3, 0, 3, 4, 0, 4, 5, 0, 5, 6, 0, 6, 1, 1, 7, 8, 2, 1, 8, 2, 8, 9, 3, 2, 9, 3, 9, 10, 4, 3, 10,
         4, 10, 11, 5, 4, 11, 5, 11, 12, 6, 5, 12, 6, 12, 7, 1, 6, 7, 7, 13, 14, 8, 7, 14, 8, 14, 15, 9, 8, 15, 9, 15,
         16, 10, 9, 16, 10, 16, 17, 11, 10, 17, 11, 17, 18, 12, 11, 18, 12, 18, 13, 7, 12, 13, 13, 19, 20, 14, 13, 20,
         14, 20, 21, 15, 14, 21, 15, 21, 22, 16, 15, 22, 16, 22, 23, 17, 16, 23, 17, 23, 24, 18, 17, 24, 18, 24, 19, 13,
         18, 19, 19, 25, 26, 20, 19, 26, 20, 26, 27, 21, 20, 27, 21, 27, 28, 22, 21, 28, 22, 28, 29, 23, 22, 29, 23, 29,
         30, 24, 23, 30, 24, 30, 25, 19, 24, 25, 25, 31, 32, 26, 25, 32, 26, 32, 33, 27, 26, 33, 27, 33, 34, 28, 27, 34,
         28, 34, 35, 29, 28, 35, 29, 35, 36, 30, 29, 36, 30, 36, 31, 25, 30, 31, 32, 31, 37, 33, 32, 37, 34, 33, 37, 35,
         34, 37, 36, 35, 37, 31, 36, 37
    ]

    # create the mesh
    meshFn = om2.MFnMesh()
    meshFn.create(vertices, polygonFaces, polygonConnects, parent=parentObj)

    return parentName


def createRigidBody(name, radius=1.0, height=2.0, parent=None):
    """
    Creates a capsule rigid body.

    Args:
        name(str): A mesh name.
        radius(float): The capsule radius.
        height(float): The capsule height.
        parent(str): An optional parent node.

    Returns:
        The capsule joint.
    """

    # Create a capsule joint
    joint = cmds.createNode('joint', name='%s_rb' % name)

    # Generate capsule
    mesh = createCapsule(height=height, radius=radius, name='%s_rb_capsule' % name)

    # Apply rigid body material
    assignPhysicsMaterial(mesh)

    # Lock and hide transformations
    for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']:
        cmds.setAttr('%s.%s' % (mesh, attr), lock=True, k=False, cb=False)

    # Parent mesh
    cmds.parent(mesh, joint)
    if parent is not None:
        cmds.parent(joint, parent)

    return joint


def createPhysicsMaterial():
    """
    Creates a new Skyrim physics material.

    Returns:
        str: The material node.
    """
    # Create the phong shader
    material = cmds.shadingNode('phong', asShader=1, name=RB_MATERIAL_NAME)
    SG = cmds.sets(renderable=1, noSurfaceShader=1, empty=1, name=f'{RB_MATERIAL_NAME}_sg')
    cmds.connectAttr(f'{material}.outColor', f'{SG}.surfaceShader', f=1)

    # Set shader attributes
    cmds.setAttr(f'{RB_MATERIAL_NAME}.color', 0.9599999785423279, 0.800000011920929, 0.6899999976158142)
    cmds.setAttr(f'{RB_MATERIAL_NAME}.transparency', 0.8999999761581421, 0.8999999761581421, 0.8999999761581421)
    cmds.setAttr(f'{RB_MATERIAL_NAME}.ambientColor', 0.9599999785423279, 0.800000011920929, 0.6899999976158142)
    cmds.setAttr(f'{RB_MATERIAL_NAME}.incandescence', 0.9599999785423279, 0.800000011920929, 0.6899999976158142)
    cmds.setAttr(f'{RB_MATERIAL_NAME}.specularColor', 0.20000000298023224, 0.20000000298023224, 0.20000000298023224)
    cmds.setAttr(f'{RB_MATERIAL_NAME}.reflectivity', 1.0)
    cmds.setAttr(f'{RB_MATERIAL_NAME}.diffuse', 1.0)
    cmds.setAttr(f'{RB_MATERIAL_NAME}.cosinePower', 2.0)
    cmds.addAttr(RB_MATERIAL_NAME, ln='CollisionLayer', dt='string')
    cmds.setAttr(f'{RB_MATERIAL_NAME}.CollisionLayer', 'SKYL_BIPED', type='string')

    return material


def assignPhysicsMaterial(mesh):
    """
    Assigns a physics material in the scene to a mesh.
    If a material does not exist, this will create one.

    Args:
        mesh(str): A mesh node.
    """
    # Find a material in the scene
    material = None
    for _material in cmds.ls(f'{RB_MATERIAL_NAME}*', type='phong'):
        material = _material

    # Create one if none were found
    if material is None:
        material = createPhysicsMaterial()

    # Assign the material
    shadingGroup = cmds.sets(empty=True, renderable=True, noSurfaceShader=True, name=f"{material}_sg")
    cmds.connectAttr(f'{material}.outColor', f'{shadingGroup}.surfaceShader', f=True)
    cmds.sets(mesh, e=True, forceElement=shadingGroup)


def getCapsuleMatrix(points):
    """
    Gets a capsule matrix given vertex positions and a pivot position.

    Args:
        points(list): A list of vertex positions.

    Returns:
        MMatrix: A capsule matrix.
    """
    points = [om2.MVector(point) for point in points]

    xVector = (points[CAPSULE_END_ID] - points[CAPSULE_START_ID]).normal()
    upVector = (points[CAPSULE_Z_UP_ID] - points[CAPSULE_START_ID]).normal()
    yVector = (xVector ^ upVector).normal()
    zVector = (xVector ^ yVector).normal()
    origin = points[CAPSULE_START_ID]
    capsuleMatrix = om2.MMatrix([
        [xVector[0], xVector[1], xVector[2], 0.0],
        [yVector[0], yVector[1], yVector[2], 0.0],
        [zVector[0], zVector[1], zVector[2], 0.0],
        [origin[0], origin[1], origin[2], 1.0],
    ])
    return capsuleMatrix


def getCapsulePivot(points):
    """
    Gets the pivot point from a list of capsule points.

    Args:
        points(list): A list of vertex positions.

    Returns:
        MVector: A pivot point.
    """
    points = [om2.MVector(point) for point in points]
    return points[CAPSULE_START_ID]


def _composeMatrix(translate=None, rotate=None, scale=None):
    """
    Composes a matrix given the individual transformations.

    Args:
        translate(MVector or tuple): The translation component.
        rotate(MEulerRotation or tuple): The rotation component.
        scale(MVector or tuple): The scale component.

    Returns:
        MMatrix: A matrix value.
    """
    matrix = om2.MTransformationMatrix()
    if translate:
        matrix.setTranslation(om2.MVector(translate), om2.MSpace.kWorld)
    if rotate:
        if not isinstance(rotate, om2.MEulerRotation):
            rotate = om2.MEulerRotation([math.radians(angle) for angle in rotate])
        matrix.setRotation(rotate)
    if scale:
        matrix.setScale(scale, om2.MSpace.kWorld)
    return matrix.asMatrix()


def _decomposeMatrix(matrix):
    """
    Decomposes the translation component of a matrix.

    Args:
        matrix(MMatrix): A matrix.

    Returns:
        MVector: The translation component.
    """
    return om2.MTransformationMatrix(matrix).translation(om2.MSpace.kWorld)


def updateCapsule(mesh, radius=None, height=None):
    """
    Updates the height and radius of a capsule mesh.

    Args:
        mesh(str): A mesh name.
        radius(float): The new radius.
        height(float): The new height.
    """

    # Get the mesh node
    if not cmds.nodeType(mesh) == 'mesh':
        mesh = cmds.listRelatives(mesh, type='mesh', fullPath=True)[0]

    # Get the mesh vertex positions
    vertices = cmds.ls('%s.vtx[*]' % mesh, fl=True)
    vertexPoints = [om2.MVector(cmds.xform(v, t=True, ws=True, q=True)) for v in vertices]

    # Get the local capsule matrix
    capsuleMatrix = getCapsuleMatrix(vertexPoints)

    # Determine the height and radius if not set
    if height is not None and radius is None:
        radius = getCapsuleRadius(mesh) - ((height - getCapsuleHeight(mesh)) / 2.0)
    elif height is None and radius is not None:
        height = max(0.0, getCapsuleHeight(mesh) - ((radius - getCapsuleRadius(mesh)) * 2.0))
    elif height is None and radius is None:
        radius = getCapsuleRadius(mesh)
        height = getCapsuleHeight(mesh)

    # Generate new vertex positions
    newVertexPoints = capsulePoints(height, radius)

    # Convert positions from capsule space to object space
    newVertexPoints = [_decomposeMatrix(_composeMatrix(point) * capsuleMatrix) for point in newVertexPoints]

    # Update vertex positions
    try:
        cmds.undoInfo(openChunk=True)
        for vertex, point in zip(vertices, newVertexPoints):
            cmds.xform(vertex, t=point, ws=True)
    finally:
        cmds.undoInfo(closeChunk=True)


def transformCapsule(mesh, translate=(0,0,0), rotate=(0,0,0), scale=(1,1,1), space=om2.MSpace.kWorld):
    """
    Applies a transformation to a capsule mesh.

    Spaces:
        kWorld: Transforms in world space.
        kObject: Transforms in local transform space.
        kTransform: Transforms in capsule space.

    Args:
        mesh(str): A capsule node name.
        translate(list): The translation.
        rotate(list): The rotation.
        scale(list): The scale.
        space(int): The MSpace constant to apply the transformation.
    """
    # Get the mesh node
    if not cmds.nodeType(mesh) == 'mesh':
        mesh = cmds.listRelatives(mesh, type='mesh', fullPath=True)[0]

    # Get the mesh vertex positions
    vertices = cmds.ls('%s.vtx[*]' % mesh, fl=True)
    vertexPoints = [om2.MVector(cmds.xform(v, t=True, ws=True, q=True)) for v in vertices]

    # Get the capsule matrix
    capsuleMatrix = om2.MMatrix.kIdentity
    if space == om2.MSpace.kObject:
        parent = cmds.listRelatives(mesh, parent=True, fullPath=True)[0]
        capsuleMatrix = om2.MMatrix(cmds.xform(parent, m=True, q=True, ws=True))
    elif space == om2.MSpace.kTransform:
        capsuleMatrix = getCapsuleMatrix(vertexPoints)

    # Convert vertex positions into local space
    vertexMatrices = [_composeMatrix(point) * capsuleMatrix.inverse() for point in vertexPoints]

    # Generate the transformation matrix
    matrix = _composeMatrix(translate, rotate, scale)

    # Apply transformation to points
    newVertexPoints = [_decomposeMatrix(pointMatrix * matrix * capsuleMatrix) for pointMatrix in vertexMatrices]

    # Update vertex positions
    try:
        cmds.undoInfo(openChunk=True)
        for vertex, point in zip(vertices, newVertexPoints):
            cmds.xform(vertex, t=point, ws=True)
    finally:
        cmds.undoInfo(closeChunk=True)


def aimCapsule(mesh, target):
    """
    Aims a capsule mesh at a target transform or position.

    Args:
        mesh(str): A capsule mesh name.
        target(str or MVector): A transform name or position vector.
    """
    # Get the mesh node
    if not cmds.nodeType(mesh) == 'mesh':
        mesh = cmds.listRelatives(mesh, type='mesh', fullPath=True)[0]

    # Get the target vector
    if not isinstance(target, (om2.MVector, tuple, list)):
        target = cmds.xform(target, t=True, ws=True, q=True)
    targetMatrix = _composeMatrix(om2.MVector(target))

    # Get the mesh vertex positions
    points = getMeshPoints(mesh)

    # Get the capsule matrix
    capsuleMatrix = getCapsuleMatrix(points)

    # Convert the target matrix into capsule space
    targetMatrix = targetMatrix * capsuleMatrix.inverse()
    targetPoint = _decomposeMatrix(targetMatrix)

    startVector = om2.MVector(1,0,0)
    endVector = targetPoint.normal()
    rotation = endVector.rotateTo(startVector)
    rotation = rotation.asEulerRotation()

    # Rotate the capsule towards the target
    transformCapsule(mesh, rotate=rotation, space=om2.MSpace.kObject)


