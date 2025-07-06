# AWS Route 53

## 📖 개요

### Route 53이란?
AWS Route 53은 **인터넷의 주소록 역할을 하는 DNS(Domain Name System) 서비스**입니다.

> 💡 **쉽게 이해하기**: 인터넷에서 웹사이트를 찾을 때, 우리는 `www.google.com` 같은 주소를 사용합니다. 하지만 실제로는 컴퓨터가 이해하는 IP 주소(예: 142.250.191.78)로 변환해야 합니다. Route 53이 바로 이 변환 작업을 담당하는 서비스입니다.

### 이름의 유래
- **Route**: 경로를 찾아주는 역할
- **53**: DNS 프로토콜이 사용하는 포트 번호
- 즉, "53번 포트로 경로를 찾아주는 서비스"

---

## 🔧 핵심 개념 이해하기

### DNS (Domain Name System)란?
**인터넷의 전화번호부**라고 생각하면 됩니다.

```javascript
// 실제 동작 과정
const dnsLookup = {
  domain: "www.example.com",
  process: [
    "1. 사용자가 브라우저에 도메인 입력",
    "2. 로컬 DNS 서버에 'example.com의 IP가 뭐야?'라고 물어봄",
    "3. Route 53이 '192.168.1.1'이라고 답변",
    "4. 브라우저가 해당 IP로 연결"
  ]
};
```

### 도메인 구조 이해하기
```
www.example.com
│   │      │
│   │      └── TLD (Top Level Domain): .com, .net, .org
│   └────────── Second Level Domain: example
└────────────── Subdomain: www
```

---

## 🎯 Route 53의 주요 기능

### 1. 도메인 등록 및 관리
**인터넷에서 사용할 주소를 구매하고 관리**하는 기능

#### 도메인 등록 과정
```javascript
const domainRegistration = {
  step1: "도메인 이름 검색 (예: mywebsite.com)",
  step2: "가용성 확인 (이미 사용 중인지 체크)",
  step3: "등록 기간 선택 (1-10년)",
  step4: "개인정보 보호 설정",
  step5: "결제 및 등록 완료"
};
```

#### 도메인 가격 예시
```javascript
const domainPrices = {
  ".com": "$12.00/년",
  ".net": "$12.00/년", 
  ".org": "$15.00/년",
  ".io": "$40.00/년",
  ".co.kr": "$15.00/년"
};
```

### 2. DNS 레코드 관리
**도메인과 실제 서버를 연결**하는 설정

#### 주요 DNS 레코드 타입

| 레코드 타입 | 설명 | 예시 |
|------------|------|------|
| **A 레코드** | 도메인 → IPv4 주소 | `example.com → 192.168.1.1` |
| **AAAA 레코드** | 도메인 → IPv6 주소 | `example.com → 2001:db8::1` |
| **CNAME 레코드** | 도메인 → 다른 도메인 | `www.example.com → example.com` |
| **MX 레코드** | 메일 서버 지정 | `example.com → mail.example.com` |
| **TXT 레코드** | 도메인 검증 정보 | `example.com → "v=spf1 include:_spf.google.com ~all"` |

#### JavaScript로 DNS 레코드 표현
```javascript
const dnsRecords = {
  aRecord: {
    name: "example.com",
    type: "A",
    value: "192.168.1.1",
    ttl: 300 // 5분
  },
  
  cnameRecord: {
    name: "www.example.com", 
    type: "CNAME",
    value: "example.com",
    ttl: 300
  },
  
  mxRecord: {
    name: "example.com",
    type: "MX", 
    value: "10 mail.example.com",
    ttl: 3600 // 1시간
  }
};
```

### 3. 트래픽 라우팅
**사용자 요청을 적절한 서버로 분배**하는 기능

#### 라우팅 정책 종류

**1. 단순 라우팅 (Simple)**
```javascript
const simpleRouting = {
  description: "가장 기본적인 라우팅 방식",
  useCase: "단일 서버로 운영하는 웹사이트",
  example: {
    domain: "example.com",
    target: "192.168.1.1"
  }
};
```

**2. 가중치 라우팅 (Weighted)**
```javascript
const weightedRouting = {
  description: "트래픽을 비율에 따라 분배",
  useCase: "A/B 테스트, 점진적 배포",
  example: {
    "server1.example.com": { weight: 70, ip: "192.168.1.1" },
    "server2.example.com": { weight: 30, ip: "192.168.1.2" }
  }
};
```

**3. 지리적 라우팅 (Geolocation)**
```javascript
const geolocationRouting = {
  description: "사용자 위치에 따라 서버 선택",
  useCase: "지역별 콘텐츠 제공",
  example: {
    "US": { server: "us-server.example.com", ip: "192.168.1.1" },
    "Asia": { server: "asia-server.example.com", ip: "192.168.1.2" },
    "Europe": { server: "eu-server.example.com", ip: "192.168.1.3" }
  }
};
```

**4. 지연 시간 라우팅 (Latency-based)**
```javascript
const latencyRouting = {
  description: "가장 빠른 응답 시간을 제공하는 서버 선택",
  useCase: "글로벌 서비스 최적화",
  example: {
    "us-east-1": { latency: 50, server: "us-east.example.com" },
    "ap-northeast-1": { latency: 30, server: "ap-northeast.example.com" },
    "eu-west-1": { latency: 80, server: "eu-west.example.com" }
  }
};
```

### 4. 헬스 체크
**서버가 정상 작동하는지 모니터링**하는 기능

