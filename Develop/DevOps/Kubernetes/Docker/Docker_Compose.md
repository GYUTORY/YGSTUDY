---
title: Docker Compose
tags: [application-architecture, kubernetes, docker, docker-compose]
updated: 2025-11-23
---

# Docker Compose

## 목차
- [Docker Compose란?](#docker-compose란)
- [파일 구조 및 주요 구성 요소](#파일-구조-및-주요-구성-요소)
- [실전 예제](#실전-예제)
- [명령어 및 운영 방법](#명령어-및-운영-방법)
- [고급 활용 기법](#고급-활용-기법)
- [리소스 제한 및 관리](#리소스-제한-및-관리)
- [CI/CD 파이프라인 통합](#cicd-파이프라인-통합)
- [성능 최적화 및 트러블슈팅](#성능-최적화-및-트러블슈팅)
- [참고자료](#참고자료)

---

## Docker Compose란?

Docker Compose는 다중 컨테이너 Docker 애플리케이션을 정의하고 실행하기 위한 도구입니다. YAML 파일을 사용하여 애플리케이션의 서비스, 네트워크, 볼륨을 구성하고, 단일 명령어로 모든 서비스를 관리할 수 있습니다.

### Docker Compose의 핵심 가치

**1. 선언적 구성 관리**
- docker-compose.yml 파일을 통해 인프라를 코드로 관리
- 버전 관리 시스템을 통한 구성 변경 추적 가능
- 재현 가능한 환경 구축

**2. 서비스 오케스트레이션**
- 여러 컨테이너 간의 의존성 관리
- 서비스 간 통신 및 네트워킹 자동화
- 로드 밸런싱 및 스케일링 지원

**3. 개발 생산성 향상**
- 복잡한 멀티 컨테이너 환경을 단순화
- 개발, 테스트, 프로덕션 환경의 일관성 보장
- 로컬 개발 환경과 프로덕션 환경의 차이 최소화

---

## 파일 구조 및 주요 구성 요소

### 기본 파일 구조

Docker Compose는 YAML 형식의 구성 파일을 사용하며, 다음과 같은 계층적 구조를 가집니다:

```yaml
version: '3.8'  # Compose 파일 형식 버전
services:       # 서비스 정의 섹션
  service1:     # 개별 서비스 정의
  service2:
networks:       # 네트워크 정의 (선택사항)
volumes:        # 볼륨 정의 (선택사항)
secrets:        # 시크릿 정의 (선택사항)
configs:        # 설정 파일 정의 (선택사항)
```

### 핵심 구성 요소 상세 분석

**Services (서비스)**
- Docker Compose의 핵심 구성 요소
- 각 서비스는 하나의 컨테이너를 나타냄
- 서비스 간 의존성, 네트워킹, 볼륨 마운트 등을 정의

**Networks (네트워크)**
- 서비스 간 통신을 위한 네트워크 정의
- 기본적으로 모든 서비스는 동일한 네트워크에 연결
- 사용자 정의 네트워크를 통한 세밀한 네트워킹 제어

**Volumes (볼륨)**
- 컨테이너 간 데이터 공유 및 영구 저장
- 호스트 파일시스템과 컨테이너 간 데이터 바인딩
- 데이터베이스 데이터, 로그 파일, 설정 파일 등에 활용

### 주요 설정 옵션

| 구성 요소 | 설명 | 주요 옵션 |
|-----------|------|-----------|
| **version** | Compose 파일 형식 버전 | 3.8, 3.9, 3.10 |
| **services** | 컨테이너 서비스 정의 | image, build, ports, volumes |
| **image** | 사용할 Docker 이미지 | 공식 이미지명 또는 커스텀 이미지 |
| **build** | Dockerfile 기반 이미지 빌드 | context, dockerfile, args |
| **ports** | 포트 매핑 | "호스트포트:컨테이너포트" |
| **volumes** | 볼륨 마운트 | 호스트경로:컨테이너경로 |
| **environment** | 환경 변수 설정 | KEY=VALUE 형식 |
| **depends_on** | 서비스 의존성 | 서비스 시작 순서 제어 |
| **networks** | 네트워크 연결 | 사용자 정의 네트워크 지정 |
| **restart** | 재시작 정책 | no, always, on-failure |

---

## 실전 예제

### Node.js + MongoDB + Redis 스택

다음은 Node.js 웹 애플리케이션, MongoDB 데이터베이스, Redis 캐시를 포함한 완전한 스택을 구성하는 예제입니다.

**파일명: docker-compose.yml**
```yaml
version: '3.8'

services:
  # Node.js 웹 애플리케이션
  app:
    build: 
      context: .
      dockerfile: Dockerfile
      args:
        NODE_ENV: production
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - MONGO_URL=mongodb://mongodb:27017/myapp
      - REDIS_URL=redis://redis:6379
      - PORT=3000
    depends_on:
      - mongodb
      - redis
    volumes:
      - ./logs:/app/logs
    networks:
      - app-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # MongoDB 데이터베이스
  mongodb:
    image: mongo:6.0
    ports:
      - "27017:27017"
    environment:
      - MONGO_INITDB_ROOT_USERNAME=admin
      - MONGO_INITDB_ROOT_PASSWORD=password123
      - MONGO_INITDB_DATABASE=myapp
    volumes:
      - mongo-data:/data/db
      - ./mongo-init:/docker-entrypoint-initdb.d
    networks:
      - app-network
    restart: unless-stopped

  # Redis 캐시
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes --requirepass redis123
    volumes:
      - redis-data:/data
    networks:
      - app-network
    restart: unless-stopped

  # Nginx 리버스 프록시
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    networks:
      - app-network
    restart: unless-stopped

volumes:
  mongo-data:
    driver: local
  redis-data:
    driver: local

networks:
  app-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### 구성 요소 상세 분석

**애플리케이션 서비스 (app)**
- `build` 섹션에서 Dockerfile을 사용한 이미지 빌드
- `args`를 통한 빌드 시점 환경 변수 전달
- `healthcheck`를 통한 서비스 상태 모니터링
- `restart: unless-stopped`로 자동 재시작 정책 설정

**데이터베이스 서비스 (mongodb)**
- 초기 사용자 및 데이터베이스 설정
- 볼륨을 통한 데이터 영구 저장
- 초기화 스크립트 마운트를 통한 데이터베이스 설정

**캐시 서비스 (redis)**
- AOF(Append Only File) 활성화로 데이터 지속성 보장
- 인증 비밀번호 설정으로 보안 강화

**리버스 프록시 (nginx)**
- SSL/TLS 종료 및 로드 밸런싱
- 정적 파일 서빙 및 압축

---

## 명령어 및 운영 방법

### 기본 명령어

**서비스 시작 및 실행**
```bash
# 모든 서비스 백그라운드 실행
docker-compose up -d

# 특정 서비스만 실행
docker-compose up -d app mongodb

# 이미지 재빌드 후 실행
docker-compose up -d --build

# 강제 재생성 후 실행
docker-compose up -d --force-recreate
```

**서비스 상태 관리**
```bash
# 실행 중인 서비스 상태 확인
docker-compose ps

# 서비스 로그 확인
docker-compose logs -f app

# 특정 서비스 재시작
docker-compose restart app

# 서비스 중지
docker-compose stop

# 서비스 중지 및 리소스 정리
docker-compose down

# 볼륨까지 포함하여 완전 정리
docker-compose down -v
```

### 고급 운영 명령어

**스케일링 및 확장**
```bash
# 특정 서비스의 인스턴스 수 조정
docker-compose up -d --scale app=3

# 서비스 실행 순서 제어
docker-compose up -d --no-deps app
```

**디버깅 및 모니터링**
```bash
# 서비스 내부 쉘 접근
docker-compose exec app /bin/bash

# 실시간 리소스 사용량 모니터링
docker-compose top

# 서비스 간 네트워크 연결 테스트
docker-compose exec app ping mongodb
```

### 환경별 구성 관리

**개발 환경 실행**
```bash
# 개발용 compose 파일 사용
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

**프로덕션 환경 실행**
```bash
# 프로덕션용 compose 파일 사용
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## 고급 활용 기법

### 환경 변수 관리

**환경 변수 파일 (.env) 활용**
```bash
# .env 파일
MONGO_USER=admin
MONGO_PASSWORD=secure_password_123
REDIS_PASSWORD=redis_secure_456
NODE_ENV=production
```

**docker-compose.yml에서 환경 변수 사용**
```yaml
version: '3.8'

services:
  mongodb:
    image: mongo:6.0
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_USER}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}
    volumes:
      - mongo-data:/data/db

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis-data:/data

volumes:
  mongo-data:
  redis-data:
```

### 다중 환경 구성

**기본 docker-compose.yml**
```yaml
version: '3.8'

services:
  app:
    build: .
    environment:
      - NODE_ENV=${NODE_ENV:-development}
    depends_on:
      - mongodb

  mongodb:
    image: mongo:6.0
    environment:
      - MONGO_INITDB_ROOT_USERNAME=${MONGO_USER}
      - MONGO_INITDB_ROOT_PASSWORD=${MONGO_PASSWORD}
```

**개발 환경 오버라이드 (docker-compose.dev.yml)**
```yaml
version: '3.8'

services:
  app:
    ports:
      - "3000:3000"
    volumes:
      - .:/app
      - /app/node_modules
    environment:
      - NODE_ENV=development
      - DEBUG=true

  mongodb:
    ports:
      - "27017:27017"
```

**프로덕션 환경 오버라이드 (docker-compose.prod.yml)**
```yaml
version: '3.8'

services:
  app:
    restart: always
    environment:
      - NODE_ENV=production
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  mongodb:
    restart: always
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
```

### 보안 및 시크릿 관리

**Docker Secrets 활용**
```yaml
version: '3.8'

services:
  app:
    image: myapp:latest
    secrets:
      - db_password
      - api_key
    environment:
      - DB_PASSWORD_FILE=/run/secrets/db_password
      - API_KEY_FILE=/run/secrets/api_key

secrets:
  db_password:
    file: ./secrets/db_password.txt
  api_key:
    file: ./secrets/api_key.txt
```

### 네트워킹 및 서비스 디스커버리

**사용자 정의 네트워크 구성**
```yaml
version: '3.8'

services:
  app:
    image: myapp:latest
    networks:
      - frontend
      - backend

  mongodb:
    image: mongo:6.0
    networks:
      - backend

  nginx:
    image: nginx:alpine
    networks:
      - frontend
    depends_on:
      - app

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true
```

### 모니터링 및 로깅

**로그 드라이버 설정**
```yaml
version: '3.8'

services:
  app:
    image: myapp:latest
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    labels:
      - "com.example.service=web"
      - "com.example.version=1.0"

  mongodb:
    image: mongo:6.0
    logging:
      driver: "syslog"
      options:
        syslog-address: "tcp://logserver:514"
```

---

## 리소스 제한 및 관리

Docker Compose에서 컨테이너의 리소스를 제한하는 것은 시스템 안정성과 성능 최적화에 매우 중요합니다. 적절한 리소스 제한이 없으면 한 컨테이너가 전체 시스템의 리소스를 독점하여 다른 서비스에 영향을 줄 수 있습니다.

### 메모리 제한

#### 메모리 제한 옵션

**기본 메모리 제한:**
```yaml
version: '3.8'

services:
  app:
    image: myapp:latest
    mem_limit: 512m        # 하드 리미트 (최대 메모리)
    mem_reservation: 256m  # 소프트 리미트 (보장되는 메모리)
```

**상세 메모리 제어:**
```yaml
version: '3.8'

services:
  app:
    image: myapp:latest
    deploy:
      resources:
        limits:
          memory: 512M      # 최대 메모리 사용량
        reservations:
          memory: 256M      # 최소 보장 메모리
    mem_swappiness: 0       # 스왑 사용 비율 (0-100)
    memswap_limit: 1g       # 메모리 + 스왑 총합 제한
```

#### 메모리 제한 동작 원리

**하드 리미트 (limits):**
- 컨테이너가 절대 초과할 수 없는 최대 메모리 양
- 초과 시 OOM(Out of Memory) Killer가 컨테이너를 강제 종료
- Linux cgroup의 `memory.limit_in_bytes` 값으로 설정됨

**소프트 리미트 (reservations):**
- 시스템이 컨테이너에 보장하려고 시도하는 메모리 양
- 다른 컨테이너가 유휴 상태일 때 이 값보다 더 사용 가능
- 메모리 경합 시 최소한 이 값은 보장받음

**동작 시나리오:**
```
1. 정상 상황:
   reservations(256M) ≤ 실제 사용(300M) ≤ limits(512M)
   → 정상 동작

2. 메모리 부족:
   실제 사용 > limits(512M)
   → OOM Killer 발동, 컨테이너 강제 종료

3. 메모리 경합:
   전체 시스템 메모리 부족
   → reservations 값에 따라 메모리 재분배
```

#### 메모리 스왑 제어

**mem_swappiness:**
- 0-100 사이의 값으로 스왑 사용 경향성 설정
- `0`: 스왑 최소화 (성능 우선)
- `100`: 스왑 적극 사용 (메모리 절약 우선)

```yaml
services:
  database:
    image: postgres:13
    mem_swappiness: 0        # 스왑 비활성화 (DB는 메모리 성능 중요)
    mem_limit: 2g
    
  cache:
    image: redis:7
    mem_swappiness: 0        # 캐시도 스왑 비활성화
    mem_limit: 1g
    
  worker:
    image: worker:latest
    mem_swappiness: 60       # 백그라운드 작업은 스왑 허용
    mem_limit: 512m
```

#### OOM(Out of Memory) 동작 제어

**oom_kill_disable:**
```yaml
services:
  critical-service:
    image: myapp:latest
    mem_limit: 1g
    oom_kill_disable: true   # OOM 발생 시에도 종료하지 않음 (주의!)
```

**oom_score_adj:**
```yaml
services:
  high-priority:
    image: important-app:latest
    oom_score_adj: -500      # 낮은 값 = 종료 우선순위 낮음 (-1000 ~ 1000)
    
  low-priority:
    image: worker:latest
    oom_score_adj: 500       # 높은 값 = 종료 우선순위 높음
```

**OOM Score 동작:**
```
OOM Killer가 메모리 부족 시 종료할 프로세스 선택 기준:
1. oom_score_adj 값이 높을수록 먼저 종료
2. 메모리 사용량이 많을수록 점수 증가
3. 시스템 프로세스는 보호됨

예시:
- nginx (oom_score_adj: -500, 100M 사용) → OOM Score: 낮음
- worker (oom_score_adj: 500, 300M 사용) → OOM Score: 높음
→ worker가 먼저 종료됨
```

### CPU 제한

#### CPU 할당 방식

**CPU Shares (상대적 비율):**
```yaml
services:
  web:
    image: nginx:alpine
    cpu_shares: 1024        # 기본값 1024
    
  api:
    image: api:latest
    cpu_shares: 2048        # web의 2배 CPU 시간 할당
    
  worker:
    image: worker:latest
    cpu_shares: 512         # web의 절반 CPU 시간 할당
```

**동작 원리:**
- 모든 컨테이너가 CPU를 사용하려고 할 때만 적용
- 절대적 제한이 아닌 상대적 우선순위
- 유휴 CPU는 다른 컨테이너가 자유롭게 사용 가능

**시나리오:**
```
총 CPU: 4코어
web(1024) + api(2048) + worker(512) = 3584 shares

CPU 100% 사용 시:
- web: 1024/3584 × 400% = 114% (1.14 코어)
- api: 2048/3584 × 400% = 228% (2.28 코어)
- worker: 512/3584 × 400% = 57% (0.57 코어)

web만 사용 시:
- web: 400% (4코어 모두 사용 가능)
```

**CPU 절대 제한:**
```yaml
services:
  app:
    image: myapp:latest
    cpus: '1.5'             # 최대 1.5 코어 사용
    deploy:
      resources:
        limits:
          cpus: '2.0'       # deploy 방식으로도 가능
        reservations:
          cpus: '0.5'       # 최소 0.5 코어 보장
```

**cpus 옵션 상세:**
- 소수점으로 코어 수 지정 가능
- `0.5` = 1코어의 50% 사용
- `2.0` = 2코어 전체 사용
- 초과 시 CPU 스로틀링 발생

#### CPU 코어 지정 (CPU Pinning)

**특정 코어에 고정:**
```yaml
services:
  high-performance:
    image: compute:latest
    cpuset_cpus: "0,1"      # CPU 0번, 1번 코어에만 실행
    cpuset_mems: "0"        # NUMA 노드 0의 메모리만 사용
    
  database:
    image: postgres:13
    cpuset_cpus: "2-3"      # CPU 2번, 3번 코어에만 실행
    cpuset_mems: "0"
```

**CPU Pinning 사용 이유:**
```
1. 성능 최적화:
   - L1/L2 캐시 히트율 향상
   - 컨텍스트 스위칭 감소
   - NUMA 지역성 활용

2. 격리 보장:
   - 중요한 서비스를 특정 코어에 격리
   - 다른 서비스의 영향 최소화

3. 실시간 처리:
   - 레이턴시에 민감한 애플리케이션
   - CPU 이동으로 인한 지연 방지
```

**NUMA (Non-Uniform Memory Access) 고려:**
```yaml
services:
  numa-aware:
    image: myapp:latest
    cpuset_cpus: "0-7"      # NUMA 노드 0의 코어
    cpuset_mems: "0"        # NUMA 노드 0의 메모리
    # 같은 NUMA 노드를 사용하여 메모리 액세스 속도 최적화
```

#### CPU 쿼터와 피리어드

**세밀한 CPU 시간 제어:**
```yaml
services:
  app:
    image: myapp:latest
    cpu_quota: 50000        # 마이크로초 단위 (50ms)
    cpu_period: 100000      # 마이크로초 단위 (100ms)
    # 결과: 100ms 중 50ms만 사용 가능 = 0.5 코어
```

**동작 원리:**
```
cpu_quota: 컨테이너가 cpu_period 동안 사용할 수 있는 최대 CPU 시간
cpu_period: CPU 시간 측정 주기

예시 1:
cpu_period: 100000 (100ms)
cpu_quota: 50000 (50ms)
→ 100ms마다 50ms만 사용 가능 = 0.5 코어

예시 2:
cpu_period: 100000 (100ms)
cpu_quota: 200000 (200ms)
→ 100ms마다 200ms 사용 가능 = 2.0 코어

실시간 제한:
- 매 period마다 quota 리셋
- quota 소진 시 다음 period까지 CPU 사용 차단
- 스로틀링 발생
```

### 디스크 I/O 제한

#### Block I/O 가중치

**I/O 우선순위 설정:**
```yaml
services:
  database:
    image: postgres:13
    blkio_weight: 1000          # 높은 I/O 우선순위
    volumes:
      - db-data:/var/lib/postgresql/data
    
  logs:
    image: logstash:latest
    blkio_weight: 100           # 낮은 I/O 우선순위
    volumes:
      - log-data:/var/log
```

**blkio_weight 동작:**
- 범위: 10-1000
- 기본값: 500
- CPU shares와 유사한 상대적 가중치
- 높을수록 더 많은 I/O 대역폭 할당

#### 디바이스별 I/O 제한

**읽기/쓰기 속도 제한:**
```yaml
services:
  app:
    image: myapp:latest
    device_read_bps:
      - "/dev/sda:10mb"         # 초당 10MB 읽기 제한
    device_write_bps:
      - "/dev/sda:5mb"          # 초당 5MB 쓰기 제한
    device_read_iops:
      - "/dev/sda:1000"         # 초당 1000번 읽기 제한
    device_write_iops:
      - "/dev/sda:500"          # 초당 500번 쓰기 제한
```

**IOPS vs BPS:**
```
BPS (Bytes Per Second):
- 처리량 중심 제한
- 대용량 순차 I/O에 효과적
- 예: 대용량 파일 읽기/쓰기

IOPS (I/O Operations Per Second):
- 작업 횟수 중심 제한
- 소량 랜덤 I/O에 효과적
- 예: 데이터베이스 트랜잭션

사용 예시:
- 데이터베이스: IOPS 제한 (많은 작은 쿼리)
- 파일 저장소: BPS 제한 (큰 파일 전송)
- 로그 수집: BPS 제한 (연속적인 쓰기)
```

#### 디스크 I/O 스케줄러

**CFQ (Completely Fair Queuing) 설정:**
```yaml
services:
  app:
    image: myapp:latest
    blkio_weight: 500
    blkio_weight_device:
      - "/dev/sda:800"          # sda에 대해서만 높은 가중치
      - "/dev/sdb:200"          # sdb에 대해서는 낮은 가중치
```

### 네트워크 대역폭 제한

Docker Compose에서는 기본적으로 네트워크 대역폭 제한을 직접 지원하지 않지만, tc(Traffic Control)를 사용하여 구현할 수 있습니다.

```yaml
services:
  app:
    image: myapp:latest
    cap_add:
      - NET_ADMIN
    command: >
      sh -c "tc qdisc add dev eth0 root tbf rate 1mbit burst 32kbit latency 400ms &&
             /app/start.sh"
```

### 프로세스 수 제한

**PID 제한:**
```yaml
services:
  app:
    image: myapp:latest
    pids_limit: 100             # 최대 100개 프로세스
```

**동작:**
- 컨테이너 내부에서 생성 가능한 최대 프로세스 수
- fork bomb 공격 방지
- 리소스 고갈 방지

### 파일 디스크립터 제한

**ulimits 설정:**
```yaml
services:
  app:
    image: myapp:latest
    ulimits:
      nofile:
        soft: 65536             # 소프트 리미트
        hard: 65536             # 하드 리미트
      nproc:
        soft: 4096
        hard: 4096
      memlock:
        soft: -1                # 무제한
        hard: -1
```

**주요 ulimit 옵션:**
```
nofile: 열 수 있는 파일 디스크립터 수
  - 웹 서버, 데이터베이스에 중요
  - 기본값(1024)은 고부하 시 부족

nproc: 생성 가능한 최대 프로세스 수
  - 멀티프로세스 애플리케이션에 중요
  
memlock: 잠글 수 있는 메모리 크기
  - 공유 메모리, IPC에 필요
  - Elasticsearch, Redis 등에서 사용

stack: 스택 크기
  - 재귀 함수가 많은 애플리케이션

core: 코어 덤프 파일 크기
  - 디버깅 시 필요
```

### 실전 리소스 프로파일

**데이터베이스 프로파일:**
```yaml
services:
  postgres:
    image: postgres:13
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 4G
        reservations:
          cpus: '2.0'
          memory: 2G
    mem_swappiness: 0           # 스왑 비활성화
    blkio_weight: 1000          # 높은 I/O 우선순위
    cpuset_cpus: "0-3"          # 전용 코어 할당
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
      nproc:
        soft: 4096
        hard: 4096
    volumes:
      - postgres-data:/var/lib/postgresql/data
```

**웹 애플리케이션 프로파일:**
```yaml
services:
  web:
    image: nginx:alpine
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 128M
    cpu_shares: 1024
    mem_swappiness: 60
    ulimits:
      nofile:
        soft: 10000
        hard: 10000
```

**백그라운드 워커 프로파일:**
```yaml
services:
  worker:
    image: worker:latest
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 256M
    cpu_shares: 512             # 낮은 CPU 우선순위
    mem_swappiness: 100         # 스왑 적극 사용
    blkio_weight: 300           # 낮은 I/O 우선순위
    oom_score_adj: 500          # OOM 시 먼저 종료
```

**캐시 서버 프로파일:**
```yaml
services:
  redis:
    image: redis:7-alpine
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
    mem_swappiness: 0           # 스왑 절대 금지
    cpuset_cpus: "4-5"          # 전용 코어
    ulimits:
      nofile:
        soft: 10240
        hard: 10240
    command: >
      redis-server
      --maxmemory 1800mb
      --maxmemory-policy allkeys-lru
```

### 리소스 모니터링

**Docker Stats 사용:**
```bash
# 실시간 리소스 사용량
docker stats

# Compose 서비스별 확인
docker-compose ps -q | xargs docker stats
```

**cAdvisor 통합:**
```yaml
services:
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    ports:
      - "8080:8080"
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
```

---

## CI/CD 파이프라인 통합

### GitHub Actions를 활용한 자동 배포

**기본 배포 워크플로우**
```yaml
name: Deploy Application

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Run tests with Docker Compose
        run: |
          docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
          docker-compose -f docker-compose.test.yml down

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Deploy to production
        run: |
          docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
          docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### 테스트 환경 구성

**테스트용 docker-compose.test.yml**
```yaml
version: '3.8'

services:
  app:
    build: .
    environment:
      - NODE_ENV=test
      - MONGO_URL=mongodb://test-mongodb:27017/testdb
    depends_on:
      - test-mongodb
    command: npm test

  test-mongodb:
    image: mongo:6.0
    environment:
      - MONGO_INITDB_DATABASE=testdb
    tmpfs:
      - /data/db

  test-redis:
    image: redis:7-alpine
    command: redis-server --save ""
```

### Blue-Green 배포 전략

**배포 스크립트 (deploy.sh)**
```bash
#!/bin/bash

# 현재 실행 중인 스택 확인
CURRENT_STACK=$(docker-compose ps -q | wc -l)

if [ $CURRENT_STACK -gt 0 ]; then
    echo "Blue-Green 배포 시작..."
    
    # Green 환경 구축
    docker-compose -f docker-compose.yml -f docker-compose.green.yml up -d --build
    
    # Health check
    sleep 30
    if curl -f http://localhost:8080/health; then
        echo "Green 환경 배포 성공"
        
        # Blue 환경 중지
        docker-compose -f docker-compose.yml -f docker-compose.blue.yml down
        
        # Green을 Blue로 변경
        mv docker-compose.green.yml docker-compose.blue.yml
    else
        echo "Green 환경 배포 실패, 롤백"
        docker-compose -f docker-compose.yml -f docker-compose.green.yml down
    fi
else
    echo "초기 배포"
    docker-compose -f docker-compose.yml -f docker-compose.blue.yml up -d --build
fi
```

---

## 성능 최적화 및 트러블슈팅

### 성능 최적화 기법

**리소스 제한 및 예약**
```yaml
version: '3.8'

services:
  app:
    image: myapp:latest
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
```

**볼륨 최적화**
```yaml
version: '3.8'

services:
  app:
    image: myapp:latest
    volumes:
      # 성능 향상을 위한 tmpfs 사용
      - type: tmpfs
        target: /tmp
        tmpfs:
          size: 100M
      # 바인드 마운트 최적화
      - type: bind
        source: ./app
        target: /app
        consistency: cached
```

### 일반적인 문제 해결

**서비스 시작 순서 문제**
```yaml
version: '3.8'

services:
  app:
    image: myapp:latest
    depends_on:
      mongodb:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  mongodb:
    image: mongo:6.0
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**네트워크 연결 문제**
```bash
# 네트워크 상태 확인
docker network ls
docker network inspect <network_name>

# 서비스 간 연결 테스트
docker-compose exec app ping mongodb
docker-compose exec app nslookup mongodb
```

### 모니터링 및 로그 관리

**통합 모니터링 스택**
```yaml
version: '3.8'

services:
  app:
    image: myapp:latest
    labels:
      - "prometheus.scrape=true"
      - "prometheus.port=3000"
      - "prometheus.path=/metrics"

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
```

---

## 참고자료

### 관련 문서

- [Kubernetes 심화 전략](../Kubernetes_심화_전략.md) - Kubernetes와 Docker Compose 비교
- [CI/CD 고급 패턴](../../CI_CD/고급_CI_CD_패턴.md) - Docker Compose를 활용한 CI/CD
- [배포 전략](../../../Framework/Node/배포/배포_전략.md) - 컨테이너 배포 전략
- [AWS ECS](../../../../AWS/Containers/ECS.md) - AWS 컨테이너 서비스
- [Terraform 인프라 자동화](../../Infrastructure_as_Code/Terraform.md) - 인프라 자동화

---

### 공식 문서
- [Docker Compose 공식 문서](https://docs.docker.com/compose/)
- [Docker Compose 파일 참조](https://docs.docker.com/compose/compose-file/)
- [Docker Compose 명령어 참조](https://docs.docker.com/compose/reference/)

### 관련 기술 문서
- [Docker 공식 문서](https://docs.docker.com/)
- [Dockerfile 모범 사례](https://docs.docker.com/develop/dev-best-practices/)
- [Docker 보안 모범 사례](https://docs.docker.com/engine/security/)

### 추가 학습 자료
- [Docker Compose 네트워킹 가이드](https://docs.docker.com/compose/networking/)
- [Docker Compose 볼륨 가이드](https://docs.docker.com/compose/compose-file/compose-file-v3/#volumes)
- [Docker Compose 환경 변수 가이드](https://docs.docker.com/compose/environment-variables/)

### 도구 및 플러그인
- [Docker Compose VSCode 확장](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-docker)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Portainer - Docker 관리 UI](https://www.portainer.io/)

