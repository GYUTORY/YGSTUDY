---
title: AWS IAM Identity and Access Management
tags: [aws, security, iam]
updated: 2025-09-23
---

# AWS IAM (Identity and Access Management)

## 목차
- [IAM이란?](#iam이란)
- [핵심 개념](#핵심-개념)
- [정책과 권한 관리](#정책과-권한-관리)
- [보안 강화 방안](#보안-강화-방안)
- [실무 적용 가이드](#실무-적용-가이드)
- [모니터링과 감사](#모니터링과-감사)

---

## IAM이란?

### 정의와 목적
IAM(Identity and Access Management)은 AWS 계정 내에서 **누가(Who)**, **어떤 리소스에(What)**, **어떤 작업을(How)** 수행할 수 있는지를 제어하는 중앙집중식 보안 서비스입니다.

### 왜 IAM이 중요한가?

**보안 관점에서의 필요성:**
- **최소 권한 원칙**: 사용자에게 작업에 필요한 최소한의 권한만 부여
- **접근 제어**: 무단 접근을 방지하고 적절한 인증/인가 메커니즘 제공
- **감사 추적**: 모든 접근과 작업에 대한 로그 기록
- **규정 준수**: 다양한 보안 규정과 표준을 준수할 수 있는 기반 제공

**비즈니스 관점에서의 가치:**
- **운영 효율성**: 역할 기반 접근으로 관리 부담 감소
- **비용 최적화**: 불필요한 리소스 접근으로 인한 비용 증가 방지
- **확장성**: 조직이 성장해도 일관된 보안 정책 유지

---

## 핵심 개념

### 1. 사용자 (User)
AWS 계정에서 실제 작업을 수행하는 개인이나 애플리케이션을 나타냅니다.

**특징:**
- **영구적 자격 증명**: 장기간 사용되는 계정
- **다양한 접근 방식**: 콘솔 로그인, API 호출, CLI 사용
- **개별 관리**: 각 사용자별로 독립적인 권한 설정 가능

**사용자 유형:**
- **인간 사용자**: 개발자, 관리자, 운영자 등
- **애플리케이션**: 서드파티 앱이나 외부 시스템
- **서비스 계정**: 자동화된 작업을 위한 전용 계정

### 2. 그룹 (Group)
비슷한 역할이나 업무를 수행하는 사용자들을 논리적으로 묶은 집합입니다.

**장점:**
- **권한 관리 단순화**: 개별 사용자 대신 그룹 단위로 권한 부여
- **일관성 보장**: 동일한 역할의 사용자들이 같은 권한을 가짐
- **유지보수 효율성**: 그룹 정책 변경 시 모든 구성원에게 자동 적용

**실무 활용 예시:**
- 개발팀, 운영팀, 보안팀 등 조직 구조에 맞춘 그룹 구성
- 프로젝트별, 환경별(개발/스테이징/프로덕션) 그룹 분리

### 3. 역할 (Role)
특정 작업을 수행할 때 임시로 부여되는 권한의 집합입니다.

**핵심 특징:**
- **임시 자격 증명**: 일정 시간 후 자동으로 만료
- **신뢰 관계**: 역할을 사용할 수 있는 주체를 명시적으로 정의
- **서비스 간 통신**: AWS 서비스들이 서로 접근할 때 사용

**주요 사용 사례:**
- **EC2 인스턴스**: S3, DynamoDB 등 다른 서비스에 접근
- **Lambda 함수**: 실행에 필요한 AWS 서비스 접근
- **Cross-Account 접근**: 다른 AWS 계정의 리소스에 접근
- **Federated Access**: 외부 ID 공급자(AD, SAML)를 통한 접근

### 4. 정책 (Policy)
권한을 정의하는 JSON 형식의 문서입니다.

**정책 구조:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-bucket/*"
    }
  ]
}
```

**정책 유형:**
- **관리형 정책**: AWS에서 제공하거나 사용자가 생성한 재사용 가능한 정책
- **인라인 정책**: 특정 사용자, 그룹, 역할에 직접 연결되는 정책
- **리소스 기반 정책**: S3 버킷, SNS 토픽 등 리소스에 직접 연결되는 정책

---

## 정책과 권한 관리

### 정책 작성 원칙

**1. 최소 권한 원칙 (Principle of Least Privilege)**
- 사용자에게 작업 수행에 필요한 최소한의 권한만 부여
- 불필요한 권한은 보안 위험을 증가시킴

**2. 명시적 거부 (Explicit Deny)**
- Deny 정책은 Allow 정책보다 우선순위가 높음
- 특정 조건에서의 접근을 명시적으로 차단

**3. 조건부 접근 (Conditional Access)**
- IP 주소, 시간, MFA 사용 여부 등 조건에 따른 접근 제어
- 상황에 맞는 세밀한 권한 관리 가능

### 정책 예시와 해석

**S3 읽기 전용 정책:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::company-data",
        "arn:aws:s3:::company-data/*"
      ]
    }
  ]
}
```

**조건부 접근 정책 (IP 제한):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::secure-bucket/*",
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": "192.168.1.0/24"
        }
      }
    }
  ]
}
```

### 권한 상속과 조합

**권한 계산 방식:**
1. **사용자 직접 권한**: 사용자에게 직접 연결된 정책
2. **그룹 권한**: 사용자가 속한 그룹의 정책들
3. **역할 권한**: 사용자가 수행하는 역할의 정책들
4. **리소스 기반 권한**: 리소스에 연결된 정책들

**권한 우선순위:**
- Explicit Deny > Explicit Allow > Default Deny
- 여러 Allow 정책이 있을 경우 모두 허용
- 하나라도 Deny가 있으면 접근 거부

---

## 보안 강화 방안

### 다중 인증 (MFA)

**MFA의 중요성:**
- 패스워드만으로는 보안이 취약할 수 있음
- 추가 인증 요소로 보안 강화
- AWS 콘솔 접근 시 필수 권장

**MFA 구현 방법:**
- **하드웨어 토큰**: 물리적 보안 장치
- **소프트웨어 토큰**: Google Authenticator, Authy 등
- **SMS**: 휴대폰 번호로 인증 코드 전송
- **U2F**: USB 형태의 보안 키

### 액세스 키 관리

**액세스 키 보안 원칙:**
- **정기적 로테이션**: 90일마다 키 교체 권장
- **최소 권한**: 필요한 작업에만 사용
- **안전한 저장**: 환경 변수나 AWS Secrets Manager 활용
- **사용 모니터링**: 비정상적인 사용 패턴 감지

**키 관리 모범 사례:**
- 개발/운영 환경별 키 분리
- 사용하지 않는 키 즉시 삭제
- 키 사용 이력 정기적 검토

### 권한 검토와 정리

**정기적 권한 감사:**
- **분기별 검토**: 사용자별 권한 현황 점검
- **미사용 권한 제거**: 90일 이상 사용하지 않은 권한 정리
- **역할 변경 대응**: 사용자 역할 변경 시 권한 조정

**자동화된 권한 관리:**
- AWS Access Analyzer 활용
- CloudTrail과 CloudWatch를 통한 모니터링
- 정책 시뮬레이터로 권한 테스트

---

## 실무 적용 가이드

### 조직 구조에 맞는 IAM 설계

**계층적 구조 설계:**
```
/company/
  /departments/
    /development/
      /frontend-team/
      /backend-team/
    /operations/
      /devops-team/
      /security-team/
```

**역할 기반 접근 제어 (RBAC):**
- 조직의 실제 역할과 AWS 권한을 매핑
- 팀별, 프로젝트별 권한 분리
- 환경별(개발/스테이징/프로덕션) 접근 제어

### Cross-Account 접근 관리

**계정 간 신뢰 관계 설정:**
- 개발/운영/보안 계정 분리
- 중앙 집중식 로그 수집 계정
- 공유 서비스 계정 운영

**역할 체인 (Role Chaining):**
- 여러 계정을 거쳐 최종 리소스에 접근
- 각 단계별 권한 검증
- 감사 추적성 확보

### 서비스 간 통신 보안

**EC2 인스턴스 역할:**
- 인스턴스 프로파일을 통한 자격 증명
- 하드코딩된 키 사용 금지
- 최소 권한 원칙 적용

**Lambda 함수 권한:**
- 실행 역할(Execution Role) 설정
- 필요한 서비스만 접근 허용
- 환경별 권한 분리

---

## 모니터링과 감사

### CloudTrail을 통한 감사

**로그 수집 항목:**
- 모든 IAM API 호출
- 사용자 로그인/로그아웃
- 권한 변경 이력
- 정책 수정 내역

**로그 분석 방법:**
- 실시간 알림 설정
- 정기적 보안 리포트 생성
- 비정상 패턴 감지

### CloudWatch를 통한 모니터링

**주요 메트릭:**
- 실패한 로그인 시도
- 권한 거부 횟수
- API 호출 빈도
- 사용자별 활동 패턴

**알림 설정:**
- 다중 실패 로그인 시도
- 관리자 권한 사용
- 새로운 사용자 생성
- 정책 변경

### 보안 사고 대응

**사고 대응 절차:**
1. **즉시 대응**: 의심스러운 활동 감지 시 즉시 계정 비활성화
2. **조사**: CloudTrail 로그를 통한 상세 분석
3. **복구**: 영향받은 리소스 식별 및 복구
4. **예방**: 재발 방지를 위한 정책 강화

**자동화된 대응:**
- AWS Config Rules 활용
- Lambda 함수를 통한 자동 대응
- SNS를 통한 즉시 알림

---

## 참고 자료

- [AWS IAM 공식 문서](https://docs.aws.amazon.com/ko_kr/IAM/latest/UserGuide/introduction.html)
- [IAM 정책 시뮬레이터](https://policysim.aws.amazon.com/)
- [AWS 정책 생성기](https://awspolicygen.s3.amazonaws.com/policygen.html)
- [IAM Best Practices](https://docs.aws.amazon.com/ko_kr/IAM/latest/UserGuide/best-practices.html)
- [AWS Well-Architected Framework - Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [AWS Security Best Practices](https://aws.amazon.com/architecture/security-identity-compliance/)
