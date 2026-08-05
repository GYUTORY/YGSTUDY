---
title: Envoy
tags:
  - infra
  - load-balancer
  - envoy
  - proxy
  - service-mesh
  - xds
updated: 2026-06-22
---

# Envoy

## Envoy를 만지게 되는 상황

HAProxy나 nginx로 충분한 환경이라면 Envoy를 굳이 꺼낼 일이 없다. Envoy가 들어오는 건 대개 두 경로다. 하나는 Istio나 Linkerd 같은 서비스 메시를 도입했더니 사이드카로 Envoy가 깔려 있어서 어쩔 수 없이 만지게 되는 경우, 다른 하나는 gRPC 트래픽을 제대로 분산해야 하는데 기존 LB로는 한계를 느낀 경우다.

gRPC는 HTTP/2 위에서 동작하고, HTTP/2는 하나의 TCP 커넥션에 여러 요청을 멀티플렉싱한다. HAProxy를 L4 모드로 쓰면 커넥션 단위로만 분산하니까, 클라이언트가 한 번 커넥션을 맺으면 그 뒤 모든 gRPC 호출이 같은 백엔드로 쏠린다. Envoy는 HTTP/2를 이해해서 같은 커넥션 안의 개별 스트림을 서로 다른 백엔드로 나눠 보낸다. 이게 처음 Envoy를 진지하게 보게 되는 결정적 이유인 경우가 많다.

Lyft에서 만들어 CNCF에 기부한 프로젝트고, C++로 작성됐다. 설정을 YAML이나 JSON으로 정적으로 줄 수도 있고, gRPC API로 런타임에 동적으로 밀어넣을 수도 있다. 이 동적 설정 기능이 서비스 메시의 컨트롤플레인이 데이터플레인을 제어하는 핵심 통로다.

## L4와 L7을 한 프로세스에서

Envoy는 L4(TCP/UDP) 프록시와 L7(HTTP) 프록시를 같은 바이너리에서 처리한다. 둘의 차이는 어떤 필터 체인을 listener에 붙이느냐로 결정된다.

L4 프록시는 TCP 페이로드를 들여다보지 않고 바이트 스트림을 그대로 흘려보낸다. `tcp_proxy` 필터를 쓴다. MySQL, Redis, 암호화된 패스스루 같은 트래픽에 쓴다.

L7 프록시는 HTTP 메시지를 파싱해서 경로, 헤더, 메서드를 보고 라우팅한다. `http_connection_manager` 필터를 쓰고, 이 안에 다시 라우팅 테이블과 여러 HTTP 필터가 들어간다. 경로 기반 라우팅, 헤더 조작, 재시도, 타임아웃, 인증 같은 게 전부 L7에서 일어난다.

같은 Envoy 인스턴스가 80번 포트는 L7으로, 3306번 포트는 L4로 동시에 처리하게 만들 수 있다. listener를 포트마다 따로 정의하면 된다.

## 설정의 네 기둥: listener, filter, cluster, route

Envoy 설정을 처음 보면 HAProxy의 frontend/backend처럼 한눈에 들어오지 않는다. 개념이 더 잘게 쪼개져 있어서다. 핵심은 네 개다.

- **listener**: 어느 주소/포트에서 요청을 받을지. HAProxy의 frontend에 해당한다.
- **filter chain**: listener로 들어온 트래픽을 어떻게 처리할지. L4면 `tcp_proxy`, L7이면 `http_connection_manager`.
- **route**: L7에서 어떤 요청을 어느 cluster로 보낼지. 경로/헤더 매칭 규칙.
- **cluster**: 실제 백엔드 서버 묶음(upstream). HAProxy의 backend에 해당한다. 여기에 엔드포인트 목록, 로드밸런싱 정책, 헬스체크, 서킷브레이커가 붙는다.

요청은 `listener → filter chain → route → cluster → endpoint` 순서로 흘러간다. listener가 입구, cluster가 출구라고 보면 된다.

```yaml
static_resources:
  listeners:
  - name: listener_http
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 10000
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: ingress_http
          route_config:
            name: local_route
            virtual_hosts:
            - name: backend
              domains: ["*"]
              routes:
              - match:
                  prefix: "/"
                route:
                  cluster: service_backend
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router

  clusters:
  - name: service_backend
    connect_timeout: 1s
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: service_backend
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: backend.internal
                port_value: 8080
```

