---
title: 프록시 (Proxy) 완벽 가이드
tags: [network, proxy, forward-proxy, reverse-proxy, load-balancing, caching]
updated: 2024-12-19
---

# 프록시 (Proxy) 완벽 가이드

## 배경

### 프록시란?
프록시는 "대리인" 또는 "중개자"라는 의미로, 클라이언트와 서버 사이에서 중개 역할을 하는 소프트웨어나 하드웨어를 말합니다. 일상생활의 부동산 중개업소와 같은 역할을 하며, 클라이언트와 서버가 직접 연결되지 않고 프록시를 통해 통신합니다.

### 프록시의 필요성
1. **보안**: 직접 연결을 차단하여 공격으로부터 보호
2. **익명성**: 클라이언트 정보를 숨김
3. **성능**: 캐싱으로 빠른 응답
4. **제어**: 특정 사이트 접근 차단
5. **로드 밸런싱**: 서버 부하 분산

### 기본 개념
- **Forward Proxy**: 클라이언트 측에서 사용하는 프록시
- **Reverse Proxy**: 서버 측에서 사용하는 프록시
- **Transparent Proxy**: 클라이언트가 프록시 존재를 모르는 프록시
- **Anonymous Proxy**: 프록시 사용을 숨기는 프록시

## 핵심

### 1. Forward Proxy (포워드 프록시)

클라이언트 → 프록시 → 서버 방향으로 요청이 흐르며, 주로 클라이언트 보호와 접근 제어에 사용됩니다.

#### 사용 환경
- 회사 네트워크
- 학교 네트워크
- 인터넷 접근 제한이 필요한 환경

#### JavaScript 예시
```javascript
const http = require('http');

// 포워드 프록시 서버 생성
const forwardProxy = http.createServer((clientReq, clientRes) => {
  console.log('클라이언트가 요청한 URL:', clientReq.url);
  console.log('클라이언트 IP:', clientReq.connection.remoteAddress);

  // 실제 서버로 요청을 전달할 설정
  const serverOptions = {
    hostname: 'api.example.com',  // 실제 서버 주소
    port: 80,
    path: clientReq.url,          // 클라이언트가 요청한 경로
    method: clientReq.method,     // GET, POST 등
    headers: {
      ...clientReq.headers,
      'X-Forwarded-For': clientReq.connection.remoteAddress  // 원본 IP 기록
    }
  };

  // 실제 서버로 요청 전송
  const serverReq = http.request(serverOptions, (serverRes) => {
    console.log('서버 응답 상태:', serverRes.statusCode);
    
    // 서버 응답을 클라이언트에게 전달
    clientRes.writeHead(serverRes.statusCode, serverRes.headers);
    serverRes.pipe(clientRes);
  });

  // 에러 처리
  serverReq.on('error', (error) => {
    console.error('서버 요청 에러:', error);
    clientRes.writeHead(500);
    clientRes.end('프록시 서버 에러');
  });

  // 클라이언트 요청 데이터를 서버로 전달
  clientReq.pipe(serverReq);
});

// 프록시 서버 시작
forwardProxy.listen(8080, () => {
  console.log('포워드 프록시 서버가 8080 포트에서 실행 중입니다.');
  console.log('클라이언트는 http://localhost:8080 으로 접속하세요.');
});
```

### 2. Reverse Proxy (리버스 프록시)

클라이언트 → 프록시 → 여러 서버 방향으로 요청이 흐르며, 주로 서버 보호와 로드 밸런싱에 사용됩니다.

#### 사용 환경
- 웹 서버 로드 밸런싱
- SSL 인증서 관리
- 캐싱 서버
- API 게이트웨이

