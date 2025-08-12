---
title: AWS
tags: [aws, security, basic]
updated: 2025-08-10
---
# AWS 보안 서비스 통합 개요

## 배경
- AWS WAF
  - L7(HTTP/HTTPS) 보안 필터. 규칙으로 요청을 허용·차단·카운트한다.
  - 샘플 로그를 CloudWatch Logs/S3/Kinesis로 내보내 트렌드와 공격 패턴을 본다.
- AWS Shield
  - DDoS 완화 서비스. Standard는 기본 제공, Advanced는 L3/4/7 보호와 비용 보호, 24x7 DRT 연계.
  - 공격 이벤트/지표가 CloudWatch로 노출되어 상황을 관찰할 수 있다.

- Amazon GuardDuty
  - 위협 탐지 서비스. CloudTrail, VPC Flow Logs, DNS Logs, EKS 감사 로그 등을 머신러닝/룰로 분석한다.
  - 결과는 Finding으로 축적되며 심각도/리소스/전형(ThreatPurpose)로 분류된다.

- AWS WAF
  - 매니지드 룰(예: CommonRuleSet, KnownBadInputs)로 기본 면역력을 확보하고, 사용자 정의 룰로 경로/메서드/IP/헤더 기반 제어.
  - 레이트 리밋 룰로 L7 과도한 요청을 자동 제어.
- AWS Shield Advanced
  - DDoS 탐지 시 자동 완화와 WAF 통합 룰 업데이트. 애플리케이션 레벨까지 커버.

- AWS Security Hub
  - 보안 결과를 한곳에 모아 표준(ASFF) 형태로 통합. GuardDuty/WAF/Inspector/Config 등의 Findings를 수집·상관분석.
  - EventBridge와 연동해 자동 대응 플레이북을 실행(격리, 키 회전, WAF 룰 강화 등).

### 예: GuardDuty → Security Hub → EventBridge → 자동 조치
1) GuardDuty가 의심스러운 API 호출을 탐지(Finding 생성)
2) Security Hub가 수집/통합, 심각도 기준으로 EventBridge 룰과 매칭
3) EventBridge가 람다/SSM Automation 실행
4) 조치 예시: WAF 차단 목록에 IP 추가, IAM 액세스 키 비활성화, 보안그룹 폐쇄

간단 이벤트 패턴(개념)
```json
{
  "source": ["aws.securityhub"],
  "detail-type": ["Security Hub Findings - Imported"],
  "detail": { "findings": { "Severity": { "Label": ["HIGH", "CRITICAL"] } } }
}
```

### 용어 정리
- 매니지드 룰: AWS/서드파티가 유지하는 WAF 룰 묶음. 기본 위협을 빠르게 커버.
- Finding: 탐지 결과 객체. 서비스별 포맷을 Security Hub가 ASFF로 표준화.
- DRT: AWS DDoS Response Team. Shield Advanced 고객의 심각 이벤트에 지원.


- 매니지드 룰: AWS/서드파티가 유지하는 WAF 룰 묶음. 기본 위협을 빠르게 커버.
- Finding: 탐지 결과 객체. 서비스별 포맷을 Security Hub가 ASFF로 표준화.
- DRT: AWS DDoS Response Team. Shield Advanced 고객의 심각 이벤트에 지원.







아래 네 가지를 하나의 흐름으로 잇는다: 관찰 → 탐지 → 차단 → 대응.

- 매니지드 룰: AWS/서드파티가 유지하는 WAF 룰 묶음. 기본 위협을 빠르게 커버.
- Finding: 탐지 결과 객체. 서비스별 포맷을 Security Hub가 ASFF로 표준화.
- DRT: AWS DDoS Response Team. Shield Advanced 고객의 심각 이벤트에 지원.


- 매니지드 룰: AWS/서드파티가 유지하는 WAF 룰 묶음. 기본 위협을 빠르게 커버.
- Finding: 탐지 결과 객체. 서비스별 포맷을 Security Hub가 ASFF로 표준화.
- DRT: AWS DDoS Response Team. Shield Advanced 고객의 심각 이벤트에 지원.







아래 네 가지를 하나의 흐름으로 잇는다: 관찰 → 탐지 → 차단 → 대응.





