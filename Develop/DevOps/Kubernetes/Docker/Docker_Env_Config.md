---
title: 컨테이너 환경변수 관리
tags: [docker, devops, backend, security]
updated: 2026-09-28
---

# 컨테이너 환경변수 관리

## ENV와 ARG는 다른 시점에 산다

Dockerfile에서 환경변수를 다루는 두 키워드가 있는데, 처음 Docker를 쓰면 이 둘을 같은 것으로 오해하는 경우가 많다.

`ARG`는 빌드 시점에만 존재한다. `docker build --build-arg KEY=VALUE`로 넘기고, 빌드가 끝나면 이미지의 환경변수 목록에 남지 않는다. 정확히는, 목록에는 없지만 이 값으로 실행된 레이어 자체는 캐시에 남는다.

`ENV`는 이미지에 구워진다. 빌드 시점에도 쓸 수 있고, 컨테이너를 실행할 때도 살아있다. `docker run -e KEY=VALUE`로 덮어쓸 수 있다.

```dockerfile
ARG BUILD_ENV=production
ENV APP_ENV=$BUILD_ENV
```

이렇게 ARG 값을 ENV로 받으면, ARG는 이미지 목록에 없지만 ENV는 이미지에 박힌다. 이 차이가 시크릿 관리에서 결정적으로 갈린다.

## .env 파일과 --env-file 플래그

이름이 비슷해서 같은 동작을 할 것 같지만 목적이 다르다.

`docker run --env-file .env app`은 파일 안의 `KEY=VALUE` 라인을 컨테이너 환경변수로 전달한다.

Docker Compose에서 `.env` 파일은 다르게 동작한다. Compose 파일 자체의 변수 보간에 쓰인다. `docker-compose.yml` 안의 `${DB_HOST}`를 치환하는 용도다. 이 파일의 내용이 컨테이너 내부로 자동으로 전달되지는 않는다.

```yaml
# docker-compose.yml
services:
  app:
    image: myapp
    environment:
      - DB_HOST=${DB_HOST}   # .env의 DB_HOST를 읽어서 컨테이너 환경변수로 전달
    # env_file: .env.app     # 파일 전체를 컨테이너에 넘길 때는 이 방법
```

컨테이너 내부에 파일 전체를 넘기려면 `env_file:` 키를 써야 한다. `.env` 파일 하나를 두 가지 용도로 혼용하다 보면 "분명히 환경변수 설정했는데 컨테이너에서 왜 없지?" 같은 상황이 생긴다.

`.env` 파일 형식도 미묘하게 다르다. `docker run --env-file`은 주석(`#`)을 지원하고 따옴표를 그대로 값에 포함시킨다. `export KEY=VALUE` 형식은 지원하지 않는다.

## 민감값이 이미지 레이어에 박히는 실수

빌드 중에 API 키나 비밀번호가 필요한 경우가 있다. private npm registry 인증, Maven 리포지토리 자격증명 같은 것들이다. 이걸 ARG로 넘기면 안전하다고 생각하지만, RUN에서 사용하는 순간 레이어에 흔적이 남는다.

```dockerfile
ARG NPM_TOKEN
RUN echo "//registry.npmjs.org/:_authToken=${NPM_TOKEN}" > ~/.npmrc && \
    npm install && \
    rm ~/.npmrc   # 삭제해도 이전 레이어에 이미 기록됨
```

`rm ~/.npmrc`로 지워도 Docker 레이어는 명령 단위로 스냅샷을 찍기 때문에, 이전 레이어에 `.npmrc` 파일이 그대로 남아있다.

```bash
# 이전 레이어를 직접 꺼내서 확인할 수 있다
docker save myimage | tar x -O '*/layer.tar' | tar t 2>/dev/null | grep npmrc
```

멀티스테이지 빌드로 이 문제를 해결한다.

```dockerfile
FROM node:20-alpine AS builder
ARG NPM_TOKEN
RUN echo "//registry.npmjs.org/:_authToken=${NPM_TOKEN}" > ~/.npmrc && \
    npm install && \
    rm ~/.npmrc

# 최종 이미지는 builder 스테이지의 레이어 히스토리를 포함하지 않는다
FROM node:20-alpine
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
```

`COPY --from=builder`는 파일만 복사하고 레이어 메타데이터는 가져오지 않는다. builder 스테이지에 NPM_TOKEN이 있었어도 최종 이미지에서는 볼 수 없다.

Docker BuildKit(Docker 23.0 이상 기본 활성화)을 쓰면 `--mount=type=secret`으로 더 깔끔하게 처리할 수 있다.

```dockerfile
# syntax=docker/dockerfile:1
FROM node:20-alpine AS builder
RUN --mount=type=secret,id=npmtoken \
    NPM_TOKEN=$(cat /run/secrets/npmtoken) && \
    echo "//registry.npmjs.org/:_authToken=${NPM_TOKEN}" > ~/.npmrc && \
    npm install && \
    rm ~/.npmrc
```

