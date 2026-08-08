---
title: RDS 보안
tags: [aws, security, vpc, encryption]
updated: 2026-07-24
---

# RDS 보안

RDS 보안은 크게 네 층으로 나뉜다. 네트워크 접근 통제, 전송 데이터 암호화, 저장 데이터 암호화, 인증 자격증명 관리다. 이 중 하나라도 빠지면 나머지를 잘 해도 허점이 생긴다.

## VPC Private Subnet 배치

RDS를 퍼블릭 서브넷에 두고 `publicly_accessible = true`로 열어두는 건 그 자체로 위험하다. 인터넷에서 DB 포트로 직접 스캔이 들어오고, 자격증명이 약하면 무차별 대입 공격에 노출된다.

프로덕션 RDS는 무조건 프라이빗 서브넷에 둔다. 퍼블릭 서브넷에는 인터넷 게이트웨이가 붙어 있어서 외부 트래픽이 들어올 수 있지만, 프라이빗 서브넷은 라우팅 테이블에 인터넷 게이트웨이 경로가 없어 외부에서 직접 닿을 수 없다.

DB 서브넷 그룹은 Multi-AZ를 위해 최소 두 개 AZ에 걸쳐 서브넷을 지정해야 한다.

```hcl
resource "aws_db_subnet_group" "rds" {
  name       = "prod-rds-subnet-group"
  subnet_ids = [
    aws_subnet.private_a.id,  # ap-northeast-2a, 프라이빗
    aws_subnet.private_b.id,  # ap-northeast-2b, 프라이빗
  ]
}

resource "aws_db_instance" "mysql" {
  identifier             = "prod-mysql"
  db_subnet_group_name   = aws_db_subnet_group.rds.name
  publicly_accessible    = false  # 반드시 false
  # ...
}
```

`publicly_accessible = false`를 설정하면 RDS 엔드포인트 DNS가 프라이빗 IP로 해석된다. `true`로 두면 퍼블릭 IP가 할당되고, 보안 그룹으로 막아도 인터넷에 노출된 구조가 된다.

앱 서버가 프라이빗 서브넷 RDS에 접근하는 방법은 두 가지다. 앱 서버도 프라이빗 서브넷에 있고 ALB를 앞에 두는 구조(가장 일반적), 또는 VPN이나 AWS Direct Connect로 온프레미스에서 프라이빗 서브넷에 접근하는 구조다.

운영자가 직접 DB에 쿼리를 날려야 할 때는 배스천 호스트나 AWS Systems Manager Session Manager를 통해 접근한다. 배스천 호스트를 쓴다면 배스천은 퍼블릭 서브넷에 두고, 배스천 SG에서만 RDS SG 인바운드를 허용하는 방식으로 접근을 제한한다.

## Security Group 설정

보안 그룹은 DB에 접근할 수 있는 출처를 제어하는 마지막 네트워크 방어선이다. RDS 보안 그룹의 인바운드 규칙은 가능한 좁게 잡는 게 원칙이다.

실무에서 가장 흔한 실수 두 가지다. 첫째, IP 대역으로 `0.0.0.0/0` 또는 VPC CIDR 전체를 열어두는 것. VPC 안에 있는 모든 리소스가 DB에 접근할 수 있게 되므로, EC2 하나가 뚫리면 DB까지 바로 닿는다. 둘째, 개발 편의로 열어둔 규칙을 운영에 그대로 두는 것.

올바른 구성은 애플리케이션 보안 그룹 ID를 소스로 지정하는 방식이다.

