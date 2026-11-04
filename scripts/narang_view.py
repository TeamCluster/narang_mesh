"""비교용 3D 뷰 설정."""
import math

import bpy
from mathutils import Euler, Vector

VIEWS = {
    "front": (90, 0),
    "right": (90, -90),
    "left": (90, 90),
    "back": (90, 180),
    "three_quarter": (82, 30),
}


def set_view(kind, center=(0, 0, 0.5), distance=1.9):
    tilt, turn = VIEWS[kind]
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                space = area.spaces.active
                region = space.region_3d
                region.view_perspective = "ORTHO"
                region.view_rotation = Euler((math.radians(tilt), 0, math.radians(turn))).to_quaternion()
                region.view_location = Vector(center)
                region.view_distance = distance
                space.overlay.show_floor = False
                space.overlay.show_axis_x = False
                space.overlay.show_axis_y = False
                area.tag_redraw()
