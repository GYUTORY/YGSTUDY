---
title: Spring Batch
tags: [spring, batch, job, step, reader, writer, processor, chunk, partitioning, monitoring]
updated: 2026-03-30
---

# Spring Batch

## 개요

Spring Batch는 대용량 데이터를 배치 처리하는 프레임워크다. 수백만~수억 건의 데이터를 읽고, 가공하고, 저장하는 작업을 트랜잭션 관리, 재시도, 재시작 기능과 함께 제공한다.

```
배치 처리 사용 사례:
  - 매일 밤 정산 처리 (수백만 건 거래 집계)
  - 월말 보고서 생성
  - 데이터 마이그레이션 (레거시 → 신규 시스템)
  - CSV/XML 파일 일괄 처리
  - 대량 이메일/알림 발송
```

### 핵심 아키텍처

```
┌─────────────────────────────────────────┐
│                  Job                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐│
│  │  Step 1   │→│  Step 2   │→│  Step 3   ││
│  │ (데이터   │ │ (가공)    │ │ (결과    ││
│  │  읽기)    │ │           │ │  저장)   ││
│  └──────────┘ └──────────┘ └──────────┘│
└─────────────────────────────────────────┘

Step 내부 (Chunk 기반):
  ItemReader → ItemProcessor → ItemWriter
  (읽기)        (가공)          (쓰기)

  10건 읽기 → 10건 가공 → 10건 저장 (1 Chunk)
  10건 읽기 → 10건 가공 → 10건 저장 (1 Chunk)
  ...
```

---

## JobRepository와 메타데이터 테이블

Spring Batch는 Job 실행 상태를 DB에 저장한다. 이 메타데이터가 재시작, 중복 실행 방지, 실행 이력 조회의 근거가 된다.

### 메타데이터 테이블 구조

```
BATCH_JOB_INSTANCE
  └─ BATCH_JOB_EXECUTION (1:N)
       ├─ BATCH_JOB_EXECUTION_PARAMS
       ├─ BATCH_JOB_EXECUTION_CONTEXT
       └─ BATCH_STEP_EXECUTION (1:N)
            └─ BATCH_STEP_EXECUTION_CONTEXT
```

| 테이블 | 역할 |
|--------|------|
| `BATCH_JOB_INSTANCE` | Job 이름 + JobParameters 조합으로 식별되는 논리적 Job 단위. 같은 파라미터로 두 번 실행하면 같은 Instance다. |
| `BATCH_JOB_EXECUTION` | Instance의 실제 실행 기록. 실패 후 재실행하면 같은 Instance에 새로운 Execution이 생긴다. |
| `BATCH_JOB_EXECUTION_PARAMS` | 실행 시 전달된 파라미터. `identifying=true`인 파라미터만 Instance 식별에 사용된다. |
| `BATCH_STEP_EXECUTION` | 각 Step의 실행 기록. `read_count`, `write_count`, `commit_count`, `rollback_count` 등 처리 통계가 들어 있다. |
| `BATCH_JOB_EXECUTION_CONTEXT` / `BATCH_STEP_EXECUTION_CONTEXT` | ExecutionContext를 직렬화해서 저장. 재시작 시 이전 상태를 복원하는 데 쓴다. |

실무에서 자주 조회하는 쿼리:

```sql
-- 실패한 Job 목록
SELECT ji.JOB_NAME, je.START_TIME, je.END_TIME, je.STATUS, je.EXIT_CODE
FROM BATCH_JOB_EXECUTION je
JOIN BATCH_JOB_INSTANCE ji ON je.JOB_INSTANCE_ID = ji.JOB_INSTANCE_ID
WHERE je.STATUS = 'FAILED'
ORDER BY je.START_TIME DESC;

-- 특정 Job의 Step별 처리 건수
SELECT se.STEP_NAME, se.READ_COUNT, se.WRITE_COUNT, se.SKIP_COUNT,
       se.STATUS, se.EXIT_MESSAGE
FROM BATCH_STEP_EXECUTION se
JOIN BATCH_JOB_EXECUTION je ON se.JOB_EXECUTION_ID = je.JOB_EXECUTION_ID
WHERE je.JOB_EXECUTION_ID = ?;
```

메타데이터 테이블 스키마는 `spring-batch-core` JAR 안에 DB별 DDL이 들어 있다. Spring Boot를 쓰면 `spring.batch.jdbc.initialize-schema=always`로 자동 생성할 수 있는데, 운영 환경에서는 `never`로 두고 직접 관리하는 게 안전하다. 스키마 자동 생성이 기존 테이블을 날리는 사고가 가끔 일어난다.

---

## 재시작(Restart) 동작 원리

Spring Batch의 재시작은 `BATCH_STEP_EXECUTION_CONTEXT`에 저장된 상태를 기반으로 동작한다.

### 동작 흐름

1. Job이 실패하면 `BATCH_JOB_EXECUTION`의 STATUS가 `FAILED`로 남는다.
2. 같은 JobParameters로 다시 실행하면, 같은 `JOB_INSTANCE`에 새로운 `JOB_EXECUTION`이 생긴다.
3. 이미 `COMPLETED`된 Step은 건너뛴다. (`allowStartIfComplete(false)`가 기본값)
4. `FAILED`된 Step부터 다시 시작하는데, chunk 기반 Step은 마지막으로 커밋된 지점 이후부터 읽기를 재개한다.

```
첫 실행:
  Step1(COMPLETED) → Step2(100건 중 60건 처리 후 FAILED)

재시작:
  Step1(SKIP - 이미 완료) → Step2(61건째부터 재개)
```

주의할 점:

- `JdbcPagingItemReader`는 `ExecutionContext`에 현재 페이지 정보를 저장하므로 재시작이 정확하게 동작한다. `JdbcCursorItemReader`도 `read_count`를 기반으로 재시작한다.
- `ItemReader`가 `ItemStream`을 구현해야 재시작이 가능하다. 커스텀 Reader를 만들 때 `open()`, `update()`, `close()`를 구현하지 않으면 재시작 시 처음부터 다시 읽는다.
- `RunIdIncrementer`를 쓰면 매 실행마다 `run.id`가 증가해서 항상 새로운 Instance가 생긴다. 재시작이 필요한 Job에는 쓰지 않는 게 맞다.

