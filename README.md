# TYPEUP

> 틀린 문제보다, 틀린 유형을 찾는 TOEIC 맞춤 학습 서비스

TYPEUP은 TOEIC Part 5·6 문법 문제를 세부 유형과 오답 함정 단위로 분석하여  
사용자의 취약 유형을 찾고, 개인별 학습 추천과 오답 복습, AI 해설을 제공하는 학습 서비스입니다.

단순히 몇 문제를 맞고 틀렸는지를 보여주는 것이 아니라,

- 어떤 세부 유형에서 자주 틀리는지
- 어떤 오답 함정에 반복해서 걸리는지
- 다음에 어떤 학습을 진행해야 하는지

를 누적 학습 데이터를 기반으로 분석합니다.

## 평가 자료 바로가기

- [서비스 아키텍처](docs/ARCHITECTURE.md)
- [기능·CI 검증 결과](docs/VERIFICATION.md)
- [코드 스타일·자동 검사](docs/STYLE.md)
- [안정성 측정 결과](docs/STABILITY.md)
- [사용자 설문 결과](docs/USER_FEEDBACK.md)
- [Git 협업·팀원별 기여](docs/CONTRIBUTIONS.md)

---

## 1. 프로젝트 개요

### 프로젝트명

**TYPEUP**

### 프로젝트 목표

기존 TOEIC 문제 풀이 서비스는 정답률이나 오답 문제 중심으로 학습 결과를 제공하는 경우가 많습니다.

TYPEUP은 문제를 세부 유형과 함정 단위로 구조화하고 사용자의 풀이 기록을 누적하여,  
단순 오답 복습을 넘어 **취약 유형 기반 맞춤 학습 경험**을 제공하는 것을 목표로 합니다.

### 핵심 사용자 흐름

```text
회원가입 / 로그인
        ↓
무료 진단 20문항
        ↓
진단 결과
        ↓
취약 유형 분석
        ↓
맞춤 학습 추천
        ↓
약점 유형 반복 학습
        ↓
오답 복습
        ↓
AI 오답 해설
        ↓
학습 리포트 / PDF 보고서
```

추가적으로 일반 학습, 문법 집중, 어휘 집중, 오늘의 단어 및 단어 퀴즈 기능을 제공합니다.

---

## 2. 주요 기능

### 2.1 회원가입 / 로그인

- Supabase Auth 기반 사용자 인증
- Access Token 기반 보호 API 호출
- 로그인 상태 복원
- 사용자별 학습 데이터 분리
- 다른 사용자의 학습 세션 및 리포트 접근 방지를 위한 ownership 검증

---

### 2.2 무료 진단

- TOEIC 문법 진단 20문항 제공
- Frontend에서는 정답을 보유하지 않음
- Backend에서 답안을 채점하고 풀이 기록 저장
- 진단 결과를 기반으로 강점 및 취약 유형 제공

---

### 2.3 취약 유형 분석 및 학습 추천

사용자의 누적 풀이 기록을 세부 유형(subtype) 단위로 분석합니다.

분석 요소:

- 총 풀이 수
- 정답 수 / 오답 수
- 정답률
- 최근 오답 여부
- 마지막 풀이 결과
- 연속 오답 횟수
- 반복적으로 발생한 오답 함정(trap)

추천은 LLM이 아닌 **규칙 기반 알고리즘**으로 수행합니다.

```text
낮은 정답률
+ 충분한 풀이 표본
+ 최근 오답
+ 마지막 오답
+ 연속 오답
+ 반복 함정
        ↓
취약 유형 우선순위 계산
        ↓
최대 3개 유형 추천
```

---

### 2.4 약점 유형 반복 학습

추천된 세부 유형을 기준으로 문제를 한 문제씩 제공합니다.

```text
취약 subtype 선택
        ↓
해당 subtype 문제 풀이
        ↓
정답 여부 확인
        ↓
2회 연속 정답
        ↓
약점 학습 완료
```

현재 MVP에서는 AI가 새로운 문제를 생성하지 않고,  
기존 문제은행에서 해당 취약 유형과 일치하는 문제를 제공합니다.

