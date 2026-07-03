---
title: HashiCorp Vault
tags:
  - infra
  - secrets
  - security
  - vault
  - kubernetes
updated: 2026-06-03
---

# HashiCorp Vault

## Vault를 도입하는 이유

서비스가 작을 땐 `.env` 파일에 DB 비밀번호 넣고 git에 안 올리는 걸로 충분했다. 그런데 마이크로서비스가 10개를 넘기고, 개발/스테이징/프로덕션 환경이 분리되고, 신입이 들어와서 자격증명을 받아가는 일이 생기면 상황이 달라진다. 누가 어떤 비밀을 봤는지, 누가 회전시켰는지, 회전 후 모든 서비스가 새 자격증명을 받았는지 추적이 안 된다. 결국 누군가 슬랙 DM으로 비밀번호를 공유하고, 그 메시지가 영원히 남는다.

Vault는 이 문제를 풀려는 도구다. 모든 시크릿을 한 곳에 모으고, 접근은 토큰 기반으로 제어하며, 누가 언제 무엇을 읽었는지 audit log로 남긴다. 더 나아가 정적 시크릿이 아니라 요청 시점에 동적으로 발급해서 짧은 수명만 가지게 만들 수 있다.

직접 운영해보면 알게 되는 사실은 Vault 자체가 또 하나의 운영 대상이라는 점이다. 클러스터 구성, unseal 절차, audit 백엔드 관리, 토큰 만료 처리. 처음 도입할 땐 "비밀번호 저장소 하나 띄우면 되는 거 아니냐"라고 생각했다가 실제로 운영하면서 데이고 나서야 진지하게 다루게 된다.

## Secret Engine의 종류와 선택

Vault의 시크릿 엔진은 경로 단위로 마운트된다. `secret/`이라는 경로에 KV 엔진이 붙어있고, `database/`에 데이터베이스 엔진이 붙는 식이다. 각 엔진은 독립적으로 동작하므로 같은 Vault 인스턴스에 여러 엔진을 동시에 마운트할 수 있다.

### KV Secret Engine

가장 기본이 되는 정적 시크릿 저장소다. 키-값 쌍을 저장하고 읽는다. v1과 v2가 있는데, v2는 버전 관리와 소프트 삭제를 지원한다. 신규 도입이면 무조건 v2를 쓴다. 잘못 덮어썼을 때 이전 버전으로 복구할 수 있는 게 운영에서 의외로 자주 도움이 된다.

```bash
# KV v2 마운트
vault secrets enable -path=secret -version=2 kv

# 시크릿 저장
vault kv put secret/myapp/prod \
  db_password=verysecret \
  api_key=xxxxx

# 시크릿 읽기
vault kv get secret/myapp/prod

# 특정 버전 읽기 (실수로 덮어썼을 때)
vault kv get -version=3 secret/myapp/prod

# 메타데이터 조회 (버전 히스토리)
vault kv metadata get secret/myapp/prod
```

KV 엔진의 한계는 명확하다. 저장된 값을 누군가 꺼내가면 그 값은 그 사람의 손에 있는 것이다. Vault가 회수하지 못한다. 그래서 사람이 직접 다루는 시크릿(외부 API 키, OAuth 클라이언트 시크릿)에만 쓰고, 자동화된 서비스 자격증명에는 동적 엔진을 쓰는 게 정석이다.

### Database Secret Engine

DB 자격증명을 요청 시점에 발급하고, TTL이 끝나면 자동으로 삭제한다. 정적 비밀번호를 영원히 들고 있는 대신, 30분짜리 임시 계정을 매번 새로 받는 모델이다.

```bash
# Database 엔진 마운트
vault secrets enable database

# PostgreSQL 연결 설정
vault write database/config/myapp-postgres \
  plugin_name=postgresql-database-plugin \
  allowed_roles="readonly,readwrite" \
  connection_url="postgresql://{{username}}:{{password}}@db.internal:5432/myapp?sslmode=disable" \
  username="vault_admin" \
  password="admin_password"

# 역할 정의 — 발급될 계정의 권한과 TTL
vault write database/roles/readonly \
  db_name=myapp-postgres \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
  default_ttl="1h" \
  max_ttl="24h"

# 자격증명 발급
vault read database/creds/readonly
```