```java
// 재시작 가능한 Job - RunIdIncrementer를 쓰지 않는다
@Bean
public Job restartableJob(JobRepository jobRepository, Step step) {
    return new JobBuilder("restartableJob", jobRepository)
        .start(step)
        .build();
}

// 재시작 불가한 Job - preventRestart() 명시
@Bean
public Job oneTimeJob(JobRepository jobRepository, Step step) {
    return new JobBuilder("oneTimeJob", jobRepository)
        .preventRestart()
        .start(step)
        .build();
}
```

---

## Chunk vs Tasklet 선택 기준

### Chunk 기반

데이터를 Reader → Processor → Writer 파이프라인으로 처리한다. 대량 데이터를 일정 단위(chunk size)로 읽고, 가공하고, 쓰는 패턴에 적합하다.

- 트랜잭션이 chunk 단위로 커밋된다. 1000건 처리 중 500건째에서 실패하면 이전 커밋된 chunk까지는 보존된다.
- 재시작 시 마지막 커밋 지점부터 재개할 수 있다.
- Skip, Retry 같은 fault-tolerant 기능이 chunk 레벨에서 동작한다.

### Tasklet 기반

하나의 `execute()` 메서드에서 작업 전체를 처리한다. Reader/Writer 패턴이 맞지 않는 작업에 쓴다.

```java
// Tasklet이 적합한 경우: 파일 정리, 테이블 TRUNCATE, 외부 API 호출
@Bean
public Step archiveStep(JobRepository jobRepository, PlatformTransactionManager tx) {
    return new StepBuilder("archiveStep", jobRepository)
        .tasklet((contribution, chunkContext) -> {
            // 30일 이전 로그 파일 삭제
            Path logDir = Path.of("/var/log/batch");
            try (var files = Files.list(logDir)) {
                files.filter(f -> isOlderThan(f, 30))
                     .forEach(f -> {
                         try { Files.delete(f); }
                         catch (IOException e) { log.warn("삭제 실패: {}", f, e); }
                     });
            }
            return RepeatStatus.FINISHED;
        }, tx)
        .build();
}
```

### 판단 기준

| 상황 | 선택 |
|------|------|
| DB 테이블에서 대량 데이터를 읽어 가공 후 저장 | Chunk |
| CSV/파일에서 읽어 DB에 적재 | Chunk |
| 임시 파일 삭제, 디렉토리 정리 | Tasklet |
| 외부 API 한 번 호출해서 결과 저장 | Tasklet |
| 테이블 TRUNCATE 후 데이터 재적재 | TRUNCATE는 Tasklet, 재적재는 Chunk (Step 분리) |
| 처리 건수가 수십 건 이하로 작고, 파이프라인이 과한 경우 | Tasklet |

Chunk를 쓸지 Tasklet을 쓸지 애매하면 Chunk를 쓰는 게 낫다. 나중에 데이터가 늘어도 chunk size 조정으로 대응할 수 있고, 재시작/Skip/Retry 기능이 기본으로 따라온다.

---

## JpaCursorItemReader vs JpaPagingItemReader

둘 다 JPA로 데이터를 읽는 Reader지만, 내부 동작 방식이 다르다.

### JpaPagingItemReader

```java
@Bean
public JpaPagingItemReader<Order> pagingReader(EntityManagerFactory emf) {
    return new JpaPagingItemReaderBuilder<Order>()
        .name("orderPagingReader")
        .entityManagerFactory(emf)
        .queryString("SELECT o FROM Order o WHERE o.status = 'PENDING' ORDER BY o.id")
        .pageSize(100)
        .build();
}
```

- 내부적으로 `LIMIT/OFFSET` (또는 DB별 동등 구문)을 사용한다.
- 페이지마다 새로운 쿼리를 실행한다. 1페이지는 `OFFSET 0 LIMIT 100`, 2페이지는 `OFFSET 100 LIMIT 100`.
- 페이지를 넘길 때마다 EntityManager를 clear하므로 영속성 컨텍스트가 매 페이지 초기화된다.
- 문제: 처리 중에 데이터가 변경되면(예: status를 UPDATE하면) OFFSET이 밀린다. 100건 읽고 그 중 일부를 UPDATE했는데 다음 페이지 OFFSET 계산 시 이미 변경된 행이 빠져서 일부 행을 건너뛰는 현상이 생긴다.

### JpaCursorItemReader

```java
@Bean
public JpaCursorItemReader<Order> cursorReader(EntityManagerFactory emf) {
    return new JpaCursorItemReaderBuilder<Order>()
        .name("orderCursorReader")
        .entityManagerFactory(emf)
        .queryString("SELECT o FROM Order o WHERE o.status = 'PENDING' ORDER BY o.id")
        .build();
}
```

- 쿼리를 한 번만 실행하고, JDBC `ResultSet`을 커서로 순회한다.
- DB 커넥션을 Step이 끝날 때까지 유지한다.
- OFFSET 문제가 없다. 커서가 결과 셋 위에서 한 행씩 이동하므로 데이터 변경에 영향을 받지 않는다.
- 대신 DB 커넥션을 오래 잡고 있으므로, 처리 시간이 긴 배치에서는 커넥션 타임아웃을 주의해야 한다.

### 선택 기준

| 조건 | 선택 |
|------|------|
| 처리 도중 읽은 데이터를 UPDATE하는 경우 (status 변경 등) | `JpaCursorItemReader` — Paging은 OFFSET 밀림 문제가 있다 |
| 멀티 스레드 Step에서 사용하는 경우 | `JpaPagingItemReader` — Cursor는 thread-safe하지 않다 |
| 데이터가 수천만 건 이상이고 커넥션 점유 시간이 길어지는 경우 | `JpaPagingItemReader` — Cursor는 커넥션을 Step 끝까지 잡는다 |
| 데이터 정합성이 중요한 정산/금융 배치 | `JpaCursorItemReader` — 행 누락이 없다 |

