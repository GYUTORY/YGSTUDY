---
title: tzdata 버전 관리
tags: [backend, docker, kubernetes, java]
updated: 2026-07-31
---

# tzdata 버전 관리

tzdata는 IANA(Internet Assigned Numbers Authority)가 관리하는 타임존 데이터베이스다. 전 세계 각 지역의 UTC 오프셋, DST 전환 날짜, 역사적 타임존 변경 이력을 담고 있다. 국가가 DST 규칙을 바꾸거나 표준시를 변경하면 tzdata가 업데이트된다. 운영 서버가 이 업데이트를 반영하지 않으면 타임존 ID를 올바르게 써도 오래된 규칙으로 계산한다.

서비스를 운영하다 보면 tzdata를 직접 관리할 일이 생각보다 많다. OS, JVM, Python, Node.js, Go가 각각 별도 경로로 tzdata를 가지고 있어서 하나를 업데이트해도 나머지는 그대로인 경우가 흔하다.

## OS 레벨 tzdata

### Ubuntu / Debian

```bash
# 현재 버전 확인
dpkg -l tzdata
# 또는
cat /usr/share/zoneinfo/+VERSION
# tzdata2024a 형태로 출력됨

# 업데이트
apt-get update && apt-get install -y tzdata
```

`tzdata` 패키지를 설치하면 `/usr/share/zoneinfo/` 아래에 타임존 파일들이 위치한다. `TZ` 환경변수나 `/etc/localtime` 심볼릭 링크로 시스템 기본 타임존을 결정한다.

Ubuntu에서 `tzdata` 패키지는 설치 시 인터랙티브 프롬프트를 띄운다. Docker 빌드나 자동화 스크립트에서 이게 걸리면 빌드가 멈춘다.

```dockerfile
# DEBIAN_FRONTEND=noninteractive로 인터랙티브 프롬프트 방지
RUN DEBIAN_FRONTEND=noninteractive apt-get update \
    && apt-get install -y tzdata \
    && rm -rf /var/lib/apt/lists/*
```

### Alpine

Alpine Linux는 기본 이미지에 tzdata가 없다. Python의 `zoneinfo`, Go의 `time` 패키지 등이 OS tzdata를 참조하면 Alpine에서 `ZoneInfoNotFoundError`나 런타임 패닉이 뜬다.

```dockerfile
# Alpine에서 tzdata 설치
RUN apk add --no-cache tzdata
```

설치 후 `/usr/share/zoneinfo/`가 생긴다. `apk`는 `DEBIAN_FRONTEND` 같은 설정 없이도 조용하게 설치된다.

## JVM 내장 tzdata와 OS tzdata 분리 구조

JVM은 자체 tzdata를 갖고 있다. JDK 배포판에 번들된 tzdata 파일이 `$JAVA_HOME/lib/tzdb.dat`(Java 9+) 또는 `$JAVA_HOME/jre/lib/zi/`(Java 8)에 있다. OS tzdata를 업데이트해도 JVM 내장 tzdata는 그대로다.

```bash
# JVM 내장 tzdata 버전 확인 (Java 8)
java -XshowSettings:all -version 2>&1 | grep -i timezone

# Java 9+에서 tzdb.dat 버전 확인 방법이 없으므로
# JDK 패키지 버전으로 간접 확인
java -version
# openjdk version "21.0.3" 형태 — 릴리스 날짜로 tzdata 버전 추정
```

JVM이 `ZoneId.of("America/Mexico_City")`로 시간을 계산할 때 참조하는 것은 OS tzdata가 아니라 JVM 내장 tzdb.dat다. OS tzdata가 2023a로 업데이트돼 멕시코 DST 폐지를 반영해도, JVM이 구버전 tzdb.dat를 쓰면 여전히 DST를 적용한다.

### JVM tzdata 업데이트 방법

#### Oracle JDK — TZUpdater

```bash
# Oracle JDK TZUpdater 다운로드 후 실행
java -jar tzupdater.jar -u
# 또는 특정 버전 지정
java -jar tzupdater.jar -v 2024a
```

#### Amazon Corretto

Corretto는 별도 tzdata 업데이트 패키지를 제공하지 않는다. Corretto 패키지 자체를 업데이트해야 tzdata도 업데이트된다.

