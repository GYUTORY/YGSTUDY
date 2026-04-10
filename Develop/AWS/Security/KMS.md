---
title: AWS KMS (Key Management Service)
tags: [aws, security, kms, encryption]
updated: 2026-04-10
---

# AWS KMS (Key Management Service)

## 개요

AWS KMS는 암호화 키를 생성, 저장, 제어하는 완전 관리형 서비스다.  
데이터 암호화의 복잡성을 AWS가 대신 처리해주며, 다양한 AWS 서비스와 연동된다.

### 주요 기능
- 암호화 키(CMK) 생성 및 관리
- 데이터 암호화/복호화 기능 제공
- AWS 서비스(S3, EBS 등)와 연동
- CloudTrail, CloudWatch 기반의 로깅과 감사

---

## 암호화 개념 요약

| 용어 | 설명 |
|------|------|
| 평문(Plaintext) | 암호화 전 데이터 |
| 암호문(Ciphertext) | 암호화된 데이터 |
| 키(Key) | 암호화/복호화에 사용되는 값 |
| KMS Key (구 CMK) | KMS에서 관리하는 마스터 키 |
| Data Key | 실제 데이터 암호화에 사용되는 키 |

---

## KMS 키 계층 구조

KMS의 키는 3단계 계층으로 구성된다. 상위 키가 하위 키를 암호화하는 구조로, 최상위 키는 AWS가 관리하는 HSM 내부에서만 존재한다.

```
┌─────────────────────────────────────────────────┐
│              AWS KMS HSM (하드웨어)                │
│                                                   │
│  ┌───────────────────────────────────────┐        │
│  │  HSM Backing Key (AWS 관리)            │        │
│  │  - HSM 내부에서만 존재                  │        │
│  │  - 사용자 접근 불가                     │        │
│  │  - KMS Key를 암호화                    │        │
│  └──────────────┬────────────────────────┘        │
│                 │ 암호화                            │
│  ┌──────────────▼────────────────────────┐        │
│  │  KMS Key (Customer Master Key)         │        │
│  │  - 논리적 키 리소스 (KeyId, ARN)        │        │
│  │  - 키 정책, 로테이션 설정 포함           │        │
│  │  - 직접 데이터 암호화는 4KB까지만 가능    │        │
│  └──────────────┬────────────────────────┘        │
│                 │                                   │
└─────────────────┼───────────────────────────────────┘
                  │ GenerateDataKey API
                  │
   ┌──────────────▼────────────────────────┐
   │  Data Key (데이터 키)                   │
   │  - 실제 데이터 암호화에 사용             │
   │  - 평문 키는 사용 후 즉시 폐기           │
   │  - 암호화된 키만 데이터와 함께 저장       │
   └────────────────────────────────────────┘
```

### KMS Key 종류

| 키 종류 | 설명 | 관리 주체 | 키 정책 수정 |
|---------|------|----------|-------------|
| AWS 소유 키 | AWS 서비스 내부용, 사용자에게 노출 안 됨 | AWS | 불가 |
| AWS 관리형 키 | `aws/s3`, `aws/ebs` 같은 키. 서비스가 자동 생성 | AWS | 불가 |
| 고객 관리형 키 | 사용자가 직접 생성. 키 정책, 로테이션 직접 제어 | 사용자 | 가능 |

실무에서는 감사 요건이 있거나 cross-account 접근이 필요한 경우 고객 관리형 키를 쓴다. 그 외에는 AWS 관리형 키로 충분한 경우가 많다.

---

## Envelope Encryption

KMS의 핵심 패턴이다. 4KB 이상 데이터를 암호화할 때 반드시 이 방식을 써야 한다.

### 암호화 흐름

