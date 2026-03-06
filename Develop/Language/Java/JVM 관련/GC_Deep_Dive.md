---
title: JVM Garbage Collection 심화 가이드
tags: [java, jvm, gc, garbage-collection, g1gc, zgc, heap, memory, tuning]
updated: 2026-03-01
---

# JVM Garbage Collection 심화

## 개요

GC(Garbage Collection)는 JVM이 **사용하지 않는 객체를 자동으로 해제**하는 메모리 관리 메커니즘이다. 개발자가 직접 메모리를 해제하지 않아도 되지만, GC 동작을 이해해야 **성능 문제를 진단하고 튜닝**할 수 있다.

### 왜 GC를 알아야 하는가

```
문제 상황:
  - API 응답이 간헐적으로 1초 이상 걸린다 → GC Pause
  - 서버가 갑자기 OOM으로 죽는다 → 메모리 누수
  - 부하 테스트에서 TPS가 점점 떨어진다 → GC 오버헤드

→ GC 로그를 읽고 튜닝할 수 있어야 한다
```

## 핵심

### 1. JVM 힙 메모리 구조

```
┌──────────────────────────────────────────────┐
│                    Heap                       │
│  ┌─────────────────────┐  ┌───────────────┐  │
│  │    Young Generation  │  │ Old Generation│  │
│  │  ┌─────┬─────┬─────┐│  │               │  │
│  │  │Eden │ S0  │ S1  ││  │  (Tenured)    │  │
│  │  │     │     │     ││  │               │  │
│  │  └─────┴─────┴─────┘│  └───────────────┘  │
│  └─────────────────────┘                      │
├──────────────────────────────────────────────┤
│  Metaspace (클래스 메타데이터, 네이티브 메모리)    │
└──────────────────────────────────────────────┘
```

| 영역 | 역할 | 크기 비율 |
|------|------|----------|
| **Eden** | 새 객체가 생성되는 곳 | Young의 80% |
| **Survivor (S0, S1)** | Minor GC에서 살아남은 객체 | Young의 각 10% |
| **Old (Tenured)** | 오래 살아남은 객체 | 전체 Heap의 2/3 |
| **Metaspace** | 클래스 메타데이터 | 네이티브 메모리 (별도) |

### 2. GC 동작 원리

#### 객체 생명주기

```
1. 객체 생성 → Eden에 할당
2. Eden이 가득 참 → Minor GC 발생
3. 살아있는 객체 → Survivor 영역으로 이동 (age +1)
4. age가 임계치 도달 → Old 영역으로 이동 (Promotion)
5. Old가 가득 참 → Major GC (Full GC) 발생
```

```
Minor GC:
  Eden [████████████] → GC → Eden [          ]
  살아남은 객체 → S0 [██]

다음 Minor GC:
  Eden [████████████] + S0 [██] → GC
  살아남은 객체 → S1 [███]  (S0 비움)

객체 age가 15 도달:
  Survivor → Old 영역으로 이동 (Promotion)
```

#### GC 유형 비교

| 유형 | 대상 | 빈도 | 시간 | STW |
|------|------|------|------|-----|
| **Minor GC** | Young 영역 | 자주 | 짧음 (ms) | 짧음 |
| **Major GC** | Old 영역 | 가끔 | 길 수 있음 | 길 수 있음 |
| **Full GC** | 전체 Heap + Metaspace | 드물게 | 가장 김 | 가장 김 |

### 3. GC 알고리즘

#### Mark and Sweep

```
1. Mark: 루트(GC Root)에서 시작하여 참조 체인을 따라 살아있는 객체 표시
2. Sweep: 표시되지 않은 객체 해제
3. Compact: 파편화 방지를 위해 객체를 한쪽으로 모음

GC Root:
  - 스택의 지역 변수
  - static 변수
  - JNI 참조
  - 활성 스레드
```

### 4. GC 컬렉터 비교

| 컬렉터 | 목표 | STW | 적합한 경우 |
|--------|------|-----|-----------|
| **Serial GC** | 단순함 | 길다 | 소규모 앱, 클라이언트 |
| **Parallel GC** | 처리량 | 보통 | 배치 처리, 백그라운드 |
| **G1 GC** | 균형 (처리량+지연) | 짧음 | **프로덕션 기본 (Java 9+)** |
| **ZGC** | 초저지연 | **< 1ms** | 대용량 힙, 실시간 |
| **Shenandoah** | 초저지연 | **< 1ms** | 대용량 힙 (RedHat) |

#### G1 GC (Garbage-First)

Java 9+ 기본 GC. 힙을 **리전(Region)** 단위로 나누어 관리한다.

```
G1 힙 구조 (리전 기반):

┌───┬───┬───┬───┬───┬───┬───┬───┐
│ E │ E │ S │ O │ O │ H │ E │ O │
├───┼───┼───┼───┼───┼───┼───┼───┤
│ O │ E │ O │ O │ S │ E │ O │   │
├───┼───┼───┼───┼───┼───┼───┼───┤
│ E │ O │ O │ E │ O │ O │ E │ O │
└───┴───┴───┴───┴───┴───┴───┴───┘

E=Eden, S=Survivor, O=Old, H=Humongous (대형 객체)

→ 가비지가 많은 리전부터 우선 수거 (Garbage-First)
```

