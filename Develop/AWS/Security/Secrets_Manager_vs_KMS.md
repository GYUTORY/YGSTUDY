---
title: Secrets Manager vs KMS — 뭘 써야 하나
tags: [aws, security, kms, secretsmanager, ssm, encryption]
updated: 2026-04-06
---

# Secrets Manager vs KMS — 뭘 써야 하나

AWS 보안 서비스를 처음 접하면 Secrets Manager, KMS, SSM Parameter Store가 비슷해 보인다. 셋 다 "민감한 값을 저장하는 서비스"로 오해하기 쉬운데, 실제로는 역할이 다르다. 이 문서에서는 각 서비스의 본질적인 차이와 실무에서 어떤 상황에 어떤 서비스를 쓰는지 정리한다.

---

## 역할부터 구분하자

### KMS — 암호화 키를 관리하는 서비스

KMS는 데이터를 직접 저장하지 않는다. 암호화/복호화에 쓰이는 "키"를 만들고, 그 키를 HSM(Hardware Security Module) 안에 보관하고, 키를 써서 암호화·복호화 API를 제공하는 서비스다.

S3에 파일을 올릴 때 SSE-KMS를 켜면, S3가 KMS에게 "이 키로 암호화해줘"라고 요청한다. EBS 볼륨 암호화도 마찬가지다. KMS는 직접 데이터를 갖고 있지 않고, 키만 관리한다.

핵심: **"데이터를 암호화하는 열쇠를 관리하는 금고"**

### Secrets Manager — 비밀 값을 저장하고 수명주기를 관리하는 서비스

Secrets Manager는 DB 비밀번호, API 키, OAuth 토큰 같은 실제 비밀 값을 저장한다. 저장할 때 내부적으로 KMS를 써서 암호화한다. 여기서 핵심은 자동 로테이션이다. Lambda를 연결해서 DB 비밀번호를 30일마다 자동으로 바꾸고, 애플리케이션은 항상 최신 값을 가져가는 구조를 만들 수 있다.

핵심: **"비밀번호를 넣어두고 알아서 바꿔주는 비서"**

### SSM Parameter Store — 설정값을 저장하는 서비스

Parameter Store는 Secrets Manager보다 범용적이다. 암호화가 필요 없는 일반 설정값(`String` 타입)도 저장하고, 암호화가 필요한 값(`SecureString` 타입)도 저장한다. SecureString은 내부적으로 KMS를 쓴다.

핵심: **"환경변수 저장소. 필요하면 암호화도 해줌"**

---

## 세 서비스의 관계

```
┌──────────────────────────────────────────────────┐
│                  애플리케이션                       │
│                                                    │
│   DB 비밀번호 필요 → Secrets Manager에서 조회       │
│   설정값 필요     → Parameter Store에서 조회        │
└────────────┬───────────────────────┬───────────────┘
             │                       │
             ▼                       ▼
   ┌─────────────────┐    ┌──────────────────┐
   │ Secrets Manager  │    │ Parameter Store   │
   │ (비밀 값 저장)    │    │ (설정값 저장)      │
   │ + 자동 로테이션   │    │ + SecureString    │
   └────────┬─────────┘    └────────┬──────────┘
            │                       │
            │  암호화 요청            │  SecureString 암호화 요청
            ▼                       ▼
         ┌─────────────────────────────┐
         │           KMS               │
         │  (암호화 키 생성/관리/사용)    │
         │  HSM 내부에 키 보관           │
         └─────────────────────────────┘
```

Secrets Manager와 Parameter Store 둘 다 KMS를 "내부 엔진"으로 사용한다. KMS는 이 둘과 독립적으로도 동작하며, S3·EBS·RDS 등 수십 개 AWS 서비스의 암호화를 담당한다.

---

## 3자 비교

| 항목 | KMS | Secrets Manager | SSM Parameter Store |
|------|-----|-----------------|---------------------|
| **본질** | 암호화 키 관리 | 비밀 값 저장 + 수명주기 관리 | 설정값/비밀 값 저장 |
| **저장 대상** | 키만 저장 (데이터 저장 안 함) | DB 비밀번호, API 키, 토큰 | 설정값, 비밀번호, 연결 문자열 |
| **암호화** | 암호화 자체를 수행 | KMS로 암호화 (항상) | KMS로 암호화 (SecureString만) |
| **자동 로테이션** | 키 자동 로테이션 (1년 주기) | Lambda 기반 시크릿 로테이션 | 미지원 |
| **값 크기 제한** | 4KB (직접 암호화) | 64KB | 8KB (Advanced) / 4KB (Standard) |
| **버전 관리** | 키 로테이션 시 자동 버전 관리 | AWSCURRENT, AWSPREVIOUS 레이블 | 미지원 (덮어쓰기) |
| **계층 구조** | 키 별칭(alias) | 이름에 `/`로 경로 구분 | 이름에 `/`로 경로 구분 |
| **Cross-account 접근** | 키 정책으로 가능 | 리소스 정책으로 가능 | 미지원 |
| **CloudFormation 연동** | 지원 | 지원 | Dynamic Reference 지원 |

