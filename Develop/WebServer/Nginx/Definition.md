# Nginx 이해하기

## 📖 웹서버란 무엇일까?

### 웹서버의 기본 개념
웹서버는 인터넷에서 웹사이트를 제공하는 프로그램입니다. 마치 식당에서 손님(클라이언트)의 주문을 받아서 요리(웹페이지)를 제공하는 것과 비슷합니다.

**간단한 비유:**
- 클라이언트 = 손님 (브라우저)
- 웹서버 = 식당 (서버)
- 요청 = 주문 (HTTP 요청)
- 응답 = 음식 (HTML, CSS, JS 등)

### 웹서버가 하는 일
1. **정적 파일 제공** - 이미 만들어진 파일들을 그대로 전달
   - HTML 파일 (웹페이지 구조)
   - CSS 파일 (디자인)
   - JavaScript 파일 (동작)
   - 이미지, 동영상 등

2. **동적 처리** - 실시간으로 만들어지는 내용
   - 사용자 로그인 처리
   - 데이터베이스에서 정보 가져오기
   - 실시간 계산 결과

### JavaScript로 이해하는 웹서버
```javascript
// 간단한 웹서버 예시 (Node.js)
const http = require('http');

const server = http.createServer((req, res) => {
    // 클라이언트의 요청을 받음
    console.log('클라이언트가 요청했습니다:', req.url);
    
    // 응답을 보냄
    res.writeHead(200, {'Content-Type': 'text/html'});
    res.end('<h1>안녕하세요! 웹서버입니다!</h1>');
});

server.listen(3000, () => {
    console.log('웹서버가 3000번 포트에서 실행 중입니다');
});
```

## 🚀 Nginx 소개

### Nginx란?
Nginx(엔진엑스)는 2004년에 만들어진 고성능 웹서버입니다. 현재 전 세계 웹사이트의 약 33%가 사용하고 있어요.

**이름의 의미:**
- Nginx = "Engine X" (엔진 X)
- X는 알 수 없다는 의미로, 어떤 엔진인지 모르겠다는 뜻

### Nginx의 특징
1. **빠르다** - 동시에 많은 사용자를 처리할 수 있음
2. **가볍다** - 메모리를 적게 사용
3. **안정적이다** - 오랫동안 안정적으로 작동
4. **다재다능하다** - 다양한 기능 제공

### JavaScript로 이해하는 Nginx의 역할
```javascript
// Nginx가 하는 일을 JavaScript로 표현
class Nginx {
    constructor() {
        this.connections = new Map(); // 연결 관리
        this.cache = new Map();       // 캐시 저장
    }
    
    // 요청 처리 (비동기 방식)
    async handleRequest(request) {
        // 1. 캐시 확인
        if (this.cache.has(request.url)) {
            return this.cache.get(request.url);
        }
        
        // 2. 정적 파일인지 확인
        if (this.isStaticFile(request.url)) {
            const content = await this.serveStaticFile(request.url);
            this.cache.set(request.url, content);
            return content;
        }
        
        // 3. 백엔드 서버로 전달
        return await this.proxyToBackend(request);
    }
    
    // 정적 파일 확인
    isStaticFile(url) {
        const staticExtensions = ['.html', '.css', '.js', '.jpg', '.png'];
        return staticExtensions.some(ext => url.endsWith(ext));
    }
}
```

## 🔍 주요 용어 설명

### 1. 정적 컨텐츠 vs 동적 컨텐츠

**정적 컨텐츠 (Static Content)**
- 미리 만들어져 있는 파일
- 요청할 때마다 같은 내용
- 예: HTML, CSS, JavaScript, 이미지

```javascript
// 정적 컨텐츠 예시
const staticFiles = {
    '/index.html': '<html><body><h1>안녕하세요</h1></body></html>',
    '/style.css': 'body { font-family: Arial; }',
    '/script.js': 'console.log("Hello World");'
};
```

**동적 컨텐츠 (Dynamic Content)**
- 실시간으로 만들어지는 내용
- 요청할 때마다 다른 내용
- 예: 사용자별 맞춤 페이지, 실시간 데이터

```javascript
// 동적 컨텐츠 예시
function generateDynamicContent(userId) {
    return `<html>
        <body>
            <h1>${userId}님 환영합니다!</h1>
            <p>현재 시간: ${new Date().toLocaleString()}</p>
        </body>
    </html>`;
}
```

### 2. 이벤트 기반 (Event-Driven)
Nginx의 핵심 특징 중 하나입니다.

