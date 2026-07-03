---
title: Linkerd 서비스 메시 도입
tags: [infra, service-mesh, linkerd, kubernetes, mtls, observability]
updated: 2026-06-03
---

# Linkerd 서비스 메시 도입

## 1. Linkerd를 선택하는 이유

Service Mesh를 도입할 때 사실상 후보는 Istio와 Linkerd 둘이다. 둘 다 같은 문제(서비스 간 mTLS, 재시도, 트래픽 라우팅, 메트릭)를 푸는데 접근 방식이 다르다.

Istio는 Envoy를 사이드카로 쓰고 기능이 많다. CRD가 수십 개고 VirtualService, DestinationRule, EnvoyFilter까지 익혀야 한다. 처음 도입한 팀은 보통 첫 한 달 동안 yaml만 쓴다.

Linkerd는 의도적으로 기능을 줄였다. 사이드카는 Rust로 작성한 자체 프록시(`linkerd2-proxy`)를 쓰고, mTLS는 기본값이며, 설정 CRD는 손에 꼽는다. 트래픽 분기는 Kubernetes SMI(Service Mesh Interface)의 `TrafficSplit`을 따른다.

실무에서 Linkerd가 적합한 상황은 보통 이런 경우다.

- 마이크로서비스 수가 50개 미만이고 복잡한 라우팅 규칙은 필요 없다
- mTLS와 기본 메트릭(성공률, p99 지연)만 있으면 충분하다
- 사이드카 리소스를 아끼고 싶다 (노드당 파드가 많은 환경)
- 학습 비용을 최소화하고 운영 인원이 1~2명이다

반대로 JWT 기반 인가, 외부 서비스 라우팅, WASM 필터, mTLS 외 ALB 통합 같은 게 필요하면 Istio로 가야 한다.

---

## 2. Linkerd vs Istio: 사이드카 차이

가장 큰 차이는 사이드카 프록시다. Istio의 Envoy는 C++로 작성한 범용 L7 프록시고 기능이 광범위하다. Linkerd2-proxy는 Rust로 작성한 서비스 메시 전용 프록시다.

### 2.1 메모리/CPU 비교

같은 환경(50 RPS, gRPC 트래픽)에서 측정한 사이드카 리소스 사용량은 대략 이렇다.

| 항목 | Linkerd2-proxy | Envoy (Istio) |
|---|---|---|
| 메모리 (idle) | 10~15 MB | 50~70 MB |
| 메모리 (50 RPS) | 20~30 MB | 80~120 MB |
| CPU (idle) | 1~2 mCPU | 5~10 mCPU |
| p99 추가 지연 | 1~2 ms | 3~5 ms |

노드당 파드가 30~40개씩 뜨는 환경에서는 사이드카가 잡아먹는 메모리만 2~3 GB 차이 난다. AWS m5.large 노드 기준으로 보면 무시할 수 없는 수치다.

Rust 기반이라 GC가 없고 메모리 풋프린트가 일정한 것도 장점이다. Envoy는 부하 패턴에 따라 메모리가 들쭉날쭉한데, Linkerd2-proxy는 평탄하다.

### 2.2 기능 차이

```
                Linkerd          Istio
mTLS            기본 on          설정 필요
재시도          ServiceProfile    VirtualService
타임아웃        ServiceProfile    VirtualService
트래픽 분기      TrafficSplit     VirtualService + DestinationRule
JWT 인가        없음              RequestAuthentication
외부 서비스      불가              ServiceEntry
WASM 필터       불가              EnvoyFilter
프로토콜        HTTP/1, HTTP/2, gRPC, TCP    HTTP/1, HTTP/2, gRPC, TCP, MongoDB, Redis 등
```

Linkerd는 HTTP/HTTPS와 gRPC만 제대로 다룬다. MongoDB나 Redis 트래픽도 TCP로는 처리하지만 프로토콜 인식은 안 된다. 메트릭이 필요하면 별도로 익스포터를 붙여야 한다.

---

## 3. 설치 절차

Linkerd 설치는 CLI로 시작한다. Helm으로도 가능하지만 처음 도입한다면 CLI가 편하다.

### 3.1 CLI 설치 및 사전 점검

