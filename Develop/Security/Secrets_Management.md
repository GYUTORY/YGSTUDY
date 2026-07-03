---
title: 시크릿 관리
tags: [secrets-management, vault, aws-secrets-manager, kubernetes-secrets, gitleaks, trufflehog, env-files, secret-rotation, security, devops]
updated: 2026-05-03
---

# 시크릿 관리

DB 비밀번호, API 키, JWT 서명 키, OAuth 클라이언트 시크릿, TLS 인증서. 애플리케이션이 돌아가려면 이런 값들이 어딘가에 있어야 한다. 문제는 이걸 어디에 두느냐다. 코드에 하드코딩하면 git에 박히고, .env 파일에 넣으면 실수로 커밋되고, 환경변수에 넣으면 `ps`나 `/proc/<pid>/environ`으로 노출된다. "그냥 잘 관리하면 되지" 같은 얘기로는 안 끝난다. 한 번 누출되면 키 회전, 영향 범위 추적, 사후 감사까지 며칠을 잡아먹는다.

## 시크릿이 어디서 새는가

실무에서 시크릿이 누출되는 경로는 패턴이 정해져 있다.

첫 번째는 git 커밋이다. 개발자가 로컬에서 테스트하다가 .env 파일이나 config.yaml을 그대로 커밋한다. private 레포라 괜찮다고 생각하지만, GitHub은 private 레포의 누출도 자동 스캐닝하고, 실제로 fork된 적이 있거나 잠깐이라도 public이었던 시점이 있으면 노출 가능성이 있다. 더 흔한 건 신입이 자신의 GitHub 계정으로 회사 코드를 push하는 경우다.

두 번째는 로그다. 디버깅 로그에 request body를 그대로 찍는 코드가 있는데, 거기에 인증 헤더가 포함된다. 또는 에러 스택 트레이스에 DB 연결 문자열이 그대로 노출된다. CloudWatch나 Datadog에 한 번 들어간 로그는 retention 기간 내내 검색 가능한 상태로 남는다.

세 번째는 도커 이미지다. `Dockerfile`에서 `ENV API_KEY=...` 같은 식으로 빌드하거나, 빌드 중에 시크릿 파일을 COPY했다가 나중에 RM해도 이전 레이어에 남아있다. `docker history`로 누구나 볼 수 있다.

네 번째는 클라이언트 사이드다. React 앱의 `.env.production`에 `REACT_APP_API_KEY`로 넣은 값은 빌드된 JS 번들에 그대로 박힌다. 이건 시크릿이 아니라 공개 정보다.

이런 패턴을 알고 있어야 어디에 방어를 둬야 하는지 판단할 수 있다.

## 환경변수와 .env 파일

가장 기본이 되는 방식이다. 코드에서 분리한다는 점에서 하드코딩보다는 낫지만, 이게 최종 답은 아니다.

### .env 파일 사용 시 주의사항

```bash
# .env 파일은 절대 커밋하지 않는다
# .gitignore에 반드시 들어가야 한다
.env
.env.local
.env.*.local

# 대신 .env.example을 커밋해서 어떤 변수가 필요한지만 알린다
# .env.example
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
JWT_SECRET=change-me-in-production
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```

.env.example은 키 이름과 형식만 보여주고 실제 값은 비워둔다. 새 개발자가 합류하면 이 파일을 보고 자기 환경에 맞게 .env를 만든다.

Node.js에서 dotenv를 쓸 때는 production에서는 안 쓰는 게 원칙이다.

```javascript
// 잘못된 방식 — production에서도 dotenv 로딩
require('dotenv').config();

// 올바른 방식 — development에서만 로딩
if (process.env.NODE_ENV !== 'production') {
  require('dotenv').config();
}
```

production에서는 컨테이너 오케스트레이터나 시크릿 매니저가 환경변수를 주입한다. .env 파일을 production 서버에 두면 파일 권한 관리가 또 다른 부담이 된다.

### 환경변수의 한계

환경변수는 편리하지만 한계가 명확하다.

`ps eauxf` 명령으로 다른 프로세스의 환경변수를 볼 수 있는 경우가 있다. 리눅스 커널 설정에 따라 다르지만, 같은 사용자로 실행되는 프로세스끼리는 `/proc/<pid>/environ`에 접근 가능하다. 컨테이너 내부에서는 `docker inspect`로 환경변수가 평문으로 노출된다.

