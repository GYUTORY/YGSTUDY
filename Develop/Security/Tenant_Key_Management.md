---
title: 테넌트별 암호화 키 격리
tags: [security, architecture, encryption]
updated: 2026-08-04
---

# 테넌트별 암호화 키 격리

## 시작하기 전에

멀티테넌트 SaaS에서 데이터베이스 암호화를 적용할 때 가장 쉬운 방법은 RDS 기본 암호화를 켜거나 KMS 키 하나로 전체 데이터를 암호화하는 것이다. 동작하기는 하지만 테넌트 격리 관점에서는 약하다.

하나의 키로 모든 테넌트 데이터를 암호화하면, 키가 유출될 때 전체 테넌트 데이터가 위험해진다. 테넌트 A가 데이터 삭제를 요청해도 물리 디스크에 남은 암호화 데이터는 같은 키로 복호화할 수 있다. 테넌트별로 키를 분리하면 이 문제를 다르게 접근할 수 있다. 탈퇴 테넌트의 키만 폐기하면, 스토리지에 암호화된 데이터가 남아있어도 더 이상 복호화할 수 없다. 이를 암호화 삭제(Cryptographic Erasure)라고 한다.

---

## AWS KMS에서 테넌트별 CMK 분리

AWS KMS에서 Customer Managed Key(CMK)를 테넌트마다 생성하는 것이 기본이다. CMK 자체는 암호화 키 재료를 직접 다루지 않고 KMS 서비스 안에서 관리된다. 애플리케이션 코드는 CMK ID를 참조해서 KMS API를 호출할 뿐이다.

```python
import boto3

kms = boto3.client('kms', region_name='ap-northeast-2')

def create_tenant_cmk(tenant_id: str) -> str:
    response = kms.create_key(
        Description=f'CMK for tenant {tenant_id}',
        KeyUsage='ENCRYPT_DECRYPT',
        KeySpec='SYMMETRIC_DEFAULT',
        Tags=[
            {'TagKey': 'tenant_id', 'TagValue': tenant_id},
            {'TagKey': 'managed_by', 'TagValue': 'key-management-service'},
        ]
    )
    key_id = response['KeyMetadata']['KeyId']

    # 별칭 설정 - ARN 대신 사람이 읽기 쉬운 이름으로 참조 가능
    kms.create_alias(
        AliasName=f'alias/tenant/{tenant_id}',
        TargetKeyId=key_id
    )

    return key_id
```

CMK 비용은 월 $1/키다. 테넌트가 수천 개면 월 수천 달러가 된다. 이 비용이 부담스러우면 유료 플랜 테넌트에만 전용 CMK를 부여하고, 무료/기본 플랜은 플랜 공유 CMK를 쓰되 암호화 컨텍스트로 테넌트를 바인딩하는 절충안을 쓰기도 한다.

CMK를 생성한 뒤 Key Policy를 설정해야 한다. 기본 Key Policy는 계정 루트가 전체 권한을 갖지만, 실제로는 키 관리 권한과 키 사용 권한을 분리한다.

```json
{
  "Statement": [
    {
      "Sid": "AllowKeyAdministration",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/KeyAdminRole"
      },
      "Action": [
        "kms:Create*", "kms:Describe*", "kms:Enable*",
        "kms:List*", "kms:Put*", "kms:Update*",
        "kms:Revoke*", "kms:Disable*", "kms:Delete*",
        "kms:ScheduleKeyDeletion", "kms:CancelKeyDeletion"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowKeyUsage",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/AppServerRole"
      },
      "Action": [
        "kms:GenerateDataKey",
        "kms:Decrypt"
      ],
      "Resource": "*"
    }
  ]
}
```

애플리케이션 서버 역할(`AppServerRole`)에는 `GenerateDataKey`와 `Decrypt`만 준다. `ScheduleKeyDeletion` 같은 키 관리 작업은 별도 관리 역할(`KeyAdminRole`)에만 허용한다. 이 분리를 하지 않으면 애플리케이션 서버가 탈취됐을 때 공격자가 키를 삭제해버릴 수 있다.

---

## DEK/KEK 계층 구조

CMK로 모든 데이터를 직접 암호화하면 문제가 생긴다. 대용량 파일을 KMS API로 직접 암호화할 수 없고(최대 4KB), API 호출 횟수가 데이터 레코드 수만큼 늘어나서 비용과 레이턴시 문제가 된다.