```bash
# linkerd CLI 설치 (macOS)
brew install linkerd

# 또는 직접 다운로드
curl -sL https://run.linkerd.io/install | sh
export PATH=$PATH:$HOME/.linkerd2/bin

# 버전 확인
linkerd version
# Client version: stable-2.14.10
# Server version: unavailable

# 클러스터가 Linkerd를 설치할 수 있는 상태인지 점검
linkerd check --pre
```

`linkerd check --pre`는 클러스터 권한, 쿠버네티스 버전, 가용 리소스, 인증서 발급 능력을 전부 확인한다. 실패 항목이 있으면 설치해도 컨트롤 플레인이 뜨지 않으니 반드시 통과시켜야 한다.

자주 걸리는 항목은 두 가지다.

- `pre-kubernetes-cluster-setup`에서 cluster role binding 권한 부족 → kubeconfig를 cluster-admin으로 교체
- `pre-kubernetes-capability`에서 PodSecurityPolicy 충돌 → PSP를 제거하거나 Linkerd용 PSP 별도 정의

### 3.2 컨트롤 플레인 설치

Linkerd는 컨트롤 플레인을 두 단계로 나눠서 설치한다. CRD를 먼저 깔고 본체를 깐다.

```bash
# 1단계: CRD 설치
linkerd install --crds | kubectl apply -f -

# 2단계: 컨트롤 플레인 설치
linkerd install | kubectl apply -f -

# 설치 완료 대기 및 검증
linkerd check
```

컨트롤 플레인 구성 요소는 이렇다.

- `linkerd-destination`: 서비스 디스커버리, 정책 결정, 인증서 검증
- `linkerd-identity`: mTLS용 인증서 발급 (CA 역할)
- `linkerd-proxy-injector`: 어드미션 웹훅으로 사이드카 자동 주입

기본값으로 설치하면 컨트롤 플레인 자체가 100~150 MB 메모리를 쓴다. Istio의 1/3 수준이다.

### 3.3 사이드카 주입

Linkerd는 네임스페이스나 파드에 어노테이션을 붙이면 사이드카를 자동으로 주입한다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: payment
  annotations:
    linkerd.io/inject: enabled
```

이미 떠 있는 디플로이먼트라면 롤링 재시작이 필요하다.

```bash
kubectl rollout restart deployment -n payment

# 또는 yaml에 직접 어노테이션 추가
kubectl get deploy -n payment -o yaml \
  | linkerd inject - \
  | kubectl apply -f -
```

주입이 잘 됐는지 확인하는 명령은 `linkerd check --proxy`다. 각 파드의 프록시 버전과 컨트롤 플레인 연결 상태를 점검한다.

---

## 4. mTLS 자동 설정

Linkerd의 mTLS는 별도 설정 없이 동작한다. 사이드카가 주입된 파드끼리 통신하면 자동으로 mTLS가 적용된다. Istio처럼 `PeerAuthentication`을 따로 만들 필요가 없다.

### 4.1 동작 방식

`linkerd-identity`가 클러스터 내부 CA 역할을 한다. 각 사이드카는 시작할 때 ServiceAccount 토큰으로 자신의 신원을 증명하고, identity 컴포넌트로부터 24시간짜리 인증서를 받는다. 이 인증서로 다른 사이드카와 TLS 핸드셰이크를 한다.

```bash
# mTLS가 적용 중인지 실시간 확인
linkerd viz edges deployment -n payment

# 출력 예시
SRC                     DST              SRC_NS    DST_NS   SECURED
checkout                payment-api      checkout  payment  √
order-service           payment-api      order     payment  √
```

`SECURED` 컬럼이 `√`면 mTLS가 적용된 상태다. `-`로 표시되면 한쪽 파드에 사이드카가 없거나 인증서 발급에 실패한 경우다.

### 4.2 trust anchor 만료 문제

기본 설치에서 가장 자주 터지는 사고가 trust anchor 만료다. `linkerd install`로 기본 설치하면 trust anchor의 유효기간이 1년으로 잡힌다. 1년 뒤에 모든 mTLS가 한꺼번에 깨진다.

운영 환경이라면 trust anchor를 직접 만들어서 유효기간을 길게(보통 10년) 가져가야 한다. 발급 인증서(issuer)는 짧게(1년) 유지하면서 정기 교체하면 된다.

```bash
# step CLI로 trust anchor 생성 (10년 유효)
step certificate create root.linkerd.cluster.local ca.crt ca.key \
  --profile root-ca --no-password --insecure \
  --not-after=87600h

