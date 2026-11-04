# 나랑이 베이스 메시 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 스티커형 나랑이의 파트 분리형 베이스 메시를 `narang_base.blend`로 만든다.

**Architecture:** 파트별 빌드 스크립트를 블렌더 MCP의 `execute_blender_code`로 실행한다. 스크립트는 다시 실행해도 같은 결과가 나오도록 해당 파트를 지우고 새로 만든다. 공통 도우미와 메시 검사는 별도 모듈로 둔다.

**Tech Stack:** Blender 5.2.3 LTS, `bpy`, `bmesh`, Blender MCP

**Spec:** `docs/superpowers/specs/2026-11-04-narang-base-mesh-design.md`

## Global Constraints

- 저장 위치: `D:\NR_NARANG\narang_base.blend`
- 컬렉션: `NARANG_Base`. 테스트용 `Cube`, `Sphere`는 삭제하지 않고 숨긴다.
- 키 1m, 발바닥 z=0, 캐릭터는 -Y 방향을 본다, 좌우 대칭축은 X.
- 쿼드 위주 + Subdivision. 미러 모디파이어는 적용하지 않는다.
- 파트는 구멍 없는 닫힌 메시로 만든다.
- 이름 규칙: 오브젝트 `NR_*`, 머티리얼 `NR_White`, `NR_Gold`, `NR_Black`, `NR_Gray`.
- UV, 텍스처, 리깅, 소품, 백팩은 만들지 않는다.
- 프로젝트가 git 저장소가 아니므로 커밋 단계는 없다.

## Review Focus

1. 스크립트 재실행: `NR_Helmet_Shell.001` 같은 중복 없이 파트 수가 그대로여야 한다. (Task 1)
2. 미러 경계: 가운데를 지나는 파트는 모디파이어 적용 결과에서 X=0에 구멍이나 틈이 없어야 한다. (Task 2, 3)
3. 얇은 부위: 키 100mm로 출력해도 부러지지 않도록 손가락 지름은 0.02 이상이어야 한다. (Task 4)
4. 바닥 접지: 발바닥이 z=0에 놓여 세웠을 때 뜨지 않아야 한다. (Task 4)
5. 기존 씬 보존: `Cube`, `Sphere`와 `Red`, `Blue` 머티리얼이 남아 있어야 한다. (Task 1)

---

### Task 1: 씬 준비, 공통 도우미, 메시 검사

**Files:**
- Create: `scripts/narang_common.py`
- Create: `scripts/narang_check.py`

**Interfaces:**
- Produces (`narang_common`): `ensure_collection() -> Collection`, `get_material(name: str) -> Material`, `replace_object(name: str, mesh: Mesh, material: str, mirror: bool = False, subsurf: int = 2) -> Object`, `save() -> None`
- Produces (`narang_check`): `check_part(name: str) -> dict` (키: `non_manifold`, `boundary`, `tri_ratio`, `dims`, `min_z`, 모디파이어 적용 결과 기준), `check_scene() -> dict`

- [ ] **Step 1:** `narang_check.py`를 작성하고 `check_part("Cube")`를 실행한다. Expected: `non_manifold == 0`, `boundary == 0`, `dims == [2, 2, 2]`
- [ ] **Step 2:** `narang_common.py`를 작성한다. 머티리얼 색은 `NR_White (0.9,0.9,0.9)`, `NR_Gold (0.85,0.6,0.1)`, `NR_Black (0.01,0.01,0.012)`, `NR_Gray (0.5,0.5,0.52)`. Base Color와 뷰포트 색을 같이 설정한다.
- [ ] **Step 3:** 씬 준비: 컬렉션을 만들고 `Cube`, `Sphere`를 뷰포트와 렌더에서 숨긴 뒤 저장한다.
- [ ] **Step 4:** `replace_object("NR_Test", ...)`를 두 번 실행한다. Expected: `NR_Test` 하나만 남고 `.001`이 없다. 확인 후 `NR_Test`를 지운다.
- [ ] **Step 5:** `Cube`, `Sphere`, `Red`, `Blue`가 남아 있고 `narang_base.blend`가 저장됐는지 확인한다.

### Task 2: 헬멧

**Files:**
- Create: `scripts/build_helmet.py`

**Interfaces:**
- Consumes: `replace_object`, `check_part`
- Produces: `build_helmet() -> list[str]`. 오브젝트 `NR_Helmet_Shell`, `NR_Helmet_Rim`, `NR_Helmet_Visor`, `NR_Helmet_Ear`(미러)

