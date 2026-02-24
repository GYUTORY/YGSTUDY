---
title: AWS CloudTrail
tags: [aws, monitoring-and-management, cloudtrail, auditing, compliance]
updated: 2025-12-07
---

# AWS CloudTrail

## 개요

CloudTrail은 AWS 계정의 모든 API 호출을 자동으로 기록하는 감사 서비스다. 누가 언제 어떤 작업을 했는지 추적할 수 있다.

**사용하는 경우:**
- "누가 EC2 인스턴스를 삭제했나?"
- "어떤 사용자가 S3 버킷 권한을 변경했나?"
- "비정상적인 API 호출이 있었나?"
- 규정 준수(SOX, PCI-DSS, HIPAA 등) 요구사항 충족

**기록되는 정보:**
- API 호출자 (사용자, 역할, 서비스)
- 호출 시간
- 호출한 API 작업
- 요청한 리소스
- 성공/실패 여부
- IP 주소

---

## 핵심 기능

### API 호출 로깅

CloudTrail은 AWS 계정의 모든 API 호출을 자동으로 기록한다.

**기록되는 호출:**
- AWS Management Console 작업
- AWS CLI 명령어
- SDK를 통한 API 호출
- 서드파티 도구를 통한 접근

**로그 레코드 내용:**
- 사용자/서비스 신원
- 요청 시간
- API 작업
- 요청한 리소스
- 성공/실패 여부
- IP 주소
- User-Agent

### 이벤트 유형

CloudTrail은 세 가지 이벤트 유형을 추적한다.

**1. 관리 이벤트 (Management Events)**
- 리소스 생성, 수정, 삭제 작업
- IAM 정책 변경, 보안 그룹 수정, VPC 설정 변경
- 기본적으로 활성화됨
- 가장 중요한 감사 정보 제공

**2. 데이터 이벤트 (Data Events)**
- S3 객체 읽기/쓰기 작업
- Lambda 함수 실행
- 기본적으로 비활성화됨
- 활성화 시 추가 비용 발생

**주의사항:**
데이터 이벤트는 로그 볼륨이 크다. S3 버킷 전체를 로깅하면 비용이 급증한다. 필요한 버킷이나 경로만 선택적으로 활성화해야 한다.

**3. 인사이트 이벤트 (CloudTrail Insights)**
- 비정상적인 API 활동 패턴 자동 감지
- 예상치 못한 서비스 활동, 비정상적인 에러율, 리소스 생성 탐지
- 머신러닝 기반으로 작동

**실무 팁:**
인사이트는 추가 비용이 발생한다. 보안 요구사항이 높은 환경에서만 사용한다.

### 다중 리전 및 계정 지원

**다중 리전 추적:**
- 단일 CloudTrail로 모든 AWS 리전의 활동 추적
- 글로벌 서비스(IAM, Route 53)와 리전별 서비스 통합 관리
- 중앙화된 감사 로그로 운영 효율성 향상

**AWS Organizations 통합:**
- 여러 AWS 계정을 하나의 조직으로 관리
- 조직 전체에 대한 통합 감사 추적
- 계정 간 리소스 공유 시에도 추적 가능

**실무 팁:**
Organizations를 사용하면 조직 단위 CloudTrail을 생성해 모든 계정의 로그를 중앙에서 관리할 수 있다.

---

## 로그 구조

### 로그 파일 형식

CloudTrail 로그는 JSON 형식으로 저장된다.

```json
{
  "Records": [
    {
      "eventTime": "2025-09-23T10:30:00Z",
      "eventName": "CreateBucket",
      "eventSource": "s3.amazonaws.com",
      "userIdentity": {
        "type": "IAMUser",
        "principalId": "AIDACKCEVSQ6C2EXAMPLE",
        "arn": "arn:aws:iam::123456789012:user/username",
        "userName": "username"
      },
      "sourceIPAddress": "203.0.113.12",
      "userAgent": "aws-cli/1.16.70",
      "requestParameters": {
        "bucketName": "my-new-bucket"
      },
      "responseElements": null,
      "requestID": "C3C14B5B4B5B4B5B",
      "eventID": "12345678-1234-1234-1234-123456789012",
      "eventType": "AwsApiCall",
      "awsRegion": "us-east-1"
    }
  ]
}
```

