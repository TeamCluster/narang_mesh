"""얼굴과 하트 화면 텍스처. 좌표는 시트에서 쟀다."""
import math
import os

import bpy
import numpy as np

from narang_common import ROOT

TEXTURE_DIR = os.path.join(ROOT, "textures")
SIZE = 1024
CYAN = (0.15, 0.95, 0.95)
RED = (1.0, 0.16, 0.13)
WHITE = (0.75, 0.75, 0.75)


class Canvas:
    """월드 좌표 (x, z)로 그리는 정사각 그림판."""

    def __init__(self, span, center_z):
        self.span, self.center_z = span, center_z
        self.pixels = np.zeros((SIZE, SIZE, 3), dtype=np.float32)

    def px(self, x, z):
        return (int((0.5 + x / self.span) * SIZE), int((0.5 + (z - self.center_z) / self.span) * SIZE))

    def rect(self, x0, z0, x1, z1, color):
        a, b = self.px(x0, z0), self.px(x1, z1)
        self.pixels[min(a[1], b[1]):max(a[1], b[1]), min(a[0], b[0]):max(a[0], b[0])] = color

    def line(self, x0, z0, x1, z1, width, color):
        for t in np.linspace(0, 1, 400):
            x, z = x0 + (x1 - x0) * t, z0 + (z1 - z0) * t
            self.rect(x - width / 2, z - width / 2, x + width / 2, z + width / 2, color)

    def save(self, name):
        os.makedirs(TEXTURE_DIR, exist_ok=True)
        rgba = np.concatenate([self.pixels, np.ones((SIZE, SIZE, 1), np.float32)], axis=2)
        image = bpy.data.images.get(name) or bpy.data.images.new(name, SIZE, SIZE, alpha=False)
        image.pixels.foreach_set(rgba.ravel())
        image.filepath_raw = os.path.join(TEXTURE_DIR, name)
        image.file_format = "PNG"
        image.save()
        return image


def face_texture():
    c = Canvas(0.52, 0.735)
    w = 0.017
    c.rect(-0.140, 0.682, -0.140 + w, 0.782, CYAN)     # L
    c.rect(-0.140, 0.682, -0.053, 0.682 + w, CYAN)
    x0, x1, top, mid, low = 0.065, 0.145, 0.782, 0.732, 0.682
    c.rect(x0, top - w, x1, top, CYAN)                 # 2
    c.rect(x1 - w, mid, x1, top, CYAN)
    c.rect(x0, mid - w / 2, x1, mid + w / 2, CYAN)
    c.rect(x0, low, x0 + w, mid, CYAN)
    c.rect(x0, low, x1, low + w, CYAN)
    n = 0.012
    c.rect(-0.027, 0.608, -0.027 + n, 0.664, CYAN)     # N
    c.rect(0.040 - n, 0.608, 0.040, 0.664, CYAN)
    c.line(-0.021, 0.658, 0.034, 0.614, n, CYAN)
    for i in range(12):  # 유리 오른쪽 위의 반사선
        a0, a1 = math.radians(72 - i * 3.6), math.radians(72 - (i + 1) * 3.6)
        c.line(0.215 * math.cos(a0), 0.735 + 0.175 * math.sin(a0),
               0.215 * math.cos(a1), 0.735 + 0.175 * math.sin(a1), 0.004, WHITE)
    return c.save("narang_face.png")


def heart_texture():
    c = Canvas(0.30, 0.284)
    cell = 0.0205
    rows = [".XX.XX.", "XXXXXXX", "XXXXXXX", ".XXXXX.", "..XXX..", "...X..."]
    left, top = -0.004 - 3.5 * cell, 0.278 + 3 * cell
    for r, row in enumerate(rows):
        for col, mark in enumerate(row):
            if mark == "X":
                x, z = left + col * cell, top - r * cell
                c.rect(x, z - cell, x + cell, z, RED)
    c.rect(0.067, 0.352, 0.105, 0.356, WHITE)
    c.rect(0.101, 0.2615, 0.105, 0.356, WHITE)
    c.rect(0.099, 0.238, 0.106, 0.245, WHITE)
    return c.save("narang_heart.png")


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
    connect("NR_Visor", face_texture(), 2.0)
    connect("NR_Screen", heart_texture(), 2.0)
