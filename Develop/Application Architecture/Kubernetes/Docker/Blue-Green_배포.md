---
title: Docker Blue-Green
tags: [application-architecture, kubernetes, docker, blue-green배포]
updated: 2025-08-10
---
# Docker Blue-Green 배포

## 🎯 Blue-Green 배포란?

Blue-Green 배포는 **무중단 배포 전략** 중 하나입니다. 

## 배경
- **Blue**: 현재 운영 중인 안정적인 환경
- **Green**: 새로 배포할 새로운 환경
- 두 환경을 **완전히 분리**해서 운영하고, 준비가 완료되면 트래픽을 한 번에 전환하는 방식

1. 현재 사용자들은 **Blue 환경**에서 서비스를 이용
2. **Green 환경**에 새로운 버전을 배포하고 테스트
3. Green 환경이 안정적이면 **트래픽을 Blue에서 Green으로 전환**
4. 문제 발생 시 **즉시 Blue로 롤백** 가능

---


### **무중단 배포 (Zero-Downtime Deployment)**
- 서비스 중단 없이 새로운 버전을 배포하는 방식
- 사용자가 서비스 중단을 경험하지 않음

### **트래픽 스위칭 (Traffic Switching)**
- 사용자 요청을 한 환경에서 다른 환경으로 전환하는 과정
- 보통 로드 밸런서(Load Balancer)를 통해 수행

### **롤백 (Rollback)**
- 새로운 버전에 문제가 있을 때 이전 버전으로 되돌리는 과정
- Blue-Green 배포에서는 매우 빠르게 수행 가능

### **로드 밸런서 (Load Balancer)**
- 사용자 요청을 여러 서버에 분산시키는 장치
- 트래픽 전환의 핵심 역할을 담당

---

```
blue-green-deploy/
├── nginx/
│   └── default.conf          # 트래픽 전환 설정
├── blue/
│   ├── Dockerfile
│   ├── package.json
│   └── app.js               # Blue 버전 애플리케이션
├── green/
│   ├── Dockerfile
│   ├── package.json
│   └── app.js               # Green 버전 애플리케이션
└── docker-compose.yml       # 전체 환경 구성
```

---


### Blue 버전 (`blue/app.js`)
```javascript
const express = require('express');
const app = express();
const port = 3000;

app.get('/', (req, res) => {
  res.json({
    message: 'Hello from BLUE version!',
    version: '1.0.0',
    timestamp: new Date().toISOString()
  });
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy', environment: 'blue' });
});

app.listen(port, () => {
  console.log(`Blue app listening at http://localhost:${port}`);
});
```

### Green 버전 (`green/app.js`)
```javascript
const express = require('express');
const app = express();
const port = 3000;

app.get('/', (req, res) => {
  res.json({
    message: 'Hello from GREEN version!',
    version: '2.0.0',
    timestamp: new Date().toISOString(),
    newFeature: 'Enhanced user experience'
  });
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy', environment: 'green' });
});

app.listen(port, () => {
  console.log(`Green app listening at http://localhost:${port}`);
});
```

### Package.json (Blue & Green 동일)
```json
{
  "name": "blue-green-app",
  "version": "1.0.0",
  "main": "app.js",
  "dependencies": {
    "express": "^4.18.2"
  },
  "scripts": {
    "start": "node app.js"
  }
}
```

---

WORKDIR /app

RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
```

---

- Blue와 Green 환경이 같은 데이터베이스를 사용할 경우
- 데이터베이스 스키마 변경 시 마이그레이션 전략 필요
- 데이터 일관성 유지가 중요

- 두 개의 완전한 환경을 유지해야 함
- 인프라 비용이 증가할 수 있음

- 사용자 세션이 Blue에 저장된 경우 Green으로 전환 시 문제 발생 가능
- 세션 공유 또는 세션리스 아키텍처 고려 필요

- 환경별 설정 파일 관리
- 환경 변수와 설정 값의 동기화

---

- Blue와 Green 환경이 같은 데이터베이스를 사용할 경우
- 데이터베이스 스키마 변경 시 마이그레이션 전략 필요
- 데이터 일관성 유지가 중요

- 두 개의 완전한 환경을 유지해야 함
- 인프라 비용이 증가할 수 있음

- 사용자 세션이 Blue에 저장된 경우 Green으로 전환 시 문제 발생 가능
- 세션 공유 또는 세션리스 아키텍처 고려 필요

- 환경별 설정 파일 관리
- 환경 변수와 설정 값의 동기화

---


1. Green 환경에 새 버전 배포
2. 자동화된 테스트 실행
3. 수동 검증 및 승인
4. 트래픽을 Blue에서 Green으로 전환
5. Blue 환경을 새로운 Green으로 준비

1. Green 환경에 핫픽스 배포
2. 빠른 검증 후 즉시 전환
3. 문제 발생 시 Blue로 롤백

1. Green 환경에서 문제 감지
2. 즉시 Blue 환경으로 트래픽 전환
3. Green 환경에서 문제 해결
4. 해결 후 다시 Green으로 전환

1. Green 환경에 새 버전 배포
2. 자동화된 테스트 실행
3. 수동 검증 및 승인
4. 트래픽을 Blue에서 Green으로 전환
5. Blue 환경을 새로운 Green으로 준비

