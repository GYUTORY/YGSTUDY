---
title: 생성 패턴 (Creational Patterns)
tags: [application-architecture, design-pattern, creational-patterns, singleton, factory, builder, prototype, nodejs, backend]
updated: 2026-08-07
---

# 생성 패턴 (Creational Patterns)

## 배경

### 생성 패턴이란?

생성 패턴은 **객체 생성의 복잡성을 관리하고 코드의 유지보수성을 높이는 실용적인 설계 기법**입니다. 

Node.js 백엔드 개발에서 자주 마주치는 문제들:
- 데이터베이스 연결 관리
- API 클라이언트 생성
- 설정 객체 구성
- 복잡한 비즈니스 객체 생성

이 상황에서 생성 패턴을 적절히 활용하면 코드의 품질과 확장성을 크게 향상시킬 수 있습니다.

### 왜 생성 패턴이 필요한가?

#### 1. 객체 생성의 복잡성 문제
```javascript
// 나쁜 예: 복잡한 객체 생성
const user = new User(
    "홍길동",           // 이름
    "hong@example.com", // 이메일
    "010-1234-5678",    // 전화번호
    "서울시 강남구",     // 주소
    "개발자",           // 직업
    true,               // 이메일 수신 동의
    false,              // SMS 수신 동의
    "2023-01-01",       // 가입일
    "ACTIVE"            // 상태
);
```

**문제점:**
- 매개변수 순서를 기억하기 어려움
- 선택적 필드 처리 복잡
- 테스트 시 mock 객체 생성 어려움
- 코드 리뷰 시 실수 발견 어려움

#### 2. 의존성 결합 문제
```javascript
// 나쁜 예: 구체 클래스에 직접 의존
class OrderService {
    async processOrder() {
        const dbConnection = new MySQLConnection(); // MySQL에 강하게 결합
        const logger = new FileLogger();            // 파일 로깅에 강하게 결합
        const emailService = new SendGridService(); // SendGrid에 강하게 결합
        
        // 비즈니스 로직...
    }
}
```

**문제점:**
- 데이터베이스 변경 시 코드 수정 필요
- 로깅 시스템 교체 시 전체 코드 수정
- 테스트 시 실제 외부 서비스 의존
- 환경별 설정 변경 어려움

#### 3. 런타임 유연성 부족
```javascript
// 나쁜 예: 하드코딩된 객체 생성
function createPaymentProcessor(type) {
    if (type === "card") {
        return new CardPaymentProcessor();
    } else if (type === "bank") {
        return new BankPaymentProcessor();
    } else if (type === "kakao") {
        return new KakaoPayProcessor();
    }
    // 새로운 결제 방식 추가 시마다 코드 수정 필요
    throw new Error('Unsupported payment type');
}
```

**문제점:**
- 새로운 결제 방식 추가 시 코드 수정 필요
- 조건문이 복잡해질수록 가독성 저하
- 각 결제 방식별 설정이 하드코딩됨
- 테스트 케이스 작성 어려움

### 생성 패턴이 중요한 이유

#### 1. **의존성 주입과 테스트 용이성**
```javascript
// 좋은 예: 의존성 주입을 통한 테스트 가능한 코드
class OrderService {
    constructor(dbConnection, logger, emailService) {
        this.db = dbConnection;
        this.logger = logger;
        this.email = emailService;
    }
    
    async processOrder() {
        // 비즈니스 로직...
    }
}
```

#### 2. **환경별 설정 관리**
```javascript
// 개발/스테이징/프로덕션 환경별 다른 객체 생성
const config = process.env.NODE_ENV === 'production' 
    ? new ProductionConfig() 
    : new DevelopmentConfig();
```

#### 3. **확장성과 유지보수성**
- 새로운 기능 추가 시 기존 코드 수정 최소화
- 플러그인 아키텍처 구현 가능
- 마이크로서비스 간 통신 객체 생성 표준화

---

## 패턴 목록

각 패턴의 상세 내용은 개별 파일을 참조하세요.

### 1. Singleton Pattern (싱글톤 패턴)

애플리케이션 전체에서 **단 하나의 인스턴스만 존재하도록 보장**하는 패턴. 데이터베이스 연결 풀, Redis 클라이언트, 로깅 시스템, 전역 설정 관리에 활용됩니다.

→ 상세: [[Singleton_Pattern]]

### 2. Factory Method Pattern (팩토리 메서드 패턴)