```bash
# Amazon Linux 2
yum update java-21-amazon-corretto-headless

# Debian/Ubuntu
apt-get update && apt-get install --only-upgrade java-21-amazon-corretto
```

#### Eclipse Temurin (AdoptOpenJDK)

```bash
# Debian/Ubuntu
apt-get update && apt-get install --only-upgrade temurin-21-jdk
```

Temurin은 새 JDK 마이너 릴리스에 최신 tzdata를 포함해서 배포하는 편이다.

#### Maven 프로젝트 — zone.tab 직접 교체

빠르게 특정 tzdata 버전을 적용해야 하는데 JDK 교체가 어려운 상황이라면, `tzdb.dat`를 직접 교체하는 방법이 있다.

```bash
# IANA에서 tzdata 다운로드
wget https://data.iana.org/time-zones/releases/tzdata2024a.tar.gz

# tzdb.dat 생성 (JDK의 javazic 도구 필요)
# 또는 미리 빌드된 tzdb.dat를 제공하는 서드파티 도구 사용
# https://github.com/nicmarti/tzupdater 참고
```

이 방식은 관리 부담이 크다. 릴리스 자동화에 엮어두지 않으면 누락되기 쉽다.

### JVM 타임존 관련 환경변수

```bash
# JVM 기본 타임존 설정
-Duser.timezone=UTC

# JVM이 OS tzdata를 우선 참조하도록 (Java 8u161+)
-Djava.util.TimeZone.useSystemTz=true
```

`useSystemTz=true`를 쓰면 JVM 내장 tzdb.dat 대신 OS의 `/usr/share/zoneinfo/`를 참조한다. OS tzdata만 관리하면 JVM도 같이 업데이트된다. 단, 이 옵션이 모든 JVM 구현체에서 동일하게 동작하지는 않으므로 사용 전 검증이 필요하다.

## Python tzdata pip 패키지

Python 3.9+의 `zoneinfo` 모듈은 기본적으로 OS tzdata를 참조한다. OS tzdata가 없으면 `ZoneInfoNotFoundError`가 발생한다.

```python
from zoneinfo import ZoneInfo
tz = ZoneInfo('America/New_York')
# Alpine 또는 slim 이미지에서 tzdata 없으면 ZoneInfoNotFoundError
```

`pip install tzdata`로 Python 전용 tzdata 패키지를 설치하면 OS tzdata 없이도 동작한다.

```bash
pip install tzdata
```

설치 후 `zoneinfo`는 OS tzdata와 pip tzdata 중 OS tzdata를 우선 참조한다. OS tzdata가 있으면 pip tzdata는 무시된다. Alpine에서 OS tzdata를 설치하지 않고 pip tzdata만 쓰거나, Ubuntu slim 이미지에서 apt-get 없이 tzdata를 쓰고 싶을 때 pip tzdata가 대안이 된다.

```python
# pip tzdata 패키지 버전 확인
import importlib.metadata
print(importlib.metadata.version('tzdata'))
# 2024.1 형태
```

pip tzdata 버전 번호는 `YYYY.N` 형태다. `2024.1`이면 2024년 첫 번째 IANA 릴리스(tzdata2024a)에 해당한다.

```
requirements.txt에서 고정:
tzdata==2024.1
```

버전을 고정해두지 않으면 `pip install` 시점마다 tzdata 버전이 달라진다. 환경마다 tzdata 버전이 다르면 재현하기 어려운 타임존 계산 차이가 생긴다.

`pytz`는 내부에 tzdata 파일을 직접 번들해서 배포한다. OS tzdata나 pip tzdata와 무관하게 pytz 패키지 버전이 tzdata 버전을 결정한다. `pip install pytz`로 설치한 버전에 따라 tzdata가 고정된다.

```python
import pytz
print(pytz.OLSON_VERSION)  # '2024.1' 형태
```

## Node.js / Go 런타임의 tzdata 처리

### Node.js

Node.js는 V8 엔진에 tzdata를 번들하지 않는다. `Intl` API(ECMAScript Internationalization API)를 통해 ICU 데이터에 포함된 tzdata를 사용한다.

```bash
# Node.js가 사용하는 ICU 버전 확인
node -e "console.log(process.versions.icu)"
# 73.1 형태

# ICU tzdata 버전은 직접 확인하기 어려움
# Node.js 릴리스 노트에서 ICU 버전과 tzdata 버전 매핑 확인
```

