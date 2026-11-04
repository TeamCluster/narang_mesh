"""나랑이 빌드 스크립트의 공통 도우미."""
import math

import bmesh
import bpy
from mathutils import Vector

ROOT = r"D:\NR_NARANG"
BLEND_PATH = ROOT + r"\narang_base.blend"
COLLECTION = "NARANG_Base"
COLORS = {
    "NR_White": (0.8, 0.8, 0.81, 1.0),
    "NR_Gold": (0.78, 0.5, 0.06, 1.0),
    "NR_Gray": (0.42, 0.42, 0.43, 1.0),
    "NR_Dark": (0.05, 0.05, 0.055, 1.0),
    "NR_Visor": (0.008, 0.008, 0.01, 1.0),
    "NR_Screen": (0.012, 0.012, 0.014, 1.0),
    "NR_Red": (0.75, 0.03, 0.04, 1.0),
    "NR_Green": (0.05, 0.75, 0.12, 1.0),
    "NR_Cyan": (0.05, 0.65, 0.72, 1.0),
    "NR_Blue": (0.08, 0.2, 0.85, 1.0),
    "NR_Navy": (0.12, 0.2, 0.55, 1.0),
    "NR_Tan": (0.55, 0.45, 0.2, 1.0),
    "NR_HoseBlue": (0.1, 0.32, 0.55, 1.0),
    "NR_HoseGreen": (0.3, 0.55, 0.45, 1.0),
    "NR_Glass": (0.85, 0.92, 0.95, 1.0),
}
ROUGHNESS = {"NR_White": 0.42, "NR_Gold": 0.3, "NR_Visor": 0.08, "NR_Screen": 0.2, "NR_Glass": 0.03}
METALLIC = {"NR_Gold": 1.0}
ALPHA = {"NR_Glass": 0.22}


def ensure_collection():
    collection = bpy.data.collections.get(COLLECTION)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION)
        bpy.context.scene.collection.children.link(collection)
    return collection


