# SDD ledger — plan: docs/superpowers/plans/2026-11-04-narang-base-mesh.md

Setup: Ruling: git 저장소가 아니므로 worktree, sdd 스크립트, 커밋을 생략하고 이 파일을 수동 관리한다 — 사용자가 git init을 요청하지 않았고 계획에도 커밋이 없음 — 틀려도 나중에 git init하면 됨.
Pre-flight: Task 2~4는 Task 1의 replace_object, check_part를 소비, Task 5는 check_scene과 NR_* 10개를 소비. 이름 일치, 충돌 없음.
Task 1: complete (Cube 검사 통과, 없는 파트 KeyError RED, 재실행 중복 없음, 기존 씬 보존, blend 저장)
Task 2: Ruling: outline()이 270도 초과에서 음수 각도가 되어 턱 윤곽이 잘못됨 — 각도 정규화로 수정, outline(300도)==0.89 재현 후 수정. 비용 없음.
Task 2: Ruling: 쉘, 바이저, 테두리, 몸통, 목 링, 패널도 반쪽 + 미러로 제작 — 스펙의 좌우 대칭 규칙을 가운데 파트까지 적용 — 틀려도 미러 적용으로 해결.
Task 2: complete (4파트 non_manifold 0, boundary 0, 쉘 폭 0.588 높이 0.510)
Task 3: Ruling: 몸통을 0.15~0.50에서 0.12~0.50으로 늘림 — 스티커 대비 다리가 길어 보임, 스펙이 조정을 허용, 스펙 표도 갱신 — 틀려도 상수 하나 수정.
Task 3: Ruling: 목 링을 z 0.482, 주반경 0.09로 조정 — 측면에서 헬멧과 벌어져 보임 — 상수 수정.
Task 3: complete (4파트 닫힘)
Task 4: Ruling: 손가락 측정 범위 0.03을 0.02로 축소 — 옆 손가락까지 측정돼 0.042로 과대 측정 — 측정값이 근사치임.
Task 4: complete (손가락 0.0221~0.0233, NR_Leg min_z 0)
Task 5: complete (10파트 닫힘, 키 0.9949, STL non_manifold 0, shells 1, 100mm, 사본 잔류 없음)
Final review: 별도 검토자(opus). Critical 0, Important 4, Minor 7.
Final: fixed 세웠을 때 불안정 — stand_margin RED 2.09도 → GREEN 4.32도 (발바닥 평평하게, 앞뒤로 연장)
Final: fixed 손가락 측정 오류와 납작한 단면 — finger_sections RED 비율 1.7~2.49 → GREEN 1.10~1.35, 최소 폭 0.0248. Task 4의 0.0221~0.0233 기록은 측정 오류였음.
Final: Ruling: 단면 측정을 25, 50, 75%에서 50, 75%로 변경 — 엄지 25% 단면은 폭 0.05~0.08로 손바닥을 자른 값 — 뿌리 쪽 단면은 검증되지 않음.
Final: Ruling: 발바닥을 평평하게 변경 — 스펙의 "끝이 둥근 발"과 다르지만 가장자리는 둥글고 STL 안정성이 우선 — 외형이 어색하면 LEG_SECTIONS 수정.
Final: fixed 새 세션 재현 불가 — build_all.py 추가, 새 블렌더 프로세스에서 같은 수치로 빌드 확인
Final: fixed 스티커 비교 근거 없음 — renders/compare_sticker.png 생성, 닮음 판단은 사용자 확인 대기
Final: Ruling: 작업 기록을 지우지 않고 유지 — git 이력이 없어 이 파일이 유일한 기록 — 폴더 하나가 남음.
Final: minor (deferred): all_outward가 전체 부피 부호만 검사
Final: minor (deferred): tri_ratio가 Subdivision 뒤 값이라 항상 0
Final: minor (deferred): shells, height_mm 검사의 판별력이 약함 (검토자가 STL 파일을 따로 검사해 이상 없음 확인)
Final: minor (deferred): export_stl_test에 try/finally 없음
Final: minor (deferred): merged_mesh에 MESH 타입 필터 없음, 리깅 전에 수정 필요
Final: minor (deferred): check_scene이 파트 이름을 확인하지 않음
Final: minor (deferred): 리깅 후 빌더를 다시 실행하면 웨이트와 부모 관계가 사라짐