Node.js `full-icu` 빌드와 `small-icu` 빌드가 있다. `small-icu`는 영어만 지원하는 최소 ICU를 포함하고, `full-icu`는 모든 로케일 데이터를 포함한다. Docker 공식 이미지는 `small-icu`를 쓰는 경우가 있다.

```bash
# small-icu 여부 확인
node -e "console.log(Intl.DateTimeFormat('ko').resolvedOptions())"
# small-icu면 한국어 포맷이 제대로 안 될 수 있음
```

`Intl.DateTimeFormat`의 타임존 계산은 ICU 번들 tzdata를 쓴다. Node.js 버전을 올리지 않고 tzdata만 갱신하는 방법은 공식적으로 없다. 실질적으로 Node.js 버전을 올리거나, 타임존 처리를 `date-fns-tz`, `luxon` 같은 라이브러리에 위임하는 방식으로 대응한다.

```bash
# Temporal API (Node.js 21+, experimental)
node --experimental-temporal -e "
const dt = Temporal.ZonedDateTime.from('2024-07-01T00:00:00[America/New_York]');
console.log(dt.offsetNanoseconds);
"
```

`Temporal` API는 ICU tzdata를 사용한다. Node.js 21 이상에서 쓸 수 있지만 2026년 기준으로 아직 Stage 3 단계라 프로덕션 적용 전 검토가 필요하다.

### Go

Go는 `time` 패키지에 tzdata를 임베딩하는 방식을 지원한다. Go 1.15+에서 `time/tzdata` 패키지를 blank import하면 tzdata가 바이너리에 포함된다.

```go
import (
    _ "time/tzdata" // tzdata를 바이너리에 임베딩
    "time"
)

func main() {
    loc, err := time.LoadLocation("America/New_York")
    if err != nil {
        panic(err)
    }
    t := time.Now().In(loc)
    fmt.Println(t)
}
```

`_ "time/tzdata"`를 임베딩하지 않으면 Go 런타임은 OS의 `/usr/share/zoneinfo/`를 찾는다. Alpine이나 scratch 이미지처럼 tzdata가 없는 환경에서 `time.LoadLocation()`이 `unknown time zone` 오류를 낸다.

임베딩된 tzdata 버전은 Go 컴파일러 버전에 묶인다. Go 1.22를 쓰면 그 버전에 번들된 tzdata가 바이너리에 들어간다. tzdata만 업데이트하려면 Go를 업그레이드하거나 OS tzdata를 쓰는 방식으로 돌아가야 한다.

```bash
# Go 바이너리에 임베딩된 tzdata 버전 확인 방법 없음
# Go 릴리스 changelog에서 tzdata 버전 확인
# https://go.dev/doc/go1.22 에서 "tzdata" 검색
```

```bash
# OS tzdata를 사용하는 방식 (scratch 이미지 제외)
# time/tzdata 미import + OS tzdata 설치
RUN apk add --no-cache tzdata
```

Go 서비스를 scratch 이미지로 배포할 때는 `time/tzdata` 임베딩이 사실상 필수다. CGO를 안 쓰는 정적 바이너리라면 이게 가장 단순하다.

## Docker 이미지에서 tzdata 고정

### 버전 고정 원칙

Docker 이미지 빌드 시 tzdata 버전을 고정하지 않으면 `apt-get install tzdata`나 `apk add tzdata`가 실행될 때마다 최신 버전이 설치된다. 이미지 빌드 날짜에 따라 tzdata 버전이 달라진다.

```dockerfile
# Ubuntu/Debian — 버전 고정
FROM ubuntu:22.04
RUN DEBIAN_FRONTEND=noninteractive apt-get update \
    && apt-get install -y tzdata=2024a-0ubuntu0.22.04.1 \
    && rm -rf /var/lib/apt/lists/*
ENV TZ=UTC
```

정확한 패키지 버전 문자열은 `apt-cache policy tzdata`로 확인한다.

```dockerfile
# Alpine — 버전 고정
FROM alpine:3.19
RUN apk add --no-cache tzdata=2024a-r0
ENV TZ=UTC
```

Alpine 패키지 버전은 `https://pkgs.alpinelinux.org/`에서 확인한다.

### 멀티스테이지 빌드에서 tzdata 처리