**전통적인 방식 (Apache)**
```javascript
// 프로세스/스레드 기반 (Apache 방식)
class TraditionalServer {
    handleRequest(request) {
        // 각 요청마다 새로운 프로세스/스레드 생성
        const process = new Process();
        process.run(() => {
            // 요청 처리
            this.processRequest(request);
        });
    }
}
```

**이벤트 기반 (Nginx 방식)**
```javascript
// 이벤트 기반 (Nginx 방식)
class EventDrivenServer {
    constructor() {
        this.eventLoop = new EventLoop();
    }
    
    handleRequest(request) {
        // 이벤트 큐에 추가
        this.eventLoop.addEvent(() => {
            this.processRequest(request);
        });
    }
    
    // 이벤트 루프
    runEventLoop() {
        while (true) {
            const event = this.eventLoop.getNextEvent();
            if (event) {
                event.execute();
            }
        }
    }
}
```

### 3. 리버스 프록시 (Reverse Proxy)
클라이언트와 백엔드 서버 사이에서 중개자 역할을 합니다.

```javascript
// 리버스 프록시 예시
class ReverseProxy {
    constructor() {
        this.backendServers = [
            'http://server1:3000',
            'http://server2:3000',
            'http://server3:3000'
        ];
        this.currentServer = 0;
    }
    
    // 요청을 백엔드 서버로 전달
    async proxyRequest(request) {
        // 로드 밸런싱 (라운드 로빈)
        const backendServer = this.backendServers[this.currentServer];
        this.currentServer = (this.currentServer + 1) % this.backendServers.length;
        
        // 백엔드 서버로 요청 전달
        const response = await fetch(backendServer + request.url, {
            method: request.method,
            headers: request.headers,
            body: request.body
        });
        
        return response;
    }
}
```

### 4. 로드 밸런싱 (Load Balancing)
여러 서버에 요청을 분산시키는 기술입니다.

```javascript
// 로드 밸런싱 알고리즘들
class LoadBalancer {
    constructor(servers) {
        this.servers = servers;
        this.currentIndex = 0;
        this.serverLoads = new Map();
        servers.forEach(server => this.serverLoads.set(server, 0));
    }
    
    // 라운드 로빈 방식
    roundRobin() {
        const server = this.servers[this.currentIndex];
        this.currentIndex = (this.currentIndex + 1) % this.servers.length;
        return server;
    }
    
    // 최소 연결 방식
    leastConnections() {
        let minLoad = Infinity;
        let selectedServer = null;
        
        for (const [server, load] of this.serverLoads) {
            if (load < minLoad) {
                minLoad = load;
                selectedServer = server;
            }
        }
        
        return selectedServer;
    }
    
    // IP 해시 방식
    ipHash(clientIP) {
        const hash = clientIP.split('.').reduce((acc, octet) => {
            return acc + parseInt(octet);
        }, 0);
        return this.servers[hash % this.servers.length];
    }
}
```

## 🏗️ Nginx의 구조

### 프로세스 구조
Nginx는 두 가지 프로세스로 구성됩니다:

1. **Master Process (마스터 프로세스)**
   - 설정 파일 관리
   - Worker Process 관리
   - 로그 관리

2. **Worker Process (워커 프로세스)**
   - 실제 요청 처리
   - CPU 코어 수만큼 생성

```javascript
// Nginx 프로세스 구조를 JavaScript로 표현
class NginxProcess {
    constructor() {
        this.masterProcess = new MasterProcess();
        this.workerProcesses = [];
        this.cpuCores = require('os').cpus().length;
    }
    
    start() {
        // 마스터 프로세스 시작
        this.masterProcess.start();
        
        // CPU 코어 수만큼 워커 프로세스 생성
        for (let i = 0; i < this.cpuCores; i++) {
            const worker = new WorkerProcess(i);
            this.workerProcesses.push(worker);
            worker.start();
        }
    }
}

class MasterProcess {
    start() {
        console.log('마스터 프로세스 시작');
        // 설정 파일 읽기, 워커 관리 등
    }
}

class WorkerProcess {
    constructor(id) {
        this.id = id;
        this.connections = new Map();
    }
    
    start() {
        console.log(`워커 프로세스 ${this.id} 시작`);
        // 실제 요청 처리
    }
}
```

## ⚡ Nginx vs Apache 비교

### 성능 비교

**Apache (전통적인 방식)**
```javascript
// Apache 방식 - 프로세스/스레드 기반
class ApacheServer {
    handleRequest(request) {
        // 각 요청마다 새로운 프로세스 생성
        const process = new Process();
        process.run(() => {
            // 요청 처리
            this.processRequest(request);
        });
    }
}

// 문제점: 동시 접속자가 많으면 메모리 부족
// 1000명 동시 접속 = 1000개 프로세스 = 메모리 부족
```

