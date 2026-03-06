---
title: Spring Batch 가이드
tags: [spring, batch, job, step, reader, writer, processor, chunk, scheduling, large-data]
updated: 2026-03-01
---

# Spring Batch

## 개요

Spring Batch는 **대용량 데이터를 안정적으로 배치 처리**하는 프레임워크이다. 수백만~수억 건의 데이터를 읽고, 가공하고, 저장하는 작업을 트랜잭션 관리, 재시도, 재시작 기능과 함께 제공한다.

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

## 핵심

### 1. Job과 Step

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
            .<OldUser, NewUser>chunk(100, transactionManager)  // 100건씩 처리
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

### 2. ItemReader (읽기)

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
        .linesToSkip(1)  // 헤더 건너뛰기
        .delimited()
        .names("name", "email", "age")
        .targetType(UserCsv.class)
        .build();
}

// JPA에서 읽기
@Bean
public JpaPagingItemReader<User> jpaReader() {
    return new JpaPagingItemReaderBuilder<User>()
        .name("jpaReader")
        .entityManagerFactory(entityManagerFactory)
        .queryString("SELECT u FROM User u WHERE u.active = true")
        .pageSize(100)
        .build();
}
```

### 3. ItemProcessor (가공)

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

### 4. ItemWriter (쓰기)

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

### 5. 멀티 Step & 흐름 제어

```java
@Bean
public Job complexJob(JobRepository jobRepository) {
    return new JobBuilder("complexJob", jobRepository)
        .start(validateStep())             // 1단계: 검증
        .on("FAILED").to(errorStep())      // 실패 시 에러 처리
        .from(validateStep())
        .on("*").to(processStep())         // 성공 시 처리
        .next(reportStep())               // 3단계: 리포트
        .end()
        .build();
}

// Tasklet (단순 작업, Chunk 불필요 시)
@Bean
public Step cleanupStep(JobRepository jobRepository,
                         PlatformTransactionManager tx) {
    return new StepBuilder("cleanupStep", jobRepository)
        .tasklet((contribution, chunkContext) -> {
            // 임시 파일 삭제 등 단순 작업
            Files.deleteIfExists(Path.of("/tmp/batch-temp.csv"));
            return RepeatStatus.FINISHED;
        }, tx)
        .build();
}
```

### 6. 스케줄링

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

### 7. 병렬 처리

```java
// 멀티 스레드 Step
@Bean
public Step parallelStep(JobRepository jobRepository,
                          PlatformTransactionManager tx) {
    return new StepBuilder("parallelStep", jobRepository)
        .<User, User>chunk(100, tx)
        .reader(reader())          // 스레드 안전한 Reader 필요
        .processor(processor())
        .writer(writer())
        .taskExecutor(taskExecutor())
        .throttleLimit(4)          // 동시 스레드 4개
        .build();
}

@Bean
public TaskExecutor taskExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(4);
    executor.setMaxPoolSize(8);
    executor.setQueueCapacity(25);
    return executor;
}

// 파티셔닝 (데이터 분할 후 병렬 처리)
@Bean
public Step partitionedStep(JobRepository jobRepository) {
    return new StepBuilder("partitionedStep", jobRepository)
        .partitioner("workerStep", partitioner())
        .step(workerStep())
        .gridSize(4)               // 4개 파티션
        .taskExecutor(taskExecutor())
        .build();
}
```

### 8. 에러 처리

| 전략 | 설명 | 설정 |
|------|------|------|
| **Skip** | 실패한 항목을 건너뛰고 계속 | `.skip(Exception.class).skipLimit(10)` |
| **Retry** | 실패한 항목을 재시도 | `.retry(Exception.class).retryLimit(3)` |
| **Restart** | 실패 지점부터 재시작 | Job 메타데이터 기반 자동 |
| **Listener** | 실패 시 로그/알림 | `SkipListener`, `RetryListener` |

```java
// Skip + Retry + Listener 조합
@Bean
public Step robustStep(JobRepository jobRepository,
                        PlatformTransactionManager tx) {
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

## 참고

- [Spring Batch 공식 문서](https://docs.spring.io/spring-batch/reference/)
- [Spring Test](Spring_Test.md) — 배치 테스트
- [Java 동시성](../../Language/Java/멀티스레딩 및 동시성/Java_Concurrency.md) — 병렬 처리 기초
