---
title: GCS 암호화 심화
tags: [gcp, encryption, security, cloud]
updated: 2026-07-27
---

# GCS 암호화

GCS는 저장된 모든 데이터를 기본적으로 암호화한다. 암호화 방식은 세 가지인데, 키를 누가 관리하느냐에 따라 나뉜다.

## 암호화 방식 비교

| 방식 | 키 관리 주체 | 키 저장 위치 | 주요 제약 |
|------|-------------|-------------|----------|
| Google 관리 암호화 (GMEK) | Google | Google 내부 KMS | 키 제어 불가 |
| 고객 관리 암호화 키 (CMEK) | 고객 (Cloud KMS 경유) | Cloud KMS | KMS 권한 설정 필요 |
| 고객 제공 암호화 키 (CSEK) | 고객 | 고객 시스템 | 요청마다 키 직접 전달 |

Cloud KMS 키는 다시 보호 수준(protection level)으로 나뉜다. SOFTWARE, HSM, EXTERNAL, EXTERNAL_VPC 네 가지다. CMEK를 쓴다고 다 같은 게 아니라, 키가 어떤 하드웨어 또는 외부 시스템에서 보호받는지가 달라진다.

---

## Google 관리 암호화 (GMEK)

별도 설정 없이 자동 적용된다. AES-256으로 데이터를 암호화하고, 봉투 암호화(Envelope Encryption) 방식으로 키를 보호한다. 키 교체도 Google이 알아서 한다.

규제 요건이 없고, 키 관리 부담을 줄이고 싶을 때 쓴다. 대부분의 서비스에서 이걸로 충분하다.

---

## CMEK — Cloud KMS 연동

고객이 Cloud KMS에서 직접 키를 만들어 GCS 버킷에 연결하는 방식이다. 키 교체 주기 설정, 키 비활성화, 감사 로그 확인이 가능하다.

금융권이나 의료 데이터처럼 "우리 회사가 키를 통제한다"는 걸 증명해야 하는 상황에서 사용한다.

### 기본 설정

**1. KMS 키링과 키 생성**

```bash
# 키링 생성
gcloud kms keyrings create my-keyring \
  --location=asia-northeast3

# 소프트웨어 보호 키 생성 (기본값)
gcloud kms keys create my-bucket-key \
  --location=asia-northeast3 \
  --keyring=my-keyring \
  --purpose=encryption
```

**2. GCS 서비스 계정에 KMS 권한 부여**

```bash
# GCS 서비스 계정 확인
gcloud storage service-agent --project=my-project

# KMS 암호화/복호화 권한 부여
gcloud kms keys add-iam-policy-binding my-bucket-key \
  --location=asia-northeast3 \
  --keyring=my-keyring \
  --member="serviceAccount:service-123456@gs-project-accounts.iam.gserviceaccount.com" \
  --role="roles/cloudkms.cryptoKeyEncrypterDecrypter"
```

**3. 버킷에 CMEK 적용**

```bash
gcloud storage buckets create gs://my-bucket \
  --location=ASIA-NORTHEAST3 \
  --default-kms-key=projects/my-project/locations/asia-northeast3/keyRings/my-keyring/cryptoKeys/my-bucket-key
```

기존 버킷에 적용할 때는 `buckets update`를 쓰면 된다.

```bash
gcloud storage buckets update gs://my-bucket \
  --default-kms-key=projects/my-project/locations/asia-northeast3/keyRings/my-keyring/cryptoKeys/my-bucket-key
```

---

### Cloud HSM 기반 키

FIPS 140-2 Level 3 인증을 받은 하드웨어 보안 모듈(HSM)에서 키를 생성하고 보호하는 방식이다. 키가 HSM 외부로 나오지 않는다. PCI-DSS나 특정 금융 규제에서 "키는 HSM에서만 관리되어야 한다"는 요건을 충족할 때 선택한다.

SOFTWARE 키 대비 비용이 높고, 암호화/복호화 레이턴시도 소폭 증가한다. 대용량 데이터를 자주 암호화하는 경우 레이턴시 차이가 쌓인다.

