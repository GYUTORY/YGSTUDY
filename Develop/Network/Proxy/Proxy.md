# Proxy (프록시) 완벽 이해하기

## 📖 프록시란?

프록시는 **"대리인"** 또는 **"중개자"**라는 의미로, 클라이언트와 서버 사이에서 중개 역할을 하는 소프트웨어나 하드웨어를 말합니다.

### 🔍 쉽게 이해하기
- **일상생활 예시**: 부동산 중개업소
  - 집을 구하려는 사람(클라이언트) → 중개업소(프록시) → 집주인(서버)
  - 직접 만나지 않고 중개업소를 통해 거래

### 💡 왜 프록시를 사용할까?
1. **보안**: 직접 연결을 차단하여 공격으로부터 보호
2. **익명성**: 클라이언트 정보를 숨김
3. **성능**: 캐싱으로 빠른 응답
4. **제어**: 특정 사이트 접근 차단

---

## 🚀 프록시의 두 가지 주요 유형

### 1️⃣ Forward Proxy (포워드 프록시)

**클라이언트 → 프록시 → 서버** 방향으로 요청이 흐릅니다.

#### 🏢 사용 환경
- 회사 네트워크
- 학교 네트워크
- 인터넷 접근 제한이 필요한 환경

#### 📝 JavaScript 예시

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

#### 🔧 주요 용어 설명
- **hostname**: 실제 서버의 도메인 주소
- **X-Forwarded-For**: 클라이언트의 원본 IP 주소를 기록하는 헤더
- **pipe()**: 데이터 스트림을 연결하는 메서드
- **writeHead()**: HTTP 응답 헤더를 설정하는 메서드

---

### 2️⃣ Reverse Proxy (리버스 프록시)

**클라이언트 → 프록시 → 여러 서버** 방향으로 요청이 흐릅니다.

#### 🏢 사용 환경
- 웹 서버 로드 밸런싱
- SSL 인증서 관리
- 캐싱 서버
- API 게이트웨이

#### 📝 JavaScript 예시

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

#### 🔧 주요 용어 설명
- **라운드 로빈**: 요청을 순차적으로 각 서버에 분배하는 방식
- **로드 밸런싱**: 서버 부하를 여러 서버에 분산시키는 기술
- **Host 헤더**: 요청이 어떤 서버로 가는지 지정하는 HTTP 헤더
- **502 Bad Gateway**: 프록시가 백엔드 서버로부터 잘못된 응답을 받았을 때의 HTTP 상태 코드

---

## 🔄 프록시 동작 과정

### Forward Proxy 동작 흐름
```
1. 클라이언트가 프록시 서버에 요청
2. 프록시가 클라이언트 정보를 기록
3. 프록시가 실제 서버에 요청 전달
4. 서버가 프록시에 응답
5. 프록시가 클라이언트에 응답 전달
```

### Reverse Proxy 동작 흐름
```
1. 클라이언트가 프록시 서버에 요청
2. 프록시가 적절한 백엔드 서버 선택
3. 프록시가 백엔드 서버에 요청 전달
4. 백엔드 서버가 프록시에 응답
5. 프록시가 클라이언트에 응답 전달
```

---

## ⚖️ 프록시의 장단점

### ✅ 장점
- **보안 강화**: 직접 연결 차단으로 공격 방지
- **익명성 보장**: 클라이언트 정보 숨김
- **성능 향상**: 캐싱으로 응답 속도 개선
- **트래픽 제어**: 특정 사이트 접근 차단 가능
- **로드 밸런싱**: 서버 부하 분산

### ❌ 단점
- **지연 시간**: 프록시를 거치면서 추가 지연 발생
- **복잡성**: 설정과 유지보수 필요
- **단일 장애점**: 프록시 서버 장애 시 전체 서비스 영향
- **대역폭 사용**: 프록시 서버의 추가 리소스 필요

---

## 🛠️ 실제 활용 사례

### 1. 회사 네트워크 관리
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

### 2. 캐싱 프록시
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
```

### 3. SSL 종료 (Reverse Proxy)
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
```

---

## 📚 관련 개념들

### HTTP 헤더
- **X-Forwarded-For**: 클라이언트 원본 IP
- **X-Forwarded-Host**: 클라이언트 원본 호스트
- **X-Forwarded-Proto**: 클라이언트 원본 프로토콜

### 프록시 패턴
- **Transparent Proxy**: 클라이언트가 프록시 존재를 모름
- **Anonymous Proxy**: 프록시 사용을 숨김
- **High Anonymity Proxy**: 완전한 익명성 제공

### 로드 밸런싱 알고리즘
- **Round Robin**: 순차 분배
- **Least Connections**: 연결 수가 적은 서버 우선
- **IP Hash**: 클라이언트 IP 기반 서버 선택
- **Weighted Round Robin**: 가중치 기반 분배

---

## 🎯 마무리

프록시는 현대 웹 아키텍처에서 **보안, 성능, 확장성**을 위해 필수적인 기술입니다. Forward Proxy는 클라이언트 보호에, Reverse Proxy는 서버 관리에 특화되어 있으며, 각각의 특성을 이해하고 적절히 활용하는 것이 중요합니다.