#### JavaScript 예시
```javascript
const http = require('http');
const url = require('url');

// 여러 백엔드 서버 목록
const backendServers = [
  { hostname: 'server1.example.com', port: 3001, weight: 1 },
  { hostname: 'server2.example.com', port: 3002, weight: 1 },
  { hostname: 'server3.example.com', port: 3003, weight: 1 }
];

let currentServerIndex = 0;

// 라운드 로빈 방식으로 서버 선택
function getNextServer() {
  const server = backendServers[currentServerIndex];
  currentServerIndex = (currentServerIndex + 1) % backendServers.length;
  return server;
}

// 리버스 프록시 서버 생성
const reverseProxy = http.createServer((clientReq, clientRes) => {
  const parsedUrl = url.parse(clientReq.url);
  const selectedServer = getNextServer();
  
  console.log(`요청을 ${selectedServer.hostname}:${selectedServer.port}로 전달`);

  // 백엔드 서버로 요청 전달할 설정
  const serverOptions = {
    hostname: selectedServer.hostname,
    port: selectedServer.port,
    path: parsedUrl.path,
    method: clientReq.method,
    headers: {
      ...clientReq.headers,
      'Host': selectedServer.hostname  // 호스트 헤더 변경
    }
  };

  // 백엔드 서버로 요청 전송
  const serverReq = http.request(serverOptions, (serverRes) => {
    console.log(`서버 ${selectedServer.hostname} 응답:`, serverRes.statusCode);
    
    // 서버 응답을 클라이언트에게 전달
    clientRes.writeHead(serverRes.statusCode, serverRes.headers);
    serverRes.pipe(clientRes);
  });

  // 에러 처리
  serverReq.on('error', (error) => {
    console.error(`서버 ${selectedServer.hostname} 연결 에러:`, error);
    clientRes.writeHead(502);
    clientRes.end('백엔드 서버 연결 실패');
  });

  // 클라이언트 요청 데이터를 백엔드 서버로 전달
  clientReq.pipe(serverReq);
});

// 리버스 프록시 서버 시작
reverseProxy.listen(80, () => {
  console.log('리버스 프록시 서버가 80 포트에서 실행 중입니다.');
  console.log('로드 밸런싱 대상 서버:');
  backendServers.forEach((server, index) => {
    console.log(`  ${index + 1}. ${server.hostname}:${server.port}`);
  });
});
```

### 3. 프록시 동작 흐름

#### Forward Proxy 동작 흐름
```
1. 클라이언트가 프록시 서버에 요청
2. 프록시가 클라이언트 정보를 기록
3. 프록시가 실제 서버에 요청 전달
4. 서버가 프록시에 응답
5. 프록시가 클라이언트에 응답 전달
```

#### Reverse Proxy 동작 흐름
```
1. 클라이언트가 프록시 서버에 요청
2. 프록시가 적절한 백엔드 서버 선택
3. 프록시가 백엔드 서버에 요청 전달
4. 백엔드 서버가 프록시에 응답
5. 프록시가 클라이언트에 응답 전달
```

## 예시

### 1. 실제 사용 사례

#### 회사 네트워크 관리
```javascript
// 특정 사이트 차단 예시
const blockedSites = ['facebook.com', 'youtube.com', 'twitter.com'];

function isBlockedSite(url) {
  return blockedSites.some(site => url.includes(site));
}

// 프록시에서 차단 로직 적용
if (isBlockedSite(clientReq.url)) {
  clientRes.writeHead(403);
  clientRes.end('접근이 차단된 사이트입니다.');
  return;
}
```

#### 캐싱 프록시
```javascript
const cache = new Map();

// 캐시 확인 및 응답
function serveFromCache(url, clientRes) {
  const cached = cache.get(url);
  if (cached && Date.now() - cached.timestamp < 300000) { // 5분 캐시
    console.log('캐시에서 응답');
    clientRes.writeHead(200, cached.headers);
    clientRes.end(cached.data);
    return true;
  }
  return false;
}

// 캐시 저장
function saveToCache(url, headers, data) {
  cache.set(url, {
    headers: headers,
    data: data,
    timestamp: Date.now()
  });
}
```