# issuer 생성 (1년 유효)
step certificate create identity.linkerd.cluster.local issuer.crt issuer.key \
  --profile intermediate-ca --not-after=8760h --no-password --insecure \
  --ca ca.crt --ca-key ca.key

# 인증서를 지정해서 설치
linkerd install \
  --identity-trust-anchors-file=ca.crt \
  --identity-issuer-certificate-file=issuer.crt \
  --identity-issuer-key-file=issuer.key \
  | kubectl apply -f -
```

issuer 인증서 갱신은 `linkerd upgrade`로 무중단 교체가 가능하다. 다만 trust anchor를 교체하려면 새 anchor를 기존 anchor와 함께 번들로 묶어서 점진적으로 롤아웃해야 한다. 한 번에 교체하면 사이드카끼리 신뢰가 깨져서 전체 트래픽이 멈춘다.

### 4.3 cert-manager 연동

수동 관리가 번거로우면 cert-manager를 붙인다. issuer 인증서를 cert-manager가 자동 갱신하게 만들 수 있다.

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: linkerd-identity-issuer
  namespace: linkerd
spec:
  secretName: linkerd-identity-issuer
  duration: 8760h    # 1년
  renewBefore: 720h  # 만료 30일 전 갱신
  issuerRef:
    name: linkerd-trust-anchor
    kind: ClusterIssuer
  commonName: identity.linkerd.cluster.local
  isCA: true
  privateKey:
    algorithm: ECDSA
```

cert-manager가 갱신한 시크릿을 Linkerd가 인식하려면 `linkerd-identity` 디플로이먼트가 재시작되어야 한다. trust-manager 같은 도구로 자동 재시작까지 묶어두는 게 안전하다.

---

## 5. TrafficSplit으로 카나리 배포

Linkerd는 SMI 표준의 `TrafficSplit`을 따른다. Istio처럼 자체 CRD가 아니라 표준 스펙이라서 Flagger 같은 카나리 자동화 도구와 잘 맞는다.

### 5.1 기본 TrafficSplit

배포 전 v1, 신버전 v2가 있다고 하자. 두 디플로이먼트는 각자 별도 Service로 떠 있어야 한다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: payment-v1
spec:
  selector:
    app: payment
    version: v1
  ports:
    - port: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: payment-v2
spec:
  selector:
    app: payment
    version: v2
  ports:
    - port: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: payment
spec:
  selector:
    app: payment
  ports:
    - port: 8080
```

여기에 TrafficSplit을 붙이면 클라이언트가 `payment` 서비스를 호출할 때 v1/v2로 분기된다.

```yaml
apiVersion: split.smi-spec.io/v1alpha1
kind: TrafficSplit
metadata:
  name: payment-split
  namespace: default
spec:
  service: payment   # 클라이언트가 호출하는 서비스
  backends:
    - service: payment-v1
      weight: 900    # 90%
    - service: payment-v2
      weight: 100    # 10%
```

weight는 가중치라 합이 1000이 아니어도 된다. `900:100`도 되고 `9:1`도 동작한다.

### 5.2 점진적 트래픽 이동

수동 카나리는 weight를 점점 바꾸면 된다.

```bash
# v2를 10%로 시작
kubectl patch trafficsplit payment-split --type='json' \
  -p='[{"op":"replace","path":"/spec/backends/0/weight","value":900},
       {"op":"replace","path":"/spec/backends/1/weight","value":100}]'

# 30분 모니터링 후 50%로 증가
kubectl patch trafficsplit payment-split --type='json' \
  -p='[{"op":"replace","path":"/spec/backends/0/weight","value":500},
       {"op":"replace","path":"/spec/backends/1/weight","value":500}]'

# 안정적이면 100%로
kubectl patch trafficsplit payment-split --type='json' \
  -p='[{"op":"replace","path":"/spec/backends/0/weight","value":0},
       {"op":"replace","path":"/spec/backends/1/weight","value":1000}]'