```bash
# HSM 보호 키 생성
gcloud kms keys create my-hsm-key \
  --location=asia-northeast3 \
  --keyring=my-keyring \
  --purpose=encryption \
  --protection-level=hsm
```

HSM 은 일부 리전에서는 지원되지 않는다. 사용 전에 해당 리전의 HSM 지원 여부를 확인해야 한다.

```bash
# 리전별 HSM 지원 여부 확인
gcloud kms locations list
```

키 생성 후 `describe`로 protection level을 검증한다.

```bash
gcloud kms keys describe my-hsm-key \
  --location=asia-northeast3 \
  --keyring=my-keyring
# versionTemplate.protectionLevel: HSM 이 출력되어야 정상
```

---

### 키 자동 교체(Rotation Schedule) 설정

키 생성 시 교체 주기와 다음 교체 시점을 지정하면 Cloud KMS가 자동으로 새 키 버전을 생성한다. 교체가 발생해도 기존 키 버전은 비활성화되지 않는다. 기존 객체 복호화에 이전 버전이 여전히 필요하기 때문이다.

```bash
# 키 생성 시 교체 주기 설정 (90일마다 자동 교체)
gcloud kms keys create my-rotating-key \
  --location=asia-northeast3 \
  --keyring=my-keyring \
  --purpose=encryption \
  --rotation-period=90d \
  --next-rotation-time=2026-10-01T00:00:00Z
```

기존 키에 교체 스케줄을 추가하거나 변경할 때는 `update`를 쓴다.

```bash
gcloud kms keys update my-bucket-key \
  --location=asia-northeast3 \
  --keyring=my-keyring \
  --rotation-period=90d \
  --next-rotation-time=2026-10-01T00:00:00Z
```

교체 주기 설정 후 교체가 발생하면 새 키 버전이 primary로 지정되고, 이후 업로드되는 객체는 새 버전으로 암호화된다. 기존 객체를 새 버전으로 재암호화하려면 `rewrite` API를 별도로 호출해야 한다.

```bash
# 특정 객체를 현재 primary 키 버전으로 재암호화
gsutil rewrite -k gs://my-bucket/existing-file.txt
```

교체 스케줄을 제거하려면 아래 명령을 쓴다.

```bash
gcloud kms keys update my-bucket-key \
  --location=asia-northeast3 \
  --keyring=my-keyring \
  --remove-rotation-schedule
```

---

### 크로스 프로젝트 CMEK

보안 전담 프로젝트에서 KMS 키를 중앙 관리하고, 여러 프로젝트의 GCS 버킷이 그 키를 공유하는 패턴이 있다. 규모가 커질수록 프로젝트별로 키를 따로 만드는 것보다 중앙 관리가 감사 추적에 유리하다.

설정 순서는 명확하다. 사용하는 프로젝트(project-a)의 GCS 서비스 계정에, 키를 소유한 프로젝트(security-project)의 KMS 키 권한을 부여한다.

```bash
# 1. 버킷이 있는 프로젝트의 GCS 서비스 계정 확인
gcloud storage service-agent --project=project-a
# 출력: service-111111111111@gs-project-accounts.iam.gserviceaccount.com

# 2. 키 프로젝트에서 해당 서비스 계정에 권한 부여
gcloud kms keys add-iam-policy-binding central-key \
  --project=security-project \
  --location=asia-northeast3 \
  --keyring=central-keyring \
  --member="serviceAccount:service-111111111111@gs-project-accounts.iam.gserviceaccount.com" \
  --role="roles/cloudkms.cryptoKeyEncrypterDecrypter"

# 3. 버킷에 크로스 프로젝트 키 적용
gcloud storage buckets update gs://project-a-bucket \
  --default-kms-key=projects/security-project/locations/asia-northeast3/keyRings/central-keyring/cryptoKeys/central-key
```

이 패턴의 주의점은 키 프로젝트의 Cloud Audit Logs에 다른 프로젝트 버킷의 암호화/복호화 이벤트가 모두 기록된다는 것이다. 감사 목적으로는 유리하지만, 어느 프로젝트에서 어떤 데이터에 접근했는지 로그를 분리해서 보기 번거로울 수 있다.