이 방식의 가장 큰 이점은 회전을 별도로 신경 쓸 필요가 없다는 거다. 30분 후 자동으로 만료되니까. 다만 운영해보면 함정이 몇 개 있다. PostgreSQL의 경우 발급 계정 이름은 `v-token-readonly-XXX` 형태인데, 길이 제한(63자)에 걸리기 쉽다. 역할 이름이 너무 길면 truncate되어 발급 자체가 실패한다. 또 connection pool을 쓰는 애플리케이션은 TTL 만료 시점에 들고 있던 커넥션이 한꺼번에 끊기는 문제가 있다. 그래서 lease 갱신 로직을 따로 구현해야 한다.

Vault Admin 계정도 따로 관리해야 한다. Vault가 새 계정을 만들 때 쓸 마스터 계정인데, 이걸 Vault 안에 같이 넣어두면 닭과 달걀 문제가 생긴다. 별도 secret store(예: AWS Secrets Manager의 부트스트랩 비밀)에 두고 Vault가 시작할 때만 읽는 식으로 분리한다.

### Transit Secret Engine

Transit은 시크릿을 저장하지 않는다. 암호화/복호화 기능만 제공한다. 키는 Vault 안에 보관되고, 평문 데이터는 Vault로 보내서 암호문을 받거나, 암호문을 보내서 평문을 받는다.

```bash
vault secrets enable transit

# 암호화 키 생성
vault write -f transit/keys/myapp-key

# 암호화 (Base64로 인코딩된 평문 전송)
vault write transit/encrypt/myapp-key \
  plaintext=$(echo -n "주민번호1234567" | base64)
# 응답: ciphertext: vault:v1:abc123...

# 복호화
vault write transit/decrypt/myapp-key \
  ciphertext="vault:v1:abc123..."

# 키 회전
vault write -f transit/keys/myapp-key/rotate
```

ciphertext 앞에 붙은 `v1`이 키 버전이다. 회전하면 `v2`가 되고, 새 데이터는 `v2`로 암호화된다. 그런데 DB에 이미 저장된 `v1` 암호문도 Vault가 여전히 복호화해준다. 키 회전을 해도 데이터를 다시 암호화할 필요가 없다는 게 Transit의 핵심이다.

실무에서 Transit을 쓰는 전형적인 패턴이 envelope encryption이다. 큰 데이터를 Vault로 직접 보내면 네트워크 비용이 크니까, 애플리케이션에서 임시 데이터 키로 데이터를 암호화하고, 그 데이터 키만 Vault로 보내서 암호화한다. 복호화할 때는 반대로 데이터 키를 먼저 복호화한 다음 그걸로 데이터를 푼다.

```python
# Envelope encryption 예제 (의사 코드)
import os
from cryptography.fernet import Fernet

def encrypt_large_data(plaintext: bytes):
    # 1. 데이터 키 생성 (애플리케이션 메모리에서만 존재)
    data_key = Fernet.generate_key()

    # 2. 데이터 키로 평문 암호화 (로컬 연산)
    cipher = Fernet(data_key)
    encrypted_data = cipher.encrypt(plaintext)

    # 3. 데이터 키 자체는 Vault로 암호화
    response = vault_client.secrets.transit.encrypt_data(
        name='myapp-key',
        plaintext=base64.b64encode(data_key).decode()
    )
    encrypted_data_key = response['data']['ciphertext']

    # 4. 암호화된 데이터와 암호화된 데이터 키를 함께 저장
    return {
        'data': encrypted_data,
        'wrapped_key': encrypted_data_key
    }

def decrypt_large_data(envelope):
    # 1. 데이터 키 복호화
    response = vault_client.secrets.transit.decrypt_data(
        name='myapp-key',
        ciphertext=envelope['wrapped_key']
    )
    data_key = base64.b64decode(response['data']['plaintext'])

    # 2. 복호화된 데이터 키로 본문 복호화 (로컬)
    cipher = Fernet(data_key)
    return cipher.decrypt(envelope['data'])
```

