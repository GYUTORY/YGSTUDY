---
title: DNS (Domain Name System)
tags: [network, domain, dns, name-resolution, internet-infrastructure]
updated: 2024-12-19
---

# DNS (Domain Name System)

## 배경

### DNS의 기본 개념
DNS는 인터넷의 전화번호부와 같은 역할을 하는 분산형 데이터베이스 시스템입니다. 사람이 이해하기 쉬운 도메인 이름(예: google.com)을 컴퓨터가 이해할 수 있는 IP 주소(예: 172.217.31.46)로 변환하는 역할을 합니다.

### DNS의 역사
1983년 Paul Mockapetris가 개발한 이래로 인터넷의 핵심 인프라로 작동해왔습니다. 초기에는 단일 파일로 관리되었지만, 인터넷의 급속한 성장으로 인해 분산형 시스템으로 발전했습니다.

### DNS의 필요성
- **사용자 편의성**: IP 주소 대신 기억하기 쉬운 도메인 이름 사용
- **유연성**: IP 주소 변경 시 도메인 이름은 그대로 유지
- **확장성**: 분산형 구조로 대용량 트래픽 처리 가능

## 핵심

### DNS의 작동 원리

#### 1. DNS 쿼리 과정
1. 사용자가 브라우저에 도메인 이름을 입력합니다 (예: www.example.com)
2. 브라우저는 먼저 로컬 DNS 캐시를 확인합니다
3. 캐시에 없으면, 운영체제에 설정된 DNS 서버(보통 ISP의 DNS 서버)에 쿼리를 보냅니다
4. DNS 서버는 다음과 같은 순서로 IP 주소를 찾습니다:
   - Root DNS 서버 (.com, .org 등의 최상위 도메인 정보)
   - TLD (Top Level Domain) 서버
   - Authoritative DNS 서버 (실제 도메인 정보를 관리하는 서버)
5. 찾은 IP 주소를 클라이언트에게 반환합니다
6. 클라이언트는 해당 IP 주소로 웹 서버에 접속합니다

#### 2. DNS 계층 구조
```
Root DNS Servers (.)
├── .com TLD Servers
│   ├── example.com Authoritative Servers
│   └── google.com Authoritative Servers
├── .org TLD Servers
└── .net TLD Servers
```

### DNS 레코드 타입

#### 1. A 레코드 (Address Record)
도메인 이름을 IPv4 주소로 매핑하는 가장 기본적인 레코드 타입입니다.

```dns
example.com.    IN    A    93.184.216.34
```

**장점:**
- 직접적인 IP 주소 매핑으로 빠른 응답이 가능합니다
- DNS 쿼리 횟수가 적어 성능이 좋습니다

**단점:**
- IP 주소가 변경될 때마다 DNS 레코드를 수정해야 합니다
- 서버 이전이나 IP 변경이 빈번한 환경에서는 관리가 어려울 수 있습니다

#### 2. CNAME (Canonical Name)
도메인 이름을 다른 도메인 이름으로 매핑하는 레코드 타입입니다.

```dns
www.example.com.    IN    CNAME    example.com.
```

**장점:**
- IP 주소 변경 시 원본 도메인만 수정하면 됩니다
- 여러 서브도메인이 하나의 IP를 가리킬 때 유용합니다
- CDN이나 클라우드 서비스 연동 시 유연하게 대응 가능합니다

**단점:**
- 최종 IP 주소를 얻기 위해 추가 DNS 쿼리가 필요합니다
- 성능이 A 레코드보다 약간 느릴 수 있습니다

#### 3. AAAA 레코드
IPv6 주소를 매핑하는 레코드입니다.

```dns
example.com.    IN    AAAA    2606:2800:220:1:248:1893:25c8:1946
```

#### 4. MX 레코드 (Mail Exchange)
이메일 서버의 주소를 지정합니다.

```dns
example.com.    IN    MX    10    mail.example.com.
```

#### 5. NS 레코드 (Name Server)
도메인의 DNS 서버를 지정합니다.

```dns
example.com.    IN    NS    ns1.example.com.
```

#### 6. TXT 레코드
도메인에 대한 텍스트 정보를 저장합니다. 주로 SPF, DKIM 등의 이메일 인증에 사용됩니다.

