---
title: 백엔드 신입 Docker 입문
tags: [docker, devops, backend, linux]
updated: 2026-08-15
---

# 백엔드 신입 Docker 입문

20선 로드맵에서 ECS/Fargate로 바로 넘어가는데, 실제로 그 문서를 처음 읽으면 "Task Definition이 뭔지는 알겠는데 이미지는 어떻게 만들죠?"에서 막힌다. Docker 없이 ECS를 이해하려는 건 Jar 없이 EC2 배포를 이해하려는 것과 같다. 이 문서는 ECS 문서를 읽기 전에 반드시 쌓아야 하는 Docker 기초를 다룬다.

---

## 컨테이너가 VM과 다른 이유

VM은 OS를 통째로 올린다. 하이퍼바이저 위에 Guest OS가 올라가고 그 위에 앱이 돈다. 반면 컨테이너는 호스트 OS의 커널을 공유하고, 프로세스 격리(namespace)와 자원 제한(cgroups)으로 환경을 분리한다.

실무적으로 이 차이가 중요한 이유는 두 가지다.

첫째, 컨테이너는 올리는 데 1~2초면 충분하다. 내 Spring Boot 앱 이미지가 500MB더라도 `docker run` 후 앱 프로세스가 시작되기까지 JVM 기동 시간이 전부다. VM 스핀업 30초와 비교하면 ECS Fargate에서 오토스케일링이 의미 있는 수준으로 작동한다.

둘째, "내 로컬에서는 됐는데"라는 말이 사라진다. 컨테이너 이미지 안에 라이브러리 버전, 환경 변수, 파일 시스템 구조까지 전부 담겨있어서 로컬에서 빌드한 이미지가 프로덕션에서 동일하게 돈다.

---

## Dockerfile 작성

Dockerfile은 이미지를 만드는 명령어 목록이다. 각 명령어가 레이어 하나를 만들고, 레이어는 캐시된다.

### Spring Boot 앱 기본 Dockerfile

```dockerfile
FROM eclipse-temurin:17-jre-alpine

WORKDIR /app

COPY build/libs/app.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
```

`eclipse-temurin:17-jre-alpine`을 쓰는 이유는 JRE만 있는 Alpine 베이스라 이미지 크기가 200MB 이하다. `openjdk:17`은 JDK 전체가 들어있어 400MB를 넘는다. 프로덕션에서 JDK가 필요한 경우는 거의 없으니 JRE 이미지로 시작하는 게 맞다.

### 레이어 캐시 문제

위 Dockerfile의 문제는 `app.jar` 하나가 변경되면 그 레이어 이후가 전부 무효화된다는 거다. Spring Boot 앱에서 의존성은 자주 안 바뀌지만 소스는 매번 바뀐다. 의존성과 소스를 레이어로 분리하면 의존성 레이어가 캐시에서 재사용된다.

```dockerfile
FROM eclipse-temurin:17-jre-alpine

WORKDIR /app

# 의존성 레이어 먼저
ARG DEPENDENCY=build/dependency
COPY ${DEPENDENCY}/BOOT-INF/lib /app/BOOT-INF/lib
COPY ${DEPENDENCY}/META-INF /app/META-INF
COPY ${DEPENDENCY}/BOOT-INF/classes /app/BOOT-INF/classes

EXPOSE 8080

ENTRYPOINT ["java", "org.springframework.boot.loader.JarLauncher"]
```

이 방식은 `bootJar` 태스크 실행 전에 `build/dependency`에 레이어를 언패킹해야 한다.

```bash
mkdir -p build/dependency
cd build/dependency && jar -xf ../libs/app.jar
```

더 간단하게는 Spring Boot 2.3 이상이면 `bootBuildImage` 태스크가 Buildpacks로 레이어를 자동 분리한 이미지를 만들어준다. 다만 Buildpacks 이미지는 크기가 크고 빌드가 느려서 CI 시간이 아깝다면 직접 분리하는 게 낫다.

실무에서 레이어 캐시 효과는 빌드 시간 기준으로 봤을 때 의존성 레이어가 캐시될 경우 2~3분 → 30초 수준으로 줄었다. CI 빌드 비용이 있는 환경에서 차이가 크다.

### 빌드 컨텍스트 크기

`docker build .`을 실행하면 현재 디렉토리 전체를 Docker 데몬에 전송한다. Gradle 프로젝트 루트에서 실행하면 `build/` 폴더 전체가 딸려간다. `build/` 안에 generated sources, test results, intermediate jars가 있으면 컨텍스트가 1GB를 넘는 경우도 있다.

`.dockerignore` 파일로 제외한다.

```
.gradle
build
.git
*.md
out
.idea
```

`.dockerignore`가 없으면 첫 `docker build`가 유독 느린 이유가 여기 있다.

---

## docker-compose로 로컬 DB 띄우기

팀에서 MySQL이나 PostgreSQL을 로컬에 직접 설치하면 버전 충돌, 데이터 오염, OS마다 설정 경로가 달라지는 문제가 생긴다. docker-compose로 DB를 띄우면 `docker-compose down -v`로 완전 초기화가 가능하고, 프로젝트마다 격리된 DB를 유지할 수 있다.

```yaml
# docker-compose.yml
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: myapp
      MYSQL_USER: myapp
      MYSQL_PASSWORD: myapp
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  mysql_data:
```

