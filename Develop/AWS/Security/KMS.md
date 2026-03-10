---
title: AWS KMS (Key Management Service)
tags: [aws, security, kms]
updated: 2026-01-06
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
| CMK | KMS에서 관리하는 마스터 키 |
| Data Key | 실제 데이터 암호화에 사용되는 키 |

---

## KMS 키 구조

### CMK (Customer Master Key)
- 키의 최상위 단위
- 대칭키(AES-256) 또는 비대칭키(RSA/ECC)
- KMS 내부 HSM에서 보관
- 직접 데이터 암호화는 하지 않고 Data Key를 암호화함

### Data Key
- 실제 데이터 암호화에 사용
- CMK로 암호화된 상태로 저장
- 평문 키는 메모리에서만 존재

---

## KMS 작동 원리

### 암호화 절차

1. 앱이 KMS에 Data Key 생성을 요청
2. KMS가 CMK를 이용해 Data Key 생성
3. 평문 키와 암호화된 키를 앱에 반환
4. 평문 키로 데이터 암호화
5. 암호화된 데이터 + 암호화된 키 저장

### 복호화 절차

1. 앱이 암호화된 키를 KMS에 전달
2. KMS가 CMK로 복호화하여 평문 키 반환
3. 평문 키로 데이터 복호화

---

## 키 유형 비교

| 키 종류 | 설명 |
|---------|------|
| AWS 관리형 키 | AWS 서비스에서 자동 생성/관리 |
| 고객 관리형 키 | 사용자가 직접 생성하고 정책 관리 |
| 비대칭 키 | 공개키/개인키 쌍, 서명/검증 목적 |

---

## 주요 기능 정리

### 키 관리
- 키 생성, 활성화/비활성화, 삭제 예약 (7~30일)
- 자동 키 로테이션 지원 (1년 주기)
- 키 정책: 키 수준의 권한 관리
- IAM 정책: 사용자/역할 기반 권한 부여
- Grant: 제한된 일시적 권한 제공

### 감사 및 보안
- CloudTrail: 키 사용 이력 기록
- CloudWatch: 모니터링 및 경보
- 키 접근 로그로 감사 대응 가능

---

## AWS 서비스와의 연동 예

| 서비스 | 연동 방식 |
|--------|-----------|
| S3 | SSE-KMS를 통한 객체 암호화 |
| EBS | 볼륨 암호화 및 스냅샷 보안 |
| RDS | 저장 데이터 및 백업 암호화 |
| Lambda | 환경변수 KMS 암호화 지원 |

---

## 보안 및 운영 전략

### 권한 관리
- 최소 권한 원칙 적용
- IAM 정책과 키 정책 조합 필수
- Grant로 세분화된 권한 위임 가능

### 네트워크 보안
- VPC 엔드포인트 사용 권장
- KMS API 호출은 HTTPS 기반

### 로깅 및 모니터링
- 모든 키 작업은 CloudTrail에 기록
- 이상 행동 탐지를 위한 로그 분석 필요

---

## 요금 구조

| 항목 | 설명 |
|------|------|
| CMK 보관료 | $1/month (활성 CMK 기준) |
| 요청 요금 | 암호화/복호화 1,000건당 $0.03 |
| Free Tier | 월 20,000건 무료 요청 제공 |

### 비용 최적화 전략
- Data Key 패턴 사용: CMK 호출 최소화
- 불필요한 CMK 삭제
- 필요한 서비스에만 사용자 지정 키 적용

---

## 제한 사항 및 주의점

- KMS 키는 리전 단위로만 존재 (리전 간 공유 불가)
- 단일 요청 암호화 데이터: 최대 4KB
- KMS 호출 제한: 계정당 초당 10,000 요청 제한
- CMK 삭제 = 복구 불가능 (암호화된 데이터 복구 불가)

---

## 실무 적용 사례

### 전자상거래
- 고객 PII, 결제 정보 암호화
- PCI DSS 준수

### 의료 시스템
- 환자 정보 암호화
- HIPAA 규정 대응

### 금융 서비스
- 민감한 금융 데이터 보호
- 자동 로테이션을 통한 리스크 감소

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
- [KMS 보안 모범 사례](https://docs.aws.amazon.com/kms/latest/developerguide/best-practices.html)
- [KMS 요금 페이지](https://aws.amazon.com/kms/pricing/)