처음 이 YAML을 마주하면 `typed_config`와 `"@type"` 라인 때문에 질린다. 이건 Envoy 설정이 내부적으로 protobuf 메시지라서 그렇다. YAML은 protobuf를 사람이 쓰기 위한 표현일 뿐이고, `"@type"`은 이 블록을 어떤 protobuf 메시지로 해석할지 지정하는 타입 URL이다. 손으로 다 외울 수 없으니 공식 문서의 예제를 복사해서 고치는 식으로 작업하게 된다.

버전 표기(`v3`)도 주의해야 한다. Envoy는 API 버전을 올리면서 v2를 완전히 제거했다. 인터넷에 떠도는 오래된 예제가 `v2` 타입 URL을 쓰고 있으면 최신 Envoy에서 그대로 안 뜬다.

## cluster의 타입과 엔드포인트 발견

cluster의 `type`은 엔드포인트를 어떻게 알아내는지를 정한다.

- `STATIC`: IP를 설정에 직접 박는다.
- `STRICT_DNS`: DNS 이름을 주기적으로 조회해서 A 레코드 전부를 엔드포인트로 쓴다. 쿠버네티스 헤드리스 서비스와 잘 맞는다.
- `LOGICAL_DNS`: DNS를 조회하되 첫 응답 하나만 새 커넥션용으로 쓴다. 엔드포인트가 많은 외부 서비스(예: 대형 클라우드 API)에 쓴다.
- `EDS`: Endpoint Discovery Service. 엔드포인트 목록을 xDS API로 외부에서 받아온다. 서비스 메시가 이걸 쓴다.

`STRICT_DNS`를 쓸 때 자주 겪는 문제가 DNS TTL과 Envoy의 갱신 주기 불일치다. 백엔드 파드가 죽고 새 IP로 떴는데 Envoy가 옛 IP를 계속 들고 있으면 503이 난다. `dns_refresh_rate`를 짧게 주거나 헬스체크로 죽은 엔드포인트를 빨리 빼야 한다.

## xDS: 설정을 런타임에 밀어넣기

Envoy의 진짜 차별점은 설정을 재시작 없이 동적으로 바꾸는 xDS API다. x는 와일드카드고, 각 리소스 종류마다 Discovery Service가 있다.

- **LDS** (Listener Discovery Service): listener
- **RDS** (Route Discovery Service): route
- **CDS** (Cluster Discovery Service): cluster
- **EDS** (Endpoint Discovery Service): endpoint
- **SDS** (Secret Discovery Service): TLS 인증서

이것들을 한 스트림으로 묶은 게 **ADS**(Aggregated Discovery Service)다. ADS를 쓰면 cluster가 만들어지기 전에 route가 그 cluster를 참조하는 순서 꼬임을 막을 수 있다. 서비스 메시에서는 거의 ADS를 쓴다.

동작 방식은 이렇다. Envoy가 부팅하면 부트스트랩 설정에 적힌 컨트롤플레인(xDS 서버)으로 gRPC 스트림을 연다. 컨트롤플레인은 현재 상태를 push하고, 이후 변경이 생길 때마다 새 설정을 push한다. Envoy는 받은 설정을 검증하고 적용한다. 백엔드 파드가 하나 추가되면 컨트롤플레인이 EDS로 새 엔드포인트를 밀어넣고, Envoy는 다음 요청부터 그 파드로도 트래픽을 보낸다. 재시작이 없다.

```yaml
# 부트스트랩에서 컨트롤플레인을 가리키는 부분
dynamic_resources:
  ads_config:
    api_type: GRPC
    transport_api_version: V3
    grpc_services:
    - envoy_grpc:
        cluster_name: xds_cluster
  cds_config:
    ads: {}
  lds_config:
    ads: {}

static_resources:
  clusters:
  - name: xds_cluster
    connect_timeout: 1s
    type: STRICT_DNS
    typed_extension_protocol_options:
      envoy.extensions.upstreams.http.v3.HttpProtocolOptions:
        "@type": type.googleapis.com/envoy.extensions.upstreams.http.v3.HttpProtocolOptions
        explicit_http_config:
          http2_protocol_options: {}
    load_assignment:
      cluster_name: xds_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: control-plane.internal
                port_value: 18000
```

