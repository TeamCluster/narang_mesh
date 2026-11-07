"""헬멧. 치수는 reference/narang_turnaround_v2.png에서 쟀다 (전체 키 = 1, 797px)."""
import math

from mathutils import Vector

from narang_common import MeshBuilder, planar_uv, plate, quad_sphere, replace_object, ribbon, torus

# 쉘: 가로, 앞쪽, 뒤쪽 반지름, 중심 높이, 위쪽 높이, 아래쪽 높이. 시트의 얼굴 쪽은 뒤통수보다 납작하다
A, B_FRONT, B_BACK, ZC, TOP, BOTTOM = 0.2935, 0.259, 0.281, 0.7064, 0.2965, 0.283

# 금색 테두리 윤곽 (정면 투영): 중심 높이, 가로, 위, 아래 반지름, 곡면 지수
RIM_Z, RIM_X, RIM_UP, RIM_DOWN, RIM_POWER = 0.735, 0.248, 0.2035, 0.2638, 2.0
# 턱: 아래 방향에서 잰 각도별 반지름. 가운데 호, 안쪽 봉우리, 바깥 V자 끝 순서
CHIN = [(0.0, 0.198), (13.0, 0.200), (26.6, 0.2046), (44.0, 0.2235), (46.7, 0.2552)]

EAR_Y, EAR_Z = 0.043, 0.705
VISOR_UV = 0.52


def shell_transform(p):
    depth = B_FRONT if p.y < 0 else B_BACK
    return Vector((A * p.x, depth * p.y, ZC + (TOP if p.z > 0 else BOTTOM) * p.z))


def head_rho(z):
    dz = z - ZC
    return math.sqrt(max(1.0 - (dz / (TOP if dz >= 0 else BOTTOM)) ** 2, 0.0))


def head_normal(point):
    height = TOP if point.z >= ZC else BOTTOM
    return Vector((point.x / A ** 2, point.y / B_FRONT ** 2, (point.z - ZC) / height ** 2)).normalized()


def head_front(x, z, offset=0.0):
    """정면 좌표 (x, z)의 머리 앞면 위 점. offset만큼 바깥으로 띄운다."""
    w = math.sqrt(max(head_rho(z) ** 2 - (x / A) ** 2, 0.0))
    point = Vector((x, -B_FRONT * w, z))
    return point + head_normal(point) * offset


def chin_radius(from_down):
    for (a0, r0), (a1, r1) in zip(CHIN, CHIN[1:]):
        if from_down <= a1:
            return r0 + (r1 - r0) * (from_down - a0) / (a1 - a0)
    return CHIN[-1][1]


def outline(theta):
    """각도별 테두리 반지름."""
    degrees = (math.degrees(theta) + 180.0) % 360.0 - 180.0
    from_down = abs(degrees + 90.0)
    from_down = min(from_down, 360.0 - from_down)
    if from_down < CHIN[-1][0]:
        return chin_radius(from_down)
    c, s = math.cos(theta), math.sin(theta)
    up = RIM_UP if s > 0 else RIM_DOWN
    return ((abs(c) / RIM_X) ** RIM_POWER + (abs(s) / up) ** RIM_POWER) ** (-1.0 / RIM_POWER)


def visor_shape(s, t):
    x = s * math.sqrt(1.0 - t * t / 2.0)
    y = t * math.sqrt(1.0 - s * s / 2.0)
    rho = math.hypot(x, y)
    theta = math.atan2(y, x)
    r = (outline(theta) + 0.003) * rho
    return r * math.cos(theta), RIM_Z + r * math.sin(theta)


def rim_point(theta):
    r = outline(theta)
    return head_front(r * math.cos(theta), RIM_Z + r * math.sin(theta), 0.005)


def build_shell():
    builder = quad_sphere(8, shell_transform)
    builder.cut_half()
    replace_object("NR_Helmet_Shell", builder.to_mesh("NR_Helmet_Shell"), "NR_White", mirror=True)