---

### 객체 단위 CMEK 오버라이드

버킷에 기본 CMEK가 설정되어 있어도, 개별 객체 업로드 시 다른 키를 지정할 수 있다. 동일 버킷 안에서 데이터 민감도에 따라 키를 분리해야 할 때 쓴다.

```bash
# 버킷 기본 키와 다른 키로 특정 객체 업로드
gcloud storage cp sensitive-file.txt gs://my-bucket/sensitive-file.txt \
  --encryption-key=projects/my-project/locations/asia-northeast3/keyRings/special-keyring/cryptoKeys/high-sensitivity-key
```

객체에 적용된 키는 메타데이터에서 확인한다.

```bash
gcloud storage objects describe gs://my-bucket/sensitive-file.txt \
  --format="get(kmsKeyName)"
```

객체 단위로 키를 오버라이드하면 키 관리 복잡도가 늘어난다. 어떤 객체가 어떤 키로 암호화되어 있는지 추적 체계를 먼저 세우지 않으면, 나중에 키 교체나 비활성화 시 어떤 객체에 영향이 가는지 파악하기 어렵다.

---

### KMS Audit Log 확인

Cloud KMS는 Data Access 감사 로그를 활성화하면 암호화/복호화 작업이 모두 Cloud Audit Logs에 기록된다. 기본적으로 Admin Activity 로그만 켜져 있고, 실제 키 사용 이력을 보려면 Data Access 로그를 별도로 활성화해야 한다.

**Data Access 로그 활성화**

Cloud Console → IAM & Admin → Audit Logs → Cloud Key Management Service API 에서 DATA_READ 로그를 활성화한다.

```bash
# 현재 감사 로그 설정 확인
gcloud projects get-iam-policy my-project \
  --format=json | jq '.auditConfigs'
```

**Logs Explorer 쿼리**

KMS 키를 사용한 복호화 이벤트만 필터링한다.

```
resource.type="cloudkms_cryptokey"
resource.labels.key_ring_id="my-keyring"
resource.labels.crypto_key_id="my-bucket-key"
protoPayload.methodName=~"Decrypt|Encrypt"
```

특정 기간에 GCS 서비스 계정이 키를 사용한 이력만 보고 싶다면 `protoPayload.authenticationInfo.principalEmail`로 필터를 더한다.

```
resource.type="cloudkms_cryptokey"
protoPayload.authenticationInfo.principalEmail="service-111111@gs-project-accounts.iam.gserviceaccount.com"
timestamp>="2026-07-01T00:00:00Z"
```

**gcloud CLI로 로그 조회**

```bash
gcloud logging read \
  'resource.type="cloudkms_cryptokey" AND resource.labels.key_ring_id="my-keyring"' \
  --project=my-project \
  --limit=100 \
  --format=json | jq '.[].protoPayload | {method: .methodName, caller: .authenticationInfo.principalEmail, time: .requestMetadata.requestAttributes.time}'
```

---

### KMS 권한 설정 실수 사례

CMEK를 처음 적용할 때 가장 많이 실패하는 지점이 KMS 권한이다.

**케이스 1: 잘못된 서비스 계정에 권한을 준 경우**

GCS의 KMS 작업은 GCS 내부 서비스 계정(`service-PROJECT_NUMBER@gs-project-accounts.iam.gserviceaccount.com`)이 수행한다. 개발자 본인 계정이나 워크로드 서비스 계정에 권한을 줘도 소용없다.

```bash
# 실제 GCS 서비스 계정 조회
gcloud storage service-agent --project=my-project
```

**케이스 2: KMS 키가 다른 리전에 있는 경우**

버킷이 `asia-northeast3`인데 KMS 키가 `us-central1`에 있으면 CMEK 적용이 거부된다. 버킷 리전과 KMS 키 리전을 일치시키거나, KMS 키를 `global` 리전으로 만들어야 한다.

**케이스 3: 권한 부여 후 전파 지연**

IAM 권한 변경은 최대 2~3분 전파 지연이 있다. 권한을 준 직후 업로드가 실패하면 잠깐 기다렸다가 재시도한다.

