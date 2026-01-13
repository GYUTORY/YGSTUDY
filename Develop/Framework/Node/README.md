---
title: Node.js 프레임워크 문서 인덱스
tags: [framework, node, index, navigation]
updated: 2026-01-13
---

# Node.js 프레임워크 문서 인덱스

Node.js 백엔드 개발을 위한 기술 문서 모음입니다.

## 주제별 문서 분류

### 기초 및 구조

Node.js의 내부 동작 원리와 모듈 시스템, 프로세스 관리에 대한 문서입니다.

#### Node.js 기본
- [Node.js 기본 개념과 구조](./Nodejs의%20구조%20및%20작동%20원리/Node.md) - V8 엔진과 libuv의 역할, 이벤트 루프 동작 원리 및 비동기 처리 메커니즘
- [Cluster](./Nodejs의%20구조%20및%20작동%20원리/Cluster.md) - Cluster 모듈을 활용한 멀티프로세싱, 마스터-워커 패턴, 로드 밸런싱
- [Cluster와 Multi Thread](./Nodejs의%20구조%20및%20작동%20원리/Cluster와%20Multi%20Thread.md) - 멀티프로세싱을 통한 CPU 활용 최적화, 워커 스레드를 활용한 병렬 처리
- [Thread](./Nodejs의%20구조%20및%20작동%20원리/Thread.md) - Worker Threads API를 활용한 CPU 집약적 작업 처리 및 메인 스레드 블로킹 방지

#### 모듈 시스템
- [CommonJS vs ESM](./모듈%20시스템/CommonJS%20vs%20ESM.md) - CommonJS와 ES Modules의 차이점, 동적/정적 로딩, 호환성 고려사항
- [npm](./모듈%20시스템/npm.md) - 패키지 설치 및 버전 관리, package.json 설정, 의존성 해결
- [npx](./모듈%20시스템/npx.md) - 로컬 설치 없이 패키지 실행, 일회성 스크립트 실행 방법
- [pnpm](./모듈%20시스템/pnpm.md) - 심볼릭 링크 기반 효율적인 디스크 공간 활용, 엄격한 의존성 관리

#### 프로세스 관리
- [PM2](./Process%20Management%20Tool/pm2/pm2.md) - 프로세스 관리, 자동 재시작, 로그 관리, 메모리 모니터링
- [PM2 클러스터 모드](./Process%20Management%20Tool/pm2/클러스터_모드.md) - 멀티 코어 활용을 위한 클러스터 모드 설정 및 로드 밸런싱
- [PM2 Ecosystem](./Process%20Management%20Tool/pm2/ecosystem.md) - ecosystem.config.js를 통한 환경별 설정 관리 및 배포 자동화
- [Forever](./Process%20Management%20Tool/forever.md) - 간단한 프로세스 관리 도구, 개발 환경에서의 활용

### API 개발

#### API 설계
- [API 설계 원칙](./API/API_설계_원칙.md) - RESTful 원칙과 버저닝, OpenAPI/Swagger를 활용한 API 문서화, 하위 호환성을 고려한 설계
- [GraphQL](./API/GraphQL.md) - GraphQL 스키마 설계, 리졸버 구현, N+1 문제 해결, 데이터 로더 패턴
- [Rate Limiting](./API/Rate_Limiting.md) - 토큰 버킷, 슬라이딩 윈도우 알고리즘을 활용한 API 제한 및 DDoS 보호

#### 통신
- [WebSocket/Socket.io](./통신/WebSocket_SocketIO.md) - 실시간 양방향 통신 구현, 방 관리, 이벤트 기반 메시징, 연결 관리 및 재연결
- [스트림](./데이터%20처리%20및%20통신/스트림(Stream).md) - Readable, Writable, Transform 스트림 활용, 대용량 데이터 처리 및 메모리 효율성

### 데이터베이스

- [ORM 심화](./데이터베이스/ORM_심화_전략.md) - TypeORM, Sequelize, Prisma 비교 및 선택 기준, 관계 매핑, 쿼리 최적화, 마이그레이션
- [연결 풀 관리](./데이터베이스/연결_풀_관리.md) - 연결 풀 크기 최적화, 타임아웃 설정, Read/Write 분리를 통한 부하 분산
- [분산 트랜잭션](./데이터베이스/분산_트랜잭션_전략.md) - Saga 패턴을 통한 분산 트랜잭션 처리, 이벤트 소싱, CQRS 아키텍처 구현

### 인증 및 보안

- [JWT 구현 및 보안](./인증/JWT_구현_및_보안.md) - Access/Refresh Token 패턴, 토큰 갱신, XSS/CSRF 방어, 토큰 저장 및 전송 보안
- [보안 모범 사례](./보안/Node.js_보안_모범사례.md) - Helmet을 통한 HTTP 헤더 보안, CORS 설정, 입력 검증 및 sanitization, SQL Injection 방지

### 성능 및 최적화