이 패턴의 장점은 명확하다. 데이터 크기가 100MB여도 Vault로는 32바이트 데이터 키만 오간다. 단점은 데이터 키를 함께 저장해야 해서 스키마가 살짝 복잡해진다.

세 엔진을 어떻게 골라 쓰는지 정리하면, 사람이 직접 다루는 정적 값(외부 API 키, TLS 인증서 같이 회전 빈도가 낮은 것)은 KV. 애플리케이션이 자동으로 받아 쓰는 자격증명(DB, RabbitMQ, AWS IAM)은 동적 엔진. 데이터 자체를 암호화해서 저장해야 할 때(개인정보, 결제 정보)는 Transit이다.

## 동적 시크릿과 자격증명 자동 회전

정적 비밀번호의 문제는 누군가 한 번 보면 영원히 유효하다는 거다. 사람이 회사를 떠나도, 노트북을 잃어버려도, 회수할 방법이 없다. 동적 시크릿은 매번 새 자격증명을 받고, 짧은 TTL을 두어 자동 만료시킨다.

```bash
# DB 자격증명 발급 요청
curl -X GET \
  -H "X-Vault-Token: $VAULT_TOKEN" \
  https://vault.internal:8200/v1/database/creds/readonly

# 응답
{
  "lease_id": "database/creds/readonly/abc123",
  "lease_duration": 3600,
  "renewable": true,
  "data": {
    "username": "v-token-readonly-abc123-1717392000",
    "password": "A1b2C3d4-randomly-generated"
  }
}
```

발급된 lease는 갱신할 수 있다. `vault lease renew database/creds/readonly/abc123`을 호출하면 TTL이 다시 늘어난다. 다만 `max_ttl`을 넘기지 못한다. 24시간이 max_ttl이면 그 시점에 강제로 회수되고, 애플리케이션은 새 자격증명을 받아야 한다.

여기서 자주 하는 실수가 lease 갱신 로직을 누락하는 거다. 처음 발급받고 그대로 1시간 후 lease가 만료되면 DB 연결이 실패한다. 보통 TTL의 2/3 지점쯤에 갱신을 시도하도록 백그라운드 워커를 둔다.

```python
# Lease 갱신 워커 예제
import threading
import time

class VaultDBCreds:
    def __init__(self, vault_client, role='readonly'):
        self.client = vault_client
        self.role = role
        self.creds = None
        self.lease_id = None
        self.lease_duration = 0
        self.lock = threading.Lock()
        self._fetch()
        threading.Thread(target=self._renew_loop, daemon=True).start()

    def _fetch(self):
        resp = self.client.secrets.database.generate_credentials(name=self.role)
        with self.lock:
            self.creds = (resp['data']['username'], resp['data']['password'])
            self.lease_id = resp['lease_id']
            self.lease_duration = resp['lease_duration']

    def _renew_loop(self):
        while True:
            # TTL의 2/3 지점에서 갱신 시도
            time.sleep(self.lease_duration * 2 / 3)
            try:
                resp = self.client.sys.renew_lease(self.lease_id)
                self.lease_duration = resp['lease_duration']
            except Exception:
                # max_ttl 초과 등으로 갱신 실패 시 재발급
                self._fetch()
```

실제 운영에서는 이 정도로는 부족하다. connection pool에 들어가있는 기존 커넥션이 갱신 후에도 옛날 자격증명으로 살아있을 수 있다. PostgreSQL은 세션 단위로 인증하므로 기존 세션은 계정이 만료돼도 끊기지 않을 때가 있다. 그래서 자격증명이 바뀌면 풀을 통째로 갈아엎는 게 안전하다. 갈아엎을 때는 in-flight 쿼리가 끝나길 기다리면서 새 풀을 점진적으로 만든다.

## 인증 메서드 — AppRole과 Kubernetes Auth

Vault에 접근하려면 토큰이 필요하다. 그런데 토큰 자체를 어떻게 얻느냐가 또 다른 문제다. 환경변수에 토큰을 박아두면 Vault를 쓰는 의미가 없다. 그 토큰이 다시 시크릿이니까.

### AppRole

