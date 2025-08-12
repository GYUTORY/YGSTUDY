최종 업데이트 2025-08-08, 버전 v1.0

> 이전 명칭 안내: 과거 문서명 CloudTail → CloudTrail로 정정했습니다.
---
title: AWS CloudTrail
tags: [aws, monitoring-and-management, cloudtrail]
updated: 2025-08-10
---

# AWS CloudTrail 개념 및 설명

## AWS CloudTrail이란?
**AWS CloudTrail**은 AWS 계정 내에서 발생하는 **모든 API 호출을 추적**하고 **로그를 저장하는 서비스**입니다.  
이를 통해 보안 감사, 문제 해결, 규정 준수를 위한 기록을 남길 수 있습니다.

> CloudTrail은 AWS에서 발생하는 모든 API 호출을 기록하여 "누가, 언제, 어떤 작업을 했는지" 추적할 수 있도록 해줍니다.

---

## CloudTrail의 주요 기능
### 1) AWS API 호출 로깅
- AWS 계정에서 수행된 모든 API 호출을 자동으로 기록합니다.
- 콘솔, SDK, CLI를 통한 요청 모두 추적됩니다.

### 2) 로그 저장 및 분석
- 로그 데이터는 기본적으로 S3 버킷에 저장되며, 이를 활용해 분석이 가능합니다.
- CloudWatch Logs 및 AWS Athena를 사용해 데이터를 쿼리할 수도 있습니다.

### 3) 실시간 보안 모니터링
- CloudTrail Insights를 사용하면 비정상적인 API 활동을 감지하고 알림을 받을 수 있습니다.

### 4) 다중 계정 및 리전 관리
- AWS Organizations를 활용하면 여러 개의 AWS 계정에 대한 CloudTrail을 중앙에서 관리할 수 있습니다.

---

## CloudTrail 이벤트 유형

CloudTrail 이벤트는 크게 세 가지로 나뉜다.

#### 1. 관리 이벤트 (Management Events)
#### 2. 데이터 이벤트 (Data Events)
#### 3. 인사이트 이벤트 (CloudTrail Insights)

---

## CloudTrail 로그 저장 방식
- S3 버킷 기본 저장, CloudWatch Logs 전송 가능, Athena 분석 지원

---

## CloudTrail 설정 방법 (CLI 예시)
```bash
aws cloudtrail create-trail \
  --name MyCloudTrail \
  --s3-bucket-name my-cloudtrail-bucket \
  --is-multi-region-trail
```

---

## 배경
- AWS CloudTrail — AWS Docs, `https://docs.aws.amazon.com/cloudtrail/`
- CloudTrail Pricing — AWS, `https://aws.amazon.com/cloudtrail/pricing/`

---

- [CloudWatch](../Monitoring & Management/CloudWatch.md) — 로그/메트릭과 연계
- [IAM](../Security/IAM.md) — 접근 제어와 감사 트레일 연결
- [SSM_Deploy](../Monitoring & Management/SSM_Deploy.md) — 운영 자동화와 감사 연계










