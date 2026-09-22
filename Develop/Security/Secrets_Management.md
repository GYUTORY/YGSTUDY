---
title: 시크릿 관리
tags: [security, devops]
updated: 2026-09-22
---

# 시크릿 관리

DB 비밀번호, API 키, JWT 서명 키, OAuth 클라이언트 시크릿, TLS 인증서. 애플리케이션이 돌아가려면 이런 값들이 어딘가에 있어야 한다. 문제는 이걸 어디에 두느냐다. 코드에 하드코딩하면 git에 박히고, .env 파일에 넣으면 실수로 커밋되고, 환경변수에 넣으면 `ps`나 `/proc/<pid>/environ`으로 노출된다. 한 번 누출되면 키 회전, 영향 범위 추적, 사후 감사까지 며칠을 잡아먹는다.

## 시크릿이 어디서 새는가

실무에서 시크릿이 누출되는 경로는 패턴이 정해져 있다.

첫 번째는 git 커밋이다. 개발자가 로컬에서 테스트하다가 .env 파일이나 config.yaml을 그대로 커밋한다. private 레포라 괜찮다고 생각하지만, GitHub은 private 레포의 누출도 자동 스캐닝하고, 실제로 fork된 적이 있거나 잠깐이라도 public이었던 시점이 있으면 노출 가능성이 있다. 더 흔한 건 신입이 자신의 GitHub 계정으로 회사 코드를 push하는 경우다.

두 번째는 로그다. 디버깅 로그에 request body를 그대로 찍는 코드가 있는데, 거기에 인증 헤더가 포함된다. 에러 스택 트레이스에 DB 연결 문자열이 그대로 노출되는 경우도 있다. CloudWatch나 Datadog에 한 번 들어간 로그는 retention 기간 내내 검색 가능한 상태로 남는다.

세 번째는 도커 이미지다. `Dockerfile`에서 `ENV API_KEY=...` 같은 식으로 빌드하거나, 빌드 중에 시크릿 파일을 COPY했다가 나중에 RUN rm으로 지워도 이전 레이어에 남아있다. `docker history`로 누구나 볼 수 있다.

네 번째는 클라이언트 사이드다. React 앱의 `.env.production`에 `REACT_APP_API_KEY`로 넣은 값은 빌드된 JS 번들에 그대로 박힌다. 이건 시크릿이 아니라 공개 정보다.

## 환경변수만으로 부족한 이유

가장 기본이 되는 방식이다. 코드에서 분리한다는 점에서 하드코딩보다는 낫지만, 이게 최종 답은 아니다.

### .env 파일 기본 설정

```bash
# .env 파일은 커밋하지 않는다
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
// production에서도 dotenv 로딩 — 잘못된 방식
require('dotenv').config();

// development에서만 로딩
if (process.env.NODE_ENV !== 'production') {
  require('dotenv').config();
}
```

production에서는 컨테이너 오케스트레이터나 시크릿 매니저가 환경변수를 주입한다. .env 파일을 production 서버에 두면 파일 권한 관리가 또 다른 부담이 된다.

### 환경변수의 구조적 한계

규모가 작을 때는 환경변수로 충분하지만, 시스템이 커질수록 한계가 드러난다.

`ps eauxf` 명령으로 다른 프로세스의 환경변수를 볼 수 있는 경우가 있다. 리눅스 커널 설정에 따라 다르지만, 같은 사용자로 실행되는 프로세스끼리는 `/proc/<pid>/environ`에 접근 가능하다. 컨테이너 내부에서는 `docker inspect`로 환경변수가 평문으로 노출된다.

자식 프로세스로 환경변수가 그대로 전파된다. shell에서 npm 스크립트를 실행하면 그 안에서 호출하는 모든 서브프로세스가 환경변수를 상속받는다. 의도치 않게 외부 라이브러리가 시크릿을 읽을 수 있는 상태가 된다.

로테이션이 어렵다. 환경변수는 프로세스 시작 시점에 고정되므로, 시크릿을 바꾸려면 프로세스를 재시작해야 한다. 무중단 배포 환경에서는 매번 재시작이 부담이다.

감사(audit)가 안 된다. 누가 언제 어떤 시크릿을 읽었는지 추적할 방법이 없다. 보안 감사나 사고 대응 시 이게 치명적이다.

접근 제어가 없다. 환경변수가 주입된 프로세스 안의 코드라면 어디서든 읽을 수 있다. DB 비밀번호가 필요한 코드 모듈과 Slack API 키가 필요한 코드 모듈이 같은 환경변수 세트를 공유한다.