```hcl
# 앱 서버용 보안 그룹
resource "aws_security_group" "app" {
  name   = "prod-app-sg"
  vpc_id = aws_vpc.main.id
}

# RDS용 보안 그룹
resource "aws_security_group" "rds" {
  name   = "prod-rds-sg"
  vpc_id = aws_vpc.main.id

  # 앱 SG에서만 MySQL 포트 허용
  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  # 아웃바운드는 필요한 경우만 열거나 전체 허용
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

IP 대역 대신 소스로 보안 그룹 ID를 지정하면, 해당 SG가 붙은 리소스만 접근 가능하다. 앱 서버가 스케일아웃되어 IP가 바뀌어도 규칙을 수정할 필요가 없고, 권한 범위도 정확하다.

배스천 호스트가 있다면 배스천 SG도 인바운드 소스로 추가한다.

```hcl
ingress {
  from_port       = 3306
  to_port         = 3306
  protocol        = "tcp"
  security_groups = [
    aws_security_group.app.id,
    aws_security_group.bastion.id,
  ]
}
```

PostgreSQL은 포트 5432, Oracle은 1521, SQL Server는 1433으로 포트를 맞춰서 지정한다.

## KMS 암호화 (저장 데이터)

RDS 저장 데이터 암호화는 인스턴스 생성 시점에만 활성화할 수 있다. 이미 암호화 없이 만든 인스턴스에 나중에 암호화를 켜는 방법은 없다. 스냅샷을 뜨고 암호화 옵션을 켜서 복원한 뒤 기존 인스턴스를 교체하는 과정이 필요하다. 만들 때 무조건 켜는 게 맞다.

암호화 범위는 DB 인스턴스의 스토리지, 자동 백업, Read Replica, 스냅샷 전체다.

KMS 키는 두 종류다. AWS 관리형 키(`aws/rds`)는 별도 설정 없이 쓸 수 있지만, 키 회전 주기를 직접 제어하거나 다른 계정과 공유하거나 특정 서비스에서만 쓰도록 정책을 거는 게 안 된다. 고객 관리형 키(CMK)를 쓰면 이 모든 것을 직접 통제할 수 있다. 보안 감사나 컴플라이언스 요건이 있는 환경이면 CMK를 쓴다.

```hcl
resource "aws_kms_key" "rds" {
  description             = "RDS encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true  # 1년 주기 자동 키 회전
}

resource "aws_kms_alias" "rds" {
  name          = "alias/prod-rds"
  target_key_id = aws_kms_key.rds.key_id
}

resource "aws_db_instance" "mysql" {
  # ...
  storage_encrypted = true
  kms_key_id        = aws_kms_key.rds.arn
}
```

주의할 점이 하나 있다. 암호화된 스냅샷을 다른 리전이나 계정으로 복사할 때 원래 KMS 키가 따라가지 않는다. 복사 대상 리전/계정에서 별도 KMS 키를 지정해 재암호화해야 한다.

```bash
# 암호화된 스냅샷을 다른 리전으로 복사 (재암호화)
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier arn:aws:rds:ap-northeast-2:123456789:snapshot:prod-mysql-2026-01-01 \
  --target-db-snapshot-identifier prod-mysql-2026-01-01-backup \
  --kms-key-id arn:aws:kms:us-east-1:123456789:key/abcd1234 \
  --region us-east-1
```

CMK를 삭제하면 그 키로 암호화된 RDS 인스턴스와 스냅샷을 복호화할 수 없게 된다. KMS 키 삭제는 7~30일의 대기 기간이 있으므로, 대기 기간 안에 취소할 수 있지만 이미 키를 삭제 예약해 두고 까먹으면 돌이킬 수 없다. CMK 삭제 예약은 반드시 CloudWatch 알람으로 감지하도록 해야 한다.

## SSL/TLS 강제 연결

RDS는 기본적으로 SSL 없이도 연결이 된다. 암호화되지 않은 평문 트래픽이 VPC 내부를 오간다. VPC 내부라 외부에서 볼 수 없다고 해도, 네트워크 탭을 잡을 수 있는 위치에 공격자가 있으면 패킷을 볼 수 있다.

전송 데이터 암호화를 강제하려면 파라미터 그룹으로 설정한다.

**MySQL**

```bash
aws rds modify-db-parameter-group \
  --db-parameter-group-name prod-mysql8-params \
  --parameters "ParameterName=require_secure_transport,ParameterValue=ON,ApplyMethod=immediate"
