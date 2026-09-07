---
title: Railway 데이터베이스 서비스
tags: [cloud, database, rdbms, postgresql, mysql, redis, nosql, mongodb, backend]
updated: 2026-09-07
---

# Railway 데이터베이스 서비스

Railway에서 데이터베이스는 별도 서버 없이 프로젝트 안에 서비스 형태로 추가한다. PostgreSQL, MySQL, Redis, MongoDB 네 종류를 제공한다. 서비스를 추가하는 순간 컨테이너가 뜨고, 접속 정보가 담긴 환경변수가 같은 프로젝트의 다른 서비스에 자동으로 주입된다.

## 데이터베이스 서비스 추가

대시보드에서 프로젝트를 열고 `+ New Service` → `Database`를 선택하면 된다. CLI로도 추가할 수 있다.

```bash
# PostgreSQL 추가
railway add --database postgresql

# MySQL 추가
railway add --database mysql

# Redis 추가
railway add --database redis

# MongoDB 추가
railway add --database mongodb
```

CLI로 추가하면 프로젝트에 데이터베이스 서비스가 생기고 잠시 후 실행 상태가 된다. 서비스 이름은 `postgresql-<random>` 형태로 자동 부여된다. 이름을 바꾸려면 대시보드에서 서비스 설정으로 들어가 수동으로 변경한다.

Railway가 제공하는 데이터베이스는 Docker 이미지 기반이다. PostgreSQL은 `postgres:16`, MySQL은 `mysql:8`처럼 Railway가 고정한 버전을 쓴다. 버전을 직접 지정하려면 커스텀 서비스로 Docker 이미지를 직접 등록해야 한다. Railway 제공 DB 서비스는 버전 선택 UI가 없다.

## DATABASE_URL 환경변수 자동 주입

데이터베이스 서비스를 추가하면 Railway가 접속 정보를 환경변수로 생성한다. 이 환경변수들은 같은 프로젝트 안의 다른 서비스에서 `${{Postgresql.DATABASE_URL}}` 형태로 참조할 수 있다. 변수 참조 문법은 Railway가 빌드·실행 시에 실제 값으로 치환한다.

PostgreSQL을 추가하면 다음 변수들이 생긴다.

```
PGHOST        = postgres.railway.internal   (내부 네트워크 주소)
PGPORT        = 5432
PGDATABASE    = railway
PGUSER        = postgres
PGPASSWORD    = <자동 생성된 패스워드>
DATABASE_URL  = postgresql://postgres:<password>@postgres.railway.internal:5432/railway
```

다른 서비스의 환경변수 설정 화면에서 `${{Postgresql.DATABASE_URL}}`을 입력하면 데이터베이스 서비스가 생성한 값을 그대로 가져다 쓴다. 값을 복사해서 하드코딩하지 않아도 된다.

```bash
# API 서비스의 환경변수 설정 예시
DATABASE_URL=${{Postgresql.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
```

MongoDB는 변수 이름이 조금 다르다.

```
MONGO_URL       = mongodb://mongo:<password>@mongodb.railway.internal:27017/railway
MONGOHOST       = mongodb.railway.internal
MONGOPASSWORD   = <패스워드>
MONGOPORT       = 27017
MONGOUSER       = mongo
```

Redis는 `REDIS_URL`이 핵심 변수다. `redis://default:<password>@redis.railway.internal:6379` 형태다.

자동 주입 구조의 주의점이 있다. 참조 문법 `${{서비스명.변수명}}`은 Railway 대시보드에서만 동작한다. 로컬 `.env` 파일에 저 문자열을 그대로 쓰면 연결이 안 된다. 로컬에서 Railway DB에 붙어야 할 때는 퍼블릭 접속 URL을 따로 복사해서 써야 한다.

## 프라이빗 네트워크와 퍼블릭 접속

Railway 프로젝트 안의 서비스들은 `.railway.internal` 도메인으로 서로 연결된다. 이 주소는 같은 프로젝트 내부에서만 라우팅되고 외부에서는 접근할 수 없다.

```
# 내부 접속 (같은 프로젝트 서비스끼리)
postgresql://postgres:<password>@postgres.railway.internal:5432/railway

# 퍼블릭 접속 (외부 도구, 로컬 개발)
postgresql://postgres:<password>@roundhouse.proxy.rlwy.net:<port>/railway
```

퍼블릭 접속 URL은 기본적으로 비활성화다. 대시보드에서 데이터베이스 서비스를 선택하고 `Connect` 탭에서 Public Network를 켜야 외부에서 접속할 수 있는 주소와 포트가 생긴다.

퍼블릭 접속을 열면 포트 번호가 5432가 아니라 Railway가 임의로 배정한 번호가 된다. 예를 들면 `roundhouse.proxy.rlwy.net:12345` 같은 식이다. 이 포트는 변경될 수 있으므로 외부 서비스나 CI에서 퍼블릭 URL을 박아두면 어느 시점에 연결이 끊기는 경우가 생긴다. 퍼블릭 URL은 로컬 개발과 DB 클라이언트 접속 용도로만 쓰는 것이 낫다.

퍼블릭 접속을 열어두면 보안 면에서 주의가 필요하다. Railway는 자동 생성된 강한 패스워드를 쓰지만, DB 포트가 인터넷에 노출된다. 운영 환경에서는 퍼블릭 접속을 꺼두고 내부 네트워크만 쓰는 편이 낫다. 로컬에서 테스트할 일이 생기면 그때만 켜고 끄는 방식이 현실적이다.