이런 한계 때문에 규모가 커지면 시크릿 매니저로 옮기게 된다.

## HashiCorp Vault

자체 운영하는 시크릿 매니저로 가장 많이 쓰인다. 클라우드 종속성이 없고 정책을 세밀하게 정할 수 있다는 게 장점이다. 단점은 Vault 자체를 운영하는 부담이 만만치 않다는 것. seal/unseal, 백업, HA 구성, audit 로그까지 신경 써야 한다.

### 기본 동작 방식

Vault는 모든 시크릿을 암호화해서 저장한다. 시작할 때 unseal key가 필요한데, 보통 5명에게 나눠주고 그중 3명이 모여야 unseal이 된다(Shamir's Secret Sharing). EC2가 재부팅되면 누군가 unseal key를 가지고 와서 풀어줘야 한다. AWS KMS로 auto-unseal을 설정하는 게 일반적이다.

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

### 인증 방식

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

컨테이너 환경변수로 들어가는 순간 환경변수의 한계를 그대로 갖는다. 시크릿이 바뀌어도 컨테이너 재시작 전까지는 옛날 값을 들고 있다.

### 자동 로테이션

Secrets Manager는 Lambda 함수를 트리거해서 시크릿을 자동 로테이션한다. RDS는 빌트인 로테이션 함수가 있어서 클릭 몇 번이면 30일마다 비밀번호가 바뀐다.

직접 만든 시크릿(서드파티 API 키 같은)을 로테이션하려면 Lambda를 직접 작성해야 한다. 4단계 워크플로우(createSecret, setSecret, testSecret, finishSecret)를 구현해야 하는데, 이게 생각보다 까다롭다. 새 키 생성 → 적용 → 테스트 → 기존 키 폐기 순서를 정확히 지키지 않으면 운영 중에 인증 실패가 발생한다.

### 비용 고려

Secret 1개당 월 $0.40, API 호출 10,000건당 $0.05다. 마이크로서비스 100개에 시크릿 5개씩 두면 200달러가 그냥 나간다. 더 큰 문제는 호출 비용이다. 매 요청마다 시크릿을 읽으면 호출 횟수가 폭증한다. 반드시 캐싱해야 한다.

```python
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

`echo 'cGFzc3dvcmQxMjM=' | base64 -d`로 누구나 디코딩할 수 있다.

### etcd 암호화 활성화

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

이걸 활성화해도 etcd에 접근할 수 있는 사람은 여전히 시크릿을 볼 수 있다. 키 자체가 etcd 호스트에 평문으로 있기 때문이다. 진짜 안전하게 하려면 KMS provider를 사용한다. AWS KMS, GCP KMS, 또는 Vault를 KMS로 연결한다.

### External Secrets Operator

Kubernetes Secret의 한계를 우회하기 위해 외부 시크릿 매니저를 직접 연동하는 패턴이 일반화됐다. External Secrets Operator가 표준처럼 쓰인다.

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

파일 마운트가 환경변수보다 안전하다. 컨테이너 안에서만 보이고, 외부 프로세스에서 환경변수처럼 들여다볼 수 없다. Secret이 바뀌면 마운트된 파일도 자동으로 갱신된다(약간의 지연 있음). 애플리케이션이 파일을 다시 읽도록 만들면 재시작 없이 시크릿 갱신이 가능하다.

## 시크릿 로테이션 구현

시크릿은 주기적으로 바꿔야 한다. 누출됐는지 모를 가능성을 항상 염두에 둬야 하기 때문이다.

DB 비밀번호는 90일, JWT 서명 키는 6개월~1년, 외부 API 키는 발급 정책에 따라 다르지만 보통 6개월. TLS 인증서는 Let's Encrypt면 90일, 상용이면 1년. AWS Access Key는 90일을 넘기지 말아야 한다.

### 무중단 JWT 키 로테이션

키를 바꾸는 순간 기존에 발급된 토큰들이 전부 무효가 된다. 사용자들이 갑자기 로그아웃되는 사고가 난다. 검증 시점에 여러 키를 동시에 시도해보는 구조가 필요하다.

```python
import jwt
import boto3
import json
from datetime import datetime, timezone

def get_signing_keys():
    sm = boto3.client('secretsmanager')
    secret = json.loads(
        sm.get_secret_value(SecretId='prod/myapp/jwt-keys')['SecretString']
    )
    # current: 현재 서명 키, previous: 이전 키 (로테이션 과도기)
    return secret['current'], secret.get('previous')

def sign_token(payload):
    current_key, _ = get_signing_keys()
    return jwt.encode(payload, current_key, algorithm='HS256')

def verify_token(token):
    current_key, previous_key = get_signing_keys()
    keys = [current_key]
    if previous_key:
        keys.append(previous_key)
    for key in keys:
        try:
            return jwt.decode(token, key, algorithms=['HS256'])
        except jwt.InvalidSignatureError:
            continue
    raise jwt.InvalidTokenError('token signature invalid')
```

로테이션 절차:
1. 새 키 생성
2. Secrets Manager에 `previous = current`, `current = new_key` 로 업데이트
3. 토큰 만료 기간(예: 24시간) 이후 `previous` 제거

발급은 항상 새 키로, 검증은 새 키와 이전 키 둘 다로. 이전 키는 토큰 만료 기간이 지나면 폐기한다.

### 무중단 DB 비밀번호 로테이션

PostgreSQL은 한 사용자에 비밀번호 하나뿐이다. 단순히 비밀번호를 바꾸면 기존 커넥션 풀이 다음 재연결 시도 때 실패한다.

```python
import psycopg2
import boto3
import json
import secrets
import string

def generate_password(length=32):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def rotate_db_password():
    sm = boto3.client('secretsmanager')
    secret_id = 'prod/myapp/database'
    
    # 현재 시크릿 읽기
    current = json.loads(sm.get_secret_value(SecretId=secret_id)['SecretString'])
    
    # 1단계: 새 비밀번호 생성
    new_password = generate_password()
    
    # 2단계: DB에 새 비밀번호 적용
    # 관리자 연결로 비밀번호 변경 (애플리케이션 연결과 분리된 관리자 계정)
    admin_dsn = f"host={current['host']} dbname={current['dbname']} user=admin password={ADMIN_PASSWORD}"
    with psycopg2.connect(admin_dsn) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "ALTER USER %s WITH PASSWORD %s",
                (current['username'], new_password)
            )
    
    # 3단계: Secrets Manager 업데이트
    current['password'] = new_password
    sm.update_secret(SecretId=secret_id, SecretString=json.dumps(current))
    
    # 4단계: 새 비밀번호로 연결 테스트
    test_dsn = f"host={current['host']} dbname={current['dbname']} user={current['username']} password={new_password}"
    with psycopg2.connect(test_dsn) as conn:
        conn.cursor().execute('SELECT 1')
    
    return new_password