---

## EKM — 외부 키 관리자 연동

Cloud EKM(External Key Manager)은 키 자체를 GCP 외부 시스템에 두고, GCP가 암호화 작업이 필요할 때마다 외부 키 서버를 호출하는 방식이다. 키가 GCP 내부에 저장되지 않는다는 것이 핵심이다.

규제상 "암호화 키는 우리 온프레미스 HSM에만 있어야 한다" 또는 "GCP가 키에 물리적으로 접근하면 안 된다"는 요건이 있을 때 사용한다. 실무에서 이런 요건이 생기는 경우는 주로 금융감독원 권고나 특정 B2B 계약 조건이다.

EKM은 두 가지 연결 방식이 있다.

- EXTERNAL: 인터넷을 통해 외부 키 서버(Thales, Fortanix, Futurex, Securosys 등 파트너 시스템)에 연결
- EXTERNAL_VPC: VPC 피어링을 통해 내부 네트워크의 키 서버에 연결

**EKM 연결 생성**

먼저 외부 키 관리 파트너 시스템과 연동 설정을 완료해야 한다. 파트너 시스템에서 서비스 URL, 인증서, API 키를 발급받은 뒤 GCP에 EKM 연결을 만든다.

```bash
# EKM 연결 생성 (인터넷 방식)
gcloud kms ekm-connections create my-ekm-connection \
  --location=asia-northeast3 \
  --service-resolvers=hostname=ekm.example.com,uri-prefix=/v0/kms/,server-certificates-files=server-cert.pem \
  --key-management-mode=MANUAL

# EKM 키 생성 (외부 키 URN은 파트너 시스템에서 발급받은 값)
gcloud kms keys create my-ekm-key \
  --location=asia-northeast3 \
  --keyring=my-keyring \
  --purpose=encryption \
  --protection-level=external \
  --ekm-connection=my-ekm-connection \
  --external-key-uri=https://ekm.example.com/v0/kms/keys/my-key-id
```

EXTERNAL_VPC 방식은 외부 키 서버가 VPC 내부 IP에서 접근 가능할 때 쓴다.

```bash
gcloud kms ekm-connections create my-vpc-ekm-connection \
  --location=asia-northeast3 \
  --service-resolvers=hostname=internal-ekm.example.com,uri-prefix=/v0/kms/,server-certificates-files=server-cert.pem \
  --service-directory-service=projects/my-project/locations/asia-northeast3/namespaces/my-ns/services/ekm-service \
  --key-management-mode=MANUAL

gcloud kms keys create my-vpc-ekm-key \
  --location=asia-northeast3 \
  --keyring=my-keyring \
  --purpose=encryption \
  --protection-level=external_vpc \
  --ekm-connection=my-vpc-ekm-connection \
  --external-key-uri=https://internal-ekm.example.com/v0/kms/keys/my-key-id
```

**EKM의 실질적인 트레이드오프**

외부 키 서버가 다운되면 GCS 데이터 암호화/복호화 자체가 불가능해진다. GCP 서비스 자체는 멀쩡한데 키 서버 장애로 데이터 접근이 막히는 상황이 생길 수 있다. 가용성 요건과 보안 요건 사이에서 판단해야 한다.

EKM 키를 GCS CMEK로 적용하는 방법은 일반 CMEK와 동일하다.

```bash
gcloud storage buckets update gs://my-bucket \
  --default-kms-key=projects/my-project/locations/asia-northeast3/keyRings/my-keyring/cryptoKeys/my-ekm-key
```

---

## CSEK — 고객 제공 암호화 키

키를 Google에 저장하지 않고, 요청마다 직접 전달하는 방식이다. Google은 요청 처리 중에만 키를 메모리에 두고, 완료되면 버린다. 키 분실 시 데이터 복구가 불가능하다.

