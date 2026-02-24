---
title: 학습 및 보완 항목
updated: 2026-01-18
---

# 학습 및 보완 항목

5년차 백엔드 개발자 관점에서 실무에 필요한 항목을 정리했다. 우선순위는 현업에서 자주 마주치는 순서다.

## AWS 인프라

### 컴퓨팅 & 컨테이너 (우선순위: 높음)
- [V] **EKS**: 프로덕션에서 Kubernetes 운영 시 필수. ECS와 비교하면서 학습
- [V] **Fargate**: 서버리스 컨테이너 실행. ECS/EKS 운영 부담 줄이는 용도
- [V] **Auto Scaling**: EC2, ECS 스케일링 정책 설정. CPU/메모리 임계값 기반
- [V] **Elastic Beanstalk**: 빠른 배포가 필요한 경우 사용. 하지만 제약사항 많음

### 메시징 & 스트리밍 (우선순위: 높음)
- [V] **Kinesis**: 실시간 로그 처리, 이벤트 스트리밍. SQS로는 부족한 경우
- [V] **EventBridge**: 이벤트 기반 아키텍처. SNS/SQS 조합보다 유연함
- [V] **MSK**: Kafka 관리형 서비스. 직접 운영할 필요 없음
- [V] **Step Functions**: Lambda 여러 개 연결할 때. 워크플로우 시각화 가능

### 데이터베이스 & 캐싱 (우선순위: 높음)
- [V] **DynamoDB**: NoSQL 필요한 경우. 키-값 조회가 많으면 적합
- [V] **ElastiCache**: Redis/Memcached 관리형. 직접 운영보다 편함
- [V] **DMS**: RDS 간 마이그레이션, 온프레미스에서 AWS로 이전
- [V] **DAX**: DynamoDB 앞단 캐시. 읽기 성능 향상

### 네트워킹 & 보안 (우선순위: 중간)
- [V] **Transit Gateway**: 여러 VPC 연결. VPC Peering보다 관리 편함
- [V] **PrivateLink**: 외부 노출 없이 서비스 연결. 보안 강화
- [V] **WAF**: SQL Injection, XSS 방어. ALB 앞단 배치
- [V] **Shield**: DDoS 공격 방어. Standard는 자동 적용됨
- [V] **ACM**: SSL 인증서 자동 갱신. Route 53 + ALB와 연동
- [V] **Security Groups vs NACLs**: 차이점 명확히 알아야 함
- [V] **VPC Peering**: VPC 간 프라이빗 통신

### 스토리지 & 백업 (우선순위: 낮음)
- [V] **EBS**: EC2 볼륨. IOPS, Throughput 타입별 차이
- [V] **EFS**: 여러 EC2에서 파일 공유. NFS 프로토콜
- [V] **S3 Glacier**: 장기 보관용. 비용 저렴하지만 복구 느림
- [V] **AWS Backup**: RDS, EBS 자동 백업 설정

### 모니터링 & 로깅 (우선순위: 높음)
- [V] **X-Ray**: 분산 추적. Lambda, ECS 호출 흐름 파악
- [V] **CloudWatch Logs Insights**: 로그 쿼리. SQL 비슷한 문법
- [V] **CloudWatch Alarms**: CPU, 메모리, 큐 깊이 알람 설정
- [V] **AWS Config**: 리소스 변경 추적. 컴플라이언스 체크

### 배포 & CI/CD (우선순위: 중간)
- [V] **CodePipeline**: GitHub Actions, Jenkins 대체 가능
- [V] **CodeBuild**: Docker 이미지 빌드, 테스트 실행
- [V] **CodeDeploy**: Blue-Green, Canary 배포 지원
- [V] **CodeCommit**: Git 저장소. GitHub/GitLab 대신 사용 가능

### 비용 & 거버넌스 (우선순위: 중간)
- [V] **Cost Explorer**: 비용 분석. 어디서 돈 나가는지 파악
- [V] **Budgets**: 예산 초과 시 알림
- [V] **Organizations**: 멀티 어카운트 관리. 개발/스테이징/프로덕션 분리
- [V] **SCP**: 조직 단위 정책. 특정 리전 사용 제한 등

## 백엔드 아키텍처

