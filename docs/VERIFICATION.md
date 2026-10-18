# 기능 검증 기록 (#2·#4)

## 대상과 실행 환경

- 대상 제품 코드: `ffb9fa8b803c84d4e84d043a527c1b206f9b1453` (`main`/`origin/main`, 2026-10-18 확인). 테스트·CI·이 문서는 이 커밋 위의 미커밋 변경이다. 기존 `docs/ARCHITECTURE.md` 변경은 이 검증 범위 밖이며 유지했다.
- 로컬 실행: Windows, Python 3.12.14, Node.js 24.21.0, npm 11.19.0. Python은 Codex 제공 실행 파일을 사용했고 [기존 백엔드 의존성](../backend/requirements.txt)을 무시되는 `backend/.venv`에 설치했다. 프런트엔드는 [잠금 파일](../frontend/package-lock.json)로 `npm ci`를 실행했다. 추가 테스트 패키지는 없다.
- 자동화 파일: [백엔드 `unittest`](../backend/tests/test_verification.py), [GitHub Actions](../.github/workflows/verification.yml). CI는 이번 작업에서 실행하지 않았다.

## 실행 명령과 결과

| 명령 | 로컬 결과 |
| --- | --- |
| `cd backend && python -m unittest discover -s tests -p 'test_*.py' -v` | **18개 통과, 실패 0개**. 로컬에서는 동일 명령에 Codex Python 실행 파일과 `PYTHONPATH`(기존 의존성 디렉터리)를 사용했다. |
| `cd frontend && npm run build` | 최초 **실패**: 기존 `node_modules`에 잠금 파일의 `jspdf`가 없어 import 해석 실패. |
| `cd frontend && npm ci --no-audit --no-fund` 후 `npm run build` | **통과**: Vite 8.3.3, 341개 모듈 변환. `dist/`는 Git 무시 대상이다. |

테스트 작성 중 첫 실행은 테스트 파일 문법 오류로 실패했고, 다음 실행은 로컬 `TestClient` 경로에서 정체되어 중단했다. 핸들러 직접 호출 방식으로 바꾼 뒤 최종 18개가 통과했으며, 중단된 실행은 통과 근거로 사용하지 않았다. 최초 `npm ci`는 샌드박스 DNS 오류로 실패했고, 네트워크 접근을 허용한 재실행은 통과했다.

GitHub Actions는 `push`·`pull_request`·수동 실행에서 Python 3.12 백엔드 테스트와 Node 24 프런트엔드 `npm ci`/빌드를 별도 작업으로 실행하도록 설정했다. 원격 CI 실행 결과는 **미검증**이다.

## 자동 검증 범위

| 항목 | 확인 내용 |
| --- | --- |
| 진단 채점·저장 | 정오답·함정·점수 계산, 학습자 소유 세션과 풀이 기록 저장 인수·저장 payload, 중복 문항 거부 |
| 취약 유형 추천 | 요청 학습자의 누적 기록 사용, 취약 유형 순위·반복 함정·강점 및 표본 부족 유형 제외 |
| 약점 학습 완료 | 오답 시 연속 정답 초기화, 2회 연속 정답에서만 완료, 답안마다 저장 |
| 오답 복습 대상 갱신 | 문항별 최신 풀이가 오답인 경우만 포함, 이후 정답·재오답에 따른 대상 변화 |
| 타 사용자 접근 | 다른 사용자의 진단 리포트·약점 학습 세션·오답 복습 항목·AI 풀이 접근 거부, AI 풀이 조회의 학습자 필터, 토큰 누락 401 |
| AI 해설 | 구조화된 문제·유형·함정 검색 결과, 생성 응답 스키마 검증, 저장·캐시 적중, 무효 응답·제공자 오류에서 저장 차단 및 502 매핑 |