실제로는 두 계층으로 나눈다.

- KEK(Key Encryption Key): AWS CMK. 테넌트마다 하나
- DEK(Data Encryption Key): CMK로 보호되는 실제 암호화 키. 레코드나 파일 단위로 생성

KMS에서 DEK를 생성하면 평문 DEK와 암호화된 DEK(CiphertextBlob)를 함께 돌려준다. 평문 DEK로 로컬에서 데이터를 AES-256-GCM으로 암호화하고, 평문 DEK는 메모리에서 즉시 제거한다. 암호화된 데이터와 암호화된 DEK를 함께 저장한다. 복호화할 때는 암호화된 DEK를 KMS에 보내서 평문 DEK를 다시 받아 데이터를 복호화한다.

```python
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def encrypt_data(tenant_id: str, plaintext: bytes) -> dict:
    # CMK로 DEK 생성
    response = kms.generate_data_key(
        KeyId=f'alias/tenant/{tenant_id}',
        KeySpec='AES_256',
        EncryptionContext={'tenant_id': tenant_id}
    )

    plaintext_dek = response['Plaintext']       # 평문 DEK (메모리에만 존재)
    encrypted_dek = response['CiphertextBlob']  # 암호화된 DEK (저장)

    # AES-256-GCM으로 데이터 암호화
    nonce = os.urandom(12)
    aesgcm = AESGCM(plaintext_dek)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    # 평문 DEK 제거 (명시적 덮어쓰기)
    plaintext_dek = b'\x00' * len(plaintext_dek)

    return {
        'ciphertext': base64.b64encode(ciphertext).decode(),
        'nonce': base64.b64encode(nonce).decode(),
        'encrypted_dek': base64.b64encode(encrypted_dek).decode(),
        'tenant_id': tenant_id,
    }


def decrypt_data(tenant_id: str, encrypted_payload: dict) -> bytes:
    encrypted_dek = base64.b64decode(encrypted_payload['encrypted_dek'])

    # KMS에서 DEK 복호화
    response = kms.decrypt(
        CiphertextBlob=encrypted_dek,
        EncryptionContext={'tenant_id': tenant_id}
    )

    plaintext_dek = response['Plaintext']

    nonce = base64.b64decode(encrypted_payload['nonce'])
    ciphertext = base64.b64decode(encrypted_payload['ciphertext'])
    aesgcm = AESGCM(plaintext_dek)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)

    plaintext_dek = b'\x00' * len(plaintext_dek)

    return plaintext
```

DEK를 레코드마다 생성하면 KMS API 호출이 많아진다. 성능이 문제라면 DEK를 일정 시간 동안 메모리에 캐시하는 방식을 쓰기도 한다. 캐시 유효 시간은 5~15분이 적당하다. 다만 캐시된 평문 DEK가 메모리에 상주하는 만큼 보안 트레이드오프가 있다.

---

## 암호화 컨텍스트로 테넌트 바인딩

`EncryptionContext`는 KMS에서 암호화/복호화 시 추가로 제공하는 키-값 쌍이다. KMS는 이 값을 암호화 알고리즘에 포함시켜서, 같은 암호화된 DEK라도 다른 컨텍스트로 복호화를 시도하면 실패한다.

위 코드에서 `EncryptionContext={'tenant_id': tenant_id}`를 넣었다. 테넌트 A의 컨텍스트로 생성한 암호화된 DEK를 테넌트 B의 컨텍스트로 복호화하려 하면 KMS가 `InvalidCiphertextException`을 돌려준다. 애플리케이션 버그로 잘못된 테넌트의 DEK를 복호화하는 경우를 방지한다.

컨텍스트에는 필요에 따라 정보를 더 추가할 수 있다.

```python
EncryptionContext={
    'tenant_id': tenant_id,
    'data_classification': 'pii',
    'region': 'ap-northeast-2',
}
```

EncryptionContext는 KMS CloudTrail 로그에 평문으로 기록된다. 로그를 분석하면 어떤 테넌트가 언제 어떤 데이터를 암호화하거나 복호화했는지 추적할 수 있어서, 별도 작업 없이 감사 로그로 활용된다.

