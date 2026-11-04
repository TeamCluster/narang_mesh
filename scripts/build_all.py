"""나랑이 베이스 메시 전체를 다시 만든다.

블렌더 안에서: runpy.run_path("D:/NR_NARANG/scripts/build_all.py", run_name="__main__")
새 세션에서: blender -b narang_base.blend --python scripts/build_all.py
다른 파일로 저장: blender -b --python scripts/build_all.py -- 저장경로.blend
"""
import importlib
import json
import os
import sys

import bpy

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

MODULES = ("narang_common", "narang_check", "narang_look", "build_helmet", "build_body", "build_limbs", "build_pack")
MIN_TIP_ANGLE = 3.0


def load_modules():
    """수정한 상수가 무시되지 않도록 항상 다시 읽는다."""
    return [importlib.reload(importlib.import_module(name)) for name in MODULES]


def prepare_scene(common):
    """컬렉션의 오브젝트는 모두 스크립트가 만든 것이므로 지우고 다시 만든다."""
    collection = common.ensure_collection()
    for obj in list(collection.objects):
        data = obj.data
        bpy.data.objects.remove(obj)
        if data is not None and data.users == 0:
            bpy.data.meshes.remove(data)
    for name in ("Cube", "Sphere"):
        obj = bpy.data.objects.get(name)
        if obj is not None:
            obj.hide_viewport = True
            obj.hide_render = True


def failures(report):
    problems = []
    if not report["all_closed"]:
        bad = [p["name"] for p in report["parts"] if p["non_manifold"] or p["boundary"]]
        problems.append("닫히지 않은 파트 " + ", ".join(bad))
    if not report["all_outward"]:
        bad = [p["name"] for p in report["parts"] if p["volume"] <= 0]
        problems.append("뒤집힌 파트 " + ", ".join(bad))
    if report["stand"]["tip_angle"] < MIN_TIP_ANGLE:
        problems.append("세웠을 때 불안정하다 %.2f도" % report["stand"]["tip_angle"])
    return problems


def build_all(save_path=None):
    common, check, look, helmet, body, limbs, pack = load_modules()
    prepare_scene(common)
    helmet.build_helmet()
    body.build_body()
    limbs.build_limbs()
    pack.build_pack()
    look.apply_textures()
    bpy.context.view_layer.update()
    report = check.check_scene()
    problems = failures(report)
    if problems:
        raise RuntimeError("검사 실패: " + "; ".join(problems))
    common.save(save_path or common.BLEND_PATH)
    return {key: value for key, value in report.items() if key != "parts"}


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    print("NARANG_RESULT " + json.dumps(build_all(args[0] if args else None), ensure_ascii=False))