- [성능 최적화 및 프로파일링](./Performance/Node.js_성능_최적화_및_프로파일링.md) - 프로파일링 도구를 활용한 CPU/메모리 분석, 비동기 처리 최적화, 메모리 누수 탐지 및 해결
- [부하 테스트](./성능/부하_테스트_전략.md) - k6, Artillery를 활용한 부하 테스트 시나리오 작성, 성능 벤치마킹 및 병목 지점 분석
- [캐싱](./캐싱/캐싱_전략.md) - Redis를 활용한 캐싱 패턴, 캐시 무효화, 캐시 스탬피드 방지, 분산 캐시 관리

### 모니터링 및 관찰 가능성

- [로깅](./로깅/로깅_전략.md) - Winston, Pino를 활용한 구조화 로깅, 로그 레벨 관리, 로그 집계 및 분석
- [Observability](./모니터링/Observability_전략.md) - APM 도구를 통한 성능 모니터링, 분산 추적, OpenTelemetry를 활용한 표준화된 관찰 가능성 구축

### 안정성 및 품질

- [에러 핸들링](./에러_핸들링/에러_핸들링_전략.md) - 에러 타입 분류, 커스텀 에러 클래스 설계, 에러 복구, 일관된 에러 응답 형식
- [코드 품질 및 리팩토링](./코드_품질/리팩토링_전략.md) - 코드 냄새 식별, 리팩토링 패턴 적용, 테스트 가능한 코드 구조 설계

### 배포 및 운영

- [배포](./배포/배포_전략.md) - Blue-Green, Canary, Rolling 배포 비교 및 선택 기준, 롤백
- [Bitbucket Pipeline](./Bitbucket_Pipeline.md) - Bitbucket Pipelines를 활용한 CI/CD 파이프라인 구성, 테스트 자동화, 배포 자동화

### 백그라운드 작업

- [작업 큐 처리](./백그라운드_작업/작업_큐_처리.md) - Bull Queue, Agenda를 활용한 작업 큐 구현, 작업 우선순위 관리, 재시도, 작업 모니터링

### 파일 처리

- [파일 업로드 및 처리](./파일_처리/파일_업로드_및_처리.md) - Multer를 활용한 파일 업로드, AWS S3 연동, 이미지 리사이징 및 최적화, 파일 검증 및 보안

### 테스트

- [테스트 자동화 및 품질 보증](./Testing/테스트_자동화_및_품질_보증.md) - Jest, Mocha를 활용한 테스트 작성, 테스트 커버리지 관리, CI/CD 파이프라인 통합
- [API E2E 테스트 패턴](./Testing/API_E2E_테스트_패턴.md) - API 엔드포인트 E2E 테스트 작성, 테스트 데이터 관리, 테스트 격리
- [데이터베이스 통합 테스트](./Testing/Database_Integration_Testing.md) - 데이터베이스 통합 테스트, 테스트용 데이터베이스 설정, 트랜잭션 롤백을 통한 테스트 격리
- [외부 API 모킹](./Testing/외부_API_모킹.md) - 외부 API 의존성 모킹, nock, MSW를 활용한 HTTP 모킹, 테스트 안정성 확보

### 프레임워크

#### NestJS
- [NestJS 사용법](./NestJS/How_To_USE.md) - NestJS 아키텍처, 모듈 시스템, 의존성 주입, 데코레이터 활용
- [NestJS vs Express](./NestJS/NestJs%20vs%20ExpressJs.md) - NestJS와 Express의 차이점, 사용 사례별 선택 기준
- [NestJS 실전 예제](./NestJS/실전_예제.md) - REST API, 데이터베이스 연동, 인증/인가, 파일 업로드, WebSocket 구현 예제

#### 프레임워크 비교
- [NestJS vs Hapi vs Express vs Fastify](./Nest_Hapi_Express_fastify.md) - 주요 Node.js 프레임워크 종합 비교, 성능, 생태계, 학습 곡선 분석

### 아키텍처

- [마이크로서비스 통신 패턴](./아키텍처/마이크로서비스_통신_패턴.md) - 동기/비동기 통신 패턴, Circuit Breaker 패턴, Service Discovery, API Gateway 패턴
- [Event Driven Architecture with AWS](./아키텍처/Event_Driven_Architecture_with_AWS.md) - NestJS와 AWS SNS/SQS를 활용한 이벤트 기반 아키텍처, Lambda 통합, 마이크로서비스 구현

### 실전 예제

- [프로젝트 구조 예제](./실전_예제/프로젝트_구조_예제.md) - Express/NestJS 기반 프로젝트 구조 설계, 레이어 분리, 모듈화

### 기타

- [함수형 프로그래밍](./함수형%20프로그래밍.md) - 함수형 프로그래밍 패러다임, 불변성, 고차 함수, 함수 합성

## 실전 시나리오

### RESTful API 개발

표준 RESTful API를 설계하고 구현할 때 필요한 핵심 문서들입니다.