객체 생성 인터페이스를 정의하되 **어떤 클래스를 생성할지는 서브클래스가 결정**하는 패턴. 결제 모듈, 알림 서비스, 데이터베이스 드라이버처럼 런타임에 타입이 결정되는 경우에 사용합니다.

→ 상세: [[Factory Method]]

### 3. Abstract Factory Pattern (추상 팩토리 패턴)

**관련 객체들의 집합을 일관성 있게 생성**하는 패턴. 환경별 인프라 조합(DB + Cache + Logger), 결제 시스템 조합처럼 연관된 여러 객체를 함께 생성해야 할 때 사용합니다.

→ 상세: [[Abstract_Factory_Pattern]]

### 4. Builder Pattern (빌더 패턴)

**복잡한 객체의 생성 과정을 단계별로 분리**하여 가독성과 유연성을 높이는 패턴. HTTP 요청 구성, 동적 SQL 쿼리 생성, 이메일 메시지 구성처럼 선택적 매개변수가 많은 객체 생성에 사용합니다.

→ 상세: [[Builder_Pattern]]

### 5. Prototype Pattern (프로토타입 패턴)

**기존 객체를 복제하여 새로운 객체를 생성**하는 패턴. 복잡한 설정 객체를 기반으로 변형된 버전을 만들거나, 생성 비용이 큰 객체를 재사용할 때 사용합니다.

→ 상세: [[Prototype_Pattern]]

---

## 패턴 선택 기준

### 언제 어떤 패턴을 쓰는가?

| 상황 | 권장 패턴 | 이유 | 예시 |
|------|-----------|------|------|
| 전역적으로 하나만 존재해야 함 | Singleton | 단일 인스턴스 보장 | Config, Logger, Cache |
| 런타임에 타입이 결정됨 | Factory Method | 서브클래스가 타입 결정 | Payment, SMS, Email |
| 관련 객체들을 함께 생성해야 함 | Abstract Factory | 인프라 조합의 일관성 | DB + Cache + Logger |
| 매개변수가 5개 이상, 선택적 필드 많음 | Builder | 가독성과 유연성 | HTTP Request, DB Query |
| 기존 객체 기반으로 변형 생성 | Prototype | 생성 비용 절감 | 설정 객체 복제 |
| 단순한 객체 | 직접 생성 | 오버엔지니어링 방지 | `{ id: 1, name: '...' }` |

### 패턴 선택 의사결정 트리

```
객체 생성이 필요한가?
├─ 전역적으로 하나만 존재해야 하는가?
│  ├─ 예 → Singleton Pattern
│  └─ 아니오 → 다음 질문
├─ 런타임에 타입이 결정되는가?
│  ├─ 예 → Factory Method Pattern
│  └─ 아니오 → 다음 질문
├─ 관련된 여러 객체를 함께 생성해야 하는가?
│  ├─ 예 → Abstract Factory Pattern
│  └─ 아니오 → 다음 질문
├─ 매개변수가 5개 이상이거나 선택적 필드가 많은가?
│  ├─ 예 → Builder Pattern
│  └─ 아니오 → 다음 질문
└─ 기존 객체를 복제해서 생성하는가?
   ├─ 예 → Prototype Pattern
   └─ 아니오 → 직접 생성
```

### 패턴 간 비교

| 패턴 | 복잡도 | 메모리 | 테스트 용이성 | 확장성 | 성능 |
|------|--------|--------|---------------|--------|------|
| Singleton | 낮음 | 낮음 | 어려움 | 낮음 | 높음 |
| Factory Method | 중간 | 중간 | 쉬움 | 높음 | 중간 |
| Abstract Factory | 높음 | 높음 | 어려움 | 높음 | 낮음 |
| Builder | 중간 | 중간 | 쉬움 | 중간 | 중간 |
| Prototype | 낮음 | 낮음 | 쉬움 | 중간 | 높음 |

---

## 핵심 원칙

1. **단순함 우선**: 복잡한 패턴보다는 단순한 해결책을 먼저 고려
2. **실용성 중심**: 프로젝트에서의 유용성에 집중
3. **성능 고려**: 패턴 적용 시 성능 영향도 함께 고려
4. **테스트 가능**: 패턴이 테스트를 어렵게 만들지 않도록 주의
5. **유지보수성**: 장기적으로 유지보수하기 쉬운 코드 작성