```

`require_secure_transport = ON`으로 설정하면 SSL 없이 연결 시도하는 클라이언트는 에러를 받는다.

```
ERROR 3159 (HY000): Connections using insecure transport are prohibited while --require_secure_transport=ON.
```

**PostgreSQL**

```bash
aws rds modify-db-parameter-group \
  --db-parameter-group-name prod-pg15-params \
  --parameters "ParameterName=rds.force_ssl,ParameterValue=1,ApplyMethod=pending-reboot"
```

PostgreSQL은 `rds.force_ssl = 1`을 쓴다. 재부팅이 필요한 파라미터다.

애플리케이션 쪽에서도 SSL 연결을 맞춰야 한다. RDS CA 인증서는 `rds-ca-rsa2048-g1` 또는 `rds-ca-rsa4096-g1`를 사용한다. AWS가 주기적으로 CA를 갱신하므로, 앱에 번들된 CA 파일도 만료 전에 교체해야 한다. 2024년부터 기본 CA가 변경되었는데, 이를 인지 못하고 기존 CA 파일을 쓰다 연결 실패가 난 사례가 있다.

```java
// Spring Boot JDBC 예시 (MySQL)
String url = "jdbc:mysql://prod-mysql.xxxx.ap-northeast-2.rds.amazonaws.com:3306/mydb" +
             "?useSSL=true" +
             "&requireSSL=true" +
             "&trustCertificateKeyStoreUrl=file:/path/to/rds-ca.jks" +
             "&trustCertificateKeyStorePassword=changeit";
```

```python
# Python (SQLAlchemy + MySQL)
engine = create_engine(
    "mysql+pymysql://user:pass@host:3306/db",
    connect_args={
        "ssl": {
            "ca": "/path/to/rds-ca-2019-root.pem"
        }
    }
)
```

파라미터 변경 전에 앱이 SSL 연결을 제대로 맺는지 반드시 먼저 확인한다. `require_secure_transport = ON`을 먼저 켰다가 앱이 SSL 준비가 안 되어 있으면 전체 연결이 끊긴다. 앱에서 SSL 연결을 검증한 뒤 파라미터를 켜는 순서로 진행한다.

## IAM DB 인증

IAM DB 인증은 DB 비밀번호 대신 IAM이 발급하는 임시 토큰으로 DB에 접속하는 방식이다. 비밀번호를 코드나 환경 변수에 하드코딩하지 않아도 된다는 점이 장점이다.

동작 흐름은 다음과 같다.

```
1. 앱 서버에서 AWS SDK로 RDS 인증 토큰 요청
   (aws rds generate-db-auth-token)

2. IAM이 15분 유효한 토큰 발급

3. 앱이 토큰을 비밀번호 자리에 넣어 DB 연결

4. RDS가 토큰을 IAM으로 검증

5. 검증 성공 시 연결 수립
```

설정 순서는 세 단계다.

**1단계: RDS 인스턴스에서 IAM 인증 활성화**

```bash
aws rds modify-db-instance \
  --db-instance-identifier prod-mysql \
  --enable-iam-database-authentication \
  --apply-immediately
```

**2단계: DB 사용자 생성**

```sql
-- MySQL
CREATE USER 'iam_user'@'%' IDENTIFIED WITH AWSAuthenticationPlugin AS 'RDS';
GRANT SELECT, INSERT, UPDATE, DELETE ON mydb.* TO 'iam_user'@'%';

-- PostgreSQL
CREATE USER iam_user;
GRANT rds_iam TO iam_user;
```

**3단계: IAM 정책 연결**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "rds-db:connect",
      "Resource": "arn:aws:rds-db:ap-northeast-2:123456789:dbuser:db-ABCDEFGH/iam_user"
    }
  ]
}
```

Resource ARN의 `db-ABCDEFGH` 부분은 인스턴스 ARN이 아니라 `DbiResourceId`다. 콘솔에서 RDS 인스턴스 상세 정보에서 찾거나 아래로 확인한다.

```bash
aws rds describe-db-instances \
  --db-instance-identifier prod-mysql \
  --query 'DBInstances[0].DbiResourceId'
```

**토큰 발급과 연결 예시 (Python)**