```
┌──────────────┐         ┌──────────────┐
│  애플리케이션  │         │   AWS KMS     │
└──────┬───────┘         └──────┬───────┘
       │                        │
       │  1. GenerateDataKey    │
       │───────────────────────>│
       │                        │  KMS Key로
       │                        │  Data Key 생성
       │  2. 평문 키 + 암호화 키  │
       │<───────────────────────│
       │                        │
       │  3. 평문 키로 데이터 암호화
       │  (로컬에서 AES-256)
       │
       │  4. 평문 키 메모리에서 삭제
       │
       │  5. 암호화된 데이터 + 암호화된 키 함께 저장
       │  (S3, DB 등)
       ▼
```

### 복호화 흐름

```
┌──────────────┐         ┌──────────────┐
│  애플리케이션  │         │   AWS KMS     │
└──────┬───────┘         └──────┬───────┘
       │                        │
       │  1. 저장소에서 암호화된 데이터 + 암호화된 키 조회
       │
       │  2. Decrypt(암호화된 키) │
       │───────────────────────>│
       │                        │  KMS Key로
       │                        │  Data Key 복호화
       │  3. 평문 키 반환        │
       │<───────────────────────│
       │                        │
       │  4. 평문 키로 데이터 복호화
       │  (로컬에서 AES-256)
       │
       │  5. 평문 키 메모리에서 삭제
       ▼
```

핵심은 **평문 키가 KMS 외부에서 존재하는 시간을 최소화하는 것**이다. 암호화가 끝나면 평문 키를 즉시 폐기하고, 암호화된 키만 보관한다. 복호화가 필요할 때마다 KMS에 복호화를 요청한다.

이 구조의 장점은 KMS API 호출을 줄일 수 있다는 것이다. Data Key 하나로 여러 데이터를 암호화한 뒤 키를 폐기하면, GenerateDataKey 호출은 1번이면 된다.

---

## 멀티리전 키 (Multi-Region Key)

KMS 키는 기본적으로 리전에 종속된다. 하지만 멀티리전 키를 사용하면 여러 리전에서 동일한 키 material로 암호화/복호화할 수 있다.

```
┌─────────────────────────────────────────────────────────┐
│                     멀티리전 키 구조                       │
│                                                          │
│  ap-northeast-2 (Primary)      us-east-1 (Replica)      │
│  ┌─────────────────────┐      ┌─────────────────────┐   │
│  │  mrk-1234abcd        │      │  mrk-1234abcd        │  │
│  │  (Primary Key)       │─────>│  (Replica Key)       │  │
│  │                      │ 복제  │                      │  │
│  │  키 정책: 독립 관리    │      │  키 정책: 독립 관리    │  │
│  └─────────────────────┘      └─────────────────────┘   │
│                                                          │
│  - 동일한 Key ID (mrk- 접두사)                             │
│  - 동일한 key material                                    │
│  - 키 정책은 리전별로 독립                                  │
│  - Primary에서만 key material 관리 (로테이션 등)             │
└─────────────────────────────────────────────────────────┘
```

### 사용하는 경우

- **DR(재해복구)**: 한 리전이 장애 나면 다른 리전에서 데이터 복호화 가능
- **글로벌 서비스**: DynamoDB Global Table 같은 멀티리전 서비스에서 같은 키로 암복호화
- **리전 간 데이터 이동**: S3 Cross-Region Replication에서 암호화된 객체를 다른 리전에서 읽어야 할 때

### 생성 및 복제

```bash
# Primary 키 생성 (서울 리전)
PRIMARY_KEY_ID=$(aws kms create-key \
  --region ap-northeast-2 \
  --description "Multi-region primary key" \
  --multi-region \
  --query 'KeyMetadata.KeyId' --output text)

# Replica 키 생성 (버지니아 리전)
aws kms replicate-key \
  --region us-east-1 \
  --key-id $PRIMARY_KEY_ID \
  --replica-region us-east-1 \
  --description "Multi-region replica key"
```

### 주의사항

- 멀티리전 키는 일반 키보다 비용이 동일하지만, 리전마다 $1/월 과금된다
- Replica 키는 독자적으로 로테이션할 수 없다. Primary에서 로테이션하면 모든 Replica에 반영된다
- 키 정책은 리전마다 따로 설정해야 한다. Primary 키 정책을 바꿔도 Replica에는 자동 반영 안 된다
- 멀티리전 키를 단일 리전 키로 변경하는 건 불가능하다. 처음부터 `--multi-region` 플래그를 넣어야 한다