Revision: 사용자가 기존 모델을 거부하고 턴어라운드 시트 제공. 시트를 기준으로 전체 재제작.
Revision: Ruling: 양팔을 시트의 날개형으로 대칭 제작, 가리키는 팔은 만들지 않음 — 리깅용 기본 자세 — 가리키기는 리깅 후 포즈로 표현.
Revision: Ruling: 얼굴, 하트 텍스처와 백팩을 범위에 포함 — 사용자가 최대한 비슷하게 요청 — 초기 스펙의 제외 항목 번복.
Revision: Ruling: 발바닥은 평평하게 유지, 넘어짐 기준 4도를 3도로 완화 — 시트의 작은 발로는 4도 불가 — 출력 시 받침대 필요.
Revision: Ruling: STL에서 복셀 2개 크기 이하의 내부 빈 공간 삭제 — 실제 부품 크기 아님 — 삭제 개수를 보고.

Revision 2 (2026-11-07): 사용자가 새 시트 기준 재제작을 요청. 기준을 reference/narang_turnaround_v2.png로 변경, 키 1 = 797px.
Revision 2: Ruling: 백팩, 플라스크, 호스를 코드까지 완전 삭제 — 사용자 지시 — git 이력에서 복구 가능.
Revision 2: Ruling: 팔은 정면, 후면 뷰를 따름 — 시트 측면 뷰는 팔이 내려와 있어 T포즈와 불일치 — 측면 IoU가 그만큼 낮게 나옴.
Revision 2: Ruling: 엄지를 NR_Thumb 별도 파트로 분리 — 면 돌출은 Subdivision에 묻혀 주름이 안 생김 — 리깅 때 손 뼈에 같이 묶어야 함.
Revision 2: fixed narang_compare 구멍 메우기가 팔찌와 목 사이 빈 공간까지 채움 — 바깥에서 채우는 방식으로 교체, IoU가 전보다 엄격해짐.
Revision 2: complete (25파트 닫힘, 키 0.9971, 넘어짐 5.39도, IoU 정면 0.962 우 0.953 좌 0.940 후 0.964, STL non_manifold 0, shells 1, 100mm, OBJ 25파트)
Revision 2: open: 옆 장식판이 측면에서 모양이 고르지 않음, 턱 V자가 시트보다 부드러움, 바이저가 시트보다 회색으로 렌더됨. 사용자 승인 대기.

Revision 3 (2026-11-07): 사용자가 엄지(소시지를 붙인 느낌)와 하반신(다리 왜곡, 발이 다리와 끊김)을 지적.
Revision 3: Ruling: NR_Thumb 폐기, NR_Hand로 교체 — 손바닥 안쪽 한 점에서 방사형으로 표면을 찾아 손과 엄지를 한 표면으로 만듦. 팔과 손 경계는 팔찌 아래, 리깅 때 NR_Arm과 NR_Hand를 같이 묶어야 함.
Revision 3: Ruling: 단면 쌓기 방식의 손은 엄지 끝이 선반처럼 잘려 폐기 — 시도 후 확인.
Revision 3: Ruling: 다리와 발을 foot_point 표면 하나로 재제작. 밑창(NR_Shoe)은 그 표면을 기울어진 선(SOLE_LINE) 아래로 덮는 껍질, 장식판도 같은 표면 위에 놓음.
Revision 3: complete (25파트 닫힘, 키 0.9971, 넘어짐 4.23도, IoU 정면 0.965 우 0.955 좌 0.942 후 0.965, STL non_manifold 0, shells 1, 100mm, OBJ 25파트)
Revision 3: open: 턱 V자가 시트보다 부드러움, 바이저가 시트보다 회색으로 렌더됨. 사용자 승인 대기.

Revision 4 (2026-11-07): 사용자가 날개를 지적. 달걀 겹치기와 둥근 막대 합치기는 윗선이 울퉁불퉁하고 주름이 얕아 폐기.
Revision 4: Ruling: 시트에서 딴 윤곽(OUTLINE)을 쿠션처럼 부풀리는 방식으로 재제작 — 깃털 사이 홈에서 뿌리 쪽으로 주름을 파고, 날개 평면은 위쪽만 몸에 붙고 아래로 벌어짐.
Revision 4: complete (25파트 닫힘, 키 0.9971, 넘어짐 4.34도, IoU 정면 0.964 우 0.959 좌 0.946 후 0.966). STL, OBJ 재출력.
Revision 5 (2026-11-07): 얼굴 N을 시트의 뾰족한 글자에서 narang_ex (3).png의 고딕체로 변경. 사용자 지시로 이 글자만 시트 대신 예시 이미지를 따름. 텍스처만 변경, 메시 수치 동일.
