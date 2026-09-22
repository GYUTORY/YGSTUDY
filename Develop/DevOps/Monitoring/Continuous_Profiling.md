---
title: 지속적 프로파일링
tags: [monitoring, observability, go, nodejs, java, devops, performance]
updated: 2026-09-22
---

# 지속적 프로파일링

## 프로파일러가 필요한 시점

CPU 사용률이 70%를 넘기 시작했는데 APM 트레이스에는 아무것도 안 잡혔다. 각 엔드포인트 응답 시간은 정상이었고, 느린 쿼리도 없었다. 그런데 서버는 계속 뜨거웠다.

로그를 전부 뒤졌고, 메트릭을 전부 봤다. 결국 원인은 JSON 직렬화 내부에서 과도하게 불리는 리플렉션 로직이었는데, 이건 프로파일러 없이는 절대 못 찾는다. 스팬 하나에는 JSON 직렬화 5마이크로초, 근데 초당 10만 번 불리면 CPU가 50%다.

APM은 "어디서 느린가"를 알려준다. 프로파일러는 "왜 CPU를 먹는가"를 알려준다. 둘은 다르다.

메모리 릭도 마찬가지다. Heap 사용량이 꾸준히 오르는데 GC 로그에는 눈에 띄는 게 없다면, 어떤 객체가 참조를 놓지 않는지 heap dump나 allocation profiler 없이는 알 수 없다.

---

## pprof: Go 내장 프로파일러

Go는 `net/http/pprof`를 표준 라이브러리로 제공한다. HTTP 서버에 임포트 한 줄이면 프로파일링 엔드포인트가 붙는다.

```go
import _ "net/http/pprof"
```

이렇게 하면 `/debug/pprof/` 아래에 다음 엔드포인트가 생긴다.

- `/debug/pprof/profile` — CPU 프로파일 (기본 30초)
- `/debug/pprof/heap` — 현재 heap 스냅샷
- `/debug/pprof/goroutine` — 전체 goroutine 스택 덤프
- `/debug/pprof/allocs` — 메모리 할당 프로파일
- `/debug/pprof/mutex` — mutex 경합
- `/debug/pprof/block` — 블로킹 연산 (channel receive, syscall 등)

CPU 프로파일을 30초 수집하고 flamegraph로 보는 방법:

```bash
# 30초 CPU 프로파일 수집
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30

# 또는 파일로 저장
curl -o cpu.pprof http://localhost:6060/debug/pprof/profile?seconds=30
go tool pprof -http=:8080 cpu.pprof
```

`go tool pprof -http=:8080`이 브라우저에서 flamegraph를 보여준다. Graphviz가 없으면 텍스트 모드로 떨어진다. `brew install graphviz` 또는 `apt install graphviz`로 설치해야 SVG가 나온다.

goroutine 덤프는 goroutine 릭 추적에 쓴다. goroutine 수가 계속 늘어난다면 `/debug/pprof/goroutine?debug=2`를 주기적으로 수집해 어떤 스택이 쌓이는지 본다.

```bash
# goroutine 전체 스택 텍스트로 보기
curl http://localhost:6060/debug/pprof/goroutine?debug=2 | head -200
```

pprof의 단점은 **순간 스냅샷**이라는 것이다. 문제가 재현되는 순간에 직접 수집해야 한다. 밤새 메모리가 새는 서버에 아침에 붙으면 이미 GC가 돌았거나 서버가 재시작됐을 수 있다. 프로덕션에서 문제가 간헐적으로 난다면 pprof만으로는 한계가 있다.

### pprof 엔드포인트를 프로덕션에 노출할 때

내부 포트(별도 HTTP 서버)로만 열어야 한다. 외부에 노출되면 30초 CPU 프로파일 수집이 서비스에 영향을 줄 수 있고, 내부 구조가 노출된다.