DB 조회·저장 함수와 AI 제공자 호출은 모두 테스트 대역으로 대체했다. 일부 API 핸들러는 직접 호출해 접근 경계와 오류 매핑을 확인했으며 실제 HTTP 서버, Supabase Auth/DB, AI 제공자, 배포 환경을 통과하는 종단 간 검증은 아니다. 프런트엔드 빌드는 정적 번들 생성만 확인하며 사용자 동작이나 PDF 내용의 정확성을 보증하지 않는다.

## 실제 화면 점검표

2026-10-18에 테스트 전용 계정으로 배포 화면을 점검했다. 계정의 테스트 전용 여부는 사용자가 확인했다. 결과와 근거는 아래의 배포 검증 표에 기록한다.

| 순서 | 화면에서 확인할 동작 | 상태 |
| --- | --- | --- |
| 1. 로그인 | 테스트 계정으로 로그인, 새로고침 후 세션 복원, 로그아웃 확인 | 통과. 중첩 경로 새로고침은 실패(아래 표) |
| 2. 진단 | 진단 문항 제출, 정오답·함정·결과 리포트 및 저장 이력 확인 | 통과 |
| 3. 추천 | 진단 후 취약 세부 유형과 추천 이유, 재로그인 후 동일 이력 반영 확인 | 통과. 진단 직후에는 유형당 표본 1회라 추천 없음 |
| 4. 학습 | 추천 유형 학습에서 오답 후 연속 정답 초기화, 2회 연속 정답 시 완료 확인 | 통과 |
| 5. 복습 | 틀린 문항이 오답 복습에 나타나고, 맞힌 뒤 대상에서 제외되는지 확인 | 통과 |
| 6. AI | 소유한 풀이의 해설 생성, 재요청 시 캐시, 제공자 오류 시 사용자 메시지 확인 | 해설 표시·동일 풀이 재요청 통과. 캐시 여부·제공자 오류 미검증 |
| 7. PDF | 학습 리포트 PDF 다운로드, 내용·한글 글꼴·페이지 잘림 확인 | 통과 |
| 추가. 접근 제어 | 다른 테스트 계정의 세션·풀이 ID로 접근 시 노출되지 않는지 확인 | 미검증 |

## 코드 스타일 검사 (#6)

- 프런트엔드 기존 [ESLint 규칙](../frontend/eslint.config.js)을 그대로 유지한다. 새 [Prettier 설정](../frontend/.prettierrc.json)은 작은따옴표, 세미콜론 없음, 후행 쉼표, 2칸 들여쓰기, 100자 줄 너비, LF 줄 끝을 사용한다. [제외 목록](../frontend/.prettierignore)은 `node_modules/`, `dist/`, `coverage/`, 생성된 `package-lock.json`에 한정한다. 백엔드 스타일 도입은 이번 범위 밖이다.
- [npm 스크립트](../frontend/package.json)의 `npm run format`과 `npm run format:check`는 [변경 파일 선택기](../frontend/scripts/format-changed.mjs)를 사용한다. 로컬에서는 `HEAD` 대비 수정·신규 프런트엔드 파일, CI에서는 PR 기준 커밋 또는 push 직전 커밋 대비 변경 파일 중 Prettier가 지원하고 제외되지 않은 파일을 검사한다. 전체 저장소 포맷은 실행하지 않았다.
- 실행 결과: `cd frontend && npm run lint` **통과(오류 0, 경고 0)**. `npm run format`은 이번 변경 파일 3개만 처리했고, `npm run format:check` **3개 통과**. `npm run build`도 **통과**했다. `prettier --list-different .` 전체 진단은 **기존 미해결 78개 파일**, 종료 코드 1이다. 변경되지 않은 기존 파일은 CI 포맷 검사 대상이 아니며, 이후 수정되면 검사 대상이 된다.
- [CI](../.github/workflows/verification.yml)는 전체 프런트엔드 lint와 변경 파일 포맷 검사를 필수 단계로 추가했고, 백엔드 테스트와 프런트엔드 빌드를 유지한다. 원격 CI 실행은 **미검증**이다. 개발 의존성은 Prettier 3.9.10만 추가하고 [잠금 파일](../frontend/package-lock.json)을 갱신했다.

