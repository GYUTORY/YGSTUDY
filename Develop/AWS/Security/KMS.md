---
title: AWS KMS (Key Management Service)
tags: [aws, security, kms, encryption]
updated: 2026-05-29
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

## 키 스펙(KeySpec)과 KeyUsage

CMK를 만들 때 키 스펙과 용도(KeyUsage)를 정한다. 한 번 정하면 못 바꾼다. 대칭으로 만든 키를 나중에 비대칭으로 전환하는 식은 안 되고, 새 키를 만들어야 한다.

| KeySpec | 종류 | KeyUsage | 용도 |
|---------|------|----------|------|
| SYMMETRIC_DEFAULT | 대칭 (AES-256-GCM) | ENCRYPT_DECRYPT | 일반 암복호화, GenerateDataKey |
| RSA_2048 / RSA_3072 / RSA_4096 | 비대칭 | ENCRYPT_DECRYPT 또는 SIGN_VERIFY | 암복호화 또는 서명/검증 |
| ECC_NIST_P256 / P384 / P521 / ECC_SECG_P256K1 | 비대칭 | SIGN_VERIFY | 서명/검증 |
| HMAC_224 / 256 / 384 / 512 | 대칭 (HMAC) | GENERATE_VERIFY_MAC | 메시지 인증 코드(MAC) |

대부분은 SYMMETRIC_DEFAULT면 된다. 비대칭이나 HMAC 키는 특정 요구가 있을 때만 쓴다.

### 대칭 키 (SYMMETRIC_DEFAULT)

기본값이다. 키 material이 KMS 밖으로 안 나가고, Encrypt/Decrypt/GenerateDataKey를 전부 쓸 수 있다. Envelope Encryption도 대칭 키로만 된다.

### 비대칭 키 (RSA / ECC)

public key를 KMS 밖으로 꺼낼 수 있다는 게 대칭 키와의 결정적 차이다. GetPublicKey로 공개키를 받아 클라이언트나 외부 시스템에 배포하고, 검증·암호화는 KMS 호출 없이 그 공개키로 처리한다.

제약이 몇 가지 있다.

- 비대칭 키는 GenerateDataKey를 못 쓴다. Envelope Encryption 패턴에 못 넣는다. 직접 Encrypt/Decrypt(또는 Sign/Verify)만 되고, RSA로 한 번에 직접 암호화할 수 있는 데이터도 작다. RSA_2048 + OAEP-SHA256이면 약 190바이트가 한계다.
- KeyUsage를 ENCRYPT_DECRYPT로 만들면 서명에 못 쓰고, SIGN_VERIFY로 만들면 암복호화에 못 쓴다. 둘 다 필요하면 키를 두 개 만든다.
- ECC 키는 SIGN_VERIFY만 된다. 암복호화 용도가 필요하면 RSA를 쓴다.

#### 비대칭 키로 JWT 서명/검증

JWT 서명에 비대칭 키를 쓰면 서명용 private key는 KMS 안에만 있고, 검증은 public key로 어디서든 한다. 검증 측은 KMS를 호출할 필요가 없다.

```bash
# RSA 서명용 키 생성
aws kms create-key \
  --key-spec RSA_2048 \
  --key-usage SIGN_VERIFY \
  --description "JWT signing key"

# JWT의 header.payload 부분을 서명
aws kms sign \
  --key-id alias/jwt-signing \
  --message fileb://jwt-unsigned.txt \
  --message-type RAW \
  --signing-algorithm RSASSA_PKCS1_V1_5_SHA_256 \
  --query Signature --output text

# 검증은 KMS Verify로도 되지만, 공개키를 받아 오프라인 검증하는 게 일반적
aws kms get-public-key \
  --key-id alias/jwt-signing \
  --query PublicKey --output text | base64 --decode > jwt-public.der
```

서명은 KMS, 검증은 공개키로 오프라인 처리하는 Node 예제다.

```javascript
const { KMSClient, SignCommand } = require('@aws-sdk/client-kms');
const crypto = require('crypto');

const kms = new KMSClient({ region: 'ap-northeast-2' });

async function signJwt(headerPayload) {
    const res = await kms.send(new SignCommand({
        KeyId: 'alias/jwt-signing',
        Message: Buffer.from(headerPayload),
        MessageType: 'RAW',
        SigningAlgorithm: 'RSASSA_PKCS1_V1_5_SHA_256'
    }));
    return Buffer.from(res.Signature).toString('base64url');
}

// 검증 측: GetPublicKey로 받아 둔 공개키로 KMS 호출 없이 검증
function verifyJwt(headerPayload, signatureB64, publicKeyPem) {
    const verifier = crypto.createVerify('RSA-SHA256');
    verifier.update(headerPayload);
    return verifier.verify(publicKeyPem, Buffer.from(signatureB64, 'base64url'));
}
```

