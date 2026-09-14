---
title: Railway 플랫폼 개요
tags: [cloud, devops, docker, backend, ci-cd]
updated: 2026-09-14
---

# Railway 플랫폼 개요

Railway는 코드를 푸시하면 빌드·배포를 자동으로 처리해 주는 PaaS다. Heroku가 무료 플랜을 폐지한 이후 마이그레이션 대상으로 자주 거론됐고, 사이드 프로젝트나 스테이징 환경 용도로 실제로 많이 쓰인다.

## 프로젝트 / 서비스 / 환경 구조

Railway의 계층은 세 단계다.

**프로젝트(Project)** 가 최상위 단위다. 하나의 프로젝트 안에 여러 서비스가 들어간다. 청구도 프로젝트 단위로 집계된다.

**서비스(Service)** 는 실제로 실행되는 단위다. GitHub 레포를 연결하거나, Docker 이미지를 직접 지정하거나, Railway가 제공하는 데이터베이스 플러그인(PostgreSQL, Redis, MySQL 등)을 추가하면 서비스가 생긴다. 하나의 프로젝트에 API 서버, 워커, DB를 묶어 두는 것이 일반적인 구성이다.

**환경(Environment)** 은 같은 서비스 설정을 여러 맥락으로 복제해 쓰는 개념이다. production과 staging을 별도 환경으로 만들면, 서비스 정의는 공유하되 환경 변수나 연결된 브랜치만 다르게 유지된다. Heroku 파이프라인과 비슷하지만 UI가 더 직관적이다.

서비스 간 통신은 프로젝트 내부 도메인으로 처리한다. 같은 프로젝트 안의 서비스끼리 `<service-name>.railway.internal` 형태의 내부 주소를 자동으로 부여한다. 외부에 노출할 필요 없는 DB나 캐시는 퍼블릭 도메인을 열지 않고 이 주소만 쓰면 된다.

## GitHub 연동 배포 흐름

GitHub 레포를 서비스에 연결하면 지정한 브랜치에 푸시가 발생할 때마다 자동으로 빌드·배포가 트리거된다. PR 브랜치에 대해 미리보기 환경을 자동 생성하는 기능도 있다.

배포 흐름은 이렇다.

1. 레포 연결 → 트리거 감지 브랜치 설정
2. Railway가 코드를 클론해 빌드 실행
3. 빌드 성공 시 새 인스턴스로 트래픽 전환(무중단)
4. 롤백이 필요하면 대시보드에서 이전 배포를 클릭해 재활성화

배포 로그는 실시간으로 스트리밍되고, 빌드 단계와 실행 단계 로그가 분리돼 있어서 어디서 죽었는지 찾기 쉽다.

## Nixpacks vs Dockerfile

Railway는 두 가지 빌드 방식을 지원한다.

**Nixpacks**는 Railway의 기본 빌더다. `package.json`, `requirements.txt`, `go.mod` 같은 파일을 보고 언어와 런타임을 자동 감지해 빌드 명령과 시작 명령을 추론한다. 별도 설정 없이 바로 배포할 수 있다.

단점은 감지가 틀릴 때 디버깅이 번거롭다는 것이다. 모노레포 구조이거나 커스텀 빌드 스텝이 있으면 잘못된 명령을 추론해 빌드가 조용히 깨지는 경우가 있다. 이런 경우 `nixpacks.toml`로 빌드 페이즈를 명시할 수 있다.

**Dockerfile**은 루트에 `Dockerfile`이 있으면 자동으로 이걸 쓴다. Nixpacks보다 명시적이고 재현성이 높다. 멀티스테이지 빌드도 잘 동작한다. 프로덕션에서 쓸 서비스라면 Dockerfile로 관리하는 것이 낫다.

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY --from=build /app/node_modules ./node_modules
EXPOSE 3000
CMD ["node", "dist/main.js"]
```

Nixpacks와 Dockerfile이 둘 다 있으면 Dockerfile이 우선이다.

## PORT 환경변수를 읽지 않으면 배포가 죽는다

Railway 배포에서 가장 흔히 겪는 문제가 포트 바인딩이다. Railway는 컨테이너가 바인딩해야 하는 포트를 `PORT` 환경변수로 알려준다. 서버가 이 변수를 읽지 않고 하드코딩된 포트에 바인딩하면 헬스체크가 실패하고 배포가 계속 재시작된다.

```javascript
// Railway에서 죽는 코드
app.listen(3000);

