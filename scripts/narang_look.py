"""얼굴 텍스처. 좌표는 reference/narang_turnaround_v2.png에서 쟀다."""
import os

import bpy
import numpy as np

from narang_common import ROOT

TEXTURE_DIR = os.path.join(ROOT, "textures")
SIZE = 1024
GLASS = (0.006, 0.026, 0.036)
GLOW = (0.1, 0.72, 0.64)
REFLECTION = (0.06, 0.085, 0.09)


class Canvas:
    """월드 좌표 (x, z)로 그리는 정사각 그림판."""

    def __init__(self, span, center_z, background):
        self.span, self.center_z = span, center_z
        self.pixels = np.empty((SIZE, SIZE, 3), dtype=np.float32)
        self.pixels[:] = background

    def px(self, x, z):
        return ((0.5 + x / self.span) * SIZE, (0.5 + (z - self.center_z) / self.span) * SIZE)

    def polygon(self, points, color):
        """짝홀 규칙으로 다각형을 채운다."""
        corners = [self.px(x, z) for x, z in points]
        cols, rows = np.meshgrid(np.arange(SIZE) + 0.5, np.arange(SIZE) + 0.5)
        inside = np.zeros((SIZE, SIZE), dtype=bool)
        for (x0, y0), (x1, y1) in zip(corners, corners[1:] + corners[:1]):
            if y0 == y1:
                continue
            crosses = (y0 > rows) != (y1 > rows)
            inside ^= crosses & (cols < (x1 - x0) * (rows - y0) / (y1 - y0) + x0)
        self.pixels[inside] = color

    def save(self, name):
        os.makedirs(TEXTURE_DIR, exist_ok=True)
        rgba = np.concatenate([self.pixels, np.ones((SIZE, SIZE, 1), np.float32)], axis=2)
        image = bpy.data.images.get(name) or bpy.data.images.new(name, SIZE, SIZE, alpha=False)
        image.pixels.foreach_set(rgba.ravel())
        image.filepath_raw = os.path.join(TEXTURE_DIR, name)
        image.file_format = "PNG"
        image.save()
        return image


def sheet(cx, cy):
    """시트 바이저를 2배 확대한 좌표를 월드 좌표로 바꾼다."""
    return (cx - 454) / 1594.0, (774 - cy / 2) / 797.0


def arc(start, middle, end, steps=16):
    """세 점을 지나는 2차 곡선."""
    out = []
    for i in range(steps + 1):
        t = i / steps
        out.append(tuple(
            (1 - t) ** 2 * start[k] + 2 * t * (1 - t) * (2 * middle[k] - (start[k] + end[k]) / 2) + t * t * end[k]
            for k in (0, 1)
        ))
    return out


def shape(canvas, sheet_points, color):
    canvas.polygon([sheet(x, y) for x, y in sheet_points], color)


def face_texture():
    c = Canvas(0.52, 0.735, GLASS)
    # 유리 반사: 위쪽 넓은 띠와 왼쪽 가는 호
    shape(c, arc((230, 170), (454, 100), (672, 170)) + arc((650, 212), (454, 170), (245, 218)), REFLECTION)
    shape(c, arc((205, 190), (130, 255), (108, 360)) + arc((122, 360), (145, 262), (212, 200)), REFLECTION)

    shape(c, [(205, 297), (240, 297), (240, 432), (345, 432), (345, 468), (205, 468)], GLOW)     # L
    shape(c, [(565, 278), (716, 278), (716, 392), (582, 392), (582, 432), (697, 432), (697, 468),
              (547, 468), (547, 355), (680, 355), (680, 315), (565, 315)], GLOW)                 # 2
    # N: narang_ex (3).png처럼 두 기둥이 같은 높이에서 끝나는 고딕체
    shape(c, [(385, 482), (421, 482), (483, 576), (483, 482), (513, 482), (513, 622), (477, 622),
              (415, 528), (415, 622), (385, 622)], GLOW)
    return c.save("narang_face.png")


def connect(material_name, image, strength):
    tree = bpy.data.materials[material_name].node_tree
    for node in [n for n in tree.nodes if n.type == "TEX_IMAGE"]:
        tree.nodes.remove(node)
    texture = tree.nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.location = (-400, 0)
    bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
    tree.links.new(texture.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = strength


def apply_textures():
    connect("NR_Visor", face_texture(), 1.25)
