# 저빈도 가용성 예비 측정 (#3)

## 대상과 조건

- 대상 코드 버전: `ffb9fa8b803c84d4e84d043a527c1b206f9b1453` (`main`/`origin/main`). 측정 스크립트와 이 문서는 미커밋 변경이다.
- 배포 주소: [README](../README.md#10-배포)의 Render 백엔드 `https://typeup-backend.onrender.com`.
- 측정 URL: [`GET /health`](https://typeup-backend.onrender.com/health)([구현](../backend/app/main.py))와 [`GET /diagnostic/items?limit=1`](https://typeup-backend.onrender.com/diagnostic/items?limit=1)([라우터](../backend/app/api/diagnostic.py), [조회 서비스](../backend/app/services/diagnostic_service.py), [읽기 전용 저장소 조회](../backend/app/repositories/question_repository.py)). 후자는 인증 없는 공개 문항 조회이며 `select`만 수행한다.
- 실행 환경·도구: Windows, Python 3.12.14(Codex 제공 실행 파일), 표준 라이브러리 기반 [check_stability.py](../backend/scripts/check_stability.py). 두 URL을 한 번에 하나씩 번갈아 요청하고 요청 시작 목표 간격은 60초다. 총 측정 목표 600초, 요청 타임아웃 50초. 인증 헤더, 쓰기 요청, AI 호출 없음.
- 증빙: [요청별 JSONL](evidence/stability-preview-2026-10-18.jsonl). 각 행에는 UTC 요청 시각, URL, HTTP 상태코드, 지연시간, 오류가 있다. 성공은 최종 HTTP 2xx로 정의한다. p50/p95는 성공한 요청 지연시간의 최근접 순위값이다.

## 10분 예비 측정 결과

2026-10-18 **15:41:35~15:51:35 KST**(06:41:35~06:51:35 UTC), 실제 경과 **600.0초**. `while` 반복은 시작 즉시 1건을 요청한 뒤 전체 URL 목록에서 다음 URL로 넘어가며, 시작 시각부터 600초 미만인 0·60·…·540초에만 요청한다. 따라서 전체 10건, 두 URL 각각 5건이다. JSONL의 UTC 시각 기준 **전체 요청 간격은 59.990~60.012초**, **같은 URL의 요청 간격은 `/health` 119.987~120.014초, `/diagnostic/items?limit=1` 119.999~120.009초**였다. 마지막 540초 요청 뒤 남은 시간까지 대기하여 600초를 측정했으며, 그 60초 구간에 요청이 있었던 것으로 계산하지 않는다. 아래 성공률은 각 URL에서 관측한 5건에만 적용된다.

| URL | 표본 / 성공 | 표본 성공률 | 성공 응답 p50 | 성공 응답 p95 | 최장 연속 실패 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `/health` | 5 / 5 | 100% | 156 ms | 1,141 ms | 0건 |
| `/diagnostic/items?limit=1` | 5 / 5 | 100% | 797 ms | 2,016 ms | 0건 |

실행 명령(PowerShell):

```powershell
& 'C:\Users\sese1\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' backend/scripts/check_stability.py `
  --url 'https://typeup-backend.onrender.com/health' `
  --url 'https://typeup-backend.onrender.com/diagnostic/items?limit=1' `
  --duration-seconds 600 --interval-seconds 60 --timeout-seconds 50 `
  --output docs/evidence/stability-preview-2026-10-18.jsonl
```

JSONL 증빙 10행의 SHA-256: `67ac27e0635076170fc8d7a4ad7806125d72cd0ca8c3a4919eb0cc9a80451b16`.

측정 전 별도 단일 `/health` 연결 확인은 샌드박스 DNS 오류로 실패했고, 네트워크 접근을 허용한 재요청도 20초 응답 타임아웃이었다. 이 예비 요청은 10분 표본에 포함하지 않는다.

## 24시간 측정 (진행 중)

```powershell
& 'C:\Users\sese1\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' backend/scripts/check_stability.py `
  --url 'https://typeup-backend.onrender.com/health' `
  --url 'https://typeup-backend.onrender.com/diagnostic/items?limit=1' `
  --duration-seconds 86400 --interval-seconds 60 --timeout-seconds 50 --prevent-sleep `
  --output docs/evidence/stability-24h-YYYYMMDD.jsonl
```

이 브랜치는 병합 후 `main` 커밋 `06df5f5ca3b1200adb008969e27dba98bbd265da`를 기준으로 작성했다. 이 PC의 자동 절전 설정은 AC/DC 모두 180초이므로, 장시간 측정에는 `--prevent-sleep`으로 Windows에 실행 중 시스템 유지를 요청한다. 이 요청은 프로세스가 종료되면 해제되며 수동 절전·노트북 덮개 닫기·전원 차단·네트워크 단절까지 막지는 못한다. 완료 후 JSONL 요청 시각 간격과 오류, 표준 출력의 최종 요약, 표준 오류를 대조해 중단·누락·비정상 간격을 결과에 명시한다. 완료 전에는 24시간 성공률이나 업타임을 확정하지 않는다.

2026-10-18 **19:30:03 KST**에 위 인자와 두 공개 URL로 Windows `Start-Process -WindowStyle Hidden`을 사용해 시작했다(PID `43804`). 요청 진행 기록은 커밋하지 않는 `docs/evidence/stability-24h-20261018.jsonl`, 최종 출력은 `docs/evidence/stability-24h-20261018.stdout.log`, 오류 출력은 `docs/evidence/stability-24h-20261018.stderr.log`에 분리했다. 시작 뒤 독립 프로세스가 실행 중이고 JSONL 기록이 증가하는 것을 확인했다. **예상 종료는 2026-10-19 19:30:03 KST**이며, 이 시각은 완료를 보장하지 않는다. PC 절전·네트워크 중단 여부와 실제 측정 경과·성공률은 종료 후 로그로 확인해야 한다. 진행 중 파일 3개는 PR에 포함하지 않는다.

이 방식의 성공률은 관측한 GET 표본의 비율이며 표본 사이 미측정 시간을 업타임으로 환산하지 않는다. 순차·저빈도 가용성 확인이므로 부하 테스트, 로그인부터 PDF까지의 사용자 흐름 검증, 운영 DB·AI 통합 검증을 대신하지 않는다.
