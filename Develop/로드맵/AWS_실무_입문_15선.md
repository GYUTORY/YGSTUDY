---
title: AWS 실무 입문 15선
tags: [AWS, Cloud, Architecture, DevOps]
updated: 2026-08-07
---

# AWS 실무 입문 15선

AWS를 처음 쓰는 백엔드 개발자를 위한 서비스별 입문 경로입니다.
"어디서부터 읽어야 하나" 막막한 분들을 위해 실무 투입 순서로 정렬했습니다.

---

## 핵심 인프라 (1–5편)

배포 한 번 해보려면 이 5편은 무조건.

1. [VPC](../Cloud/AWS/Network/VPC.md)
   — 퍼블릭/프라이빗 서브넷, IGW, NAT Gateway. 모든 AWS 서비스의 뼈대.

2. [EC2](../Cloud/AWS/Compute/EC2.md)
   — 인스턴스 유형과 구매 옵션. 과금 최적화 포함.

3. [ALB](../Cloud/AWS/Load_Balancer/ALB.md)
   — HTTP 라우팅, HTTPS 오프로드, 타겟 그룹.

4. [RDS](../Cloud/AWS/Database/RDS.md)
   — 관리형 MySQL/PostgreSQL. Multi-AZ와 Read Replica.

5. [IAM](../Cloud/AWS/Security/IAM.md)
   — 최소 권한 원칙. 역할과 정책 설계.

---

## 컨테이너와 서버리스 (6–9편)

모던 백엔드의 핵심 실행 환경.

6. [ECS](../Cloud/AWS/Containers/ECS.md)
   — Fargate 모드로 컨테이너 배포. Task Definition 구조.

7. [Fargate](../Cloud/AWS/Containers/Fargate.md)
   — 서버리스 컨테이너. EC2 관리 없는 ECS.

8. [Lambda](../Cloud/AWS/Compute/Lambda.md)
   — 이벤트 드리븐 함수. 트리거 유형과 한계.

9. [ECR](../Cloud/AWS/Containers/ECR.md)
   — 컨테이너 이미지 저장소. CI/CD 파이프라인 연동.

---

## 스토리지와 메시지 (10–12편)

데이터를 저장하고 흘리는 방법.

10. [S3](../Cloud/AWS/Network/S3.md)
    — 버킷 정책, 퍼블릭 액세스 차단, 라이프사이클.

11. [SQS](../Cloud/AWS/Application_Integration/SQS.md)
    — 큐 기반 비동기 처리. DLQ(Dead Letter Queue) 패턴.

12. [SNS](../Cloud/AWS/Application_Integration/SNS.md)
    — 토픽 기반 팬아웃. SQS와 조합.

---

## 모니터링과 보안 (13–15편)

운영에 진입하기 전 반드시.

13. [CloudWatch](../Cloud/AWS/Monitoring/CloudWatch.md)
    — 메트릭, 로그, 알람. 온콜의 기본 도구.

14. [Secrets Manager](../Cloud/AWS/Security/Secrets_Manager.md)
    — DB 비밀번호와 API 키 관리. `.env` 파일 금지의 대안.

15. [WAF](../Cloud/AWS/Security/WAF.md)
    — L7 방화벽. SQL 인젝션·XSS 차단 규칙.

---

## 서비스 조합 예시

```
[클라이언트]
    ↓ HTTPS
[Route 53] → [ALB] → [ECS/Fargate]
                          ↓
                    [RDS (Private Subnet)]
                    [ElastiCache (Private Subnet)]
                          ↓
                    [S3] (정적 자산)
                    [Secrets Manager] (비밀값)
                    [CloudWatch] (모니터링)
```

이 구성이 스타트업에서 가장 많이 쓰는 표준 스택입니다.

---

## 다음 단계

- **고가용성**: [Multi-AZ](../Cloud/AWS/Database/RDS_Multi_AZ.md), [Auto Scaling](../Cloud/AWS/Compute/Auto_Scaling.md)
- **비용 최적화**: [Savings Plans](../Cloud/AWS/Cost/Savings_Plans.md), [Compute Optimizer](../Cloud/AWS/Cost/Compute_Optimizer.md)
- **심화 네트워킹**: [Transit Gateway](../Cloud/AWS/Network/Transit_Gateway.md), [PrivateLink](../Cloud/AWS/Network/PrivateLink.md)