```

지표가 나빠지면 즉시 weight를 v1로 되돌리면 된다.

### 5.3 Flagger로 자동화

Flagger는 Linkerd 메트릭을 보고 자동으로 weight를 조정한다. 성공률이 임계치 이하로 떨어지면 자동 롤백한다.

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: payment
spec:
  provider: linkerd
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: payment
  service:
    port: 8080
  analysis:
    interval: 30s
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
      - name: request-success-rate
        thresholdRange:
          min: 99
        interval: 1m
      - name: request-duration
        thresholdRange:
          max: 500
        interval: 30s
```

10%씩 올리면서 30초마다 성공률과 지연을 본다. 5번 연속 임계치를 못 넘기면 롤백한다. 임계치는 정확히 동작하는 v1 트래픽을 기준으로 잡아야 한다. 평소 성공률이 99.5%인데 임계치를 99.9%로 잡으면 카나리가 시작도 못 한다.

---

## 6. ServiceProfile로 재시도와 타임아웃

`ServiceProfile`은 Linkerd가 서비스의 API 경로별로 메트릭을 수집하고 재시도/타임아웃을 적용하기 위한 CRD다. 경로별로 그룹화된 메트릭(p99 지연, 성공률)이 나오게 된다.

### 6.1 ServiceProfile 작성

```yaml
apiVersion: linkerd.io/v1alpha2
kind: ServiceProfile
metadata:
  name: payment.default.svc.cluster.local
  namespace: default
spec:
  routes:
    - name: GET /api/payments/{id}
      condition:
        method: GET
        pathRegex: /api/payments/[^/]+
      timeout: 500ms
      isRetryable: true

    - name: POST /api/payments
      condition:
        method: POST
        pathRegex: /api/payments
      timeout: 2s
      isRetryable: false  # 결제 생성은 중복 위험이 있으므로 재시도 금지

  retryBudget:
    retryRatio: 0.2        # 원본 요청의 20%까지만 재시도
    minRetriesPerSecond: 10
    ttl: 10s
```

`retryBudget`은 전체 서비스 차원의 재시도 예산이다. 원본 요청의 20%까지만 추가 재시도를 허용한다. 평소 100 RPS면 추가로 20 RPS까지만 재시도가 발생한다. 장애 시 재시도 폭주로 서비스가 더 망가지는 사고를 막는 안전장치다.

### 6.2 ServiceProfile 자동 생성

수십 개 경로를 일일이 작성하기 힘들면 swagger나 protobuf에서 뽑아낼 수 있다.

```bash
# swagger에서 추출
linkerd profile -n default \
  --open-api ./openapi.yaml \
  payment > payment-profile.yaml

# 실제 트래픽에서 추출 (10초간 관찰)
linkerd profile -n default \
  --tap deploy/payment \
  --tap-duration 10s \
  payment > payment-profile.yaml
```

`--tap`은 실제 운영 트래픽을 보고 경로를 추출한다. 처음 도입할 때 가장 빠르게 ServiceProfile을 만드는 방법이다. 다만 트래픽이 적은 경로는 누락되니 생성 후 사람이 확인해야 한다.

### 6.3 isRetryable 주의사항

`isRetryable: true`로 설정한 경로는 5xx 응답이 오면 자동으로 재시도된다. 멱등하지 않은 API(POST/PATCH/PUT 일부)에 켜두면 중복 처리 사고가 난다.

실무에서 안전한 기준은 이렇다.

- GET, HEAD: 켜도 됨
- DELETE: 백엔드가 멱등하면 켜도 됨 (이미 삭제된 경우 200 또는 404 반환)
- POST: 멱등키(Idempotency-Key)를 지원할 때만 켬
- PATCH/PUT: 백엔드 검증 후 결정

---

## 7. Viz 확장으로 메트릭 수집

Linkerd 기본 설치에는 메트릭 UI가 없다. `linkerd-viz` 확장을 별도로 깔아야 한다.

```bash
linkerd viz install | kubectl apply -f -
linkerd viz check
```

Viz는 Prometheus, Grafana, 자체 대시보드를 같이 깐다. 기본 retention은 6시간이라 장기 보관이 필요하면 외부 Prometheus로 메트릭을 보내야 한다.

### 7.1 핵심 CLI 명령