1. Green 환경에 핫픽스 배포
2. 빠른 검증 후 즉시 전환
3. 문제 발생 시 Blue로 롤백

1. Green 환경에서 문제 감지
2. 즉시 Blue 환경으로 트래픽 전환
3. Green 환경에서 문제 해결
4. 해결 후 다시 Green으로 전환










## 🌐 Nginx 설정

### `nginx/default.conf`
```nginx

upstream blue_backend {
    server blue:3000;
}

upstream green_backend {
    server green:3000;
}

server {
    listen 80;
    server_name localhost;

    # 기본적으로 Blue 환경으로 트래픽 전달
    location / {
        proxy_pass http://blue_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 헬스 체크 엔드포인트
    location /health {
        proxy_pass http://blue_backend;
        proxy_set_header Host $host;
    }
}
```

---

## 🐳 Docker Compose 설정

### `docker-compose.yml`
```yaml
version: '3.8'

services:


### 1️⃣ 초기 환경 구축
```bash

cd blue-green-deploy

docker-compose ps
```

### 2️⃣ Blue 환경 테스트
```bash

curl http://localhost:80
```

### 4️⃣ 롤백 (문제 발생 시)
```bash


### 전환 스크립트 (`switch-traffic.js`)
```javascript
const fs = require('fs');
const { exec } = require('child_process');

function switchToGreen() {
  console.log('🔄 Green 환경으로 전환 중...');
  
  // Nginx 설정 파일 읽기
  let config = fs.readFileSync('./nginx/default.conf', 'utf8');
  
  // Blue에서 Green으로 변경
  config = config.replace(
    /proxy_pass http:\/\/blue_backend;/g,
    'proxy_pass http://green_backend;'
  );
  
  // 설정 파일 저장
  fs.writeFileSync('./nginx/default.conf', config);
  
  // Nginx 재시작
  exec('docker-compose restart nginx', (error, stdout, stderr) => {
    if (error) {
      console.error('❌ 전환 실패:', error);
      return;
    }
    console.log('✅ Green 환경으로 전환 완료!');
  });
}

function switchToBlue() {
  console.log('🔄 Blue 환경으로 롤백 중...');
  
  // Nginx 설정 파일 읽기
  let config = fs.readFileSync('./nginx/default.conf', 'utf8');
  
  // Green에서 Blue로 변경
  config = config.replace(
    /proxy_pass http:\/\/green_backend;/g,
    'proxy_pass http://blue_backend;'
  );
  
  // 설정 파일 저장
  fs.writeFileSync('./nginx/default.conf', config);
  
  // Nginx 재시작
  exec('docker-compose restart nginx', (error, stdout, stderr) => {
    if (error) {
      console.error('❌ 롤백 실패:', error);
      return;
    }
    console.log('✅ Blue 환경으로 롤백 완료!');
  });
}

// 명령행 인수에 따라 전환
const target = process.argv[2];
if (target === 'green') {
  switchToGreen();
} else if (target === 'blue') {
  switchToBlue();
} else {
  console.log('사용법: node switch-traffic.js [blue|green]');
}
```

---

- 사용자가 서비스 중단을 경험하지 않음
- 24/7 서비스 운영 가능

- 문제 발생 시 즉시 이전 버전으로 복구
- 장애 시간 최소화

- 실제 트래픽 없이 새 버전 테스트 가능
- 완전히 분리된 환경에서 검증

- 전체 사용자를 한 번에 전환하지 않고 점진적으로 가능
- A/B 테스트와 연계 가능

---


## 🏗 Docker 기반 Blue-Green 배포 실습

## 📦 Dockerfile 작성

### Blue & Green용 Dockerfile
```dockerfile
# Node.js 18 버전을 베이스로 사용
FROM node:18-alpine

# package.json과 package-lock.json 복사
COPY package*.json ./

  # Nginx 리버스 프록시
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - blue
      - green
    networks:
      - app-network

  # Blue 환경 (현재 운영 중)
  blue:
    build:
      context: ./blue
      dockerfile: Dockerfile
    container_name: blue-app
    ports:
      - "3001:3000"
    networks:
      - app-network
    environment:
      - NODE_ENV=production

  # Green 환경 (새로운 버전)
  green:
    build:
      context: ./green
      dockerfile: Dockerfile
    container_name: green-app
    ports:
      - "3002:3000"
    networks:
      - app-network
    environment:
      - NODE_ENV=production

networks:
  app-network:
    driver: bridge
```

---

# Docker Compose로 환경 실행
docker-compose up -d

# Blue 환경 직접 접근
curl http://localhost:3001

# Nginx를 통한 접근 (현재 Blue로 설정됨)
curl http://localhost:80
```

### 3️⃣ Green 환경으로 전환
```bash
# Nginx 설정 파일 수정
# nginx/default.conf에서 proxy_pass를 green_backend로 변경

# Nginx 재시작
docker-compose restart nginx

# Nginx 설정을 다시 blue_backend로 변경
# nginx/default.conf 수정

# Nginx 재시작
docker-compose restart nginx
```

---

## ✅ Blue-Green 배포의 장점