주의할 점은 암호화 시와 복호화 시의 EncryptionContext 값이 정확히 일치해야 한다는 것이다. 대소문자, 공백 하나도 달라지면 복호화가 실패한다. 컨텍스트 값을 동적으로 생성하는 경우 정규화 로직을 통일해야 한다.

```python
def build_encryption_context(tenant_id: str) -> dict:
    return {'tenant_id': str(tenant_id).lower().strip()}
```

---

## 키 로테이션 주기 관리

AWS KMS에서 CMK 자동 로테이션을 켜면 매년 새 키 재료(backing key)가 생성된다.

```python
kms.enable_key_rotation(KeyId=f'alias/tenant/{tenant_id}')

# 로테이션 상태 확인
response = kms.get_key_rotation_status(KeyId=f'alias/tenant/{tenant_id}')
print(response['KeyRotationEnabled'])  # True
```

자동 로테이션에서 중요한 것은 기존 데이터를 다시 암호화하지 않는다는 점이다. 새 키 재료로는 새로 생성하는 DEK만 암호화된다. 이전에 암호화된 DEK들은 당시 키 재료로 복호화된다. KMS가 내부적으로 어떤 키 재료로 암호화됐는지 추적하기 때문에 별도 처리 없이 자동으로 맞는 키를 쓴다.

자동 로테이션은 1년 주기다. 보안 정책상 더 짧은 주기를 요구한다면 DEK를 수동으로 교체해야 한다.

```python
def rotate_tenant_dek(tenant_id: str, current_payload: dict) -> dict:
    # 기존 데이터 복호화
    plaintext = decrypt_data(tenant_id, current_payload)

    # 새 DEK로 재암호화
    new_payload = encrypt_data(tenant_id, plaintext)

    return new_payload
```

수백만 건의 레코드를 한 번에 재암호화하면 KMS API 쿼터 문제가 생긴다. 배치 작업으로 나눠서 처리하되, KMS의 `GenerateDataKey` 쿼터(기본 초당 5,500회)를 확인하고 필요하면 쿼터 증가 요청을 해야 한다.

---

## 테넌트 탈퇴 시 키 폐기

테넌트가 탈퇴하면 해당 테넌트의 CMK를 삭제 예약(ScheduleKeyDeletion)한다. AWS KMS는 즉시 삭제를 허용하지 않고 최소 7일, 최대 30일의 대기 기간을 요구한다.

```python
def schedule_tenant_key_deletion(tenant_id: str, pending_days: int = 30) -> dict:
    response = kms.schedule_key_deletion(
        KeyId=f'alias/tenant/{tenant_id}',
        PendingWindowInDays=pending_days  # 7~30
    )

    deletion_date = response['DeletionDate']

    # DB에 삭제 예정 일시 기록
    record_key_deletion_scheduled(tenant_id, deletion_date)

    return {
        'tenant_id': tenant_id,
        'deletion_date': deletion_date.isoformat(),
    }
```

대기 기간 동안에는 키를 복구할 수 있다.

```python
def cancel_tenant_key_deletion(tenant_id: str):
    key_id = get_key_id_by_tenant(tenant_id)
    kms.cancel_key_deletion(KeyId=key_id)
    kms.enable_key(KeyId=key_id)
```

삭제 예약 후에는 해당 CMK로 `GenerateDataKey`나 `Decrypt`를 호출하면 `KMSInvalidStateException`이 발생한다. 키가 완전히 삭제되면 암호화된 DEK를 복호화할 방법이 없어지고, 스토리지에 남아있는 암호화된 데이터는 영구적으로 접근 불가 상태가 된다.

키 삭제 전에 해당 테넌트 데이터를 물리적으로 삭제할지, 암호화된 채로 남겨둘지는 규정 요구사항에 따라 다르다. GDPR Right to Erasure에서 암호화 삭제를 물리적 삭제와 동등하게 인정하는 경우가 있지만, 규제 기관마다 해석이 다르고 법적 검토가 필요하다.

