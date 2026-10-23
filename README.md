<div align="center">

# ⚾ KKY 야구 티켓팅
### AWS WAF Bot Control 매크로 봇 방어 실측 프로젝트
**MSP Architect Training 2026 · Team 05**

---

![Frontend](https://img.shields.io/badge/Frontend-React%20%7C%20TypeScript-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Backend](https://img.shields.io/badge/Backend-Spring%20Boot%203.2.4-6DB33F?style=for-the-badge&logo=springboot&logoColor=white)
![Database](https://img.shields.io/badge/Database-MySQL%20%7C%20Redis-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![Infra](https://img.shields.io/badge/Infra-AWS%20%7C%20Terraform-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)
![Deploy](https://img.shields.io/badge/Deploy-Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![WAF](https://img.shields.io/badge/WAF-Bot%20Control%20Targeted-DD344C?style=for-the-badge&logo=amazonaws&logoColor=white)
![Monitoring](https://img.shields.io/badge/Monitoring-CloudWatch%20%7C%20Athena-F46800?style=for-the-badge&logo=amazonaws&logoColor=white)

</div>

---

## 📌 배경

### 🏢 기업 관점

티켓팅 서비스를 운영하다 보면 오픈 순간마다 같은 상황이 반복된다.  
매크로 봇이 대량 요청으로 좌석을 선점하고, 정상 사용자는 티켓을 구하지 못한다.  
독점된 티켓은 암표 시장에서 몇 배의 가격으로 거래되고,  
**결국 서비스에 대한 신뢰도 하락으로 이어진다.**

### 👤 사용자 관점

티켓 오픈 시간에 맞춰 대기하고, 정각에 버튼을 눌렀는데 이미 매진이다.  
분명히 오픈 직후였는데 어떻게 된 건지 알 수가 없다.  
매크로 봇이 이미 모든 좌석을 점유한 뒤였다.  
얼마 지나지 않아 같은 티켓이 몇 배의 가격으로 암표 시장에 올라온다.

---

## 🎯 프로젝트 목표

매크로 봇 문제를 해결하기 위한 솔루션은 존재하지만,  
**AWS WAF Bot Control만으로 어느 수준까지 방어 가능한지 직접 확인한 실측 데이터는 찾기 어렵다.**

단계별 매크로 봇으로 WAF Bot Control이 어느 수준의 봇까지 막는지 한계를 확인하고,  
**봇 차단 결과와 정상 사용자 오탐 여부를 수치로 남겨 도입 판단 근거를 만든다.**

---

## 💡 기대 효과

- **실측 데이터 제공** — AWS WAF Bot Control의 실제 방어 결과를 WAF 로그 기반으로 공개
- **오탐 확인** — 정상 사용자가 차단될 위험을 직접 접속 테스트로 확인
- **자동 대응 검증** — 공격 감지 시 방어 규칙을 자동으로 강화하는 파이프라인의 대응 시간 측정

---

## 🧪 검증 시나리오

| # | 방식 | 내용 |
|---|------|------|
| 1 | Before / After | 단순 HTTP 봇 → Selenium → Playwright + Stealth → TLS 위장 봇까지 단계별 차단 비교 |
| 2 | Chaos Engineering | EC2 강제 종료 시 서비스 응답 유지 여부와 ASG 복구 시간 측정 |
| 3 | 자동 대응 | CloudWatch 알람 → SNS → Lambda → WAF 규칙 강화까지 걸린 시간 측정 |

---

## 📊 성공 기준 (KPI)

| 항목 | 기준 | 결과 |
|------|------|------|
| 단순 HTTP 봇 (Python requests) | 차단 | ✓ 로그인 단계 차단 |
| 브라우저 자동화 봇 (Selenium, Playwright + Stealth) | 차단 | ✓ 로그인 단계 차단 |
| 정상 사용자 오탐 | 차단 0회 | ✓ 예매 13회 모두 성공 (재검증 후) |
| 자동 대응 속도 | ≤ 60초 | ✓ 약 3.3초 |

---

## ✅ 결과

### 프로젝트 기간 (팀)
- 봇 6종(v1, v3~v7)이 로그인 단계에서 Challenge 또는 차단됨 (WAF 로그 기준)
- 자동 대응 파이프라인 동작 확인 (알람 전환 후 약 3초)
- EC2 1대 종료 시 ASG 자동 복구 확인

### 프로젝트 이후 재검증 (2026-10-23 ~ 10-24, 개인)
인프라를 다시 배포해 정상 사용자 테스트와 봇 테스트를 다시 진행했고, 찾은 문제를 수정한 뒤 재확인했다.

| 구분 | 수정 전 | 수정 후 |
|------|---------|---------|
| 정상 사용자 (직접 브라우저 접속) | 5회 중 2회 차단 | 예매 13회 모두 성공, 차단 0회 |
| 대기열을 건너뛰는 봇 (v4) | 좌석 선점·결제까지 성공 | 좌석 선점 단계에서 차단 |
| 봇 8종 (v1~v7 + UA 위장 v7) | - | 예매까지 간 봇 0개 |
| 자동 대응 | - | 알람 전환 후 약 3.3초 |
| EC2 1대 장애 | - | 2분 52초 만에 복구, 종료 직후 약 5초간 요청 3건 502 |

**수정 내용**
- **정상 사용자 차단 해결**: 세션 요청량 규칙(TGT_VolumetricSession)을 Block으로 강화했던 설정이 정상 사용자를 막았음 → 기본 동작(CAPTCHA)으로 되돌리고, 앱이 모든 화면에서 WAF CAPTCHA·Challenge를 처리하도록 수정
- **토큰 없는 요청 차단**: 브라우저 검사 토큰이 없는 요청이 대기열 진입·좌석 선점·결제·예매로 오면 Challenge를 거는 WAF 규칙 추가
- **대기열 우회 차단**: 백엔드에서 대기열 통과 여부를 좌석 선점·결제·예매 전에 검사하도록 추가 (WAF가 뚫려도 앱에서 한 번 더 확인)

자세한 결과와 근거 로그: [RESULTS.md](https://github.com/yangjunpyo1/msp-team05/blob/feature/infra/docs/evidence/retest-2026-10-23/RESULTS.md)

### 한계
- 실제 여러 IP를 쓰는 봇은 테스트하지 못함 (v5의 IP 로테이션은 헤더 위조 방식)
- 실제 브라우저 확장 프로그램 매크로처럼 WAF 토큰을 받아내는 봇은 테스트하지 못함
- 정상 사용자 테스트는 한 명이 PC와 휴대폰으로 진행한 소규모 테스트
- 실제 티켓 오픈 수준의 대규모 트래픽은 검증하지 않음

---

## 🏗️ 시스템 아키텍처

<img width="950" height="850" alt="image" src="https://github.com/user-attachments/assets/cab75c62-71e6-4213-a746-6dc888bd0cd9" />

> 📖 상세 아키텍처는 [Wiki — 시스템 아키텍처](../../wiki/시스템-아키텍처) 참조

---

## 🛠️ 기술 스택

| 계층 | 기술 |
|------|------|
| **Frontend** | React TypeScript · Vite · Tailwind CSS |
| **Backend** | Spring Boot 3.2.4 · JPA · Spring Security · JWT |
| **Database** | RDS MySQL 8.0 · ElastiCache Redis 7.x |
| **WAF / Security** | AWS WAF Bot Control Targeted · CloudFront · Geo IP 차단 |
| **Infra** | EC2 + Auto Scaling · ALB · S3 · Secrets Manager · ACM · Route53 |
| **IaC** | Terraform |
| **분석** | Athena · CloudWatch |
| **자동 대응** | CloudWatch → SNS → Lambda → WAF |
| **봇 시뮬레이션** | Python requests · Selenium · Playwright |

---

## 📂 브랜치

| 브랜치 | 내용 |
|--------|------|
| `feature/frontend-backend-integration` | 프로젝트 기간 앱 코드 (Backend, Frontend, Bot) |
| `feature/infra` | Terraform 인프라 코드, 재검증 결과 (`docs/evidence/retest-2026-10-23/`) |
| `feature/retest-fixes` | 재검증 후 앱 수정 (WAF CAPTCHA 공통 처리, 대기열 통과 검사, CORS) |

---

## 👥 팀원

| 역할 | 이름 | 주요 담당 | GitHub |
|------|------|-----------|--------|
| 팀장 | 김재훈 | | |
| 팀원 | 김수경 | | |
| 팀원 | 양준표 | | [yangjunpyo1](https://github.com/yangjunpyo1) |

---

## 📚 문서

자세한 내용은 **[Wiki](../../wiki)** 를 참고해주세요.  
프로젝트 진행 현황 → **[Project Board](https://github.com/Team-msp-architect-2026/msp-team05/projects)**
