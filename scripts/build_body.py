"""몸통: 항아리형 몸, 목 링, 점 장식 띠, 콘솔, 입체 하트 화면."""
import math

from mathutils import Vector

from narang_common import MeshBuilder, plate, quad_sphere, replace_object, ribbon, torus

# 몸통: 가로, 앞뒤 반지름, 앞뒤 중심, 중심 높이, 위쪽, 아래쪽 높이, 곡면 지수
X, Y, YC, ZC, UP, DOWN, POWER = 0.219, 0.177, -0.002, 0.275, 0.205, 0.208, 2.7

CONSOLE_Z = 0.374
SCREEN_Z = 0.2455
HEART_CELL, HEART_TOP = 0.021, 0.2999
HEART_ROWS = [".XX..XX.", "XXXXXXXX", "XXXXXXXX", ".XXXXXX.", "..XXXX..", "...XX..."]
# 콘솔 왼쪽에서 목 옆으로 올라가는 띠의 정면 좌표. 시트에서 캐릭터 오른쪽에만 있다
COLLAR = [(-0.058, 0.378), (-0.0765, 0.3845), (-0.1016, 0.3908), (-0.1267, 0.399), (-0.1487, 0.4097), (-0.1631, 0.4222)]
COLLAR_DOTS = [(-0.0765, 0.385), (-0.1016, 0.3918), (-0.1279, 0.3990), (-0.1474, 0.4085), (-0.1612, 0.4210)]


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


def build_neck():
    ring = torus((0, 0.005, 0.444), (0, 1, 0), (1, 0, 0), 0.118, 0.150, 0.0235, segments=32, sides=10)
    ring.cut_half()
    replace_object("NR_Neck_Ring", ring.to_mesh("NR_Neck_Ring"), "NR_LightGray", mirror=True)


def surface_normal(point):
    return Vector((point.x / X ** 2 * 0.6, (point.y - YC) / Y ** 2, 0.25 * (point.z - ZC) / UP ** 2)).normalized()


def build_collar():
    surface = body_front(0.007)
    points = [surface(x, z) for x, z in COLLAR]
    builder = MeshBuilder()
    ribbon(builder, points, surface_normal, 0.0105, 0.008)
    replace_object("NR_Collar_Band", builder.to_mesh("NR_Collar_Band"), "NR_White", subsurf=1)

    dots = MeshBuilder()
    for x, z in COLLAR_DOTS:
        center = body_front(0.0155)(x, z)
        dots.extend(quad_sphere(2, lambda p, c=center: c + Vector((0.0056 * p.x, 0.0028 * p.y, 0.0056 * p.z))))
    replace_object("NR_Collar_Dots", dots.to_mesh("NR_Collar_Dots"), "NR_Dark", subsurf=1)


def build_buttons():
    center = body_front(0.0)(-0.0257, CONSOLE_Z)
    radius = 0.0188
    builder = quad_sphere(6, lambda p: center + Vector((radius * p.x, -0.0195 + 0.006 * p.y, radius * p.z)))
    replace_object("NR_Console_Red", builder.to_mesh("NR_Console_Red"), "NR_Red", subsurf=1)

    long, short, cx = 0.0176, 0.0052, 0.0289
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
    mesh = builder.to_mesh("NR_Console_Cross")
    mesh.shade_flat()
    replace_object("NR_Console_Cross", mesh, "NR_Dark", subsurf=0)


def heart_runs(row):
    """한 행에서 이어진 칸의 (시작, 끝) 목록."""
    runs, start = [], None
    for index, mark in enumerate(row + "."):
        if mark == "X" and start is None:
            start = index
        elif mark != "X" and start is not None:
            runs.append((start, index))
            start = None
    return runs


def build_heart():
    """픽셀 하트. 행마다 이어진 칸을 판 하나로 만든다. 각진 모양이라 Subdivision을 쓰지 않는다."""
    builder = MeshBuilder()
    left = -len(HEART_ROWS[0]) * HEART_CELL / 2
    for r, row in enumerate(HEART_ROWS):
        top = HEART_TOP - r * HEART_CELL
        for a, b in heart_runs(row):
            x0, x1 = left + a * HEART_CELL, left + b * HEART_CELL

            def shape(s, t, x0=x0, x1=x1, top=top):
                return x0 + (x1 - x0) * (s + 1) / 2, top - HEART_CELL * (1 - t) / 2

            builder.extend(plate(4, body_front(0.016), body_front(0.004), shape))
    mesh = builder.to_mesh("NR_Heart")
    mesh.shade_flat()
    replace_object("NR_Heart", mesh, "NR_Red", subsurf=0)


def build_body():
    builder = quad_sphere(6, body_transform)
    builder.cut_half()
    replace_object("NR_Body", builder.to_mesh("NR_Body"), "NR_White", mirror=True)

    build_neck()
    build_collar()
    replace_object("NR_Console_Frame", panel("NR_Console_Frame", CONSOLE_Z, 0.0634, 0.0273, 0.012),
                   "NR_Dark", mirror=True)
    replace_object("NR_Console_Face", panel("NR_Console_Face", CONSOLE_Z, 0.0585, 0.0225, 0.016),
                   "NR_White", mirror=True)
    build_buttons()

    replace_object("NR_Screen_Frame", panel("NR_Screen_Frame", SCREEN_Z, 0.1445, 0.0965, 0.006, roundness=0.03, grid=12),
                   "NR_Gray", mirror=True)
    replace_object("NR_Heart_Screen", panel("NR_Heart_Screen", SCREEN_Z, 0.1375, 0.0895, 0.0085, roundness=0.03, grid=12),
                   "NR_Screen", mirror=True)
    build_heart()