---

## Envelope Encryption — 두 서비스가 맞물리는 지점

실무에서 KMS와 Secrets Manager(또는 다른 서비스)가 가장 밀접하게 연동되는 부분이 Envelope Encryption이다. 이 패턴을 이해해야 KMS 비용 구조와 성능 특성이 납득된다.

### 왜 Envelope Encryption이 필요한가

KMS API로 직접 암호화할 수 있는 데이터 크기는 **4KB**다. DB에 들어갈 고객 정보, S3에 올릴 파일은 4KB를 훌쩍 넘는다. 그래서 KMS는 "데이터 키"를 만들어주고, 실제 데이터 암호화는 애플리케이션이 직접 한다.

### 동작 흐름

```
1. 앱 → KMS: "CMK(마스터 키)로 데이터 키 하나 만들어줘" (GenerateDataKey)

2. KMS → 앱: 두 가지를 돌려줌
   - 평문 데이터 키 (Plaintext Data Key)
   - CMK로 암호화된 데이터 키 (Encrypted Data Key)

3. 앱: 평문 데이터 키로 실제 데이터를 AES-256 암호화

4. 앱: 암호화된 데이터 + 암호화된 데이터 키를 함께 저장
   (평문 데이터 키는 메모리에서 즉시 삭제)

5. 복호화 시:
   앱 → KMS: "이 암호화된 데이터 키를 복호화해줘" (Decrypt)
   KMS → 앱: 평문 데이터 키 반환
   앱: 평문 데이터 키로 데이터 복호화
```

이 구조에서 KMS API를 호출하는 횟수는 암호화할 때 1번(GenerateDataKey), 복호화할 때 1번(Decrypt)이다. 100MB 파일이든 1GB 파일이든 KMS 호출은 동일하다. KMS 호출 비용과 네트워크 지연을 최소화하면서도 HSM 수준의 키 보호를 받는 구조다.

### Secrets Manager 내부에서도 같은 일이 일어난다

시크릿을 저장할 때:
1. Secrets Manager가 KMS에 `GenerateDataKey` 요청
2. 받은 평문 데이터 키로 시크릿 값을 암호화
3. 암호화된 시크릿 + 암호화된 데이터 키를 저장
4. 평문 데이터 키 삭제

시크릿을 조회할 때:
1. 암호화된 데이터 키를 KMS에 `Decrypt` 요청
2. 받은 평문 데이터 키로 시크릿을 복호화
3. 복호화된 값을 애플리케이션에 반환

즉, `GetSecretValue` API를 호출할 때마다 내부적으로 KMS API가 한 번 호출된다. Secrets Manager 비용과 별도로 KMS 요청 비용이 쌓이는 이유가 여기 있다.

---

## 비용 비교

### 월 고정 비용

| 항목 | KMS | Secrets Manager | Parameter Store |
|------|-----|-----------------|-----------------|
| 보관 비용 | CMK당 $1/월 | 시크릿당 $0.40/월 | Standard: 무료 / Advanced: 파라미터당 $0.05/월 |

### API 호출 비용

| 항목 | KMS | Secrets Manager | Parameter Store |
|------|-----|-----------------|-----------------|
| 호출 비용 | 10,000건당 $0.03 | 10,000건당 $0.05 | Standard: 무료 / Advanced: 10,000건당 $0.05 |
| 무료 제공량 | 월 20,000건 | 없음 | Standard는 무료 |

### 실제 비용 계산 예시

DB 비밀번호 1개를 관리하는 경우를 생각해보자.

**Secrets Manager 사용 시:**
- 시크릿 1개 보관: $0.40/월
- 하루 1,000번 조회 × 30일 = 30,000건: $0.15/월
- 내부 KMS 호출 30,000건: $0.09/월 (20,000건 무료 차감 후)
- **합계: 약 $0.64/월**