xDS 서버는 직접 구현할 일이 거의 없다. Istio의 istiod, Linkerd의 destination 컨트롤러가 그 역할을 한다. 직접 만든다면 Go의 `go-control-plane` 라이브러리를 쓴다. 다만 디버깅할 때 Envoy가 어떤 xDS 리소스를 받았는지는 자주 확인하게 된다(아래 admin 인터페이스 참고).

## HAProxy, nginx와 무엇이 다른가

세 도구 다 리버스 프록시이자 로드밸런서지만 출발점이 다르다.

nginx는 웹서버다. 정적 파일 서빙, FastCGI, 리버스 프록시를 다 하지만 로드밸런싱은 그중 하나다. 설정 변경하면 보통 reload가 필요하고, reload는 워커를 새로 띄우는 방식이라 동적이긴 해도 외부 API로 실시간 조작하는 모델은 아니다.

HAProxy는 로드밸런서/프록시 전용으로, LB 기능의 밀도가 높다. Runtime API로 서버를 빼고 넣는 건 되지만, 전체 설정 토폴로지를 외부에서 실시간으로 재구성하는 용도는 아니다.

Envoy는 처음부터 "동적으로 제어되는 데이터플레인"으로 설계됐다. xDS로 listener/cluster/route를 통째로 갈아끼울 수 있고, HTTP/2와 gRPC를 1급 시민으로 다룬다. 관측성도 깊어서 cluster별/엔드포인트별 통계를 수백 개씩 뽑아낸다.

정리하면, 단순 L4/L7 분산이면 HAProxy나 nginx가 가볍고 충분하다. gRPC 멀티플렉싱 분산, 또는 컨트롤플레인이 데이터플레인을 동적으로 조종하는 구조가 필요하면 Envoy를 쓴다. 메모리 사용량은 Envoy가 가장 무겁다. 사이드카로 파드마다 한 개씩 붙으면 그 오버헤드가 누적된다.

## 서비스 메시의 데이터플레인으로 쓰이는 이유

Istio나 Linkerd 같은 메시는 트래픽 제어 로직을 애플리케이션 밖으로 빼낸다. 각 파드 옆에 프록시(사이드카)를 붙이고, 파드가 주고받는 모든 트래픽을 그 프록시가 가로채서 라우팅, 재시도, mTLS, 관측을 처리한다.

이 사이드카 자리에 Envoy가 들어간다(Linkerd는 자체 경량 프록시를 쓰지만, Istio는 Envoy를 그대로 쓴다). 이유는 xDS다. 컨트롤플레인이 수천 개의 사이드카에 설정을 일관되게 push하려면 데이터플레인이 동적 설정 프로토콜을 표준으로 지원해야 한다. Envoy의 xDS가 사실상 그 표준이 됐다. 새 프록시를 만드는 것보다 검증된 Envoy를 데이터플레인으로 채택하고 컨트롤플레인만 만드는 게 현실적이라 많은 메시가 이 길을 택했다.

실무에서 Istio를 운영하다 문제가 생기면 결국 Envoy 설정과 통계를 들여다보게 된다. istioctl이 추상화를 제공하지만, 503이 왜 나는지 끝까지 추적하려면 사이드카 Envoy의 admin 인터페이스에서 실제로 어떤 cluster와 route가 적용됐는지 확인해야 하는 경우가 많다.

## 헬스체크

cluster에 active health check를 붙이면 Envoy가 주기적으로 엔드포인트를 직접 찔러보고 죽은 엔드포인트를 풀에서 뺀다.

```yaml
clusters:
- name: service_backend
  connect_timeout: 1s
  type: STRICT_DNS
  lb_policy: ROUND_ROBIN
  health_checks:
  - timeout: 1s
    interval: 5s
    unhealthy_threshold: 3
    healthy_threshold: 2
    http_health_check:
      path: /healthz
  load_assignment:
    cluster_name: service_backend
    endpoints:
    - lb_endpoints:
      - endpoint:
          address:
            socket_address:
              address: backend.internal
              port_value: 8080
```

active 헬스체크와 별개로 **outlier detection**(passive health check)이 있다. 이건 별도 프로브를 보내지 않고, 실제 트래픽에서 특정 엔드포인트가 연속으로 5xx나 커넥션 실패를 내면 일시적으로 풀에서 빼는 방식이다. eject(추방) 시간이 지나면 다시 넣어보고, 또 실패하면 더 오래 뺀다.

```yaml
  outlier_detection:
    consecutive_5xx: 5
    interval: 10s
    base_ejection_time: 30s
    max_ejection_percent: 50
```