### 저장 옵션

**1. S3 버킷 저장 (기본)**
- 비용 효율적
- 장기 보관 가능
- 버전 관리 지원
- 암호화 지원
- 생명주기 정책 적용 가능

**주의사항:**
별도의 S3 버킷이 필요하다. CloudTrail 전용 버킷을 만들고 버전 관리를 활성화해야 한다.

**2. CloudWatch Logs 전송**
- 실시간 모니터링
- 알림 설정 가능
- 다른 AWS 서비스와 통합

**주의사항:**
추가 비용이 발생한다. 대용량 로그는 비용이 급증할 수 있다.

**3. AWS Athena 연동**
- SQL 쿼리로 로그 분석
- 복잡한 검색 및 분석 가능
- 서버리스 쿼리 엔진

**사용 예시:**
```sql
-- 특정 사용자의 API 호출 조회
SELECT eventTime, eventName, sourceIPAddress
FROM cloudtrail_logs
WHERE userIdentity.userName = 'admin'
AND eventTime >= '2025-12-01'
ORDER BY eventTime DESC;
```

**실무 팁:**
S3에 저장하고 필요할 때만 Athena로 분석하는 게 비용 효율적이다.

---

## 보안

### 데이터 보호

**암호화:**
- 전송 중: HTTPS로 전송
- 저장 시: S3 서버 측 암호화(SSE) 지원
- 고객 관리 키: AWS KMS를 통한 키 관리 가능

**접근 제어:**
- 최소 권한 원칙: CloudTrail 로그 접근 최소화
- IAM 정책: 세밀한 권한 제어
- MFA 요구: 중요한 로그 접근 시 다중 인증

**실무 팁:**
CloudTrail 로그는 별도 계정에 저장하는 게 좋다. 로그를 삭제하거나 수정하는 것을 방지할 수 있다.

### 규정 준수

CloudTrail은 다음 규정 준수 요구사항을 충족한다:
- SOX: 재무 보고의 정확성과 투명성
- PCI DSS: 신용카드 데이터 보안 표준
- HIPAA: 의료 정보 보호 규정
- GDPR: 유럽 개인정보보호 규정
- ISO 27001: 정보보안 관리 시스템

---

## 운영 고려사항

### 이벤트 선택

모든 이벤트를 로깅하면 비용이 급증한다. 비즈니스 요구사항에 맞게 선택적으로 활성화해야 한다.

**필수:**
- 관리 이벤트는 반드시 활성화

**선택적:**
- 데이터 이벤트는 필요한 버킷이나 경로만 활성화
- 인사이트는 보안 요구사항이 높을 때만 사용

**비용 고려:**
데이터 이벤트는 로그 볼륨이 크다. S3 버킷 전체를 로깅하면 비용이 급증한다.

### 로그 무결성 보장

**별도 계정 사용:**
CloudTrail 로그를 별도의 AWS 계정에 저장한다. 로그를 삭제하거나 수정하는 것을 방지할 수 있다.

**버전 관리:**
S3 버킷의 버전 관리를 활성화한다. 실수로 삭제해도 복구할 수 있다.

**MFA 삭제:**
중요한 로그 삭제 시 MFA를 요구한다.

**정기 검증:**
로그 파일의 무결성을 정기적으로 검증한다.

### 모니터링 및 알림

**CloudWatch 알람:**
비정상적인 API 활동을 감지한다.

**예시:**
```javascript
// 루트 계정 로그인 감지
{
  "eventName": "ConsoleLogin",
  "userIdentity.type": "Root"
}

// IAM 정책 변경 감지
{
  "eventName": ["PutUserPolicy", "PutRolePolicy", "PutGroupPolicy"]
}

// 보안 그룹 변경 감지
{
  "eventName": ["AuthorizeSecurityGroupIngress", "RevokeSecurityGroupIngress"]
}
```

