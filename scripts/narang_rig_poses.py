"""리그 확인용 테스트 포즈. 블렌더 화면이 있는 세션에서 실행한다.

render_poses("D:/NR_NARANG/renders")는 포즈마다 rig_<포즈>_<뷰>.png를 저장하고 포즈를 비운다.
"""
import math
import os

import bpy
from mathutils import Quaternion, Vector

import narang_view
from narang_rig_check import RIG_COLLECTION, RIG_NAME, clear_pose as clear_bones, move_bone

VIEWS = ("front", "right", "three_quarter")
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))

# 포즈: {"move": {본: 월드 이동}, "turn": {본: (월드 축, 각도)}}
POSES = {
    "walk": {
        "move": {"foot_ik.L": (0, -0.07, 0), "foot_ik.R": (0, 0.06, 0.024), "torso": (0, 0, -0.008),
                 "hand_ik.L": (-0.09, 0.09, -0.12), "hand_ik.R": (0.09, -0.09, -0.12)},
        "turn": {"foot_ik.R": (X, 25), "hand_ik.L": (Y, 60), "hand_ik.R": (Y, -60)},
    },
    "sit": {
        "move": {"torso": (0, 0, -0.035), "foot_ik.L": (0, -0.03, 0), "foot_ik.R": (0, -0.03, 0)},
        "turn": {},
    },
    "arms_up": {
        "move": {"hand_ik.L": (-0.046, 0, 0.106), "hand_ik.R": (0.046, 0, 0.106)},
        "turn": {"hand_ik.L": (Y, -50), "hand_ik.R": (Y, 50)},
    },
    "arms_down": {
        "move": {"hand_ik.L": (-0.101, 0, -0.1435), "hand_ik.R": (0.101, 0, -0.1435)},
        "turn": {"hand_ik.L": (Y, 70), "hand_ik.R": (Y, -70)},
    },
    "nod_forward": {"move": {}, "turn": {"head": (X, 20)}},
    "nod_back": {"move": {}, "turn": {"head": (X, -20)}},
    "turn_left": {"move": {}, "turn": {"head": (Z, 45)}},
    "turn_right": {"move": {}, "turn": {"head": (Z, -45)}},
}


def rig():
    return bpy.data.objects[RIG_NAME]


def turn_bone(armature, name, axis, degrees):
    """포즈 본을 월드 축 기준으로 돌린다. 리그 오브젝트는 원점에 있다."""
    bone = armature.pose.bones[name]
    rest = bone.bone.matrix_local.to_3x3()
    bone.rotation_mode = "QUATERNION"
    bone.rotation_quaternion = Quaternion(rest.inverted() @ axis, math.radians(degrees))


def clear_pose():
    clear_bones(rig())


def apply_pose(name):
    armature = rig()
    clear_bones(armature)
    for bone, delta in POSES[name]["move"].items():
        move_bone(armature, bone, delta)
    for bone, (axis, degrees) in POSES[name]["turn"].items():
        turn_bone(armature, bone, axis, degrees)
    bpy.context.view_layer.update()


def view_context():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                region = next(r for r in area.regions if r.type == "WINDOW")
                return window, area, region
    raise RuntimeError("3D 뷰가 없다")


def render_poses(folder, names=None):
    window, area, region = view_context()
    space = area.spaces.active
    scene = bpy.context.scene
    collection = bpy.data.collections[RIG_COLLECTION]
    saved = (scene.render.filepath, space.overlay.show_overlays, collection.hide_viewport)
    written = []
    try:
        space.overlay.show_overlays = False
        collection.hide_viewport = True
        for name in names or POSES:
            apply_pose(name)
            for view in VIEWS:
                narang_view.set_view(view)
                path = os.path.join(folder, "rig_%s_%s.png" % (name, view))
                scene.render.filepath = path
                with bpy.context.temp_override(window=window, area=area, region=region):
                    bpy.ops.render.opengl(view_context=True, write_still=True)
                written.append(path)
    finally:
        scene.render.filepath, space.overlay.show_overlays, collection.hide_viewport = saved
        clear_pose()
    return written
