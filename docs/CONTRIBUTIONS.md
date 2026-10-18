# Git 협업 및 개인별 기여 근거

- 기준일: 2026-10-18 (KST)
- 저장소: [sese15260/codysseyfinal](https://github.com/sese15260/codysseyfinal)
- 기본 브랜치: `main`
- 집계 대상 커밋: [`ffb9fa8b803c84d4e84d043a527c1b206f9b1453`](https://github.com/sese15260/codysseyfinal/commit/ffb9fa8b803c84d4e84d043a527c1b206f9b1453) (`main`의 확인된 HEAD)

## 브랜치와 PR 협업 흐름

GitHub에서 확인한 브랜치는 총 15개다. `main`, `develop`과 `feature/auth-api`, `feature/branding`, `feature/diagnostic-api`, `feature/diagnostic-report`, `feature/frontend-integration`, `feature/frontend-pages`, `feature/init-project`, `feature/landing`, `feature/learning-test-api`, `feature/report-export`, `feature/setup-supabase`, `feature/weak-learning-api`, `feature/weak-learning-report`가 있다. 브랜치가 남아 있다는 사실만으로 현재 작업 중이라고 판단하지 않는다.

확인된 병합 PR 15건 중 [#1](https://github.com/sese15260/codysseyfinal/pull/1)~[#13](https://github.com/sese15260/codysseyfinal/pull/13)은 각 `feature/*`에서 `develop`으로, [#14](https://github.com/sese15260/codysseyfinal/pull/14)와 [#15](https://github.com/sese15260/codysseyfinal/pull/15)는 `develop`에서 `main`으로 병합됐다. 대표 흐름은 진단 API [#3](https://github.com/sese15260/codysseyfinal/pull/3), 프론트엔드 화면 [#9](https://github.com/sese15260/codysseyfinal/pull/9), PDF 보고서 [#13](https://github.com/sese15260/codysseyfinal/pull/13), MVP 통합 [#14](https://github.com/sese15260/codysseyfinal/pull/14)에서 확인할 수 있다. PR 병합 사실은 확인했으나 리뷰 승인·회의·공동 의사결정 과정은 이 자료로 확인하지 않았다.

## 팀원별 확인 가능한 결과물

아래 실명과 역할은 [README의 팀원 역할](../README.md#7-팀원-역할)을 기준으로 했다. 관련 계정은 역할·이름 표기·PR 변경 범위를 대조해 연결했으며, 실명과 계정의 본인 동일성은 별도 자료로 확인하지 못했다. Git 작성자 표기와 GitHub 계정의 대응은 각 대표 PR의 head 커밋에 연결된 GitHub 작성자 계정으로 확인했으며, 그 밖의 별칭은 합산하지 않았다.

| 팀원 / GitHub 계정 / Git 작성자 | 담당 기능과 확인 가능한 결과물 | 대표 근거 |
| --- | --- | --- |
| 이혜원 / `HyewonLee-hub` / `Lee Hyewon` | FastAPI 진단 채점·저장, Supabase 스키마, 인증·학습·AI 해설 및 API 연동. [`backend/app/api/diagnostic.py`](../backend/app/api/diagnostic.py), [`backend/app/services/ai_explanation_service.py`](../backend/app/services/ai_explanation_service.py), [`supabase/migrations/`](../supabase/migrations/) | [진단 API #3](https://github.com/sese15260/codysseyfinal/pull/3), [인증·학습 백엔드 #8](https://github.com/sese15260/codysseyfinal/pull/8), [프론트엔드 API 연동 #10](https://github.com/sese15260/codysseyfinal/pull/10), [작성자 연결 커밋](https://github.com/sese15260/codysseyfinal/commit/9f30623144d7d5a9f571aac96717cc27a21d6068) |
| 김세인 / `sese15260` / `sein` | React 화면·공통 UI·반응형 화면. [`frontend/src/pages/`](../frontend/src/pages/), [`frontend/src/components/`](../frontend/src/components/) | [프론트엔드 화면 #9](https://github.com/sese15260/codysseyfinal/pull/9), [작성자 연결 커밋](https://github.com/sese15260/codysseyfinal/commit/a51a4058e0ee03e7b0ae13fda191ad5087769567) |
| 김태희 / `luvtaehee-prog` / `luvtaehee-prog` | 진단·학습 결과의 PDF 보고서 양식과 내보내기. [`frontend/src/report/`](../frontend/src/report/) | [PDF 보고서 #13](https://github.com/sese15260/codysseyfinal/pull/13), [작성자 연결 커밋](https://github.com/sese15260/codysseyfinal/commit/7449d3d793d15b30bb439b713c91e2a240faf727) |

README에 기재된 서비스 기획, 원본 Figma 디자인, TYPEUP 브랜딩 원안의 개인별 제작 산출물은 GitHub 기록만으로 확인하지 못했다. 저장소에서 확인되는 로고·랜딩 구현은 [#11](https://github.com/sese15260/codysseyfinal/pull/11)과 [#12](https://github.com/sese15260/codysseyfinal/pull/12)의 변경 파일이며 두 PR의 작성자는 `HyewonLee-hub`이다. 따라서 원안 제작자를 해당 코드 작성자 또는 다른 팀원으로 추정하지 않는다.

## 기본 브랜치 비병합 커밋 집계

대상은 위 `main` 커밋에서 도달 가능한 **전체 이력**이다. `git shortlog -sne --no-merges ffb9fa8b803c84d4e84d043a527c1b206f9b1453`으로 Git 작성자 이름·이메일 조합별 건수를 구하고, `git rev-list --count --no-merges ffb9fa8b803c84d4e84d043a527c1b206f9b1453`으로 총 37건을 대조했다. 병합 커밋은 제외하고 일반 커밋은 PR에 포함됐더라도 기본 브랜치에서 도달 가능하면 한 번 센다. 아래 표에서는 이메일을 표시하지 않는다.

| Git 작성자 표기 | 비병합 커밋 수 |
| --- | ---: |
| `Lee Hyewon` | 16 |
| `sein` | 19 |
| `luvtaehee-prog` | 2 |
| **합계** | **37** |

이 수치는 커밋 메타데이터의 분포이며 작업량·품질·기여도 점수나 순위를 뜻하지 않는다. GitHub 밖의 기획·디자인 작업과 공동 작업량은 이 집계에 포함되지 않는다.