내부 네트워크 지연은 외부 접속보다 눈에 띄게 낮다. 같은 Railway 리전 안에서 `.railway.internal`로 연결하면 왕복 1ms 이내인 경우가 대부분이다. 같은 프로젝트 안에서 DB에 연결할 때는 항상 내부 주소를 써야 한다.

```javascript
// 환경별로 URL을 나누는 패턴
const dbUrl = process.env.DATABASE_URL;
// Railway에서 실행 중이면 내부 URL이 주입됨
// 로컬에서는 .env에 퍼블릭 URL을 넣어서 씀
```

## 데이터 볼륨과 퍼시스턴스

Railway 데이터베이스 서비스는 기본적으로 퍼시스턴트 볼륨을 자동으로 마운트한다. PostgreSQL이나 MySQL을 추가하면 Railway가 내부적으로 볼륨을 생성하고 데이터 디렉토리에 마운트한다. 재배포가 일어나도 데이터가 유지된다.

문제는 이 볼륨이 눈에 잘 안 보인다는 점이다. 대시보드에서 해당 DB 서비스를 클릭하면 `Volumes` 탭에서 마운트된 볼륨을 확인할 수 있다. 용량 사용량도 여기서 본다.

볼륨 용량 상한에 부딪히면 DB가 쓰기를 거부한다. Railway Starter·Hobby 플랜에서 기본 볼륨 크기는 1GB다. 대시보드에서 볼륨 크기를 늘릴 수 있지만, 늘린 용량만큼 비용이 추가된다. 볼륨 크기를 줄이는 건 지원하지 않는다. 한 번 늘리면 줄일 수 없다.

Redis는 기본 설정이 인메모리다. 별도 볼륨을 지정하지 않으면 서비스가 재시작될 때 데이터가 날아간다. 세션이나 캐시 용도라면 이 기본 동작이 문제없지만, 큐나 Pub/Sub처럼 재시작 후에도 남아 있어야 하는 데이터는 RDB 또는 AOF 퍼시스턴스를 활성화해야 한다.

Railway에서 Redis 퍼시스턴스를 켜려면 해당 서비스의 Variables 탭에서 설정을 추가한다.

```
# RDB 스냅샷 방식 (900초 안에 변경 1건 이상이면 저장)
REDIS_ARGS=--save 900 1 --appendonly no

# AOF 방식 (모든 쓰기 로그 보존, 재시작 시 재생)
REDIS_ARGS=--appendonly yes --appendfsync everysec
```

공식 Railway Redis 서비스 이미지가 `REDIS_ARGS` 환경변수를 `redis-server`에 넘긴다. 이 방법으로 퍼시스턴스를 활성화하면 볼륨이 없으면 의미가 없다. Volumes 탭에서 볼륨을 먼저 마운트해야 한다.

MongoDB는 별도 볼륨 설정 없이도 Railway가 자동으로 데이터를 퍼시스턴트 스토리지에 저장한다.

## 서비스 삭제 시 데이터 삭제

여기서 가장 많이 데이는 부분이다.

Railway에서 데이터베이스 서비스를 삭제하면 그 서비스에 연결된 볼륨도 함께 삭제된다. 백업 없이 서비스를 지우면 데이터는 복구 불가능하다. 대시보드에서 서비스 삭제 버튼을 누를 때 경고창이 뜨지만, 빠르게 클릭하다 보면 지나치기 쉽다.

환경(Environment)을 삭제할 때도 같은 문제가 생긴다. production 환경을 잘못 지우면 그 안의 DB 서비스와 볼륨이 통째로 날아간다.

프로젝트를 삭제하는 것도 마찬가지다. 프로젝트 삭제는 모든 서비스와 볼륨을 포함해서 지운다.

Railway 자체에는 자동 스냅샷 기능이 없다. 데이터 보호는 직접 해야 한다.

PostgreSQL 백업은 `pg_dump`로 한다.

```bash
# railway run으로 Railway의 DB에 연결된 상태에서 덤프
railway run pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# 또는 퍼블릭 URL을 직접 넣어서
pg_dump "postgresql://postgres:<password>@roundhouse.proxy.rlwy.net:<port>/railway" \
  > backup_$(date +%Y%m%d).sql
```

MySQL은 `mysqldump`를 쓴다.

```bash
mysqldump -h <퍼블릭호스트> -P <포트> -u root -p<password> railway \
  > backup_$(date +%Y%m%d).sql
```

MongoDB는 `mongodump`다.

```bash
mongodump --uri="mongodb://mongo:<password>@<퍼블릭호스트>:<포트>/railway" \
  --out=./backup_$(date +%Y%m%d)
```

정기 백업이 필요하면 GitHub Actions를 써서 크론으로 돌리거나, Railway 안에 별도 워커 서비스를 만들어 스케줄로 실행하는 방식을 쓴다. Railway 자체의 크론 지원은 서비스 설정의 `Cron Schedule` 필드로 처리한다.

볼륨 삭제 없이 DB 서비스를 재배포하거나 설정을 바꾸는 작업은 데이터에 영향을 주지 않는다. 서비스 재시작이나 재배포 자체는 볼륨을 건드리지 않는다. 데이터가 날아가는 경우는 서비스 삭제, 환경 삭제, 프로젝트 삭제 세 가지다.
