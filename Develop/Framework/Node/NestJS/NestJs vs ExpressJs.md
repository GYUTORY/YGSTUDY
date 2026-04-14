---
title: NestJS vs Express.js
tags: [framework, node, nestjs, nestjs-vs-expressjs, nodejs]
updated: 2026-04-14
---

# NestJS vs Express.js: 심층 비교 분석

## 소개

### Express.js
Express.js는 Node.js의 가장 인기 있는 웹 프레임워크 중 하나로, 2010년에 출시되었습니다. 미니멀리즘과 유연성을 강조하는 경량 프레임워크입니다.

### NestJS
NestJS는 2017년에 출시된 비교적 새로운 프레임워크로, Angular의 영향을 받아 TypeScript를 기반으로 구축되었습니다. 엔터프라이즈급 애플리케이션을 위한 구조화된 아키텍처를 제공합니다.

---

## 아키텍처 비교

### Express.js 아키텍처
- **미들웨어 기반**: 요청-응답 사이클을 처리하는 미들웨어 함수 체인
- **유연한 구조**: 개발자가 원하는 대로 구조화 가능
- **라우팅**: 간단한 라우팅 시스템
- **미니멀리즘**: 핵심 기능만 제공하고 나머지는 개발자가 구현

### NestJS 아키텍처
- **모듈 기반**: 기능별로 모듈화된 구조
- **의존성 주입**: DI 컨테이너가 인스턴스 생성과 주입을 관리
- **데코레이터**: TypeScript 데코레이터를 활용한 선언적 프로그래밍
- **계층 구조**: Controller, Service, Module 등 명확한 계층 분리

### 아키텍처 구조 다이어그램

Express.js는 app 객체 하나에 미들웨어와 라우터를 직접 등록하는 평면 구조다. 프로젝트가 커지면 파일을 어떻게 나눌지 전적으로 개발자 몫이 된다.

```mermaid
graph TB
    subgraph Express["Express.js 아키텍처"]
        EA[app.js] --> EM1[미들웨어 1]
        EA --> EM2[미들웨어 2]
        EA --> ER1[Router: /users]
        EA --> ER2[Router: /orders]
        ER1 --> EH1[핸들러 함수]
        ER2 --> EH2[핸들러 함수]
        EH1 --> EDB[(DB 직접 접근)]
        EH2 --> EDB
    end

    subgraph Nest["NestJS 아키텍처"]
        NM[AppModule] --> NM1[UsersModule]
        NM --> NM2[OrdersModule]
        NM1 --> NC1[UsersController]
        NM1 --> NS1[UsersService]
        NM2 --> NC2[OrdersController]
        NM2 --> NS2[OrdersService]
        NS1 --> NR1[UsersRepository]
        NS2 --> NR2[OrdersRepository]
        NR1 --> NDB[(DB)]
        NR2 --> NDB
    end

    style Express fill:#f5f5f5,stroke:#333
    style Nest fill:#f5f5f5,stroke:#333
```

Express.js는 라우터 핸들러에서 바로 DB에 접근하는 경우가 많다. 규모가 작을 땐 빠르지만, 비즈니스 로직이 복잡해지면 핸들러 함수가 비대해진다.

NestJS는 Module → Controller → Service → Repository 계층이 강제된다. 처음엔 파일이 많다고 느끼지만, 팀에 새로 합류한 사람이 코드 위치를 예측할 수 있다는 점에서 유지보수에 유리하다.

---

## 요청 처리 흐름 비교

HTTP 요청이 들어왔을 때 각 프레임워크가 어떤 순서로 처리하는지 비교한다. 실제로 디버깅할 때 "내 코드가 어느 시점에 실행되는가"를 파악하는 데 이 흐름을 알아두면 시간을 줄일 수 있다.

### Express.js 요청 흐름

```mermaid
sequenceDiagram
    participant C as Client
    participant A as Express App
    participant M as 미들웨어 체인
    participant R as 라우트 핸들러
    participant D as DB

    C->>A: HTTP 요청
    A->>M: 미들웨어 순차 실행
    Note over M: body-parser, cors,<br/>인증 체크 등
    M->>R: next()로 전달
    R->>D: 쿼리 실행
    D-->>R: 결과 반환
    R-->>C: res.json() 응답
```

Express.js는 `app.use()`로 등록한 순서대로 미들웨어가 실행된다. `next()`를 호출하지 않으면 요청이 거기서 멈추는데, 이걸 빠뜨려서 요청이 hanging되는 실수가 흔하다.

### NestJS 요청 흐름

```mermaid
sequenceDiagram
    participant C as Client
    participant G as Guard
    participant I as Interceptor
    participant P as Pipe
    participant CT as Controller
    participant S as Service
    participant D as DB

    C->>G: HTTP 요청
    Note over G: 인증/인가 확인
    G->>I: 통과 시 전달
    Note over I: 요청 전처리<br/>(로깅, 캐싱 등)
    I->>P: 전달
    Note over P: 유효성 검사,<br/>타입 변환
    P->>CT: 검증된 데이터 전달
    CT->>S: 비즈니스 로직 위임
    S->>D: 쿼리 실행
    D-->>S: 결과 반환
    S-->>CT: 처리 결과
    CT-->>I: 응답 데이터
    Note over I: 응답 후처리<br/>(변환, 캐싱)
    I-->>C: 최종 응답
```