검증할 때마다 KMS Verify를 호출하면 호출 비용과 지연이 붙는다. 공개키를 한 번 받아 캐싱하고 오프라인 검증하면 KMS 호출은 서명할 때만 일어난다. 트래픽이 많은 인증 서버에서 이 차이가 크다.

#### public key 다운로드 후 클라이언트 측 암호화

클라이언트가 데이터를 암호화해서 보내고 서버만 복호화하게 하려면 ENCRYPT_DECRYPT 용도의 RSA 키를 쓴다. 공개키는 클라이언트에 배포하고, private key는 KMS 안에 둔다.

```bash
aws kms get-public-key \
  --key-id alias/client-upload \
  --query PublicKey --output text | base64 --decode > pub.der
```

클라이언트는 pub.der로 RSA-OAEP 암호화만 하고, 서버는 받은 암호문을 KMS Decrypt로 푼다.

```javascript
// 서버 측 복호화
const { DecryptCommand } = require('@aws-sdk/client-kms');

async function decryptFromClient(ciphertextB64) {
    const res = await kms.send(new DecryptCommand({
        KeyId: 'alias/client-upload',
        CiphertextBlob: Buffer.from(ciphertextB64, 'base64'),
        EncryptionAlgorithm: 'RSAES_OAEP_SHA_256'
    }));
    return Buffer.from(res.Plaintext).toString('utf-8');
}
```

비대칭 Decrypt는 EncryptionAlgorithm을 명시해야 한다. 클라이언트가 OAEP-SHA256으로 암호화했으면 복호화 때도 같은 알고리즘을 줘야 하고, 안 맞으면 InvalidCiphertextException이 난다.

### HMAC 키

GENERATE_VERIFY_MAC 용도로만 쓴다. 메시지 무결성 검증용 MAC을 만들고 검증한다. 애플리케이션이 HMAC 키를 직접 들고 있지 않고 KMS 안에 두고 GenerateMac/VerifyMac을 호출한다. 웹훅 서명 검증처럼 공유 비밀이 노출되면 안 되는 곳에 쓴다.

```bash
aws kms create-key --key-spec HMAC_256 --key-usage GENERATE_VERIFY_MAC

aws kms generate-mac \
  --key-id alias/webhook-mac \
  --message fileb://payload.json \
  --mac-algorithm HMAC_SHA_256
```

---

## 키 출처(Origin)

키 material을 누가 만들고 어디에 두느냐다. 생성 시 `--origin`으로 정한다.

| Origin | 키 material 생성 주체 | 보관 위치 | 자동 로테이션 |
|--------|----------------------|----------|--------------|
| AWS_KMS | KMS | AWS KMS HSM | 지원 |
| EXTERNAL | 사용자가 import (BYOK) | AWS KMS HSM | 미지원 |
| AWS_CLOUDHSM | CloudHSM 클러스터 | 사용자 소유 CloudHSM | 미지원 |

### AWS_KMS (기본)

KMS가 HSM 안에서 키 material을 만들고 보관한다. 따로 신경 쓸 게 없고, 대부분 이걸 쓴다.

### EXTERNAL (BYOK, 키 material import)

규제나 내부 정책상 키 material을 직접 생성해서 가져와야 할 때 쓴다. 절차가 까다롭다.

```bash
# 1. EXTERNAL 키 생성 (아직 키 material 없음 → PendingImport 상태)
KEY_ID=$(aws kms create-key \
  --origin EXTERNAL \
  --description "BYOK key" \
  --query 'KeyMetadata.KeyId' --output text)

# 2. import 파라미터 요청 → 래핑용 공개키 + import token 수령
aws kms get-parameters-for-import \
  --key-id $KEY_ID \
  --wrapping-algorithm RSAES_OAEP_SHA_256 \
  --wrapping-key-spec RSA_4096 \
  --query '{PublicKey:PublicKey,ImportToken:ImportToken}'

# 3. 받은 공개키로 내 키 material을 래핑 (로컬에서 OpenSSL 등으로)

# 4. 래핑된 키 material + import token으로 import
aws kms import-key-material \
  --key-id $KEY_ID \
  --encrypted-key-material fileb://wrapped-key.bin \
  --import-token fileb://import-token.bin \
  --expiration-model KEY_MATERIAL_DOES_NOT_EXPIRE
```