**Parameter Store SecureString 사용 시:**
- Standard 파라미터 보관: 무료
- API 호출: 무료 (Standard 기준)
- 내부 KMS 호출 30,000건: $0.03/월 (무료 제공량 차감 후)
- **합계: 약 $0.03/월**

비용 차이가 20배다. 단, Parameter Store는 자동 로테이션이 없고, 버전 관리도 안 되고, Cross-account 공유도 안 된다. 비용만 보고 선택하면 안 되는 이유다.

---

## 실무 판단 기준

### Secrets Manager를 써야 하는 경우

**자동 로테이션이 필요할 때** — RDS 비밀번호를 30일마다 바꿔야 하는 컴플라이언스 요건이 있다면, Secrets Manager 외에 선택지가 없다. Lambda 기반 로테이션을 직접 구현할 수도 있지만, AWS가 제공하는 RDS/Aurora/Redshift용 로테이션 템플릿을 쓰면 검증된 방식으로 처리된다.

**Cross-account 시크릿 공유가 필요할 때** — 여러 AWS 계정에서 같은 시크릿에 접근해야 하는 경우. Parameter Store는 이걸 지원하지 않는다.

**시크릿 버전 관리가 필요할 때** — 로테이션 후 이전 값으로 롤백해야 하는 상황. `AWSCURRENT`, `AWSPREVIOUS` 레이블로 관리된다.

### Parameter Store SecureString을 써야 하는 경우

**비용에 민감한 환경** — 개발·스테이징 환경에서 DB 비밀번호를 저장하는데 자동 로테이션까지 필요하진 않은 경우. Standard 티어는 무료다.

**설정값과 시크릿을 한 곳에서 관리하고 싶을 때** — 서비스 설정값(`/app/config/max-retry`)과 비밀 값(`/app/secret/db-password`)을 같은 인터페이스로 관리하면 코드가 단순해진다.

**ECS/Lambda 환경변수 주입** — ECS Task Definition이나 CloudFormation에서 Parameter Store 값을 직접 참조하는 패턴이 많다. `{{resolve:ssm:/path/to/param}}` 같은 Dynamic Reference를 쓰면 배포 시점에 값이 주입된다.

### KMS를 직접 써야 하는 경우

**애플리케이션 레벨 암호화가 필요할 때** — DB 컬럼 단위로 암호화하거나, 파일을 암호화해서 S3에 올리는 경우. Secrets Manager는 "값을 저장하는 서비스"지 "데이터를 암호화하는 서비스"가 아니다.

**서명·검증이 필요할 때** — 비대칭 키(RSA/ECC)로 JWT 서명하거나, 메시지 무결성을 검증하는 경우.

**AWS 서비스의 서버사이드 암호화 커스터마이징** — S3 SSE-KMS, EBS 암호화 등에서 AWS 관리형 키 대신 자체 키를 써서 키 정책을 세밀하게 제어하고 싶을 때.

---

## 흔한 실수

### "KMS에 비밀번호를 저장하면 되지 않나?"

KMS는 데이터 저장소가 아니다. `Encrypt` API에 평문을 넘기면 암호문을 돌려주는데, 그 암호문을 어딘가에 저장해야 한다. 결국 S3든 DynamoDB든 저장소가 필요하다. 그러느니 Secrets Manager를 쓰는 게 맞다.

다만, 아주 단순한 경우 — 예를 들어 환경변수 하나를 KMS로 암호화해서 Lambda 환경변수에 넣어두고, 런타임에 복호화해서 쓰는 패턴은 있다. Secrets Manager API 호출 비용을 아끼면서 단순하게 처리할 때 쓸 수 있다.

### "Parameter Store가 무료니까 다 여기에 넣자"

Standard 티어는 파라미터 10,000개까지, 각 4KB까지 저장 가능하다. API 호출 TPS(초당 처리량)가 낮다 — Standard는 40 TPS, Advanced로 올려도 1,000 TPS다. 트래픽이 높은 서비스에서 매 요청마다 Parameter Store를 호출하면 스로틀링에 걸릴 수 있다. 캐싱 없이 쓰면 문제가 된다.

### "Secrets Manager와 Parameter Store를 혼용하면 복잡해진다"

오히려 실무에서는 혼용하는 게 자연스럽다. 자동 로테이션이 필요한 DB 비밀번호는 Secrets Manager에, 나머지 설정값과 단순 시크릿은 Parameter Store에 넣는 패턴이 일반적이다. 코드에서 두 서비스를 호출하는 건 SDK 한 줄 차이다.

---

## 조합 패턴 예시

### 패턴 1: RDS + Secrets Manager + KMS

