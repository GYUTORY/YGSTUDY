---
title: Railway 네트워킹
tags: [cloud, backend, docker, devops]
updated: 2026-09-07
---

## 프로젝트 내부 네트워크

Railway 프로젝트 안에서 서비스끼리 통신할 때 퍼블릭 인터넷을 거치지 않는다. 각 서비스는 자동으로 `.railway.internal` 도메인을 받고, 이 도메인은 프로젝트 내부 네트워크에서만 해석된다.

형식은 `{서비스명}.railway.internal`이다. 서비스 이름에 공백이 있으면 하이픈으로 바뀐다. `api-server`라는 서비스는 `api-server.railway.internal`로 접근한다.

```env
DATABASE_URL=postgresql://user:password@postgres.railway.internal:5432/mydb
REDIS_URL=redis://redis.railway.internal:6379
```

퍼블릭 도메인으로 서비스 간 통신하면 Railway CDN을 타고 돌아온다. 레이턴시도 늘고 불필요한 트래픽 비용도 붙는다. 같은 프로젝트 안에서는 `.railway.internal`만 쓴다.

### 포트 번호

`.railway.internal`을 쓸 때 포트는 서비스가 실제로 바인딩하는 값 그대로다. Railway가 `PORT` 환경변수를 자동으로 주입하는데, 앱이 이 값을 읽어서 리슨해야 한다. `app.listen(3000)`처럼 하드코딩하면 Railway가 주입한 포트와 불일치가 생겨 헬스체크에서 죽는다.

```javascript
const port = process.env.PORT || 3000;
app.listen(port);
```

## 포트 충돌이 없는 이유

Docker 네트워크 격리 때문이다. Railway의 각 서비스는 별도 컨테이너로 실행되고, 각 컨테이너에는 독립된 네트워크 네임스페이스가 있다. A 서비스가 8080에서 리슨하고 B 서비스도 8080에서 리슨해도 서로 다른 네임스페이스에 있어서 충돌이 없다.

`.railway.internal` 도메인 해석도 Railway 내부 DNS가 서비스 이름을 컨테이너 IP로 매핑하는 구조라, 포트는 각 컨테이너 기준이다. PostgreSQL, Redis, 앱 서버를 전부 같은 포트로 띄워도 문제가 없다.

## 퍼블릭 도메인

### 자동 생성 도메인

서비스에 퍼블릭 엔드포인트를 붙이면 Railway가 `{랜덤}-production.up.railway.app` 형식의 도메인을 자동으로 만든다. HTTPS가 기본으로 붙고, 인증서 관리는 Railway가 처리한다.

자동 도메인은 서비스를 삭제하고 다시 만들면 주소가 바뀐다. 외부 시스템이 이 주소를 하드코딩했다면 깨진다. 웹훅 URL이나 OAuth 리다이렉트 URL에 자동 도메인을 쓰면 이런 상황이 생긴다.

### 커스텀 도메인 연결

Railway 대시보드에서 커스텀 도메인을 추가하면 CNAME 레코드 값을 알려준다. DNS 제공자에서 이 CNAME을 설정하면 인증서 발급까지 자동으로 처리된다.

```
CNAME: {서비스명}.up.railway.app
```

CNAME 전파는 5분에서 최대 48시간까지 걸린다. Railway 대시보드의 "Verify DNS" 버튼이 전파 전에는 계속 실패로 나온다. 기다리면 자동으로 통과된다.

루트 도메인(`example.com`)에는 CNAME을 쓸 수 없다는 DNS 스펙 제약이 있다. Cloudflare의 CNAME Flattening이나 AWS Route53의 ALIAS 레코드로 해결한다. 일반 호스팅 제공자에서 루트 도메인을 Railway에 붙이려면 이 제약을 먼저 확인해야 한다.

## TCP Proxy

HTTP가 아닌 프로토콜을 쓰는 서비스—PostgreSQL, Redis, MySQL 등—를 외부에서 직접 접속하려면 TCP Proxy를 활성화해야 한다.

서비스의 "Settings" > "Networking" 탭에서 TCP Proxy를 켜면 두 가지를 준다.

- 호스트: `roundhouse.proxy.rlwy.net` 형식의 주소
- 포트: 랜덤 5자리 포트 번호

```
postgresql://user:password@roundhouse.proxy.rlwy.net:12345/mydb
```

데이터베이스 GUI 툴이나 외부 서버에서 마이그레이션을 돌릴 때 이 주소를 쓴다. 구조는 외부 → TCP Proxy → 내부 컨테이너 포트 순서다.

### 주의사항

연결 수 제한이 있다. 무료 플랜에서는 TCP Proxy 연결이 자주 끊긴다. 프로덕션 데이터베이스를 외부에서 상시 연결해두는 용도로는 적합하지 않다.

TCP Proxy 레벨의 SSL 처리에는 Railway가 관여하지 않는다. PostgreSQL의 경우 `sslmode=require`를 쓰면 데이터베이스 자체의 SSL 설정을 따른다. Postgres가 SSL을 비활성화한 상태면 연결이 실패한다.

```
postgresql://user:password@proxy-host:port/db?sslmode=disable
```

로컬 개발에서 Railway 데이터베이스에 붙을 때 `sslmode=disable`로 시작해서 연결부터 확인하는 게 빠르다.

## 서비스 참조로 주소 주입

Railway의 서비스 참조(Service References) 기능으로 다른 서비스의 환경변수를 가져온다. `${{서비스명.변수명}}` 문법을 쓴다.

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
```

Railway가 자동으로 주입하는 변수도 있다.

```env
RAILWAY_PRIVATE_DOMAIN=api-server.railway.internal
RAILWAY_PUBLIC_DOMAIN=api-server-production.up.railway.app
PORT=3000
```

서비스 이름을 바꾸면 `RAILWAY_PRIVATE_DOMAIN`도 바뀐다. 다른 서비스에서 `.railway.internal` 주소를 하드코딩했다면 이름 변경 시 같이 수정해야 한다.