1. [API 설계 원칙](./API/API_설계_원칙.md) - RESTful 원칙과 버저닝
2. [JWT 구현 및 보안](./인증/JWT_구현_및_보안.md) - Access/Refresh Token 기반 인증 구현
3. [ORM 심화](./데이터베이스/ORM_심화_전략.md) - TypeORM, Sequelize, Prisma를 활용한 데이터베이스 연동
4. [Rate Limiting](./API/Rate_Limiting.md) - API 보호 및 트래픽 제어
5. [에러 핸들링](./에러_핸들링/에러_핸들링_전략.md) - 일관된 에러 응답 및 복구
6. [로깅](./로깅/로깅_전략.md) - 구조화된 로깅 및 운영 모니터링

### 실시간 애플리케이션

WebSocket 기반 실시간 통신 애플리케이션 구축 시 참고할 문서들입니다.

1. [WebSocket/Socket.io](./통신/WebSocket_SocketIO.md) - 실시간 양방향 통신 구현
2. [JWT 구현 및 보안](./인증/JWT_구현_및_보안.md) - WebSocket 연결 인증 및 보안
3. [캐싱](./캐싱/캐싱_전략.md) - 실시간 데이터 캐싱 및 상태 관리
4. [Observability](./모니터링/Observability_전략.md) - 실시간 시스템 모니터링 및 추적

### 고성능 시스템 구축

대규모 트래픽을 처리하는 고성능 시스템을 구축할 때 필요한 문서들입니다.

1. [성능 최적화](./Performance/Node.js_성능_최적화_및_프로파일링.md) - 프로파일링 기반 성능 최적화
2. [연결 풀 관리](./데이터베이스/연결_풀_관리.md) - 데이터베이스 연결 풀 최적화 및 Read/Write 분리
3. [캐싱](./캐싱/캐싱_전략.md) - Redis 기반 캐싱 및 무효화 패턴
4. [부하 테스트](./성능/부하_테스트_전략.md) - k6, Artillery를 활용한 성능 벤치마킹
5. [Observability](./모니터링/Observability_전략.md) - APM 및 분산 추적을 통한 성능 모니터링

### 프로덕션 배포

안정적이고 안전한 프로덕션 환경 구축을 위한 문서들입니다.

1. [보안 모범 사례](./보안/Node.js_보안_모범사례.md) - Helmet, CORS, 입력 검증 등 보안 강화
2. [에러 핸들링](./에러_핸들링/에러_핸들링_전략.md) - 프로덕션 환경 에러 처리 및 복구
3. [로깅](./로깅/로깅_전략.md) - 운영 환경 로깅 및 로그 관리
4. [Observability](./모니터링/Observability_전략.md) - OpenTelemetry 기반 모니터링 구축
5. [배포](./배포/배포_전략.md) - Blue-Green, Canary, Rolling 배포

## 빠른 참조

### 관련 문서 연결

- **인증 구현**: [JWT 구현 및 보안](./인증/JWT_구현_및_보안.md)과 [보안 모범 사례](./보안/Node.js_보안_모범사례.md)를 함께 참고
- **데이터베이스 최적화**: [ORM 심화](./데이터베이스/ORM_심화_전략.md)와 [연결 풀 관리](./데이터베이스/연결_풀_관리.md)를 함께 검토
- **성능 개선**: [성능 최적화 및 프로파일링](./Performance/Node.js_성능_최적화_및_프로파일링.md)으로 병목 지점 파악 후 [부하 테스트](./성능/부하_테스트_전략.md)로 검증
- **운영 모니터링**: [로깅](./로깅/로깅_전략.md) 구축 후 [Observability](./모니터링/Observability_전략.md)로 확장

### 문제 해결 가이드

| 문제 상황 | 참고 문서 |
|----------|----------|
| API 응답 속도 저하 | [성능 최적화 및 프로파일링](./Performance/Node.js_성능_최적화_및_프로파일링.md), [캐싱](./캐싱/캐싱_전략.md) |
| 메모리 사용량 지속 증가 | [성능 최적화 및 프로파일링](./Performance/Node.js_성능_최적화_및_프로파일링.md) |
| 데이터베이스 쿼리 성능 저하 | [ORM 심화](./데이터베이스/ORM_심화_전략.md), [연결 풀 관리](./데이터베이스/연결_풀_관리.md) |
| 보안 취약점 발견 | [보안 모범 사례](./보안/Node.js_보안_모범사례.md), [JWT 구현 및 보안](./인증/JWT_구현_및_보안.md) |
| 배포 중 서비스 장애 | [배포](./배포/배포_전략.md), [에러 핸들링](./에러_핸들링/에러_핸들링_전략.md) |
| 운영 중 문제 진단 어려움 | [Observability](./모니터링/Observability_전략.md), [로깅](./로깅/로깅_전략.md) |

## 문서 업데이트

- **최종 업데이트**: 2025-11-17
- **문서 버전**: v2.0