def get_material(name):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    tree = material.node_tree
    bsdf = next((n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
        output = next((n for n in tree.nodes if n.type == "OUTPUT_MATERIAL"), None)
        output = output or tree.nodes.new("ShaderNodeOutputMaterial")
        output.location = (300, 0)
        tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = COLORS[name]
    bsdf.inputs["Roughness"].default_value = ROUGHNESS.get(name, 0.45)
    bsdf.inputs["Metallic"].default_value = METALLIC.get(name, 0.0)
    bsdf.inputs["Alpha"].default_value = ALPHA.get(name, 1.0)
    if name in ALPHA:
        material.surface_render_method = "BLENDED"
    material.diffuse_color = COLORS[name]
    return material


def replace_object(name, mesh, material, mirror=False, subsurf=2, mirror_u=False):
    """같은 이름의 파트를 지우고 새로 만든다. 다시 실행해도 중복이 생기지 않는다."""
    old = bpy.data.objects.get(name)
    if old is not None:
        old_mesh = old.data
        bpy.data.objects.remove(old)
        if old_mesh is not mesh and old_mesh.users == 0:
            bpy.data.meshes.remove(old_mesh)
    mesh.name = name
    obj = bpy.data.objects.new(name, mesh)
    ensure_collection().objects.link(obj)
    mesh.materials.append(get_material(material))
    if mirror:
        modifier = obj.modifiers.new("Mirror", "MIRROR")
        modifier.use_axis = (True, False, False)
        modifier.use_clip = True
        modifier.use_mirror_merge = True
        modifier.merge_threshold = 0.0005
        modifier.use_mirror_u = mirror_u
    if subsurf:
        modifier = obj.modifiers.new("Subdivision", "SUBSURF")
        modifier.levels = subsurf
        modifier.render_levels = subsurf
    return obj


def save(path=BLEND_PATH):
    bpy.ops.wm.save_as_mainfile(filepath=path)


class MeshBuilder:
    """정점과 면 목록으로 쿼드 메시를 조립한다."""

    def __init__(self):
        self.verts = []
        self.faces = []

    def add(self, co):
        self.verts.append(Vector(co))
        return len(self.verts) - 1

    def ring(self, points):
        return [self.add(p) for p in points]

    def bridge(self, ring_a, ring_b):
        n = len(ring_a)
        for i in range(n):
            j = (i + 1) % n
            self.faces.append((ring_a[i], ring_a[j], ring_b[j], ring_b[i]))

    def cap(self, ring, center):
        """짝수 개 정점 고리를 가운데 정점 하나와 쿼드로 막는다."""
        c = self.add(center)
        n = len(ring)
        for i in range(0, n, 2):
            self.faces.append((c, ring[i], ring[i + 1], ring[(i + 2) % n]))

    def extrude_face(self, face, centers, scales, squash=()):
        """쿼드 하나를 경로를 따라 뽑아내고 끝을 막는다.

        squash는 (축, 배율) 목록으로, 뿌리에서 두 번째 고리까지 서서히 적용된다.
        """
        self.faces.remove(face)
        base = sum((self.verts[i] for i in face), Vector()) / len(face)
        offsets = [self.verts[i] - base for i in face]
        previous = list(face)
        for index, (center, scale) in enumerate(zip(centers, scales)):
            ramp = min((index + 1) / 2, 1.0)
            shaped = list(offsets)
            for axis, factor in squash:
                shaped = [o + axis * o.dot(axis) * (factor - 1) * ramp for o in shaped]
            current = self.ring([center + o * scale for o in shaped])
            self.bridge(previous, current)
            previous = current
        self.faces.append(tuple(previous))

    def cut_half(self, eps=1e-5):
        """X<0 쪽을 지우고 X=0 정점을 맞춘다. 미러 모디파이어용."""
        for v in self.verts:
            if abs(v.x) < eps:
                v.x = 0.0
        kept = [f for f in self.faces if all(self.verts[i].x >= 0.0 for i in f)]
        used = sorted({i for f in kept for i in f})
        remap = {old: new for new, old in enumerate(used)}
        self.verts = [self.verts[i] for i in used]
        self.faces = [tuple(remap[i] for i in f) for f in kept]

    def to_mesh(self, name):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([tuple(v) for v in self.verts], [], self.faces)
        mesh.update()
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        mesh.shade_smooth()
        return mesh


def quad_sphere(n, transform):
    """극점 삼각형이 없는 큐브 기반 구. transform은 단위 구 위의 점을 받는다."""
    builder = MeshBuilder()
    index = {}

    def vert(p):
        key = tuple(round(c, 6) for c in p)
        if key not in index:
            index[key] = builder.add(transform(Vector(p).normalized()))
        return index[key]

    for axis in range(3):
        for sign in (-1, 1):
            for i in range(n):
                for j in range(n):
                    quad = []
                    for a, b in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                        p = [0.0, 0.0, 0.0]
                        p[axis] = float(sign)
                        p[(axis + 1) % 3] = -1 + 2 * a / n
                        p[(axis + 2) % 3] = -1 + 2 * b / n
                        quad.append(vert(p))
                    builder.faces.append(tuple(quad))
    return builder


def plate(n, surface_front, surface_back, shape):
    """앞뒤 곡면과 옆면으로 닫힌 판. shape는 (s, t)를 곡면 좌표로 바꾼다."""
    builder = MeshBuilder()
    layers = []
    for surface in (surface_front, surface_back):
        grid = [
            [builder.add(surface(*shape(-1 + 2 * i / n, -1 + 2 * j / n))) for j in range(n + 1)]
            for i in range(n + 1)
        ]
        for i in range(n):
            for j in range(n):
                builder.faces.append((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
        layers.append(grid)

    def border(grid):
        return (
            [grid[i][0] for i in range(n)]
            + [grid[n][j] for j in range(n)]
            + [grid[i][n] for i in range(n, 0, -1)]
            + [grid[0][j] for j in range(n, 0, -1)]
        )

    builder.bridge(border(layers[0]), border(layers[1]))
    return builder


def superquadric(p, n):
    """단위 구 위의 점을 |x|^n + |y|^n + |z|^n = 1 곡면으로 옮긴다."""
    return p / (abs(p.x) ** n + abs(p.y) ** n + abs(p.z) ** n) ** (1.0 / n)


def rounded_box(center, half, n=5.0, level=4):
    center, half = Vector(center), Vector(half)

    def transform(p):
        q = superquadric(p, n)
        return center + Vector((q.x * half.x, q.y * half.y, q.z * half.z))

    return quad_sphere(level, transform)


def catmull(points, per=8):
    """조절점을 지나는 부드러운 곡선."""
    pts = [Vector(p) for p in points]
    pts = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1:i + 3]
        for k in range(per):
            t = k / per
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-2])
    return out


def tube(points, radii, sides=8):
    """곡선을 따라가는 양끝이 막힌 관. radii는 숫자 또는 점마다의 목록이다."""
    builder = MeshBuilder()
    if not isinstance(radii, (list, tuple)):
        radii = [radii] * len(points)
    normal = (points[1] - points[0]).orthogonal().normalized()
    rings = []
    for i, point in enumerate(points):
        tangent = (points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]).normalized()
        normal = (normal - tangent * normal.dot(tangent)).normalized()
        side = tangent.cross(normal)
        rings.append(builder.ring([
            point + (normal * math.cos(a) + side * math.sin(a)) * radii[i]
            for a in (2 * math.pi * k / sides for k in range(sides))
        ]))
    for a, b in zip(rings, rings[1:]):
        builder.bridge(a, b)
    builder.cap(rings[0], points[0] - (points[1] - points[0]).normalized() * radii[0] * 0.5)
    builder.cap(rings[-1], points[-1] + (points[-1] - points[-2]).normalized() * radii[-1] * 0.5)
    return builder


def lathe(profile, x, y, sides=12):
    """(반지름, 높이) 단면을 Z축으로 돌린 닫힌 형태."""
    builder = MeshBuilder()
    rings = [
        builder.ring([
            Vector((x + r * math.cos(2 * math.pi * k / sides), y + r * math.sin(2 * math.pi * k / sides), z))
            for k in range(sides)
        ])
        for r, z in profile
    ]
    for a, b in zip(rings, rings[1:]):
        builder.bridge(a, b)
    builder.cap(rings[0], (x, y, profile[0][1]))
    builder.cap(rings[-1], (x, y, profile[-1][1]))
    return builder


def planar_uv(mesh, span, center_x, center_z):
    """정면에서 투영한 UV. 화면 텍스처용."""
    layer = mesh.uv_layers.new(name="UVMap")
    for loop in mesh.loops:
        co = mesh.vertices[loop.vertex_index].co
        layer.data[loop.index].uv = (0.5 + (co.x - center_x) / span, 0.5 + (co.z - center_z) / span)
