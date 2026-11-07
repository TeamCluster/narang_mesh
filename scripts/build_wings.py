"""등의 작은 날개. 시트에서 딴 윤곽을 쿠션처럼 부풀린 하나의 표면이다.

+X 쪽만 만들고 미러로 복제한다. 좌표는 시트 후면 뷰를 2배 확대한 픽셀이며, 몸 중심이 가로 464다.
"""
import math

from mathutils import Vector

from narang_common import catmull, quad_sphere, replace_object

PIXELS = 1594.0   # 확대 좌표에서 키 1이 차지하는 픽셀
# 날개 평면의 앞뒤 위치: 위쪽만 몸에 붙고 아래로 갈수록 등에서 벌어지며, 바깥쪽은 몸을 따라 앞으로 말린다
WING_TOP_Y, WING_TOP_Z, WING_SPREAD, WING_CURL = 0.150, 0.41, 0.38, 0.12

ROOT = Vector((600.0, 190.0))
GRID = 34
# 윤곽을 시계 방향으로 따라간 점. 깃털 끝 셋과 그 사이 홈 둘을 지난다
OUTLINE = [
    (487, 225), (495, 175), (520, 140), (565, 115), (620, 110), (680, 122), (735, 155), (780, 205),
    (812, 262), (826, 312), (815, 338), (785, 347), (745, 338), (717, 325), (718, 350), (700, 375),
    (665, 380), (630, 368), (611, 348), (600, 372), (570, 383), (535, 372), (510, 340), (495, 290),
]
NOTCHES = [(717, 325), (611, 348)]   # 깃털 사이 홈. 여기서 뿌리 쪽으로 주름이 올라간다
THICKNESS = 0.031        # 앞뒤 반두께
EDGE_POWER = 2.6         # 클수록 가장자리까지 통통하다
CREASE_DEPTH = 0.62
CREASE_WIDTH = math.radians(5.5)
CREASE_FADE = 1.4        # 클수록 주름이 뿌리 쪽에서 빨리 사라진다
ANGLES = 720


def closed_outline():
    points = [Vector((x, y, 0.0)) for x, y in OUTLINE]
    curve = catmull(points[-1:] + points + points[:2], 6)[6:-6]
    return [Vector((p.x, p.y)) for p in curve]


def ray_length(angle, curve):
    """ROOT에서 angle 방향으로 나가 윤곽에 닿는 거리."""
    direction = Vector((math.cos(angle), math.sin(angle)))
    best = 0.0
    for a, b in zip(curve, curve[1:] + curve[:1]):
        edge = b - a
        denominator = direction.x * edge.y - direction.y * edge.x
        if abs(denominator) < 1e-9:
            continue
        offset = a - ROOT
        t = (offset.x * edge.y - offset.y * edge.x) / denominator
        u = (offset.x * direction.y - offset.y * direction.x) / denominator
        if t > best and 0.0 <= u <= 1.0:
            best = t
    return best


def radius_table():
    curve = closed_outline()
    return [ray_length(2 * math.pi * i / ANGLES, curve) for i in range(ANGLES)]


def radius_at(table, angle):
    position = (angle % (2 * math.pi)) / (2 * math.pi) * ANGLES
    index = int(position)
    t = position - index
    return table[index % ANGLES] * (1 - t) + table[(index + 1) % ANGLES] * t


def crease(angle, rho):
    """홈 방향에서 두께를 줄이는 배율. 가장자리에서 깊고 뿌리 쪽에서 사라진다."""
    amount = 0.0
    for x, y in NOTCHES:
        notch = math.atan2(y - ROOT.y, x - ROOT.x)
        gap = (angle - notch + math.pi) % (2 * math.pi) - math.pi
        amount = max(amount, math.exp(-(gap / CREASE_WIDTH) ** 2))
    return 1.0 - CREASE_DEPTH * amount * rho ** CREASE_FADE


def plane_y(x, z):
    return WING_TOP_Y + WING_SPREAD * (WING_TOP_Z - z) - WING_CURL * x


def build_wings():
    table = radius_table()

    def transform(p):
        rho = min(math.hypot(p.x, p.y), 1.0)
        angle = math.atan2(p.y, p.x)
        point = ROOT + Vector((math.cos(angle), math.sin(angle))) * radius_at(table, angle) * rho
        x, z = (point.x - 464) / PIXELS, (768 - point.y) / PIXELS
        height = THICKNESS * math.sqrt(max(1.0 - rho ** EDGE_POWER, 0.0)) * crease(angle, rho)
        return Vector((x, plane_y(x, z) + math.copysign(height, p.z), z))

    builder = quad_sphere(GRID, transform)
    replace_object("NR_Wing", builder.to_mesh("NR_Wing"), "NR_LightGray", mirror=True, subsurf=1)
