"""나랑이 리그. 본 23개와 IK를 만들고 25개 파트에 웨이트를 준다.

메시를 다시 만들면 웨이트가 사라지므로 build_all()이 메시 다음에 이 스크립트를 호출한다.
NR_Rig 오브젝트는 지우지 않고 재사용한다. 지우면 거기 연결된 애니메이션이 끊긴다.

좌표는 docs/superpowers/specs/2026-11-07-narang-rig-design.md 기준이다. 앞이 -Y이므로 +X가 왼쪽(.L)이다.
"""
from contextlib import contextmanager

import bpy
from mathutils import Vector

import narang_rig_check

RIG_NAME = "NR_Rig"
RIG_COLLECTION = "NARANG_Rig"
BASE_COLLECTION = "NARANG_Base"
CONSTRAINT_PREFIX = "NR_"

UP = (0, 0, 1)
FRONT = (0, -1, 0)

SHOULDER = (0.19, 0.004, 0.3935)
ELBOW = (0.2875, 0.010, 0.3935)
WRIST = (0.346, 0.004, 0.3935)
HAND_TIP = (0.46, 0.004, 0.39)
HIP = (0.1035, 0.0, 0.18)
KNEE = (0.1035, -0.006, 0.14)
ANKLE = (0.1035, 0.0, 0.05)
TOE = (0.1035, -0.08, 0.02)
ELBOW_POLE = (0.2875, 0.25, 0.3935)
KNEE_POLE = (0.1035, -0.25, 0.14)
POLE_LENGTH = 0.05

# 이름: (시작, 끝, 부모, 부모에 연결, 본의 Z축이 향할 방향)
CENTER = {
    "root": ((0, 0, 0), (0, 0, 0.1), None, False, FRONT),
    "torso": ((0, 0, 0.17), (0, 0, 0.45), "root", False, FRONT),
    "head": ((0, 0, 0.45), (0, 0, 0.75), "torso", False, FRONT),
}
# 한쪽 본. 이름의 %s 자리에 L, R이 들어가고 R은 X를 뒤집는다
SIDE = {
    "upper_arm.%s": (SHOULDER, ELBOW, "torso", False, UP),
    "forearm.%s": (ELBOW, WRIST, "upper_arm.%s", True, UP),
    "hand.%s": (WRIST, HAND_TIP, "forearm.%s", True, UP),
    "thigh.%s": (HIP, KNEE, "torso", False, FRONT),
    "shin.%s": (KNEE, ANKLE, "thigh.%s", True, FRONT),
    "foot.%s": (ANKLE, TOE, "shin.%s", True, UP),
    "hand_ik.%s": (WRIST, HAND_TIP, "root", False, UP),
    "foot_ik.%s": (ANKLE, TOE, "root", False, UP),
    "elbow_pole.%s": (ELBOW_POLE, (ELBOW_POLE[0], ELBOW_POLE[1] + POLE_LENGTH, ELBOW_POLE[2]), "root", False, UP),
    "knee_pole.%s": (KNEE_POLE, (KNEE_POLE[0], KNEE_POLE[1] - POLE_LENGTH, KNEE_POLE[2]), "root", False, UP),
}
CONTROLS = ("root", "hand_ik", "foot_ik", "elbow_pole", "knee_pole")
# IK를 거는 본: (체인 시작 본, 목표, 폴)
IK_CHAINS = {"forearm": ("upper_arm", "hand_ik", "elbow_pole"), "shin": ("thigh", "foot_ik", "knee_pole")}
ROTATION_COPIES = {"hand": "hand_ik", "foot": "foot_ik"}
DEF_COLOR, CTRL_COLOR = "THEME04", "THEME01"


def flip(point, side):
    return Vector((-point[0] if side == "R" else point[0], point[1], point[2]))


def bone_table():
    """이름: (시작, 끝, 부모, 연결, Z축 방향). 좌우를 펼친 전체 목록이다."""
    table = {name: (Vector(a), Vector(b), parent, connect, Vector(axis))
             for name, (a, b, parent, connect, axis) in CENTER.items()}
    for side in ("L", "R"):
        for name, (a, b, parent, connect, axis) in SIDE.items():
            table[name % side] = (flip(a, side), flip(b, side), parent % side if "%s" in parent else parent,
                                  connect, flip(axis, side))
    return table


EXPECTED_BONES = set(bone_table())


def is_control(name):
    return name.split(".")[0] in CONTROLS


def to_object_mode():
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def rig_collection():
    collection = bpy.data.collections.get(RIG_COLLECTION)
    if collection is None:
        collection = bpy.data.collections.new(RIG_COLLECTION)
    if collection.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(collection)
    return collection


def find_layer_collection(layer, name):
    if layer.name == name:
        return layer
    for child in layer.children:
        found = find_layer_collection(child, name)
        if found is not None:
            return found
    return None


