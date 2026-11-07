# 나랑이 리깅 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `narang_base.blend`의 25개 파트를 움직이는 본 23개짜리 전용 리그를 스크립트로 만든다.

**Architecture:** `scripts/build_rig.py`가 아마추어, IK, 웨이트, 모디파이어를 만들고 `scripts/narang_rig_check.py`가 결과를 검사한다. `build_all()`이 메시 검사 뒤 저장 전에 리그를 만든다. 테스트 포즈는 `scripts/narang_rig_poses.py`가 잡는다.

**Tech Stack:** Blender 5.2.3 LTS, `bpy`, `bmesh`, Blender MCP

**Spec:** `docs/superpowers/specs/2026-11-07-narang-rig-design.md`

## Global Constraints

- 본 좌표, 부모, 파트별 웨이트, 혼합 구간은 스펙 표의 값을 `build_rig.py` 상수로 옮긴다.
- 아마추어 오브젝트 `NR_Rig`, 아마추어 데이터 `NR_Rig`, 컬렉션 `NARANG_Rig`. `NARANG_Base`에 넣지 않는다.
- 모디파이어 순서는 Mirror, Armature, Subdivision. Mirror는 적용하지 않는다.
- `NR_Rig` 오브젝트는 지우지 않고 재사용한다. 본 이름은 바꾸지 않는다.
- 저장 위치는 `D:\NR_NARANG\narang_base.blend`. 기존 `Cube`, `Sphere`와 재질은 건드리지 않는다.
- 스크립트 주석과 메시지는 기존 파일처럼 한국어로 쓴다.
- 테스트 프레임워크는 없다. 검사는 블렌더 안에서 `narang_rig_check.py`로 실행한다.
- 스크립트 실행: MCP `execute_blender_code`에서 `runpy.run_path("D:/NR_NARANG/scripts/<파일>.py", run_name="__main__")`. 모듈 함수는 `importlib.reload` 후 호출한다.
- 커밋은 사용자가 요청할 때만 한다. `scripts/__pycache__`는 스테이징하지 않는다.

## Review Focus

1. 재실행: `build_rig()`을 두 번 돌려도 모디파이어, 본, 그룹이 늘지 않아야 한다. (Task 3)
2. 포즈가 남은 채 재빌드: 기본 자세 검사는 현재 포즈에 영향받지 않아야 하고, 사용자의 포즈를 지우지 않아야 한다. (Task 4)
3. 애니메이션 보존: `NR_Rig`에 연결된 액션은 `build_all()` 뒤에도 연결돼 있어야 한다. (Task 4)
4. 미러 쪽 변형: `.R` 본을 움직이면 -X 쪽만 움직이고 +X 쪽은 그대로여야 한다. (Task 3)
5. 시작 모드: 사용자가 Edit, Pose 모드에 있어도, 백그라운드 실행(`blender -b`)이어도 동작해야 한다. (Task 2, 4)

---

### Task 1: 팔꿈치 엣지 고리

**Files:**
- Modify: `scripts/build_limbs.py:17-24`

**Interfaces:**
- Produces: `NR_Arm` 기본 메시에 x 0.275, 0.300 고리

- [ ] **Step 1: 수정 전 측정**

MCP로 `NR_Arm`의 모디파이어 적용 결과 경계 상자를 기록한다. 고리 x 목록에 0.275, 0.3이 없음을 확인한다.

- [ ] **Step 2: `ARM_SECTIONS`에 단면 추가**

`(0.275, 0.3935, 0.0575, 0.0545)`와 `(0.300, 0.3935, 0.0575, 0.0545)`를 x 순서에 맞게 넣는다.

- [ ] **Step 3: `build_all.py` 실행 후 확인**

Expected: 예외 없이 `NARANG_RESULT` 값이 나오고, 파트 25개. `NR_Arm` 고리에 0.275, 0.3이 있고, 경계 상자가 Step 1과 0.001 이내로 같다.

---

### Task 2: 아마추어와 IK

**Files:**
- Create: `scripts/build_rig.py`
- Create: `scripts/narang_rig_check.py`

**Interfaces:**
- Produces: `build_rig.build_armature() -> bpy.types.Object`
- Produces: `narang_rig_check.check_bones() -> list[str]` (문제 문장 목록, 비면 통과)
- Produces: 상수 `build_rig.BONES` (`.L`과 가운데 본 정의), `build_rig.EXPECTED_BONES` (이름 23개 집합)

- [ ] **Step 1: `check_bones()` 작성**