```

이 방식은 DB에 비밀번호가 반영된 뒤 기존 커넥션 풀의 연결들이 시간이 지나면서 재연결 시도를 하게 된다. 재연결 시점에 새 비밀번호를 쓰는 코드가 있어야 한다. 커넥션 풀 라이브러리가 시크릿을 캐싱하고 있으면 재시작 없이는 갱신이 안 된다.

PgBouncer를 쓰는 환경이라면 PgBouncer의 userlist.txt도 같이 갱신해야 한다.

### 자동화

수동 로테이션은 결국 잊어버린다. 90일마다 알람이 울려도 바쁘면 미루게 되고, 그러다 1년이 지나간다. 로테이션은 자동화가 답이다.

자동 로테이션을 도입하기 전에는 반드시 모니터링과 롤백 메커니즘부터 만들어야 한다. 새벽에 자동으로 키가 바뀌었는데 일부 서비스가 옛날 키를 들고 있으면 인증 실패가 폭주한다. 알림이 늦으면 한참 후에 발견한다.

## git에 노출된 크리덴셜 대응 절차

가장 흔한 시나리오다. 발견하면 당황하기 쉬운데, 순서를 틀리면 사태가 더 커진다.

### 즉시 해야 할 일 (1시간 이내)

**시크릿 무효화가 첫 번째다.** git history를 정리하는 건 그 다음이다. "히스토리만 지우면 되겠지"라고 생각하면 안 된다. 누군가 이미 fetch했을 수 있고, GitHub의 캐시나 미러에 남아있을 수 있다. 시크릿은 이미 노출됐다고 가정해야 한다.

AWS Access Key라면 콘솔에서 즉시 비활성화한다. DB 비밀번호라면 즉시 변경한다. API 키라면 발급처에서 revoke한다. 이게 분 단위로 빨라야 한다.

시크릿 무효화 후 영향 범위를 파악한다.

```bash
# CloudTrail에서 해당 Access Key의 호출 내역 검색
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=AccessKeyId,AttributeValue=AKIAEXAMPLEKEY \
  --start-time 2026-01-01 \
  --end-time 2026-09-22