```dockerfile
# Go 서비스 — scratch 이미지에 tzdata 복사
FROM golang:1.22-alpine AS builder

# time/tzdata 임베딩 방식을 쓰면 scratch에서 별도 설치 불필요
RUN apk add --no-cache tzdata

WORKDIR /app
COPY . .
RUN CGO_ENABLED=0 go build -o server .

FROM scratch
# tzdata 파일 복사 (time/tzdata 미임베딩 시)
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /app/server /server

ENV TZ=UTC
ENTRYPOINT ["/server"]
```

### JVM 이미지

```dockerfile
FROM eclipse-temurin:21-jre-jammy

# OS tzdata 업데이트
RUN DEBIAN_FRONTEND=noninteractive apt-get update \
    && apt-get install -y tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=UTC
ENTRYPOINT ["java", "-Duser.timezone=UTC", "-jar", "/app/app.jar"]
```

`-Duser.timezone=UTC`와 `ENV TZ=UTC`를 동시에 설정한다. JVM은 `-Duser.timezone`을 우선 참조하고, OS와 JVM 기본 타임존을 둘 다 UTC로 맞춰 일관성을 유지한다.

## Kubernetes 클러스터에서 tzdata 버전 드리프트 감지

### 드리프트 발생 경로

Kubernetes 클러스터에서 노드 OS 이미지, 컨테이너 이미지, JVM 버전이 각각 독립적으로 관리되면 tzdata 버전 드리프트가 생긴다. 노드 A는 tzdata2024a, 노드 B는 tzdata2023c인 상태에서 Pod가 다른 노드에 스케줄링될 때마다 타임존 계산이 달라진다.

증상은 조용하다. 타임존 계산이 틀렸다는 에러가 나지 않는다. 배치 실행 시각이 노드마다 1시간 차이 나거나, 특정 날짜에만 재현되는 로컬라이제이션 버그로 나타난다.

### 버전 확인 방법

```yaml
# DaemonSet으로 모든 노드의 tzdata 버전 확인
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: tzdata-checker
spec:
  selector:
    matchLabels:
      app: tzdata-checker
  template:
    metadata:
      labels:
        app: tzdata-checker
    spec:
      containers:
      - name: checker
        image: ubuntu:22.04
        command: ["/bin/sh", "-c"]
        args:
        - |
          echo "Node: $NODE_NAME"
          cat /usr/share/zoneinfo/+VERSION
          sleep infinity
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
```

```bash
# 각 Pod 로그에서 노드별 tzdata 버전 수집
kubectl logs -l app=tzdata-checker --all-containers=true | grep -A1 "Node:"
```

### 컨테이너 이미지 버전 확인

애플리케이션 컨테이너 자체의 tzdata 버전은 Pod exec로 확인한다.

```bash
# Java 서비스 Pod
kubectl exec deploy/my-service -- sh -c "cat /usr/share/zoneinfo/+VERSION 2>/dev/null || echo 'no OS tzdata'"

# Python 서비스 Pod
kubectl exec deploy/my-service -- python3 -c "
import importlib.metadata
try:
    print('pip tzdata:', importlib.metadata.version('tzdata'))
except:
    print('pip tzdata not installed')
import subprocess
result = subprocess.run(['cat', '/usr/share/zoneinfo/+VERSION'], capture_output=True, text=True)
print('OS tzdata:', result.stdout.strip() or 'not found')
"
```

### 모니터링 쿼리

Prometheus + Grafana 환경이라면 커스텀 메트릭을 노출하는 방식이 낫다. 애플리케이션 startup 시점에 tzdata 버전을 메트릭으로 노출한다.

```python
# Python FastAPI 예시
from prometheus_client import Info
import importlib.metadata
import subprocess

tzdata_info = Info('tzdata', 'tzdata version info')

def get_tzdata_versions():
    versions = {}
    try:
        versions['pip'] = importlib.metadata.version('tzdata')
    except importlib.metadata.PackageNotFoundError:
        versions['pip'] = 'not_installed'
    
    result = subprocess.run(
        ['cat', '/usr/share/zoneinfo/+VERSION'],
        capture_output=True, text=True
    )
    versions['os'] = result.stdout.strip() or 'not_found'
    return versions

tzdata_info.info(get_tzdata_versions())
```

Grafana에서 `tzdata_info`로 쿼리하면 각 Pod의 tzdata 버전을 한눈에 볼 수 있다. 버전이 섞인 Pod가 보이면 이미지 롤아웃이 완료되지 않은 것이다.

