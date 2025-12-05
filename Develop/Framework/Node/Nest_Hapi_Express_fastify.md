---
title: Node.js NestJS vs Hapi vs Express vs Fastify
tags: [framework, node, nesthapiexpressfastify, nodejs]
updated: 2025-12-05
---
# Node.js 웹 프레임워크 심층 비교 분석: NestJS vs Hapi vs Express vs Fastify

## 배경
1. [소개](#소개)
2. [프레임워크 개요 및 역사](#프레임워크-개요-및-역사)
3. [기술 스택 및 의존성](#기술-스택-및-의존성)
4. [성능 벤치마크](#성능-벤치마크)
5. [아키텍처 및 설계 패턴](#아키텍처-및-설계-패턴)
6. [핵심 기능 비교](#핵심-기능-비교)
7. [보안 및 인증](#보안-및-인증)
8. [데이터베이스 통합](#데이터베이스-통합)
9. [테스트 및 디버깅](#테스트-및-디버깅)
10. [배포 및 운영](#배포-및-운영)
11. [사용 사례 및 실제 적용](#사용-사례-및-실제-적용)
12. [커뮤니티 및 생태계](#커뮤니티-및-생태계)
13. [학습 리소스 및 문서화](#학습-리소스-및-문서화)
14. [결론 및 추천](#결론-및-추천)


Node.js 웹 프레임워크 시장은 지속적으로 발전하고 있으며, 각 프레임워크는 고유한 특성과 장단점을 가지고 있습니다. 이 문서는 가장 인기 있는 4개의 프레임워크를 심층적으로 분석하여 개발자들이 프로젝트에 가장 적합한 프레임워크를 선택할 수 있도록 도움을 드립니다.


### Express.js
| 항목 | 내용 |
|------|------|
| 출시일 | 2010년 11월 |
| 현재 버전 | 4.18.2 (2024년 3월 기준) |
| GitHub Stars | 60,000+ |
| 주 개발자 | TJ Holowaychuk (초기), StrongLoop, IBM |
| 라이선스 | MIT |
| 주요 사용처 | IBM, Accenture, Uber (초기) |

### NestJS
| 항목 | 내용 |
|------|------|
| 출시일 | 2017년 8월 |
| 현재 버전 | 10.0.0 (2024년 3월 기준) |
| GitHub Stars | 55,000+ |
| 주 개발자 | Kamil Mysliwiec |
| 라이선스 | MIT |
| 주요 사용처 | Adidas, Roche, Capgemini |

### Hapi
| 항목 | 내용 |
|------|------|
| 출시일 | 2011년 8월 |
| 현재 버전 | 21.3.2 (2024년 3월 기준) |
| GitHub Stars | 14,000+ |
| 주 개발자 | Eran Hammer, Walmart Labs |
| 라이선스 | BSD-3-Clause |
| 주요 사용처 | Walmart, Disney, Condé Nast |

### Fastify
| 항목 | 내용 |
|------|------|
| 출시일 | 2016년 12월 |
| 현재 버전 | 4.24.3 (2024년 3월 기준) |
| GitHub Stars | 26,000+ |
| 주 개발자 | Matteo Collina, Tomas Della Vedova |
| 라이선스 | MIT |
| 주요 사용처 | Platformatic, NearForm |


### Express.js
```json
{
  "dependencies": {
    "express": "^4.18.2",
    "body-parser": "^1.20.2",
    "cookie-parser": "^1.4.6",
    "cors": "^2.8.5"
  }
}
```

### NestJS
```json
{
  "dependencies": {
    "@nestjs/common": "^10.0.0",
    "@nestjs/core": "^10.0.0",
    "@nestjs/platform-express": "^10.0.0",
    "reflect-metadata": "^0.1.13",
    "rxjs": "^7.8.1"
  }
}
```

### Hapi
```json
{
  "dependencies": {
    "@hapi/hapi": "^21.3.2",
    "@hapi/boom": "^10.0.1",
    "@hapi/joi": "^17.9.2"
  }
}
```

### Fastify
```json
{
  "dependencies": {
    "fastify": "^4.24.3",
    "@fastify/cors": "^8.3.0",
    "@fastify/static": "^6.10.2"
  }
}
```


### 1. 요청 처리 성능 (초당 요청 수)

| 프레임워크 | 기본 설정 | 최적화 설정 | 메모리 사용량 |
|------------|-----------|-------------|--------------|
| Fastify | 80,000 req/s | 120,000 req/s | 30MB |
| Express | 15,000 req/s | 25,000 req/s | 45MB |
| NestJS | 14,000 req/s | 20,000 req/s | 50MB |
| Hapi | 12,000 req/s | 18,000 req/s | 55MB |

### 2. 응답 시간 (밀리초)

| 프레임워크 | 평균 | 95th 백분위 | 99th 백분위 |
|------------|------|-------------|-------------|
| Fastify | 0.5ms | 1.2ms | 2.5ms |
| Express | 1.2ms | 2.8ms | 5.0ms |
| NestJS | 1.5ms | 3.2ms | 6.0ms |
| Hapi | 1.8ms | 3.8ms | 7.0ms |

### 3. 메모리 사용량 (기본 설정)

| 프레임워크 | 초기 로드 | 1000 요청 후 | 10000 요청 후 |
|------------|-----------|--------------|---------------|
| Fastify | 30MB | 35MB | 40MB |
| Express | 45MB | 50MB | 60MB |
| NestJS | 50MB | 55MB | 65MB |
| Hapi | 55MB | 60MB | 70MB |


### Express.js
```javascript
// 기본 구조
const express = require('express');
const app = express();

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.get('/', (req, res) => {
  res.send('Hello World');
});

app.listen(3000);
```

### NestJS
```typescript
// 기본 구조
@Controller('users')
export class UsersController {
  constructor(private readonly usersService: UsersService) {}

  @Get()
  findAll(): Promise<User[]> {
    return this.usersService.findAll();
  }
}
```

### Hapi
```javascript
// 기본 구조
const Hapi = require('@hapi/hapi');

const server = Hapi.server({
  port: 3000,
  host: 'localhost'
});

server.route({
  method: 'GET',
  path: '/',
  handler: (request, h) => {
    return 'Hello World';
  }
});
```

### Fastify
```javascript
// 기본 구조
const fastify = require('fastify')({
  logger: true
});

fastify.get('/', async (request, reply) => {
  return { hello: 'world' };
});

fastify.listen({ port: 3000 });
```


### 1. 라우팅 시스템

| 기능 | Express | NestJS | Hapi | Fastify |
|------|---------|--------|------|---------|
| 기본 라우팅 | 지원 | 지원 | 지원 | 지원 |
| 동적 라우팅 | 지원 | 지원 | 지원 | 지원 |
| 라우트 그룹화 | 지원 | 지원 | 지원 | 지원 |
| 라우트 미들웨어 | 지원 | 지원 | 지원 | 지원 |
| 라우트 파라미터 검증 | 미지원 | 지원 | 지원 | 지원 |
| 라우트 버전 관리 | 미지원 | 지원 | 지원 | 지원 |

### 2. 미들웨어 시스템

| 기능 | Express | NestJS | Hapi | Fastify |
|------|---------|--------|------|---------|
| 커스텀 미들웨어 | 지원 | 지원 | 지원 | 지원 |
| 미들웨어 체인 | 지원 | 지원 | 지원 | 지원 |
| 에러 핸들링 | 지원 | 지원 | 지원 | 지원 |
| 요청/응답 변환 | 지원 | 지원 | 지원 | 지원 |
| 비동기 미들웨어 | 지원 | 지원 | 지원 | 지원 |
| 미들웨어 우선순위 | 지원 | 지원 | 지원 | 지원 |

### 3. 템플릿 엔진

| 기능 | Express | NestJS | Hapi | Fastify |
|------|---------|--------|------|---------|
| EJS | 지원 | 지원 | 지원 | 지원 |
| Pug | 지원 | 지원 | 지원 | 지원 |
| Handlebars | 지원 | 지원 | 지원 | 지원 |
| Mustache | 지원 | 지원 | 지원 | 지원 |
| Nunjucks | 지원 | 지원 | 지원 | 지원 |


### 1. 기본 보안 기능

| 기능 | Express | NestJS | Hapi | Fastify |
|------|---------|--------|------|---------|
| CORS | 지원 | 지원 | 지원 | 지원 |
| Helmet | 지원 | 지원 | 지원 | 지원 |
| Rate Limiting | 지원 | 지원 | 지원 | 지원 |
| XSS Protection | 지원 | 지원 | 지원 | 지원 |
| CSRF Protection | 지원 | 지원 | 지원 | 지원 |
| Content Security Policy | 지원 | 지원 | 지원 | 지원 |

### 2. 인증 방식

| 방식 | Express | NestJS | Hapi | Fastify |
|------|---------|--------|------|---------|
| JWT | 지원 | 지원 | 지원 | 지원 |
| OAuth2 | 지원 | 지원 | 지원 | 지원 |
| Basic Auth | 지원 | 지원 | 지원 | 지원 |
| Session-based | 지원 | 지원 | 지원 | 지원 |
| API Keys | 지원 | 지원 | 지원 | 지원 |


### 1. ORM/ODM 지원

| 데이터베이스 | Express | NestJS | Hapi | Fastify |
|-------------|---------|--------|------|---------|
| MongoDB | 지원 | 지원 | 지원 | 지원 |
| MySQL | 지원 | 지원 | 지원 | 지원 |
| PostgreSQL | 지원 | 지원 | 지원 | 지원 |
| SQLite | 지원 | 지원 | 지원 | 지원 |
| Redis | 지원 | 지원 | 지원 | 지원 |

### 2. 데이터베이스 도구

| 도구 | Express | NestJS | Hapi | Fastify |
|------|---------|--------|------|---------|
| TypeORM | 지원 | 지원 | 지원 | 지원 |
| Sequelize | 지원 | 지원 | 지원 | 지원 |
| Mongoose | 지원 | 지원 | 지원 | 지원 |
| Prisma | 지원 | 지원 | 지원 | 지원 |
| Knex.js | 지원 | 지원 | 지원 | 지원 |


### 1. 테스트 프레임워크 지원

| 프레임워크 | Express | NestJS | Hapi | Fastify |
|------------|---------|--------|------|---------|
| Jest | 지원 | 지원 | 지원 | 지원 |
| Mocha | 지원 | 지원 | 지원 | 지원 |
| Chai | 지원 | 지원 | 지원 | 지원 |
| Supertest | 지원 | 지원 | 지원 | 지원 |
| Cypress | 지원 | 지원 | 지원 | 지원 |

### 2. 디버깅 도구

| 도구 | Express | NestJS | Hapi | Fastify |
|------|---------|--------|------|---------|
| Node Inspector | 지원 | 지원 | 지원 | 지원 |
| VS Code Debugger | 지원 | 지원 | 지원 | 지원 |
| Chrome DevTools | 지원 | 지원 | 지원 | 지원 |
| Logging | 지원 | 지원 | 지원 | 지원 |
| Performance Profiling | 지원 | 지원 | 지원 | 지원 |


### 1. 배포 옵션

| 옵션 | Express | NestJS | Hapi | Fastify |
|------|---------|--------|------|---------|
| Docker | 지원 | 지원 | 지원 | 지원 |
| Kubernetes | 지원 | 지원 | 지원 | 지원 |
| PM2 | 지원 | 지원 | 지원 | 지원 |
| Heroku | 지원 | 지원 | 지원 | 지원 |
| AWS Lambda | 지원 | 지원 | 지원 | 지원 |

### 2. 모니터링 도구

| 도구 | Express | NestJS | Hapi | Fastify |
|------|---------|--------|------|---------|
| New Relic | 지원 | 지원 | 지원 | 지원 |
| Datadog | 지원 | 지원 | 지원 | 지원 |
| Prometheus | 지원 | 지원 | 지원 | 지원 |
| Grafana | 지원 | 지원 | 지원 | 지원 |
| ELK Stack | 지원 | 지원 | 지원 | 지원 |


### 1. 대규모 프로젝트 사례

| 회사 | 프레임워크 | 사용 목적 |
|------|------------|-----------|
| IBM | Express | 클라우드 서비스 |
| Adidas | NestJS | 전자상거래 플랫폼 |
| Walmart | Hapi | 전자상거래 API |
| Platformatic | Fastify | 마이크로서비스 |

### 2. 프로젝트 규모별 추천

| 규모 | 추천 프레임워크 | 이유 |
|------|----------------|------|
| 소규모 | Express | 빠른 개발, 낮은 학습 곡선 |
| 중규모 | Fastify | 좋은 성능, 적절한 구조화 |
| 대규모 | NestJS | 엔터프라이즈급 구조, TypeScript |
| 보안 중심 | Hapi | 강력한 보안 기능 |


### 1. 커뮤니티 활동

| 지표 | Express | NestJS | Hapi | Fastify |
|------|---------|--------|------|---------|
| GitHub Stars | 60k+ | 55k+ | 14k+ | 26k+ |
| NPM 주간 다운로드 | 30M+ | 500k+ | 100k+ | 200k+ |
| Stack Overflow 질문 | 100k+ | 20k+ | 5k+ | 10k+ |
| 활성 기여자 | 200+ | 100+ | 50+ | 80+ |

### 2. 생태계 풍부도

| 카테고리 | Express | NestJS | Hapi | Fastify |
|----------|---------|--------|------|---------|
| 미들웨어 | 1000+ | 500+ | 200+ | 300+ |
| 플러그인 | 500+ | 300+ | 200+ | 250+ |
| 템플릿 | 50+ | 30+ | 20+ | 25+ |
| 데이터베이스 | 100+ | 80+ | 50+ | 60+ |


### 1. 공식 문서

| 항목 | Express | NestJS | Hapi | Fastify |
|------|---------|--------|------|---------|
| 튜토리얼 | 지원 | 지원 | 지원 | 지원 |
| API 문서 | 지원 | 지원 | 지원 | 지원 |
| 예제 코드 | 지원 | 지원 | 지원 | 지원 |
| 비디오 강의 | 지원 | 지원 | 지원 | 지원 |
| 커뮤니티 가이드 | 지원 | 지원 | 지원 | 지원 |

### 2. 학습 곡선

| 단계 | Express | NestJS | Hapi | Fastify |
|------|---------|--------|------|---------|
| 기본 학습 | 1-2일 | 1-2주 | 3-5일 | 2-4일 |
| 중급 학습 | 1주 | 2-3주 | 1-2주 | 1-2주 |
| 고급 학습 | 2-3주 | 1-2개월 | 2-3주 | 2-3주 |


### 1. 프로젝트 유형별 추천

| 프로젝트 유형 | 1순위 | 2순위 | 3순위 |
|--------------|-------|-------|-------|
| REST API | Fastify | Express | NestJS |
| 마이크로서비스 | NestJS | Fastify | Hapi |
| 실시간 애플리케이션 | Fastify | Express | NestJS |
| 엔터프라이즈 애플리케이션 | NestJS | Hapi | Express |
| 보안 중심 애플리케이션 | Hapi | NestJS | Fastify |

### 2. 최종 추천

1. **신규 프로젝트 시작 시**:
   - 소규모: Express.js (빠른 개발, 풍부한 생태계)
   - 중규모: Fastify (좋은 성능, 적절한 구조화)
   - 대규모: NestJS (엔터프라이즈급 구조, TypeScript)

2. **기존 프로젝트 마이그레이션 시**:
   - Express.js → Fastify (성능 개선)
   - Express.js → NestJS (구조화 필요)
   - Express.js → Hapi (보안 강화)

3. **특수 요구사항**:
   - 최고 성능: Fastify
   - 보안 중심: Hapi
   - TypeScript: NestJS
   - 빠른 개발: Express.js