`max_ejection_percent`를 꼭 챙겨야 한다. 이걸 안 막으면 일시적으로 백엔드 전체가 5xx를 뱉을 때(예: DB 장애로 모든 인스턴스가 동시에 에러) Envoy가 엔드포인트를 100% 빼버리고, 그 순간 보낼 곳이 없어서 장애가 더 커진다. 50%로 막으면 절반은 남겨둔다.

## 서킷브레이커

Envoy의 서킷브레이커는 흔히 생각하는 "에러율 임계치 넘으면 차단"이 아니라, cluster로 향하는 동시 요청/커넥션 수의 상한선이다. 상한을 넘으면 그 위 요청은 즉시 503으로 떨군다(overflow). 백엔드가 느려질 때 요청이 무한정 쌓여서 메모리가 터지거나 전체가 같이 죽는 걸 막는 장치다.

```yaml
  circuit_breakers:
    thresholds:
    - priority: DEFAULT
      max_connections: 1024
      max_pending_requests: 256
      max_requests: 1024
      max_retries: 3
```

`max_pending_requests`가 자주 놓치는 항목이다. 백엔드 처리가 느려지면 대기 큐에 요청이 쌓이는데, 이 값이 너무 크면 큐가 길어져서 응답 지연이 누적되고 사용자는 타임아웃을 본다. 차라리 빨리 503을 주고 클라이언트가 재시도하거나 폴백하게 만드는 편이 나은 상황이 있다. 값을 낮게 잡으면 빨리 떨구고, 높게 잡으면 오래 버틴다. 트래픽 패턴 보고 조정해야 한다.

서킷브레이커가 동작했는지는 `upstream_rq_pending_overflow`, `upstream_cx_overflow` 통계로 확인한다.

## 재시도

재시도는 route 레벨에 설정한다. 어떤 조건일 때 몇 번 재시도할지 정한다.

```yaml
routes:
- match:
    prefix: "/"
  route:
    cluster: service_backend
    retry_policy:
      retry_on: "5xx,reset,connect-failure"
      num_retries: 2
      per_try_timeout: 1s
```

`retry_on` 조건을 신중히 골라야 한다. `5xx`를 넣으면 500도 재시도하는데, 500이 멱등하지 않은 POST에서 나면 같은 작업을 두 번 실행하는 사고가 난다. 보통은 `connect-failure`, `reset`, `retriable-status-codes`(503 같은 명백히 일시적인 것)만 켜고, 멱등하지 않은 메서드는 재시도에서 빼는 식으로 간다.

`per_try_timeout`과 전체 route timeout 관계도 함정이다. route 전체 타임아웃이 1초인데 per_try가 1초면, 첫 시도가 1초를 다 쓰고 나면 재시도할 시간이 없다. 전체 타임아웃은 `per_try_timeout × (num_retries + 1)`보다 넉넉하게 잡아야 재시도가 의미 있게 동작한다.

재시도는 서킷브레이커의 `max_retries`와도 엮인다. 백엔드가 전반적으로 흔들릴 때 모든 요청이 동시에 재시도하면 retry storm이 일어나 백엔드를 더 밀어붙인다. `max_retries`로 동시 재시도 총량을 제한해서 이걸 막는다.

## envoy.yaml 작성 시 자주 밟는 지뢰

**들여쓰기와 타입 URL.** YAML 들여쓰기 한 칸 틀리면 설정이 통째로 무시되거나 부팅이 안 된다. `"@type"` 한 줄 빠지면 그 블록 전체를 파싱 못 한다. 에러 메시지가 protobuf 필드 경로로 나와서 처음엔 어디가 문제인지 잘 안 보인다.

**static과 dynamic 혼용.** `static_resources`에 정의한 cluster와 xDS로 받는 cluster를 섞어 쓸 때, 같은 이름이 충돌하거나 route가 아직 안 온 cluster를 참조하면 NACK(설정 거부)이 난다. 부트스트랩에 필요한 최소한(xDS 서버용 cluster 등)만 static으로 두고 나머지는 동적으로 받는 게 깔끔하다.

**HTTP/2 명시.** 업스트림이 gRPC면 cluster에 `http2_protocol_options`를 명시해야 한다. 안 그러면 Envoy가 HTTP/1.1로 붙으려다 깨진다. xDS 서버용 cluster도 gRPC라 같은 설정이 필요하다.