## 배포 사용자 흐름 검증 (2026-10-18 KST)

- 대상: 프런트엔드 `https://typeup-silk.vercel.app`, 백엔드 `https://typeup-backend.onrender.com`([README](../README.md#10-배포)). Windows Chrome에서 화면 흐름을 실행했다. **실제 배포 커밋은 미확인**이다. 앞의 로컬 제품 코드 커밋 `ffb9fa8b803c84d4e84d043a527c1b206f9b1453`을 배포 버전으로 단정하지 않는다.
- 사용자가 테스트 전용임을 확인한 계정으로 로그인했다. 계정 식별자·비밀값은 기록하지 않았다. 진단 1회, 오답 복습 1회, 약점 학습 1회만 제출했다. AI 해설은 같은 풀이 1건에 대해서만 요청하고 다시 열었다. 테스트 계정의 풀이 기록 외 데이터 변경이나 다른 계정 접근은 실행하지 않았다.

| 항목 | 기대값 | 실제 결과 | 판정·증빙 |
| --- | --- | --- | --- |
| 로그인·세션 | 로그인, 로그아웃, 재로그인 후 기록 유지 | 보호 메뉴에서 로그인 화면 진입, Chrome에서 로그인·로그아웃·재로그인 확인. 재로그인 후 보고서 2건 유지 | **통과** · [인증 상태 기록](evidence/chrome-auth-state-2026-10-18.txt), [재로그인 후 보고서](evidence/reports-after-relogin-2026-10-18.json) |
| 진단 채점·저장 | 20문항 제출 후 결과와 저장 보고서 표시 | 20문항 제출, 저장된 결과 5/20·25% 표시. 재로그인 후 무료진단 보고서 조회 | **통과** · [진단 결과 화면](evidence/diagnostic-result-2026-10-18.jpg), [저장 점수](evidence/saved-report-scores-2026-10-18.json), [재로그인 후 보고서](evidence/reports-after-relogin-2026-10-18.json) |
| 취약 유형 추천 | 풀이 이력에 근거한 유형·이유 표시와 재조회 | 진단 직후 유형별 1회 풀이로 추천 없음. 복습 후 35회 풀이·추천 3개, 학습 후 재로그인 시 38회 풀이·추천 3개 표시 | **통과** · [표본 부족](evidence/recommendation-insufficient-2026-10-18.jpg), [복습 후 추천](evidence/recommendations-after-review-2026-10-18.jpg), [재로그인 후 추천](evidence/recommendations-after-relogin-2026-10-18.json) |
| 약점 학습 완료 | 오답 뒤 연속 정답 2회에만 완료 | 첫 오답 후 연속 정답 0, 다음 두 정답 후 완료. 3회 중 2회 정답·연속 2회가 보고서에 표시 | **통과** · [학습 결과](evidence/weak-learning-complete-2026-10-18.jpg) |
| 오답 복습 대상 갱신 | 복습에서 맞힌 문항이 오답 대상에서 제외 | 진단 오답 15개 중 1개 정답·14개 오답으로 제출, 결과에 남은 오답 14개 표시 | **통과** · [복습 결과](evidence/wrong-review-result-2026-10-18.jpg) |
| AI 해설 표시·동일 풀이 재요청 | 해설 표시, 같은 풀이를 다시 열 때 같은 해설 제공 | 한 풀이의 해설 본문 표시, 닫았다 다시 열어 동일 내용 표시. 다른 풀이의 생성은 실행하지 않음 | **통과(화면)** · [첫 표시](evidence/ai-explanation-first-2026-10-18.jpg), [재표시](evidence/ai-explanation-repeat-2026-10-18.jpg) |
| AI 캐시·RAG 실행 증거 | 첫 응답 `cached=false`, 재요청 `cached=true`, 검색 문맥·제공자 호출 수 확인 | 화면은 `cached` 필드와 검색 문맥을 노출하지 않고 서버 로그도 확보하지 못함. 실제 캐시 적중·검색 문맥·제공자 호출 횟수 및 최초 생성 여부는 판별 불가 | **미검증** · 화면 증빙은 위 AI 항목 참조 |
| 리포트·PDF | 저장된 리포트 조회, PDF 다운로드와 한글·페이지 확인 | 약점 학습 보고서 재조회, PDF 2쪽(A4) 다운로드. 두 쪽 모두 시각 확인 시 한글·내용·페이지 잘림 문제 없음 | **통과** · [개인정보 제외 PDF 점검 기록](evidence/weak-pdf-inspection-2026-10-18.txt), [재조회 보고서](evidence/reports-after-refresh-2026-10-18.json) |
| 새로고침·재로그인 후 기록·추천 | 페이지 재진입 뒤 저장 기록과 추천 유지 | 중첩 경로 새로고침은 404. 홈으로 다시 진입하니 인증 복원, 보고서 2건·추천 3개 유지. 로그아웃·재로그인 후에도 동일 기록·추천 조회 | **통과(기록 유지)** · [새로고침 후 보고서](evidence/reports-after-refresh-2026-10-18.json), [재로그인 후 추천](evidence/recommendations-after-relogin-2026-10-18.json) |
| 중첩 경로 직접 접근·새로고침 | `/login` 및 학습 결과 URL 재방문 시 화면 표시 | `/login` 직접 접근과 `/study/review/wrong/result` 새로고침에서 Vercel `404_NOT_FOUND` | **실패** · [로그인 URL](evidence/login-direct-404-2026-10-18.jpg), [결과 URL](evidence/nested-refresh-404-2026-10-18.jpg) |
| 제공자 오류·타 사용자 접근 | 오류 안내와 다른 사용자 데이터 차단 | 오류를 유발하거나 다른 계정 데이터를 요청하지 않음 | **미검증** · 배포 환경의 추가 검증 필요 |

[검색 서비스](../backend/app/services/ai_retrieval_service.py)는 문제·선택지·유형·함정의 구조화된 문맥을 조립하고, [해설 서비스](../backend/app/services/ai_explanation_service.py)는 저장된 해설 조회 후 생성을 시도한다. 이는 **코드 확인**이며 배포 실행의 검색 문맥·캐시 적중 증거가 아니다. 개인정보가 포함된 원본 PDF는 `docs/evidence/`에 복사하지 않았다. 이 검증은 테스트 계정의 화면 흐름에 한정되며, 전체 사용자·운영 데이터·배포 SHA·서버 로그는 확인하지 못했다.

## Vercel 중첩 경로 404 설정 보완 (2026-10-18 KST)

- 원인: [앱 라우팅](../frontend/src/App.jsx)은 `window.location.pathname`과 `history.pushState`로 경로를 처리한다. Vite 빌드의 진입 파일은 `dist/index.html`이며 기존 저장소에 `vercel.json`이 없었다. 배포 화면에서 `/login` 직접 접근과 `/study/review/wrong/result` 새로고침이 Vercel 404였으므로, 서버가 브라우저 경로에 `index.html`을 제공하지 않은 SPA fallback 누락으로 판단했다. [Vercel의 Vite SPA 안내](https://vercel.com/docs/frameworks/frontend/vite)도 같은 재작성을 명시한다.
- 변경: Vite 앱과 `package.json`이 있는 프로젝트 디렉터리 `frontend/`에 [vercel.json](../frontend/vercel.json)을 추가하고 `/(.*)` → `/index.html` 재작성 1개만 설정했다. Vercel은 [기존 파일을 재작성보다 먼저 제공](https://vercel.com/docs/project-configuration/vercel-json)하므로 빌드된 `/assets/*`는 정적 파일로 남는다. 프런트엔드 API 클라이언트는 `VITE_API_BASE_URL`의 별도 Render 백엔드에 요청하며 Vercel 프로젝트 안에 `/api` 경로는 없다. Vercel 대시보드의 실제 **Root Directory 설정은 저장소에서 확인할 수 없었다**. 배포 전에 `frontend`인지 확인해야 이 파일의 적용을 보장할 수 있다.
- 로컬 결과: `cd frontend && npm run build` **통과**(Vite 8.3.3, 341개 모듈). `vercel.json` JSON·재작성 값 검사와 `npm exec prettier -- --check vercel.json` **통과**. Vite `npm run preview`에서 `/login`, `/diagnosis/result`, `/study/review/wrong/result`, `/mypage/reports/diagnostic/test-session`은 모두 HTTP 200 및 앱 HTML을 반환했고, 실제 `/assets/*.js`는 HTTP 200·`text/javascript`로 앱 HTML이 아니었다. 이 미리보기 검사는 **Vercel 재작성 적용 여부를 검증하지 않는다**.
- 배포 후 재검증할 실제 중첩 경로 3개: `/diagnosis/result`, `/study/review/wrong/result`, `/study/review/weak/result`. 각 URL을 직접 열고 새로고침해 HTTP 200과 해당 화면을 확인한다. `/login` 직접 접근도 기존 실패 회귀 검사로 확인한다. **배포·운영 재검증은 실행하지 않았으며 운영 404 해결은 미확인**이다.

## PR #16 병합·운영 배포 후 확인 (2026-10-18 KST)

- [PR #16](https://github.com/sese15260/codysseyfinal/pull/16)의 최신 소스 커밋 `6d4df9342433dad7325faf25efdffc868d92cf2c`에 대해 GitHub Actions `Verification`의 백엔드 테스트·프런트엔드 빌드가 성공했고, 병합 가능 상태를 확인한 뒤 `main`에 병합했다. 병합 커밋은 [`8cb4ee4ec01ba0679f32c1aef3617adef81c8331`](https://github.com/sese15260/codysseyfinal/commit/8cb4ee4ec01ba0679f32c1aef3617adef81c8331)이다.
- 이 병합 커밋의 [Vercel 배포 상태](https://vercel.com/hyewonlee-hubs-projects/typeup/AFezAp9VCXYH2m2FrVe721XbzdfX)는 GitHub에서 `success`로 확인했다. 운영 주소는 `https://typeup-silk.vercel.app`이다. 운영 도메인이 제공하는 정확한 커밋 식별자는 별도로 확인하지 못했다.
- 기존 테스트 전용 계정으로 로그인된 Chrome 탭에서 `/diagnosis/result`를 직접 열고 새로고침했다. 두 직후 상태 모두 Vercel 404 화면 대신 앱의 `로그인 정보를 확인하는 중입니다.`가 표시됐고, 인증 복원 완료를 기다려도 결과 화면으로 진행하지 않았다. 따라서 실제 진단 결과 표시와 새로고침 성공은 **미검증**이다. 브라우저 확인이 이 상태에서 실패하여 요청에 따라 추가 브라우저 시도를 중단했다.

| 운영 경로 | 직접 접근 | 새로고침 | 실제 결과 화면 판정 |
| --- | --- | --- | --- |
| `/diagnosis/result` | 앱 인증 확인 화면 표시, 결과 미표시 | 앱 인증 확인 화면 표시, 결과 미표시 | **미검증** |
| `/study/review/wrong/result` | 미실행 | 미실행 | **미검증** |
| `/study/review/weak/result` | 미실행 | 미실행 | **미검증** |

HTTP 200 또는 SPA 셸 표시만으로 경로 검증을 통과 처리하지 않았다. 세 결과 화면의 직접 접근·새로고침과 운영 도메인의 배포 커밋 대조를 다시 확인해야 한다. AI 캐시 적중·RAG 실행 문맥도 서버 응답·로그 증거가 없어 **미검증**이다. 새 풀이·AI 해설 생성은 실행하지 않았다.

## 운영 결과 경로 재검증 (2026-10-18 22:49 KST)

- 대상은 `https://typeup-silk.vercel.app`이다. `main`의 문서 커밋 `06df5f5ca3b1200adb008969e27dba98bbd265da`에 연결된 [Vercel 상태](https://vercel.com/hyewonlee-hubs-projects/typeup/27zyeNDeJHAZ8aCmgm2egdU8Vkg4)는 `success`였으나, **운영 도메인이 실제 제공 중인 커밋은 독립적으로 확인하지 못했다**.
- 이전에 테스트 전용임을 확인한 계정으로 Chrome에 다시 로그인했다. 홈과 세 결과 경로에 `로그아웃` 버튼이 표시됐다. 진단 경로의 `로그인 정보를 확인하는 중입니다.`는 잠시 뒤 사라졌으며, 인증 복원에 멈추는 현상은 이번 확인에서 재현되지 않았다. 새 풀이·AI 생성은 하지 않았다.
- 각 URL의 별도 공개 GET은 **HTTP 200, `text/html`, 앱 HTML 진입점**을 반환했다. 이는 아래 브라우저 결과 화면 판정과 별개다. 개인정보 없는 [경로별 관측 기록](evidence/result-routes-recheck-2026-10-18.json)에 직접 접근·새로고침의 화면 문구와 HTTP 점검을 보관했다.

| 경로 | 직접 접근 화면 | 새로고침 화면 | 판정 |
| --- | --- | --- | --- |
| `/diagnosis/result` | `진단 결과가 없습니다.` | `진단 결과가 없습니다.` | Vercel 404는 재현되지 않음. **저장 결과 표시 미검증** |
| `/study/review/wrong/result` | `오답 복습 결과가 없습니다.` | `오답 복습 결과가 없습니다.` | Vercel 404는 재현되지 않음. **저장 결과 표시 미검증** |
| `/study/review/weak/result` | `약점 학습 보고서가 없습니다.` | `약점 학습 보고서가 없습니다.` | Vercel 404는 재현되지 않음. **저장 결과 표시 미검증** |

[앱 경로 상태](../frontend/src/App.jsx)는 진단·오답·약점 세션 ID를 탭의 `sessionStorage`에서 복원한다([진단](../frontend/src/api/diagnostic.js), [오답](../frontend/src/api/learning.js), [약점](../frontend/src/api/weakLearning.js)). 각 결과 페이지는 세션 ID가 없으면 보고서 요청을 하지 않고 위 빈 결과 화면을 표시한다. 이번에는 브라우저 저장소의 ID 존재 여부나 보고서 네트워크 요청을 직접 확인하지 못했으므로, **세션 ID 부재는 화면과 코드에 부합하는 설명이지 실행 원인 확정은 아니다**. 기존 풀이 기록을 이용해 세션 ID가 유지된 상태에서 세 경로를 다시 열거나, 마이페이지의 저장 보고서 URL을 확인해야 실제 결과 표시를 검증할 수 있다. 제품 코드는 수정하지 않았다.

## 기존 학습 세션 결과 복원 시도 (2026-10-18 22:53 KST)

- 테스트 전용 계정의 마이페이지 보고서 목록을 읽기 전용으로 확인했다. 완료된 **진단 5/20·25%**와 **약점 학습 2/3·66.67%**가 표시됐다. 오답 복습은 이 목록에 없고 기존 [오답 결과 화면](evidence/wrong-review-result-2026-10-18.jpg)에도 재조회에 필요한 세션 ID가 없어 대상 세션을 특정하지 못했다. 세션 ID·계정 식별자는 증빙에 기록하지 않았다. [개인정보 없는 이번 관측 기록](evidence/session-result-restore-2026-10-18.json)을 참조한다.
- [앱 라우팅](../frontend/src/App.jsx)은 완료 직후 `/diagnosis/result`, `/study/review/wrong/result`, `/study/review/weak/result`를 만든다. 이 URL에는 ID가 없고 탭의 `sessionStorage`에 저장된 진단 ID·오답 ID·약점 학습 ID와 subtype ID가 필요하다. 반면 [마이페이지 보고서 매핑](../frontend/src/api/mypage.js)은 서버 목록의 ID를 URL에 포함해 `/mypage/reports/diagnostic/{session_id}`와 `/mypage/reports/weak/{session_id}`를 만든다. 마이페이지 목록에는 오답 복습 보고서 경로가 없다.

| 유형 | 기존 세션 확인·화면 | 같은 URL 직접 접근·새로고침 | 판정 |
| --- | --- | --- | --- |
| 진단 | 저장 보고서 5/20을 열어 `/mypage/reports/diagnostic/{session_id}` 형식과 비어 있지 않은 `진단 결과`·강점·우선 연습 화면 확인 | 브라우저 선택자 시간 초과로 안정적인 화면 결과를 확보하지 못함 | **미검증(초기 열기만 확인)**. 세션 점수의 화면 대조와 복원 확인 필요 |
| 오답 복습 | 읽기 전용 목록·기존 증빙에서 완료 세션 ID를 찾지 못함 | 실행하지 않음 | **미검증(대상 ID 없음)** |
| 약점 학습 | 저장 보고서 목록에 2/3·66.67%가 있음. URL의 ID와 보고서 화면은 확인 전 브라우저 검사가 실패함 | 실행하지 않음 | **미검증(브라우저 검사 중단)** |

브라우저 도구의 선택자 시간 초과 뒤에는 요청대로 재시도하지 않았다. 위 빈 상태 경로의 HTTP 200은 기존 세션 보고서의 복원을 증명하지 않는다. 새 풀이·AI 해설 생성 및 제품 코드 수정은 하지 않았다.

## 기존 AI 해설 캐시 재조회 검토 (2026-10-18 KST)

- 기존 [첫 표시](evidence/ai-explanation-first-2026-10-18.jpg)와 [재표시](evidence/ai-explanation-repeat-2026-10-18.jpg)는 같은 풀이의 해설이 화면에 다시 표시된 증빙이다. 기존 검증 기록과 개인정보 없는 텍스트·JSON 증빙에서는 해당 풀이의 `attempt_id`, 이전 해설 응답 또는 `cached` 값을 찾지 못했다. 인증된 읽기 전용 API로 이를 확인할 수 있는 접근 정보도 확보하지 못했다.
- [AI API](../backend/app/api/ai.py)의 `POST /ai/explanations/{attempt_id}`는 [해설 서비스](../backend/app/services/ai_explanation_service.py)에서 캐시가 없으면 검색 후 새 AI 해설을 생성한다. 기존 ID와 캐시 저장을 입증할 수 없어 요청하지 않았다. 따라서 **실제 캐시 적중과 이전 해설의 응답 단위 일치는 미검증**이다. 화면 재표시는 `cached=true`의 증거로 취급하지 않는다.
- RAG 검색 문맥이 생성 요청에 포함됐는지 확인할 배포 실행 로그는 확보하지 못했다. 검색 서비스의 코드상 구현은 실행 증거와 구분하며 **RAG 실행은 미검증**이다.
- 앞서 기록한 `06df5f5ca3b1200adb008969e27dba98bbd265da`의 Vercel 배포 상태 `success`는 운영 도메인이 현재 제공하는 커밋 식별자가 아니므로, **실제 배포 커밋은 미확인**이다.
