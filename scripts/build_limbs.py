"""팔다리. 손과 엄지, 다리와 발은 각각 하나의 표면이다. 팔과 손의 경계는 팔찌 아래에 있다.

+X 쪽만 만들고 미러로 복제한다.

치수는 reference/narang_turnaround_v2.png에서 쟀다. 앞이 -Y다.
"""
import math

import bpy
from mathutils import Vector

from narang_common import (MeshBuilder, first_exit, plate, quad_sphere, replace_object, round_cone_distance,
                           smooth_min, torus)

ARM_Y = 0.004
# 팔 단면: (x, 중심 높이, 위아래 반폭, 앞뒤 반폭). 끝은 팔찌 아래에서 손 안으로 들어간다
ARM_SECTIONS = [
    (0.130, 0.3935, 0.0540, 0.0520),
    (0.180, 0.3935, 0.0575, 0.0545),
    (0.250, 0.3935, 0.0575, 0.0545),
    (0.275, 0.3935, 0.0575, 0.0545),
    (0.300, 0.3935, 0.0575, 0.0545),
    (0.325, 0.3935, 0.0575, 0.0545),
    (0.340, 0.3935, 0.0565, 0.0540),
    (0.350, 0.3935, 0.0500, 0.0480),
]
ARM_SIDES = 12
BRACELET_X = 0.346

# 손: 손바닥 안쪽 한 점에서 사방으로 표면을 찾는다. 손끝과 엄지가 이 점에서 뻗어 나가는 형태다
HAND_ORIGIN = Vector((0.372, -0.002, 0.385))
HAND_GRID = 20
# 벙어리장갑: 중심, 길이, 앞뒤, 위아래 반지름, 곡면 지수, 손끝이 처지는 양
MITTEN_CENTER = Vector((0.385, 0.008, 0.392))
MITTEN_RADII = Vector((0.0815, 0.058, 0.055))
MITTEN_POWER, MITTEN_DROOP = 2.3, 0.016
# 엄지: 뿌리는 손 안에 있고 끝만 갈라진다. (위치, 반지름)
THUMB_ROOT, THUMB_ROOT_RADIUS = Vector((0.372, -0.030, 0.371)), 0.024
THUMB_END, THUMB_END_RADIUS = Vector((0.418, -0.058, 0.363)), 0.0205
THUMB_BLEND = 0.012

# 다리와 발 단면: (높이, x 반폭, 앞쪽 깊이, 뒤쪽 깊이). 앞쪽 깊이가 낮은 곳에서 늘어나 앞코가 된다
FOOT_X = 0.1035
FOOT_TABLE = [
    (0.000, 0.036, 0.058, 0.040),
    (0.003, 0.044, 0.070, 0.049),
    (0.010, 0.050, 0.081, 0.057),
    (0.024, 0.0555, 0.0865, 0.061),
    (0.038, 0.059, 0.080, 0.0625),
    (0.050, 0.0615, 0.066, 0.0635),
    (0.058, 0.0635, 0.0645, 0.0655),
    (0.070, 0.0665, 0.0675, 0.068),
    (0.090, 0.0695, 0.0715, 0.071),
    (0.110, 0.0735, 0.0765, 0.074),
    (0.140, 0.080, 0.082, 0.080),
    (0.170, 0.080, 0.082, 0.080),
]
LEG_RINGS = [0.006, 0.015, 0.024, 0.032, 0.040, 0.046, 0.051, 0.055, 0.060, 0.070, 0.090, 0.110, 0.140, 0.170]
LEG_SIDES = 24
# 밑창 윗선: 앞뒤 위치별 높이. 뒤꿈치에서 내려갔다가 앞코에서 올라간다
SOLE_LINE = [(-0.095, 0.051), (-0.066, 0.051), (-0.045, 0.031), (-0.026, 0.022), (0.020, 0.028), (0.065, 0.0385)]
SOLE_OFFSET = 0.0018
SOLE_LEVELS = [0.0, 0.05, 0.2, 0.45, 0.7, 0.88, 1.0]

# 옆 장식판 네 귀퉁이 (안쪽 아래, 바깥 아래, 안쪽 위, 바깥 위): (둘레 각도, 높이)
PLATE = [(-70.5, 0.0636), (-37.0, 0.0602), (-70.5, 0.1117), (-37.0, 0.1264)]
PLATE_DOTS = [(-55.0, 0.1007), (-57.0, 0.0794)]


def lerp_table(table, key):
    """첫 값을 기준으로 나머지 값을 선형 보간한다."""
    if key <= table[0][0]:
        return list(table[0][1:])
    for low, high in zip(table, table[1:]):
        if key <= high[0]:
            t = (key - low[0]) / (high[0] - low[0])
            return [a + (b - a) * t for a, b in zip(low[1:], high[1:])]
    return list(table[-1][1:])


def mitten_distance(point):
    d = point - MITTEN_CENTER
    u = d.x / MITTEN_RADII.x
    d.z += MITTEN_DROOP * max(u, 0.0) ** 2
    power = MITTEN_POWER
    size = sum(abs(d[i] / MITTEN_RADII[i]) ** power for i in range(3)) ** (1.0 / power)
    return (size - 1.0) * MITTEN_RADII.z


def hand_distance(point):
    thumb = round_cone_distance(point, THUMB_ROOT, THUMB_ROOT_RADIUS, THUMB_END, THUMB_END_RADIUS)
    return smooth_min(mitten_distance(point), thumb, THUMB_BLEND)


