---
title: HTTP와 HTTP 2.0
tags: [network, 7-layer, application-layer, http, http2, multiplexing, server-push]
updated: 2025-09-20
---

# HTTP와 HTTP 2.0


## 개요

HTTP 2.0은 HTTP 1.1의 성능 한계를 극복하기 위해 개발된 프로토콜입니다. 가장 큰 개선점은 **속도 향상**으로, 헤더 압축, 멀티플렉싱, 서버 푸시 등의 기술을 통해 웹 성능을 크게 향상시켰습니다.

## 주요 개선사항

### 1. Multiplexed Streams (멀티플렉싱)

**HTTP 1.0의 문제점**
- 매 요청마다 새로운 TCP 연결을 생성하여 성능 저하 발생
- 연결 설정 오버헤드가 크고 자원 낭비

**HTTP 1.1의 개선**
- Keep-Alive를 통한 연결 재사용으로 일부 문제 해결
- 하지만 여전히 순차적 요청 처리로 인한 지연 발생

**HTTP 2.0의 해결책**
- **단일 TCP 연결**로 여러 요청을 동시에 처리
- **Stream**을 통해 요청을 병렬로 처리
- 순서에 상관없이 응답을 받을 수 있어 대기 시간 단축

### HTTP/2 멀티플렉싱 구조

```mermaid
sequenceDiagram
    participant Client as 클라이언트<br/>(브라우저)
    participant Server as 웹 서버
    
    Note over Client,Server: HTTP/2 멀티플렉싱 통신 과정
    
    Client->>Server: 1. TCP 연결 수립<br/>🔗 단일 TCP 연결
    Server-->>Client: 2. 연결 확인
    
    par 병렬 스트림 처리
        Client->>Server: 3a. Stream 1: HTML 요청<br/>📄 GET /index.html<br/>🎯 우선순위: 높음
        Client->>Server: 3b. Stream 2: CSS 요청<br/>🎨 GET /style.css<br/>🎯 우선순위: 중간
        Client->>Server: 3c. Stream 3: JS 요청<br/>⚡ GET /script.js<br/>🎯 우선순위: 중간
        Client->>Server: 3d. Stream 4: 이미지 요청<br/>🖼️ GET /image.jpg<br/>🎯 우선순위: 낮음
    end
    
    par 병렬 응답 처리
        Server-->>Client: 4a. Stream 1: HTML 응답<br/>📄 200 OK<br/>📊 HTML 데이터
        Server-->>Client: 4b. Stream 2: CSS 응답<br/>🎨 200 OK<br/>📊 CSS 데이터
        Server-->>Client: 4c. Stream 3: JS 응답<br/>⚡ 200 OK<br/>📊 JavaScript 데이터
        Server-->>Client: 4d. Stream 4: 이미지 응답<br/>🖼️ 200 OK<br/>📊 이미지 데이터
    end
    
    Note over Client,Server: 🚀 순서에 상관없이 응답 수신<br/>⚡ 대기 시간 최소화
```

### HTTP/1.1 vs HTTP/2 성능 비교

```mermaid
graph TB
    subgraph "HTTP/1.1 (순차적 처리)"
        A1[요청 1: HTML] --> B1[응답 1: HTML]
        B1 --> A2[요청 2: CSS]
        A2 --> B2[응답 2: CSS]
        B2 --> A3[요청 3: JS]
        A3 --> B3[응답 3: JS]
        B3 --> A4[요청 4: 이미지]
        A4 --> B4[응답 4: 이미지]
        
        C1[총 시간: 4 × RTT]
        D1[Head-of-Line Blocking]
    end
    
    subgraph "HTTP/2 (병렬 처리)"
        E1[요청 1: HTML] --> F1[응답 1: HTML]
        E2[요청 2: CSS] --> F2[응답 2: CSS]
        E3[요청 3: JS] --> F3[응답 3: JS]
        E4[요청 4: 이미지] --> F4[응답 4: 이미지]
        
        G1[총 시간: 1 × RTT]
        H1[병렬 처리로 지연 최소화]
    end
    
    subgraph "성능 개선 효과"
        I1[로딩 시간: 15-30% 단축]
        I2[대역폭 절약: 20-40%]
        I3[연결 수: 1개로 통합]
        I4[모바일 환경: 큰 성능 향상]
    end
    
    style A1 fill:#ffcdd2
    style A2 fill:#ffcdd2
    style A3 fill:#ffcdd2
    style A4 fill:#ffcdd2
    
    style E1 fill:#c8e6c9
    style E2 fill:#c8e6c9
    style E3 fill:#c8e6c9
    style E4 fill:#c8e6c9
```

### 스트림 우선순위 처리