# IAM에서 해당 키로 만들어진 추가 사용자나 Role이 있는지 확인
aws iam list-users --query 'Users[?CreateDate>`2026-09-20`]'
aws iam list-roles --query 'Roles[?CreateDate>`2026-09-20`]'
```

공격자가 키를 얻으면 보통 백도어를 심어둔다. 새 IAM 사용자나 Role이 만들어졌는지, 데이터가 유출됐는지, 권한이 escalate됐는지 점검한다.

### git history 정리

시크릿을 무효화한 뒤에 history를 정리한다. 이유는 (1) 다른 개발자가 실수로 다시 사용하지 않게, (2) 향후 자동 스캐너의 false positive를 줄이기 위해서다.

BFG Repo-Cleaner도 있지만 git filter-repo가 더 강력하고 권장된다.

```bash
# 설치
pip install git-filter-repo

# 특정 파일을 history 전체에서 삭제
git filter-repo --path config/secrets.yml --invert-paths

# 특정 문자열 패턴을 history 전체에서 마스킹
# replacements.txt 형식: 원문==>대체문
echo 'AKIAIOSFODNN7ABCDEF==>REDACTED_AWS_KEY' > replacements.txt
echo 'sk_live_abcdef1234567890==>REDACTED_STRIPE_KEY' >> replacements.txt
git filter-repo --replace-text replacements.txt

# filter-repo 실행 후 origin이 자동 제거된다. 다시 추가해야 한다.
git remote add origin git@github.com:myorg/myrepo.git
git push origin --force --all
git push origin --force --tags
```

force push 후에 모든 협업자에게 알려야 한다. 다른 개발자가 옛날 history를 가진 채 push하면 다시 살아난다. 모든 clone을 폐기하고 다시 clone하라고 공지한다.

### GitHub 캐시의 한계

GitHub은 force push 후에도 일정 기간 옛날 commit에 SHA로 직접 접근하면 보인다. fork된 적이 있으면 fork에 그대로 남아있다. PR을 열어서 commit이 GitHub의 다른 곳에 캐시됐을 수도 있다.

GitHub Support에 연락해서 캐시 삭제를 요청해야 하는 경우가 있다. 하지만 이미 노출된 시간을 되돌릴 수는 없다. 시크릿 무효화가 유일한 진짜 해결책이다.

### 사후 분석

누출 경로를 정확히 파악하지 않으면 같은 일이 반복된다. 개발자가 .env를 커밋한 거라면 pre-commit hook과 CI 스캐너가 왜 못 잡았는지 본다. 로그에 시크릿이 찍혔다면 로깅 라이브러리에 마스킹 필터가 빠져있는 것이다.

## gitleaks와 GitGuardian 설정

git에 시크릿이 들어가는 걸 막는 자동화 도구다. gitleaks는 오픈소스로 직접 운영하고, GitGuardian은 SaaS로 레포를 모니터링한다.

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

[allowlist]
paths = [
  '''docs/.*''',
  '''.*\.test\.js$'''
]
regexes = [
  '''AKIAIOSFODNN7EXAMPLE'''  # AWS 공식 문서의 예제 키
]
```

false positive가 종종 나온다. 테스트 코드의 mock 키, 문서의 예제 값 같은 게 걸린다. allowlist로 제외해야 한다.

CI 통합:

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

pre-commit hook:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
```

### GitGuardian

SaaS 기반 시크릿 감지 서비스다. gitleaks와 달리 push하는 순간 실시간으로 스캔하고, 팀 단위 알림 기능이 있다.

`ggshield`는 GitGuardian의 CLI 도구다. gitleaks처럼 pre-commit hook이나 CI에 붙일 수 있고, 400개 이상의 시크릿 타입을 감지한다.

```bash
# 설치
pip install ggshield

# GitGuardian 계정 인증
ggshield auth login

# 로컬 디렉토리 스캔
ggshield secret scan path .

# git history 전체 스캔
ggshield secret scan repo .

# staged 파일만 스캔 (pre-commit hook용)
ggshield secret scan pre-commit
```

pre-commit hook 설정:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/GitGuardian/gg-shield
    rev: v1.29.0
    hooks:
      - id: ggshield
        language: python
        pass_filenames: false
```

