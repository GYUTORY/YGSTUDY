---
title: Railway 플랫폼 개요
tags: [cloud, devops, docker, backend, ci-cd]
updated: 2026-09-07
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

## 플랜 구조와 무료 플랜 제약

Railway는 2023년부터 무료 Starter 플랜을 대폭 축소했다.

**Starter(무료 플랜)** 는 월 $5 크레딧이 제공된다. 슬립 모드 없이 항상 실행되지만, 크레딧이 소진되면 서비스가 중단된다. 리소스 사용량(CPU, 메모리, 네트워크)에 따라 크레딧이 차감되므로, 간단한 API 서버는 한 달 내내 돌려도 크레딧이 남을 수 있고, DB까지 붙이면 빨리 소진될 수 있다.

Heroku 무료 플랜처럼 30분 비활성 시 슬립이 걸리는 구조가 아니다. 슬립 없이 항상 켜져 있는 대신 사용량만큼 크레딧이 닳는 방식이다.

**Hobby 플랜** 은 월 $5 구독료를 내면 $5 크레딧이 추가로 붙어 총 $10 크레딧을 쓸 수 있다. 커스텀 도메인 지원, 서비스 수 제한 없음이 핵심이다. 사이드 프로젝트 하나를 안정적으로 운영하려면 이 플랜이 현실적이다.

**Pro 플랜** 은 팀 단위 사용을 위한 플랜이다. 팀 멤버 초대, 우선 지원, SLA 보장이 추가된다. 크레딧 개념 대신 사용량 기반 과금으로 바뀐다.

Starter와 Hobby는 서비스당 최대 8GB RAM, 8 vCPU까지 요청할 수 있다. 실제 비용을 추정하려면 Railway 대시보드의 Usage 탭에서 현재 소비 속도를 보는 것이 가장 정확하다. 월 단위 예측값도 보여준다.

## 배포 후 서비스가 올라오지 않을 때

확인 순서는 이렇다.

1. 빌드 로그 — 빌드 자체가 실패했는지
2. 런타임 로그 — 프로세스가 시작됐다가 죽는지
3. `PORT` 환경변수를 실제로 읽는지
4. 헬스체크 경로가 설정돼 있으면 그 경로가 200을 반환하는지

데이터베이스 서비스는 Railway가 내부적으로 관리하므로 직접 연결할 때 외부 접속 URL과 내부 접속 URL이 다르다. 같은 프로젝트 안에서 연결할 때는 내부 URL(`<service>.railway.internal:5432`)을 쓰면 네트워크 레이턴시가 낮다.