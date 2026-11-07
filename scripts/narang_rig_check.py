"""나랑이 리그 검사. 각 함수는 문제 문장 목록을 돌려주며, 비어 있으면 통과다."""
import bpy
from mathutils import Quaternion, Vector

RIG_NAME = "NR_Rig"
RIG_COLLECTION = "NARANG_Rig"
BASE_COLLECTION = "NARANG_Base"

CENTER_BONES = {"torso", "head"}
LIMB_BONES = {"upper_arm", "forearm", "hand", "thigh", "shin", "foot"}
CONTROL_BONES = {"hand_ik", "foot_ik", "elbow_pole", "knee_pole"}
IK_CHAINS = {"forearm": ("hand_ik", "elbow_pole"), "shin": ("foot_ik", "knee_pole")}
ROTATION_COPIES = {"hand": "hand_ik", "foot": "foot_ik"}
SIDES = ("L", "R")

PARTS_WITH_SIDES = {"NR_Arm", "NR_Hand", "NR_Bracelet", "NR_Leg", "NR_Shoe", "NR_Leg_Plate", "NR_Leg_Plate_Dots"}
REST_LIMIT = 1e-5
WEIGHT_LIMIT = 1e-4
FOOT_LIMIT = 1e-4


def sided(names):
    return {"%s.%s" % (name, side) for name in names for side in SIDES}


DEFORM_BONES = CENTER_BONES | sided(LIMB_BONES)
CTRL_BONES = {"root"} | sided(CONTROL_BONES)


def check_bones():
    rig = bpy.data.objects.get(RIG_NAME)
    if rig is None or rig.type != "ARMATURE":
        return ["리그 %s가 없다" % RIG_NAME]
    problems = []
    collections = {c.name for c in rig.users_collection}
    if RIG_COLLECTION not in collections or BASE_COLLECTION in collections:
        problems.append("리그가 %s에 없거나 %s에 들어 있다" % (RIG_COLLECTION, BASE_COLLECTION))

    bones = rig.data.bones
    names = {b.name for b in bones}
    if names != DEFORM_BONES | CTRL_BONES:
        problems.append("본 구성이 다르다 " + ", ".join(sorted(names ^ (DEFORM_BONES | CTRL_BONES))))
        return problems

    deform = {b.name for b in bones if b.use_deform}
    if deform != DEFORM_BONES:
        problems.append("변형 본이 다르다 " + ", ".join(sorted(deform ^ DEFORM_BONES)))

    for bone in bones:
        if not bone.name.endswith(".L"):
            continue
        other = bones[bone.name[:-1] + "R"]
        for left, right in ((bone.head_local, other.head_local), (bone.tail_local, other.tail_local)):
            if abs(left.x + right.x) > 1e-5 or abs(left.y - right.y) > 1e-5 or abs(left.z - right.z) > 1e-5:
                problems.append("좌우가 대칭이 아니다 " + bone.name)
                break

    for side in SIDES:
        for name, (target, pole) in IK_CHAINS.items():
            pose_bone = rig.pose.bones["%s.%s" % (name, side)]
            found = [c for c in pose_bone.constraints if c.type == "IK"]
            if len(found) != 1:
                problems.append("IK 제약이 하나가 아니다 " + pose_bone.name)
                continue
            ik = found[0]
            if (ik.chain_count != 2 or ik.target != rig or ik.subtarget != "%s.%s" % (target, side)
                    or ik.pole_target != rig or ik.pole_subtarget != "%s.%s" % (pole, side)):
                problems.append("IK 설정이 다르다 " + pose_bone.name)
        for name, target in ROTATION_COPIES.items():
            pose_bone = rig.pose.bones["%s.%s" % (name, side)]
            found = [c for c in pose_bone.constraints if c.type == "COPY_ROTATION"]
            if len(found) != 1 or found[0].subtarget != "%s.%s" % (target, side):
                problems.append("회전 복사가 다르다 " + pose_bone.name)

    groups = {c.name: {b.name for b in c.bones} for c in rig.data.collections}
    if groups.get("DEF") != DEFORM_BONES or groups.get("CTRL") != CTRL_BONES:
        problems.append("본 컬렉션 구성이 다르다")
    return problems


def parts():
    return list(bpy.data.collections[BASE_COLLECTION].objects)


def armature_modifiers(obj):
    return [m for m in obj.modifiers if m.type == "ARMATURE"]


def check_binding():
    problems = []
    for obj in parts():
        found = armature_modifiers(obj)
        if len(found) != 1 or found[0].object is None or found[0].object.name != RIG_NAME:
            problems.append("Armature 모디파이어가 맞지 않다 " + obj.name)
            continue
        kinds = [m.type for m in obj.modifiers]
        index = kinds.index("ARMATURE")
        if "MIRROR" in kinds and kinds.index("MIRROR") > index:
            problems.append("Armature가 Mirror 앞에 있다 " + obj.name)
        if "SUBSURF" in kinds and kinds.index("SUBSURF") < index:
            problems.append("Armature가 Subdivision 뒤에 있다 " + obj.name)
        if any(abs(sum(g.weight for g in v.groups) - 1.0) > WEIGHT_LIMIT for v in obj.data.vertices):
            problems.append("웨이트 합이 1이 아니다 " + obj.name)
        if obj.name in PARTS_WITH_SIDES:
            names = {g.name for g in obj.vertex_groups}
            left = {n for n in names if n.endswith(".L")}
            right = {n for n in names if n.endswith(".R")}
            if not left or {n[:-1] + "R" for n in left} != right:
                problems.append(".L, .R 그룹이 짝이 아니다 " + obj.name)
            indices = {obj.vertex_groups[n].index for n in right}
            if any(g.group in indices for v in obj.data.vertices for g in v.groups):
                problems.append(".R 그룹이 비어 있지 않다 " + obj.name)
    return problems