GitGuardian의 강점은 verification이다. 발견한 시크릿을 실제 API에 호출해서 유효한지 확인한다. AWS Access Key를 발견하면 STS GetCallerIdentity를 호출해서 살아있는 키인지 본다. false positive를 크게 줄여준다.

GitHub App을 레포에 설치하면 push 즉시 알림을 준다. 누출된 시크릿의 commit, 파일, 줄번호와 함께 Slack이나 이메일로 통보하고, 내부 대시보드에서 전체 레포의 시크릿 누출 현황을 관리할 수 있다.

무료 플랜은 공개 레포 모니터링과 개인 계정만 지원한다. 팀 단위 private 레포 모니터링은 유료다.

`.gitguardian.yaml`로 스캔 설정을 커스텀한다:

```yaml
# .gitguardian.yaml
version: 2
ignore-paths:
  - tests/fixtures/
  - docs/examples/

ignore-matches:
  - match: "AKIAIOSFODNN7EXAMPLE"
    name: "AWS example key from docs"
  - match: "test_token_placeholder"
    name: "placeholder for tests"
```

### gitleaks vs GitGuardian 선택

gitleaks는 완전 오프라인으로 돌릴 수 있고 무료다. 금융권이나 의료처럼 소스 코드를 외부 서비스에 보낼 수 없는 환경에는 gitleaks만 쓴다. 설정과 룰 관리를 직접 해야 한다는 부담은 있다.

GitGuardian은 팀 규모가 커지면 관리 편의성에서 차이가 난다. 누가 언제 어떤 시크릿을 노출했는지 대시보드에서 추적할 수 있고, 개발자별 알림도 가능하다. private 레포를 외부 서비스에 연동하는 게 조직 정책상 가능한지 먼저 확인해야 한다.

CI에서는 둘 중 하나로 충분하지만, pre-commit hook은 개발자가 `git commit --no-verify`로 우회할 수 있다. CI 검사가 마지막 방어선이다. GitHub Secret Scanning(무료)도 켜두면 push되는 순간 GitHub이 직접 검사해서 알림을 준다.

### 실제 운영에서의 한계

자동 스캐너는 형식이 정해진 시크릿(AWS Key, Stripe Key 같은 prefix가 있는 것)은 잘 잡는다. 사내에서 쓰는 임의 형식의 시크릿은 룰을 직접 만들지 않으면 못 잡는다. base64로 인코딩되거나 환경변수 합성으로 만들어지는 시크릿은 정규식으로 잡기 어렵다.

엔트로피 기반 탐지는 false positive가 많다. UUID나 hash 값도 엔트로피가 높아서 시크릿으로 오인한다. allowlist를 계속 보강해야 운영이 가능하다.

가끔 옛날 history를 새 룰로 다시 스캔해서 놓친 게 없는지 봐야 한다.

## 시크릿 관리 도구 선택 기준

소규모 단일 서버라면 .env 파일과 환경변수로 충분하다. 파일 권한 관리만 신경 쓰면 된다. 도커 컨테이너로 배포하면 docker secrets를 활용할 수 있다.

AWS 단일 클라우드 환경이라면 Secrets Manager나 Parameter Store가 가장 자연스럽다. Parameter Store는 무료(SecureString도 무료)지만 자동 로테이션이 없다. Secrets Manager는 비용이 들지만 로테이션 기능이 있다.

멀티 클라우드나 온프레미스 혼재 환경이라면 Vault를 검토한다. 운영 부담이 큰 게 단점이지만, 동적 시크릿이나 PKI, 트랜짓 암호화 같은 고급 기능이 매력적이다. HashiCorp Cloud Platform(HCP) Vault를 쓰면 운영 부담을 덜 수 있다.

쿠버네티스 위주라면 External Secrets Operator로 외부 시크릿 매니저를 연동하는 패턴이 표준이다. Sealed Secrets나 SOPS로 암호화된 시크릿을 git에 커밋하는 방식도 있다. GitOps와 잘 맞는다.

도구 선택보다 중요한 건 운영 프로세스다. 누가 시크릿을 만들 권한이 있는지, 누가 접근할 수 있는지, 로테이션은 누가 책임지는지, 사고 발생 시 누가 대응하는지가 명확해야 한다. 도구만 도입하고 프로세스가 없으면 결국 시크릿이 새는 건 같다.