**설정 검증을 부팅 전에.** 배포 전에 `envoy --mode validate -c envoy.yaml`로 설정만 검사할 수 있다. 실제 포트를 안 열고 파싱/검증만 한다. CI에 넣어두면 깨진 설정을 프로덕션 전에 잡는다.

**타임아웃 기본값.** route의 기본 timeout은 15초다. gRPC 스트리밍이나 SSE처럼 오래 열려 있어야 하는 연결은 이 기본값 때문에 15초마다 끊긴다. 스트리밍 route는 `timeout: 0s`로 끄거나 충분히 길게 잡아야 한다.

## admin 인터페이스로 디버깅

Envoy 디버깅의 출발점은 admin 인터페이스다. 부트스트랩에 admin을 열어둔다.

```yaml
admin:
  address:
    socket_address:
      address: 127.0.0.1
      port_value: 9901
```

운영에서 admin 포트를 외부에 열면 안 된다. `/quitquitquit` 같은 위험한 엔드포인트가 있어서 누구나 프로세스를 죽일 수 있다. localhost나 사이드카 내부에서만 접근하게 막는다.

자주 쓰는 엔드포인트:

- `GET /config_dump` — Envoy가 현재 들고 있는 전체 설정. xDS로 받은 게 실제로 반영됐는지 여기서 확인한다. Istio에서 "내가 설정한 VirtualService가 진짜 적용됐나"를 끝까지 추적할 때 본다.
- `GET /clusters` — 모든 cluster와 엔드포인트, 각각의 health 상태. 어떤 엔드포인트가 outlier로 빠졌는지, healthy한 게 몇 개인지 보인다.
- `GET /listeners` — 떠 있는 listener 목록과 바인딩된 주소.
- `GET /stats` — 통계 전부. 텍스트로 수백~수천 줄 나온다.
- `GET /stats/prometheus` — 프로메테우스 포맷. 모니터링에 이걸 스크랩한다.
- `GET /server_info` — Envoy 버전, 상태(LIVE/DRAINING), 빌드 정보.
- `POST /logging?level=debug` — 런타임에 로그 레벨 변경. 재시작 없이 디버그 로그를 잠깐 켰다가 끈다.

## 통계 읽는 법

`/stats`에서 503의 원인을 좁혀나간다. 이름 규칙이 일정해서 패턴만 알면 읽기 쉽다.

- `cluster.<name>.upstream_rq_503` — 해당 cluster에서 나온 503 수.
- `cluster.<name>.upstream_cx_connect_fail` — 업스트림 커넥션 실패. 백엔드가 죽었거나 방화벽에 막혔을 때 는다.
- `cluster.<name>.upstream_rq_pending_overflow` — 서킷브레이커의 pending 한도 초과로 떨군 요청. 이게 늘면 `max_pending_requests`를 의심한다.
- `cluster.<name>.upstream_rq_retry` — 재시도 횟수. retry storm 의심될 때 본다.
- `cluster.<name>.membership_healthy` / `membership_total` — healthy 엔드포인트 수 / 전체. healthy가 0이면 헬스체크나 DNS를 의심한다.
- `cluster.<name>.upstream_rq_timeout` — 업스트림 타임아웃.

503이 났을 때 응답 헤더의 `x-envoy-upstream-service-time`과 함께, 응답 본문에 Envoy가 붙이는 플래그(`UH`=healthy 엔드포인트 없음, `UO`=outlier로 추방됨, `URX`=재시도 한도 초과 등)를 access log에 찍어두면 원인 분류가 빨라진다. access log 포맷에 `%RESPONSE_FLAGS%`를 넣는다.

```yaml
# http_connection_manager 안
access_log:
- name: envoy.access_loggers.stdout
  typed_config:
    "@type": type.googleapis.com/envoy.extensions.access_loggers.stream.v3.StdoutAccessLog
    log_format:
      text_format_source:
        inline_string: "[%START_TIME%] %REQ(:METHOD)% %REQ(:PATH)% %RESPONSE_CODE% %RESPONSE_FLAGS% %DURATION%ms cluster=%UPSTREAM_CLUSTER%\n"
```

이 RESPONSE_FLAGS 한 글자가 디버깅 시간을 크게 줄인다. `UH`면 백엔드 발견/헬스체크 문제, `UO`면 outlier detection이 너무 공격적인 것, `URX`나 `UF`면 업스트림 자체 문제로 방향을 바로 잡을 수 있다.