#### SSL 종료 (Reverse Proxy)
```javascript
const https = require('https');
const fs = require('fs');

// SSL 인증서 설정
const sslOptions = {
  key: fs.readFileSync('private-key.pem'),
  cert: fs.readFileSync('certificate.pem')
};

// HTTPS 리버스 프록시
const httpsProxy = https.createServer(sslOptions, (req, res) => {
  // HTTP로 백엔드 서버와 통신
  const backendReq = http.request({
    hostname: 'backend.example.com',
    port: 3000,
    path: req.url,
    method: req.method,
    headers: req.headers
  }, (backendRes) => {
    res.writeHead(backendRes.statusCode, backendRes.headers);
    backendRes.pipe(res);
  });
  
  req.pipe(backendReq);
});

httpsProxy.listen(443, () => {
  console.log('HTTPS 리버스 프록시가 443 포트에서 실행 중입니다.');
});
```

### 2. 로드 밸런싱 알고리즘

#### 라운드 로빈 (Round Robin)
```javascript
let currentIndex = 0;

function roundRobin(servers) {
  const server = servers[currentIndex];
  currentIndex = (currentIndex + 1) % servers.length;
  return server;
}
```

#### 최소 연결 수 (Least Connections)
```javascript
function leastConnections(servers) {
  return servers.reduce((min, server) => 
    server.connections < min.connections ? server : min
  );
}
```

#### IP 해시 (IP Hash)
```javascript
function ipHash(clientIP, servers) {
  const hash = clientIP.split('.').reduce((acc, octet) => 
    acc + parseInt(octet), 0
  );
  return servers[hash % servers.length];
}
```

## 운영 팁

### 1. 프록시 설정

#### Nginx 리버스 프록시 설정
```nginx
upstream backend {
    server 192.168.1.10:3000;
    server 192.168.1.11:3000;
    server 192.168.1.12:3000;
}

server {
    listen 80;
    server_name example.com;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Apache 프록시 설정
```apache
<VirtualHost *:80>
    ServerName example.com
    
    ProxyPreserveHost On
    ProxyPass / http://backend.example.com/
    ProxyPassReverse / http://backend.example.com/
    
    ProxyRequests Off
    ProxyVia Full
</VirtualHost>
```

### 2. 모니터링 및 로깅

#### 프록시 로깅
```javascript
// 프록시 요청 로깅
function logRequest(req, res, next) {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(`${req.method} ${req.url} ${res.statusCode} ${duration}ms`);
  });
  
  next();
}
```

#### 헬스 체크
```javascript
// 백엔드 서버 헬스 체크
function healthCheck(server) {
  const req = http.request({
    hostname: server.hostname,
    port: server.port,
    path: '/health',
    timeout: 5000
  }, (res) => {
    if (res.statusCode === 200) {
      server.healthy = true;
    } else {
      server.healthy = false;
    }
  });
  
  req.on('error', () => {
    server.healthy = false;
  });
  
  req.end();
}
```

## 참고

### 프록시의 장단점

#### 장점
- **보안 강화**: 직접 연결 차단으로 공격 방지
- **익명성 보장**: 클라이언트 정보 숨김
- **성능 향상**: 캐싱으로 응답 속도 개선
- **트래픽 제어**: 특정 사이트 접근 차단 가능
- **로드 밸런싱**: 서버 부하 분산

#### 단점
- **지연 시간**: 프록시를 거치면서 추가 지연 발생
- **복잡성**: 설정과 유지보수 필요
- **단일 장애점**: 프록시 서버 장애 시 전체 서비스 영향
- **대역폭 사용**: 프록시 서버의 추가 리소스 필요

### HTTP 헤더
- **X-Forwarded-For**: 클라이언트 원본 IP
- **X-Forwarded-Host**: 클라이언트 원본 호스트
- **X-Forwarded-Proto**: 클라이언트 원본 프로토콜

### 프록시 패턴
- **Transparent Proxy**: 클라이언트가 프록시 존재를 모름
- **Anonymous Proxy**: 프록시 사용을 숨김
- **High Anonymity Proxy**: 완전한 익명성 제공

### 결론
프록시는 현대 웹 아키텍처에서 보안, 성능, 확장성을 위해 필수적인 기술입니다. Forward Proxy는 클라이언트 보호에, Reverse Proxy는 서버 관리에 특화되어 있으며, 각각의 특성을 이해하고 적절히 활용하는 것이 중요합니다.