```dns
example.com.    IN    TXT    "v=spf1 mx ~all"
```

## 예시

### DNS 쿼리 시뮬레이션

#### 1. 재귀적 쿼리 (Recursive Query)
```javascript
// DNS 쿼리 과정을 JavaScript로 시뮬레이션
class DNSQuery {
    constructor() {
        this.cache = new Map();
        this.rootServers = ['a.root-servers.net', 'b.root-servers.net'];
        this.tldServers = {
            'com': ['a.gtld-servers.net', 'b.gtld-servers.net'],
            'org': ['a0.org.afilias-nst.info', 'a2.org.afilias-nst.info']
        };
    }

    async resolve(domain) {
        // 1. 캐시 확인
        if (this.cache.has(domain)) {
            console.log(`캐시에서 ${domain} 찾음`);
            return this.cache.get(domain);
        }

        // 2. 도메인 파싱
        const parts = domain.split('.');
        const tld = parts[parts.length - 1];
        const subdomain = parts.slice(0, -1).join('.');

        // 3. TLD 서버 쿼리
        console.log(`${tld} TLD 서버에 쿼리 중...`);
        const tldServer = this.tldServers[tld][0];

        // 4. Authoritative 서버 쿼리
        console.log(`${domain}의 Authoritative 서버에 쿼리 중...`);
        const ip = await this.queryAuthoritative(domain);

        // 5. 캐시에 저장
        this.cache.set(domain, ip);
        return ip;
    }

    async queryAuthoritative(domain) {
        // 실제로는 네트워크 쿼리를 수행
        // 여기서는 시뮬레이션을 위해 가상의 IP 반환
        const mockIPs = {
            'example.com': '93.184.216.34',
            'google.com': '172.217.31.46',
            'github.com': '140.82.113.4'
        };
        
        return mockIPs[domain] || '192.168.1.1';
    }
}

// 사용 예시
const dns = new DNSQuery();
dns.resolve('example.com').then(ip => {
    console.log(`example.com의 IP 주소: ${ip}`);
});
```

#### 2. DNS 캐싱 구현
```javascript
class DNSCache {
    constructor() {
        this.cache = new Map();
        this.ttl = 300; // 5분
    }

    set(domain, ip, ttl = this.ttl) {
        const expiry = Date.now() + (ttl * 1000);
        this.cache.set(domain, {
            ip: ip,
            expiry: expiry
        });
    }

    get(domain) {
        const record = this.cache.get(domain);
        if (!record) return null;

        if (Date.now() > record.expiry) {
            this.cache.delete(domain);
            return null;
        }

        return record.ip;
    }

    clear() {
        this.cache.clear();
    }
}
```

### DNS 설정 예제

#### 1. 웹 서버 설정
```dns
; 웹 서버 DNS 설정
example.com.        IN    A        192.168.1.100
www.example.com.    IN    CNAME    example.com.
api.example.com.    IN    A        192.168.1.101
```

#### 2. 이메일 서버 설정
```dns
; 이메일 서버 DNS 설정
example.com.        IN    MX    10    mail.example.com.
mail.example.com.   IN    A        192.168.1.102
example.com.        IN    TXT    "v=spf1 mx ~all"
```

#### 3. CDN 연동 설정
```dns
; CDN 연동 DNS 설정
example.com.        IN    A        192.168.1.100
www.example.com.    IN    CNAME    example.com.
cdn.example.com.    IN    CNAME    cdn.cloudflare.com.
```

## 운영 팁

### DNS 성능 최적화

#### 1. TTL 설정 최적화
```dns
; 자주 변경되지 않는 레코드
example.com.        IN    A        192.168.1.100    ; TTL: 3600 (1시간)

; 자주 변경되는 레코드
dev.example.com.    IN    A        192.168.1.101    ; TTL: 300 (5분)
```