---

## 키 정책 (Key Policy)

키 정책은 KMS 키에 직접 붙는 리소스 기반 정책이다. IAM 정책과 함께 동작하지만, 키 정책이 없으면 IAM 정책만으로는 키에 접근할 수 없다.

### 기본 키 정책 구조

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Enable IAM policies",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::111122223333:root" },
      "Action": "kms:*",
      "Resource": "*"
    }
  ]
}
```

이 정책이 있어야 IAM 정책으로 키 접근 권한을 위임할 수 있다. 이 Statement를 빼면 키 정책에 명시된 Principal만 키를 쓸 수 있고, IAM 정책은 무시된다.

### 조건 키 (Condition Keys)

KMS는 여러 조건 키를 제공한다. 실무에서 자주 쓰는 것들을 정리한다.

#### kms:ViaService

특정 AWS 서비스를 통해서만 키를 사용할 수 있게 제한한다. 사용자가 직접 KMS API를 호출하는 건 차단된다.

```json
{
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::111122223333:role/AppRole" },
  "Action": [
    "kms:Decrypt",
    "kms:GenerateDataKey"
  ],
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "kms:ViaService": "s3.ap-northeast-2.amazonaws.com"
    }
  }
}
```

이렇게 하면 S3를 통한 암복호화만 허용된다. 누군가 aws kms decrypt CLI로 직접 복호화를 시도하면 거부된다.

#### kms:CallerAccount

키를 사용할 수 있는 AWS 계정을 제한한다. cross-account 시나리오에서 특정 계정만 허용할 때 쓴다.

```json
{
  "Effect": "Allow",
  "Principal": { "AWS": "*" },
  "Action": [
    "kms:Decrypt"
  ],
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "kms:CallerAccount": ["111122223333", "444455556666"]
    }
  }
}
```

#### kms:EncryptionContext

Encryption Context를 강제한다. 특정 키-값 쌍이 포함된 요청만 허용할 수 있다.

```json
{
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::111122223333:role/AppRole" },
  "Action": "kms:Decrypt",
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "kms:EncryptionContext:department": "finance"
    }
  }
}
```

Encryption Context는 암호화 시 전달한 key-value 쌍으로, 복호화 시에도 동일한 값을 전달해야 한다. 추가 인증 데이터(AAD)로 동작하며, CloudTrail 로그에도 남아서 감사에 유용하다.

#### 자주 쓰는 조건 키 정리

| 조건 키 | 용도 |
|--------|------|
| `kms:ViaService` | 특정 AWS 서비스를 경유한 요청만 허용 |
| `kms:CallerAccount` | 특정 계정의 요청만 허용 |
| `kms:EncryptionContext:키` | 특정 Encryption Context 값 강제 |
| `kms:GrantIsForAWSResource` | AWS 서비스가 생성한 Grant만 허용 |
| `kms:KeyOrigin` | 키 material 출처 제한 (AWS_KMS, EXTERNAL 등) |
| `kms:KeySpec` | 특정 키 스펙만 허용 (SYMMETRIC_DEFAULT 등) |
| `kms:RequestAlias` | 특정 alias를 통한 요청만 허용 |

---

## Cross-Account 키 공유

다른 AWS 계정에서 내 KMS 키를 사용해야 하는 경우가 있다. 예를 들어, 중앙 보안 계정에서 키를 관리하고 워크로드 계정에서 사용하는 구조다.

### 설정 과정

```
┌──────────────────────┐         ┌──────────────────────┐
│  계정 A (키 소유자)    │         │  계정 B (키 사용자)    │
│  111122223333         │         │  444455556666         │
│                       │         │                       │
│  1. 키 정책에          │         │  2. IAM 정책에         │
│     계정 B 추가        │         │     KMS 권한 추가      │
│                       │         │                       │
│  KMS Key              │◄────────│  EC2 / Lambda 등      │
│  (키 정책 수정)        │ 사용     │  (IAM Role에 정책)     │
└──────────────────────┘         └──────────────────────┘
```

**양쪽 모두 설정해야 동작한다.** 키 정책만 수정하거나, IAM 정책만 추가하면 AccessDeniedException이 발생한다.

#### Step 1: 키 소유자 계정(A)의 키 정책

```json
{
  "Sid": "Allow account B to use this key",
  "Effect": "Allow",
  "Principal": {
    "AWS": "arn:aws:iam::444455556666:root"
  },
  "Action": [
    "kms:Decrypt",
    "kms:DescribeKey",
    "kms:GenerateDataKey"
  ],
  "Resource": "*"
}
```

root principal을 지정하면 계정 B의 IAM에서 세부 권한을 제어할 수 있다. 특정 Role만 허용하고 싶으면 Principal을 해당 Role ARN으로 바꾼다.

#### Step 2: 키 사용자 계정(B)의 IAM 정책

```json
{
  "Effect": "Allow",
  "Action": [
    "kms:Decrypt",
    "kms:DescribeKey",
    "kms:GenerateDataKey"
  ],
  "Resource": "arn:aws:kms:ap-northeast-2:111122223333:key/키ID"
}
```

Resource에 계정 A의 KMS Key ARN을 명시한다. `*`로 하면 안 된다.

#### CLI로 키 정책 업데이트

```bash
# 현재 키 정책 가져오기
aws kms get-key-policy \
  --key-id alias/shared-key \
  --policy-name default \
  --query Policy --output text > /tmp/key-policy.json

