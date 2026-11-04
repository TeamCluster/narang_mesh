"""시트와 같은 축척으로 렌더해서 겹쳐 보고 일치도(IoU)를 잰다."""
import math
import os

import bpy
import numpy as np
from mathutils import Euler, Vector

from narang_common import ROOT
from narang_view import VIEWS

SHEET = os.path.join(ROOT, "reference", "narang_turnaround.png")
RENDER_DIR = os.path.join(ROOT, "renders")
SCALE = 780            # 시트에서 키 1이 차지하는 픽셀
FEET_ROW = 1324
CENTERS = {"front": 423.5, "right": 995.5, "left": 1495.5, "back": 2028.0}
# 시트에서 각 뷰가 차지하는 가로 범위. 옆 뷰가 측정에 섞이지 않게 한다
BOUNDS = {"front": (100, 730), "right": (750, 1250), "left": (1260, 1740), "back": (1750, 2345)}
PANEL = 936            # 렌더 크기 (오소 1.2 * 780)
HALF_WINDOW = 350


def read_image(path):
    image = bpy.data.images.load(path, check_existing=False)
    w, h = image.size
    data = np.empty(w * h * 4, dtype=np.float32)
    image.pixels.foreach_get(data)
    bpy.data.images.remove(image)
    return data.reshape(h, w, 4)[::-1]


def write_image(path, rgb):
    h, w = rgb.shape[:2]
    rgba = np.concatenate([rgb, np.ones((h, w, 1), np.float32)], axis=2)[::-1].copy()
    image = bpy.data.images.new("NR_tmp", w, h, alpha=False)
    image.pixels.foreach_set(rgba.ravel())
    image.filepath_raw = path
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)


def render_views():
    os.makedirs(RENDER_DIR, exist_ok=True)
    scene = bpy.context.scene
    render = scene.render
    saved = dict(camera=scene.camera, engine=render.engine, path=render.filepath, x=render.resolution_x,
                 y=render.resolution_y, film=render.film_transparent, view=scene.view_settings.view_transform,
                 world=scene.world)
    camera_data = bpy.data.cameras.new("NR_RenderCam")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 1.2
    camera = bpy.data.objects.new("NR_RenderCam", camera_data)
    scene.collection.objects.link(camera)
    world = bpy.data.worlds.new("NR_RenderWorld")
    world.use_nodes = True
    background = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    background.inputs["Color"].default_value = (1, 1, 1, 1)
    background.inputs["Strength"].default_value = 0.52
    sun_data = bpy.data.lights.new("NR_RenderSun", "SUN")
    sun_data.energy = 0.7
    sun = bpy.data.objects.new("NR_RenderSun", sun_data)
    scene.collection.objects.link(sun)

    scene.camera, scene.world = camera, world
    render.engine = "BLENDER_EEVEE"
    render.film_transparent = True
    render.resolution_x = render.resolution_y = PANEL
    scene.view_settings.view_transform = "Standard"
    paths = {}
    try:
        for kind, (tilt, turn) in VIEWS.items():
            rotation = Euler((math.radians(tilt), 0, math.radians(turn)))
            camera.rotation_euler = rotation
            camera.location = Vector((0, 0, 0.5)) + rotation.to_matrix() @ Vector((0, 0, 3.0))
            sun.rotation_euler = Euler((math.radians(tilt - 35), 0, math.radians(turn + 25)))
            render.filepath = os.path.join(RENDER_DIR, "base_%s.png" % kind)
            bpy.ops.render.render(write_still=True)
            paths[kind] = render.filepath
    finally:
        scene.camera, scene.world = saved["camera"], saved["world"]
        render.engine, render.filepath = saved["engine"], saved["path"]
        render.resolution_x, render.resolution_y = saved["x"], saved["y"]
        render.film_transparent = saved["film"]
        scene.view_settings.view_transform = saved["view"]
        bpy.data.objects.remove(camera)
        bpy.data.cameras.remove(camera_data)
        bpy.data.objects.remove(sun)
        bpy.data.lights.remove(sun_data)
        bpy.data.worlds.remove(world)
    return paths


def compare(paths):
    sheet = read_image(SHEET)
    luminance = sheet[..., :3].mean(axis=2)
    saturation = sheet[..., :3].max(axis=2) - sheet[..., :3].min(axis=2)
    sheet_mask = (luminance < 0.965) | (saturation > 0.08)
    sheet_mask[1380:] = False
    # 패널 가운데는 z=0.5, 시트에서 그 높이의 행은 FEET_ROW - 0.5 * SCALE
    row_top = FEET_ROW - SCALE // 2 - PANEL // 2
    scores, tiles = {}, []
    for kind, center in CENTERS.items():
        render = read_image(paths[kind])
        mid = PANEL // 2
        window = render[:, mid - HALF_WINDOW:mid + HALF_WINDOW]
        model = window[..., 3] > 0.5
        x0 = int(center) - HALF_WINDOW
        left_pad = max(-x0, 0)
        target = np.zeros_like(model)
        limited = np.zeros_like(sheet_mask)
        limited[:, BOUNDS[kind][0]:BOUNDS[kind][1]] = sheet_mask[:, BOUNDS[kind][0]:BOUNDS[kind][1]]
        crop = limited[row_top:row_top + PANEL, max(x0, 0):x0 + 2 * HALF_WINDOW]
        target[:crop.shape[0], left_pad:left_pad + crop.shape[1]] = crop
        scores[kind] = round(float((model & target).sum() / max((model | target).sum(), 1)), 3)

        rgb = window[..., :3] * window[..., 3:4] + (1 - window[..., 3:4])
        original = np.ones_like(rgb)
        sheet_crop = sheet[row_top:row_top + PANEL, max(x0, 0):x0 + 2 * HALF_WINDOW, :3]
        original[:sheet_crop.shape[0], left_pad:left_pad + sheet_crop.shape[1]] = sheet_crop
        overlay = np.ones_like(rgb)
        overlay[model & target] = (0.8, 0.8, 0.8)
        overlay[model & ~target] = (0.9, 0.2, 0.2)   # 모델만 있음
        overlay[~model & target] = (0.2, 0.4, 0.95)  # 시트만 있음
        tiles.append((original, rgb, overlay))
    sheet_image = np.concatenate([np.concatenate(row, axis=1) for row in zip(*tiles)], axis=0)
    path = os.path.join(RENDER_DIR, "compare_turnaround.png")
    write_image(path, sheet_image[::2, ::2])
    return {"iou": scores, "path": path}