```go
// 메인 서버와 분리된 포트로 pprof 전용 서버 실행
func startPprofServer() {
    mux := http.NewServeMux()
    mux.HandleFunc("/debug/pprof/", pprof.Index)
    mux.HandleFunc("/debug/pprof/cmdline", pprof.Cmdline)
    mux.HandleFunc("/debug/pprof/profile", pprof.Profile)
    mux.HandleFunc("/debug/pprof/symbol", pprof.Symbol)
    mux.HandleFunc("/debug/pprof/trace", pprof.Trace)

    go http.ListenAndServe("127.0.0.1:6060", mux)
}
```

Kubernetes라면 Service를 NodePort나 LoadBalancer로 열지 않고, `kubectl port-forward`로 접근한다.

---

## 지속적 프로파일링과 Pyroscope

pprof가 순간 스냅샷이라면, 지속적 프로파일링은 24시간 내내 낮은 오버헤드로 프로파일을 수집해 저장한다. Grafana Pyroscope(구 Grafana Phlare)가 이 역할을 한다.

Pyroscope는 시계열로 프로파일 데이터를 저장한다. 특정 시간대로 이동해서 "오전 2시에 CPU가 높았는데 그때 flamegraph가 어땠나"를 사후에 볼 수 있다. 이게 핵심 차이다.

동작 방식은 두 가지다.

**Push 모드**: 앱이 Pyroscope SDK를 통해 주기적으로 프로파일을 Pyroscope 서버로 올린다. 가장 흔하게 쓴다.

**Pull 모드**: Pyroscope 서버가 앱의 pprof 엔드포인트를 주기적으로 스크랩한다. Prometheus가 메트릭을 긁는 것과 같은 구조다. Go 앱이 `net/http/pprof`를 이미 열어두었다면 별도 SDK 없이 붙일 수 있다.

### Pyroscope 서버 설치

```yaml
# docker-compose.yml
services:
  pyroscope:
    image: grafana/pyroscope:latest
    ports:
      - "4040:4040"
    volumes:
      - pyroscope-data:/data
    command:
      - "server"

volumes:
  pyroscope-data:
```

기본 포트는 4040이다. `/` 경로에서 UI가 열린다.

Kubernetes에 올릴 때는 StatefulSet으로 배포하고, PVC를 붙인다. Pyroscope는 로컬 디스크에 블록을 저장하는데, Deployment로 올리면 Pod 재시작 때 데이터가 사라진다.

---

## Go 앱에서 Pyroscope 설정

### Push 모드 (SDK)

```go
package main

import (
    "github.com/grafana/pyroscope-go"
)

func main() {
    profiler, err := pyroscope.Start(pyroscope.Config{
        ApplicationName: "payment-service",
        ServerAddress:   "http://pyroscope:4040",
        Logger:          pyroscope.StandardLogger,

        // 수집할 프로파일 타입 지정
        ProfileTypes: []pyroscope.ProfileType{
            pyroscope.ProfileCPU,
            pyroscope.ProfileAllocObjects,
            pyroscope.ProfileAllocSpace,
            pyroscope.ProfileInuseObjects,
            pyroscope.ProfileInuseSpace,
            pyroscope.ProfileGoroutines,
        },
    })
    if err != nil {
        log.Fatal(err)
    }
    defer profiler.Stop()

    // 서비스 실행
    startServer()
}
```

`ProfileAllocObjects`와 `ProfileAllocSpace`는 할당 프로파일이다. 둘 다 켜면 "(몇 개 객체를 할당했는가)" vs "(얼마나 많은 메모리를 할당했는가)"를 각각 볼 수 있다. GC가 자주 돈다면 할당 프로파일에서 문제 위치를 찾을 수 있다.

`ProfileGoroutines`는 goroutine 수가 비정상적으로 늘어날 때 어느 코드에서 goroutine이 생기는지 추적한다.

### Pull 모드 (pprof 스크랩)

앱이 이미 pprof 엔드포인트를 열고 있다면, Pyroscope 설정에서 scrape target을 지정한다.

