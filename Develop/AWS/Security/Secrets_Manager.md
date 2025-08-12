최종 업데이트 2025-08-08, 버전 v1.0

> 이전 명칭 안내: 과거 표기 Secret_Mangager/Secret Manager → AWS Secrets Manager로 통일했습니다.
---
title: AWS Secrets Manager
tags: [aws, security, secretsmanager]
updated: 2025-08-10
---

## 왜 Secrets Manager인가?
- 중앙집중형 관리, 자동 로테이션, 세밀한 접근제어(IAM), CloudTrail 연동, KMS 암호화

## 배경
- 시크릿 저장/검색(API/SDK)
- 자동 로테이션(Lambda)
- IAM 기반 접근제어
- CloudTrail 감사
- KMS 암호화

- AWS Secrets Manager — AWS Docs, `https://docs.aws.amazon.com/secretsmanager/`
- Rotate secrets — AWS Docs, `https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html`

---

- [IAM](./IAM.md) — 최소 권한 설계의 기반
- [KMS](./KMS.md) — 암호화 키 관리 배경
- [CloudTrail](../Monitoring & Management/CloudTrail.md) — 접근 감사 연계






AWS Secrets Manager는 완전관리형 시크릿 관리 서비스로, 애플리케이션/서비스에서 사용하는 민감 정보를 안전하게 저장·관리·조회할 수 있게 해줍니다. (DB 자격 증명, API 키, OAuth 토큰 등)





# AWS Secrets Manager란 무엇인가?

## KMS와의 관계(차이 간단 정리)
- Secrets Manager: 시크릿의 수명주기/로테이션/접근 제어
- KMS: 암호화 키 생성/보관/암복호화 (Secrets Manager 내부적으로 KMS 사용)

## Parameter Store와 비교(요약)
| 항목 | Secrets Manager | Parameter Store |
|---|---|---|
| 목적 | 시크릿 관리 | 설정/파라미터 관리 |
| 로테이션 | 지원 | 기본 미지원 |
| 비용 | 유료 | 기본 무료(고급은 유료) |