## CI/CD에서 tzdata 업데이트 자동화

### 이미지 빌드 파이프라인

```yaml
# GitHub Actions 예시
name: Build and Push
on:
  schedule:
    - cron: '0 2 * * 1'  # 매주 월요일 새벽 2시 (UTC)
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build image
        run: |
          docker build \
            --build-arg TZDATA_VERSION=$(date +%Y%m%d) \
            -t myapp:${{ github.sha }} .
      
      - name: Check tzdata version
        run: |
          docker run --rm myapp:${{ github.sha }} \
            sh -c "cat /usr/share/zoneinfo/+VERSION"
      
      - name: Push image
        run: docker push myapp:${{ github.sha }}
```

정기 빌드 스케줄을 추가하면 베이스 이미지가 최신 tzdata를 포함하고 있을 때 자동으로 반영된다. `apt-get install tzdata` 없이 베이스 이미지 자체가 최신이면 tzdata도 최신이다.

### tzdata 버전 변경 감지

```yaml
# 빌드 전후 tzdata 버전 비교
- name: Get current tzdata version
  run: |
    CURRENT=$(docker run --rm $IMAGE_LATEST \
      sh -c "cat /usr/share/zoneinfo/+VERSION 2>/dev/null || echo 'unknown'")
    echo "CURRENT_TZDATA=$CURRENT" >> $GITHUB_ENV

- name: Build new image  
  run: docker build -t $IMAGE_NEW .

- name: Get new tzdata version
  run: |
    NEW=$(docker run --rm $IMAGE_NEW \
      sh -c "cat /usr/share/zoneinfo/+VERSION 2>/dev/null || echo 'unknown'")
    echo "NEW_TZDATA=$NEW" >> $GITHUB_ENV
    
- name: Notify tzdata change
  if: env.CURRENT_TZDATA != env.NEW_TZDATA
  run: |
    echo "tzdata version changed: $CURRENT_TZDATA -> $NEW_TZDATA"
    # Slack 알림이나 PR 코멘트 추가
```

tzdata 버전이 바뀌었을 때 알림을 보내면 배포 후 이상 동작이 생겼을 때 원인 추적이 빠르다.

### Python 의존성 업데이트

```yaml
# Dependabot 설정에 pip tzdata 포함
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: pip
    directory: /
    schedule:
      interval: weekly
    allow:
      - dependency-name: tzdata
```

Dependabot이 `tzdata` 새 버전이 나오면 자동으로 PR을 만든다. `requirements.txt`에 버전을 고정해두면 Dependabot이 업데이트 PR을 보내고, CI가 통과하면 머지한다.

### Go 모듈 업데이트

Go에서 `time/tzdata` 임베딩을 쓰면 tzdata 버전이 Go 버전에 묶인다. Go 자체를 주기적으로 올리는 파이프라인이 있으면 tzdata도 같이 올라간다.

```yaml
# Go 버전 업데이트 감지
- name: Check Go version
  run: |
    CURRENT_GO=$(go version | awk '{print $3}')
    LATEST_GO=$(curl -s https://go.dev/dl/?mode=json | jq -r '.[0].version')
    if [ "$CURRENT_GO" != "$LATEST_GO" ]; then
      echo "Go update available: $CURRENT_GO -> $LATEST_GO"
    fi
```

## 정치적 DST 변경 발생 시 운영 체크 절차

정치적 DST 변경은 예고 없이 발생하고 발효까지 기간이 짧은 경우가 있다. 멕시코(2023년 DST 폐지), 이집트(2010년 DST 재도입 후 여러 차례 변경), 모로코(라마단 기간 DST 일시 정지) 같은 사례가 있었다.

IANA tzdata 릴리스 메일링 리스트(`tz-announce@iana.org`)를 구독하면 새 버전 릴리스 시 이메일을 받는다. 변경이 발생하면 아래 순서로 체크한다.

### 1. 영향 범위 확인

```bash
# 변경된 타임존 ID 확인 (tzdata 릴리스 노트에서)
# 예: 멕시코 DST 폐지 시 영향 타임존
# America/Mexico_City, America/Cancun, America/Monterrey 등

# DB에서 해당 타임존 사용자/데이터 수 확인
SELECT user_timezone, COUNT(*) 
FROM users 
WHERE user_timezone IN ('America/Mexico_City', 'America/Monterrey', 'America/Cancun')
GROUP BY user_timezone;
```