// 환경변수를 읽어야 한다
const port = process.env.PORT || 3000;
app.listen(port);
```

에러 메시지가 명확하지 않아서 처음엔 원인 파악이 어렵다. 배포 로그에서 `HEALTHCHECK failed` 또는 타임아웃 메시지가 반복되면 거의 이 문제다.

Spring Boot도 마찬가지다.

```properties
# application.properties
server.port=${PORT:8080}
```

```python
# Django
import os
port = int(os.environ.get("PORT", 8000))
```

Railway 도메인으로 들어오는 트래픽은 항상 443(HTTPS)이고, Railway가 내부에서 `PORT`로 프록시해 준다. 서버에서 TLS를 직접 처리할 필요는 없다.

## 헬스체크 설정

Railway는 Service Settings의 Health Check 탭에서 HTTP 헬스체크를 구성한다. 설정하지 않으면 Railway는 프로세스가 살아있는지만 확인하고, 실제로 HTTP 응답을 반환하는 상태인지는 모른다.

문제가 되는 상황은 앱이 완전히 뜨기 전에 Railway가 "배포 완료"로 판단하고 트래픽을 넘기는 경우다. DB 커넥션 풀 초기화나 캐시 워밍업이 끝나기 전에 요청이 들어오면 500 또는 503이 발생한다. 헬스체크 경로를 설정해 두면 Railway가 그 경로에서 200을 받기 전까지 트래픽을 넘기지 않는다.

설정 항목은 세 가지다. **경로(Health Check Path)** 는 Railway가 GET 요청을 보낼 엔드포인트다. `/health`나 `/ping` 같은 전용 경로를 만들어 두면 된다. 메인 비즈니스 로직을 거치지 않는 단순 200 응답으로 충분하다. **타임아웃(Timeout)** 은 기본값이 300초인데, JVM 기반 애플리케이션은 콜드 스타트가 길어서 기본값 안에 간신히 응답하거나 실패하는 경우가 있다. **시작 대기(Start Period)** 는 컨테이너 시작 직후 헬스체크를 몇 초 뒤부터 시작할지 지정한다. 시작 직후 실패를 재시작 카운트에 포함시키지 않기 위해 쓴다.

`railway.toml`로 관리하면 대시보드 설정과 일치 여부를 걱정하지 않아도 된다.

```toml
[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 60
```

## 재시작 정책

프로세스가 비정상 종료됐을 때 Railway가 어떻게 반응할지는 Service Settings의 Restart Policy에서 결정한다. 기본값은 `ALWAYS`로, 종료 코드에 상관없이 프로세스가 죽으면 다시 띄운다.

문제는 앱에 버그가 있어서 시작하자마자 죽는 경우다. 재시작이 반복되면서 Crash Loop 상태가 되고, 로그를 보면 시작과 종료가 몇 초 간격으로 반복되는 패턴이 보인다. 재시작 간격은 지수 백오프로 늘어나므로(1s → 2s → 4s) 초기에는 빠르게 재시도하다가 점점 느려진다. 환경변수를 빼먹거나 DB 연결 설정이 잘못됐을 때 이 패턴이 자주 나온다.

`ON_FAILURE`는 종료 코드가 0이 아닐 때만 재시작한다. 배치 작업처럼 정상 종료(exit 0)하는 서비스에 `ALWAYS`를 걸면 계속 재시작되므로 주의한다. `railway.toml`에서 지정할 수 있다.

```toml
[deploy]
restartPolicyType = "ON_FAILURE"
```

## 리소스 제한

Railway는 서비스별로 RAM과 CPU 상한선을 직접 설정한다. 설정하지 않으면 플랜 한도 내에서 최대 8GB RAM, 8 vCPU까지 쓸 수 있다. 제한이 없으면 메모리 누수가 있는 서비스가 계속 자라도 Railway가 알아서 종료하지 않아 크레딧 소진이 빨라진다.

Service Settings → Resources 탭에서 슬라이더로 설정하거나 `railway.toml`로 관리한다.

```toml
[deploy]
memoryLimit = "512Mi"
cpuLimit = "0.5"
```

메모리 한도를 넘으면 OOMKilled로 컨테이너가 종료되고 재시작 정책에 따라 다시 뜬다. 한도를 얼마로 설정할지 감이 없으면 일단 512Mi로 시작해서 Metrics 탭에서 실제 사용량을 보고 조정한다. 간단한 REST API 서버는 128~256Mi로 충분한 경우가 많다.

`railway.toml`에서 지정하지 않으면 배포할 때마다 대시보드 설정이 초기화될 수 있으므로 파일로 관리하는 것이 낫다.

## 크론잡과 워커 서비스

Railway는 웹 서버 외에 두 가지 서비스 타입을 지원한다.

**크론(Cron) 서비스**는 주기적으로 실행되고 종료하는 작업용이다. 서비스를 추가할 때 Cron을 선택하면 cron 표현식으로 실행 주기를 지정한다. 실행할 때마다 컨테이너가 올라와서 작업을 마치고 종료하는 구조라 상시 실행 비용이 없다. 단, 매 실행마다 콜드 스타트 비용이 있다. 배치 집계나 알림 발송처럼 주기적으로 실행해야 하는 작업에 쓴다.

```toml
[deploy]
cronSchedule = "0 2 * * *"  # 매일 새벽 2시
```

**워커(Worker) 서비스**는 HTTP 포트를 열지 않고 백그라운드에서 계속 실행되는 서비스다. 메시지 큐에서 작업을 꺼내 처리하거나 스트림을 소비하는 컨슈머를 올릴 때 쓴다. 퍼블릭 도메인이 필요 없으므로 노출하지 않은 상태로 실행된다. 포트를 열지 않으니 헬스체크는 프로세스 상태로만 확인된다.

## 플랜 구조와 크레딧 소진 예측

Railway는 2023년부터 무료 Starter 플랜을 대폭 축소했다.

**Starter(무료 플랜)** 는 월 $5 크레딧이 제공된다. Heroku 무료 플랜처럼 30분 비활성 시 슬립이 걸리는 구조가 아니다. 슬립 없이 항상 실행되는 대신 사용량만큼 크레딧이 닳는다. 크레딧이 소진되면 서비스가 중단된다.

**Hobby 플랜** 은 월 $5 구독료를 내면 $5 크레딧이 추가로 붙어 총 $10 크레딧을 쓸 수 있다. 커스텀 도메인 지원, 서비스 수 제한 없음이 핵심이다. 사이드 프로젝트 하나를 안정적으로 운영하려면 이 플랜이 현실적이다.

**Pro 플랜** 은 팀 단위 사용을 위한 플랜이다. 크레딧 개념 대신 사용량 기반 과금으로 바뀐다.

크레딧 소진 속도를 예측하는 가장 빠른 방법은 Usage 탭에서 "Current Month Estimate"를 확인하는 것이다. 몇 시간만 실행해도 Railway가 이 속도로 계속 쓰면 한 달에 얼마가 나온다고 추정치를 보여준다. 처음 배포하고 하루 지나면 예측값이 어느 정도 안정된다.

대략적인 기준으로는 512Mi RAM / 0.5 vCPU로 제한한 Node.js 서버 한 개가 상시 실행될 때 월 $1~2 정도 소비한다. PostgreSQL 플러그인을 붙이면 $2~3이 추가된다. DB 쿼리가 많거나 트래픽이 있으면 더 나온다. Starter $5로 서버 + DB 조합을 한 달 내내 유지하면 크레딧이 빠듯하다.

크레딧 알림은 대시보드 설정에서 임계값을 설정해 이메일로 받을 수 있다. 설정해 두지 않으면 갑자기 서비스가 멈추고 나서야 소진됐다는 걸 안다.

## 리전 제약

Railway는 미국(US West, US East)과 유럽(EU West) 리전을 지원한다. 서비스를 생성할 때 리전을 선택할 수 있지만, 실행 중인 서비스를 다른 리전으로 옮기는 기능은 없다. 리전을 바꾸려면 서비스를 다시 만들어야 한다.

아시아 리전은 없다. 한국에서 운영하는 서비스라면 US West가 레이턴시 면에서 EU보다 낫지만, AWS 서울 리전 대비 왕복 100~150ms 정도 차이가 난다. 관리 도구나 사이드 프로젝트는 문제가 안 되지만, 실시간 요구사항이 있는 서비스에는 이 제약이 병목이 된다. Railway를 선택하기 전에 레이턴시 요구사항을 먼저 확인해야 한다.

## 배포 후 서비스가 올라오지 않을 때

문제 유형은 대부분 세 가지 중 하나다.

PORT 바인딩 문제는 헬스체크 실패와 계속되는 재시작 루프로 나타난다. 배포 로그 맨 아래에 "healthcheck failed" 또는 "no response from application"이 반복되면 포트 설정부터 확인한다. 위에서 설명한 대로 `process.env.PORT`를 읽도록 수정하면 해결된다.

DB 연결 실패는 서비스가 시작되고 수 초 내에 종료되는 패턴으로 나타난다. 로그에 `connection refused`나 `authentication failed`가 찍힌다. 같은 프로젝트 내부에서 PostgreSQL에 연결할 때 내부 URL과 외부 URL을 혼동하는 경우가 많다. 내부 URL은 `<service-name>.railway.internal:5432`고, Railway가 `DATABASE_PRIVATE_URL` 환경변수로 자동 주입한다. `DATABASE_URL`은 외부 접속용이라 포트가 다르다.

빌드는 성공했는데 앱이 시작하자마자 죽는 경우는 환경변수 누락이 원인인 경우가 많다. 로컬에서는 `.env` 파일로 주입하던 값들을 Railway Variables 탭에 등록하지 않으면, 시작할 때 `undefined`를 읽다가 예외를 던지고 종료된다. Railway 대시보드의 Variables 탭과 로컬 `.env`를 대조하면 빠진 항목이 바로 보인다.