**Nginx (이벤트 기반)**
```javascript
// Nginx 방식 - 이벤트 기반
class NginxServer {
    constructor() {
        this.eventLoop = new EventLoop();
        this.connections = new Map();
    }
    
    handleRequest(request) {
        // 이벤트 큐에 추가 (메모리 사용량 적음)
        this.eventLoop.addEvent(() => {
            this.processRequest(request);
        });
    }
}

// 장점: 동시 접속자가 많아도 메모리 사용량 적음
// 1000명 동시 접속 = 1개 프로세스 = 메모리 효율적
```

### 사용 시나리오

**Apache가 좋은 경우:**
- .htaccess 파일 사용 필요
- 다양한 모듈이 필요한 경우
- PHP 애플리케이션
- 공유 호스팅 환경

**Nginx가 좋은 경우:**
- 높은 동시 접속자 수
- 정적 파일 서빙
- 리버스 프록시
- 마이크로서비스 아키텍처

## ⚙️ Nginx 설정 이해하기

### 기본 설정 구조
```nginx
# nginx.conf 파일 구조
worker_processes auto;        # 워커 프로세스 수 (CPU 코어 수)
worker_connections 1024;      # 워커당 최대 연결 수

events {
    use epoll;                # 이벤트 처리 방식
    multi_accept on;          # 여러 연결 동시 수락
}

http {
    include mime.types;       # 파일 타입 정의
    
    # 업스트림 서버 그룹 (로드 밸런싱)
    upstream backend {
        server 192.168.1.10:3000;
        server 192.168.1.11:3000;
        server 192.168.1.12:3000;
    }
    
    # 서버 설정
    server {
        listen 80;            # 포트
        server_name example.com;  # 도메인
        
        # 정적 파일 처리
        location /static/ {
            root /var/www/html;   # 파일 경로
            expires 30d;          # 캐시 기간
        }
        
        # 리버스 프록시
        location / {
            proxy_pass http://backend;  # 백엔드로 전달
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

### JavaScript로 이해하는 설정
```javascript
// Nginx 설정을 JavaScript 객체로 표현
const nginxConfig = {
    workerProcesses: 'auto',  // CPU 코어 수만큼
    workerConnections: 1024,  // 워커당 최대 연결 수
    
    events: {
        use: 'epoll',         // 이벤트 처리 방식
        multiAccept: true     // 여러 연결 동시 수락
    },
    
    http: {
        upstream: {
            backend: [
                '192.168.1.10:3000',
                '192.168.1.11:3000',
                '192.168.1.12:3000'
            ]
        },
        
        server: {
            port: 80,
            domain: 'example.com',
            
            locations: {
                '/static/': {
                    root: '/var/www/html',
                    expires: '30d'
                },
                '/': {
                    proxyPass: 'http://backend'
                }
            }
        }
    }
};
```

## 🔧 실제 사용 예시

### 1. 정적 파일 서빙
```javascript
// 정적 파일 서빙 예시
class StaticFileServer {
    constructor() {
        this.staticFiles = new Map();
        this.loadStaticFiles();
    }
    
    loadStaticFiles() {
        // 정적 파일들을 메모리에 로드
        this.staticFiles.set('/index.html', '<html>...</html>');
        this.staticFiles.set('/style.css', 'body { ... }');
        this.staticFiles.set('/script.js', 'console.log("Hello");');
    }
    
    serveFile(path) {
        if (this.staticFiles.has(path)) {
            return {
                content: this.staticFiles.get(path),
                type: this.getContentType(path),
                cached: true
            };
        }
        return null;
    }
    
    getContentType(path) {
        const extensions = {
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.jpg': 'image/jpeg',
            '.png': 'image/png'
        };
        
        const ext = path.substring(path.lastIndexOf('.'));
        return extensions[ext] || 'text/plain';
    }
}
```

### 2. 리버스 프록시
```javascript
// 리버스 프록시 예시
class ReverseProxy {
    constructor() {
        this.backendServers = [
            'http://app1:3000',
            'http://app2:3000',
            'http://app3:3000'
        ];
        this.loadBalancer = new LoadBalancer(this.backendServers);
    }
    
    async handleRequest(request) {
        // 1. 정적 파일인지 확인
        if (this.isStaticFile(request.url)) {
            return await this.serveStaticFile(request.url);
        }
        
        // 2. 백엔드 서버로 전달
        const backendServer = this.loadBalancer.roundRobin();
        return await this.proxyToBackend(backendServer, request);
    }
    