```bash
docker-compose up -d        # 백그라운드로 실행
docker-compose logs -f mysql # mysql 로그 확인
docker-compose down          # 컨테이너 종료 (데이터 유지)
docker-compose down -v       # 컨테이너 + 볼륨 전부 삭제
```

포트 매핑 `"3306:3306"` 앞의 숫자가 호스트 포트다. 로컬에 MySQL이 이미 설치되어 있으면 3306이 이미 점유되어 있어 실패한다. 그때는 호스트 포트만 바꾼다.

```yaml
ports:
  - "3307:3306"  # 호스트의 3307로 접근
```

Spring Boot `application.yml`에서는 `spring.datasource.url: jdbc:mysql://localhost:3307/myapp`으로 맞춰준다.

### Spring Boot 앱도 compose에 넣을 때 주의점

앱 컨테이너가 DB 컨테이너보다 먼저 뜨면 DB 연결에 실패하고 앱이 죽는다. `depends_on`은 컨테이너 시작 순서만 보장하고 DB가 실제로 준비됐는지는 보장하지 않는다.

```yaml
services:
  app:
    build: .
    depends_on:
      mysql:
        condition: service_healthy
    environment:
      SPRING_DATASOURCE_URL: jdbc:mysql://mysql:3306/myapp
      SPRING_DATASOURCE_USERNAME: myapp
      SPRING_DATASOURCE_PASSWORD: myapp

  mysql:
    image: mysql:8.0
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 5s
      timeout: 3s
      retries: 5
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: myapp
      MYSQL_USER: myapp
      MYSQL_PASSWORD: myapp
```

`condition: service_healthy`가 핵심이다. healthcheck가 통과해야 app 컨테이너가 시작된다.

앱에서 DB 호스트는 `localhost`가 아니라 서비스 이름 `mysql`이다. compose 네트워크 안에서 서비스 이름이 DNS로 해석된다.

---

## 이미지 빌드와 ECR 푸시

ECS에서 이미지를 가져오려면 이미지가 레지스트리에 올라가 있어야 한다. AWS 환경에서는 ECR(Elastic Container Registry)을 쓴다.

```bash
# 빌드
docker build -t myapp:latest .

# ECR 로그인 (AWS CLI 설정 필요)
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com

# 태그
docker tag myapp:latest \
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp:latest

# 푸시
docker push 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp:latest
```

CI/CD에서는 이 과정이 파이프라인으로 자동화된다. 직접 푸시하는 건 처음 흐름을 익힐 때 한 번이면 충분하다.

---

## 흔히 겪는 문제

### 포트 매핑이 됐는데 접근이 안 된다

`EXPOSE 8080`은 문서 역할이다. 실제 포트 바인딩은 `docker run -p 8080:8080`으로 한다. `EXPOSE`만 쓰고 `-p`를 빠뜨리면 컨테이너 외부에서 접근이 안 된다.

### 파일 권한 문제

Alpine 기반 이미지에서 non-root 유저로 실행하면 `/app/app.jar`에 실행 권한이 없어 `Permission denied`가 난다.

```dockerfile
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
COPY --chown=appuser:appgroup build/libs/app.jar app.jar
USER appuser
```

프로덕션에서는 root로 돌리지 않는 게 기본이다. ECS Task Definition에도 `user` 필드로 지정할 수 있다.

### 컨테이너 안에서 로그가 안 보인다

`docker logs <container_id>`로 보이는 로그는 stdout/stderr다. Spring Boot는 기본으로 콘솔에 출력하니 바로 보인다. 로그를 파일로만 쓰도록 설정했다면 `docker logs`에서 아무것도 안 나온다. 컨테이너 환경에서는 로그를 파일에 쓰지 말고 stdout으로 내보내야 CloudWatch Logs 같은 외부 수집기가 가져간다.

### 이미지 크기가 예상보다 크다

`docker image ls`로 이미지 크기를 확인하고, `docker image history myapp:latest`로 레이어별 크기를 본다. 빌드 과정에서 생긴 임시 파일이 남아있는 레이어가 크기를 키우는 경우가 있다. Multi-stage build로 빌드 의존성을 최종 이미지에서 제거하면 줄어든다.

```dockerfile
# 빌드 스테이지
FROM gradle:8-jdk17-alpine AS build
WORKDIR /workspace
COPY . .
RUN gradle bootJar --no-daemon

# 실행 스테이지
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=build /workspace/build/libs/app.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

`--from=build`로 빌드 스테이지의 결과물만 가져오고 Gradle, JDK, 소스 코드는 최종 이미지에 없다. 이미지 크기가 빌드용 이미지의 절반 이하로 줄어든다.

---

## ECS로 넘어가기 전 확인

로컬에서 아래가 동작하면 ECS 문서로 넘어갈 준비가 된 거다.

- `docker build -t myapp .`이 성공하고 이미지가 로컬에 생긴다
- `docker run -p 8080:8080 myapp`으로 앱이 뜨고 `curl localhost:8080/actuator/health`가 응답한다
- `docker-compose up`으로 MySQL + 앱이 같이 뜨고 앱이 DB에 연결된다
- ECR에 이미지를 푸시하고 ECR 콘솔에서 이미지가 보인다

ECS에서 Task Definition을 만들 때 이미지 URI, 포트 매핑, 환경 변수 설정이 나온다. 로컬에서 `docker run`으로 했던 것과 구조가 같다. 그걸 AWS 콘솔에서 클릭으로 채우는 차이다.