주의점.

- import token은 24시간 후 만료된다. GetParametersForImport로 받은 토큰과 공개키는 한 쌍이고, 만료되면 둘 다 다시 받아야 한다.
- 키 material에 만료 시각을 걸면(KEY_MATERIAL_EXPIRES) 만료 후 키가 PendingImport로 돌아가 사용 불가가 된다. 만료 전에 같은 material을 다시 import해야 한다. 만료 모델을 잘못 잡으면 운영 중 갑자기 복호화가 막힌다.
- 자동 로테이션이 안 된다. 로테이션하려면 새 키를 만들어 새 material을 import하고 alias를 옮긴다.
- AWS는 import한 material의 사본을 따로 보관해 주지 않는다. 원본 material을 잃어버린 상태에서 KMS의 material까지 DeleteImportedKeyMaterial로 지우면 그 키로 암호화한 데이터는 복구 불가다. 원본 material 백업은 사용자 책임이다.

### AWS_CLOUDHSM (Custom Key Store)

KMS 키 material을 AWS가 운영하는 공용 HSM이 아니라 내가 소유한 CloudHSM 클러스터에 두는 방식이다. 규제상 키가 전용 HSM에 있어야 할 때 쓴다.

운영 부담이 크다.

- CloudHSM 클러스터의 가용성, 백업, HSM 인스턴스 수를 직접 관리한다. 클러스터가 죽으면 그 키로 하는 KMS 작업이 전부 실패한다.
- HSM 사용자(CU) 자격 증명 관리, 클러스터 정족수 같은 CloudHSM 자체 운영 지식이 필요하다.
- 자동 로테이션 미지원.
- 비용도 높다. CloudHSM 인스턴스 시간당 과금이 KMS 요금과 별개로 붙는다.

가용성 요구가 높은 워크로드에서 단일 HSM 클러스터에 의존하면 위험하다. 멀티 AZ로 HSM을 여러 개 두고도 클러스터 장애 시나리오를 검증해야 한다. 규제 요건이 명확하지 않으면 AWS_KMS를 쓰는 게 운영상 안전하다.

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

## 키 로테이션 심화

자동 로테이션은 backing key(HSM 안의 실제 키 material)만 교체한다. KeyId와 ARN, alias는 그대로다. 그래서 애플리케이션 코드나 키 참조를 바꿀 필요가 없다.

```bash
# 자동 로테이션 켜기 (고객 관리형 대칭 키)
aws kms enable-key-rotation --key-id $KEY_ID

# 로테이션 주기 지정 (기본 365일, 90~2560일 사이)
aws kms enable-key-rotation --key-id $KEY_ID --rotation-period-in-days 180

# 상태 확인
aws kms get-key-rotation-status --key-id $KEY_ID

# 주기와 별개로 즉시 1회 로테이션
aws kms rotate-key-on-demand --key-id $KEY_ID
```

### 옛 데이터는 어떻게 복호화되나

로테이션해도 KMS가 이전 backing key를 계속 보관한다. 옛날에 암호화한 데이터에는 그때 쓴 backing key의 식별자가 암호문 안에 들어 있어서, Decrypt 시 KMS가 알맞은 옛 backing key를 골라 자동 복호화한다. 로테이션했다고 옛 데이터를 다시 암호화할 필요가 없다.

새로 암호화하는 데이터에만 최신 backing key가 쓰인다. 결과적으로 한 KMS 키 아래 여러 세대의 backing key가 쌓이고, KMS가 알아서 골라 쓴다. 사용자 입장에서는 KeyId 하나만 보면 되고, 내부 세대 관리는 신경 쓸 게 없다.

### 수동 로테이션 (alias 재지정)

비대칭 키, HMAC 키, import(EXTERNAL) 키, CloudHSM 키는 자동 로테이션이 안 된다. 이 경우 새 키를 만들고 alias를 옮겨 수동으로 로테이션한다.

```bash
NEW_KEY_ID=$(aws kms create-key --key-spec RSA_2048 --key-usage SIGN_VERIFY \
  --query 'KeyMetadata.KeyId' --output text)

# alias를 새 키로 이동 — 이후 새 암호화/서명은 새 키로 나감
aws kms update-alias --alias-name alias/jwt-signing --target-key-id $NEW_KEY_ID
```