```
Secrets Manager
  └─ prod/myapp/db-credentials (JSON: username, password, host, port)
       └─ 암호화: 고객 관리형 CMK (alias/myapp/secrets)
       └─ 로테이션: 30일, AWS 제공 Lambda 템플릿

RDS
  └─ 저장 데이터 암호화: 고객 관리형 CMK (alias/myapp/rds)
```

DB 접속 정보와 DB 저장 데이터를 각각 다른 CMK로 암호화하는 건 권한 분리 관점에서 좋은 습관이다. Secrets Manager에 접근할 수 있는 역할과 RDS 데이터를 복호화할 수 있는 역할을 분리할 수 있다.

### 패턴 2: ECS + Parameter Store + Secrets Manager

```python
# ECS Task Definition (Terraform)
container_definitions = jsonencode([{
  name = "myapp"
  secrets = [
    {
      # Secrets Manager에서 DB 비밀번호 주입
      name      = "DB_PASSWORD"
      valueFrom = "arn:aws:secretsmanager:ap-northeast-2:123456:secret:prod/db-password"
    },
    {
      # Parameter Store에서 설정값 주입
      name      = "API_ENDPOINT"
      valueFrom = "arn:aws:ssm:ap-northeast-2:123456:parameter/prod/api-endpoint"
    }
  ]
}])
```

ECS는 `secrets` 블록에서 Secrets Manager와 Parameter Store 값을 모두 주입할 수 있다. ARN 형식만 다르고 사용법은 동일하다.

### 패턴 3: 애플리케이션 레벨 Envelope Encryption

```python
import boto3
from cryptography.fernet import Fernet
import base64

kms = boto3.client('kms', region_name='ap-northeast-2')
CMK_ID = 'alias/myapp/data-encryption'

def encrypt_pii(plaintext: str) -> dict:
    """고객 PII를 Envelope Encryption으로 암호화"""
    # KMS에서 데이터 키 생성
    response = kms.generate_data_key(
        KeyId=CMK_ID,
        KeySpec='AES_256'
    )

    # 평문 데이터 키로 실제 데이터 암호화
    data_key = base64.urlsafe_b64encode(response['Plaintext'])
    f = Fernet(data_key)
    encrypted = f.encrypt(plaintext.encode())

    return {
        'encrypted_data': encrypted.decode(),
        'encrypted_key': base64.b64encode(response['CiphertextBlob']).decode()
    }
    # 평문 데이터 키는 이 함수가 끝나면 GC 대상


def decrypt_pii(encrypted_data: str, encrypted_key: str) -> str:
    """암호화된 PII 복호화"""
    # KMS에서 데이터 키 복호화
    response = kms.decrypt(
        CiphertextBlob=base64.b64decode(encrypted_key)
    )

    data_key = base64.urlsafe_b64encode(response['Plaintext'])
    f = Fernet(data_key)
    return f.decrypt(encrypted_data.encode()).decode()
```

이 패턴에서 KMS API 호출은 암호화·복호화 각 1회뿐이다. 데이터가 아무리 커도 KMS 비용은 같다.

---

## 정리

| 하고 싶은 일 | 쓸 서비스 |
|-------------|----------|
| DB 비밀번호를 저장하고 자동으로 바꾸고 싶다 | Secrets Manager |
| 애플리케이션 설정값을 중앙에서 관리하고 싶다 | Parameter Store |
| 비밀번호를 저장하는데 로테이션은 필요 없고 비용을 아끼고 싶다 | Parameter Store SecureString |
| S3/EBS/RDS 데이터를 암호화하고 싶다 | KMS (서비스 연동) |
| 애플리케이션에서 직접 데이터를 암호화하고 싶다 | KMS (Envelope Encryption) |
| JWT 서명/검증이 필요하다 | KMS (비대칭 키) |
| 여러 계정에서 같은 비밀번호를 공유해야 한다 | Secrets Manager |

세 서비스는 경쟁 관계가 아니라 레이어가 다르다. KMS가 바닥에 깔려 있고, 그 위에 Secrets Manager와 Parameter Store가 각자의 역할로 올라가 있다. 이 구조를 이해하면 어떤 상황에 뭘 써야 하는지 자연스럽게 판단할 수 있다.

---

## 관련 문서

- [KMS](./KMS.md) — KMS 상세 개념과 키 관리
- [Secrets Manager](./Secrets_Manager.md) — Secrets Manager 상세 기능과 로테이션
- [IAM](./IAM.md) — 서비스별 접근 권한 설계