# 정책 수정 후 적용
aws kms put-key-policy \
  --key-id alias/shared-key \
  --policy-name default \
  --policy file:///tmp/key-policy.json
```

### Cross-Account에서 자주 발생하는 실수

- S3 버킷의 KMS 키를 다른 계정에서 접근할 때, S3 버킷 정책 + KMS 키 정책 + IAM 정책 세 가지를 모두 확인해야 한다
- AWS 관리형 키(`aws/s3` 등)는 키 정책 수정이 불가능해서 cross-account 공유가 안 된다. 고객 관리형 키를 써야 한다
- Grant를 사용하면 키 정책 수정 없이 임시로 cross-account 접근을 허용할 수 있다

---

## AccessDeniedException 트러블슈팅

KMS에서 가장 많이 만나는 에러다. 원인이 다양해서 하나씩 확인해야 한다.

### 에러 메시지 예시

```
An error occurred (AccessDeniedException) when calling the Decrypt operation:
User: arn:aws:iam::111122223333:role/MyRole is not authorized to perform:
kms:Decrypt on resource: arn:aws:kms:ap-northeast-2:111122223333:key/abcd-1234
```

### 확인 순서

**1단계: 키 정책 확인**

```bash
aws kms get-key-policy \
  --key-id arn:aws:kms:ap-northeast-2:111122223333:key/abcd-1234 \
  --policy-name default \
  --query Policy --output text | python3 -m json.tool
```

키 정책에 "Enable IAM policies" Statement가 있는지 확인한다. 이게 없으면 IAM 정책이 아무리 맞아도 접근이 안 된다.

**2단계: IAM 정책 확인**

```bash
# Role에 붙은 정책 확인
aws iam list-attached-role-policies --role-name MyRole
aws iam list-role-policies --role-name MyRole

# 인라인 정책 내용 확인
aws iam get-role-policy --role-name MyRole --policy-name PolicyName
```

`kms:Decrypt` 등 필요한 Action이 허용되어 있는지 확인한다.

**3단계: SCP, Permission Boundary 확인**

Organizations의 SCP(Service Control Policy)나 Permission Boundary가 KMS 접근을 차단하는 경우가 있다. IAM 정책과 키 정책이 정상인데도 접근이 안 되면 이쪽을 의심한다.

**4단계: VPC Endpoint 정책 확인**

VPC Endpoint를 사용하는 환경이면 Endpoint 정책도 확인한다.

```bash
aws ec2 describe-vpc-endpoints \
  --filters "Name=service-name,Values=com.amazonaws.ap-northeast-2.kms" \
  --query 'VpcEndpoints[].PolicyDocument'
