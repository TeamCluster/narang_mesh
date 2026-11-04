"""몸통: 항아리형 몸, 주름 호스, 콘솔, 하트 스크린."""
import math

from mathutils import Vector

from narang_common import MeshBuilder, catmull, planar_uv, plate, quad_sphere, replace_object, tube

# 몸통: 가로, 앞뒤 반지름, 앞뒤 중심, 중심 높이, 위쪽, 아래쪽 높이, 곡면 지수
X, Y, YC, ZC, UP, DOWN, POWER = 0.2175, 0.177, -0.02, 0.31, 0.21, 0.22, 2.3

CONSOLE_Z = 0.415
SCREEN_Z, SCREEN_UV = 0.284, 0.30


def body_transform(p):
    r = math.hypot(p.x, p.y)
    p = p / (r ** POWER + abs(p.z) ** POWER) ** (1.0 / POWER)
    return Vector((X * p.x, YC + Y * p.y, ZC + (UP if p.z > 0 else DOWN) * p.z))


def body_front(offset):
    def point(x, z):
        dz = z - ZC
        height = UP if dz > 0 else DOWN
        rho = max(1.0 - abs(dz / height) ** POWER, 0.0) ** (1.0 / POWER)
        w = math.sqrt(max(rho * rho - (x / X) ** 2, 0.0))
        return Vector((x, YC - Y * w - offset, z))
    return point


def rounded_rect(center_z, half_width, half_height, roundness):
    def shape(s, t):
        return (half_width * s * math.sqrt(1.0 - roundness * t * t),
                center_z + half_height * t * math.sqrt(1.0 - roundness * s * s))
    return shape


def panel(name, center_z, half_width, half_height, thickness, roundness=0.15, grid=6):
    builder = plate(grid, body_front(thickness), body_front(-0.02),
                    rounded_rect(center_z, half_width, half_height, roundness))
    builder.cut_half()
    return builder.to_mesh(name)


def build_hose():
    """콘솔에서 오른쪽 어깨를 돌아 백팩으로 가는 주름 호스. 한쪽에만 있다."""
    start = body_front(0.012)(-0.05, 0.418)
    control = [start, (-0.08, -0.156, 0.430), (-0.165, -0.095, 0.462), (-0.19, -0.02, 0.478),
               (-0.165, 0.055, 0.482), (-0.095, 0.11, 0.47), (-0.035, 0.135, 0.455), (-0.02, 0.16, 0.45)]
    points = catmull(control, 11)
    radii = [(0.0155, 0.0205, 0.0205)[i % 3] for i in range(len(points))]
    builder = tube(points, radii)
    replace_object("NR_Neck_Hose", builder.to_mesh("NR_Neck_Hose"), "NR_Gray", subsurf=1)


def build_buttons():
    center = body_front(0.0)(-0.025, CONSOLE_Z)
    builder = quad_sphere(3, lambda p: center + Vector((0.0145 * p.x, -0.0195 + 0.006 * p.y, 0.0145 * p.z)))
    replace_object("NR_Console_Red", builder.to_mesh("NR_Console_Red"), "NR_Red", subsurf=1)

    long, short, cx = 0.0135, 0.0048, 0.025
    plus = [(-short, -long), (short, -long), (short, -short), (long, -short), (long, short), (short, short),
            (short, long), (-short, long), (-short, short), (-long, short), (-long, -short), (-short, -short)]
    builder = MeshBuilder()
    layers = [
        builder.ring([body_front(offset)(cx + u, CONSOLE_Z + v) for u, v in plus])
        for offset in (0.021, 0.012)
    ]
    builder.bridge(layers[0], layers[1])
    for a in layers:
        builder.faces.append((a[2], a[5], a[8], a[11]))
        builder.faces.append((a[0], a[1], a[2], a[11]))
        builder.faces.append((a[2], a[3], a[4], a[5]))
        builder.faces.append((a[5], a[6], a[7], a[8]))
        builder.faces.append((a[8], a[9], a[10], a[11]))
    replace_object("NR_Console_Cross", builder.to_mesh("NR_Console_Cross"), "NR_Dark", subsurf=1)


def build_body():
    builder = quad_sphere(6, body_transform)
    builder.cut_half()
    replace_object("NR_Body", builder.to_mesh("NR_Body"), "NR_White", mirror=True)

    build_hose()
    replace_object("NR_Console_Frame", panel("NR_Console_Frame", CONSOLE_Z, 0.054, 0.031, 0.012),
                   "NR_Gray", mirror=True)
    replace_object("NR_Console_Face", panel("NR_Console_Face", CONSOLE_Z, 0.048, 0.025, 0.016),
                   "NR_White", mirror=True)
    build_buttons()

    mesh = panel("NR_Heart_Screen", SCREEN_Z, 0.131, 0.093, 0.004, roundness=0.12, grid=8)
    planar_uv(mesh, SCREEN_UV, 0.0, SCREEN_Z)
    replace_object("NR_Heart_Screen", mesh, "NR_Screen", mirror=True, mirror_u=True)