AI 신규 문제 생성 기능은 추후 고도화 기능으로 계획하고 있습니다.

---

### 2.5 일반 / 어휘 / 문법 학습

사용자는 세 가지 학습 모드를 선택할 수 있습니다.

- 기본 실력 점검 (`general`)
- 어휘 집중 (`vocabulary`)
- 문법 집중 (`grammar`)

학습 시작 시 문제와 순서를 세션에 고정하여 새로고침 후에도 동일한 학습을 이어갈 수 있습니다.

학습 도중에는 **다른 학습 선택** 기능을 통해 현재 학습을 종료하고 다른 모드를 선택할 수 있습니다.

---

### 2.6 오답 복습

오답 복습은 단순히 과거에 한 번이라도 틀린 문제를 모두 보여주지 않습니다.

각 문제의 **가장 최근 풀이 결과**를 기준으로 복습 대상을 결정합니다.

```text
최근 풀이가 오답
→ 복습 대상

복습 후 정답
→ 오답 목록에서 제외
```

---

### 2.7 AI 오답 해설

사용자가 틀린 문제의 `attempt_id`를 기준으로 관련 데이터를 조회한 뒤 LLM에 전달합니다.

활용 정보:

- 문제 본문
- 선택지
- 정답
- 사용자가 선택한 답
- 상위 유형(type)
- 세부 유형(subtype)
- 세부 유형 학습 규칙(subtype_specs)
- 사용자가 걸린 오답 함정(trap)

AI는 이를 바탕으로 다음 내용을 생성합니다.

- 핵심 요약
- 정답 이유
- 사용자가 선택한 답이 틀린 이유
- 오답 함정 설명
- 기억해야 할 문법 규칙
- 다음 문제 풀이 팁

동일한 attempt에 대해서는 생성된 해설을 DB에 저장하여 재사용합니다.

---

### 2.8 오늘의 단어

- 사용자별 오늘의 단어 최대 30개 제공
- 단어 저장
- 암기 처리
- 암기 완료 단어 제외 및 새로운 단어 보충
- 저장 단어 목록 제공

---

### 2.9 단어 퀴즈

사용자가 저장한 단어를 기반으로 4지선다형 퀴즈를 제공합니다.

```text
영어 단어
→ 한국어 뜻 선택
→ 제출
→ 정답률 및 결과 확인
```

---

### 2.10 마이페이지

- 사용자 프로필 조회 및 수정
- 이름 / 나이 수정
- 완료된 학습 리포트 확인
- 진단 / 일반 학습 / 약점 학습 결과 상세 조회

---

### 2.11 학습 리포트 및 PDF Export

학습 결과를 웹에서 확인할 수 있으며 PDF 파일로 다운로드할 수 있습니다.

리포트에는 실제 학습 데이터만 사용하며,  
Backend에 존재하지 않는 TOEIC 예상 점수 등을 임의로 생성하지 않습니다.

---

## 3. AI 기술 요소

프로젝트 필수 기술 요소 중 다음 기능을 적용했습니다.

### 3.1 RAG

TYPEUP의 AI 해설은 구조화된 DB 검색을 기반으로 한 RAG 방식을 사용합니다.

```text
Retrieval
attempt_id 기준 문제 / subtype / subtype_specs / trap 검색
        ↓
Augmentation
검색 결과를 LLM Context에 추가
        ↓
Generation
개인화된 AI 오답 해설 생성
```

현재는 structured exact retrieval 방식이며,  
향후 embedding 및 vector search 기반 검색으로 확장할 예정입니다.

---

### 3.2 Long-term Memory

사용자의 학습 기록을 세션 종료 후에도 계속 저장하고 다음 학습 추천에 활용합니다.

```text
문제 풀이
→ question_attempts 누적 저장
→ 이후 로그인 / 학습에서도 기록 유지
→ 취약 유형 분석
→ 맞춤 학습 추천
```

이를 통해 사용자의 장기 학습 이력을 개인화에 활용합니다.

---

## 4. 데이터 구조