```python
import boto3
import pymysql

def get_rds_auth_token(host, port, user, region):
    client = boto3.client('rds', region_name=region)
    return client.generate_db_auth_token(
        DBHostname=host,
        Port=port,
        DBUsername=user,
        Region=region
    )

token = get_rds_auth_token(
    host="prod-mysql.xxxx.ap-northeast-2.rds.amazonaws.com",
    port=3306,
    user="iam_user",
    region="ap-northeast-2"
)

conn = pymysql.connect(
    host="prod-mysql.xxxx.ap-northeast-2.rds.amazonaws.com",
    user="iam_user",
    password=token,
    database="mydb",
    ssl={"ca": "/path/to/rds-ca.pem"}
)
```

IAM DB 인증은 SSL을 요구한다. SSL 없이 연결하면 거부된다.

### IAM DB 인증의 한계

장점만 보고 모든 상황에 적용하면 문제가 생긴다.

**토큰 발급 비용이 있다.** `generate_db_auth_token`은 매번 IAM 서비스에 HTTP 요청을 보낸다. 커넥션 풀 없이 요청마다 새 연결을 맺는 구조라면, DB 연결 전에 IAM 호출이 추가로 들어가 레이턴시가 높아진다. 커넥션 풀을 쓰는 구조에서는 풀이 연결을 유지하므로 토큰 발급 빈도가 낮아 문제없다.

**토큰 유효 시간이 15분이다.** 커넥션 풀이 연결을 오래 유지하면 토큰이 만료되어도 기존 커넥션은 계속 쓸 수 있다. 문제는 커넥션이 끊겼다가 재연결할 때다. 15분 전에 발급받은 토큰으로 재연결 시도하면 인증 실패가 난다. 토큰을 커넥션 풀 재연결 시점에 새로 발급받도록 구현해야 한다.

**Lambda처럼 연결이 일회성인 환경은 안 맞는다.** Lambda는 콜드 스타트마다 새 연결을 맺는데, 그때마다 IAM 토큰 발급이 들어간다. 이런 환경은 RDS Proxy + Secrets Manager 조합이 더 낫다.

**per-user 권한 제어는 가능하지만, DB 사용자와 IAM 사용자/역할을 매핑해서 관리해야 한다.** 사용자가 많아지면 관리 복잡도가 올라간다.

## Secrets Manager 연동과 자격증명 자동 교체

비밀번호를 코드에 박거나 환경 변수에 두는 방식의 문제는 교체가 어렵다는 것이다. 누가 봤는지 알 수 없고, 유출되어도 바꾸면 앱 전체를 재배포해야 한다.

Secrets Manager는 RDS 자격증명을 저장하고, 설정한 주기마다 자동으로 교체해 준다. 교체 시 Secrets Manager가 Lambda를 호출해 새 비밀번호를 생성하고 DB에 반영한 뒤 시크릿 값을 업데이트한다. 앱은 DB에 연결할 때마다 Secrets Manager에서 현재 유효한 자격증명을 읽어 쓴다.

**Secrets Manager에 RDS 자격증명 저장**

```bash
aws secretsmanager create-secret \
  --name prod/rds/mysql \
  --secret-string '{
    "username": "admin",
    "password": "initial-password",
    "engine": "mysql",
    "host": "prod-mysql.xxxx.ap-northeast-2.rds.amazonaws.com",
    "port": 3306,
    "dbname": "mydb"
  }'
```

**자동 교체 설정**

```bash
aws secretsmanager rotate-secret \
  --secret-id prod/rds/mysql \
  --rotation-rules AutomaticallyAfterDays=30 \
  --rotate-immediately
```

RDS 통합 자동 교체를 쓰면 Lambda 함수를 직접 작성하지 않아도 된다. Secrets Manager 콘솔에서 "AWS가 관리하는 교체 함수 사용"을 선택하거나, Terraform으로 설정한다.