서버나 CI 파이프라인에서 흔히 쓴다. Role ID(공개해도 무방한 식별자)와 Secret ID(짧은 수명의 인증 비밀)를 조합해서 토큰을 받는다.

```bash
# AppRole 엔진 마운트
vault auth enable approle

# 역할 생성
vault write auth/approle/role/myapp-role \
  token_policies="myapp-policy" \
  token_ttl=1h \
  token_max_ttl=4h \
  secret_id_ttl=10m \
  secret_id_num_uses=1

# Role ID 조회 (정적 값, 환경변수에 박아도 됨)
vault read auth/approle/role/myapp-role/role-id

# Secret ID 발급 (1회용)
vault write -f auth/approle/role/myapp-role/secret-id

# 로그인해서 토큰 받기
vault write auth/approle/login \
  role_id=<role-id> \
  secret_id=<secret-id>
```

AppRole의 트릭은 Secret ID를 누가 어떻게 전달하느냐다. 흔한 패턴이 Trusted Orchestrator 패턴이다. 배포 시스템(예: Ansible, Spinnaker)이 Vault에 미리 인증되어 있어서 Secret ID를 발급받아 새 인스턴스의 메모리에 한 번만 주입한다. 인스턴스는 그 Secret ID로 즉시 로그인해서 토큰을 받고, Secret ID는 폐기한다. `secret_id_num_uses=1`로 1회용으로 만들면 누가 가로채도 이미 쓰여서 무용지물이다.

### Kubernetes Auth

쿠버네티스 환경이면 ServiceAccount 토큰을 인증 수단으로 쓸 수 있다. Pod가 마운트받은 SA 토큰을 Vault에 제출하면, Vault가 Kubernetes API에 토큰을 검증 요청하고 통과하면 Vault 토큰을 발급한다.

```bash
# K8s auth 엔진 마운트
vault auth enable kubernetes

# K8s API 접근 설정
vault write auth/kubernetes/config \
  kubernetes_host="https://kubernetes.default.svc" \
  kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt \
  token_reviewer_jwt="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)"

# 역할 정의 — 어떤 SA가 어떤 정책을 받는지
vault write auth/kubernetes/role/myapp \
  bound_service_account_names=myapp \
  bound_service_account_namespaces=production \
  policies=myapp-policy \
  ttl=1h
```

Pod 안에서는 `/var/run/secrets/kubernetes.io/serviceaccount/token`을 읽어서 Vault에 로그인한다.

```python
import requests

def vault_login_k8s(vault_addr, role):
    with open('/var/run/secrets/kubernetes.io/serviceaccount/token') as f:
        jwt = f.read()

    resp = requests.post(
        f'{vault_addr}/v1/auth/kubernetes/login',
        json={'role': role, 'jwt': jwt}
    )
    return resp.json()['auth']['client_token']
```

쿠버네티스 auth의 함정 중 하나는 Bound Token Projection이다. K8s 1.21 이후 ServiceAccount 토큰은 기본적으로 시간 제한이 있는 projected token이다. 1시간마다 자동 회전된다. Vault 설정에서 `disable_iss_validation=true`나 `issuer`를 명시적으로 맞춰주지 않으면 인증이 갑자기 실패하기 시작한다. 도입 직후엔 멀쩡하다가 며칠 후 토큰 재발급 시점에 깨지는 형태로 나타나서 디버깅이 까다롭다.

또 다른 함정은 K8s API의 token review 요청이 매번 발생한다는 거다. Pod가 많고 토큰 갱신이 잦으면 K8s API server에 부하가 간다. Vault 토큰의 TTL을 너무 짧게 잡으면(예: 5분) K8s API가 죽는 모습을 볼 수 있다. 보통 1시간 정도가 무난하다.

## Transit으로 처리하는 Envelope Encryption (실전)

앞에서 KV/Database/Transit을 다뤘는데, Transit의 envelope encryption은 운영에서 자주 쓰는 패턴이라 좀 더 깊게 본다.

전형적인 사용 사례는 데이터베이스에 PII(주민번호, 카드번호 같은 것)를 저장하는 경우다. 평문으로 두면 DB가 털렸을 때 그대로 노출되니까 암호화해서 저장한다. 그런데 어플리케이션 서버에 암호화 키를 박아두면 똑같이 그 서버가 털리면 끝이다. 그래서 키는 Vault에 두고, 데이터는 DB에 둔다.