```bash
# 네임스페이스 단위 통계
linkerd viz stat deploy -n payment

# 출력 예시
NAME           MESHED   SUCCESS    RPS   LATENCY_P50   LATENCY_P95   LATENCY_P99
payment-api    3/3      99.50%   42.1     12ms          45ms          120ms
order-api      2/2      100.00%  18.3      8ms          22ms           55ms

# 실시간 요청 로그
linkerd viz tap deploy/payment-api -n payment

# 서비스 간 연결 확인
linkerd viz edges deploy -n payment

# 경로별 통계 (ServiceProfile이 있어야 동작)
linkerd viz routes svc/payment -n default
```

`linkerd viz stat`의 `MESHED` 컬럼이 가장 먼저 확인할 항목이다. `3/3`이면 모든 파드에 사이드카가 주입된 상태고, `2/3`이면 파드 하나가 사이드카 없이 떠 있다는 뜻이다.

### 7.2 외부 Prometheus 연동

운영 환경에서는 Viz 내장 Prometheus 말고 기존 Prometheus를 쓰고 싶을 때가 많다. 이때는 federation으로 메트릭을 가져오거나, Viz 설치 시 외부 Prometheus를 지정한다.

```bash
linkerd viz install \
  --set prometheusUrl=http://prometheus.monitoring:9090 \
  --set prometheus.enabled=false \
  | kubectl apply -f -
```

기존 Prometheus가 Linkerd의 사이드카 메트릭(`/metrics` 엔드포인트)을 스크랩하도록 ServiceMonitor를 설정해야 한다.

---

## 8. 실무에서 겪는 문제와 해결법

### 8.1 사이드카 메모리 누수

stable 버전에서도 가끔 사이드카 메모리가 천천히 증가하는 현상이 나온다. 원인은 보통 두 가지다.

장시간 유지되는 gRPC 스트림이 많은 경우, 스트림별 상태 관리에서 누수가 발생한다. 특히 양방향 스트리밍에서 클라이언트가 정상 종료 없이 끊으면 사이드카가 일부 리소스를 회수하지 못한다.

해결책은 사이드카에 메모리 limit을 설정하고 OOM으로 죽으면 재시작되게 만드는 거다. 이상적이진 않지만 stable 버전이 나올 때까지 임시방편이다.

```yaml
metadata:
  annotations:
    config.linkerd.io/proxy-memory-limit: "250Mi"
    config.linkerd.io/proxy-memory-request: "30Mi"
    config.linkerd.io/proxy-cpu-limit: "500m"
    config.linkerd.io/proxy-cpu-request: "10m"
```

메모리 증가가 심한 파드를 찾으려면 이렇게 본다.

```bash
kubectl top pod -n payment --containers \
  | grep linkerd-proxy \
  | sort -k4 -h -r \
  | head -10
```

특정 파드만 메모리가 튀면 그 파드의 트래픽 패턴(긴 스트림, 대량 헤더)을 분석해야 한다.

### 8.2 인증서 갱신 실패

trust anchor가 만료 직전인데 갱신이 실패하는 경우가 있다. 증상은 새로 뜨는 파드의 사이드카가 인증서를 못 받아서 `linkerd check`에서 identity 컴포넌트 오류가 뜬다.

원인은 보통 세 가지다.

첫째, cert-manager가 트리거되지 않은 경우. `kubectl describe certificate linkerd-identity-issuer -n linkerd`로 갱신 시각을 확인한다. cert-manager 컨트롤러가 죽어 있거나 RBAC가 빠지면 갱신이 안 된다.

둘째, 새 인증서를 만들었지만 `linkerd-identity` 디플로이먼트가 재시작되지 않은 경우. 시크릿이 바뀌어도 파드는 메모리에 기존 인증서를 갖고 있다.

```bash
kubectl rollout restart deploy/linkerd-identity -n linkerd
```

셋째, trust anchor와 issuer 체인이 깨진 경우. 새 issuer가 새 trust anchor로 서명됐는데 기존 사이드카는 옛 trust anchor만 신뢰한다. 이때는 trust anchor 번들(옛 anchor + 새 anchor)을 만들어서 점진 롤아웃해야 한다.