Paging Reader에서 OFFSET 밀림을 우회하는 방법도 있다. 처리 완료된 데이터를 WHERE 조건으로 제외하지 말고, 별도 컬럼(예: `processed_at`)에 기록한 뒤 배치 완료 후 한꺼번에 처리하는 식이다. 하지만 이런 우회가 필요한 시점이면 Cursor를 쓰는 게 단순하다.

---

## 대용량 처리 시 메모리 이슈와 튜닝

### OOM이 발생하는 패턴

**1. pageSize와 chunkSize 불일치**

```java
// 문제: pageSize=10, chunkSize=1000
// → 1 chunk를 채우려고 100번의 쿼리를 실행한다
.<Order, Order>chunk(1000, tx)
.reader(pagingReader())  // pageSize=10
```

pageSize와 chunkSize가 다르면 비효율적이다. pageSize가 작으면 쿼리 횟수가 늘고, chunkSize가 pageSize보다 크면 chunk를 채울 때까지 여러 번 읽기를 반복한다. 둘을 같은 값으로 맞추는 게 기본이다.

**2. JPA 영속성 컨텍스트에 엔티티가 쌓이는 문제**

`JpaCursorItemReader`는 하나의 EntityManager를 Step 동안 유지한다. chunk마다 영속성 컨텍스트를 비우지 않으면 읽은 엔티티가 계속 쌓여서 OOM이 난다.

```java
// Writer에서 명시적으로 EntityManager를 clear
@Bean
public ItemWriter<Order> orderWriter(EntityManagerFactory emf) {
    JpaItemWriter<Order> writer = new JpaItemWriter<>();
    writer.setEntityManagerFactory(emf);
    // Writer 실행 후 clear하는 래퍼
    return items -> {
        writer.write(items);
        emf.createEntityManager().clear();  // 이건 잘못된 방법
    };
}
```

위 코드는 새 EntityManager를 만들어서 clear하므로 의미가 없다. 실제로는 `@Modifying(clearAutomatically = true)` 또는 `ChunkListener`에서 처리해야 한다.

```java
// ChunkListener에서 영속성 컨텍스트 clear
@Component
public class EntityManagerClearListener implements ChunkListener {
    @PersistenceContext
    private EntityManager em;

    @Override
    public void afterChunk(ChunkContext context) {
        em.clear();
    }
}
```

**3. fetchSize 미설정**

JDBC 레벨에서 `fetchSize`를 설정하지 않으면, 드라이버 기본값이 적용된다. MySQL의 기본 fetchSize는 전체 결과를 한 번에 메모리에 올리는 방식(`Integer.MIN_VALUE`로 스트리밍 모드 전환 필요)이고, PostgreSQL은 기본값이 0(전체 패치)이다.

```java
// Hibernate hint로 fetchSize 설정
@Bean
public JpaCursorItemReader<Order> cursorReader(EntityManagerFactory emf) {
    JpaCursorItemReader<Order> reader = new JpaCursorItemReaderBuilder<Order>()
        .name("orderCursorReader")
        .entityManagerFactory(emf)
        .queryString("SELECT o FROM Order o WHERE o.status = 'PENDING'")
        .build();

    // Hibernate hint 설정
    Map<String, Object> hints = new HashMap<>();
    hints.put("org.hibernate.fetchSize", 100);
    reader.setHints(hints);
    return reader;
}

// JdbcCursorItemReader에서 fetchSize 설정
@Bean
public JdbcCursorItemReader<Order> jdbcCursorReader(DataSource ds) {
    return new JdbcCursorItemReaderBuilder<Order>()
        .name("jdbcCursorReader")
        .dataSource(ds)
        .sql("SELECT id, amount, status FROM orders WHERE status = 'PENDING'")
        .fetchSize(100)
        .rowMapper(new BeanPropertyRowMapper<>(Order.class))
        .build();
}
```

### 튜닝 정리

| 항목 | 설정 | 권장값 |
|------|------|--------|
| `chunkSize` | Step 설정 | 100~1000. 트랜잭션 크기와 메모리 사이에서 조절 |
| `pageSize` | PagingItemReader | chunkSize와 동일하게 |
| `fetchSize` | JDBC/Hibernate | 100~500. DB 커넥션 메모리와 네트워크 왕복 횟수 사이에서 조절 |

chunkSize가 너무 크면 하나의 트랜잭션이 길어져서 DB Lock 경합이 심해진다. 너무 작으면 커밋 횟수가 늘어서 I/O 오버헤드가 커진다. 100~500 사이에서 시작해서 처리 시간과 메모리를 모니터링하면서 조절하는 게 현실적이다.

---

## 파티셔닝(Partitioning) 구현

파티셔닝은 데이터를 여러 구간으로 나눠서 각 구간을 별도 Step으로 병렬 처리하는 방식이다. 멀티 스레드 Step과 달리 Reader가 thread-safe할 필요가 없다. 각 파티션이 독립적인 Reader를 가지기 때문이다.

### Partitioner 구현

```java
@Component
public class OrderRangePartitioner implements Partitioner {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Override
    public Map<String, ExecutionContext> partition(int gridSize) {
        Long min = jdbcTemplate.queryForObject(
            "SELECT MIN(id) FROM orders WHERE status = 'PENDING'", Long.class);
        Long max = jdbcTemplate.queryForObject(
            "SELECT MAX(id) FROM orders WHERE status = 'PENDING'", Long.class);

        if (min == null || max == null) return Map.of();

        long range = (max - min) / gridSize + 1;
        Map<String, ExecutionContext> partitions = new HashMap<>();

        for (int i = 0; i < gridSize; i++) {
            ExecutionContext ctx = new ExecutionContext();
            long start = min + (range * i);
            long end = Math.min(start + range - 1, max);
            ctx.putLong("minId", start);
            ctx.putLong("maxId", end);
            partitions.put("partition" + i, ctx);
        }
        return partitions;
    }
}
```