```bash
docker build --secret id=npmtoken,src=.npmtoken .
```

이 방법은 시크릿이 레이어에 기록되지 않고 빌드 중에만 접근 가능한 임시 마운트로 제공된다.

## docker inspect로 환경변수가 전부 보인다

`docker inspect`는 컨테이너의 모든 설정을 JSON으로 출력한다. 환경변수도 포함된다.

```bash
docker inspect mycontainer | python3 -c "
import json, sys
data = json.load(sys.stdin)
for env in data[0]['Config']['Env']:
    print(env)
"
```

`DB_PASSWORD=supersecret`처럼 평문으로 나온다. 컨테이너가 실행 중인 호스트에 접근할 수 있는 사람이라면 누구나 볼 수 있다.

`docker image inspect`를 쓰면 이미지에 ENV로 구워진 환경변수도 볼 수 있다.

```bash
docker image inspect myimage --format '{{range .Config.Env}}{{println .}}{{end}}'
```

이미지를 누군가에게 배포하면 ENV에 박힌 값도 함께 나간다. 이미지에는 환경변수의 키 이름만 두고, 실제 값은 컨테이너 실행 시점에 주입하는 게 맞다.

## 런타임 시크릿 주입

환경변수로 시크릿을 주입하는 건 `docker inspect`에 노출된다는 문제가 있다. 파일 마운트 방식은 이 문제를 완화한다.

### 파일 마운트

```bash
docker run -v /host/secrets/db_password:/run/secrets/db_password:ro myapp
```

애플리케이션은 환경변수 대신 파일에서 읽는다.

```java
// Spring Boot에서 파일로 시크릿 읽기
@Value("${DB_PASSWORD_FILE:/run/secrets/db_password}")
private String dbPasswordFile;

private String getDbPassword() {
    try {
        return Files.readString(Path.of(dbPasswordFile)).trim();
    } catch (IOException e) {
        throw new RuntimeException("시크릿 파일을 읽을 수 없음: " + dbPasswordFile);
    }
}
```

Docker Compose의 `secrets:` 기능을 쓰면 `/run/secrets/<name>`으로 자동 마운트된다.

```yaml
services:
  app:
    image: myapp
    secrets:
      - db_password

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

이 방법도 컨테이너 내부에서는 파일이 평문으로 보이기 때문에, 컨테이너 셸 접근이 가능한 사람에게는 막을 수 없다. 진지한 시크릿 관리가 필요하면 Vault나 AWS Secrets Manager 같은 외부 시스템에서 애플리케이션 시작 시 직접 가져오는 방식을 써야 한다.

### 환경변수 방식의 현실

개발 환경이나 내부 인프라에서는 환경변수가 여전히 가장 편하다. `docker inspect` 노출이 문제가 되는 건 호스트 접근 권한이 있는 사람이 신뢰할 수 없는 경우다. 위협 모델에 맞게 판단하는 게 맞다. 모든 환경에서 파일 마운트를 쓰는 건 복잡도 대비 실익이 없을 수 있다.

## Spring Boot와 환경변수 연동

Spring Boot는 환경변수를 `application.yml`의 프로퍼티와 자동으로 연결한다. 점(`.`)을 언더스코어(`_`)로, 소문자를 대문자로 변환하는 규칙이다.

```yaml
# application.yml
spring:
  datasource:
    url: ${SPRING_DATASOURCE_URL:jdbc:postgresql://localhost:5432/mydb}
    username: ${SPRING_DATASOURCE_USERNAME:postgres}
    password: ${SPRING_DATASOURCE_PASSWORD}
```

컨테이너 환경변수로 `SPRING_DATASOURCE_URL`을 넣으면 `spring.datasource.url`에 바인딩된다. 콜론 뒤에 기본값을 넣으면 환경변수가 없을 때 그 값을 쓴다. 기본값 없이 `${SPRING_DATASOURCE_PASSWORD}`만 쓰면, 환경변수가 없을 때 애플리케이션 시작 시 오류가 난다.

프로파일 전환도 환경변수로 한다.

```bash
docker run -e SPRING_PROFILES_ACTIVE=prod myapp
```

`application-prod.yml`이 자동으로 로드된다.

외부 설정 파일을 마운트하는 방식도 자주 쓴다.

```bash
docker run \
  -v /host/config/application-prod.yml:/app/config/application-prod.yml:ro \
  -e SPRING_CONFIG_LOCATION=file:/app/config/ \
  myapp
```

`SPRING_CONFIG_LOCATION` 경로 끝에 슬래시(`/`)가 있으면 디렉토리 전체를 스캔하고, 없으면 특정 파일 하나만 읽는다. 파일 권한도 확인해야 한다. Spring Boot 프로세스가 파일을 읽을 수 없으면 오류 없이 기본값을 쓰는 경우가 있다. "환경 설정이 안 먹힌다"는 케이스의 상당수가 여기서 나온다.