#### 2. DNS 캐싱 전략
```javascript
// DNS 캐싱 최적화
class OptimizedDNSCache {
    constructor() {
        this.cache = new Map();
        this.stats = {
            hits: 0,
            misses: 0
        };
    }

    get(domain) {
        const record = this.cache.get(domain);
        if (record && Date.now() < record.expiry) {
            this.stats.hits++;
            return record.ip;
        }
        
        this.stats.misses++;
        return null;
    }

    getStats() {
        const total = this.stats.hits + this.stats.misses;
        const hitRate = total > 0 ? (this.stats.hits / total * 100).toFixed(2) : 0;
        return {
            hits: this.stats.hits,
            misses: this.stats.misses,
            hitRate: `${hitRate}%`
        };
    }
}
```

### DNS 보안 설정

#### 1. DNSSEC 설정
```dns
; DNSSEC 서명된 레코드
example.com.        IN    A        192.168.1.100
example.com.        IN    RRSIG    A 8 2 86400 20231201000000 20231101000000 12345 example.com. ...
```

#### 2. DNS 오버 HTTPS (DoH) 구현
```javascript
// DNS over HTTPS 클라이언트
class DoHClient {
    constructor(provider = 'https://cloudflare-dns.com/dns-query') {
        this.provider = provider;
    }

    async query(domain, type = 'A') {
        const url = `${this.provider}?name=${domain}&type=${type}`;
        
        try {
            const response = await fetch(url, {
                headers: {
                    'Accept': 'application/dns-json'
                }
            });
            
            const data = await response.json();
            return data.Answer?.[0]?.data || null;
        } catch (error) {
            console.error('DoH 쿼리 실패:', error);
            return null;
        }
    }
}
```

### DNS 모니터링

#### 1. DNS 응답 시간 모니터링
```javascript
class DNSMonitor {
    constructor() {
        this.metrics = [];
    }

    async measureResponseTime(domain) {
        const start = Date.now();
        
        try {
            const ip = await this.resolve(domain);
            const responseTime = Date.now() - start;
            
            this.metrics.push({
                domain: domain,
                responseTime: responseTime,
                timestamp: new Date(),
                success: !!ip
            });
            
            return { ip, responseTime };
        } catch (error) {
            const responseTime = Date.now() - start;
            this.metrics.push({
                domain: domain,
                responseTime: responseTime,
                timestamp: new Date(),
                success: false,
                error: error.message
            });
            
            throw error;
        }
    }

    getAverageResponseTime() {
        const successful = this.metrics.filter(m => m.success);
        if (successful.length === 0) return 0;
        
        const total = successful.reduce((sum, m) => sum + m.responseTime, 0);
        return total / successful.length;
    }
}
```

## 참고

### DNS 서버 종류

| 서버 타입 | 역할 | 예시 |
|-----------|------|------|
| **Root DNS Server** | 최상위 도메인 정보 제공 | a.root-servers.net |
| **TLD DNS Server** | 최상위 도메인별 정보 제공 | a.gtld-servers.net |
| **Authoritative DNS Server** | 실제 도메인 정보 관리 | ns1.example.com |
| **Recursive DNS Server** | 클라이언트 요청 처리 | 8.8.8.8 (Google) |

### DNS 보안 위협

#### 1. DNS 캐시 포이즈닝
- 공격자가 DNS 캐시에 잘못된 정보를 주입
- 방어: DNSSEC 사용, DNS 오버 HTTPS/TLS 사용

#### 2. DNS 증폭 공격
- DNS 응답을 이용한 DDoS 공격
- 방어: DNS 응답 크기 제한, Rate Limiting

#### 3. DNS 터널링
- DNS 프로토콜을 통한 데이터 유출
- 방어: DNS 트래픽 모니터링, 패턴 분석

### DNS 도구

#### 1. 명령줄 도구
```bash
# nslookup
nslookup example.com

# dig (더 상세한 정보)
dig example.com A

# host
host example.com
```

#### 2. 온라인 도구
- **MXToolbox**: DNS 레코드 확인
- **DNSViz**: DNSSEC 검증
- **WhatsMyDNS**: 글로벌 DNS 전파 확인

### 결론
DNS는 인터넷의 핵심 인프라로, 도메인 이름과 IP 주소 간의 변환을 담당합니다.
적절한 DNS 설정과 보안 조치를 통해 안정적이고 빠른 서비스를 제공할 수 있습니다.
DNS 캐싱, TTL 최적화, 보안 설정 등을 통해 성능과 안정성을 향상시킬 수 있습니다.