NestJS는 Guard → Interceptor → Pipe → Controller → Service 순서로 요청을 처리한다. 각 단계가 역할이 명확하게 분리되어 있어서, 인증 로직은 Guard에, 유효성 검사는 Pipe에 넣으면 된다. Express.js에서는 이런 구분 없이 미들웨어에 다 넣거나 핸들러 안에서 직접 처리하게 된다.

실무에서 차이가 드러나는 부분은 에러 처리다. Express.js는 에러 미들웨어를 마지막에 등록해야 하고, 비동기 에러는 `next(err)`로 직접 넘겨야 한다. NestJS는 Exception Filter가 알아서 잡아주기 때문에 비동기 에러 누락이 거의 없다.

### 에러 처리 흐름 비교

```mermaid
graph LR
    subgraph Express["Express.js 에러 처리"]
        E1[라우트 핸들러] -->|throw 또는 next err| E2[에러 미들웨어]
        E2 --> E3[에러 응답]
        E1 -->|비동기 에러 누락| E4[프로세스 크래시]
    end

    subgraph Nest["NestJS 에러 처리"]
        N1[Controller/Service] -->|throw HttpException| N2[Exception Filter]
        N2 --> N3[에러 응답]
        N1 -->|비동기 에러| N2
    end

    style E4 fill:#ffcccc,stroke:#cc0000
    style Express fill:#f5f5f5,stroke:#333
    style Nest fill:#f5f5f5,stroke:#333
```

Express.js에서 `async` 핸들러의 에러를 `try-catch` 없이 던지면 에러 미들웨어까지 도달하지 못하고 프로세스가 죽는 경우가 있다. Express 5부터는 이 문제가 개선되었지만, Express 4를 쓰고 있다면 `express-async-errors` 같은 패키지가 필요하다.

---

## 주요 기능 비교

### 1. 타입 시스템

#### Express.js
- JavaScript 기반
- 타입 안정성을 위해 JSDoc이나 TypeScript를 별도로 설정해야 함
- 런타임 에러 발생 가능성 높음

#### NestJS
- TypeScript 기반
- 컴파일 타임에 타입 체크
- 더 안정적인 코드 작성 가능, IDE 지원 우수

### 2. 미들웨어 처리

#### Express.js
```javascript
app.use((req, res, next) => {
  // 미들웨어 로직
  next();
});
```

#### NestJS
```typescript
@Injectable()
export class LoggerMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: Function) {
    // 미들웨어 로직
    next();
  }
}
```

### 3. 라우팅

#### Express.js
```javascript
app.get('/users', (req, res) => {
  // 라우트 핸들러
});
```

#### NestJS
```typescript
@Controller('users')
export class UsersController {
  @Get()
  findAll(): User[] {
    // 컨트롤러 메서드
  }
}
```
- 데코레이터 기반 라우팅, 자동 OpenAPI 문서화 지원

### 4. 데이터베이스 통합

#### Express.js
- 직접 데이터베이스 드라이버 사용
- Mongoose, Sequelize 등 ORM/ODM을 별도로 설정
- 유연한 데이터베이스 통합

#### NestJS
- TypeORM, Mongoose 등과의 통합 공식 지원
- Repository 패턴 구현 용이
- 데이터베이스 마이그레이션 도구 내장

---

## 성능 및 확장성

### Express.js
- **장점**: 가벼운 오버헤드, 빠른 시작 시간, 낮은 메모리 사용량
- **단점**: 대규모 애플리케이션에서 구조화 어려움

### NestJS
- **장점**: 구조화된 확장성, 모듈 재사용 용이, 테스트 용이성
- **단점**: 상대적으로 높은 초기 오버헤드, 더 많은 보일러플레이트 코드

---

## 학습 곡선

### Express.js
- **장점**: 낮은 진입 장벽, 직관적인 API, 풍부한 학습 자료
- **단점**: 대규모 프로젝트에서 일관된 패턴 유지 어려움

### NestJS
- **장점**: 명확한 아키텍처 가이드라인, Angular 개발자에게 친숙
- **단점**: TypeScript·데코레이터 학습 필요, 초기 설정 복잡

---

## 사용 사례

### Express.js 적합한 경우
1. 소규모 프로젝트, 빠른 프로토타이핑
2. 마이크로서비스 (단일 책임 서비스)
3. REST API, 실시간 애플리케이션
4. Node.js 초보자

### NestJS 적합한 경우
1. 대규모 엔터프라이즈 애플리케이션
2. TypeScript 기반 프로젝트
3. 복잡한 비즈니스 로직, 마이크로서비스 아키텍처
4. Angular와 통합된 풀스택 애플리케이션

---

## 생태계 및 커뮤니티

### Express.js
- **장점**: 큰 커뮤니티, 수많은 미들웨어, 오랜 기간 검증
- **단점**: 일부 패키지 유지보수 부족, 품질 불균형

### NestJS
- **장점**: 활발한 개발, 공식 모듈 지원, 체계적인 문서
- **단점**: 상대적으로 작은 커뮤니티, 제한된 서드파티 패키지

---

## 결론

| 상황 | 권장 |
|------|------|
| 소규모 프로젝트 / 빠른 개발 | Express.js |
| 대규모 엔터프라이즈 | NestJS |
| TypeScript 기반 팀 | NestJS |
| Node.js 입문 | Express.js |
| 마이크로서비스 | 팀 경험에 따라 선택 |

각 프레임워크는 고유한 장단점이 있다. Express.js는 유연성과 간단함을, NestJS는 구조화와 확장성을 제공한다. 프로젝트 규모와 팀 역량에 맞게 선택하는 것이 중요하다.