영향받는 사용자가 없으면 업데이트 우선순위를 낮출 수 있다. 반대로 해당 지역 사용자가 많은 서비스라면 tzdata 릴리스 후 빠르게 대응해야 한다.

### 2. 현재 tzdata 버전 vs 필요 버전 파악

```bash
# IANA에서 어느 버전에서 변경이 반영됐는지 확인
# 릴리스 노트: https://data.iana.org/time-zones/releases/

# 운영 환경 현재 버전 확인
# OS
cat /usr/share/zoneinfo/+VERSION

# Java (실행 중인 서비스에서)
kubectl exec deploy/my-service -- java -XshowSettings:all -version 2>&1 | grep -i timezone

# Python
kubectl exec deploy/my-service -- python3 -c "import importlib.metadata; print(importlib.metadata.version('tzdata'))"
```

### 3. 스케줄러·배치 영향 분석

```bash
# 해당 타임존 기준으로 스케줄된 작업 목록 확인
# Quartz DB 기준
SELECT TRIGGER_NAME, TRIGGER_STATE, TIME_ZONE_ID
FROM QRTZ_CRON_TRIGGERS
WHERE TIME_ZONE_ID LIKE '%Mexico%'
   OR TIME_ZONE_ID LIKE '%America/Mexico%';
```

DST가 폐지되거나 변경된 타임존 기준 스케줄이 있으면, 업데이트 전후로 실행 시각이 달라진다. 변경 발효일 전후 2~3일치 스케줄 실행 로그를 미리 확인할 대상으로 표시해둔다.

### 4. 업데이트 실행

```bash
# OS 업데이트
apt-get update && apt-get install -y tzdata

# Python pip tzdata
pip install --upgrade tzdata

# 확인
cat /usr/share/zoneinfo/+VERSION
python3 -c "import importlib.metadata; print(importlib.metadata.version('tzdata'))"
```

JVM은 업데이트 방법이 배포판마다 다르다. Corretto, Temurin은 JDK 패키지 업데이트로 처리한다. Oracle JDK는 TZUpdater를 별도 실행한다.

### 5. 이미지 재빌드 및 배포

```bash
# Docker 이미지 재빌드 (베이스 이미지도 새로 pull)
docker build --no-cache --pull -t myapp:tzdata-$(date +%Y%m%d) .

# 확인
docker run --rm myapp:tzdata-$(date +%Y%m%d) cat /usr/share/zoneinfo/+VERSION

# Kubernetes 롤아웃
kubectl set image deploy/my-service app=myapp:tzdata-$(date +%Y%m%d)
kubectl rollout status deploy/my-service
```

### 6. 과거 데이터 처리

tzdata 업데이트 후 과거 데이터를 재계산하면 변경 이전 규칙과 이후 규칙이 다른 결과를 낼 수 있다.

```python
from zoneinfo import ZoneInfo
from datetime import datetime

mexico_city = ZoneInfo('America/Mexico_City')

# 멕시코 DST 폐지 전 여름 날짜 (2023년 이전)
# tzdata 구버전: CDT (UTC-5)
# tzdata 신버전: CST (UTC-6), DST 폐지 반영
summer_2022 = datetime(2022, 7, 1, 12, 0, tzinfo=mexico_city)
print(summer_2022.utcoffset())  # 구버전: -05:00 / 신버전: 달라질 수 있음
```

과거 데이터가 당시 규칙 기준으로 저장된 UTC라면 재계산할 필요 없다. UTC로 저장한 데이터는 tzdata 변경과 무관하다. UTC로 저장하지 않은 로컬 타임 데이터가 있을 때 처리 방법을 결정한다.

```sql
-- 변경 발효일 이후 데이터만 영향받는지 확인
-- 멕시코 DST 폐지: 2023-04-30 이후
SELECT COUNT(*)
FROM orders
WHERE user_timezone = 'America/Mexico_City'
  AND created_at >= '2023-04-30';
```

발효일 이전 데이터는 당시 tzdata 기준으로 저장된 것이므로, 현재 tzdata로 재해석하면 오히려 틀려진다. 발효일을 기준으로 데이터 처리 로직을 나눈다.