```

Endpoint 정책에서 특정 키나 Action을 제한하고 있을 수 있다.

**5단계: kms:ViaService 조건 확인**

키 정책에 `kms:ViaService` 조건이 있으면, 해당 서비스를 경유하지 않는 직접 호출은 거부된다. CLI로 직접 `aws kms decrypt`를 호출하면 실패하는데 S3를 통한 복호화는 성공하는 경우, 이 조건 때문이다.

**6단계: Encryption Context 불일치**

암호화 시 Encryption Context를 사용했으면 복호화 시에도 동일한 값을 전달해야 한다. Context가 빠져 있거나 값이 다르면 AccessDeniedException이 아니라 InvalidCiphertextException이 발생하는 경우도 있다.

### 패턴별 정리

| 증상 | 원인 | 해결 |
|------|------|------|
| 같은 계정인데 Decrypt 실패 | 키 정책에 IAM 위임 Statement 없음 | 키 정책에 `kms:*`를 root에 Allow 추가 |
| cross-account에서 실패 | 키 정책 또는 IAM 정책 한쪽만 설정 | 양쪽 모두 설정 |
| CLI 직접 호출만 실패 | `kms:ViaService` 조건 | 조건 제거하거나 해당 서비스 경유 |
| 특정 서비스에서만 실패 | 키 정책의 Action에 해당 Action 누락 | `kms:CreateGrant` 등 서비스가 필요로 하는 Action 추가 |
| Lambda에서 실패 | Lambda 실행 Role에 KMS 권한 없음 | Role에 kms:Decrypt 정책 추가 |
| EBS 스냅샷 공유 후 실패 | AWS 관리형 키로 암호화된 스냅샷 | 고객 관리형 키로 재암호화 후 공유 |

### CloudTrail로 원인 추적

```bash
# KMS 관련 AccessDenied 이벤트 조회
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=Decrypt \
  --start-time "2026-04-09T00:00:00Z" \
  --end-time "2026-04-10T23:59:59Z" \
  --query 'Events[?contains(CloudTrailEvent, `AccessDenied`)].CloudTrailEvent' \
  --output text | python3 -m json.tool
