
# Docker Compose 완전 가이드

**작성일**: 2025-09-22
**목적**: Docker Compose의 개념, 사용법, 고급 활용법에 대한 종합적인 이해

## 1. Docker Compose 개념

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

## 2. Docker Compose 파일 구조 및 주요 구성 요소

### 2.1 기본 파일 구조

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

### 2.2 핵심 구성 요소 상세 분석

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

### 2.3 주요 설정 옵션

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

## 3. 실전 예제: Node.js + MongoDB + Redis 스택

### 3.1 기본 웹 애플리케이션 스택

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

### 3.2 구성 요소 상세 분석

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

## 4. Docker Compose 명령어 및 운영 방법

### 4.1 기본 명령어

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

### 4.2 고급 운영 명령어

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

### 4.3 환경별 구성 관리

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

## 5. 고급 활용 기법 및 모범 사례

### 5.1 환경 변수 관리

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

### 5.2 다중 환경 구성

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

### 5.3 보안 및 시크릿 관리

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

### 5.4 네트워킹 및 서비스 디스커버리

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

### 5.5 모니터링 및 로깅

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

## 6. CI/CD 파이프라인 통합

### 6.1 GitHub Actions를 활용한 자동 배포

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

### 6.2 테스트 환경 구성

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

### 6.3 Blue-Green 배포 전략

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

## 7. 성능 최적화 및 트러블슈팅

### 7.1 성능 최적화 기법

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

### 7.2 일반적인 문제 해결

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

### 7.3 모니터링 및 로그 관리

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

## 8. 결론

Docker Compose는 현대적인 애플리케이션 개발과 배포에 필수적인 도구입니다. 이 가이드를 통해 다음과 같은 핵심 개념들을 다뤘습니다:

### 주요 학습 내용

1. **선언적 구성 관리**: YAML 파일을 통한 인프라 코드화
2. **서비스 오케스트레이션**: 다중 컨테이너 환경의 효율적 관리
3. **환경별 구성**: 개발, 테스트, 프로덕션 환경의 일관성 유지
4. **보안 및 시크릿 관리**: 민감한 정보의 안전한 처리
5. **CI/CD 통합**: 자동화된 배포 파이프라인 구축
6. **성능 최적화**: 리소스 관리 및 모니터링

### 실무 적용 가이드

- **개발 단계**: 로컬 개발 환경의 빠른 구축과 일관성 유지
- **테스트 단계**: 격리된 테스트 환경에서의 안정적인 검증
- **배포 단계**: Blue-Green 배포를 통한 무중단 서비스 제공
- **운영 단계**: 모니터링과 로깅을 통한 지속적인 서비스 품질 관리

Docker Compose를 효과적으로 활용하면 복잡한 멀티 컨테이너 애플리케이션을 간단하고 안정적으로 관리할 수 있으며, 팀의 개발 생산성과 서비스의 안정성을 크게 향상시킬 수 있습니다.

---

## 참조

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

