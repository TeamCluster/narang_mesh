"""팔다리: 끝이 뾰족한 날개형 팔, 벌어진 짧은 다리. +X 쪽만 만들고 미러로 복제한다."""
import math

import bpy
from mathutils import Vector

from narang_common import MeshBuilder, replace_object

# 팔 단면: (x, z, 팔 평면 안쪽 반폭, 앞뒤 반폭)
ARM_SECTIONS = [
    (0.120, 0.446, 0.055, 0.045),
    (0.176, 0.432, 0.056, 0.042),
    (0.207, 0.420, 0.050, 0.038),
    (0.232, 0.406, 0.040, 0.032),
    (0.257, 0.385, 0.032, 0.027),
    (0.279, 0.360, 0.024, 0.021),
    (0.297, 0.337, 0.018, 0.016),
    (0.310, 0.318, 0.013, 0.012),
    (0.318, 0.307, 0.007, 0.008),
]
ARM_TIP = (0.321, 0.303)
ARM_SIDES = 12

# 다리 단면: (높이, 중심 x, 중심 y, x 반폭, y 반폭)
LEG_SECTIONS = [
    (0.20, 0.095, 0.000, 0.060, 0.060),
    (0.15, 0.103, -0.003, 0.055, 0.055),
    (0.12, 0.113, -0.005, 0.047, 0.052),
    (0.09, 0.116, -0.008, 0.042, 0.052),
    (0.06, 0.122, -0.012, 0.037, 0.056),
    (0.035, 0.125, -0.018, 0.037, 0.060),
    (0.015, 0.126, -0.018, 0.037, 0.060),
    (0.006, 0.126, -0.018, 0.036, 0.058),  # 발바닥 가장자리를 잡는 루프
    (0.0, 0.126, -0.018, 0.034, 0.056),
]
LEG_SIDES = 12


def build_arm():
    builder = MeshBuilder()
    rings = []
    normals = []
    for i, (x, z, half_width, half_depth) in enumerate(ARM_SECTIONS):
        a = ARM_SECTIONS[max(i - 1, 0)]
        b = ARM_SECTIONS[min(i + 1, len(ARM_SECTIONS) - 1)]
        tangent = Vector((b[0] - a[0], 0, b[1] - a[1])).normalized()
        normal = Vector((tangent.z, 0, -tangent.x))
        normals.append(normal)
        rings.append(builder.ring([
            Vector((x, 0, z))
            + normal * half_width * math.cos(2 * math.pi * k / ARM_SIDES)
            + Vector((0, 1, 0)) * half_depth * math.sin(2 * math.pi * k / ARM_SIDES)
            for k in range(ARM_SIDES)
        ]))
    for a, b in zip(rings, rings[1:]):
        builder.bridge(a, b)
    start = ARM_SECTIONS[0]
    builder.cap(rings[0], (start[0] - 0.01, 0, start[1] + 0.003))
    builder.cap(rings[-1], (ARM_TIP[0], 0, ARM_TIP[1]))

    # 시트 팔 아래쪽의 작은 엄지 돌기
    face = (rings[5][0], rings[5][1], rings[6][1], rings[6][0])
    base = sum((builder.verts[i] for i in face), Vector()) / 4
    direction = (normals[5] + Vector((0.3, 0, -0.3))).normalized()
    builder.extrude_face(face, [base + direction * 0.007, base + direction * 0.014], [0.9, 0.55])
    replace_object("NR_Arm", builder.to_mesh("NR_Arm"), "NR_White", mirror=True)


def evaluated_points(name):
    obj = bpy.data.objects[name]
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    points = [v.co.copy() for v in mesh.vertices]
    evaluated.to_mesh_clear()
    return points


def build_leg():
    builder = MeshBuilder()
    rings = []
    for z, cx, cy, half_x, half_y in LEG_SECTIONS:
        rings.append(builder.ring([
            Vector((cx + half_x * math.cos(2 * math.pi * k / LEG_SIDES),
                    cy + half_y * math.sin(2 * math.pi * k / LEG_SIDES), z))
            for k in range(LEG_SIDES)
        ]))
    for a, b in zip(rings, rings[1:]):
        builder.bridge(a, b)
    first, last = LEG_SECTIONS[0], LEG_SECTIONS[-1]
    builder.cap(rings[0], (first[1], first[2], first[0] + 0.01))
    builder.cap(rings[-1], (last[1], last[2], 0.0))
    obj = replace_object("NR_Leg", builder.to_mesh("NR_Leg"), "NR_White", mirror=True)

    bpy.context.view_layer.update()
    lowest = min(p.z for p in evaluated_points("NR_Leg"))
    for vertex in obj.data.vertices:
        vertex.co.z -= lowest
    obj.data.update()
    bpy.context.view_layer.update()


def build_limbs():
    build_arm()
    build_leg()