```

CloudTrail 이벤트의 `errorCode`와 `errorMessage` 필드에 구체적인 거부 사유가 남는다. `requestParameters`에서 어떤 키에 대해 어떤 Action을 시도했는지 확인할 수 있다.

---

## KMS 작동 원리

### 암호화 절차

1. 앱이 KMS에 Data Key 생성을 요청
2. KMS가 KMS Key를 이용해 Data Key 생성
3. 평문 키와 암호화된 키를 앱에 반환
4. 평문 키로 데이터 암호화
5. 암호화된 데이터 + 암호화된 키 저장

### 복호화 절차

1. 앱이 암호화된 키를 KMS에 전달
2. KMS가 KMS Key로 복호화하여 평문 키 반환
3. 평문 키로 데이터 복호화

---

## 키 관리

- 키 생성, 활성화/비활성화, 삭제 예약 (7~30일)
- 자동 키 로테이션 지원 (1년 주기, 고객 관리형 키만)
- 키 정책: 키 수준의 권한 관리
- IAM 정책: 사용자/역할 기반 권한 부여
- Grant: 제한된 일시적 권한 제공

### 감사 및 보안
- CloudTrail: 키 사용 이력 기록
- CloudWatch: 모니터링 및 경보
- 키 접근 로그로 감사 대응 가능

---

## AWS 서비스와의 연동

| 서비스 | 연동 방식 |
|--------|-----------|
| S3 | SSE-KMS를 통한 객체 암호화 |
| EBS | 볼륨 암호화 및 스냅샷 보안 |
| RDS | 저장 데이터 및 백업 암호화 |
| Lambda | 환경변수 KMS 암호화 지원 |

---

## 권한 관리 실무

### IAM 정책과 키 정책 조합
- 최소 권한 원칙 적용
- IAM 정책과 키 정책 조합 필수
- Grant로 세분화된 권한 위임 가능

### 네트워크 보안
- VPC 엔드포인트 사용 권장
- KMS API 호출은 HTTPS 기반

---

## 요금 구조

| 항목 | 설명 |
|------|------|
| KMS Key 보관료 | $1/month (활성 키 기준) |
| 요청 요금 | 암호화/복호화 10,000건당 $0.03 |
| Free Tier | 월 20,000건 무료 요청 |

### 비용 줄이는 방법
- Envelope Encryption 패턴 사용: KMS API 호출 최소화
- 불필요한 키 삭제
- S3 Bucket Key 활성화: S3 SSE-KMS 요청 비용을 최대 99% 줄인다

---

## 제한 사항 및 주의점

- KMS 키는 리전 단위로 존재 (멀티리전 키 제외)
- 단일 요청 암호화 데이터: 최대 4KB
- KMS 호출 제한: 계정/리전당 초당 요청 제한 (키 유형에 따라 다름, 대칭키 Decrypt는 5,500~30,000 TPS)
- KMS Key 삭제 = 복구 불가능 (해당 키로 암호화된 데이터 전부 복구 불가)
- 삭제 대기 기간(7~30일) 동안 키 사용 시도를 CloudTrail로 모니터링해서 아직 사용 중인 곳이 없는지 확인해야 한다

---

## 코드 예제

### AWS CLI로 KMS 키 관리

```bash
# ── KMS 키 생성 ───────────────────────────────────────
KEY_ID=$(aws kms create-key \
  --description "Application data encryption key" \
  --key-usage ENCRYPT_DECRYPT \
  --key-spec SYMMETRIC_DEFAULT \
  --query 'KeyMetadata.KeyId' --output text)

# 별칭 추가 (사람이 읽기 쉬운 이름)
aws kms create-alias \
  --alias-name alias/app/database \
  --target-key-id $KEY_ID

# 자동 키 교체 활성화 (1년 주기)
aws kms enable-key-rotation --key-id $KEY_ID

# ── 데이터 암호화 / 복호화 ────────────────────────────
# 암호화
CIPHERTEXT=$(aws kms encrypt \
  --key-id alias/app/database \
  --plaintext "민감한 데이터" \
  --query 'CiphertextBlob' --output text)

echo "Encrypted: $CIPHERTEXT"

# 복호화
aws kms decrypt \
  --ciphertext-blob fileb://<(echo $CIPHERTEXT | base64 --decode) \
  --query 'Plaintext' --output text | base64 --decode

# ── 키 정책 확인 / 변경 ───────────────────────────────
aws kms get-key-policy \
  --key-id alias/app/database \
  --policy-name default \
  --query Policy --output text | jq .

# ── 키 정보 조회 ──────────────────────────────────────
aws kms describe-key --key-id alias/app/database
aws kms list-aliases
aws kms get-key-rotation-status --key-id $KEY_ID
```

### Node.js AWS SDK로 데이터 암호화

```javascript
const { KMSClient, EncryptCommand, DecryptCommand, GenerateDataKeyCommand } = require('@aws-sdk/client-kms');

const kms = new KMSClient({ region: 'ap-northeast-2' });
const KEY_ARN = process.env.KMS_KEY_ARN;  // alias/app/database

// ── 소량 데이터 직접 암호화 (4KB 이하) ───────────────
async function encryptData(plaintext) {
    const response = await kms.send(new EncryptCommand({
        KeyId: KEY_ARN,
        Plaintext: Buffer.from(plaintext, 'utf-8')
    }));
    return Buffer.from(response.CiphertextBlob).toString('base64');
}