### API 설계 (우선순위: 높음)
- [ ] **API 버저닝**: URL 방식 vs Header 방식. 하위 호환성 유지 방법
- [ ] **GraphQL**: REST API 한계 있을 때. 단일 엔드포인트로 여러 리소스 조회
- [ ] **gRPC**: 내부 서비스 간 통신. HTTP/2 기반, Protobuf 사용
- [ ] **Rate Limiting**: Token Bucket, Leaky Bucket 알고리즘. Redis 기반 구현
- [ ] **Webhook**: 이벤트 발생 시 외부에 알림. Retry, Timeout 처리

### 캐싱 (우선순위: 높음)
- [V] **Cache-Aside**: 애플리케이션에서 캐시 직접 관리
- [V] **Write-Through**: 쓰기 시 캐시도 업데이트
- [V] **Write-Behind**: 쓰기를 캐시에만 하고 나중에 DB 반영
- [V] **캐시 일관성**: 분산 환경에서 캐시 동기화. Pub/Sub 활용
- [V] **캐시 무효화**: TTL, 수동 삭제, 태그 기반 무효화
- [V] **로컬 vs 분산 캐시**: Caffeine vs Redis. 사용 시점 구분

### 데이터베이스 심화 (우선순위: 높음)
- [V] **Connection Pool**: HikariCP 설정. maximumPoolSize, connectionTimeout
- [V] **Optimistic Lock**: 버전 번호 체크. 동시 수정 감지
- [V] **Pessimistic Lock**: SELECT FOR UPDATE. 데드락 주의
- [V] **파티셔닝**: Range, List, Hash. 테이블 크기 커질 때
- [V] **Query 최적화**: EXPLAIN ANALYZE. 인덱스 활용도 체크
- [V] **N+1 문제**: Fetch Join, @EntityGraph. Lazy Loading 주의
- [V] **격리 수준**: Read Committed, Repeatable Read. Phantom Read 차이

### 동시성 & 성능 (우선순위: 높음)
- [ ] **Thread Pool**: Core, Max 크기 결정. Queue 용량 설정
- [ ] **CompletableFuture**: 비동기 체인. thenApply, thenCompose 차이
- [ ] **Reactive**: WebFlux, Reactor. 높은 동시 연결 필요할 때
- [ ] **Backpressure**: 프로듀서가 컨슈머보다 빠를 때 제어
- [ ] **Graceful Shutdown**: 진행 중인 요청 완료 대기. SIGTERM 처리
- [ ] **GC 튜닝**: G1GC, ZGC 선택. Heap 크기, Young/Old 비율

### 보안 (우선순위: 높음)
- [ ] **JWT Refresh Token**: Access Token 짧게, Refresh Token 길게
- [ ] **Token Rotation**: Refresh Token 재발급 시 갱신
- [ ] **SSO**: SAML 2.0, OpenID Connect. 기업 환경 필수
- [ ] **API Gateway 보안**: Kong, Tyk, AWS API Gateway
- [ ] **CORS Preflight**: OPTIONS 요청 처리. withCredentials 설정
- [ ] **Input Validation**: Bean Validation, 커스텀 검증 로직

### 메시징 (우선순위: 높음)
- [ ] **Kafka 최적화**: batch.size, linger.ms, compression.type
- [ ] **Consumer Group**: 파티션 개수와 컨슈머 수 관계
- [ ] **RabbitMQ**: Direct, Fanout, Topic Exchange 차이
- [ ] **멱등성**: 메시지 ID 기반 중복 체크. Redis Set 활용
- [ ] **순서 보장**: Partition Key, Message Group ID 사용
- [ ] **Dead Letter**: 재시도 횟수 초과 시 별도 큐로 이동

### 모니터링 & 관찰성 (우선순위: 높음)
- [ ] **Distributed Tracing**: Jaeger, Zipkin, AWS X-Ray
- [ ] **Trace ID 전파**: HTTP Header, MDC 활용
- [ ] **커스텀 메트릭**: Micrometer, Prometheus Client
- [ ] **로그 집계**: ELK Stack, Grafana Loki
- [ ] **SLI/SLO/SLA**: 가용성 99.9%, 응답 시간 p95 < 200ms
- [ ] **알림 피로도**: 중요도 분류. 야간 알림 최소화

### 테스트 (우선순위: 중간)
- [ ] **Contract Testing**: 마이크로서비스 간 계약 검증
- [ ] **성능 테스트**: JMeter 스크립트, k6 시나리오
- [ ] **Chaos Engineering**: 네트워크 지연, 서비스 다운 시뮬레이션
- [ ] **E2E 테스트**: Selenium, Cypress. CI에 통합
- [ ] **테스트 커버리지**: 80% 목표는 의미 없음. 핵심 로직 위주

