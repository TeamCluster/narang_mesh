"""헬멧. 치수는 reference/narang_turnaround.png에서 쟀다 (전체 키 = 1)."""
import math

from mathutils import Vector

from narang_common import MeshBuilder, catmull, planar_uv, plate, quad_sphere, replace_object

# 쉘: 가로, 앞뒤 반지름, 중심 높이, 위쪽 높이, 아래쪽 높이, 아래쪽 곡면 지수
A, B, ZC, TOP, BOTTOM, POWER = 0.290, 0.263, 0.745, 0.258, 0.283, 2.6

# 금색 테두리 윤곽 (정면 투영): 중심 높이, 가로, 위, 아래 반지름, 곡면 지수
RIM_Z, RIM_X, RIM_UP, RIM_DOWN, RIM_POWER = 0.735, 0.232, 0.197, 0.215, 2.3
# 턱: 아래 가운데가 안쪽으로 꺾여 들어간다
CHIN_ANGLE, CHIN_DEPTH, CHIN_LIFT, CHIN_WIDTH = 40.0, 0.192, 0.032, 0.136

EAR_Y, EAR_Z = 0.015, 0.725
VISOR_UV = 0.52


def shell_transform(p):
    if p.z < 0:
        r = math.hypot(p.x, p.y)
        p = p / (r ** POWER + abs(p.z) ** POWER) ** (1.0 / POWER)
    return Vector((A * p.x, B * p.y, ZC + (TOP if p.z > 0 else BOTTOM) * p.z))


def head_rho(z):
    dz = z - ZC
    if dz >= 0:
        return math.sqrt(max(1.0 - (dz / TOP) ** 2, 0.0))
    return max(1.0 - (abs(dz) / BOTTOM) ** POWER, 0.0) ** (1.0 / POWER)


def head_normal(point):
    height = TOP if point.z >= ZC else BOTTOM
    return Vector((point.x / A ** 2, point.y / B ** 2, (point.z - ZC) / height ** 2)).normalized()


def head_front(x, z, offset=0.0):
    """정면 좌표 (x, z)의 머리 앞면 위 점. offset만큼 바깥으로 띄운다."""
    w = math.sqrt(max(head_rho(z) ** 2 - (x / A) ** 2, 0.0))
    point = Vector((x, -B * w, z))
    return point + head_normal(point) * offset


def outline(theta):
    """각도별 테두리 반지름."""
    degrees = (math.degrees(theta) + 180.0) % 360.0 - 180.0
    from_down = abs(degrees + 90.0)
    from_down = min(from_down, 360.0 - from_down)
    if from_down < CHIN_ANGLE:
        a = math.radians(from_down)
        r = CHIN_DEPTH
        for _ in range(6):
            x = r * math.sin(a)
            r = (CHIN_DEPTH - CHIN_LIFT * (x / CHIN_WIDTH) ** 2.5) / math.cos(a)
        return r
    c, s = math.cos(theta), math.sin(theta)
    up = RIM_UP if s > 0 else RIM_DOWN
    return ((abs(c) / RIM_X) ** RIM_POWER + (abs(s) / up) ** RIM_POWER) ** (-1.0 / RIM_POWER)


def visor_shape(s, t):
    x = s * math.sqrt(1.0 - t * t / 2.0)
    y = t * math.sqrt(1.0 - s * s / 2.0)
    rho = math.hypot(x, y)
    theta = math.atan2(y, x)
    r = (outline(theta) - 0.004) * rho
    return r * math.cos(theta), RIM_Z + r * math.sin(theta)


def rim_point(theta):
    r = outline(theta)
    return head_front(r * math.cos(theta), RIM_Z + r * math.sin(theta), 0.006)


def build_shell():
    builder = quad_sphere(8, shell_transform)
    builder.cut_half()
    replace_object("NR_Helmet_Shell", builder.to_mesh("NR_Helmet_Shell"), "NR_White", mirror=True)


def build_visor():
    builder = plate(24, lambda x, z: head_front(x, z, 0.003), lambda x, z: head_front(x, z, -0.03), visor_shape)
    builder.cut_half()
    mesh = builder.to_mesh("NR_Helmet_Visor")
    planar_uv(mesh, VISOR_UV, 0.0, RIM_Z)
    replace_object("NR_Helmet_Visor", mesh, "NR_Visor", mirror=True, subsurf=1, mirror_u=True)


def build_rim(segments=96, sides=8, half_width=0.0135, half_height=0.012):
    builder = MeshBuilder()
    step = 2 * math.pi / segments
    rings = []
    for k in range(segments):
        theta = math.pi / 2 + k * step
        center = rim_point(theta)
        tangent = (rim_point(theta + step) - rim_point(theta - step)).normalized()
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


def add_strip(builder, front_points, half_width=0.0066, half_height=0.004, sides=8):
    """머리 표면에 붙은 납작한 띠."""
    points = [head_front(x, z, 0.001) for x, z in front_points]
    rings = []
    for i, point in enumerate(points):
        tangent = (points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]).normalized()
        normal = head_normal(point)
        side = tangent.cross(normal).normalized()
        rings.append(builder.ring([
            point
            + side * half_width * math.cos(2 * math.pi * k / sides)
            + normal * half_height * math.sin(2 * math.pi * k / sides)
            for k in range(sides)
        ]))
    for a, b in zip(rings, rings[1:]):
        builder.bridge(a, b)
    builder.cap(rings[0], points[0])
    builder.cap(rings[-1], points[-1])


def build_strip():
    builder = MeshBuilder()
    add_strip(builder, [(0.135 * i / 8, 0.502 + 0.026 * (i / 8) ** 2) for i in range(-8, 9)])
    side_path = catmull([(0.27, 0.618, 0), (0.215, 0.572, 0), (0.158, 0.535, 0)], 5)
    add_strip(builder, [(p.x, p.y) for p in side_path])
    builder.cut_half()
    replace_object("NR_Helmet_Strip", builder.to_mesh("NR_Helmet_Strip"), "NR_Gray", mirror=True, subsurf=1)


def build_ear(sides=16):
    builder = MeshBuilder()
    sections = [(0.24, 0.095), (0.295, 0.096), (0.316, 0.092), (0.326, 0.078), (0.327, 0.072),
                (0.323, 0.068), (0.323, 0.064), (0.327, 0.060), (0.329, 0.045)]
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
    builder.cap(rings[-1], (0.330, EAR_Y, EAR_Z))
    replace_object("NR_Helmet_Ear", builder.to_mesh("NR_Helmet_Ear"), "NR_White", mirror=True)


def build_helmet():
    build_shell()
    build_visor()
    build_rim()
    build_strip()
    build_ear()
