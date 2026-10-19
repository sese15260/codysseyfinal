# 코드 스타일과 자동 검사

| 영역 | 설정 | 로컬 검사 | CI 적용 범위 |
| --- | --- | --- | --- |
| 백엔드 Python | 루트 [`pyproject.toml`](../pyproject.toml)의 Ruff 규칙(Python 3.12, 줄 길이 100, E4/E7/E9/F/I) | `ruff check backend` · `ruff format --check backend` | 백엔드 Python 전체 |
| 프런트엔드 JavaScript/JSX | [`eslint.config.js`](../frontend/eslint.config.js) · [`.prettierrc.json`](../frontend/.prettierrc.json) | `cd frontend && npm run lint && npm run format:check` | 전체 lint · 변경 파일 포맷 |

백엔드 파일은 `ruff check --fix backend`와 `ruff format backend`로 정리한다. 프런트엔드 파일은 `npm run format`으로 변경 파일에 포맷을 적용한다. CI 명령과 버전은 [Verification 워크플로](../.github/workflows/verification.yml)를 따른다.