- [ ] **Step 1:** 쉘을 만든다. 중심 z=0.74, 폭 약 0.60, 높이 0.52의 납작한 구. 쿼드 구체 기반으로 극점 삼각형을 피한다.
- [ ] **Step 2:** 바이저와 금색 테두리를 만든다. 바이저는 쉘 앞면을 살짝 덮는 곡면, 테두리는 그 둘레의 닫힌 튜브이며 아래쪽 가운데에 각진 턱을 둔다.
- [ ] **Step 3:** 귀 장치를 만든다. 쉘 옆면에 박힌 짧은 원통, 미러 적용.
- [ ] **Step 4:** 네 파트에 `check_part`를 실행한다. Expected: `non_manifold == 0`, `boundary == 0`, 쉘 `dims` 폭 0.60±0.03, 높이 0.52±0.03
- [ ] **Step 5:** 정면과 3/4 뷰를 `narang_sticker01.png`와 비교해 헬멧 비율과 바이저 크기를 조정하고 저장한다.

### Task 3: 몸통

**Files:**
- Create: `scripts/build_body.py`

**Interfaces:**
- Consumes: `replace_object`, `check_part`
- Produces: `build_body() -> list[str]`. 오브젝트 `NR_Body`, `NR_Neck_Ring`, `NR_Chest_Console`, `NR_Heart_Screen`

- [ ] **Step 1:** 몸통을 만든다. z 0.15~0.50, 폭 약 0.36, 아래가 넓은 달걀형, 머리 안쪽으로 맞물린다.
- [ ] **Step 2:** 목 링을 만든다. 몸통과 헬멧의 경계를 감싸는 닫힌 토러스.
- [ ] **Step 3:** 가슴 패널과 하트 스크린 패널을 만든다. 몸통 앞면 곡률을 따르는 둥근 사각판으로, 뒷면이 몸통 안에 묻힌다.
- [ ] **Step 4:** 네 파트에 `check_part`를 실행한다. Expected: `non_manifold == 0`, `boundary == 0`, `NR_Body` 폭 0.36±0.03
- [ ] **Step 5:** 스티커 이미지와 비교해 패널 크기와 위치를 조정하고 저장한다.

### Task 4: 팔다리

**Files:**
- Create: `scripts/build_limbs.py`

**Interfaces:**
- Consumes: `replace_object`, `check_part`
- Produces: `build_limbs() -> list[str]`. 오브젝트 `NR_Arm`(미러, 장갑 손 포함), `NR_Leg`(미러)

- [ ] **Step 1:** 다리를 만든다. z 0~0.18, 짧고 뭉툭한 형태, 끝이 둥근 발, 무릎 엣지 루프 3개, 윗부분은 몸통 안에 묻는다.
- [ ] **Step 2:** 팔을 만든다. 어깨 높이 약 0.42, 길이 약 0.28, A포즈, 팔꿈치 엣지 루프 3개.
- [ ] **Step 3:** 장갑 손을 만든다. 둥근 손가락 4개(엄지 포함), 지름 0.02 이상, 관절 엣지 루프 포함.
- [ ] **Step 4:** `check_part`를 실행한다. Expected: `non_manifold == 0`, `boundary == 0`, `NR_Leg`의 `min_z` 0±0.002, 손가락 지름 0.02 이상
- [ ] **Step 5:** 스티커 이미지와 비교해 팔다리 굵기와 손 크기를 조정하고 저장한다.

### Task 5: 최종 검증

**Files:**
- Create: `scripts/export_stl_test.py`
- Create: `renders/base_front.png`, `renders/base_side.png`, `renders/base_three_quarter.png`
- Create: `exports/narang_test_100mm.stl`

**Interfaces:**
- Consumes: 모든 `NR_*` 오브젝트, `check_scene`
- Produces: `export_stl_test(height_mm: float = 100) -> dict` (키: `path`, `non_manifold`, `shells`, `height_mm`)

- [ ] **Step 1:** 정면, 측면, 3/4 렌더를 만들고 스티커 이미지와 나란히 비교한다.
- [ ] **Step 2:** `check_scene()`을 실행한다. Expected: `NR_*` 오브젝트 10개, 전부 `non_manifold == 0`, 전체 키 1.0±0.02
- [ ] **Step 3:** `export_stl_test`를 작성한다. 파트 사본을 합쳐 Voxel Remesh로 하나로 만들고 STL로 내보낸 뒤 사본을 지운다.
- [ ] **Step 4:** 실행한다. Expected: `non_manifold == 0`, `shells == 1`, `height_mm` 100±1, 씬에 사본이 남지 않는다.
- [ ] **Step 5:** 저장하고 결과를 사용자에게 렌더와 함께 보고한다.