### 아키텍처 패턴 (우선순위: 중간)
- [ ] **Hexagonal Architecture**: 도메인 로직과 인프라 분리
- [ ] **Clean Architecture**: Usecase, Entity, Gateway 계층
- [ ] **BFF**: iOS/Android/Web 각각 다른 API
- [ ] **API Composition**: 여러 마이크로서비스 결과 합침
- [ ] **Strangler Fig**: 레거시 점진적 교체. Proxy 패턴 활용
- [ ] **Bulkhead**: 스레드 풀 분리. 장애 전파 차단

### 데이터 처리 (우선순위: 중간)
- [ ] **Batch Processing**: Spring Batch. Chunk 단위 처리
- [ ] **Job Scheduling**: Quartz, @Scheduled. 분산 환경 고려
- [ ] **ETL Pipeline**: Extract, Transform, Load. Airflow 활용
- [ ] **CDC**: Debezium, AWS DMS. 데이터 변경 캡처
- [ ] **Data Versioning**: Schema 변경 관리. Flyway, Liquibase

### 배포 (우선순위: 중간)
- [ ] **Service Mesh**: Istio, Linkerd. 트래픽 관리, 보안
- [ ] **Blue-Green**: 새 버전 배포 후 트래픽 전환. 롤백 빠름
- [ ] **Canary**: 일부 트래픽만 새 버전으로. 점진적 확대
- [ ] **Feature Flag**: LaunchDarkly, Unleash. 배포와 릴리스 분리
- [ ] **Container Security**: Trivy, Clair. 이미지 취약점 스캔

### 성능 최적화 (우선순위: 중간)
- [ ] **Connection Pool 튜닝**: 최적 크기는 CPU 코어 수 * 2 정도
- [ ] **Heap Dump 분석**: VisualVM, MAT. 메모리 누수 찾기
- [ ] **CPU 프로파일링**: async-profiler. 병목 메서드 찾기
- [ ] **HTTP/2**: 멀티플렉싱. 단일 연결로 여러 요청
- [ ] **압축**: Gzip, Brotli. 응답 크기 줄이기

### 도메인 설계 (우선순위: 낮음)
- [ ] **DDD**: Aggregate, Entity, Value Object 구분
- [ ] **Bounded Context**: 도메인 경계 설정. 서로 다른 용어 사용
- [ ] **Domain Event**: 도메인 로직에서 이벤트 발행
- [ ] **Aggregate Root**: 트랜잭션 경계. 일관성 보장 범위

### 장애 대응 (우선순위: 높음)
- [V] **Circuit Breaker**: Resilience4j. 연속 실패 시 회로 차단
- [V] **Retry**: Exponential Backoff. 1초, 2초, 4초, 8초...
- [V] **Timeout**: Connection, Read, Write 각각 설정
- [V] **Fallback**: 기본값 반환, 캐시 사용, 다른 서비스 호출
- [V] **Health Check**: Liveness(프로세스 살아있는지), Readiness(요청 받을 준비)

## 학습 순서 (실무 기준)

### 1개월 차: 인프라 기초
1. EKS + Service Mesh (Istio)
2. Kinesis + Kafka
3. X-Ray + Distributed Tracing
4. ElastiCache + 캐싱 전략

### 2개월 차: API & 보안
1. API Gateway 패턴 (Rate Limiting, Circuit Breaker)
2. JWT + SSO
3. gRPC
4. GraphQL

### 3개월 차: 성능 & 모니터링
1. 성능 테스트 (JMeter, k6)
2. 커스텀 메트릭 + SLI/SLO
3. Connection Pool 튜닝
4. GC 튜닝

### 4개월 차: 아키텍처 & 설계
1. DDD + Hexagonal Architecture
2. BFF + API Composition
3. Blue-Green + Canary 배포
4. Feature Flag

### 5개월 차: 비용 & 운영
1. AWS Cost Explorer
2. 장애 대응 패턴
3. Chaos Engineering
4. 로그 집계 + 분석

## 참고

실무에서 자주 쓰는 순서대로 정리했다. 모든 항목을 다 알 필요는 없다. 현재 팀에서 사용하는 기술 스택에 맞춰서 선택적으로 학습한다.

우선순위 '높음'은 반드시 알아야 하고, '중간'은 필요할 때 찾아보면 되고, '낮음'은 나중에 천천히 학습한다.