자식 프로세스로 환경변수가 그대로 전파된다. shell에서 npm 스크립트를 실행하면 그 안에서 호출하는 모든 서브프로세스가 환경변수를 상속받는다. 의도치 않게 외부 라이브러리가 시크릿을 읽을 수 있는 상태가 된다.

로테이션이 어렵다. 환경변수는 프로세스 시작 시점에 고정되므로, 시크릿을 바꾸려면 프로세스를 재시작해야 한다. 무중단 배포 환경에서는 매번 재시작이 부담이다.

이런 한계 때문에 규모가 커지면 시크릿 매니저로 옮기게 된다.

## HashiCorp Vault

자체 운영하는 시크릿 매니저로 가장 많이 쓰인다. 클라우드 종속성이 없고 정책을 세밀하게 정할 수 있다는 게 장점이다. 단점은 Vault 자체를 운영하는 부담이 만만치 않다는 것. seal/unseal, 백업, HA 구성, audit 로그까지 신경 써야 한다.

### Vault 기본 동작 방식

Vault는 모든 시크릿을 암호화해서 저장한다. 시작할 때 unseal key가 필요한데, 보통 5명에게 나눠주고 그중 3명이 모여야 unseal이 된다(Shamir's Secret Sharing). 이게 운영의 첫 번째 허들이다. EC2가 재부팅되면 누군가 unseal key를 가지고 와서 풀어줘야 한다. AWS KMS로 auto-unseal을 설정하는 게 일반적이다.

```bash
# Vault에 KV v2 엔진으로 시크릿 저장
vault kv put secret/myapp/prod \
  database_password='actual-password-here' \
  api_key='sk_live_xxxxx'

# 읽기
vault kv get secret/myapp/prod
vault kv get -field=database_password secret/myapp/prod
```

### Dynamic Secrets

Vault의 진짜 가치는 동적 시크릿이다. 정적인 비밀번호를 저장하는 것보다, 필요할 때마다 새 비밀번호를 발급해주는 방식이다.

```bash
# DB 동적 시크릿 설정
vault write database/config/postgres-prod \
  plugin_name=postgresql-database-plugin \
  allowed_roles="readonly,readwrite" \
  connection_url="postgresql://{{username}}:{{password}}@db.internal:5432/myapp" \
  username="vault_admin" \
  password="vault_admin_password"

vault write database/roles/readonly \
  db_name=postgres-prod \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
                       GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
  default_ttl="1h" \
  max_ttl="24h"

# 애플리케이션이 자격증명 요청
vault read database/creds/readonly
# 매번 다른 username/password가 발급된다, TTL 후 자동 폐기
```

DB 비밀번호가 1시간 후 자동으로 사라진다. 누출되더라도 영향이 제한적이다. 다만 애플리케이션이 자격증명을 갱신하는 로직을 따로 구현해야 한다. 커넥션 풀이 끊기는 시점을 잘 처리하지 못하면 운영 중에 갑자기 DB 연결이 끊기는 사고가 난다.

### 인증 방식 선택

Vault는 누가 시크릿을 읽을 권한이 있는지를 판단해야 한다. 토큰을 발급받아 쓰는 게 기본이지만, 토큰을 어떻게 안전하게 전달하느냐가 또 문제다.

AWS에서는 IAM 인증 방식을 쓴다. EC2 인스턴스의 IAM Role을 Vault에서 검증해서 토큰을 발급한다. 애플리케이션은 Vault 토큰을 어디 저장할 필요가 없다. Kubernetes에서는 ServiceAccount 토큰을 쓴다. 이런 방식이 chicken-and-egg 문제(시크릿을 가져오려면 시크릿이 필요)를 해결한다.

```hcl
# Vault에 AWS 인증 활성화
path "auth/aws/role/myapp" {
  bound_iam_principal_arn = "arn:aws:iam::123456789012:role/myapp-prod"
  policies = ["myapp-prod-policy"]
  ttl = "1h"
}
```

## AWS Secrets Manager

AWS 환경이라면 Secrets Manager가 가장 편하다. Vault만큼의 기능은 없지만 운영 부담이 거의 없다.

### 기본 사용

```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='ap-northeast-2')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# 호출
secret = get_secret('prod/myapp/database')
db_password = secret['password']
```

IAM Role로 권한 제어를 하므로 EC2/ECS/Lambda에서 별도 자격증명 없이 접근 가능하다. ECS Task Definition에서는 컨테이너 환경변수로 직접 주입할 수도 있다.

```json
{
  "containerDefinitions": [{
    "name": "myapp",
    "secrets": [{
      "name": "DATABASE_PASSWORD",
      "valueFrom": "arn:aws:secretsmanager:ap-northeast-2:123456789012:secret:prod/myapp/database:password::"
    }]
  }]
}
```

이 방식의 함정은 컨테이너 환경변수로 들어가는 순간 환경변수의 한계를 그대로 갖는다는 점이다. 시크릿이 바뀌어도 컨테이너 재시작 전까지는 옛날 값을 들고 있다.

### 자동 로테이션

Secrets Manager는 Lambda 함수를 트리거해서 시크릿을 자동 로테이션한다. RDS는 빌트인 로테이션 함수가 있어서 클릭 몇 번이면 30일마다 비밀번호가 바뀐다.

직접 만든 시크릿(서드파티 API 키 같은)을 로테이션하려면 Lambda를 직접 작성해야 한다. 4단계 워크플로우(createSecret, setSecret, testSecret, finishSecret)를 구현해야 하는데, 이게 생각보다 까다롭다. 새 키 생성 → 적용 → 테스트 → 기존 키 폐기 순서를 정확히 지키지 않으면 운영 중에 인증 실패가 발생한다.

### 비용 고려

Secret 1개당 월 $0.40, API 호출 10,000건당 $0.05다. 별거 아닌 것 같지만 마이크로서비스 100개에 시크릿 5개씩 두면 200달러가 그냥 나간다. 더 큰 문제는 호출 비용이다. 매 요청마다 시크릿을 읽으면 호출 횟수가 폭증한다. 반드시 캐싱을 해야 한다.

```python
from functools import lru_cache
from datetime import datetime, timedelta

_cache = {}
_cache_ttl = timedelta(minutes=5)

def get_secret_cached(secret_name):
    now = datetime.utcnow()
    if secret_name in _cache:
        value, fetched_at = _cache[secret_name]
        if now - fetched_at < _cache_ttl:
            return value
    
    value = get_secret(secret_name)
    _cache[secret_name] = (value, now)
    return value
```

캐싱 TTL을 너무 길게 잡으면 로테이션된 시크릿이 반영되는 데 시간이 걸린다. 5분 정도가 무난하다.

## Kubernetes Secrets

쿠버네티스의 Secret 리소스는 이름이 시크릿이지만 실은 단순한 base64 인코딩이다. 암호화가 아니다. etcd에 평문으로 저장된다.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: myapp-secrets
type: Opaque
data:
  database-password: cGFzc3dvcmQxMjM=  # base64로 인코딩된 'password123'
```

이걸 보고 "안전하다"고 생각하면 안 된다. base64는 인코딩이지 암호화가 아니다. `echo 'cGFzc3dvcmQxMjM=' | base64 -d`로 누구나 디코딩할 수 있다.

### etcd 암호화 활성화

etcd 자체를 암호화하려면 별도 설정이 필요하다.

```yaml
# /etc/kubernetes/encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <base64-encoded-32byte-key>
      - identity: {}
```

이걸 활성화해도 etcd에 접근할 수 있는 사람(클러스터 관리자, 백업 파일을 가진 사람)은 여전히 시크릿을 볼 수 있다. 키 자체가 etcd 호스트에 평문으로 있기 때문이다.

진짜 안전하게 하려면 KMS provider를 사용한다. AWS KMS, GCP KMS, 또는 Vault를 KMS로 연결한다. 이러면 etcd에 접근해도 KMS에서 복호화 권한이 없으면 시크릿을 못 본다.

### External Secrets Operator

Kubernetes Secret의 한계를 우회하기 위해 외부 시크릿 매니저(Vault, AWS Secrets Manager 등)를 직접 연동하는 패턴이 일반화됐다. External Secrets Operator가 표준처럼 쓰인다.

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: myapp-db
spec:
  refreshInterval: 5m
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: myapp-db-secret
  data:
    - secretKey: password
      remoteRef:
        key: prod/myapp/database
        property: password
```

5분마다 AWS Secrets Manager에서 값을 가져와서 Kubernetes Secret으로 동기화한다. 시크릿 로테이션이 자동으로 반영된다는 장점이 있지만, Pod 자체는 환경변수가 바뀐다고 다시 읽지 않는다. Reloader 같은 컨트롤러를 추가로 써서 Secret이 바뀌면 Pod를 재시작하게 한다.

### Pod에서 시크릿 사용 시 주의

```yaml
# 환경변수로 주입 — ps나 /proc로 노출 가능
env:
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: myapp-db-secret
        key: password

# 파일로 마운트 — 환경변수보다 안전
volumes:
  - name: secrets
    secret:
      secretName: myapp-db-secret
volumeMounts:
  - name: secrets
    mountPath: /etc/secrets
    readOnly: true
```

파일 마운트가 환경변수보다 안전하다. 컨테이너 안에서만 보이고, 외부 프로세스에서 환경변수처럼 들여다볼 수 없다. 또한 Secret이 바뀌면 마운트된 파일도 자동으로 갱신된다(약간의 지연 있음). 애플리케이션이 파일을 다시 읽도록 만들면 재시작 없이 시크릿 갱신이 가능하다.

## 시크릿 로테이션

시크릿은 주기적으로 바꿔야 한다. 누출됐는지 모를 가능성을 항상 염두에 둬야 하기 때문이다. 로테이션 주기는 시크릿 종류에 따라 다르다.

DB 비밀번호는 90일, JWT 서명 키는 6개월~1년, 외부 API 키는 발급 정책에 따라 다르지만 보통 6개월. TLS 인증서는 Let's Encrypt면 90일, 상용이면 1년. AWS Access Key는 90일을 넘기지 말아야 한다.

### 로테이션의 어려움

원리는 단순하다. 새 시크릿을 만들고, 둘 다 유효한 기간을 두고, 모든 시스템이 새 시크릿을 쓰게 된 뒤 옛날 것을 폐기한다. 문제는 이걸 무중단으로 하는 게 어렵다는 것이다.

JWT 서명 키 로테이션을 예로 들면, 키를 바꾸는 순간 기존에 발급된 토큰들이 전부 무효가 된다. 사용자들이 갑자기 로그아웃되는 사고가 난다. 이걸 피하려면 검증 시점에 여러 키를 동시에 시도해보는 구조가 필요하다.

```python
# 검증 시 두 개 키를 모두 시도
def verify_token(token):
    for key in [current_key, previous_key]:
        try:
            return jwt.decode(token, key, algorithms=['HS256'])
        except jwt.InvalidSignatureError:
            continue
    raise jwt.InvalidTokenError()
```

발급은 항상 새 키로, 검증은 새 키와 이전 키 둘 다로. 이전 키는 토큰 만료 기간이 지나면 폐기한다.

DB 비밀번호도 비슷하다. 한 번에 바꾸면 연결 풀이 다 끊긴다. PostgreSQL은 한 사용자에 비밀번호 하나뿐이라, 보통 새 사용자를 만들고 권한을 동일하게 부여한 뒤 애플리케이션이 새 사용자로 전환하게 한다. 그래서 동적 시크릿 방식이 매력적이다.

### 자동화

수동 로테이션은 결국 잊어버린다. 90일마다 알람이 울려도 바쁘면 미루게 되고, 그러다 1년이 지나간다. 로테이션은 자동화가 답이다.

AWS Secrets Manager는 Lambda로 자동 로테이션한다. Vault는 동적 시크릿으로 매 요청마다 새로 발급한다. 이런 도구를 쓰지 않고 자체 구현하려면 cronjob과 잘 짜여진 워크플로우가 필요하다.

자동 로테이션을 도입하기 전에는 반드시 모니터링과 롤백 메커니즘부터 만들어야 한다. 새벽에 자동으로 키가 바뀌었는데 일부 서비스가 옛날 키를 들고 있으면 인증 실패가 폭주한다. 알림이 늦으면 한참 후에 발견한다.

## 시크릿 누출 사고 대응

누출은 언젠가 일어난다. 어떻게 대응하느냐가 피해 규모를 결정한다.

### 즉시 해야 할 것

가장 먼저 누출된 시크릿을 무효화한다. 키 회전이 아니라 즉시 폐기다. AWS Access Key라면 콘솔에서 비활성화, DB 비밀번호라면 즉시 변경, API 키라면 발급처에서 revoke. 이게 분 단위로 빨라야 한다.

다음은 영향 범위 파악이다. 누출된 시크릿으로 무엇이 가능한지 정확히 알아야 한다. AWS Access Key라면 IAM 권한을 확인하고, 해당 키로 어떤 호출이 있었는지 CloudTrail에서 확인한다. DB 자격증명이라면 audit log를 뒤져서 의심스러운 쿼리를 찾는다.

```bash
# CloudTrail에서 특정 Access Key의 호출 내역 검색
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=AccessKeyId,AttributeValue=AKIAEXAMPLEKEY \
  --start-time 2026-04-01 \
  --end-time 2026-05-03
```

영향 범위 파악이 끝나면 추가 피해 방지 조치를 한다. 데이터가 유출됐는지, 추가로 권한이 escalate됐는지, 새 IAM 사용자나 Role이 만들어졌는지 점검한다. 공격자가 키를 얻으면 보통 백도어를 심어둔다.

### Git에 시크릿이 커밋된 경우

가장 흔한 시나리오다. 발견 즉시 시크릿을 무효화하는 게 첫 번째다. git history를 정리하는 건 그 다음이다. "히스토리만 지우면 되겠지"라고 생각하면 안 된다. 누군가 이미 fetch했을 수 있고, GitHub의 캐시나 미러에 남아있을 수 있다. 시크릿은 이미 노출됐다고 가정해야 한다.

시크릿 무효화를 하고 나서 history를 정리하는 이유는 (1) 다른 개발자가 실수로 다시 사용하지 않게, (2) 향후 자동 스캐너의 false positive를 줄이기 위해서다.

#### git filter-repo 사용

BFG Repo-Cleaner도 있지만 git filter-repo가 더 강력하고 권장된다.

```bash
# 설치
pip install git-filter-repo

# 특정 파일을 history 전체에서 삭제
git filter-repo --path config/secrets.yml --invert-paths

# 특정 문자열 패턴을 history 전체에서 마스킹
echo 'sk_live_abcdef==>REDACTED' > replacements.txt
git filter-repo --replace-text replacements.txt

# force push로 원격 반영
git push origin --force --all
git push origin --force --tags
```

filter-repo를 실행하면 origin remote가 자동으로 제거된다. 안전장치다. 새로 추가하고 force push해야 한다.

force push 후에 모든 협업자에게 알려야 한다. 다른 개발자가 옛날 history를 가진 채 push하면 다시 살아난다. 모든 clone을 폐기하고 다시 clone하라고 공지한다.

#### 한계와 현실

GitHub은 force push 후에도 일정 기간 옛날 commit에 SHA로 직접 접근하면 보인다. fork된 적이 있으면 fork에 그대로 남아있다. 누군가 PR을 열어서 commit이 GitHub의 다른 곳에 캐시됐을 수도 있다.

이런 이유로 GitHub Support에 연락해서 캐시 삭제를 요청해야 하는 경우가 있다. 하지만 이미 노출된 시간을 되돌릴 수는 없다. 결국 시크릿 무효화가 유일한 진짜 해결책이다.

### 사후 분석

사고 대응이 끝나면 어떻게 누출됐는지, 왜 막지 못했는지, 어떻게 다시 발생하지 않게 할지 정리해야 한다. 이게 다음 사고를 막는다.

누출 경로를 정확히 파악하지 않으면 같은 일이 반복된다. 개발자가 .env를 커밋한 거라면 pre-commit hook과 CI 스캐너가 왜 못 잡았는지 본다. 로그에 시크릿이 찍혔다면 로깅 라이브러리에 마스킹 필터가 빠져있는 것이다.

## gitleaks와 truffleHog

git에 시크릿이 들어가는 걸 막는 자동화 도구다. 비슷해 보이지만 사용 패턴이 약간 다르다.

### gitleaks

가벼운 Go 바이너리로 빠르다. CI에 넣기 좋고 pre-commit hook으로도 쓴다.

```bash
# 현재 working directory 스캔
gitleaks detect --source . --verbose

# git history 전체 스캔
gitleaks detect --source . --log-opts="--all"

# pre-commit hook으로 staged 파일만 스캔
gitleaks protect --staged --verbose
```

gitleaks는 정규식 기반으로 동작한다. 기본 룰셋에 AWS Access Key, GitHub Token, Stripe Key, JWT 같은 흔한 패턴이 들어있다. 커스텀 룰을 .gitleaks.toml에 추가할 수 있다.

```toml
# .gitleaks.toml
[[rules]]
id = "company-internal-api-key"
description = "Internal API Key"
regex = '''int_(live|test)_[0-9a-zA-Z]{32}'''
tags = ["key", "internal"]
```

false positive가 종종 나온다. 테스트 코드의 mock 키, 문서의 예제 값 같은 게 걸린다. allowlist로 제외해야 한다.

```toml
[allowlist]
paths = [
  '''docs/.*''',
  '''.*\.test\.js$'''
]
regexes = [
  '''AKIAIOSFODNN7EXAMPLE'''  # AWS 공식 문서의 예제 키
]
```

### truffleHog

엔트로피 기반 탐지를 함께 한다. 정규식에 안 잡히는 랜덤 문자열도 의심하면 알려준다.

```bash
# git history 스캔
trufflehog git https://github.com/myorg/myrepo.git

# 로컬 디렉토리 스캔
trufflehog filesystem ./src

# 검증된 시크릿만 보고 (실제로 유효한 자격증명인지 확인)
trufflehog git https://github.com/myorg/myrepo.git --only-verified
```

truffleHog의 강력한 기능은 verification이다. 발견한 시크릿을 실제 서비스에 호출해서 유효한지 확인한다. AWS Access Key를 발견하면 STS GetCallerIdentity를 호출해서 진짜 살아있는 키인지 본다. false positive를 크게 줄여준다.

다만 속도는 gitleaks보다 느리다. 대형 레포의 history 전체를 스캔하면 시간이 한참 걸린다.

### CI/CD 통합

PR 머지 전에 자동으로 검사하게 만든다.

```yaml
# .github/workflows/secret-scan.yml
name: Secret Scan
on: [pull_request]

jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

CI 검사만으로는 부족하다. 개발자 로컬에서 push하기 전에 잡아야 한다. pre-commit hook으로 막는 게 첫 번째 방어선이다.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
```

pre-commit hook은 우회가 쉽다(`git commit --no-verify`). 강제하기 어려우므로 CI에서도 반드시 검사해야 한다. 또한 GitHub의 Secret Scanning을 켜두면 push되는 순간 GitHub이 직접 검사해서 알림을 준다. 이중삼중으로 막아야 한다.

### 실제 운영에서의 한계

자동 스캐너는 만능이 아니다. 형식이 정해진 시크릿(AWS Key, Stripe Key 같은 prefix가 있는 것)은 잘 잡지만, 사내에서 쓰는 임의 형식의 시크릿은 룰을 직접 만들지 않으면 못 잡는다. 또한 base64로 인코딩되거나 환경변수 합성으로 만들어지는 시크릿은 정규식으로 잡기 어렵다.

엔트로피 기반 탐지는 false positive가 많다. UUID나 hash 값도 엔트로피가 높아서 시크릿으로 오인한다. allowlist를 계속 보강해야 운영이 가능하다.

스캐너를 도입했다고 안심하면 안 된다. 룰 업데이트, allowlist 관리, 새 패턴 추가가 계속 필요하다. 가끔 옛날 history를 새 룰로 다시 스캔해서 놓친 게 없는지 봐야 한다.

## 시크릿 관리 도구 선택 기준

상황별로 적절한 도구가 다르다.

소규모 단일 서버라면 .env 파일과 환경변수로 충분하다. 파일 권한 관리만 신경 쓰면 된다. 도커 컨테이너로 배포하면 docker secrets를 활용할 수 있다.

AWS 단일 클라우드 환경이라면 Secrets Manager나 Parameter Store가 가장 자연스럽다. Parameter Store는 무료(SecureString도 무료)지만 자동 로테이션이 없다. Secrets Manager는 비용이 들지만 로테이션 기능이 있다.

멀티 클라우드나 온프레미스 혼재 환경이라면 Vault를 검토한다. 운영 부담이 큰 게 단점이지만, 동적 시크릿이나 PKI, 트랜짓 암호화 같은 고급 기능이 매력적이다. HashiCorp Cloud Platform(HCP) Vault를 쓰면 운영 부담을 덜 수 있다.

쿠버네티스 위주라면 External Secrets Operator로 외부 시크릿 매니저를 연동하는 패턴이 표준이다. Sealed Secrets나 SOPS로 암호화된 시크릿을 git에 커밋하는 방식도 있다. GitOps와 잘 맞는다.

도구 선택보다 중요한 건 운영 프로세스다. 누가 시크릿을 만들 권한이 있는지, 누가 접근할 수 있는지, 로테이션은 누가 책임지는지, 사고 발생 시 누가 대응하는지가 명확해야 한다. 도구만 도입하고 프로세스가 없으면 결국 시크릿이 새는 건 같다.