```yaml
# pyroscope.yml
scrape_configs:
  - job_name: payment-service
    params:
      # 각 수집 간격(기본 15초)마다 10초 CPU 프로파일 수집
      seconds: ["10"]
    scrape_interval: 15s
    scrape_timeout: 18s
    scheme: http
    static_configs:
      - targets:
          - payment-service:6060
        labels:
          service_name: payment-service
          env: production
    profiling_config:
      pprof_config:
        memory:
          enabled: true
          path: /debug/pprof/heap
        cpu:
          enabled: true
          path: /debug/pprof/profile
        goroutine:
          enabled: true
          path: /debug/pprof/goroutine
          params:
            debug: ["2"]
```

Pull 모드의 장점은 앱 코드를 건드리지 않아도 된다는 것이다. 다만 scrape 자체가 앱에 부하를 준다. 특히 CPU 프로파일 수집 시간(`seconds`) 동안 Go 런타임이 샘플링을 돌리기 때문에, 짧게(10초) 설정하더라도 수집 주기와 겹치지 않게 `scrape_interval`을 충분히 크게 잡아야 한다.

### 레이블로 환경 구분

프로덕션, 스테이징 둘 다 Pyroscope 하나에 올릴 때는 레이블로 구분한다.

```go
profiler, err := pyroscope.Start(pyroscope.Config{
    ApplicationName: "payment-service",
    ServerAddress:   "http://pyroscope:4040",
    Tags: map[string]string{
        "env":     os.Getenv("APP_ENV"),     // "production", "staging"
        "region":  os.Getenv("AWS_REGION"),  // "ap-northeast-2"
        "version": os.Getenv("APP_VERSION"), // "v1.2.3"
    },
    ProfileTypes: []pyroscope.ProfileType{
        pyroscope.ProfileCPU,
        pyroscope.ProfileInuseSpace,
    },
})
```

레이블이 있으면 Pyroscope UI에서 `{env="production", region="ap-northeast-2"}`로 필터링해서 볼 수 있다. 배포 직후 `version` 레이블로 이전 버전과 현재 버전 CPU 사용 flamegraph를 나란히 비교하는 것도 된다.

---

## Node.js 앱 프로파일링

Node.js는 V8 엔진의 CPU 프로파일러와 Heap 스냅샷을 이용한다.

```bash
npm install @pyroscope/nodejs
```

```typescript
import Pyroscope from '@pyroscope/nodejs';

Pyroscope.init({
  serverAddress: 'http://pyroscope:4040',
  appName: 'api-gateway',
  tags: {
    env: process.env.NODE_ENV ?? 'development',
    version: process.env.APP_VERSION ?? 'unknown',
  },
});

Pyroscope.start();

// 프로세스 종료 시
process.on('SIGTERM', async () => {
  await Pyroscope.stop();
  process.exit(0);
});
```

Node.js 프로파일러는 V8의 샘플링 프로파일러를 쓴다. 기본 100Hz로 샘플링한다. CPU 프로파일과 Heap 프로파일 두 가지를 지원한다.

Node.js에서 Heap 프로파일이 특히 중요하다. V8의 GC는 Mark-and-Sweep이라 참조만 끊기면 알아서 회수하는데, 클로저가 의도치 않게 객체 참조를 유지하거나, EventEmitter에 리스너를 계속 붙이고 제거하지 않으면 leak이 생긴다. `@pyroscope/nodejs`의 heap profiler가 어느 코드 경로에서 할당이 많은지 flamegraph로 보여준다.

주의할 점이 하나 있다. Node.js 프로파일러는 싱글 스레드 특성상 **CPU 바운드 작업 중 샘플링이 실제로 CPU를 쓰는 위치를 잡지 못하는 경우**가 있다. V8 프로파일러는 안전 지점(safepoint)에서만 샘플을 찍는데, 타이트한 루프나 네이티브 바인딩 호출 중에는 안전 지점이 드물어서 그 부분이 flamegraph에 과소평가된다.

Worker Thread를 많이 쓰는 앱이라면 각 워커에서 별도로 프로파일러를 시작해야 한다. 메인 스레드에서만 시작하면 워커 CPU 사용량은 안 잡힌다.

---

## JVM 앱 프로파일링

