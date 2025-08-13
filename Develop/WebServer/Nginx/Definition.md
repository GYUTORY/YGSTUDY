---
title: Nginx 이해하기
tags: [webserver, nginx, definition, web-server, reverse-proxy]
updated: 2024-12-19
---

# Nginx 이해하기

## 배경

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

### Nginx의 등장 배경
- Apache의 성능 한계 극복
- 높은 동시 접속 처리 능력
- 리버스 프록시 역할
- 로드 밸런싱 기능

## 핵심

### Nginx의 주요 특징
1. **고성능**: 이벤트 기반 비동기 처리
2. **낮은 메모리 사용량**: 효율적인 리소스 관리
3. **모듈화**: 필요한 기능만 선택적 사용
4. **확장성**: 마이크로서비스 아키텍처 지원

### 정적 컨텐츠 vs 동적 컨텐츠

**정적 컨텐츠 (Static Content)**
- 미리 만들어져 있는 파일
- 요청할 때마다 같은 내용
- 예: HTML, CSS, JavaScript, 이미지

**동적 컨텐츠 (Dynamic Content)**
- 실시간으로 만들어지는 내용
- 요청할 때마다 다른 내용
- 예: 사용자별 맞춤 페이지, 실시간 데이터

## 예시

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

### 정적 컨텐츠 처리 예시
```javascript
// 정적 컨텐츠 예시
const staticFiles = {
    '/index.html': '<html><body><h1>안녕하세요</h1></body></html>',
    '/style.css': 'body { font-family: Arial; }',
    '/script.js': 'console.log("Hello World");'
};

// 정적 파일 서빙 함수
function serveStaticFile(path) {
    return staticFiles[path] || '404 Not Found';
}
```

### 동적 컨텐츠 처리 예시
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

// 사용자별 맞춤 페이지 생성
function createUserPage(userId, userData) {
    return {
        html: generateDynamicContent(userId),
        data: userData,
        timestamp: new Date().toISOString()
    };
}
```

### Nginx 설정 예시
```javascript
// Nginx 설정을 JavaScript 객체로 표현
const nginxConfig = {
    server: {
        listen: 80,
        server_name: 'example.com',
        
        // 정적 파일 처리
        location: {
            '/static/': {
                root: '/var/www/html',
                expires: '1y',
                add_header: {
                    'Cache-Control': 'public, immutable'
                }
            },
            
            // 동적 컨텐츠 처리 (프록시)
            '/api/': {
                proxy_pass: 'http://backend:3000',
                proxy_set_header: {
                    'Host': '$host',
                    'X-Real-IP': '$remote_addr'
                }
            },
            
            // 로드 밸런싱
            '/app/': {
                proxy_pass: 'http://backend_servers',
                proxy_set_header: {
                    'Host': '$host',
                    'X-Real-IP': '$remote_addr'
                }
            }
        }
    }
};

// 로드 밸런서 설정
const upstreamConfig = {
    backend_servers: [
        { server: '192.168.1.10:3000', weight: 3 },
        { server: '192.168.1.11:3000', weight: 2 },
        { server: '192.168.1.12:3000', weight: 1 }
    ]
};
```

### Express.js와 Nginx 연동 예시
```javascript
const express = require('express');
const app = express();

// 정적 파일 서빙
app.use('/static', express.static('public'));

// API 라우트
app.get('/api/users', (req, res) => {
    res.json([
        { id: 1, name: '김철수' },
        { id: 2, name: '이영희' }
    ]);
});

// 동적 페이지 생성
app.get('/user/:id', (req, res) => {
    const userId = req.params.id;
    const userData = getUserData(userId);
    
    res.send(`
        <html>
            <head><title>사용자 정보</title></head>
            <body>
                <h1>사용자 ID: ${userId}</h1>
                <p>이름: ${userData.name}</p>
                <p>이메일: ${userData.email}</p>
            </body>
        </html>
    `);
});

app.listen(3000, () => {
    console.log('Express 서버가 3000번 포트에서 실행 중입니다');
});

function getUserData(userId) {
    // 실제로는 데이터베이스에서 조회
    return {
        name: '김철수',
        email: 'kim@example.com'
    };
}
```

### Nginx 리버스 프록시 설정
```javascript
// Nginx 리버스 프록시 설정 예시
const nginxReverseProxy = {
    upstream: {
        backend: [
            '127.0.0.1:3000',
            '127.0.0.1:3001',
            '127.0.0.1:3002'
        ]
    },
    
    server: {
        listen: 80,
        server_name: 'example.com',
        
        location: {
            '/': {
                proxy_pass: 'http://backend',
                proxy_set_header: {
                    'Host': '$host',
                    'X-Real-IP': '$remote_addr',
                    'X-Forwarded-For': '$proxy_add_x_forwarded_for',
                    'X-Forwarded-Proto': '$scheme'
                }
            }
        }
    }
};

// 헬스 체크 설정
const healthCheck = {
    interval: '30s',
    timeout: '3s',
    retries: 3,
    path: '/health'
};
```

## 운영 팁

### 성능 최적화
1. **정적 파일 캐싱**
   - 브라우저 캐시 설정
   - CDN 활용
   - 파일 압축

2. **로드 밸런싱**
   - 여러 서버에 요청 분산
   - 헬스 체크 설정
   - 세션 스티키 설정

3. **보안 설정**
   - HTTPS 강제 적용
   - 보안 헤더 설정
   - 요청 제한 설정

### 모니터링 및 로깅
```javascript
// Nginx 로그 분석 예시
const logAnalyzer = {
    // 접속 로그 분석
    analyzeAccessLog: (logData) => {
        const stats = {
            totalRequests: 0,
            uniqueIPs: new Set(),
            topPages: {},
            errorCount: 0
        };
        
        logData.forEach(line => {
            const parts = line.split(' ');
            stats.totalRequests++;
            stats.uniqueIPs.add(parts[0]);
            
            const statusCode = parseInt(parts[8]);
            if (statusCode >= 400) {
                stats.errorCount++;
            }
            
            const page = parts[6];
            stats.topPages[page] = (stats.topPages[page] || 0) + 1;
        });
        
        return stats;
    },
    
    // 실시간 모니터링
    realTimeMonitoring: () => {
        setInterval(() => {
            // CPU, 메모리, 연결 수 등 모니터링
            console.log('현재 연결 수:', getCurrentConnections());
            console.log('메모리 사용량:', getMemoryUsage());
        }, 5000);
    }
};
```

## 참고

### Nginx vs Apache 비교
| 특징 | Nginx | Apache |
|------|-------|--------|
| 성능 | 높음 (이벤트 기반) | 보통 (프로세스 기반) |
| 메모리 사용량 | 낮음 | 높음 |
| 동적 모듈 | 제한적 | 풍부함 |
| 설정 복잡도 | 간단 | 복잡 |

### 웹서버 아키텍처 패턴
1. **단일 서버**: 개발 환경
2. **로드 밸런서 + 웹서버**: 소규모 운영
3. **CDN + 로드 밸런서 + 웹서버**: 대규모 운영

### 결론
Nginx는 현대 웹 애플리케이션에서 필수적인 웹서버입니다.
고성능, 낮은 리소스 사용량, 그리고 다양한 기능을 제공하여
웹 서비스의 안정성과 성능을 크게 향상시킬 수 있습니다.