#### 헬스 체크 유형
```javascript
const healthCheckTypes = {
  http: {
    description: "웹 서버 상태 확인",
    method: "GET",
    path: "/health",
    expectedStatus: 200
  },
  
  https: {
    description: "보안 웹 서버 상태 확인", 
    method: "GET",
    path: "/health",
    expectedStatus: 200,
    ssl: true
  },
  
  tcp: {
    description: "포트 연결성 확인",
    port: 80,
    timeout: 5
  }
};
```

#### 헬스 체크 설정 예시
```javascript
const healthCheckConfig = {
  interval: 30, // 30초마다 체크
  timeout: 5,   // 5초 타임아웃
  failureThreshold: 3, // 3번 연속 실패 시 비정상 판정
  successThreshold: 3, // 3번 연속 성공 시 정상 판정
  path: "/health",
  port: 80
};
```

---

## 🛠️ 실제 설정 방법

### 1. 도메인 등록하기

#### AWS 콘솔에서 등록
1. AWS 콘솔 → Route 53 서비스 선택
2. **Domains** → **Register Domain** 클릭
3. 원하는 도메인 이름 입력 및 검색
4. TLD 선택 (.com, .net, .org 등)
5. 등록 기간 선택 (1-10년)
6. 연락처 정보 입력
7. 개인정보 보호 서비스 선택
8. 결제 및 등록 완료

### 2. 호스팅 영역 생성

#### Public Hosted Zone (공개 영역)
```javascript
const publicHostedZone = {
  name: "example.com",
  type: "Public",
  description: "인터넷에서 누구나 접근 가능한 도메인",
  useCase: "웹사이트, 이메일 서버"
};
```

#### Private Hosted Zone (비공개 영역)
```javascript
const privateHostedZone = {
  name: "internal.example.com", 
  type: "Private",
  description: "VPC 내부에서만 사용하는 도메인",
  useCase: "내부 서비스, 데이터베이스"
};
```

### 3. DNS 레코드 설정

#### A 레코드 설정
```javascript
const aRecord = {
  name: "www.example.com",
  type: "A",
  ttl: 300,
  value: "192.168.1.1"
};
```

#### CNAME 레코드 설정
```javascript
const cnameRecord = {
  name: "blog.example.com",
  type: "CNAME", 
  ttl: 300,
  value: "example.com"
};
```

#### MX 레코드 설정 (이메일)
```javascript
const mxRecord = {
  name: "example.com",
  type: "MX",
  ttl: 3600,
  records: [
    { priority: 10, value: "mail1.example.com" },
    { priority: 20, value: "mail2.example.com" }
  ]
};
```

---

## 💰 비용 구조

### 도메인 등록 비용
```javascript
const domainCosts = {
  ".com": 12.00,    // $12.00/년
  ".net": 12.00,    // $12.00/년  
  ".org": 15.00,    // $15.00/년
  ".io": 40.00,     // $40.00/년
  ".co.kr": 15.00   // $15.00/년
};
```

### 호스팅 영역 비용
```javascript
const hostedZoneCosts = {
  public: 0.50,  // $0.50/월
  private: 0.50  // $0.50/월
};
```

### 쿼리 비용
```javascript
const queryCosts = {
  standard: 0.40,        // $0.40/백만 쿼리
  latencyBased: 0.60,    // $0.60/백만 쿼리
  geolocation: 0.70      // $0.70/백만 쿼리
};
```

---

## 🔍 모니터링 및 로깅

### CloudWatch 통합
```javascript
const cloudWatchMetrics = {
  dnsQueries: "DNS 쿼리 수 모니터링",
  healthCheckStatus: "헬스 체크 상태 추적", 
  latency: "응답 시간 측정",
  errorRate: "오류율 모니터링"
};
```

### CloudTrail 통합
```javascript
const cloudTrailLogs = {
  apiCalls: "API 호출 기록",
  changes: "설정 변경 이력",
  security: "보안 감사 로그"
};
```

---

## 🚀 실제 사용 시나리오

### 1. 단일 웹사이트 운영
```javascript
const singleWebsite = {
  domain: "mywebsite.com",
  setup: [
    "1. 도메인 등록",
    "2. Public Hosted Zone 생성", 
    "3. A 레코드로 웹서버 연결",
    "4. CNAME으로 www 서브도메인 설정"
  ]
};
```

### 2. 다중 리전 배포
```javascript
const multiRegionDeployment = {
  regions: {
    "us-east-1": "192.168.1.1",
    "ap-northeast-1": "192.168.1.2", 
    "eu-west-1": "192.168.1.3"
  },
  routing: "Latency-based",
  healthCheck: "각 리전별 헬스 체크"
};
```

### 3. 장애 조치 구성
```javascript
const failoverSetup = {
  primary: {
    server: "primary.example.com",
    ip: "192.168.1.1",
    healthCheck: "/health"
  },
  secondary: {
    server: "secondary.example.com", 
    ip: "192.168.1.2",
    healthCheck: "/health"
  },
  routing: "Failover"
};
```

---

## 📚 추가 학습 포인트

### DNS 프로토콜 이해
- DNS 쿼리 타입 (A, AAAA, CNAME, MX 등)
- TTL (Time To Live) 개념
- DNS 캐싱 메커니즘

### AWS 서비스와의 통합
- CloudFront와의 연동
- ALB/NLB와의 통합
- ACM 인증서 자동 검증

### 보안 고려사항
- DNSSEC 활성화
- IAM 정책 설정
- 도메인 도용 방지

---

## 🔗 관련 AWS 서비스

- **CloudFront**: CDN 서비스와 연동
- **ALB/NLB**: 로드 밸런서와 통합
- **ACM**: SSL 인증서 자동 관리
- **CloudWatch**: 모니터링 및 알림
- **CloudTrail**: API 호출 로깅