Java와 Kotlin 앱은 Pyroscope Java 에이전트를 쓴다. 내부적으로 async-profiler를 사용한다.

### 에이전트 방식

```bash
# 에이전트 다운로드
wget https://github.com/grafana/pyroscope-java/releases/latest/download/pyroscope.jar

# JVM 시작 옵션에 추가
JAVA_OPTS="-javaagent:/path/to/pyroscope.jar"
PYROSCOPE_SERVER_ADDRESS=http://pyroscope:4040
PYROSCOPE_APPLICATION_NAME=order-service
PYROSCOPE_PROFILING_INTERVAL=10ms
PYROSCOPE_PROFILER_EVENT=cpu
PYROSCOPE_FORMAT=jfr
```

환경변수로 설정하거나 `-D` 플래그로 시스템 프로퍼티로 넘긴다.

```bash
java \
  -javaagent:/path/to/pyroscope.jar \
  -Dpyroscope.server.address=http://pyroscope:4040 \
  -Dpyroscope.application.name=order-service \
  -Dpyroscope.profiling.interval=10ms \
  -Dpyroscope.profiler.event=cpu \
  -jar app.jar
```

Spring Boot에서 Kubernetes 환경이라면 Deployment의 `env` 섹션에 넣는다.

```yaml
env:
  - name: PYROSCOPE_SERVER_ADDRESS
    value: http://pyroscope.monitoring:4040
  - name: PYROSCOPE_APPLICATION_NAME
    value: order-service
  - name: PYROSCOPE_LABELS
    value: "env=production,version=$(APP_VERSION)"
```

### 수집 이벤트 타입

`PYROSCOPE_PROFILER_EVENT`로 무엇을 프로파일할지 결정한다.

- `cpu` — CPU 샘플링 프로파일. 가장 기본. async-profiler의 `AsyncGetCallTrace`를 씀.
- `wall` — Wall-clock 프로파일. CPU를 쓰지 않고 기다리는 시간(IO wait, lock wait 등)도 잡힌다. I/O 바운드 앱에서 유용.
- `alloc` — 메모리 할당 프로파일. 어느 코드에서 객체를 많이 만드는지 보여줌.
- `lock` — Lock 경합 프로파일. synchronized 블록이나 ReentrantLock에서 대기하는 시간.

CPU 프로파일만 보고 "코드가 정상인데 왜 느리지?"라면 `wall` 타입으로 바꿔보면 I/O 대기가 눈에 보이는 경우가 있다. JVM에서 I/O는 CPU를 거의 안 쓰기 때문에 CPU 프로파일에는 안 잡힌다.

### JFR(Java Flight Recorder) 포맷

`PYROSCOPE_FORMAT=jfr`로 설정하면 JFR 포맷으로 데이터를 올린다. JFR 포맷은 여러 이벤트 타입을 한 번에 수집하는 것을 지원한다.

```bash
PYROSCOPE_FORMAT=jfr
PYROSCOPE_PROFILER_EVENT=cpu,alloc,lock
```

이렇게 하면 CPU, 메모리 할당, 락 경합을 동시에 수집해 Pyroscope에 올린다. 프로파일 타입마다 flamegraph를 전환하며 볼 수 있다.

---

## Grafana와 연동해 트레이스-프로파일 상관 분석

Grafana에서 Pyroscope 데이터 소스를 추가하면 Explore 탭에서 flamegraph를 볼 수 있다. 여기서 더 나아가 트레이스와 프로파일을 연결하면, 특정 트레이스가 느릴 때 그 시간대의 flamegraph를 함께 볼 수 있다.

### Grafana 데이터 소스 설정

```yaml
# grafana/provisioning/datasources/pyroscope.yaml
apiVersion: 1
datasources:
  - name: Pyroscope
    type: grafana-pyroscope-datasource
    url: http://pyroscope:4040
    uid: pyroscope
    jsonData:
      minStep: 15s
```

### 트레이스-프로파일 연결 (Tempo + Pyroscope)