    async proxyToBackend(backendServer, request) {
        const url = `${backendServer}${request.url}`;
        
        const response = await fetch(url, {
            method: request.method,
            headers: {
                ...request.headers,
                'X-Forwarded-For': request.ip,
                'X-Real-IP': request.ip
            },
            body: request.body
        });
        
        return response;
    }
}
```

### 3. 캐싱
```javascript
// 캐싱 예시
class CacheManager {
    constructor() {
        this.cache = new Map();
        this.maxSize = 1000;  // 최대 캐시 항목 수
    }
    
    get(key) {
        const item = this.cache.get(key);
        if (item && !this.isExpired(item)) {
            return item.value;
        }
        
        if (item) {
            this.cache.delete(key);  // 만료된 항목 제거
        }
        
        return null;
    }
    
    set(key, value, ttl = 3600000) {  // 기본 1시간
        // 캐시 크기 제한
        if (this.cache.size >= this.maxSize) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }
        
        this.cache.set(key, {
            value: value,
            timestamp: Date.now(),
            ttl: ttl
        });
    }
    
    isExpired(item) {
        return Date.now() - item.timestamp > item.ttl;
    }
}
```

## 📊 성능 최적화 팁

### 1. 정적 파일 최적화
```javascript
// 정적 파일 최적화 예시
class StaticFileOptimizer {
    constructor() {
        this.cache = new CacheManager();
        this.compression = new Compression();
    }
    
    async serveOptimizedFile(path) {
        // 1. 캐시 확인
        const cached = this.cache.get(path);
        if (cached) {
            return cached;
        }
        
        // 2. 파일 읽기
        const file = await this.readFile(path);
        
        // 3. 압축
        const compressed = await this.compression.compress(file);
        
        // 4. 캐시에 저장
        this.cache.set(path, compressed);
        
        return compressed;
    }
}
```

### 2. 연결 최적화
```javascript
// 연결 최적화 예시
class ConnectionOptimizer {
    constructor() {
        this.keepAliveTimeout = 65000;  // 65초
        this.maxKeepAliveRequests = 100;
    }
    
    optimizeConnection(connection) {
        // Keep-Alive 설정
        connection.setKeepAlive(true, this.keepAliveTimeout);
        
        // 연결 재사용
        connection.on('close', () => {
            this.reuseConnection(connection);
        });
    }
    
    reuseConnection(connection) {
        // 연결을 풀에 반환하여 재사용
        if (connection.isHealthy()) {
            this.connectionPool.push(connection);
        }
    }
}
```

## 🔒 보안 설정

### 1. SSL/TLS 설정
```javascript
// SSL/TLS 설정 예시
class SSLManager {
    constructor() {
        this.certificates = new Map();
    }
    
    setupSSL(domain, certPath, keyPath) {
        const certificate = {
            cert: this.readCertificate(certPath),
            key: this.readPrivateKey(keyPath),
            secureProtocol: 'TLSv1.2'
        };
        
        this.certificates.set(domain, certificate);
    }
    
    getCertificate(domain) {
        return this.certificates.get(domain);
    }
}
```

### 2. 접근 제어
```javascript
// 접근 제어 예시
class AccessControl {
    constructor() {
        this.allowedIPs = new Set();
        this.blockedIPs = new Set();
    }
    
    isAllowed(clientIP) {
        // 차단된 IP 확인
        if (this.blockedIPs.has(clientIP)) {
            return false;
        }
        
        // 허용된 IP 확인
        if (this.allowedIPs.size > 0) {
            return this.allowedIPs.has(clientIP);
        }
        
        return true;  // 기본적으로 허용
    }
    
    blockIP(ip) {
        this.blockedIPs.add(ip);
    }
    
    allowIP(ip) {
        this.allowedIPs.add(ip);
    }
}
```

## 📝 마무리

Nginx는 현대 웹 인프라에서 필수적인 요소입니다. 이벤트 기반 아키텍처로 높은 성능을 제공하며, 다양한 기능을 통해 웹 서비스를 효율적으로 운영할 수 있게 해줍니다.

주요 포인트:
- **이벤트 기반**: 비동기 처리로 높은 동시성
- **리버스 프록시**: 백엔드 서버 보호 및 로드 밸런싱
- **캐싱**: 성능 향상을 위한 정적 파일 캐싱
- **보안**: SSL/TLS 및 접근 제어

이해하기 어려운 부분이 있다면 실제로 작은 프로젝트를 만들어서 Nginx를 직접 설정해보는 것을 추천합니다. 실습을 통해 더 깊이 이해할 수 있을 것입니다.

---

**참고 자료:**
- https://www.nginx.com/blog/nginx-vs-apache-our-view/
- https://www.digitalocean.com/community/tutorials/apache-vs-nginx-practical-considerations
- https://www.nginx.com/resources/wiki/