### 파티션 Step 구성

```java
@Configuration
public class PartitionedJobConfig {

    @Bean
    public Job partitionedJob(JobRepository jobRepository, Step managerStep) {
        return new JobBuilder("partitionedJob", jobRepository)
            .start(managerStep)
            .build();
    }

    @Bean
    public Step managerStep(JobRepository jobRepository,
                            OrderRangePartitioner partitioner,
                            Step workerStep) {
        return new StepBuilder("managerStep", jobRepository)
            .partitioner("workerStep", partitioner)
            .step(workerStep)
            .gridSize(8)
            .taskExecutor(batchTaskExecutor())
            .build();
    }

    @Bean
    @StepScope
    public JdbcPagingItemReader<Order> partitionedReader(
            DataSource dataSource,
            @Value("#{stepExecutionContext['minId']}") Long minId,
            @Value("#{stepExecutionContext['maxId']}") Long maxId) {
        return new JdbcPagingItemReaderBuilder<Order>()
            .name("partitionedReader")
            .dataSource(dataSource)
            .selectClause("SELECT id, amount, status")
            .fromClause("FROM orders")
            .whereClause("WHERE id BETWEEN :minId AND :maxId AND status = 'PENDING'")
            .sortKeys(Map.of("id", Order.ASCENDING))
            .pageSize(500)
            .parameterValues(Map.of("minId", minId, "maxId", maxId))
            .rowMapper(new BeanPropertyRowMapper<>(Order.class))
            .build();
    }

    @Bean
    public Step workerStep(JobRepository jobRepository,
                           PlatformTransactionManager tx) {
        return new StepBuilder("workerStep", jobRepository)
            .<Order, Order>chunk(500, tx)
            .reader(partitionedReader(null, null, null))
            .processor(orderProcessor())
            .writer(orderWriter())
            .build();
    }

    @Bean
    public TaskExecutor batchTaskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(8);
        executor.setMaxPoolSize(8);
        executor.setThreadNamePrefix("batch-partition-");
        return executor;
    }
}
```

`@StepScope`이 핵심이다. 파티션마다 별도의 Reader 인스턴스가 생기고, `stepExecutionContext`에서 자신의 범위(minId, maxId)를 받아서 해당 구간만 읽는다.

gridSize는 CPU 코어 수와 DB 커넥션 풀 크기를 고려해서 정한다. gridSize가 8이면 동시에 8개 커넥션을 쓰므로, 커넥션 풀이 10개밖에 없으면 나머지 서비스에서 커넥션을 못 얻는 사고가 난다.

---

## 원격 청킹(Remote Chunking)

파티셔닝은 데이터를 구간별로 나누는 방식이지만, 원격 청킹은 읽기(Master)와 쓰기(Worker)를 물리적으로 다른 서버에서 처리한다.

```
┌──────────┐    메시지 큐    ┌──────────┐
│  Master   │ ──────────→ │  Worker   │
│ (Reader)  │  items 전송   │ (Processor│
│           │ ←────────── │  + Writer)│
│           │  완료 응답    │           │
└──────────┘              └──────────┘
```

Master가 데이터를 읽어서 메시지 큐(RabbitMQ, ActiveMQ 등)로 보내고, Worker가 받아서 가공/저장한다. 읽기는 빠르지만 쓰기가 병목인 경우에 Worker를 수평 확장할 수 있다.

### Master 설정

```java
@Configuration
public class RemoteChunkingMasterConfig {

    @Bean
    public Job remoteChunkingJob(JobRepository jobRepository, Step masterStep) {
        return new JobBuilder("remoteChunkingJob", jobRepository)
            .start(masterStep)
            .build();
    }

    @Bean
    public TaskletStep masterStep(RemoteChunkingManagerStepBuilderFactory managerFactory) {
        return managerFactory.get("masterStep")
            .<Order, Order>chunk(100)
            .reader(orderReader())
            .outputChannel(outboundChannel())   // Worker로 보내는 채널
            .inputChannel(inboundChannel())     // Worker 응답 받는 채널
            .build();
    }

    @Bean
    public DirectChannel outboundChannel() {
        return new DirectChannel();
    }

    @Bean
    public QueueChannel inboundChannel() {
        return new QueueChannel();
    }

    // RabbitMQ로 outbound 연결
    @Bean
    @ServiceActivator(inputChannel = "outboundChannel")
    public AmqpOutboundEndpoint amqpOutbound(AmqpTemplate amqpTemplate) {
        AmqpOutboundEndpoint endpoint = new AmqpOutboundEndpoint(amqpTemplate);
        endpoint.setOutputChannel(inboundChannel());
        endpoint.setRoutingKey("batch.requests");
        return endpoint;
    }
}
```

### Worker 설정

```java
@Configuration
public class RemoteChunkingWorkerConfig {

    @Bean
    public IntegrationFlow workerFlow(
            RemoteChunkingWorkerBuilder<Order, Order> workerBuilder) {
        return workerBuilder
            .itemProcessor(orderProcessor())
            .itemWriter(orderWriter())
            .inputChannel(workerInboundChannel())
            .outputChannel(workerOutboundChannel())
            .build();
    }
}
```

실무에서 원격 청킹을 도입한 경우는 드물다. 대부분의 배치는 파티셔닝으로 충분하고, 원격 청킹은 네트워크 직렬화/역직렬화 오버헤드와 메시지 큐 관리 부담이 생긴다. Writer가 외부 API 호출처럼 I/O 바운드 작업이라서 Worker를 늘려야 하는 경우에만 고려할 만하다.

---

## 배치 테스트 작성법

### @SpringBatchTest

Spring Batch 4.1부터 `@SpringBatchTest`가 도입됐다. 테스트에 필요한 `JobLauncherTestUtils`, `JobRepositoryTestUtils`를 자동으로 빈 등록해준다.