```python
def handle_tenant_offboarding(tenant_id: str):
    # 테넌트 계정 비활성화
    deactivate_tenant(tenant_id)

    # CMK 삭제 예약 (30일 후 삭제)
    schedule_tenant_key_deletion(tenant_id, pending_days=30)

    # 감사 로그 기록
    audit_log.record(
        event='tenant_key_deletion_scheduled',
        tenant_id=tenant_id,
        scheduled_by='offboarding_process',
    )

    # 물리적 삭제가 필요한 경우 별도 작업 큐에 적재
    if requires_physical_deletion(tenant_id):
        enqueue_data_deletion_job(tenant_id)
```

---

## 실무에서 생기는 문제들

### KMS API 쿼터 초과

테넌트가 많아지면 KMS API 호출이 집중되는 시간대에 `ThrottlingException`이 발생한다. 기본 쿼터인 초당 5,500회는 생각보다 빨리 소진된다. 재시도 로직에 지수 백오프를 적용하고, 장기적으로는 DEK 캐싱이나 쿼터 증가 신청을 고려해야 한다.

```python
import random
import time
from botocore.exceptions import ClientError

def decrypt_with_retry(encrypted_dek: bytes, encryption_context: dict, max_retries: int = 3) -> bytes:
    for attempt in range(max_retries):
        try:
            response = kms.decrypt(
                CiphertextBlob=encrypted_dek,
                EncryptionContext=encryption_context
            )
            return response['Plaintext']
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException' and attempt < max_retries - 1:
                wait = (2 ** attempt) + (random.random() * 0.5)
                time.sleep(wait)
            else:
                raise
```

### 암호화 컨텍스트 불일치

EncryptionContext를 잘못 구성해서 복호화가 실패하는 경우가 있다. 테넌트 ID를 숫자로 저장해두고 컨텍스트에는 문자열로 넣거나, 대소문자 변환이 중간에 끼면 `InvalidCiphertextException`이 발생한다. 에러 메시지가 "Invalid ciphertext"로 나와서 처음엔 데이터 손상이나 키 문제로 착각하기 쉽다.

컨텍스트 구성 함수를 중앙화하고, 암호화할 때 사용한 컨텍스트를 메타데이터로 함께 저장해두면 디버깅이 편하다.

### CMK 실수로 삭제 예약 후 복구 못 한 경우

실수로 CMK 삭제 예약을 했을 때 대기 기간 내에 취소하지 못하면 데이터를 영구적으로 잃는다. 이 위험을 줄이려면 키 삭제 예약 API에 대한 IAM 권한을 애플리케이션 서버 역할에서 제거하고, 별도 관리 절차를 거쳐야만 실행할 수 있도록 해야 한다.

CloudWatch에서 `kms:ScheduleKeyDeletion` 이벤트를 모니터링하고, 발생 시 즉시 알림을 받도록 설정해두는 게 최소한의 안전망이다.

```bash
aws events put-rule \
  --name kms-key-deletion-alert \
  --event-pattern '{
    "source": ["aws.kms"],
    "detail-type": ["AWS API Call via CloudTrail"],
    "detail": {
      "eventName": ["ScheduleKeyDeletion"]
    }
  }' \
  --state ENABLED
```

### 멀티 리전 구성 시 키 동기화

서울 리전과 버지니아 리전 양쪽에서 같은 테넌트 데이터에 접근해야 하는 경우가 있다. KMS 키는 리전별로 독립적이라서 서울 리전에서 암호화한 DEK를 버지니아 리전 KMS로 복호화할 수 없다. AWS KMS Multi-Region Key를 쓰면 여러 리전에서 같은 키 재료를 공유할 수 있다.

```python
# 프라이머리 키 생성 (서울 리전)
primary_response = kms.create_key(
    Description=f'Multi-Region CMK for tenant {tenant_id}',
    MultiRegion=True,
    KeyUsage='ENCRYPT_DECRYPT',
    KeySpec='SYMMETRIC_DEFAULT',
)

# 레플리카 키 생성 (버지니아 리전)
kms_us = boto3.client('kms', region_name='us-east-1')
replica_response = kms_us.replicate_key(
    KeyId=primary_response['KeyMetadata']['KeyId'],
    ReplicaRegion='us-east-1',
)
```

Multi-Region Key는 동일한 키 재료를 갖지만 각 리전에서 독립적으로 관리된다. 한 리전에서 키를 삭제해도 다른 리전의 레플리카에는 영향을 주지 않는다. 테넌트 탈퇴 시 모든 리전의 CMK를 삭제 예약해야 한다.
