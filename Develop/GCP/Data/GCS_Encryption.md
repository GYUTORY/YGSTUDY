---
title: GCS 암호화
tags: ["GCP", "Cloud Storage", "Encryption", "CMEK", "CSEK", "KMS", "Security"]
updated: 2026-07-26
---

# GCS 암호화

GCS는 저장된 모든 데이터를 기본적으로 암호화한다. 암호화 방식은 세 가지인데, 키를 누가 관리하느냐에 따라 나뉜다.

## 암호화 방식 비교

| 방식 | 키 관리 주체 | 키 저장 위치 | 주요 제약 |
|------|-------------|-------------|----------|
| Google 관리 암호화 (GMEK) | Google | Google 내부 KMS | 키 제어 불가 |
| 고객 관리 암호화 키 (CMEK) | 고객 (Cloud KMS 경유) | Cloud KMS | KMS 권한 설정 필요 |
| 고객 제공 암호화 키 (CSEK) | 고객 | 고객 시스템 | 요청마다 키 직접 전달 |

---

## Google 관리 암호화 (GMEK)

별도 설정 없이 자동 적용된다. AES-256으로 데이터를 암호화하고, 봉투 암호화(Envelope Encryption) 방식으로 키를 보호한다. 키 교체도 Google이 알아서 한다.

규제 요건이 없고, 키 관리 부담을 줄이고 싶을 때 쓴다. 대부분의 서비스에서 이걸로 충분하다.

---

## CMEK — Cloud KMS 연동

고객이 Cloud KMS에서 직접 키를 만들어 GCS 버킷에 연결하는 방식이다. 키 교체 주기 설정, 키 비활성화, 감사 로그 확인이 가능하다.

금융권이나 의료 데이터처럼 "우리 회사가 키를 통제한다"는 걸 증명해야 하는 상황에서 사용한다.

### 설정 방법

**1. KMS 키링과 키 생성**

```bash
# 키링 생성
gcloud kms keyrings create my-keyring \
  --location=asia-northeast3

# 키 생성
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

### KMS 권한 설정 실수 사례

CMEK를 처음 적용할 때 가장 많이 실패하는 지점이 KMS 권한이다.

**케이스 1: 잘못된 서비스 계정에 권한을 준 경우**

GCS의 KMS 작업은 GCS 내부 서비스 계정(`service-PROJECT_NUMBER@gs-project-accounts.iam.gserviceaccount.com`)이 수행한다. 개발자 본인 계정이나 워크로드 서비스 계정에 권한을 줘도 소용없다.

확인 방법:
```bash
# 실제 GCS 서비스 계정 조회
gcloud storage service-agent --project=my-project
```

**케이스 2: KMS 키가 다른 리전에 있는 경우**

버킷이 `asia-northeast3`인데 KMS 키가 `us-central1`에 있으면 CMEK 적용이 거부된다. 버킷 리전과 KMS 키 리전을 일치시키거나, KMS 키를 `global` 리전으로 만들어야 한다.

**케이스 3: 권한 부여 후 전파 지연**

IAM 권한 변경은 최대 2~3분 전파 지연이 있다. 권한을 준 직후 업로드가 실패하면 잠깐 기다렸다가 재시도한다.

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

CSEK의 단점이 명확하다. 모든 API 요청에 키를 포함시켜야 하고, 키 관리 시스템을 직접 구축해야 한다. 잘못 운영하면 키 분실로 데이터가 영구적으로 잠긴다. 실무에서는 규제상 어쩔 수 없는 경우가 아니면 CSEK보다 CMEK를 선택한다.

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

키를 비활성화하기 전에 반드시 확인해야 할 것들:

1. 해당 키를 기본 CMEK로 쓰는 버킷 목록 조회
2. 그 버킷에 접근하는 서비스나 파이프라인이 현재도 동작 중인지 확인
3. 데이터를 다른 키로 재암호화하거나 백업한 뒤에 비활성화

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
- 다른 프로젝트의 서비스가 버킷 데이터에 접근해야 할 때

**CSEK는 피하는 경우가 대부분**
- 키를 요청마다 전달해야 하므로 관리 복잡도가 높다
- CMEK로 충족 가능한 요건이면 CSEK를 쓸 이유가 없다
- 온프레미스 HSM과 GCS를 연동해야 하는 특수한 상황에서만 고려한다

CMEK 도입 시 처음부터 키 교체 정책과 키 폐기 절차를 문서화해 둬야 한다. 나중에 "이 키 언제 만든 거야, 어떤 데이터에 쓰이고 있어?"를 추적하는 게 생각보다 어렵다.