def get_rig():
    """사용자가 리그를 다른 컬렉션에도 넣어 두었다면 그대로 두고, NARANG_Rig에만 빠짐없이 넣는다."""
    rig = bpy.data.objects.get(RIG_NAME)
    collection = rig_collection()
    if rig is None:
        rig = bpy.data.objects.new(RIG_NAME, bpy.data.armatures.new(RIG_NAME))
    if rig.type != "ARMATURE":
        raise RuntimeError("%s가 아마추어가 아니다. 이름을 바꾸거나 지운 뒤 다시 실행한다" % RIG_NAME)
    if rig.name not in collection.objects:
        collection.objects.link(rig)
    return rig


@contextmanager
def shown(rig):
    """편집과 검사 동안만 리그와 파트를 보이게 하고, 끝나면 사용자의 표시 설정으로 돌린다."""
    def layer(name):
        return find_layer_collection(bpy.context.view_layer.layer_collection, name)

    names = (RIG_COLLECTION, BASE_COLLECTION)
    saved = {n: (layer(n).exclude, layer(n).hide_viewport, bpy.data.collections[n].hide_viewport) for n in names}
    rig_saved = (rig.hide_viewport, rig.hide_get())
    try:
        for name in names:
            layer(name).exclude = False
            layer(name).hide_viewport = False
            bpy.data.collections[name].hide_viewport = False
        rig.hide_viewport = False
        rig.hide_set(False)
        yield rig
    finally:
        to_object_mode()
        rig.hide_viewport = rig_saved[0]
        for name, (exclude, hidden, disabled) in saved.items():
            bpy.data.collections[name].hide_viewport = disabled
            layer(name).hide_viewport = hidden
            layer(name).exclude = exclude
        if not saved[RIG_COLLECTION][0]:
            rig.hide_set(rig_saved[1])


def build_bones(rig):
    """이름이 같은 본은 그대로 고쳐 쓴다. 포즈와 애니메이션이 본 이름에 묶여 있기 때문이다."""
    table = bone_table()
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    bones = rig.data.edit_bones
    for bone in list(bones):
        if bone.name not in table:
            bones.remove(bone)
    for name, (head, tail, _, _, axis) in table.items():
        bone = bones.get(name) or bones.new(name)
        bone.parent = None
        bone.use_connect = False
        bone.head = head
        bone.tail = tail
        bone.align_roll(axis)
    for name, (_, _, parent, connect, _) in table.items():
        bone = bones[name]
        bone.parent = bones[parent] if parent else None
        bone.use_connect = connect
        bone.use_deform = not is_control(name)
    bpy.ops.object.mode_set(mode="OBJECT")


def build_collections(rig):
    """스크립트가 만든 DEF, CTRL만 다시 만든다. 사용자가 만든 본 컬렉션은 남긴다."""
    data = rig.data
    for collection in [c for c in data.collections if c.name in ("DEF", "CTRL")]:
        data.collections.remove(collection)
    deform = data.collections.new("DEF")
    control = data.collections.new("CTRL")
    for bone in data.bones:
        (control if is_control(bone.name) else deform).assign(bone)
        bone.color.palette = CTRL_COLOR if is_control(bone.name) else DEF_COLOR


def pole_angle(base, end, pole):
    """IK가 기본 자세를 그대로 두는 폴 각도. base는 체인 시작 본, end는 체인 끝 본이다."""
    chain = end.tail_local - base.head_local
    normal = chain.cross(pole.head_local - base.head_local)
    direction = base.tail_local - base.head_local
    projected = normal.cross(direction)
    x_axis = base.matrix_local.to_3x3().col[0]
    angle = x_axis.angle(projected)
    return -angle if x_axis.cross(projected).dot(direction) > 0 else angle


def is_own_constraint(rig, constraint):
    """NR_ 이름이거나, 이름 규칙 전에 만든 것처럼 이 리그의 IK 컨트롤을 향하는 IK, 회전 복사 제약이다."""
    if constraint.name.startswith(CONSTRAINT_PREFIX):
        return True
    return (constraint.type in ("IK", "COPY_ROTATION") and getattr(constraint, "target", None) == rig
            and constraint.subtarget.split(".")[0] in ("hand_ik", "foot_ik"))