Grafana Tempo에서 트레이스를 볼 때 "Profiles" 버튼이 생기려면 두 가지 설정이 필요하다.

**1. Tempo 데이터 소스에 Pyroscope 연결**

```yaml
datasources:
  - name: Tempo
    type: tempo
    url: http://tempo:3200
    uid: tempo
    jsonData:
      tracesToProfiles:
        datasourceUid: pyroscope
        tags:
          - key: service.name
            value: service_name
        profileTypeId: process_cpu:cpu:nanoseconds:cpu:nanoseconds
        customQuery: false
```

`tags` 설정이 핵심이다. 트레이스 스팬의 `service.name` 속성이 Pyroscope의 `service_name` 레이블과 매핑된다. 이 매핑이 없으면 Tempo가 어느 앱의 프로파일을 가져와야 하는지 모른다.

**2. 앱에서 Profile ID를 스팬에 주입 (선택)**

Pyroscope SDK v0.3+와 OTel을 같이 쓴다면 현재 프로파일 ID를 스팬 속성으로 넣을 수 있다.

```go
// Go 예시
import (
    otelpyroscope "github.com/grafana/otel-profiling-go"
    "go.opentelemetry.io/otel"
)

// TracerProvider에 Pyroscope 래퍼를 씌운다
tp := otelpyroscope.NewTracerProvider(
    otel.GetTracerProvider(),
    otelpyroscope.WithAppName("payment-service"),
    otelpyroscope.WithRootSpanOnly(),  // 루트 스팬에만 프로파일 ID 주입
    otelpyroscope.WithAddSpanName(true),
)
otel.SetTracerProvider(tp)
```

이렇게 하면 스팬에 `pyroscope.profile.id` 속성이 자동으로 붙는다. Tempo에서 이 트레이스를 열면 "Profiles" 버튼이 정확히 그 시간대의 flamegraph를 가리킨다.

Profile ID를 주입하지 않을 때는 Grafana가 시간 범위와 서비스명으로 대략적인 프로파일을 찾는다. 정밀도가 낮아지지만 코드 수정 없이도 연결된다.

### Explore에서 트레이스-프로파일 보기

Grafana Explore에서 Tempo 데이터 소스로 TraceQL 검색을 한다. 느린 트레이스를 찾았으면 그 트레이스 뷰 오른쪽에 "Profiles" 탭이 있다. 클릭하면 그 트레이스가 실행된 시간대의 Pyroscope flamegraph가 열린다.

flamegraph에서 어느 함수가 CPU를 먹는지 보이면, 그 함수가 느린 트레이스의 원인인지 아닌지 판단할 수 있다. 트레이스 지연 시간이 400ms인데 flamegraph에서 JSON 마샬링이 200ms 차지하면 최적화 대상이 명확해진다.

---

## 프로덕션 오버헤드

지속적 프로파일링을 도입할 때 가장 먼저 나오는 질문이 "프로덕션에 켜도 괜찮냐"다.

샘플링 프로파일러의 CPU 오버헤드는 샘플링 주파수에 비례한다. 일반적으로 쓰는 100Hz 설정 기준으로 실제 측정한 수치들이다.

**Go (Pyroscope SDK, 100Hz CPU 프로파일)**
- 유휴 상태: 오버헤드 거의 없음 (<0.1%)
- 초당 1만 요청 처리 중: CPU ~1~2% 추가
- 메모리 프로파일 추가 시: 할당 카운팅 오버헤드로 ~3~5% 추가

**Node.js (V8 샘플링, 100Hz)**
- CPU 오버헤드: ~1~3%
- Heap 샘플링 프로파일 추가 시: ~2~4% 추가

**JVM (async-profiler, 100Hz CPU)**
- CPU 프로파일만: ~1~2%
- wall 타입 추가 시: ~2~3%
- alloc 타입 추가 시: 트래픽에 따라 다름. 초당 할당량이 많으면 5~10%까지 올라갈 수 있음.