```bash
# AES-256 키 생성 (32바이트)
openssl rand -base64 32
# 출력 예: xJq3K8+pR2mN7vL9wT5yU6hF0eB1cA4dG=

# CSEK로 파일 업로드
gcloud storage cp local-file.txt gs://my-bucket/file.txt \
  --encryption-key=xJq3K8+pR2mN7vL9wT5yU6hF0eB1cA4dG=

# CSEK로 파일 다운로드
gcloud storage cp gs://my-bucket/file.txt local-copy.txt \
  --decryption-keys=xJq3K8+pR2mN7vL9wT5yU6hF0eB1cA4dG=
```

CSEK의 단점이 명확하다. 모든 API 요청에 키를 포함시켜야 하고, 키 관리 시스템을 직접 구축해야 한다. 잘못 운영하면 키 분실로 데이터가 영구적으로 잠긴다. 실무에서는 규제상 어쩔 수 없는 경우가 아니면 CSEK보다 CMEK(또는 EKM)를 선택한다.

---

## SDK 코드 예제

### Python

```python
from google.cloud import storage

def upload_with_cmek(bucket_name: str, source_file: str, dest_blob: str, kms_key_name: str) -> None:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    # kms_key_name은 키 전체 리소스 이름이어야 함
    # projects/my-project/locations/asia-northeast3/keyRings/my-keyring/cryptoKeys/my-key
    blob = bucket.blob(dest_blob, kms_key_name=kms_key_name)
    blob.upload_from_filename(source_file)

def set_bucket_default_kms_key(bucket_name: str, kms_key_name: str) -> None:
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    bucket.default_kms_key_name = kms_key_name
    bucket.patch()

def get_object_kms_key(bucket_name: str, blob_name: str) -> str | None:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.get_blob(blob_name)
    return blob.kms_key_name if blob else None
```

### Go

```go
package main

import (
    "context"
    "fmt"
    "io"

    "cloud.google.com/go/storage"
)

func uploadWithCMEK(ctx context.Context, bucketName, objectName, kmsKeyName string, r io.Reader) error {
    client, err := storage.NewClient(ctx)
    if err != nil {
        return fmt.Errorf("storage.NewClient: %w", err)
    }
    defer client.Close()

    wc := client.Bucket(bucketName).Object(objectName).NewWriter(ctx)
    wc.KMSKeyName = kmsKeyName
    if _, err = io.Copy(wc, r); err != nil {
        return fmt.Errorf("io.Copy: %w", err)
    }
    return wc.Close()
}

func setBucketDefaultCMEK(ctx context.Context, bucketName, kmsKeyName string) error {
    client, err := storage.NewClient(ctx)
    if err != nil {
        return fmt.Errorf("storage.NewClient: %w", err)
    }
    defer client.Close()

    bucketAttrsToUpdate := storage.BucketAttrsToUpdate{
        Encryption: &storage.BucketEncryption{DefaultKMSKeyName: kmsKeyName},
    }
    _, err = client.Bucket(bucketName).Update(ctx, bucketAttrsToUpdate)
    return err
}
```

### Node.js

```javascript
const {Storage} = require('@google-cloud/storage');

async function uploadWithCMEK(bucketName, filePath, destFileName, kmsKeyName) {
    const storage = new Storage();
    await storage.bucket(bucketName).upload(filePath, {
        destination: destFileName,
        kmsKeyName,
    });
}

async function setBucketDefaultCMEK(bucketName, kmsKeyName) {
    const storage = new Storage();
    await storage.bucket(bucketName).setMetadata({
        encryption: {defaultKmsKeyName: kmsKeyName},
    });
}

async function getObjectKMSKey(bucketName, fileName) {
    const storage = new Storage();
    const [metadata] = await storage.bucket(bucketName).file(fileName).getMetadata();
    return metadata.kmsKeyName ?? null;
}
```

SDK에서 CMEK를 쓸 때 kmsKeyName에 키의 전체 리소스 이름을 넣어야 한다. 키 이름만 넣으면 `INVALID_ARGUMENT` 오류가 발생한다.

---

## 키 교체와 비활성화 시 주의사항

### CMEK 키 교체

KMS에서 키 버전을 교체(rotate)하면 이후 새로 업로드되는 객체는 새 키 버전으로 암호화된다. **기존 객체는 이전 키 버전으로 암호화된 상태 그대로 남는다.**