문제를 다음과 같이 구조화합니다.

```text
Type
  ↓
Subtype
  ↓
Question
  ↓
Choice
  ↓
Trap
```

예시:

```text
상위 유형: 품사
세부 유형: 부사 자리
문제: TOEIC Part 5 문법 문제
오답 보기: 형용사
Trap: 품사 혼동
```

사용자의 문제 풀이 결과는 `question_attempts`에 누적됩니다.

주요 저장 정보:

```text
learner_id
question_id
subtype_id
selected_choice
is_correct
trap_id
answered_at
```

---

## 5. 시스템 구조

```text
React Frontend
      ↓
FastAPI Router
      ↓
Service
      ↓
Repository
      ↓
Supabase
```

### Backend 역할 분리

#### API / Router

- HTTP Request / Response 처리
- 인증된 사용자 확인

#### Service

- 채점
- 추천 알고리즘
- 학습 완료 조건
- AI 해설 context 구성 등 비즈니스 로직

#### Repository

- Supabase 데이터 조회
- 데이터 저장 / 수정

#### Schema

- API Request / Response 형식 정의

---

## 6. 기술 스택

### Frontend

- React
- Vite
- JavaScript
- Tailwind CSS
- Axios
- jsPDF
- html2canvas

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic

### Database / Authentication

- Supabase
- PostgreSQL
- Supabase Auth

### AI

- OpenAI-compatible API
- `gpt-5-mini`
- Structured Retrieval 기반 RAG
- 사용자 학습 기록 기반 Long-term Memory

### Deployment

- Frontend: Vercel
- Backend: Render
- Database: Supabase

### Collaboration / Version Control

- Git
- GitHub
- GitHub Pull Request

---

## 7. 팀원 역할

| 팀원   | 역할                            | 주요 작업                                                                                      |
| ------ | ------------------------------- | ---------------------------------------------------------------------------------------------- |
| 이혜원 | Backend / DB / AI / Integration | FastAPI, Supabase DB 설계, 인증, 학습 API, 추천 알고리즘, AI 해설, Frontend-Backend 연동, 배포 |
| 김세인 | Frontend / UI                   | Figma 기반 화면 구현, React UI, 반응형 화면                                                    |
| 김태희 | 기획 / 디자인 / Report          | 서비스 기획, 사용자 흐름, TYPEUP 브랜딩, 보고서 템플릿 및 PDF Export                           |

Git 협업 및 개인별 기여 근거: [CONTRIBUTIONS.md](docs/CONTRIBUTIONS.md)