```java
@SpringBatchTest
@SpringBootTest
class OrderBatchJobTest {

    @Autowired
    private JobLauncherTestUtils jobLauncherTestUtils;

    @Autowired
    private JobRepositoryTestUtils jobRepositoryTestUtils;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @AfterEach
    void cleanup() {
        // 메타데이터 테이블 정리
        jobRepositoryTestUtils.removeJobExecutions();
    }

    @Test
    void 주문_정산_Job_정상_실행() throws Exception {
        // given - 테스트 데이터 준비
        jdbcTemplate.update(
            "INSERT INTO orders (id, amount, status) VALUES (?, ?, ?)",
            1L, 10000, "PENDING");

        JobParameters params = new JobParametersBuilder()
            .addString("date", "2026-03-30")
            .toJobParameters();

        // when
        JobExecution execution = jobLauncherTestUtils.launchJob(params);

        // then
        assertThat(execution.getStatus()).isEqualTo(BatchStatus.COMPLETED);
        assertThat(execution.getExitStatus()).isEqualTo(ExitStatus.COMPLETED);

        // Step별 검증
        StepExecution stepExecution = execution.getStepExecutions()
            .iterator().next();
        assertThat(stepExecution.getReadCount()).isEqualTo(1);
        assertThat(stepExecution.getWriteCount()).isEqualTo(1);

        // DB 결과 검증
        Integer count = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM orders WHERE status = 'COMPLETED'", Integer.class);
        assertThat(count).isEqualTo(1);
    }
}
```

### Step 단위 테스트

Job 전체가 아닌 특정 Step만 실행할 수 있다. Step이 여러 개인 Job에서 한 Step만 수정했을 때 빠르게 검증하는 데 쓴다.

```java
@Test
void 정산_Step만_테스트() {
    JobExecution execution = jobLauncherTestUtils.launchStep("settlementStep");

    assertThat(execution.getStepExecutions()).hasSize(1);
    StepExecution step = execution.getStepExecutions().iterator().next();
    assertThat(step.getExitStatus().getExitCode()).isEqualTo("COMPLETED");
}
```

### Reader/Processor 단위 테스트

Reader나 Processor를 개별로 테스트하려면 직접 인스턴스를 만들어서 호출한다.

```java
@Test
void Processor_null_반환_시_필터링() {
    OrderProcessor processor = new OrderProcessor();

    // 유효한 주문
    Order valid = new Order(1L, 10000, "PENDING");
    assertThat(processor.process(valid)).isNotNull();

    // 금액이 0인 주문은 필터링
    Order invalid = new Order(2L, 0, "PENDING");
    assertThat(processor.process(invalid)).isNull();
}
```

테스트 DB는 H2 인메모리를 쓰는 경우가 많은데, 운영 DB와 SQL 방언이 달라서 테스트에서 통과하고 운영에서 실패하는 경우가 있다. Testcontainers로 실제 DB를 띄우는 게 더 안전하다.

---

## 운영 환경에서 Job 중복 실행 방지

같은 Job이 여러 서버에서 동시에 실행되면 데이터가 꼬인다. 방지 방법은 여러 가지가 있다.

### 1. JobRepository의 기본 동작 활용

같은 `JobParameters`로 이미 `COMPLETED`된 `JOB_INSTANCE`가 있으면, Spring Batch가 `JobInstanceAlreadyCompleteException`을 던진다. 같은 파라미터로 두 번 실행 자체가 안 된다.

하지만 `STARTED` 상태인 Job에 대해서는 막지 않는다. 서버 A에서 Job이 `STARTED` 상태인데, 서버 B에서 같은 Job을 실행하면 새로운 `JOB_EXECUTION`이 생겨서 중복 실행된다.

### 2. DB Lock 활용

```java
@Component
public class JobExecutionGuard {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    /**
     * SELECT FOR UPDATE로 잠금 획득을 시도한다.
     * 다른 서버가 이미 실행 중이면 잠금 획득에 실패한다.
     */
    public boolean tryAcquireLock(String jobName) {
        try {
            // advisory lock 또는 전용 lock 테이블 사용
            jdbcTemplate.queryForObject(
                "SELECT GET_LOCK(?, 0)",  // MySQL advisory lock, 0초 대기
                Integer.class, "BATCH_" + jobName);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    public void releaseLock(String jobName) {
        jdbcTemplate.queryForObject(
            "SELECT RELEASE_LOCK(?)", Integer.class, "BATCH_" + jobName);
    }
}
```

### 3. 스케줄러 레벨에서 제어

Jenkins, Kubernetes CronJob 등 외부 스케줄러를 쓰면 스케줄러 자체에서 동시 실행을 막는다.

```yaml
# Kubernetes CronJob - concurrencyPolicy로 제어
apiVersion: batch/v1
kind: CronJob
metadata:
  name: order-settlement
spec:
  schedule: "0 2 * * *"
  concurrencyPolicy: Forbid   # 이전 Job이 실행 중이면 새 Job을 만들지 않는다
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: batch
              image: myapp:latest
              command: ["java", "-jar", "app.jar", "--job.name=settlementJob"]
          restartPolicy: OnFailure
```

### 4. ShedLock 사용

`@Scheduled`로 배치를 트리거하는 경우, ShedLock이 DB 기반 분산 락을 제공한다.

```java
@Scheduled(cron = "0 0 2 * * *")
@SchedulerLock(name = "settlementJob", lockAtMostFor = "PT2H", lockAtLeastFor = "PT5M")
public void runSettlement() throws Exception {
    jobLauncher.run(settlementJob, createParams());
}
```

실무에서는 Kubernetes CronJob + `concurrencyPolicy: Forbid` 조합이 가장 단순하다. 애플리케이션 레벨에서 분산 락을 관리하는 것보다 인프라 레벨에서 막는 게 실수할 여지가 적다.

---

## Spring Boot 3.x 변경사항

### 자동 실행 비활성화 (가장 큰 변경)