자동 로테이션과 달리 수동 로테이션은 KeyId가 바뀐다. 옛 키로 암호화/서명한 데이터를 복호화/검증하려면 옛 키를 지우면 안 된다. 비활성화도 하지 말고 살려둔 채 alias만 옮긴다. 검증 측이 여러 공개키를 동시에 받아들이도록 해 둬야 전환 중에 검증 실패가 안 난다.

### AWS 관리형 키 로테이션

`aws/s3` 같은 AWS 관리형 키는 자동으로 1년마다 로테이션된다. 끄거나 주기를 바꿀 수 없고, AWS가 알아서 처리한다.

---

## Grant 상세

Grant는 키 정책을 건드리지 않고 특정 주체에게 한정된 권한을 임시로 주는 방법이다. 프로그래밍으로 만들고 회수한다.

```bash
# Lambda 실행 Role에 Decrypt와 GenerateDataKey만 허용하는 Grant 생성
aws kms create-grant \
  --key-id $KEY_ID \
  --grantee-principal arn:aws:iam::111122223333:role/LambdaRole \
  --operations Decrypt GenerateDataKey \
  --constraints EncryptionContextSubset={app=billing} \
  --query '{GrantId:GrantId,GrantToken:GrantToken}'
```

### GrantToken

CreateGrant 응답에는 GrantId와 GrantToken이 같이 온다. Grant는 만들어도 KMS 전 리전에 퍼지는 데 시간이 걸려서(최종 일관성), 만든 직후 바로 키를 쓰면 아직 권한이 없다고 거부될 수 있다. 이때 응답으로 받은 GrantToken을 API 호출에 같이 넘기면 전파를 기다리지 않고 즉시 권한이 적용된다.

```bash
aws kms decrypt \
  --ciphertext-blob fileb://encrypted.bin \
  --grant-tokens $GRANT_TOKEN
```

### RetireGrant vs RevokeGrant

- RetireGrant: 더 쓸 일이 없을 때 Grant를 정리한다. Grant를 만든 주체, grantee, RetiringPrincipal이 호출할 수 있다. "일 끝났으니 반납"에 가깝다.
- RevokeGrant: 키 관리자가 권한을 강제로 회수한다. "당장 뺏는다"에 가깝다. 보안 사고 대응으로 권한을 즉시 끊을 때 쓴다.

```bash
aws kms retire-grant --key-id $KEY_ID --grant-id $GRANT_ID
aws kms revoke-grant --key-id $KEY_ID --grant-id $GRANT_ID
aws kms list-grants --key-id $KEY_ID
```

### AWS 서비스가 Grant를 쓰는 이유

EBS, RDS, Redshift 같은 서비스가 고객 관리형 키로 리소스를 암호화하면, 그 서비스가 내 키에 Grant를 만든다. 예를 들어 암호화 EBS 볼륨을 만들면 EC2/EBS가 볼륨 수명 동안 GenerateDataKey와 Decrypt를 할 수 있는 Grant를 내 키에 생성한다.

키 정책을 직접 고치지 않고 Grant를 쓰는 이유가 있다.

- 리소스 단위로 권한을 잘게 쪼갤 수 있다. 볼륨 하나당 Grant 하나 식이다.
- 리소스를 지우면 Grant도 회수되어 권한이 자동으로 사라진다.
- 키 정책을 매번 수정하면 정책이 비대해지고 충돌이 난다. Grant는 프로그래밍으로 대량 생성할 수 있다(키당 최대 50,000개).

`kms:GrantIsForAWSResource` 조건으로 "AWS 서비스가 자기 리소스용으로 만드는 Grant만 허용"하도록 제한할 수 있다.

### 키 정책과의 차이

| 구분 | 키 정책 | Grant |
|------|--------|-------|
| 성격 | 키에 붙는 기본 리소스 정책 | 임시·세분화 권한 위임 |
| 변경 방법 | PutKeyPolicy로 사람이 수정 | CreateGrant/RetireGrant/RevokeGrant로 프로그래밍 |
| Deny | 명시적 Deny 가능 | Allow만, Deny 없음 |
| 수명 | 명시적으로 바꿀 때까지 유지 | 회수하거나 리소스 삭제 시 사라짐 |
| 용도 | 전체 접근 통제의 뼈대 | AWS 서비스 연동, 일시 위임 |

Grant는 권한을 더해주기만 한다. 키 정책의 Deny를 Grant로 뚫을 수는 없다.

---

## 키 비활성화·삭제·삭제 예약

KMS 키는 바로 못 지운다. 키로 암호화한 데이터가 어딘가에 남아 있으면 키 삭제가 곧 데이터 영구 손실이라, AWS가 의무 대기 기간을 둔다.