```hcl
resource "aws_secretsmanager_secret" "rds" {
  name = "prod/rds/mysql"
}

resource "aws_secretsmanager_secret_version" "rds" {
  secret_id = aws_secretsmanager_secret.rds.id
  secret_string = jsonencode({
    username = "admin"
    password = var.db_password
    engine   = "mysql"
    host     = aws_db_instance.mysql.endpoint
    port     = 3306
    dbname   = "mydb"
  })
}

resource "aws_secretsmanager_secret_rotation" "rds" {
  secret_id           = aws_secretsmanager_secret.rds.id
  rotation_lambda_arn = aws_lambda_function.rds_rotation.arn

  rotation_rules {
    automatically_after_days = 30
  }
}
```

**앱에서 Secrets Manager로 자격증명 읽기**

```python
import boto3
import json
import pymysql
from functools import lru_cache

@lru_cache(maxsize=1)
def get_db_credentials():
    client = boto3.client('secretsmanager', region_name='ap-northeast-2')
    response = client.get_secret_value(SecretId='prod/rds/mysql')
    return json.loads(response['SecretString'])

def get_connection():
    creds = get_db_credentials()
    return pymysql.connect(
        host=creds['host'],
        user=creds['username'],
        password=creds['password'],
        database=creds['dbname'],
        port=creds['port']
    )
```

주의할 점이 있다. 자격증명을 캐싱하면 교체 시점에 구 비밀번호로 계속 연결을 시도해 실패한다. 캐시 TTL을 교체 주기보다 짧게 잡거나, 연결 실패 시 캐시를 무효화하고 재조회하는 로직이 필요하다.

```python
import time

_cache = {}
_cache_ttl = 3600  # 1시간

def get_db_credentials():
    now = time.time()
    if 'creds' not in _cache or now - _cache.get('fetched_at', 0) > _cache_ttl:
        client = boto3.client('secretsmanager', region_name='ap-northeast-2')
        response = client.get_secret_value(SecretId='prod/rds/mysql')
        _cache['creds'] = json.loads(response['SecretString'])
        _cache['fetched_at'] = now
    return _cache['creds']

def get_connection():
    try:
        creds = get_db_credentials()
        return pymysql.connect(
            host=creds['host'],
            user=creds['username'],
            password=creds['password'],
            database=creds['dbname'],
            port=creds['port']
        )
    except pymysql.err.OperationalError:
        # 인증 실패 시 캐시 무효화 후 재시도
        _cache.clear()
        creds = get_db_credentials()
        return pymysql.connect(
            host=creds['host'],
            user=creds['username'],
            password=creds['password'],
            database=creds['dbname'],
            port=creds['port']
        )
```

Secrets Manager는 API 호출당 비용이 든다. 요청이 많은 서비스에서 매 DB 연결마다 API를 호출하면 비용이 쌓인다. 적절한 캐시 전략이 필요하다.

Secrets Manager 자동 교체와 RDS Proxy를 함께 쓰면 교체 중 커넥션 끊김 없이 자격증명이 바뀐다. RDS Proxy가 새 자격증명을 투명하게 처리해주기 때문이다.

## 보안 설정 조합

실무에서 쓰는 구성을 정리하면 다음과 같다.

소규모 서비스나 팀 규모가 작을 때는 VPC Private Subnet + Security Group + KMS 암호화 + SSL/TLS 강제 + Secrets Manager 정도로 기반을 잡는다. IAM DB 인증은 커넥션 풀 관리가 복잡해지므로, 이 조합으로도 충분한 경우가 많다.

금융이나 규제 산업처럼 엄격한 컴플라이언스가 있는 환경은 여기에 고객 관리형 KMS 키, 감사 로그(MySQL Audit Plugin 또는 CloudTrail 데이터 이벤트), IAM DB 인증, Secrets Manager 교체 주기 단축(7~14일)을 더한다.

어떤 조합이든 저장 데이터 암호화와 SSL 강제, Private Subnet 배치는 기본값으로 잡고 시작한다. 나중에 추가하는 것은 다운타임이나 복잡한 마이그레이션 작업이 따른다.

## 참조

- [RDS.md](RDS.md)
- [DB_Proxy.md](DB_Proxy.md)
- AWS RDS 보안 문서: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.html
- AWS Secrets Manager RDS 연동: https://docs.aws.amazon.com/secretsmanager/latest/userguide/integrating_how-services-use-secrets_RDS.html