이 수치는 앱 특성에 따라 달라진다. 초당 할당이 많은 앱에서 alloc 프로파일을 켜면 오버헤드가 커진다. JVM alloc 프로파일링은 처음 프로덕션에 켤 때 10분 정도만 켜고 flamegraph 확인 후 끄거나 샘플링 간격을 늘리는 식으로 접근하는 게 안전하다.

Pyroscope SDK가 서버로 데이터를 보내는 네트워크 오버헤드는 10~15초마다 수십 KB 수준이다. 15초 주기로 보낼 때 초당 약 2~3KB. 무시할 수 있는 수준이다.

**실제로 오버헤드가 문제가 된 사례**: Go 앱에서 `ProfileAllocObjects`와 `ProfileAllocSpace`를 동시에 켰는데 GC 압박이 있는 상태에서 추가로 CPU가 4~5% 올라갔다. CPU 프로파일만 남기고 alloc 프로파일은 꺼서 해결했다. 메모리 릭이 의심될 때만 일시적으로 켜는 식으로 운영한다.

---

## 자주 마주치는 문제

**flamegraph에서 함수명이 `unknown` 또는 주소로 나오는 경우**

Go는 CGO를 쓰는 부분이 심볼이 없으면 주소로 나온다. `-gcflags="-e"` 없이 빌드하거나, 릴리즈 빌드에서 `-ldflags="-s -w"`로 심볼 테이블을 제거하면 이렇게 된다. 프로덕션 Go 바이너리를 `strip`하면 pprof 심볼이 사라지므로 `-ldflags="-w"` 없이 빌드해야 flamegraph가 제대로 나온다.

JVM은 JIT 컴파일된 코드 심볼을 async-profiler가 perf-map 파일로 추출한다. `/tmp/perf-<pid>.map`이 생성되는데, 컨테이너 환경에서 tmpfs 크기 제한이 있으면 이 파일이 잘려 심볼이 유실된다.

**Pyroscope에 데이터가 올라오지 않는 경우**

SDK 로그에서 오류를 확인한다. Go SDK는 `Logger: pyroscope.StandardLogger`를 설정하면 `stderr`에 오류를 출력한다. 가장 흔한 원인은 Pyroscope 서버 주소 오타나 방화벽 차단이다.

Pull 모드라면 Pyroscope 서버 로그에서 scrape 실패 여부를 본다. pprof 엔드포인트가 인증이 필요한 경우 `scrape_configs`에 `basic_auth`나 `bearer_token`을 설정해야 한다.

**goroutine 수가 flamegraph에 안 잡히는 경우**

`ProfileGoroutines`를 설정했는데 goroutine 수가 늘어나는 게 flamegraph에 안 보인다면, goroutine 생성이 sampling 주기보다 빠르게 생겼다가 사라지는 것일 수 있다. goroutine 수 메트릭(`go_goroutines`)으로 먼저 확인하고, 피크 시점에 `/debug/pprof/goroutine?debug=2`를 직접 수집해서 어떤 스택인지 텍스트로 보는 게 더 빠를 때가 있다.

**JVM alloc 프로파일에서 GC 관련 스택만 잔뜩 보이는 경우**

async-profiler가 alloc 프로파일을 수집할 때 TLAB(Thread-Local Allocation Buffer) 외부 할당도 잡는다. GC가 자주 돌면 GC 스레드의 할당이 flamegraph를 가득 채운다. 이런 경우 `PYROSCOPE_PROFILER_ALLOC_INTERVAL`을 높여 큰 할당만 잡도록 임계값을 올린다(기본 512KB, 1MB나 2MB로 올린다).

**Grafana에서 Profiles 탭이 안 보이는 경우**

Grafana 10.3 이상이어야 트레이스-프로파일 연결이 UI에 나온다. 이전 버전은 Explore 패널에서 수동으로 Pyroscope를 열어야 한다. Tempo 데이터 소스 설정의 `tracesToProfiles`에서 `profileTypeId` 형식이 맞는지 확인한다. Pyroscope UI에서 앱 이름과 프로파일 타입 조합을 직접 확인한 후 그 값을 넣어야 한다.