대표 커밋: 이혜원 [진단 API](https://github.com/sese15260/codysseyfinal/commit/9f30623144d7d5a9f571aac96717cc27a21d6068) · 김세인 [프런트엔드 화면](https://github.com/sese15260/codysseyfinal/commit/a51a4058e0ee03e7b0ae13fda191ad5087769567) · 김태희 [PDF 보고서](https://github.com/sese15260/codysseyfinal/commit/7449d3d793d15b30bb439b713c91e2a240faf727)

---

## 8. 프로젝트 구조

```text
codysseyfinal/
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── assets/
│   │   ├── auth/
│   │   ├── components/
│   │   ├── pages/
│   │   └── report/
│   ├── package.json
│   └── .env.example
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   └── services/
│   ├── scripts/
│   ├── requirements.txt
│   └── .env.example
│
├── supabase/
│   └── migrations/
│
├── docs/
│   └── API.md
│
└── README.md
```

---

## 9. 실행 방법

## 9.1 Repository Clone

```bash
git clone https://github.com/sese15260/codysseyfinal.git
cd codysseyfinal
```

---

## 9.2 Backend 실행

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`backend/.env` 파일을 생성합니다.

```env
SUPABASE_URL=your_supabase_url
SUPABASE_SECRET_KEY=your_supabase_secret_key

OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://copa.codyssey.kr/v1
OPENAI_MODEL=gpt-5-mini

ALLOWED_ORIGINS=http://localhost:5173
```

Backend 실행:

```bash
PYTHONPATH=. uvicorn app.main:app --reload
```

Backend:

```text
http://localhost:8000
```

Health Check:

```text
http://localhost:8000/health
```

Swagger API 문서:

```text
http://localhost:8000/docs
```

---

## 9.3 Frontend 실행

새 터미널에서:

```bash
cd frontend
npm install
```

`frontend/.env` 파일을 생성합니다.

```env
VITE_API_BASE_URL=http://localhost:8000
```

Frontend 실행:

```bash
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

## 10. 배포

### Frontend

Vercel

```text
https://typeup-silk.vercel.app
```

### Backend

Render

```text
https://typeup-backend.onrender.com
```

### API Documentation

```text
https://typeup-backend.onrender.com/docs
```

---

## 11. Git / Branch 전략

기능별 branch에서 개발한 뒤 `develop`에서 통합 테스트를 진행하고,  
안정화된 버전을 `main`으로 병합합니다.

```text
feature/*
    ↓
develop
    ↓
main
    ↓
Production Deployment
```

예시:

```text
feature/auth-api
feature/frontend-integration
feature/branding
feature/landing
feature/report-export
```

작업 흐름:

```bash
git checkout develop
git pull origin develop

git checkout -b feature/example
```

작업 완료 후:

```bash
git add .
git commit -m "feat: add example feature"
git push -u origin feature/example
```

GitHub Pull Request:

```text
feature/* → develop
```

최종 안정화 후:

```text
develop → main
```

---

## 12. 결과

현재 MVP에서 다음 사용자 흐름을 구현했습니다.

```text
회원가입
→ 로그인
→ 진단
→ 취약 유형 분석
→ 맞춤 학습 추천
→ 약점 반복 학습
→ 오답 복습
→ AI 해설
→ 리포트
→ PDF 다운로드
```

추가적으로:

- 기본 실력 점검
- 문법 집중 학습
- 어휘 집중 학습
- 오늘의 단어
- 저장 단어
- 단어 퀴즈
- 사용자 프로필
- 학습 기록 조회

기능을 구현했습니다.

Frontend와 Backend를 실제 배포 환경에 연결하여  
Vercel → Render → Supabase 간 종단 간 동작을 확인했습니다.

### 안정성 측정 결과

2026-10-18 배포 백엔드를 약 4시간 점검한 기록에서 요청 92건 중 91건이 정상 응답했으며, 서버 HTTP 오류는 관측되지 않았습니다. 자세한 결과는 [안정성 검증 기록](docs/STABILITY.md)에 있습니다.

---

## 13. 사용자 테스트

2026-10-17 사용자 설문 9건의 문항별 결과와 자유 의견을 [사용자 피드백 집계](docs/USER_FEEDBACK.md)에 기록했습니다.

주요 평가 항목:

- 서비스 사용성
- 진단 결과 이해도
- 취약 유형 분석의 적절성
- 맞춤 학습 추천의 유용성
- AI 오답 해설의 유용성
- 전체 만족도
- 재사용 의향
- 개선이 필요한 기능

사용자 피드백을 바탕으로 서비스 개선 방향을 도출합니다.

---

## 14. 현재 한계 및 향후 개선

### 현재 MVP 한계

- AI 신규 문제 생성 기능 미구현
- 문제 데이터 규모 제한
- 약점 해소 기준이 2회 연속 정답으로 단순함
- 추천 알고리즘 가중치가 규칙 기반
- TOEIC 실제 점수 환산 모델 없음
- RAG가 structured retrieval 방식으로 구현됨

### 향후 개선

- Embedding + Vector DB 기반 RAG 고도화
- AI Agent 기반 학습 코치
- 사용자 수준에 따른 문제 난이도 조절
- AI 기반 개인별 신규 문제 생성
- 취약 유형 판단 신뢰도 개선
- 추천 알고리즘 고도화
- 테스트 코드 확대
- React Router 기반 routing 구조 개선

---

## 15. TYPEUP

**틀린 문제보다, 틀린 유형을 찾습니다.**

진단을 통해 취약 유형을 확인하고,  
필요한 학습부터 집중적으로 보완해보세요.