async function decryptData(ciphertextBase64) {
    const response = await kms.send(new DecryptCommand({
        CiphertextBlob: Buffer.from(ciphertextBase64, 'base64')
    }));
    return Buffer.from(response.Plaintext).toString('utf-8');
}

// 사용 예
const encrypted = await encryptData('홍길동의 주민번호: 123456-1234567');
const decrypted = await decryptData(encrypted);

// ── 대용량 데이터: Envelope Encryption 패턴 ──────────
const crypto = require('crypto');

async function encryptLargeData(data) {
    // 1. KMS에서 데이터 키 생성 (평문 + 암호화된 키)
    const { Plaintext, CiphertextBlob } = await kms.send(new GenerateDataKeyCommand({
        KeyId: KEY_ARN,
        KeySpec: 'AES_256'
    }));

    // 2. 평문 데이터 키로 실제 데이터를 AES-256으로 암호화
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv('aes-256-cbc', Buffer.from(Plaintext), iv);
    const encrypted = Buffer.concat([cipher.update(data, 'utf8'), cipher.final()]);

    // 3. 평문 키는 버리고, 암호화된 키만 보관
    return {
        encryptedData: encrypted.toString('base64'),
        encryptedKey: Buffer.from(CiphertextBlob).toString('base64'),
        iv: iv.toString('base64')
    };
}

async function decryptLargeData({ encryptedData, encryptedKey, iv }) {
    // 1. KMS로 암호화된 데이터 키 복호화
    const { Plaintext } = await kms.send(new DecryptCommand({
        CiphertextBlob: Buffer.from(encryptedKey, 'base64')
    }));

    // 2. 복호화된 데이터 키로 실제 데이터 복호화
    const decipher = crypto.createDecipheriv(
        'aes-256-cbc',
        Buffer.from(Plaintext),
        Buffer.from(iv, 'base64')
    );
    const decrypted = Buffer.concat([
        decipher.update(Buffer.from(encryptedData, 'base64')),
        decipher.final()
    ]);
    return decrypted.toString('utf-8');
}
```

### S3 서버사이드 암호화 설정

```bash
# S3 버킷 기본 암호화 설정 (KMS 키 사용)
aws s3api put-bucket-encryption \
  --bucket my-sensitive-bucket \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms",
        "KMSMasterKeyID": "alias/app/database"
      },
      "BucketKeyEnabled": true
    }]
  }'

# 암호화 설정 확인
aws s3api get-bucket-encryption --bucket my-sensitive-bucket

# 특정 객체 업로드 시 KMS 키 지정
aws s3 cp sensitive-file.txt \
  s3://my-sensitive-bucket/ \
  --sse aws:kms \
  --sse-kms-key-id alias/app/database
```

### RDS 암호화 및 Secrets Manager 연동

```bash
# RDS 인스턴스 생성 시 KMS 암호화 활성화
aws rds create-db-instance \
  --db-instance-identifier my-encrypted-db \
  --db-instance-class db.t3.medium \
  --engine mysql \
  --master-username admin \
  --master-user-password $(openssl rand -base64 24) \
  --storage-encrypted \
  --kms-key-id alias/app/database \
  --allocated-storage 20

# Secrets Manager에 DB 비밀번호 저장 (KMS 암호화)
aws secretsmanager create-secret \
  --name prod/myapp/db-credentials \
  --kms-key-id alias/app/database \
  --secret-string '{
    "username": "admin",
    "password": "supersecretpassword",
    "host": "mydb.cluster.ap-northeast-2.rds.amazonaws.com",
    "port": 3306,
    "dbname": "myapp"
  }'
```

---

## 참고 자료

- [AWS KMS 공식 문서](https://docs.aws.amazon.com/kms/)
- [KMS 키 정책 조건 키 레퍼런스](https://docs.aws.amazon.com/kms/latest/developerguide/conditions-kms.html)
- [KMS 요금 페이지](https://aws.amazon.com/kms/pricing/)