### 비활성화 (DisableKey)

키를 못 쓰게 막되 언제든 되돌릴 수 있다. 키 material은 그대로 있고 EnableKey로 즉시 복구된다. 보관료($1/월)는 계속 나간다.

```bash
aws kms disable-key --key-id $KEY_ID
aws kms enable-key --key-id $KEY_ID
```

삭제 전에 먼저 비활성화해서 영향을 관찰하는 용도로 쓴다. 비활성화 후 한동안 CloudTrail을 보며 그 키를 쓰는 곳이 없는지 확인하고, 문제없으면 삭제를 예약한다.

### 삭제 예약 (ScheduleKeyDeletion)

즉시 삭제는 불가능하고 7~30일 대기 기간을 둔다(기본 30일). 대기 중에는 PendingDeletion 상태가 되어 키를 쓸 수 없다.

```bash
# 대기 기간 7일로 삭제 예약
aws kms schedule-key-deletion --key-id $KEY_ID --pending-window-in-days 7
```

대기 기간이 지나면 키와 metadata가 영구 삭제되고, 그 키로 암호화한 데이터는 전부 복구 불가가 된다.

### 삭제 취소 (CancelKeyDeletion)

대기 기간 안이면 삭제를 취소할 수 있다. 취소하면 키가 Disabled 상태로 돌아온다. 다시 쓰려면 EnableKey로 활성화한다.

```bash
aws kms cancel-key-deletion --key-id $KEY_ID
aws kms enable-key --key-id $KEY_ID
```

### 실무 순서

1. 비활성화한다.
2. 대기 기간(최대 30일) 동안 CloudTrail로 Decrypt/Encrypt 호출이 들어오는지 본다. 한 건이라도 있으면 아직 그 키에 의존하는 데이터나 서비스가 있다는 뜻이다.
3. 호출이 완전히 끊긴 걸 확인하면 삭제를 예약한다.

import(EXTERNAL) 키는 키 자체를 지우지 않고 키 material만 제거할 수 있다. DeleteImportedKeyMaterial로 material만 지우면 키는 PendingImport로 남고, 나중에 같은 material을 다시 import해 되살릴 수 있다. 키 정의와 정책, alias를 유지한 채 잠시 봉인하는 셈이다.

```bash
aws kms delete-imported-key-material --key-id $KEY_ID
```

멀티리전 키는 Replica가 남아 있으면 Primary를 삭제할 수 없다. Replica를 먼저 전부 정리해야 Primary를 지울 수 있다.

---

## 감사와 로깅

KMS의 모든 API 호출은 CloudTrail에 남는다. Encrypt, Decrypt, GenerateDataKey, CreateGrant 같은 호출마다 누가 어떤 키에 어떤 작업을 했는지, 어떤 Encryption Context를 넘겼는지가 이벤트로 기록된다. 키를 누가 쓰는지 추적하거나 AccessDeniedException 원인을 찾을 때 이 기록이 출발점이 된다. 삭제 예약 전에 그 키를 아직 쓰는 곳이 있는지 보는 것도 결국 CloudTrail의 Decrypt/Encrypt 이벤트를 확인하는 일이다.

CloudWatch로는 키 사용량이나 비정상 패턴에 경보를 건다. 평소보다 Decrypt 호출이 급증하거나 삭제 예약한 키에 접근 시도가 들어오면 알림이 오도록 메트릭 필터와 경보를 걸어 둔다.

---

## AWS 서비스와의 연동

| 서비스 | 연동 방식 |
|--------|-----------|
| S3 | SSE-KMS를 통한 객체 암호화 |
| EBS | 볼륨 암호화 및 스냅샷 보안 |
| RDS | 저장 데이터 및 백업 암호화 |
| Lambda | 환경변수 KMS 암호화 지원 |

---

## 네트워크 보안

KMS API는 전부 HTTPS로 호출된다. 기본적으로 퍼블릭 엔드포인트(kms.<region>.amazonaws.com)를 거치기 때문에, VPC 안에서만 도는 워크로드가 NAT 게이트웨이 없이 KMS를 쓰려면 인터페이스 VPC 엔드포인트(PrivateLink)를 만든다. 그러면 KMS 트래픽이 인터넷을 타지 않고 VPC 내부에서 처리된다. 엔드포인트에 정책을 붙여 특정 키나 Action만 통과시킬 수도 있는데, 이 정책을 너무 좁게 잡으면 그 자체가 AccessDeniedException의 원인이 되니 트러블슈팅 때 같이 본다.

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