def evaluated_coords(name):
    """모디파이어 적용 결과의 월드 좌표."""
    obj = bpy.data.objects[name]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    depsgraph.update()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    coords = [evaluated.matrix_world @ v.co for v in mesh.vertices]
    evaluated.to_mesh_clear()
    return coords


def largest_change(before, after):
    return max((a - b).length for a, b in zip(after, before))


def snapshot_pose(rig):
    return {b.name: (b.location.copy(), b.rotation_quaternion.copy(), b.rotation_euler.copy(),
                     tuple(b.rotation_axis_angle), b.rotation_mode, b.scale.copy())
            for b in rig.pose.bones}


def restore_pose(rig, saved):
    for name, (location, quaternion, euler, axis_angle, mode, scale) in saved.items():
        bone = rig.pose.bones[name]
        bone.location, bone.rotation_quaternion, bone.rotation_euler = location, quaternion, euler
        bone.rotation_axis_angle, bone.rotation_mode, bone.scale = axis_angle, mode, scale


def clear_pose(rig):
    """회전 방식과 상관없이 모든 회전 값을 비운다."""
    for bone in rig.pose.bones:
        bone.location = (0, 0, 0)
        bone.rotation_quaternion = Quaternion()
        bone.rotation_euler = (0, 0, 0)
        bone.rotation_axis_angle = (0, 0, 1, 0)
        bone.scale = (1, 1, 1)


def move_bone(rig, name, delta):
    """포즈 본을 월드 기준으로 옮긴다. 리그 오브젝트는 원점에 있다."""
    bone = rig.pose.bones[name]
    bone.location = bone.bone.matrix_local.to_3x3().inverted() @ Vector(delta)


def bound_coords():
    return {obj.name: evaluated_coords(obj.name) for obj in parts()}


def check_rest():
    """현재 포즈와 상관없이, 기본 자세에서 리그가 메시를 움직이지 않는지 잰다."""
    rig = bpy.data.objects[RIG_NAME]
    saved, position = snapshot_pose(rig), rig.data.pose_position
    modifiers = [m for obj in parts() for m in armature_modifiers(obj)]
    problems = []
    try:
        for modifier in modifiers:
            modifier.show_viewport = False
        baseline = bound_coords()
        for modifier in modifiers:
            modifier.show_viewport = True
        clear_pose(rig)
        for mode in ("REST", "POSE"):
            rig.data.pose_position = mode
            for name, coords in bound_coords().items():
                change = largest_change(baseline[name], coords)
                if change > REST_LIMIT:
                    problems.append("%s 기본 자세가 움직였다 %s %.6f" % (mode, name, change))
    finally:
        for modifier in modifiers:
            modifier.show_viewport = True
        rig.data.pose_position = position
        restore_pose(rig, saved)
    return problems


def side_changes(before, after):
    """x>0 쪽과 x<0 쪽 각각의 가장 큰 이동량."""
    left = [(a - b).length for a, b in zip(after, before) if b.x > 0]
    right = [(a - b).length for a, b in zip(after, before) if b.x < 0]
    return max(left), max(right)


def check_motion():
    rig = bpy.data.objects[RIG_NAME]
    saved, position = snapshot_pose(rig), rig.data.pose_position
    problems = []
    try:
        rig.data.pose_position = "POSE"
        clear_pose(rig)
        shoe, body, hand = (evaluated_coords(n) for n in ("NR_Shoe", "NR_Body", "NR_Hand"))

        move_bone(rig, "torso", (0, 0, -0.03))
        change = largest_change(shoe, evaluated_coords("NR_Shoe"))
        if change > FOOT_LIMIT:
            problems.append("몸통을 내리니 신발이 움직였다 %.6f" % change)
        change = largest_change(body, evaluated_coords("NR_Body"))
        if abs(change - 0.03) > FOOT_LIMIT:
            problems.append("몸통 이동량이 다르다 %.6f" % change)
        clear_pose(rig)

        for bone, moving, still in (("hand_ik.L", 0, 1), ("hand_ik.R", 1, 0)):
            move_bone(rig, bone, (0, 0, 0.05))
            changes = side_changes(hand, evaluated_coords("NR_Hand"))
            if changes[moving] < 0.01 or changes[still] > REST_LIMIT:
                problems.append("%s 좌우 이동이 다르다 %.6f %.6f" % (bone, changes[0], changes[1]))
            clear_pose(rig)
    finally:
        rig.data.pose_position = position
        restore_pose(rig, saved)
    return problems
