"""나랑이 메시 검사. 모든 값은 모디파이어를 적용한 결과 기준이다."""
import math

import bmesh
import bpy
from mathutils import Vector

COLLECTION = "NARANG_Base"


def check_part(name):
    obj = bpy.data.objects[name]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.transform(obj.matrix_world)

    boundary = sum(1 for e in bm.edges if e.is_boundary)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary)
    tris = sum(1 for f in bm.faces if len(f.verts) == 3)
    coords = [v.co.copy() for v in bm.verts]
    low = Vector((min(c[i] for c in coords) for i in range(3)))
    high = Vector((max(c[i] for c in coords) for i in range(3)))
    result = {
        "name": name,
        "non_manifold": non_manifold,
        "boundary": boundary,
        "tri_ratio": round(tris / max(len(bm.faces), 1), 4),
        "faces": len(bm.faces),
        "volume": round(bm.calc_volume(signed=True), 6),
        "dims": [round(v, 4) for v in (high - low)],
        "min_z": round(low.z, 4),
        "max_z": round(high.z, 4),
    }
    bm.free()
    evaluated.to_mesh_clear()
    return result


def stand_margin(contact_height=0.001):
    """무게중심이 발바닥 안에 있는지 앞뒤 방향으로 잰다. 겹치는 파트는 중복 계산되는 근사치다."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    volume, moment = 0.0, Vector()
    contact_y = []
    for obj in bpy.data.collections[COLLECTION].objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        coords = [obj.matrix_world @ v.co for v in mesh.vertices]
        for tri in mesh.loop_triangles:
            a, b, c = (coords[i] for i in tri.vertices)
            part = a.dot(b.cross(c)) / 6.0
            volume += part
            moment += part * (a + b + c) / 4.0
        contact_y.extend(c.y for c in coords if c.z < contact_height)
        evaluated.to_mesh_clear()
    center = moment / volume
    back = max(contact_y) - center.y
    front = center.y - min(contact_y)
    return {
        "center_y": round(center.y, 4),
        "center_z": round(center.z, 4),
        "contact_y": [round(min(contact_y), 4), round(max(contact_y), 4)],
        "tip_angle": round(math.degrees(math.atan2(min(back, front), center.z)), 2),
    }


def check_scene():
    collection = bpy.data.collections[COLLECTION]
    parts = [check_part(o.name) for o in collection.objects if o.type == "MESH"]
    return {
        "count": len(parts),
        "all_closed": all(p["non_manifold"] == 0 and p["boundary"] == 0 for p in parts),
        "all_outward": all(p["volume"] > 0 for p in parts),
        "height": round(max(p["max_z"] for p in parts) - min(p["min_z"] for p in parts), 4),
        "min_z": min(p["min_z"] for p in parts),
        "stand": stand_margin(),
        "parts": parts,
    }