직접 모든 데이터를 Vault로 보내서 암호화/복호화하면 처리량 문제가 생긴다. Vault 한 인스턴스가 처리 가능한 TPS는 수천 정도. 결제 시스템이라면 곧바로 병목이다. Envelope encryption은 데이터 키 발급/복호화만 Vault에 맡기고, 실제 데이터 암호화는 애플리케이션에서 하는 절충안이다.

```bash
# 데이터 키 발급 (datakey/plaintext는 Base64 인코딩된 평문 키)
vault write transit/datakey/plaintext/myapp-key
# 응답:
# plaintext: "wrXOoT...=="
# ciphertext: "vault:v1:..."
```

`plaintext` 키로 데이터를 암호화한 후, 평문 키는 메모리에서 즉시 폐기한다. 암호문과 ciphertext(암호화된 키)를 함께 DB에 저장한다. 나중에 읽을 때 ciphertext를 Vault로 보내 평문 키를 받아 데이터를 복호화한다.

키 회전 시 동작도 알아둘 만하다. `vault write -f transit/keys/myapp-key/rotate`로 키를 회전시켜도, 기존 데이터는 그대로 둔다. 새로 암호화되는 것만 새 버전을 쓴다. 점진적으로 옛 데이터를 다시 암호화하고 싶으면 `rewrap` 엔드포인트가 있다. 평문 노출 없이 ciphertext를 새 키 버전으로 재포장한다.

```bash
vault write transit/rewrap/myapp-key \
  ciphertext="vault:v1:old-ciphertext..."
# 응답: ciphertext: "vault:v2:new-ciphertext..."
```

`min_decryption_version`을 올리면 옛 버전으로 암호화된 데이터는 더이상 복호화되지 않는다. 강제 회전 정책을 적용할 때 쓴다. 다만 너무 빨리 올리면 회전이 끝나지 않은 데이터가 영원히 읽히지 않게 되니, rewrap을 충분히 돌리고 나서 적용한다.

## Audit Log 설정

운영하면서 가장 큰 가치를 느끼는 부분이 audit log다. 누가 언제 어떤 시크릿을 읽었는지, 어떤 정책으로 거부됐는지 전부 기록된다. 컴플라이언스 감사뿐만 아니라 사고 조사할 때도 결정적이다.

```bash
# 파일 기반 audit
vault audit enable file file_path=/var/log/vault/audit.log

# Syslog 기반
vault audit enable syslog tag="vault" facility="AUTH"

# socket 기반 (원격 수집기로 전송)
vault audit enable socket \
  address="audit-collector.internal:9090" \
  socket_type="tcp"
```

audit log를 활성화할 때 주의할 점이 두 가지 있다.

첫째, audit 백엔드가 모두 실패하면 Vault는 요청을 차단한다. 이건 의도된 동작이다. 감사 흔적이 없는 시크릿 접근을 허용하지 않겠다는 거다. 그래서 audit 백엔드를 단 하나만 활성화해두면 그 파일이 가득 차거나 디스크가 풀리는 순간 Vault 전체가 멈춘다. 보통 file 백엔드 두 개를 다른 디스크에 두거나, file + socket 조합으로 다중화한다.

둘째, audit log에는 요청과 응답이 모두 기록되지만 시크릿 값 자체는 SHA256으로 해시되어 저장된다. 평문이 audit log에 남으면 그 자체가 시크릿 유출이니까. 다만 토큰이나 lease ID 같은 식별자는 보이므로, audit log 자체를 시크릿으로 다뤄야 한다. 접근 권한을 최소화하고, 별도 보관 정책을 둔다.

```json
// audit log 한 줄 예시 (HMAC 처리된 상태)
{
  "time": "2026-06-03T10:23:45Z",
  "type": "request",
  "auth": {
    "client_token": "hmac-sha256:abcd...",
    "accessor": "hmac-sha256:efgh...",
    "policies": ["myapp-policy"],
    "metadata": {"role": "myapp"}
  },
  "request": {
    "operation": "read",
    "path": "database/creds/readonly",
    "remote_address": "10.0.1.42"
  }
}
```

