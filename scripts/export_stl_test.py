"""파트 사본을 하나로 합쳐 시험 STL을 내보낸다."""
import math
import os
import struct

import bmesh
import bpy
from mathutils import Matrix

from narang_common import COLLECTION, ROOT

STL_DIR = os.path.join(ROOT, "exports")
VOXEL_SIZE = 0.003
TEMP_NAME = "NR_STL_Temp"


def count_shells(bm):
    seen = set()
    shells = 0
    for start in bm.verts:
        if start.index in seen:
            continue
        shells += 1
        stack = [start]
        seen.add(start.index)
        while stack:
            vert = stack.pop()
            for edge in vert.link_edges:
                nxt = edge.other_vert(vert)
                if nxt.index not in seen:
                    seen.add(nxt.index)
                    stack.append(nxt)
    return shells


def drop_specks(bm, max_size):
    """파트가 맞닿는 틈에 생기는 복셀 크기의 내부 빈 공간을 지운다."""
    bm.verts.index_update()
    seen = set()
    specks = []
    for start in bm.verts:
        if start.index in seen:
            continue
        seen.add(start.index)
        stack, island = [start], [start]
        while stack:
            vert = stack.pop()
            for edge in vert.link_edges:
                nxt = edge.other_vert(vert)
                if nxt.index not in seen:
                    seen.add(nxt.index)
                    stack.append(nxt)
                    island.append(nxt)
        size = max(max(v.co[i] for v in island) - min(v.co[i] for v in island) for i in range(3))
        if size <= max_size:
            specks.append(island)
    for island in specks:
        bmesh.ops.delete(bm, geom=island, context="VERTS")
    return len(specks)


def merged_mesh():
    """모든 파트의 모디파이어 적용 결과를 메시 하나에 모은다."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    for obj in (o for o in bpy.data.collections[COLLECTION].objects if o.type == "MESH"):
        evaluated = obj.evaluated_get(depsgraph)
        part = evaluated.to_mesh()
        part.transform(obj.matrix_world)
        bm.from_mesh(part)
        evaluated.to_mesh_clear()
    mesh = bpy.data.meshes.new(TEMP_NAME)
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def stl_height_mm(path):
    with open(path, "rb") as f:
        f.seek(80)
        count = struct.unpack("<I", f.read(4))[0]
        low, high = math.inf, -math.inf
        for _ in range(count):
            data = struct.unpack("<12f", f.read(48)[:48])
            f.read(2)
            for z in (data[5], data[8], data[11]):
                low, high = min(low, z), max(high, z)
    return count, high - low


def export_stl_test(height_mm=100):
    os.makedirs(STL_DIR, exist_ok=True)
    path = os.path.join(STL_DIR, "narang_test_%dmm.stl" % height_mm)
    scene = bpy.context.scene
    leftover = bpy.data.objects.get(TEMP_NAME)
    if leftover is not None:
        bpy.data.objects.remove(leftover)

    source = bpy.data.objects.new(TEMP_NAME, merged_mesh())
    scene.collection.objects.link(source)
    remesh = source.modifiers.new("Remesh", "REMESH")
    remesh.mode = "VOXEL"
    remesh.voxel_size = VOXEL_SIZE
    bpy.context.view_layer.update()

    depsgraph = bpy.context.evaluated_depsgraph_get()
    solid = bpy.data.meshes.new_from_object(source.evaluated_get(depsgraph))
    zs = [v.co.z for v in solid.vertices]
    scale = height_mm / (max(zs) - min(zs))
    solid.transform(Matrix.Translation((0, 0, -min(zs))))
    solid.transform(Matrix.Scale(scale, 4))

    bm = bmesh.new()
    bm.from_mesh(solid)
    specks = drop_specks(bm, VOXEL_SIZE * scale * 2)
    bm.to_mesh(solid)
    bm.verts.index_update()
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    shells = count_shells(bm)
    bm.free()

    old_mesh = source.data
    bpy.data.objects.remove(source)
    bpy.data.meshes.remove(old_mesh)
    output = bpy.data.objects.new(TEMP_NAME, solid)
    scene.collection.objects.link(output)
    for obj in bpy.context.view_layer.objects:
        obj.select_set(False)
    output.select_set(True)
    bpy.context.view_layer.objects.active = output
    bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True, global_scale=1.0, use_scene_unit=False, ascii_format=False)

    bpy.data.objects.remove(output)
    bpy.data.meshes.remove(solid)
    triangles, height = stl_height_mm(path)
    return {
        "path": path,
        "non_manifold": non_manifold,
        "shells": shells,
        "specks_removed": specks,
        "height_mm": round(height, 2),
        "triangles": triangles,
        "size_mb": round(os.path.getsize(path) / 1e6, 2),
        "temp_left": TEMP_NAME in bpy.data.objects,
    }