Spring Boot 2.x에서는 애플리케이션 시작 시 등록된 Job이 자동으로 실행됐다. `spring.batch.job.enabled=false`로 끄지 않으면 서버 띄울 때마다 배치가 돌아가는 사고가 종종 있었다.

Spring Boot 3.x부터는 **자동 실행이 기본 비활성화**다. Job을 실행하려면 명시적으로 설정해야 한다.

```properties
# Spring Boot 3.x - 자동 실행을 켜려면 명시
spring.batch.job.enabled=true

# 특정 Job만 실행
spring.batch.job.name=settlementJob
```

### @EnableBatchProcessing 동작 변경

Spring Boot 3.x에서는 `@EnableBatchProcessing`을 붙이면 Spring Boot의 자동 구성이 비활성화된다. Boot 2.x에서는 이 어노테이션을 붙이든 안 붙이든 자동 구성이 동작했다.

```java
// Spring Boot 3.x - @EnableBatchProcessing을 빼야 자동 구성이 동작한다
@SpringBootApplication
// @EnableBatchProcessing  // 이거 빼야 한다
public class BatchApplication {
    public static void main(String[] args) {
        SpringApplication.run(BatchApplication.class, args);
    }
}
```

`@EnableBatchProcessing`을 쓰면 `JobRepository`, `JobLauncher` 등을 직접 설정해야 한다. 대부분의 경우 빼는 게 맞다.

### JobBuilderFactory/StepBuilderFactory 제거

Spring Batch 5.0(Spring Boot 3.x 기본)에서 `JobBuilderFactory`와 `StepBuilderFactory`가 deprecated 후 제거됐다. 대신 `JobBuilder`와 `StepBuilder`를 직접 사용한다.

```java
// Before (Spring Batch 4.x)
@Autowired
private JobBuilderFactory jobBuilderFactory;
@Autowired
private StepBuilderFactory stepBuilderFactory;

@Bean
public Job myJob() {
    return jobBuilderFactory.get("myJob")
        .start(myStep())
        .build();
}

// After (Spring Batch 5.x)
@Bean
public Job myJob(JobRepository jobRepository) {
    return new JobBuilder("myJob", jobRepository)
        .start(myStep())
        .build();
}

@Bean
public Step myStep(JobRepository jobRepository, PlatformTransactionManager tx) {
    return new StepBuilder("myStep", jobRepository)
        .<Order, Order>chunk(100, tx)
        .reader(reader())
        .writer(writer())
        .build();
}
```

### 기타 변경사항

- `JobExplorer`, `JobOperator`의 인터페이스 시그니처가 변경됐다.
- 메타데이터 테이블 DDL에 `BATCH_JOB_EXECUTION`의 `CREATE_TIME` 컬럼이 `NOT NULL`로 변경됐다. 마이그레이션 시 기존 데이터에 기본값을 넣어야 한다.
- `@EnableBatchProcessing`의 `dataSourceRef`, `transactionManagerRef` 속성이 추가돼서 멀티 데이터소스 환경에서 배치 전용 데이터소스를 지정할 수 있다.

---

## 배치 모니터링

Spring Batch Admin은 오래전에 deprecated됐다. 현재 사용할 수 있는 대안들이다.

### Spring Cloud Data Flow

Spring 공식 배치 모니터링 도구다. 배치 Job 실행 이력, 상태, Step별 통계를 대시보드로 볼 수 있다. 하지만 설치/운영이 무겁다. 배치 모니터링만을 위해 도입하기에는 오버스펙인 경우가 많다.

### Micrometer + Grafana

Spring Batch는 Micrometer 메트릭을 지원한다. `spring.batch.job.enabled`와 함께 Actuator를 켜면 Job/Step 실행 메트릭이 자동으로 수집된다.

```properties
# application.properties
management.endpoints.web.exposure.include=health,metrics,prometheus
```

수집되는 메트릭:

```
spring.batch.job (tag: name, status)
  - 실행 횟수, 소요 시간

spring.batch.job.active
  - 현재 실행 중인 Job 수

spring.batch.step (tag: name, status)
  - Step별 실행 시간

spring.batch.item.read / spring.batch.item.process / spring.batch.item.write
  - 읽기/가공/쓰기 건수와 소요 시간
```

Prometheus로 수집하고 Grafana 대시보드에서 시각화하는 구조가 일반적이다.

### 직접 구현 (실무에서 가장 흔한 방식)

메타데이터 테이블을 직접 조회하는 관리 페이지를 만드는 팀이 많다. 복잡한 모니터링 도구를 도입하는 것보다 간단하고, 필요한 정보만 볼 수 있다.

```java
@RestController
@RequestMapping("/admin/batch")
public class BatchMonitorController {

    @Autowired
    private JobExplorer jobExplorer;

    @GetMapping("/jobs/{jobName}/executions")
    public List<JobExecutionInfo> getExecutions(@PathVariable String jobName,
                                                 @RequestParam(defaultValue = "10") int count) {
        List<JobInstance> instances = jobExplorer.findJobInstancesByJobName(jobName, 0, count);

        return instances.stream()
            .flatMap(i -> jobExplorer.getJobExecutions(i).stream())
            .map(e -> new JobExecutionInfo(
                e.getId(),
                e.getStatus().toString(),
                e.getStartTime(),
                e.getEndTime(),
                e.getStepExecutions().stream()
                    .map(s -> new StepInfo(s.getStepName(), s.getReadCount(),
                        s.getWriteCount(), s.getSkipCount()))
                    .toList()
            ))
            .toList();
    }
}
```

배치 실패 시 알림은 `JobExecutionListener`에서 Slack/이메일로 보내는 게 기본이다.

```java
@Component
public class JobFailureNotifier implements JobExecutionListener {

    @Override
    public void afterJob(JobExecution jobExecution) {
        if (jobExecution.getStatus() == BatchStatus.FAILED) {
            String message = String.format("[배치 실패] %s - %s\n시작: %s\n종료: %s\n원인: %s",
                jobExecution.getJobInstance().getJobName(),
                jobExecution.getStatus(),
                jobExecution.getStartTime(),
                jobExecution.getEndTime(),
                jobExecution.getAllFailureExceptions().stream()
                    .map(Throwable::getMessage)
                    .collect(Collectors.joining(", ")));

            slackClient.send("#batch-alerts", message);
        }
    }
}
```