검사 내용:
- `NR_Rig`가 있고 컬렉션이 `NARANG_Rig` 하나뿐이며 `NARANG_Base`에 없다.
- 본 이름 집합이 스펙의 23개와 같다.
- `use_deform`이 참인 본은 `torso`, `head`, 팔다리 12개로 총 14개다. `root`와 컨트롤은 거짓이다.
- `.R` 본의 시작과 끝은 `.L`의 X를 뒤집은 값이다. (오차 0.00001)
- `forearm.*`, `shin.*`에 IK 제약이 있고 `chain_count == 2`, 목표와 폴 본이 맞다.
- `hand.*`, `foot.*`에 해당 IK 본의 회전을 복사하는 제약이 있다.
- 본 컬렉션 `DEF`, `CTRL`에 스펙대로 나뉘어 있다.

- [ ] **Step 2: 실행해서 실패 확인**

Expected: 리그가 없다는 문제가 나온다.

- [ ] **Step 3: `build_armature()` 구현**

- 시작할 때 `bpy.context.view_layer.objects.active`가 있고 모드가 Object가 아니면 Object 모드로 돌린다.
- `NR_Rig`가 있으면 재사용하고, Edit 모드에서 본을 지운 뒤 다시 만든다. 없으면 새로 만들어 `NARANG_Rig`에 넣는다.
- `.R`은 `BONES`의 `.L` 항목에서 X를 뒤집어 생성한다.
- `pose_bone.constraints`도 매번 지우고 다시 만든다. 기존 포즈 값(`location`, `rotation`)은 건드리지 않는다.
- 폴 각도는 상수로 두고, Task 3의 기본 자세 검사가 통과하는 값으로 정한다.

- [ ] **Step 4: 통과 확인**

Expected: `check_bones()`가 빈 목록을 돌려준다. Pose 모드에서 시작해 다시 실행해도 같은 결과다.

---

### Task 3: 웨이트, 모디파이어, 기본 자세

**Files:**
- Modify: `scripts/build_rig.py`
- Modify: `scripts/narang_rig_check.py`

**Interfaces:**
- Consumes: `build_armature()`, `EXPECTED_BONES`
- Produces: `build_rig.bind_parts(rig) -> None`
- Produces: `narang_rig_check.check_binding() -> list[str]`, `check_rest() -> list[str]`, `check_motion() -> list[str]`
- Produces: `narang_rig_check.evaluated_coords(name) -> list[Vector]` (모디파이어 적용 결과 월드 좌표)

- [ ] **Step 1: 검사 함수 작성**

`check_binding()`:
- 25개 파트 모두 Armature 모디파이어가 하나이고 대상이 `NR_Rig`다. Mirror가 있으면 그 뒤, Subdivision이 있으면 그 앞이다.
- 모든 정점의 웨이트 합이 1이다. (오차 0.0001)
- `.L` 그룹을 쓰는 파트에 `.R` 그룹이 있고, 기본 메시에서 `.R` 그룹은 비어 있다.

`check_rest()`:
- `rig.data.pose_position`을 `REST`로 두고 측정한 뒤 원래 값으로 돌린다.
- 각 파트에서 Armature 모디파이어를 끈 좌표와 켠 좌표의 차이가 0.00001 이하다.
- `POSE`로 돌리고 포즈 변환을 비운 상태도 같은 기준으로 측정한다. 이 측정이 폴 각도 오류를 잡는다. 사용자 포즈는 측정 뒤 복원한다.

`check_motion()`: 측정 뒤 포즈를 복원한다.
- `torso`를 z로 -0.03 옮겨도 `NR_Shoe` 좌표 변화가 0.0001 이하고, `NR_Body`는 0.03 움직인다.
- `hand_ik.R`을 옮기면 `NR_Hand`의 x<0 정점은 움직이고 x>0 정점은 그대로다.
- `hand_ik.L`을 옮기면 반대로 된다.

- [ ] **Step 2: 실행해서 실패 확인**

Expected: Armature 모디파이어가 없다는 문제가 파트별로 나온다.

- [ ] **Step 3: `bind_parts(rig)` 구현**

- 파트별 웨이트 표와 혼합 구간은 스펙 값을 상수로 둔다. 혼합은 구간 안 선형 보간이다.
- 기존 정점 그룹과 Armature 모디파이어를 지운 뒤 다시 만든다.
- 모디파이어는 `obj.modifiers.new("Armature", "ARMATURE")` 뒤 `obj.modifiers.move()`로 Mirror 바로 뒤, 없으면 맨 앞으로 옮긴다.
- 미러 파트는 `.L` 그룹에 웨이트를 넣고 빈 `.R` 그룹을 만든다. 미러가 없는 파트는 `torso` 그룹이다.
- 오브젝트 부모는 설정하지 않는다.

- [ ] **Step 4: 통과 확인**