```bash
# G1 GC 설정 (Java 9+ 기본)
java -XX:+UseG1GC \
     -XX:MaxGCPauseMillis=200 \     # 목표 GC 정지 시간 (200ms)
     -XX:G1HeapRegionSize=4m \      # 리전 크기
     -XX:InitiatingHeapOccupancyPercent=45 \  # Old 사용률 45%에서 GC 시작
     -Xms4g -Xmx4g \                # 힙 크기 고정
     -jar app.jar
```

#### ZGC (Z Garbage Collector)

**1ms 이하의 STW**를 보장하는 초저지연 GC. 16TB까지 지원.

```bash
# ZGC 설정 (Java 15+, 프로덕션 사용 가능)
java -XX:+UseZGC \
     -XX:+ZGenerational \            # 세대별 ZGC (Java 21+)
     -Xms8g -Xmx8g \
     -jar app.jar
```

| 비교 | G1 GC | ZGC |
|------|-------|-----|
| **STW** | ~200ms (목표) | **< 1ms** |
| **힙 크기** | ~32GB 적합 | 수 TB까지 |
| **CPU 오버헤드** | 낮음 | 약간 높음 |
| **Java 버전** | 9+ (기본) | 15+ |
| **적합한 경우** | 일반 서버 | 대용량 힙, 실시간 |

### 5. GC 튜닝

#### 기본 JVM 옵션

```bash
# 힙 크기 (Xms = Xmx로 고정 권장)
-Xms4g -Xmx4g

# Metaspace
-XX:MetaspaceSize=256m
-XX:MaxMetaspaceSize=512m

# GC 로그 활성화 (Java 9+)
-Xlog:gc*:file=gc.log:time,level,tags:filecount=5,filesize=100m

# Java 8 GC 로그
-verbose:gc -Xloggc:gc.log -XX:+PrintGCDetails -XX:+PrintGCDateStamps
```

#### GC 로그 분석

```
# G1 GC 로그 예시
[2026-03-01T10:15:30.123+0900] GC(42) Pause Young (Normal) (G1 Evacuation Pause)
[2026-03-01T10:15:30.123+0900] GC(42)   Eden regions: 24->0(24)
[2026-03-01T10:15:30.123+0900] GC(42)   Survivor regions: 3->3(4)
[2026-03-01T10:15:30.123+0900] GC(42)   Old regions: 15->16
[2026-03-01T10:15:30.123+0900] GC(42)   Humongous regions: 0->0
[2026-03-01T10:15:30.123+0900] GC(42) Pause Young (Normal) 168M->76M(512M) 12.345ms

읽는 법:
  168M→76M: 168MB 사용 중 → GC 후 76MB (92MB 해제)
  (512M): 전체 힙 크기
  12.345ms: GC 소요 시간 (STW)
```

#### 분석 도구

```bash
# GC 로그 분석 (GCEasy.io — 온라인 무료)
# gc.log 파일을 https://gceasy.io 에 업로드

# 힙 덤프 생성
jmap -dump:live,format=b,file=heap.hprof <PID>

# OOM 시 자동 힙 덤프
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/var/log/java/heap.hprof

# 실시간 메모리 모니터링
jstat -gc <PID> 1000    # 1초 간격
jstat -gcutil <PID> 1000

# VisualVM으로 시각적 분석
jvisualvm
```

### 6. 메모리 누수 패턴

```java
// 1. static 컬렉션에 계속 추가
static List<Object> cache = new ArrayList<>();  // 절대 해제되지 않음

// 2. 클로저/리스너 미해제
eventBus.register(listener);  // unregister 안 하면 누수

// 3. ThreadLocal 미정리
threadLocal.set(largeObject);
// threadLocal.remove() 호출 안 하면 스레드 풀에서 누수

// 4. 커넥션/스트림 미반환
Connection conn = dataSource.getConnection();
// conn.close() 미호출 → 커넥션 풀 고갈
```

### 7. 실전 튜닝 시나리오

```
시나리오: API 응답 P99 지연이 2초를 넘는다

1. GC 로그 확인
   → Full GC가 2초 소요, 30분마다 발생

2. 원인 분석
   → Old 영역이 가득 차서 Full GC 발생
   → 캐시 객체가 Old로 이동 후 해제되지 않음

3. 해결
   → 캐시 크기 제한 (LRU eviction)
   → G1 GC에서 ZGC로 전환
   → 힙 크기 증가 (-Xmx4g → -Xmx8g)

4. 검증
   → GC 로그에서 Full GC 빈도와 소요 시간 확인
   → P99 지연 1초 이내로 감소 확인
```

| 증상 | 가능한 원인 | 해결 |
|------|-----------|------|
| 간헐적 지연 | GC Pause | ZGC 전환 또는 GC 튜닝 |
| OOM 에러 | 메모리 누수 | 힙 덤프 분석 후 원인 제거 |
| TPS 감소 | GC 빈도 증가 | 힙 크기 증가, 객체 할당 최적화 |
| Metaspace OOM | 클래스 로더 누수 | Metaspace 크기 조절, 리플렉션 확인 |

## 참고

- [JVM Garbage Collectors Documentation](https://docs.oracle.com/en/java/javase/21/gctuning/)
- [GCEasy — GC 로그 분석 도구](https://gceasy.io)
- [JVM 구조](JVM 구조 및 메모리 관리.md) — JVM 기본 구조
- [자바 메모리 구조](../Java 기본 개념/자바 메모리 구조.md) — 메모리 영역