def build_hand():
    builder = quad_sphere(HAND_GRID, lambda direction: first_exit(HAND_ORIGIN, direction, hand_distance, 0.002))
    replace_object("NR_Hand", builder.to_mesh("NR_Hand"), "NR_White", mirror=True, subsurf=1)


def build_arm():
    builder = MeshBuilder()
    rings = []
    for x, z, half_height, half_depth in ARM_SECTIONS:
        rings.append(builder.ring([
            Vector((x,
                    ARM_Y + half_depth * math.sin(2 * math.pi * k / ARM_SIDES),
                    z + half_height * math.cos(2 * math.pi * k / ARM_SIDES)))
            for k in range(ARM_SIDES)
        ]))
    for a, b in zip(rings, rings[1:]):
        builder.bridge(a, b)
    first, last = ARM_SECTIONS[0], ARM_SECTIONS[-1]
    builder.cap(rings[0], (first[0] - 0.01, ARM_Y, first[1]))
    builder.cap(rings[-1], (last[0] + 0.004, ARM_Y, last[1]))
    replace_object("NR_Arm", builder.to_mesh("NR_Arm"), "NR_White", mirror=True)


def build_bracelet():
    ring = torus((BRACELET_X, ARM_Y, 0.3935), (0, 1, 0), (0, 0, 1), 0.0565, 0.0585, 0.0105, segments=24, sides=8)
    replace_object("NR_Bracelet", ring.to_mesh("NR_Bracelet"), "NR_Gold", mirror=True, subsurf=1)


def foot_point(angle, z, offset=0.0):
    """다리 둘레 각도(라디안)와 높이의 표면 위 점. 각도 -90도가 앞이다."""
    half_x, front, back = lerp_table(FOOT_TABLE, z)
    s = math.sin(angle)
    return Vector((FOOT_X + (half_x + offset) * math.cos(angle), ((front if s < 0 else back) + offset) * s, z))


def build_leg():
    builder = MeshBuilder()
    rings = [
        builder.ring([foot_point(2 * math.pi * k / LEG_SIDES, z) for k in range(LEG_SIDES)])
        for z in LEG_RINGS
    ]
    for a, b in zip(rings, rings[1:]):
        builder.bridge(a, b)
    builder.cap(rings[0], (FOOT_X, 0.0, LEG_RINGS[0]))
    builder.cap(rings[-1], (FOOT_X, 0.0, LEG_RINGS[-1] + 0.01))
    replace_object("NR_Leg", builder.to_mesh("NR_Leg"), "NR_White", mirror=True, subsurf=1)


def sole_height(angle):
    z = 0.03
    for _ in range(6):
        z = lerp_table(SOLE_LINE, foot_point(angle, z).y)[0]
    return z


def evaluated_points(name):
    obj = bpy.data.objects[name]
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    points = [v.co.copy() for v in mesh.vertices]
    evaluated.to_mesh_clear()
    return points


def build_sole():
    """다리 표면을 살짝 덮는 검은 밑창. 다리와 같은 표면에서 나와 앞코까지 이어진다."""
    builder = MeshBuilder()
    angles = [2 * math.pi * k / LEG_SIDES for k in range(LEG_SIDES)]
    tops = [sole_height(a) for a in angles]
    rings = [
        builder.ring([foot_point(a, top * level, SOLE_OFFSET) for a, top in zip(angles, tops)])
        for level in SOLE_LEVELS
    ]
    for a, b in zip(rings, rings[1:]):
        builder.bridge(a, b)
    builder.cap(rings[0], (FOOT_X, -0.005, 0.0))
    builder.cap(rings[-1], (FOOT_X, -0.005, 0.03))
    obj = replace_object("NR_Shoe", builder.to_mesh("NR_Shoe"), "NR_Dark", mirror=True, subsurf=1)

    bpy.context.view_layer.update()
    lowest = min(p.z for p in evaluated_points("NR_Shoe"))
    for vertex in obj.data.vertices:
        vertex.co.z -= lowest
    obj.data.update()
    bpy.context.view_layer.update()


def plate_shape(s, t):
    s, t = s * math.sqrt(1.0 - 0.2 * t * t), t * math.sqrt(1.0 - 0.2 * s * s)
    u, v = (s + 1) / 2, (t + 1) / 2
    low_in, low_out, high_in, high_out = PLATE
    angle, z = (
        (low_in[i] + (low_out[i] - low_in[i]) * u) * (1 - v) + (high_in[i] + (high_out[i] - high_in[i]) * u) * v
        for i in (0, 1)
    )
    return math.radians(angle), z


def build_leg_plate():
    builder = plate(6, lambda a, z: foot_point(a, z, 0.006), lambda a, z: foot_point(a, z, -0.012), plate_shape)
    replace_object("NR_Leg_Plate", builder.to_mesh("NR_Leg_Plate"), "NR_Dark", mirror=True, subsurf=1)

    dots = MeshBuilder()
    for degrees, z in PLATE_DOTS:
        angle = math.radians(degrees)
        center = foot_point(angle, z, 0.0065)
        normal = Vector((math.cos(angle), math.sin(angle), 0.0))
        side = Vector((-math.sin(angle), math.cos(angle), 0.0))

        def transform(p, c=center, n=normal, u=side):
            return c + u * 0.0054 * p.x + n * 0.0022 * p.y + Vector((0, 0, 0.0054 * p.z))

        dots.extend(quad_sphere(2, transform))
    replace_object("NR_Leg_Plate_Dots", dots.to_mesh("NR_Leg_Plate_Dots"), "NR_White", mirror=True, subsurf=1)


def build_limbs():
    build_arm()
    build_hand()
    build_bracelet()
    build_leg()
    build_sole()
    build_leg_plate()