---

## 핵심 구성 요소

### Job과 Step

```java
@Configuration
public class UserMigrationJobConfig {

    @Bean
    public Job userMigrationJob(JobRepository jobRepository, Step migrationStep) {
        return new JobBuilder("userMigrationJob", jobRepository)
            .incrementer(new RunIdIncrementer())
            .start(migrationStep)
            .build();
    }

    @Bean
    public Step migrationStep(JobRepository jobRepository,
                               PlatformTransactionManager transactionManager) {
        return new StepBuilder("migrationStep", jobRepository)
            .<OldUser, NewUser>chunk(100, transactionManager)
            .reader(oldUserReader())
            .processor(userProcessor())
            .writer(newUserWriter())
            .faultTolerant()
            .retryLimit(3)
            .retry(DataAccessException.class)
            .skipLimit(10)
            .skip(ValidationException.class)
            .build();
    }
}
```

### ItemReader

```java
// DB에서 읽기 (JdbcPagingItemReader)
@Bean
public JdbcPagingItemReader<OldUser> oldUserReader() {
    return new JdbcPagingItemReaderBuilder<OldUser>()
        .name("oldUserReader")
        .dataSource(dataSource)
        .selectClause("SELECT id, name, email, created_at")
        .fromClause("FROM old_users")
        .whereClause("WHERE migrated = false")
        .sortKeys(Map.of("id", Order.ASCENDING))
        .pageSize(100)
        .rowMapper(new BeanPropertyRowMapper<>(OldUser.class))
        .build();
}

// CSV 파일에서 읽기
@Bean
public FlatFileItemReader<UserCsv> csvReader() {
    return new FlatFileItemReaderBuilder<UserCsv>()
        .name("csvReader")
        .resource(new ClassPathResource("users.csv"))
        .linesToSkip(1)
        .delimited()
        .names("name", "email", "age")
        .targetType(UserCsv.class)
        .build();
}
```

### ItemProcessor

```java
@Component
public class UserProcessor implements ItemProcessor<OldUser, NewUser> {

    @Override
    public NewUser process(OldUser item) {
        // null 반환 시 해당 항목 스킵
        if (!isValid(item)) return null;

        return NewUser.builder()
            .name(item.getName().trim())
            .email(item.getEmail().toLowerCase())
            .status("ACTIVE")
            .migratedAt(LocalDateTime.now())
            .build();
    }
}

// 여러 Processor 체이닝
@Bean
public CompositeItemProcessor<OldUser, NewUser> compositeProcessor() {
    return new CompositeItemProcessorBuilder<OldUser, NewUser>()
        .delegates(List.of(
            validationProcessor(),
            transformProcessor(),
            enrichmentProcessor()
        ))
        .build();
}
```

### ItemWriter

```java
// DB에 쓰기 (JPA)
@Bean
public JpaItemWriter<NewUser> jpaWriter() {
    JpaItemWriter<NewUser> writer = new JpaItemWriter<>();
    writer.setEntityManagerFactory(entityManagerFactory);
    return writer;
}

// JDBC 배치 쓰기
@Bean
public JdbcBatchItemWriter<NewUser> jdbcWriter() {
    return new JdbcBatchItemWriterBuilder<NewUser>()
        .dataSource(dataSource)
        .sql("INSERT INTO new_users (name, email, status) VALUES (:name, :email, :status)")
        .beanMapped()
        .build();
}

// CSV 파일 쓰기
@Bean
public FlatFileItemWriter<NewUser> csvWriter() {
    return new FlatFileItemWriterBuilder<NewUser>()
        .name("csvWriter")
        .resource(new FileSystemResource("output/users.csv"))
        .delimited()
        .names("name", "email", "status")
        .headerCallback(writer -> writer.write("이름,이메일,상태"))
        .build();
}
```

### 멀티 Step과 흐름 제어

```java
@Bean
public Job complexJob(JobRepository jobRepository) {
    return new JobBuilder("complexJob", jobRepository)
        .start(validateStep())
        .on("FAILED").to(errorStep())
        .from(validateStep())
        .on("*").to(processStep())
        .next(reportStep())
        .end()
        .build();
}
```

### 스케줄링

```java
@Configuration
@EnableScheduling
public class BatchScheduler {

    private final JobLauncher jobLauncher;
    private final Job userMigrationJob;

    @Scheduled(cron = "0 0 2 * * *")  // 매일 새벽 2시
    public void runJob() throws Exception {
        JobParameters params = new JobParametersBuilder()
            .addString("date", LocalDate.now().toString())
            .addLong("timestamp", System.currentTimeMillis())
            .toJobParameters();

        jobLauncher.run(userMigrationJob, params);
    }
}
```

### 에러 처리

| 방식 | 설명 | 설정 |
|------|------|------|
| **Skip** | 실패한 항목을 건너뛰고 계속 | `.skip(Exception.class).skipLimit(10)` |
| **Retry** | 실패한 항목을 재시도 | `.retry(Exception.class).retryLimit(3)` |
| **Restart** | 실패 지점부터 재시작 | Job 메타데이터 기반 자동 |
| **Listener** | 실패 시 로그/알림 | `SkipListener`, `RetryListener` |

```java
// Skip + Retry + Listener 조합
@Bean
public Step robustStep(JobRepository jobRepository, PlatformTransactionManager tx) {
    return new StepBuilder("robustStep", jobRepository)
        .<User, User>chunk(100, tx)
        .reader(reader())
        .processor(processor())
        .writer(writer())
        .faultTolerant()
        .retryLimit(3)
        .retry(TransientDataAccessException.class)
        .skipLimit(100)
        .skip(ValidationException.class)
        .listener(new StepExecutionListener() {
            @Override
            public ExitStatus afterStep(StepExecution stepExecution) {
                log.info("처리: {}건, 스킵: {}건",
                    stepExecution.getWriteCount(),
                    stepExecution.getSkipCount());
                return stepExecution.getExitStatus();
            }
        })
        .build();
}
```