**EventBridge:**
특정 이벤트 발생 시 자동 대응한다.

**Lambda 함수:**
로그를 분석하고 자동 대응 워크플로우를 실행한다.

### 비용 최적화

**로그 압축:**
S3에서 로그 파일 압축을 활성화한다.

**생명주기 정책:**
오래된 로그를 자동으로 Glacier로 아카이빙한다.

**선택적 로깅:**
불필요한 이벤트 로깅을 비활성화한다.

---

## 실제 활용 시나리오

### 보안 사고 대응

보안 침해가 의심될 때 CloudTrail 로그로 다음을 추적한다.

**1. 비정상적인 로그인 시도:**
```sql
-- 실패한 인증 시도 조회
SELECT eventTime, sourceIPAddress, userIdentity.userName, errorMessage
FROM cloudtrail_logs
WHERE eventName = 'ConsoleLogin'
AND responseElements.ConsoleLogin = 'Failure'
ORDER BY eventTime DESC;
```

**2. 권한 에스컬레이션:**
```sql
-- IAM 정책 변경 이력 추적
SELECT eventTime, userIdentity.userName, eventName, requestParameters
FROM cloudtrail_logs
WHERE eventName IN ('PutUserPolicy', 'PutRolePolicy', 'AttachUserPolicy')
ORDER BY eventTime DESC;
```

**3. 데이터 유출:**
```sql
-- 대용량 데이터 다운로드 감지
SELECT eventTime, userIdentity.userName, sourceIPAddress, requestParameters
FROM cloudtrail_logs
WHERE eventName = 'GetObject'
AND responseElements.contentLength > 1000000000  -- 1GB 이상
ORDER BY eventTime DESC;
```

**4. 리소스 남용:**
```sql
-- 예상치 못한 리소스 생성
SELECT eventTime, userIdentity.userName, eventName, awsRegion
FROM cloudtrail_logs
WHERE eventName LIKE 'Create%'
AND eventTime >= '2025-12-01'
ORDER BY eventTime DESC;
```

### 운영 문제 해결

**서비스 장애:**
API 호출 실패 패턴을 분석한다.

**성능 이슈:**
느린 API 응답 시간을 추적한다.

**비용 급증:**
예상치 못한 리소스 사용 패턴을 분석한다.

### 규정 준수 감사

**접근 권한 검토:**
정기적으로 사용자 권한을 감사한다.

**데이터 처리 추적:**
개인정보 처리 활동을 기록한다.

**변경 관리:**
인프라 변경 이력을 문서화한다.

---

## 다른 AWS 서비스와의 통합

### CloudWatch 통합

로그를 CloudWatch Logs로 전송해 실시간 모니터링한다.

**사용 예시:**
```javascript
// CloudWatch Logs Insights 쿼리
fields @timestamp, eventName, userIdentity.userName, sourceIPAddress
| filter eventName = "ConsoleLogin"
| stats count() by userIdentity.userName
```

**메트릭 필터:**
특정 이벤트를 메트릭으로 변환해 알람을 설정할 수 있다.

### AWS Config와의 차이

**CloudTrail:**
- "누가 무엇을 했는가" (활동 추적)
- API 호출 이력

**AWS Config:**
- "리소스의 현재 상태는 무엇인가" (상태 추적)
- 리소스 설정 변경 이력

**실무 팁:**
두 서비스를 함께 사용하면 완전한 감사 추적이 가능하다.

### Security Hub 통합

보안 이벤트를 중앙에서 관리한다. 자동화된 보안 위협 탐지 및 대응이 가능하다.

## 참고

- AWS CloudTrail 사용자 가이드: https://docs.aws.amazon.com/cloudtrail/
- AWS CloudTrail 가격: https://aws.amazon.com/cloudtrail/pricing/
- AWS Well-Architected Framework: https://docs.aws.amazon.com/wellarchitected/










