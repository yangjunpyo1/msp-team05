# PPT 내용 재검증 (2026-10-23 ~ 10-24 KST)

배포 커밋: origin `feature/frontend-backend-integration` f13510d6 (+ 배포용 worktree 로컬 수정 3건, 미커밋)

## 구조
| # | 결과 | 근거 |
|---|---|---|
| 1 | 맞음 | CloudFront(WAF kky-prod-waf 연결) → ALB kky-prod-alb → ASG EC2 → RDS/ElastiCache |
| 2 | 맞음 | ASG AZ ap-northeast-2a,2c / Min 2, Desired 2, Max 3, 실행 인스턴스 2a·2c 각 1대 |
| 3 | 맞음 | RDS kky-prod-mysql MySQL 8.0 MultiAZ=True(Primary 2c, Standby 2a), Redis 복제그룹 2노드(2c/2a) Multi-AZ·자동 장애조치 |
| 4 | 맞음 | 기본 동작 → S3-Frontend, /api/* 와 /ws/* → ALB-Backend, ECR kky-prod-backend |
| 5 | 맞음 | us-east-1 kkybot.net(+www) ISSUED, DNS 검증(Route53 레코드), CloudFront 사용. 별도로 ALB용 api.kkybot.net 인증서가 ap-northeast-2에 있음 |
| 6 | 맞음 | kky-prod-db-secret(host,port,dbname,username,password), redis-secret, jwt-secret |

## WAF
| # | 결과 | 근거 |
|---|---|---|
| 7 | 맞음 | Priority 0, Block, NOT GeoMatch[KR] |
| 8 | 맞음 | InspectionLevel TARGETED, ScopeDown URI STARTS_WITH /api/ (ML 사용, TGT_TokenReuseIp·TGT_VolumetricSession은 Block으로 override) |
| 9 | 맞음 | Limit 1000 / 300초 / IP, 범위 /api/queue OR /api/reservations (좌석 선점 /api/games/*/seats/lock은 제외) |
| 10 | 맞음 | Priority 3 Allow, URI EXACTLY /actuator/health. 단, CloudFront에 /actuator/* 동작이 없어 S3로 가고 ALB 헬스체크는 WAF를 거치지 않으므로 실제로는 효과가 없음 |

## 자동 대응
| # | 결과 | 근거 |
|---|---|---|
| 11 | 맞음 | 사용자가 set-alarm-state ALARM 실행. 알람 전환 00:06:21.819 → Lambda 실행 00:06:22.386 → "New rate limit: 100" 00:06:25.086, 약 3.3초. 경로: 알람 kky-prod-waf-blocked → SNS kky-prod-waf-alarm-use1 → Lambda kky-prod-waf-auto-response |
| 12 | 맞음(자동) | 다음 평가에서 알람이 ALARM→OK로 바뀜(00:08:03.5) → OKActions → Lambda "New rate limit: 1000"(1000은 00:08:10 조회에서 확인). 수동으로 돌려놓지 않았음. 수동 원복 방법: set-alarm-state OK 또는 terraform apply(코드값 1000). 참고: 알람이 INSUFFICIENT_DATA→OK로 바뀔 때마다 Lambda가 WAF를 1000으로 다시 쓰고 있음(23:53, 00:02 로그) |

## 장애 복구
| # | 결과 | 근거 |
|---|---|---|
| 13 | 맞음(짧은 502 있음) | **재테스트(브라우저, 사용자 IP 핫스팟 IP(사람용)-C):** 00:11:24에 i-0c59449037d0ef3f4(2c) 종료 → 교체 인스턴스가 00:14:16에 healthy(2분 52초), 그동안 i-0aa02c1c17209d051(2a) 1대가 계속 서비스. 사용자 /api 요청 56건 중 200이 52건, **502가 3건**(00:11:27·30·32, CloudFront OriginError. 종료 중인 대상으로 라운드로빈된 요청이며 사이사이 200이 섞여 있음), 000이 1건(00:11:21 클라이언트 연결 끊김). 00:11:33 이후는 모두 200. WAF: 해당 IP ALLOW 280 / BLOCK 0 / CAPTCHA 0 / CHALLENGE 0. ALB 지표: ELB 5XX 3건(00:11), Target 5XX 0건. CloudFront 5xxErrorRate는 00:11에 2.0%, 나머지 0%. ALB ELB 4XX 54건(00:12)·16건(00:13)은 CloudFront 로그에 사용자 4xx가 없어 사용자 요청이 아님. ALB 접근 로그가 꺼져 있어 출처는 확인 불가. 원인 추정: EC2를 직접 종료해서 ASG/ALB 등록 해제(drain) 전에 연결이 끊김. failover-test2.log, cloudfront-failover2.tsv, cloudfront-logs-raw/, waf-logs-raw/15/ 참고 |
| 13(1차) | 참고 | curl 테스트: 00:01:09 종료 → 00:04:27 healthy(3분 18초). curl은 WAF에 막혀 index.html을 받았으므로 API 응답이 이어졌는지 판단하는 근거로는 쓰지 않음. failover-test.log 참고 |

## 앱
| # | 결과 | 근거 |
|---|---|---|
| 14 | 다름(일부) | 순번: Redis INCR queue:position:{gameId}(TTL 24시간). 대기열 토큰: MySQL queue_tokens(Redis 아님). 좌석 임시 선점: Redis setIfAbsent seat_lock:{game}:{seat} TTL 5분(SETNX 방식 분산 락, Redisson 없음). lock_token도 TTL 5분 |

## 사람 테스트 (23:38 이후, S3 WAF 전체 로그 기준)
| # | 결과 | 근거 |
|---|---|---|
| 15 | 아래 참고 | 핫스팟 IP(사람용)-A: ALLOW 69 / BLOCK 10 / CAPTCHA 0 / CHALLENGE 0. 핫스팟 IP(사람용)-B: ALLOW 38 / BLOCK 20 / CAPTCHA 0 / CHALLENGE 0. BLOCK 30건은 모두 BotControlRule / TGT_VolumetricSession |

- 핫스팟 IP(사람용)-A 차단: 23:40:56~23:43:54, /api/games·/api/reservations·/api/auth/login·/api/auth/signup
- 핫스팟 IP(사람용)-B(휴대폰) 차단: 23:52:40부터 /api/games/{id}/seats, /api/reservations, /api/games, /api/queue/enter
- **23:53 휴대폰 예매 실패 원인은 WAF임.** 23:51:52 첫 예매는 성공. 23:52:30 두 번째 시도는 대기열 진입과 좌석 조회까지 ALLOW였지만, 23:52:40부터 TGT_VolumetricSession에 BLOCK되어 좌석 선점 요청까지 가지 못함. 앱의 매수 제한(요청당 최대 4석, EXCEED_MAX_SEATS 400)은 사용자별 누적 제한이 아니며, 23:50~23:56 컨테이너 로그에 WARN/ERROR 없음

## B. 봇 테스트 (집 Wi-Fi, 공인 IP 집 IP(봇용))
- 1차 시도는 PC가 iPhone 핫스팟(핫스팟 IP(사람용)-C)이라 중단하고, 네트워크를 바꾼 뒤 실행함
- 실행 방법: Bot/ 원본은 수정하지 않음. scratchpad에 복사본을 만들어 `BASE_URL`만 https://kkybot.net으로 바꿈(원본은 옛 도메인 kkybot.click). 로그인은 기존 관리자 계정 관리자 테스트 계정(admin@…) 사용(새 계정 없음)
- 로그: bot-v2.log, bot_v7_tls.log, bot_v7_tls_ua.log, bot_v2_error.png, WAF 판정 waf-bot-tests-B.txt

| 테스트 | 결과 | 걸린 규칙 / 근거 |
|---|---|---|
| v2 Selenium (headless Chrome) 00:27 | **차단** | `POST /api/auth/login` BLOCK — BotControlRule / **SignalAutomatedBrowser** (라벨 `bot-control:signal:automated_browser`, 토큰 accepted). /login 페이지(S3)는 ALLOW. 화면에는 "이메일 또는 비밀번호가 올바르지 않습니다"가 뜸(프론트가 모든 로그인 실패를 같은 문구로 표시) |
| v7 원본 (tls_client chrome_120, UA 없음) 00:27:52 | **차단** | `POST /api/auth/login` BLOCK — BotControlRule / **SignalNonBrowserUserAgent** (UA `tls-client/1.0.1`, 토큰 없음). 응답이 JSON이 아니어서 스크립트가 JSONDecodeError로 종료 |
| v7 복사본 + Chrome 120 UA 00:28:13 | **처음 5건 통과 후 CHALLENGE** | login·games·queue/my·queue/enter·queue/status 첫 요청은 ALLOW(토큰 없음). 00:28:17부터 3초 간격 queue/status 52건이 모두 CHALLENGE — BotControlRule / **TGT_VolumetricIpTokenAbsent** (토큰 없이 같은 IP에서 요청이 반복됨). 봇은 challenge를 풀지 못해 대기열을 통과하지 못했고 3분 뒤 타임아웃. 좌석·결제 요청은 보내지 못함 |

## C. 정상 사용자가 차단된 원인 (S3 WAF 전체 로그, waf-volumetric-analysis.txt)
| 구분 | PC 핫스팟 IP(사람용)-A | 휴대폰 핫스팟 IP(사람용)-B |
|---|---|---|
| WAF 토큰 | `token:accepted` (id 4124b3c8, 23:38:49부터) | `token:accepted` (id 51ff39af, 23:50:45부터) |
| 세션 시작 → 첫 BLOCK | 23:38:49 → 23:40:56 (2.1분) | 23:50:45 → 23:52:40 (1.9분) |
| 첫 BLOCK 전 같은 세션의 /api 요청 | 16건 | 22건 |
| 직전 60초 / 300초 /api | 1 / 17건 | 12 / 23건 |
| 많이 호출된 API | GET /api/games 3, queue/status 2, seats 2, 나머지 예매 흐름 각 1 | games·games/{id}·queue/status·seats 각 3, queue enter/exit 각 2, reservations 2 |
| 세션 라벨 | volumetric:session low→medium→high→maximum | 23:52:26 low/medium(ALLOW) → 23:52:40 high(BLOCK) |
| 기타 라벨 | captcha:rejected(:not_solved) — CAPTCHA를 푼 기록이 없다는 뜻이며 차단 원인은 아님 | 동일 |

- **근거:** 두 사람 모두 정상 브라우저였음(토큰 accepted, UA는 Windows Chrome / iPhone Safari). 예매 1회 흐름(목록→상세→대기열 진입·상태·이탈→좌석 조회→선점→결제 준비·확인→예매→예매내역)이 약 2분 동안 /api 16~22건을 만듦. 같은 토큰 세션에서 두 번째 흐름을 시작하거나 화면을 새로고침하자 세션 볼륨 라벨이 high에 도달했고, TGT_VolumetricSession(Block으로 override됨)에 걸림
- **해석(추정):** TGT_VolumetricSession은 같은 토큰 세션의 요청량이 "평소보다 높다"고 판단하면 라벨을 붙이는 규칙임. 새로 만든 Web ACL이라 비교할 정상 트래픽 기준이 거의 없고, SPA가 화면 하나에 여러 API를 동시에 호출해서 세션당 요청이 몰림. 그래서 몇 분 안에 사람도 high로 분류됐을 가능성이 높음. 이 규칙을 Block으로 override한 것(932636c)이 정상 사용자 차단으로 바로 이어짐

## D. 개선 확인
### D1. TGT_VolumetricSession Block override 제거 (2026-10-24 02:45:12 KST, CLI update-web-acl)
- 관리형 규칙의 기본 동작(`describe-managed-rule-group`): **TGT_VolumetricSession = CAPTCHA**, TGT_VolumetricIpTokenAbsent = Challenge
- 변경 전 BotControlRule override: `TGT_TokenReuseIp → Block`, `TGT_VolumetricSession → Block`
- 변경 후 BotControlRule override: `TGT_TokenReuseIp → Block` (TGT_VolumetricSession은 기본 동작인 CAPTCHA로 돌아감)
- 그 밖의 설정(규칙 순서, Geo, RateBasedRule 1000, HealthCheck, 기본 동작 Allow)은 그대로임. 증거: webacl-before-D1.json, webacl-after-D1.json, D1-change.log
- **주의:** Terraform 코드(modules/waf/main.tf)에는 아직 Block override가 남아 있어서, `terraform apply`를 하면 이 변경이 되돌아감

### D2 준비: 프론트 WAF CAPTCHA/Challenge 공통 처리 (2026-10-24 02:52:20 KST 배포, 미커밋, msp-team05-deploy)
- `Frontend/src/api/wafCaptcha.ts` (신규): `showWafCaptcha()`는 화면 공통 모달에 `AwsWafCaptcha.renderCaptcha`를 띄우고, 풀면 resolve함. 여러 요청이 동시에 405를 받아도 모달은 하나만 뜸. `solveWafChallenge()`는 `AwsWafIntegration.getToken()`으로 토큰을 받음. CAPTCHA API 키와 `window` 타입 선언을 SeatSelectPage에서 이 파일로 옮김
- `Frontend/src/api/axios.ts:2` import 추가, `:22-32` 성공 응답 중 202 + `x-amzn-waf-action: challenge`이면 토큰을 받고 1회 재시도, `:38-46` 405 + `x-amzn-waf-action: captcha`이면 캡차를 푼 뒤 1회 재시도(`_wafRetry` 플래그로 반복 방지)
- `Frontend/src/pages/SeatSelectPage.tsx`: 화면 전용 캡차 코드 삭제(기존 :36 API 키, :60-75 window 타입, :88-93 캡차 state, :140-158 renderCaptcha effect, :287-310 모달 JSX). `fetchZones`(:72-76)는 `AwsWafIntegration.fetch` 대신 `api.get`을 쓰도록 바꿈
- 검증: `tsc -b && vite build` 통과. 번들에 `x-amzn-waf-action` 처리가 들어 있고 `kkybot.click`/`localhost:8080` 참조는 0건. S3 sync 후 CloudFront 무효화 I85AHIQN190OODKM9YWRRB649B. WAF는 D1 상태 그대로(override는 TGT_TokenReuseIp 하나)

### D2 사람 재테스트 (02:52~02:54 KST, 핫스팟 핫스팟 IP(사람용)-D) — waf-D2-0252.txt
- WAF 34건이 모두 ALLOW이고, **volumetric 라벨(low/medium/high)은 0건**, CAPTCHA도 0건. 토큰은 aee9ff4d 하나이고 accepted 상태
- 이 IP의 WAF·CloudFront 로그는 모두 **02:53:30~02:54:36(66초)**만 있고, 그 안의 `/api` 요청은 22건. 좌석 선점과 예매 확정은 각 1회 → 로그로는 예매 1회만 확인됨(사용자가 말한 "2회 연속"과 다름. 02:52대 요청은 없음)
- 지난번과 비교: /api 요청 수는 비슷함(PC 16건/2.1분, 휴대폰 22건/1.9분 → 이번 22건/1.1분). 다른 점은 세션 길이와 흐름 횟수. 지난번은 같은 토큰으로 예매를 끝낸 뒤 두 번째 흐름을 시작하면서 라벨이 붙었고, 이번에는 세션 66초 동안 흐름 1회로 끝남

### D2 사람 재테스트 2회차 (사용자 보고: 1차 03:20~03:24 집 Wi-Fi 집 IP(봇용), 2차 핫스팟 시각 미기재) — waf-D2-0320-0328.txt
- **2차(핫스팟 핫스팟 IP(사람용)-E):** WAF와 CloudFront 로그 모두 **03:28:15~03:28:59(44초)**만 있음. 25건이 모두 ALLOW이고, `/api` 13건, 좌석 선점 1회, **예매 확정(POST /api/reservations) 1회**, **volumetric 라벨 0건**, **CAPTCHA 발생 0건**. 토큰은 aee9ff4d로 02:53 세션과 같은 토큰을 다시 씀
- **1차(집 IP(봇용), 03:20~03:24):** WAF S3 로그(18/20 폴더 없음), CloudFront 로그(18:20~18:24에 이 IP 0건), WAF 샘플 어디에도 요청이 없음 → kkybot.net에 도달한 요청이 없음
- 결론: 로그 기준으로는 "같은 탭에서 예매 2회 + 새로고침"이 재현되지 않았음(예매 확정 1회, 44초). 그래서 TGT_VolumetricSession이 CAPTCHA로 바뀐 뒤의 동작은 아직 검증되지 않음

### D3 준비: 토큰 없는 대기열·예매 요청에 Challenge 규칙 추가 (2026-10-24 03:36:14 KST, CLI update-web-acl)
- **적용 전 확인(token-absent-precheck.txt):** WAF 로그 571건(23:13~03:28) 중 `/api/queue/enter`와 `/api/reservations` 요청은 사람 브라우저 IP(핫스팟 IP(사람용)-A, B, D, E 등) 모두 `token:accepted`였음. `token:absent`는 1건뿐이고, B 테스트의 v7 UA 위장 봇(집 IP(봇용), 00:28:14 POST /api/queue/enter)이었음 → 정상 브라우저 흐름은 이 규칙에 걸리지 않음
- **추가한 규칙:** `TokenAbsentChallengeRule`, Priority 2, Action **Challenge**. 조건: 라벨 `awswaf:managed:token:absent` AND (URI가 `/api/queue/enter`로 시작 OR `/api/reservations`로 시작). 샘플과 지표 사용(MetricName TokenAbsentChallengeRule)
- **우선순위 변경:** Bot Control 바로 다음에 넣느라 기존 RateBasedRule 2→3, HealthCheckExceptionRule 3→4로 한 칸씩 밀림(평가 순서는 그대로). 그 밖의 설정(Geo, Bot override TGT_TokenReuseIp, Rate 1000)은 변경 없음
- 라벨은 Bot Control(범위 /api/)이 붙이므로 두 경로 모두 라벨 평가 대상임. 프론트는 202 Challenge를 axios 인터셉터에서 처리함(토큰 발급 후 1회 재시도)
- 증거: webacl-before-tokenrule.json, webacl-after-tokenrule.json, tokenrule-change.log
- **주의:** Terraform 코드에는 이 규칙이 없음. `terraform apply`를 하면 이 규칙이 삭제되고 우선순위와 D1 변경도 되돌아감

### 정상 사용자 테스트 (03:38~03:48 KST, 핫스팟, D1 + TokenAbsentChallengeRule 적용 상태) — user-test-0338-sessions.json, user-test-0338-detail.txt
WAF 로그 172건(03:36~03:59, 18/35·18/40·18/45 폴더 파일 5개)을 WAF 토큰(세션)별로 나눔. 토큰 없는 첫 요청은 같은 IP·UA의 토큰 세션에 붙여서 셈.

| 세션(토큰) | 시간 | 기기 / IP | ALLOW | CAPTCHA | CHALLENGE | BLOCK | volumetric 라벨 | 캡차 통과 | 예매 확정 |
|---|---|---|---|---|---|---|---|---|---|
| 9cecff09 | 03:38:11~03:45:06 | Windows Chrome / 핫스팟 IP(사람용)-E | 131 | 1 (03:40:26 POST seats/lock) | 0 | 0 | low→medium→high→maximum | **통과** (03:40:33 같은 요청 재시도 ALLOW, captcha:accepted) | **8** (03:39:08, 03:40:35, 03:41:00, 03:41:29, 03:43:13, 03:43:42, 03:44:40, 03:45:05) |
| 82864f86 | 03:45:25~03:47:48 | iPhone Safari / 핫스팟 IP(사람용)-F | 39 | 1 (03:47:20 GET seats) | 0 | 0 | low→medium→high | **통과** (03:47:34 재시도 ALLOW) | **2** (03:46:37, 03:47:47) |

**전체 요약**
- WAF 세션 2개, 예매 성공 10회(PC 8 + iPhone 2), BLOCK 0건, **막혀서 예매하지 못한 세션 0개(오탐 0)**
- 캡차가 뜬 세션 2개 중 **2개 모두 통과**(7초, 14초 만에 재시도 성공). 두 번 모두 TGT_VolumetricSession(기본 동작 CAPTCHA). 각 세션의 2번째 예매 흐름에서 high 라벨이 붙은 직후에 뜸 → 사용자가 말한 "2회째쯤 캡차"와 일치
- 캡차를 푼 뒤에는 high/maximum 라벨이 계속 붙어도 captcha:accepted 상태라 추가 캡차 없이 통과함
- TokenAbsentChallengeRule과 CHALLENGE는 0건(사람 요청은 모두 token:accepted)
- **기록과 다른 점:** 사용자는 "회차마다 시크릿 창을 새로 열었다"고 했지만, PC 쪽은 8회 예매가 모두 같은 WAF 토큰(9cecff09)이었음. Chrome 시크릿 창은 열려 있는 시크릿 창이 하나라도 있으면 쿠키를 함께 쓰므로, 시크릿 창을 모두 닫지 않고 새로 열면 같은 세션이 됨(추정)

### 봇 최종 재검증 (최종 WAF 설정: D1 + TokenAbsentChallengeRule) — bots-final/
- 네트워크: 집 Wi-Fi 집 Wi-Fi, 공인 IP 집 IP(봇용)(핫스팟 아님). 시간 03:58~04:05 KST
- Bot/ 원본은 수정하지 않음. scratchpad/bots2에 복사본을 만들어 `BASE_URL`만 kkybot.net으로 바꿈. 로그인 계정은 관리자 테스트 계정(admin@…). v3는 scratchpad venv(playwright 1.60.0, playwright-stealth 2.0.3, 브라우저도 scratchpad)로 실행. v5는 사용자 승인(A)으로 원본 그대로 실행(동시 10)
- WAF 판정 근거: bots-final/waf-bots-final.txt (S3 로그 18/55, 19/00, 19/05)

| 봇 | 로그인 | 대기열 | 좌석 선점 | 결제 | 예매 확정 | 막힌 지점 / 규칙 |
|---|---|---|---|---|---|---|
| v1 requests | ✗ | - | - | - | - | POST /api/auth/login **BLOCK** BotControlRule/**CategoryHttpLibrary** (UA python-requests) |
| v2 Selenium headless | ✗ | - | - | - | - | POST /api/auth/login **BLOCK** BotControlRule/**SignalAutomatedBrowser** |
| v3 Playwright + stealth | ✗ | - | - | - | - | POST /api/auth/login **BLOCK** BotControlRule/**SignalAutomatedBrowser** (stealth를 써도 탐지됨) |
| v4 매크로(requests + 브라우저 UA 위장) | ✓ | (호출 안 함) | ✓ | ✓ prepare·confirm | ✗ | POST /api/reservations **CHALLENGE** **TokenAbsentChallengeRule** |
| v5 동시 10 + IP 헤더 위장 | ✗ | - | - | - | - | 첫 요청 GET /api/games 10건 모두 **CHALLENGE** BotControlRule/**TGT_VolumetricIpTokenAbsent**. 가입 단계까지 가지 않아 봇 계정 생성 0 |
| v6 WebSocket | ✗ | - | - | - | - | POST /api/auth/login **BLOCK** BotControlRule/**CategoryHttpLibrary** |
| v7 tls_client | ✗ | - | - | - | - | POST /api/auth/login **BLOCK** BotControlRule/**SignalNonBrowserUserAgent** (UA tls-client) |
| v7 + Chrome 120 UA | ✗ | - | - | - | - | POST /api/auth/login **CHALLENGE** BotControlRule/**TGT_VolumetricIpTokenAbsent** |

- **예매까지 간 봇 0개.** BLOCK 5개(v1, v2, v3, v6, v7), CHALLENGE 3개(v4, v5, v7+UA)
- **v4가 로그인·결제를 통과한 이유:** requests 라이브러리지만 headers.py의 브라우저 UA(Mac)를 써서 non_browser_user_agent·http_library 신호가 없었음. 토큰은 없었지만(token:absent), 이 시점(04:00)에는 같은 IP의 토큰 없는 요청이 아직 적어서 TGT_VolumetricIpTokenAbsent 라벨도 붙지 않음(04:01 v6부터 붙음). TokenAbsentChallengeRule은 `/api/queue/enter`와 `/api/reservations`에만 걸리는데, v4는 대기열을 건너뛰므로 예매 확정에서 처음 걸림
- **새 규칙 검증:** TokenAbsentChallengeRule은 v4의 `/api/reservations`에서 실제로 동작함(CHALLENGE). **v7 + Chrome UA는 이번에 로그인 단계에서 TGT_VolumetricIpTokenAbsent에 먼저 걸려 대기열까지 가지 못했으므로, 대기열 진입에서 막히는지는 확인되지 않음.** 참고로 규칙을 넣기 전(00:28, B 테스트)에는 같은 봇이 대기열 진입까지 ALLOW였음
- **남은 위험:** v4는 결제 준비·확정(`/api/payments/*`)까지 성공한 뒤 예매에서 막힘 → 결제는 DONE인데 예매가 없는 데이터가 생길 수 있음. 결제 API는 Rate·TokenAbsent 규칙 범위 밖이고, 앱도 대기열을 거치지 않은 결제를 막지 않음

### 앱 대기열 통과 검사 추가 (2026-10-24 04:23 배포, msp-team05-deploy, 미커밋) — queue-pass-verify.log
- **방식:** 대기열이 ALLOWED가 되면 Redis `queue:pass:{gameId}:{userId}`를 TTL 10분으로 발급. 좌석 선점 성공 시 TTL을 10분으로 다시 늘림(선점 5분 + 결제 여유 5분). 예매 확정 시 삭제(한 번 통과 = 한 번 예매). 기록이 없으면 **409 `QUEUE_NOT_PASSED`** (403은 CloudFront가 index.html로 바꾸므로 사용하지 않음)
- **변경 파일:**
  - `Backend/.../domain/queue/service/QueuePassService.java` (신규): grant/require/extendForPayment/consume
  - `Backend/.../domain/queue/scheduler/QueueScheduler.java:5,21,53`: ALLOWED로 바꿀 때 grant
  - `Backend/.../domain/seat/service/SeatService.java:7,44,152-154,192-194`: lockSeats 앞에서 require, 선점 성공 후 extendForPayment
  - `Backend/.../domain/payment/controller/PaymentController.java:7,34,57-59`: prepare에서 require(seatLock의 경기). confirm은 prepare가 만든 orderId로만 진행되므로 따로 검사하지 않음
  - `Backend/.../domain/reservation/service/ReservationService.java:7,37,53-55,82-84`: createReservation 앞에서 require, 끝에서 consume
  - `Frontend/src/pages/SeatSelectPage.tsx` handleLock catch, `Frontend/src/pages/CheckoutPage.tsx:49-54`: 409 QUEUE_NOT_PASSED를 받으면 "대기열을 먼저 통과해 주세요." 알림을 띄우고 경기 상세로 이동
- **배포:** compileJava 통과 → Docker 이미지 7221027a → ECR push → Instance Refresh 성공(04:34:50, 2대 healthy). 프론트 S3 sync + CloudFront 무효화 I2G5U0TWKOUQGQY9UX2XBAM2W1
- **검증 (SSM으로 EC2 안의 localhost:8080, 관리자 계정):**
  1. 대기열 없이 좌석 선점 → **409 QUEUE_NOT_PASSED**
  2. 정상 흐름: 대기열 진입 → 약 4초 뒤 ALLOWED → 통과 기록 TTL 600 → 5초 뒤 594 → 선점 성공 후 600으로 늘어남 → prepare·confirm·reservation 모두 200 → 예매 후 통과 기록 삭제(TTL -2) → 대기열을 다시 거치지 않고 선점하면 **409**
  3. 통과 기록이 있을 때 선점하고 기록을 지운 뒤 prepare → **409**, reservation → **409**
- 남은 확인: 브라우저 정상 흐름(알림 표시 포함), v4 재실행(좌석 선점에서 409가 예상됨)

### TokenAbsentChallengeRule 범위 확장: 좌석 선점·결제 (2026-10-24 04:38:18 KST, CLI update-web-acl)
- **적용 전 확인(token-absent-precheck-lock-payments.txt):** WAF 로그 770건(23:13~04:05) 중 사람 브라우저 IP 5개(핫스팟 IP(사람용)-A, B, D, E, F)가 보낸 `POST .../seats/lock`, `/api/payments/prepare`, `/api/payments/confirm` 45건은 **모두 token:accepted**였음. token:absent 3건은 모두 v4 봇(집 IP(봇용), 04:00:40~41)
- **변경 전 경로:** STARTS_WITH `/api/queue/enter` | STARTS_WITH `/api/reservations`
- **변경 후 경로:** 위 2개 + **ENDS_WITH `/seats/lock`** + **STARTS_WITH `/api/payments/`**. 좌석 선점 경로는 중간에 경기 ID가 있어서 끝부분으로 맞춤. 라벨 조건(token:absent)은 Bot Control(범위 /api/)이 붙이므로 /api/ 밖의 경로는 맞지 않음
- 규칙 순서, Action(Challenge), Bot override(TGT_TokenReuseIp), Rate 1000은 변경 없음
- 증거: webacl-before-tokenrule-v2.json, webacl-after-tokenrule-v2.json, tokenrule-v2-change.log
- **주의:** Terraform 코드에는 이 규칙이 없으므로 `terraform apply`를 하면 되돌아감. 확장 후 봇(v4)·사람 테스트는 아직 하지 않음

### 앱 통과 검사 + WAF 범위 확장 후 재검증 (04:39~04:43 KST) — user-test-0439-*.json/txt, bots-final/v4-after-queuepass.log, db-check-0445.txt
**사람 테스트 (핫스팟, WAF 로그 19/35·19/40 + CloudFront 로그 + DB)**
| 세션(토큰) | 시간 | 기기 / IP | ALLOW | CAPTCHA | CHALLENGE | BLOCK | 409 QUEUE_NOT_PASSED | 예매 확정(DB) |
|---|---|---|---|---|---|---|---|---|
| 63b506f1 | 04:39:53~04:41:18 | Windows Chrome / 핫스팟 IP(사람용)-G | 35 | 0 | 0 | 0 | 0 | 2 (04:40:53, 04:41:17) |
| 82864f86 | 04:41:30~04:41:49 | iPhone Safari / 핫스팟 IP(사람용)-H | 18 | 0 | 0 | 0 | 0 | 1 (04:41:48) |
- 사용자 보고(PC 2회, 휴대폰 1회)와 DB 예매 3건이 일치함. CloudFront의 /api 응답은 모두 2xx이고 409는 0건 → 정상 사용자 오탐 0

**v4 재실행 (집 Wi-Fi 집 IP(봇용), 04:43)**
- 로그인·경기 조회·좌석 조회는 ALLOW. `POST /api/games/{id}/seats/lock`에서 **CHALLENGE — TokenAbsentChallengeRule(WAF)** (token:absent, CloudFront 202). 요청이 앱까지 가지 않았으므로 앱의 409 검사는 이번에 동작하지 않음(앱 검사는 SSM 직접 호출로 따로 검증함)
- 결제 단계에 가지 못함 → 이번에 새로 생긴 결제 없음

**결제만 있고 예매가 없는 데이터 (DB)**
- `payments.created_at`이 모두 NULL이라 시간으로 맞출 수 없음 → 사용자별 PAID 건수와 예매(distinct lock_token) 건수를 비교함. 결제 상태값은 API 응답의 DONE이 아니라 DB에는 `PAID`로 저장됨
- 사용자 계정: PAID 18 / 예매 18 (일치). 관리자 계정: PAID 2 / 예매 1 → 짝이 없는 1건은 수정 전 04:00 v4 실행분. 수정 후(04:23 이후) **새로 생긴 건은 없음**(04:35 SSM 정상 흐름은 결제와 예매가 함께 생성됨). botv5 계정 0개

## 파일
- waf-logs-raw/ : S3 aws-waf-logs-kky-prod 원본(.log.gz)
- waf-analysis-since-2338.txt : IP별 집계, 차단 상세, 23:48~23:58 전체 요청
- waf-sampled/ : get-sampled-requests 결과(JSON)
- webacl-rules-before-test.json : 테스트 전 WAF 규칙
- failover-test.log : 13번 로그