기존 객체를 새 키 버전으로 재암호화하려면 객체를 다시 쓰거나, `rewrite` API를 호출해야 한다.

```bash
# 객체 재암호화 (gsutil 사용)
gsutil rewrite -k gs://my-bucket/existing-file.txt
```

### 키 비활성화 시 발생하는 문제

KMS 키를 비활성화(disable)하거나 삭제하면 해당 키로 암호화된 객체에 접근이 불가능해진다. 읽기, 복사, 삭제 모두 안 된다.

```
Error: google.api_core.exceptions.PermissionDenied: 403 PERMISSION_DENIED: 
Cloud KMS key is disabled, destroyed, or scheduled for destruction
```

실제로 이 문제를 겪는 경우가 있다. 보안 감사 후 "더 이상 안 쓰는 키 정리"를 지시받아 KMS 키를 비활성화했는데, 그 키로 암호화된 GCS 버킷 데이터 전체가 접근 불가 상태가 된 사례다.

키를 비활성화하기 전에 반드시 확인해야 할 것들이 있다. 해당 키를 기본 CMEK로 쓰는 버킷 목록을 조회하고, 그 버킷에 접근하는 서비스나 파이프라인이 현재도 동작 중인지 확인하고, 데이터를 다른 키로 재암호화하거나 백업한 뒤에 비활성화한다.

```bash
# 특정 키를 사용하는 리소스 확인
gcloud kms keys get-iam-policy my-bucket-key \
  --location=asia-northeast3 \
  --keyring=my-keyring

# 키 비활성화 (복구 가능)
gcloud kms keys versions disable 1 \
  --location=asia-northeast3 \
  --keyring=my-keyring \
  --key=my-bucket-key

# 키 삭제 예약 (30일 후 삭제, 복구 불가)
gcloud kms keys versions destroy 1 \
  --location=asia-northeast3 \
  --keyring=my-keyring \
  --key=my-bucket-key
```

`disable`은 복구가 가능하다. `destroy`로 삭제 예약하면 기본 30일 뒤 영구 삭제되고, 그 시점 이후에는 데이터 복구 방법이 없다.

---

## 실무 적용 기준

**GMEK로 충분한 경우**
- 내부 운영 데이터, 로그, 개발/스테이징 환경
- 키 관리 부담을 최소화하고 싶을 때
- 규제 요건이 없을 때

**CMEK를 써야 하는 경우**
- 개인정보보호법, HIPAA, PCI-DSS 등 규제 대상 데이터
- 키 접근 로그(Cloud Audit Logs)가 필요할 때
- 특정 사유로 데이터 접근을 즉시 차단해야 하는 시나리오 (키 비활성화로 전체 접근 차단)
- 여러 프로젝트가 하나의 키를 공유해야 할 때

**Cloud HSM을 추가로 선택하는 경우**
- FIPS 140-2 Level 3 인증이 명시적으로 요구될 때
- PCI-DSS 준수 환경에서 감사인이 HSM 증거를 요구할 때

**EKM을 선택하는 경우**
- 키가 GCP 외부에 있어야 한다는 규제 또는 계약 요건이 있을 때
- 기존 온프레미스 HSM 인프라를 GCS 암호화에 연결해야 할 때
- 외부 키 서버 가용성이 충분히 높다고 판단될 때

**CSEK는 피하는 경우가 대부분**
- 키를 요청마다 전달해야 하므로 관리 복잡도가 높다
- CMEK로 충족 가능한 요건이면 CSEK를 쓸 이유가 없다
- 온프레미스 HSM과 GCS를 직접 연동해야 하는 특수한 상황에서만 고려한다

CMEK 도입 시 처음부터 키 교체 정책과 키 폐기 절차를 문서화해 둬야 한다. 나중에 "이 키 언제 만든 거야, 어떤 데이터에 쓰이고 있어?"를 추적하는 게 생각보다 어렵다. 자동 교체 스케줄을 설정해 두면 관리 부담이 줄지만, 교체 후 기존 객체 재암호화 여부는 별도 정책으로 결정해야 한다.