---

## 실무 트러블슈팅

### Job이 STARTED 상태로 멈춤

서버가 비정상 종료(OOM Kill, 강제 종료)되면 `BATCH_JOB_EXECUTION`의 STATUS가 `STARTED`로 남는다. 이 상태에서 같은 Job을 재실행하면 `JobExecutionAlreadyRunningException`이 발생한다.

```java
// 해결: STARTED 상태인 오래된 Execution을 수동으로 FAILED 처리
@Component
public class StalledJobCleaner {

    @Autowired
    private JobExplorer jobExplorer;
    @Autowired
    private JobRepository jobRepository;

    public void cleanStalledJobs(String jobName) {
        jobExplorer.findJobInstancesByJobName(jobName, 0, 100).stream()
            .flatMap(i -> jobExplorer.getJobExecutions(i).stream())
            .filter(e -> e.getStatus() == BatchStatus.STARTED)
            .filter(e -> e.getStartTime().isBefore(
                LocalDateTime.now().minusHours(6)))  // 6시간 이상 경과
            .forEach(e -> {
                e.setStatus(BatchStatus.FAILED);
                e.setEndTime(LocalDateTime.now());
                e.setExitStatus(ExitStatus.FAILED.addExitDescription(
                    "수동 FAILED 처리 - 서버 비정상 종료 추정"));
                jobRepository.update(e);

                e.getStepExecutions().forEach(se -> {
                    se.setStatus(BatchStatus.FAILED);
                    se.setEndTime(LocalDateTime.now());
                    jobRepository.update(se);
                });
            });
    }
}
```

운영에서는 이 정리 작업을 배치 실행 전에 자동으로 돌리는 팀도 있다. 하지만 실제로 실행 중인 Job을 FAILED로 바꾸는 사고를 막기 위해 시간 임계값(위 예에서 6시간)을 넉넉히 잡아야 한다.

### 멀티 스레드 Step에서 Reader가 같은 데이터를 중복 읽음

`JdbcPagingItemReader`는 `synchronized` 블록으로 `read()`를 보호하므로 thread-safe하다. 하지만 커스텀 Reader를 만들면서 `read()` 동기화를 빼먹으면 같은 데이터를 여러 스레드가 읽는다.

```java
// 커스텀 Reader에서 thread-safe 보장
public class CustomItemReader implements ItemReader<Order> {

    private final Queue<Order> buffer = new ConcurrentLinkedQueue<>();
    private volatile boolean initialized = false;

    @Override
    public synchronized Order read() {
        if (!initialized) {
            // 초기화 로직
            initialized = true;
        }
        return buffer.poll();  // null이면 읽기 종료
    }
}
```

기본 제공 Reader를 쓰면 이런 문제가 없다. 커스텀 Reader를 만들어야 하면 `SynchronizedItemStreamReader`로 감싸는 게 간단하다.

```java
@Bean
public SynchronizedItemStreamReader<Order> synchronizedReader() {
    SynchronizedItemStreamReader<Order> reader = new SynchronizedItemStreamReader<>();
    reader.setDelegate(customReader());
    return reader;
}
```

### chunkSize 변경 후 재시작 시 데이터 누락

Step의 chunkSize를 바꾸고 실패한 Job을 재시작하면, 이전 Execution에서 저장한 `ExecutionContext`의 읽기 위치와 현재 chunkSize가 맞지 않아서 일부 데이터를 건너뛰거나 중복 처리할 수 있다.

chunkSize를 바꿔야 하면, 실패한 Job은 기존 chunkSize로 재시작해서 완료시키고, 새 chunkSize는 다음 실행부터 적용하는 게 안전하다. 또는 `BATCH_STEP_EXECUTION_CONTEXT`를 직접 수정하는 방법도 있지만 권장하지 않는다.

### JpaItemWriter에서 bulk INSERT가 안 됨

Hibernate는 `GenerationType.IDENTITY`를 쓰면 JDBC batch insert를 비활성화한다. `INSERT` 후 DB가 생성한 ID를 바로 받아야 해서 한 건씩 INSERT한다.

```properties
# application.properties
spring.jpa.properties.hibernate.jdbc.batch_size=100
spring.jpa.properties.hibernate.order_inserts=true
spring.jpa.properties.hibernate.order_updates=true
```

위 설정을 해도 `IDENTITY` 전략이면 효과가 없다. `SEQUENCE` 전략으로 바꾸거나, 대량 INSERT가 필요하면 `JdbcBatchItemWriter`를 쓰는 게 낫다. JPA의 영속성 관리가 필요 없는 단순 INSERT라면 JDBC가 성능이 훨씬 좋다.

### 배치에서 @Transactional을 쓰면 안 되는 이유

Spring Batch는 chunk 단위로 자체 트랜잭션을 관리한다. Processor나 Writer에 `@Transactional`을 붙이면 Spring Batch의 트랜잭션과 충돌해서 예상치 못한 커밋/롤백이 일어난다.

```java
// 하면 안 되는 것
@Component
public class OrderProcessor implements ItemProcessor<Order, Order> {

    @Transactional  // Spring Batch 트랜잭션과 충돌
    @Override
    public Order process(Order item) {
        // ...
    }
}
```

배치 내부에서 추가 트랜잭션이 필요하면 `REQUIRES_NEW` 전파를 쓰되, 이 경우 해당 작업은 chunk 트랜잭션과 독립적으로 커밋/롤백되므로 데이터 정합성을 직접 관리해야 한다.

---

## 참고

- [Spring Batch 공식 문서](https://docs.spring.io/spring-batch/reference/)
- [Spring Test](Spring_Test.md) — 배치 테스트
- [Java 동시성](../../Language/Java/멀티스레딩 및 동시성/Java_Concurrency.md) — 병렬 처리 기초