`remote_address`만 잘 봐도 의외로 많은 걸 알 수 있다. 갑자기 모르는 IP에서 시크릿을 읽기 시작했다면 즉시 조사 대상이다. 보통 Loki나 Splunk 같은 곳으로 흘려보내고, 비정상 접근 패턴에 알람을 건다.

## 실무 트러블슈팅

### Unseal Key 분실 대응

Vault는 시작될 때 sealed 상태로 뜬다. 디스크에 저장된 데이터는 마스터 키로 암호화되어 있고, 그 마스터 키를 복호화하려면 unseal key 조각들이 필요하다. 기본은 5개 중 3개(Shamir's Secret Sharing).

unseal key를 분실하면 끝이다. 복구가 불가능하다. 백업이 있어도 백업도 같은 키로 암호화되어 있으므로 의미가 없다. 다음과 같은 시나리오에서 자주 사고가 난다.

- 초기 unseal key를 발급받은 사람이 퇴사하면서 보관처를 알리지 않음
- 1Password 공유 저장소에 넣었는데 그 vault가 삭제됨
- 키 5개를 5명에게 나눠줬는데 3명이 동시에 퇴사

대응책은 사후가 아니라 사전이다. unseal key를 다음과 같이 관리한다.

1. 키 분산은 7개 중 4개(또는 5개 중 3개) 같은 임계치로 한다. 1개만 분실해도 운영이 가능한 구조.
2. 키 보관자는 서로 다른 부서/팀에서 선정해서 동시 퇴사 리스크를 분산한다.
3. 정기적으로 `vault operator rekey` 명령으로 키 자체를 회전한다. 회전 시점에 모든 보관자가 새 키를 받게 되므로 분실 가능성을 정기적으로 점검할 수 있다.
4. Auto-unseal을 사용한다. AWS KMS, GCP KMS, Azure Key Vault에 마스터 키를 위탁한다. 그러면 unseal key 대신 recovery key가 발급되고, 일상 운영에서는 클라우드 KMS가 자동으로 unseal한다.

Auto-unseal은 거의 표준이다. 사람이 매번 키 조각을 들고 와서 unseal하는 건 야간 장애 시 큰 부담이다. KMS에 의존하는 게 불안하면 두 클라우드의 KMS에 동시 위탁하는 멀티 클라우드 구성도 있다.

```hcl
# AWS KMS auto-unseal 설정 예시 (config.hcl)
seal "awskms" {
  region     = "ap-northeast-2"
  kms_key_id = "arn:aws:kms:ap-northeast-2:123456789012:key/abcd-1234"
}

storage "raft" {
  path    = "/vault/data"
  node_id = "node1"
}
```

### 토큰 TTL 관리 실수

가장 흔한 실수는 토큰 TTL을 너무 길게 잡는 거다. "혹시 갱신 실패할까봐" 30일짜리 토큰을 발급해두면 그 토큰이 유출됐을 때 30일간 무방비가 된다.

또 다른 실수는 root token을 일상 운영에 쓰는 거다. root token은 만료가 없고 모든 권한이 있다. 초기 설정 후에는 반드시 폐기하고, 정책 기반 토큰만 사용한다. `vault token revoke <root-token>`으로 폐기한 뒤, 비상시에만 `vault operator generate-root`로 임시 발급한다. 임시 발급된 root token은 사용 후 즉시 다시 폐기한다.

`token_max_ttl`과 `max_lease_ttl`을 헷갈리는 경우도 잦다. 전자는 인증 토큰의 최대 수명이고, 후자는 lease(예: DB 자격증명)의 최대 수명이다. 동적 시크릿을 쓰면서 `default_lease_ttl=1h`, `max_lease_ttl=24h`로 두면 lease는 24시간까지 갱신 가능하지만 토큰이 1시간 후 만료되면 그 시점에 lease 갱신 자체가 불가능해진다. 토큰과 lease의 TTL은 별개로 추적해야 한다.

토큰 만료 디버깅할 때는 `vault token lookup` 명령으로 현재 토큰의 TTL, 정책, accessor를 확인한다. accessor는 토큰 값을 노출하지 않고 토큰을 추적할 수 있는 핸들이다. 사고 조사 시 accessor만으로 토큰을 폐기할 수 있다.

```bash
vault token lookup
# Key                Value
# accessor           XXxxXXxxXXxx
# creation_time      1717392000
# creation_ttl       1h
# expire_time        2026-06-03T11:23:45Z
# policies           [default myapp-policy]
# renewable          true
# ttl                58m
```

### Raft Storage 복구

Vault Enterprise가 아니어도 Raft를 내장 storage backend로 쓸 수 있게 되면서 운영이 한결 단순해졌다. 외부 Consul 클러스터를 띄울 필요가 없다. 다만 Raft는 자체적인 운영 지식이 필요하다.

Raft 클러스터에서 가장 자주 만나는 문제는 quorum 손실이다. 3노드 클러스터에서 2노드가 죽으면 quorum이 깨져서 쓰기가 불가능해진다. 5노드 클러스터에서 3노드가 죽어도 마찬가지. 노드 한 대 잃었을 때 곧바로 복구를 시작해야 한다.

```bash
# 클러스터 상태 확인
vault operator raft list-peers

# 죽은 노드 제거
vault operator raft remove-peer <node-id>

# 새 노드를 클러스터에 합류시킴 (새 노드의 config에 retry_join 설정 후 시작하면 자동 합류)
```

스냅샷 백업은 반드시 자동화한다. Raft 데이터 디렉토리를 그대로 복사하는 게 아니라, `vault operator raft snapshot save` 명령으로 일관성 있는 스냅샷을 만들어야 한다.

```bash
# 스냅샷 생성
vault operator raft snapshot save /backup/vault-$(date +%Y%m%d-%H%M).snap

# 복원 (DR 시나리오)
vault operator raft snapshot restore /backup/vault-20260603-0300.snap
```

복원할 때 주의할 점은 unseal/recovery key가 백업 시점과 동일해야 한다는 거다. 백업 직전에 rekey를 했다면 새 키가 필요하다. 복원 후 클러스터의 다른 노드들은 새 leader에 다시 합류해야 하므로 한 노드씩 재시작하면서 합류시킨다.

스냅샷이 손상돼서 복원이 안 되는 케이스도 있었다. 복구 가능성을 검증하려면 정기적으로 별도 환경에 실제로 복원해본다. 백업이 있다는 사실보다 백업이 복원 가능하다는 사실이 더 중요하다.

### Kubernetes Sidecar Injector와 시크릿 갱신 누락

Vault Agent Injector는 Mutating Admission Webhook으로 동작한다. Pod에 특정 annotation(예: `vault.hashicorp.com/agent-inject: "true"`)이 붙으면 Pod spec에 sidecar 컨테이너를 자동으로 끼워넣는다. 이 sidecar가 Vault에 인증해서 시크릿을 받아 공유 volume에 파일로 떨어뜨리고, 메인 컨테이너는 그 파일을 읽는다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    metadata:
      annotations:
        vault.hashicorp.com/agent-inject: "true"
        vault.hashicorp.com/role: "myapp"
        vault.hashicorp.com/agent-inject-secret-db: "database/creds/readonly"
        vault.hashicorp.com/agent-inject-template-db: |
          {{- with secret "database/creds/readonly" -}}
          DB_USERNAME={{ .Data.username }}
          DB_PASSWORD={{ .Data.password }}
          {{- end -}}
    spec:
      serviceAccountName: myapp
      containers:
      - name: app
        image: myapp:latest
        command: ["/bin/sh", "-c"]
        args: ["source /vault/secrets/db && exec /app/server"]
```

Pod 시작 시점에 `/vault/secrets/db` 파일이 생성되고, sidecar는 백그라운드에서 lease를 갱신한다. 여기서 첫 번째 함정이 발생한다.

파일이 갱신돼도 애플리케이션이 다시 읽지 않으면 의미가 없다. 위 예제에서는 `source /vault/secrets/db`로 환경변수로 로드하므로 프로세스 시작 시점의 값만 잡힌다. 1시간 후 자격증명이 바뀌어도 프로세스는 옛 값을 들고 있다.

해결 방법은 두 가지다. 첫째, 애플리케이션이 파일을 주기적으로 다시 읽도록 만든다. 둘째, sidecar에 `vault.hashicorp.com/agent-inject-command-db` 같은 명령을 등록해서 시크릿이 갱신될 때마다 메인 컨테이너에 SIGHUP을 보낸다. 그런데 SIGHUP을 받아도 애플리케이션이 무시하면 또 의미가 없으므로 결국 애플리케이션 측 협력이 필요하다.

두 번째 함정은 init 컨테이너 모드의 동작이다. `vault.hashicorp.com/agent-pre-populate-only: "true"`로 설정하면 init 컨테이너로만 동작하고 sidecar가 안 뜬다. Pod 시작 시 시크릿을 한 번만 받고 끝. lease 갱신이 안 되므로 TTL이 만료되면 그대로 죽는다. 짧은 작업(예: CronJob)에만 쓰고, 장수 Pod에는 절대 쓰지 않는다.

세 번째 함정은 sidecar의 자원 사용이다. Pod 하나당 추가 컨테이너가 붙으므로 메모리/CPU가 추가로 든다. 수백 Pod가 있으면 누적이 크다. 대안으로 Secrets Store CSI Driver를 쓰는 방법이 있다. CSI 드라이버가 노드 단위로 한 번만 띄워지고, Pod에 시크릿을 볼륨으로 마운트한다. 자원 효율은 좋지만 갱신 메커니즘이 sidecar 방식과 달라서 운영 절차를 다시 짜야 한다.

네 번째 함정은 Webhook 자체의 가용성이다. Mutating Webhook이 응답하지 않으면 Pod 생성이 실패한다. `failurePolicy=Fail`로 두면 Vault Injector가 죽었을 때 신규 Pod 배포가 막힌다. `failurePolicy=Ignore`로 두면 죽었을 때 sidecar 없이 Pod가 뜨면서 시크릿을 못 받아 애플리케이션이 곧바로 죽는다. 어느 쪽이든 장애가 발생하는데, 일반적으로는 `Fail`이 안전하다. 시크릿 없는 Pod가 뜨는 것보다 새 배포가 막히는 게 디버깅이 쉽다.

### Vault Agent 측 캐시 동작

Sidecar로 주입되는 Vault Agent는 자체 캐시를 가진다. 같은 시크릿을 반복 요청하면 캐시에서 응답한다. 캐시 TTL이 끝나기 전까지는 백엔드에 요청이 가지 않는다.

문제는 강제 회전 시나리오다. 보안 사고가 발생해서 모든 자격증명을 즉시 회수해야 하는데, Vault에서 lease를 폐기해도 sidecar의 캐시는 살아있다. 캐시 TTL이 끝날 때까지 옛 자격증명이 유효한 것처럼 보인다.

이런 경우 `vault.hashicorp.com/agent-cache-enable: "false"`로 캐시를 끄거나, sidecar를 강제로 재시작한다. Pod를 통째로 rollout restart하는 게 가장 확실한 방법이다.

## 운영하면서 느낀 것

Vault는 단순한 비밀번호 저장소가 아니다. 인증 시스템이고, 키 관리 시스템이고, 정책 엔진이다. 도입하는 순간 운영팀의 책임이 늘어난다. unseal 절차, 키 회전, audit log 모니터링, 토큰 만료 추적까지 전부 챙겨야 한다.

그런데도 도입할 가치는 분명하다. 시크릿 유출 사고가 한 번 나면 비교가 안 되는 비용이 든다. DB 자격증명 하나가 새어나가서 데이터가 털리면 회사 신뢰가 무너진다. Vault는 그 한 번을 막아주는 보험에 가깝다.

처음 도입할 때는 KV 엔진만 써도 좋다. 그게 익숙해지면 Database 동적 시크릿으로 넘어가고, 그 다음 Transit으로 데이터 암호화를 다룬다. 한 번에 다 도입하면 운영 부담이 폭발한다. 작게 시작해서 점진적으로 확장하는 게 안전하다.