```mermaid
graph TD
    subgraph "HTTP/2 스트림 우선순위"
        A[HTML 문서<br/>우선순위: 높음] --> B[즉시 처리]
        C[CSS 파일<br/>우선순위: 중간] --> D[HTML 완료 후 처리]
        E[JavaScript<br/>우선순위: 중간] --> F[HTML 완료 후 처리]
        G[이미지들<br/>우선순위: 낮음] --> H[다른 리소스 완료 후 처리]
    end
    
    subgraph "처리 순서"
        I[1. HTML 먼저 로드] --> J[2. CSS 로드]
        J --> K[3. JavaScript 로드]
        K --> L[4. 이미지 로드]
    end
    
    subgraph "사용자 경험 개선"
        M[페이지 렌더링 시작]
        N[스타일 적용]
        O[인터랙션 활성화]
        P[이미지 표시]
    end
    
    B --> I
    D --> J
    F --> K
    H --> L
    
    I --> M
    J --> N
    K --> O
    L --> P
    
    style A fill:#ff9999
    style C fill:#ffcc99
    style E fill:#ffcc99
    style G fill:#ccffcc
```

### 2. Stream Prioritization (스트림 우선순위)

**개념**
- 각 요청에 **우선순위(Priority)**를 부여
- 중요한 리소스를 먼저 처리하여 사용자 경험 향상

**실제 예시**
```
요청 순서: HTML 문서 → CSS 파일 → JavaScript → 이미지들
우선순위: HTML(높음) → CSS(중간) → JS(중간) → 이미지(낮음)
```

**효과**
- HTML 문서를 먼저 받아 렌더링 시작
- 이미지가 먼저 와도 의미가 없으므로 효율적인 리소스 배분
- 페이지 로딩 시간 단축

### 3. Server Push (서버 푸시)

**기존 방식 (HTTP 1.1)**
1. 클라이언트가 HTML 요청
2. 서버가 HTML 응답
3. 클라이언트가 HTML 파싱 후 CSS, JS, 이미지 요청
4. 서버가 각각 응답

**HTTP 2.0 Server Push**
1. 클라이언트가 HTML 요청
2. 서버가 HTML과 함께 **예상되는 리소스들을 미리 푸시**
3. 클라이언트가 HTML 파싱할 때 이미 필요한 리소스들이 준비됨

**장점**
- **라운드트립 시간 단축**: 추가 요청 없이 리소스 확보
- **네트워크 지연 감소**: 예측적 리소스 전송
- **사용자 경험 향상**: 페이지 로딩 속도 개선

### 4. Header Compression (헤더 압축)

**HTTP 1.1의 문제점**
- 매 요청마다 동일한 헤더 정보를 반복 전송
- 쿠키, User-Agent 등 중복 데이터로 인한 대역폭 낭비

**HTTP 2.0의 해결책**
- **HPACK 압축 알고리즘** 사용
- 허프만 코딩 기반의 효율적인 압축
- 이전 요청과의 차이점만 전송하여 대역폭 절약

**압축 효과**
```
HTTP 1.1: 매 요청마다 전체 헤더 전송 (예: 800 bytes)
HTTP 2.0: 차이점만 전송 (예: 50 bytes)
절약률: 약 94% 대역폭 절약
```

## 성능 비교

| 항목 | HTTP 1.1 | HTTP 2.0 |
|------|----------|----------|
| 연결 방식 | Keep-Alive | Multiplexing |
| 요청 처리 | 순차적 | 병렬적 |
| 헤더 압축 | 없음 | HPACK |
| 서버 푸시 | 불가능 | 가능 |
| 우선순위 | 없음 | 있음 |

## 실제 성능 향상

- **페이지 로딩 시간**: 15-30% 단축
- **대역폭 사용량**: 20-40% 절약
- **동시 연결 수**: 1개로 통합 (연결 오버헤드 감소)
- **모바일 환경**: 특히 큰 성능 향상

## 마이그레이션 고려사항

### 장점
- **자동 적용**: 대부분의 현대 브라우저에서 지원
- **하위 호환성**: HTTP 1.1과 완전 호환
- **투명한 업그레이드**: 클라이언트/서버 설정만으로 적용 가능

### 주의사항
- **HTTPS 필수**: 대부분의 브라우저에서 HTTP 2.0을 HTTPS에서만 지원
- **서버 설정**: 웹서버(nginx, Apache) 설정 필요
- **모니터링**: 새로운 프로토콜에 대한 성능 모니터링 필요

## 결론

HTTP 2.0은 웹 성능을 획기적으로 개선한 프로토콜입니다. 멀티플렉싱, 서버 푸시, 헤더 압축 등의 기술을 통해 사용자 경험을 크게 향상시키며, 현대 웹 애플리케이션의 필수 기술로 자리잡았습니다.