`build_armature()`, `bind_parts()`를 두 번 연속 실행하고 세 검사를 돌린다.
Expected: 세 검사 모두 빈 목록. 파트마다 Armature 모디파이어 1개, 본 23개, 이름에 `.001` 없음.

---

### Task 4: 빌드 연결

**Files:**
- Modify: `scripts/build_rig.py`
- Modify: `scripts/build_all.py:18,70-85`

**Interfaces:**
- Consumes: Task 2, 3의 함수 전체
- Produces: `build_rig.build_rig() -> dict` (`bones`, `bound_parts`). 검사 실패 시 `RuntimeError("리그 검사 실패: ...")`

- [ ] **Step 1: 시나리오 테스트 준비**

MCP에서 `NR_Rig`에 테스트 액션을 연결하고, `hand_ik.L`을 옮겨 둔 채로 `build_all.py`를 실행하는 코드를 만든다. 액션 이름은 `TEST_rig_keep`을 쓴다.

- [ ] **Step 2: 연결 전 실패 확인**

Expected: `build_all()` 뒤 파트에 Armature 모디파이어가 없다.

- [ ] **Step 3: 구현**

- `build_rig()`은 `build_armature()`, `bind_parts()`, 세 검사와 `check_bones()`를 차례로 실행한다.
- `build_all.py`의 `MODULES`에 `narang_rig_check`, `build_rig`를 추가하고, 메시 검사 뒤 `common.save()` 전에 `build_rig()`를 호출한다. 결과는 `rig` 키로 반환값에 넣는다.

- [ ] **Step 4: 시나리오 통과 확인**

Expected: `build_all()` 성공. `NR_Rig.animation_data.action`이 `TEST_rig_keep`이고, `hand_ik.L` 포즈가 유지된다.

- [ ] **Step 5: 테스트 흔적 제거**

테스트 액션을 지우고 포즈를 비운 뒤 `build_all.py`를 다시 실행해 저장한다.

- [ ] **Step 6: 백그라운드 실행 확인**

Run: `blender -b --python scripts/build_all.py -- <스크래치패드>/rig_test.blend`. 저장되지 않은 새 씬에서 실행되는 경로라 기존 `narang_base.blend`를 덮어쓰지 않는다.
Expected: `NARANG_RESULT` 출력에 `rig` 값이 있고 오류가 없다. `blender`가 PATH에 없으면 설치 경로를 찾아 쓴다.

---

### Task 5: 테스트 포즈와 조정

**Files:**
- Create: `scripts/narang_rig_poses.py`
- Modify: `scripts/build_rig.py` (관절 상수 조정이 필요할 때)
- Modify: `docs/superpowers/specs/2026-11-07-narang-rig-design.md` (값이 바뀌거나 허용 범위를 기록할 때)
- Output: `renders/rig_*.png`

**Interfaces:**
- Consumes: `narang_view.set_view(kind, center, distance)`, `build_rig.build_rig()`
- Produces: `narang_rig_poses.POSES`, `apply_pose(name) -> None`, `clear_pose() -> None`, `render_poses(folder) -> list[str]`

- [ ] **Step 1: 포즈 스크립트 작성**

`POSES` 이름과 내용:
- `walk`: 한 발 앞 접지, 반대 발 뒤, 팔 반대로 흔들기
- `sit`: `torso`를 내려 무릎을 굽힘
- `arms_up`, `arms_down`: 양손을 머리 위, 몸 옆으로
- `nod`: `head` 앞으로 20도, 뒤로 20도 두 장
- `turn`: `head` 좌우 45도

`render_poses`는 포즈마다 `front`, `right`, `three_quarter`를 `bpy.ops.render.opengl(view_context=True, write_still=True)`로 저장한다. 이때 `NARANG_Rig` 컬렉션은 숨겼다가 복원한다. 끝나면 `clear_pose()`한다.

- [ ] **Step 2: 렌더하고 이미지를 읽어 확인**

스펙의 "볼 것"을 포즈별로 기록한다. 무릎과 몸통, 어깨와 몸통, 헬멧과 몸통의 파고듦, 팔꿈치 꺾임, 장식판과 팔찌 뜸.

- [ ] **Step 3: 문제 조정**

관절 상수를 고치고 `build_rig()`를 다시 실행해 렌더한다. 세 번 고쳐도 남는 문제는 동작 허용 범위로 스펙 "위험 요소"에 적는다.

- [ ] **Step 4: 마무리 확인**

`clear_pose()` 뒤 `build_all.py` 실행.
Expected: 메시 검사와 리그 검사 통과, 포즈가 비어 있는 상태로 `narang_base.blend` 저장.

- [ ] **Step 5: 사용자에게 렌더 공유**

포즈별 결과와 남은 허용 범위를 보고한다.