```bash
# 옛 인증서와 새 인증서를 한 파일로 합침
cat old-ca.crt new-ca.crt > bundle.crt

# 번들을 적용해서 양쪽 anchor를 모두 신뢰하게 만듦
linkerd upgrade --identity-trust-anchors-file=bundle.crt \
  | kubectl apply -f -

# 모든 사이드카가 번들을 받은 뒤(보통 24시간 후) 옛 anchor 제거
linkerd upgrade --identity-trust-anchors-file=new-ca.crt \
  | kubectl apply -f -
```

이 순서를 지키지 않으면 전체 클러스터의 mTLS가 한 번에 멈춘다. 운영 환경에서 가장 무서운 사고다.

### 8.3 multi-cluster trust anchor 충돌

Linkerd의 multi-cluster 기능은 서로 다른 클러스터의 서비스를 mTLS로 연결한다. 두 클러스터를 묶을 때 가장 흔한 문제가 trust anchor 충돌이다.

각 클러스터를 따로 설치하면서 기본값으로 trust anchor를 생성한 경우, 두 클러스터의 anchor가 다르다. 이 상태로 `linkerd multicluster link`를 하면 게이트웨이끼리 mTLS 핸드셰이크가 실패한다.

해결책은 처음부터 공통 trust anchor를 만들어서 양쪽 클러스터에 동일하게 설치하는 거다.

```bash
# 한 번만 생성
step certificate create root.linkerd.cluster.local \
  shared-ca.crt shared-ca.key \
  --profile root-ca --no-password --insecure \
  --not-after=87600h

# 클러스터 A에서 사용할 issuer
step certificate create identity.linkerd.cluster.local \
  cluster-a-issuer.crt cluster-a-issuer.key \
  --profile intermediate-ca --not-after=8760h --no-password --insecure \
  --ca shared-ca.crt --ca-key shared-ca.key

# 클러스터 B에서 사용할 issuer
step certificate create identity.linkerd.cluster.local \
  cluster-b-issuer.crt cluster-b-issuer.key \
  --profile intermediate-ca --not-after=8760h --no-password --insecure \
  --ca shared-ca.crt --ca-key shared-ca.key

# 각 클러스터에 동일한 trust anchor + 서로 다른 issuer로 설치
# 클러스터 A
linkerd install \
  --identity-trust-anchors-file=shared-ca.crt \
  --identity-issuer-certificate-file=cluster-a-issuer.crt \
  --identity-issuer-key-file=cluster-a-issuer.key \
  --cluster-domain=cluster.local \
  --identity-trust-domain=cluster.local \
  | kubectl --context=cluster-a apply -f -
```

이미 다른 trust anchor로 양쪽이 설치되어 있다면 한 쪽의 trust anchor를 다른 쪽 anchor와 번들로 합치고, 점진적으로 issuer를 교체해야 한다. 운영 클러스터라면 무중단으로 가야 하니 이 작업은 최소 일주일 일정으로 잡는 게 안전하다.

multi-cluster 게이트웨이가 정상인지 확인하는 명령은 이렇다.

```bash
linkerd --context=cluster-a multicluster check
linkerd --context=cluster-a multicluster gateways
```

`gateways` 출력에서 `ALIVE` 컬럼이 `True`고 `NUM_SVC`가 0보다 크면 정상이다. `ALIVE`가 `False`면 보통 trust anchor 문제 아니면 게이트웨이 LoadBalancer가 외부 IP를 못 받은 경우다.

### 8.4 사이드카가 일부 트래픽을 못 잡는 경우

사이드카는 iptables 규칙으로 모든 트래픽을 가로채는데, 컨테이너가 사이드카보다 먼저 시작해서 트래픽을 보내면 일부 요청이 그냥 빠져나간다. Init 컨테이너에서 외부 API를 호출하는 경우 자주 발생한다.

해결책은 `linkerd-await`를 init 컨테이너 앞에 두거나, 사이드카가 먼저 준비되도록 어노테이션을 붙이는 거다.

```yaml
metadata:
  annotations:
    config.linkerd.io/proxy-await: "enabled"
```

이 어노테이션을 붙이면 메인 컨테이너가 사이드카의 준비 상태를 기다린 뒤 시작한다. Kubernetes 1.28부터는 sidecar container가 정식 기능으로 들어와서 이 문제가 자동 해결되지만, 그 이전 버전에서는 명시적으로 켜야 한다.