def build_visor():
    builder = plate(32, lambda x, z: head_front(x, z, 0.003), lambda x, z: head_front(x, z, -0.03), visor_shape)
    builder.cut_half()
    mesh = builder.to_mesh("NR_Helmet_Visor")
    planar_uv(mesh, VISOR_UV, 0.0, RIM_Z)
    replace_object("NR_Helmet_Visor", mesh, "NR_Visor", mirror=True, subsurf=1, mirror_u=True)


def rim_angles(segments=120):
    """테두리를 나눌 각도(라디안). 턱이 꺾이는 구간은 촘촘하게 나눈다."""
    degrees = {round(90.0 + k * 360.0 / segments, 3) for k in range(segments)}
    dense = [41.0 + 0.25 * i for i in range(33)] + [a for a, _ in CHIN]
    for a in dense:
        degrees.update((round(270.0 - a, 3), round(270.0 + a, 3)))
    return [math.radians(d) for d in sorted(degrees)]


def build_rim(sides=8, half_width=0.0125, half_height=0.009):
    builder = MeshBuilder()
    angles = rim_angles()
    segments = len(angles)
    rings = []
    for k, theta in enumerate(angles):
        center = rim_point(theta)
        tangent = (rim_point(angles[(k + 1) % segments]) - rim_point(angles[k - 1])).normalized()
        normal = head_normal(center)
        side = tangent.cross(normal).normalized()
        rings.append(builder.ring([
            center
            + side * half_width * math.cos(2 * math.pi * i / sides)
            + normal * half_height * math.sin(2 * math.pi * i / sides)
            for i in range(sides)
        ]))
    for k in range(segments):
        builder.bridge(rings[k], rings[(k + 1) % segments])
    builder.cut_half()
    replace_object("NR_Helmet_Rim", builder.to_mesh("NR_Helmet_Rim"), "NR_Gold", mirror=True, subsurf=1)


def build_smile():
    """바이저 아래의 미소 모양 선."""
    points = [head_front(0.118 * i / 8, 0.485 + 0.016 * (i / 8) ** 2, 0.001) for i in range(-8, 9)]
    builder = MeshBuilder()
    ribbon(builder, points, head_normal, 0.0052, 0.0028)
    builder.cut_half()
    replace_object("NR_Helmet_Smile", builder.to_mesh("NR_Helmet_Smile"), "NR_LightGray", mirror=True, subsurf=1)


def build_ear(sides=16):
    builder = MeshBuilder()
    sections = [(0.24, 0.090), (0.297, 0.0905), (0.319, 0.0875), (0.326, 0.078), (0.3275, 0.072),
                (0.328, 0.056), (0.3295, 0.04), (0.331, 0.02)]
    rings = [
        builder.ring([
            Vector((x, EAR_Y + r * math.cos(2 * math.pi * i / sides), EAR_Z + r * math.sin(2 * math.pi * i / sides)))
            for i in range(sides)
        ])
        for x, r in sections
    ]
    for a, b in zip(rings, rings[1:]):
        builder.bridge(a, b)
    builder.cap(rings[0], (0.235, EAR_Y, EAR_Z))
    builder.cap(rings[-1], (0.3315, EAR_Y, EAR_Z))
    replace_object("NR_Helmet_Ear", builder.to_mesh("NR_Helmet_Ear"), "NR_White", mirror=True)

    ring = torus((0.3262, EAR_Y, EAR_Z), (0, 1, 0), (0, 0, 1), 0.0715, 0.0715, 0.0028, segments=32, sides=6)
    replace_object("NR_Helmet_Ear_Ring", ring.to_mesh("NR_Helmet_Ear_Ring"), "NR_Gray", mirror=True, subsurf=1)


def build_helmet():
    build_shell()
    build_visor()
    build_rim()
    build_smile()
    build_ear()