def build_constraints(rig):
    """스크립트가 만든 제약은 이름 앞에 NR_를 붙여 구분하고 그것만 지운다. 사용자가 단 제약은 남긴다."""
    bones = rig.data.bones
    for pose_bone in rig.pose.bones:
        for constraint in [c for c in pose_bone.constraints if is_own_constraint(rig, c)]:
            pose_bone.constraints.remove(constraint)
    for side in ("L", "R"):
        for name, (base, target, pole) in IK_CHAINS.items():
            full = "%s.%s" % (name, side)
            ik = rig.pose.bones[full].constraints.new("IK")
            ik.name = CONSTRAINT_PREFIX + "IK"
            ik.target = rig
            ik.subtarget = "%s.%s" % (target, side)
            ik.pole_target = rig
            ik.pole_subtarget = "%s.%s" % (pole, side)
            ik.chain_count = 2
            ik.pole_angle = pole_angle(bones["%s.%s" % (base, side)], bones[full], bones["%s.%s" % (pole, side)])
        for name, target in ROTATION_COPIES.items():
            copy = rig.pose.bones["%s.%s" % (name, side)].constraints.new("COPY_ROTATION")
            copy.name = CONSTRAINT_PREFIX + "Copy_Rotation"
            copy.target = rig
            copy.subtarget = "%s.%s" % (target, side)


def build_armature():
    to_object_mode()
    rig = get_rig()
    rig.show_in_front = True
    rig.data.pose_position = "POSE"
    with shown(rig):
        build_bones(rig)
    build_collections(rig)
    build_constraints(rig)
    return rig


# 본 하나에 100% 붙는 파트. 이름의 %s 자리에 좌우가 들어간다
RIGID_PARTS = {
    **{"NR_Helmet_" + n: "head" for n in ("Shell", "Visor", "Rim", "Smile", "Ear", "Ear_Ring")},
    **{"NR_" + n: "torso" for n in ("Body", "Neck_Ring", "Collar_Band", "Collar_Dots", "Console_Frame", "Console_Face",
                                    "Console_Red", "Console_Cross", "Screen_Frame", "Heart_Screen", "Heart", "Wing")},
    "NR_Hand": "hand.%s",
    "NR_Bracelet": "forearm.%s",
    "NR_Leg_Plate": "shin.%s",
    "NR_Leg_Plate_Dots": "shin.%s",
    "NR_Shoe": "foot.%s",
}
# 혼합 구간: 이 값 아래는 앞의 본, 위는 뒤의 본이다
ELBOW_BLEND = (0.265, 0.31)
KNEE_BLEND = (0.125, 0.155)
ANKLE_BLEND = (0.046, 0.06)


def ramp(value, blend):
    return min(max((value - blend[0]) / (blend[1] - blend[0]), 0.0), 1.0)


def arm_weights(co):
    t = ramp(co.x, ELBOW_BLEND)
    return {"upper_arm.L": 1.0 - t, "forearm.L": t}


def leg_weights(co):
    thigh = ramp(co.z, KNEE_BLEND)
    foot = 1.0 - ramp(co.z, ANKLE_BLEND)
    return {"thigh.L": thigh, "foot.L": foot, "shin.L": 1.0 - thigh - foot}


BLENDED_PARTS = {"NR_Arm": arm_weights, "NR_Leg": leg_weights}


def part_weights(name):
    """파트의 정점 좌표를 받아 {그룹 이름: 웨이트}를 돌려주는 함수."""
    if name in BLENDED_PARTS:
        return BLENDED_PARTS[name]
    bone = RIGID_PARTS[name]
    bone = bone % "L" if "%s" in bone else bone
    return lambda co: {bone: 1.0}


def weigh_part(obj):
    """미러는 .L 그룹을 .R로 옮겨 주지만 대상 그룹이 있어야 하므로 빈 .R 그룹도 만든다."""
    obj.vertex_groups.clear()
    weights = part_weights(obj.name)
    for vertex in obj.data.vertices:
        for name, weight in weights(vertex.co).items():
            if weight <= 0.0:
                continue
            group = obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
            group.add([vertex.index], weight, "REPLACE")
    for group in list(obj.vertex_groups):
        if group.name.endswith(".L"):
            obj.vertex_groups.new(name=group.name[:-1] + "R")


def add_armature_modifier(obj, rig):
    for modifier in [m for m in obj.modifiers if m.type == "ARMATURE"]:
        obj.modifiers.remove(modifier)
    modifier = obj.modifiers.new("Armature", "ARMATURE")
    modifier.object = rig
    modifier.use_vertex_groups = True
    modifier.use_bone_envelopes = False
    kinds = [m.type for m in obj.modifiers]
    obj.modifiers.move(len(kinds) - 1, kinds.index("MIRROR") + 1 if "MIRROR" in kinds else 0)


def bind_parts(rig):
    for obj in bpy.data.collections[BASE_COLLECTION].objects:
        weigh_part(obj)
        add_armature_modifier(obj, rig)


def build_rig():
    rig = build_armature()
    bind_parts(rig)
    with shown(rig):
        problems = (narang_rig_check.check_bones() + narang_rig_check.check_binding()
                    + narang_rig_check.check_rest() + narang_rig_check.check_motion())
    if problems:
        raise RuntimeError("리그 검사 실패: " + "; ".join(problems))
    return {"bones": len(rig.data.bones), "bound_parts": len(narang_rig_check.parts())}
