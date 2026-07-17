---
title: Traefik on Kubernetes
tags:
  - infra
  - load-balancer
  - traefik
  - kubernetes
  - ingress
  - crd
  - cert-manager
updated: 2026-07-17
---

# Traefik on Kubernetes

## 표준 Ingress와 IngressRoute CRD

쿠버네티스 클러스터에 Traefik를 설치하면 두 가지 방식으로 라우팅을 정의할 수 있다. 표준 `Ingress` 리소스를 쓰는 방법과, Traefik가 자체 정의한 CRD인 `IngressRoute`를 쓰는 방법이다.

표준 Ingress는 쿠버네티스 코어 스펙이라 다른 인그레스 컨트롤러(nginx, Contour 등)로 갈아타도 YAML을 대부분 재사용할 수 있다. 반면 Traefik 특화 기능인 Middleware 체이닝, TCP 라우팅, TLS 옵션 세부 제어 같은 것들은 어노테이션으로 집어넣어야 해서 어노테이션이 길어지고 읽기 어려워진다.

```yaml
# 표준 Ingress
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  namespace: production
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
    traefik.ingress.kubernetes.io/router.middlewares: production-strip-prefix@kubernetescrd
spec:
  ingressClassName: traefik
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /v1
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 8080
  tls:
    - hosts:
        - api.example.com
      secretName: api-tls-secret
```

`IngressRoute`는 표준 Ingress의 어노테이션 한계를 넘기 위해 Traefik가 설계한 CRD다. 라우팅 규칙, 미들웨어 참조, TLS 옵션이 하나의 YAML 안에 구조적으로 들어간다.

```yaml
# IngressRoute CRD
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: api-ingressroute
  namespace: production
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`api.example.com`) && PathPrefix(`/v1`)
      kind: Rule
      middlewares:
        - name: strip-prefix
          namespace: production
      services:
        - name: api-service
          port: 8080
  tls:
    secretName: api-tls-secret
```

두 방식의 차이가 크게 체감되는 지점은 복잡한 라우팅이다. 미들웨어를 두세 개 이상 엮거나, TCP와 HTTP 라우팅을 섞거나, TLS 파라미터를 세밀하게 제어해야 하면 IngressRoute가 훨씬 관리하기 쉽다. 반면 팀이 인그레스 컨트롤러를 Traefik로 고정하지 않았거나 GitOps 도구가 표준 Ingress를 기준으로 동작한다면 표준 Ingress를 유지하는 게 낫다.

실무에서는 표준 Ingress로 시작했다가 Middleware 어노테이션이 길어지면서 IngressRoute로 옮기는 경우가 많다. 한 클러스터 안에서 두 방식을 혼용해도 되지만, 팀 내에서 통일하지 않으면 누군가 표준 Ingress를 수정할 때 IngressRoute 동작을 모르고 서로 간섭하는 상황이 생긴다.

## Middleware CRD 정의와 참조

쿠버네티스 환경에서 미들웨어는 `Middleware` CRD로 별도 리소스를 만들고 IngressRoute에서 참조한다.

```yaml
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: strip-prefix
  namespace: production
spec:
  stripPrefix:
    prefixes:
      - /v1
---
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: rate-limit
  namespace: production
spec:
  rateLimit:
    average: 100
    burst: 50
---
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: secure-headers
  namespace: production
spec:
  headers:
    stsSeconds: 31536000
    stsIncludeSubdomains: true
    contentTypeNosniff: true
    frameDeny: true
```

IngressRoute에서 여러 미들웨어를 엮을 때는 `middlewares` 배열에 순서대로 나열한다. Traefik는 배열 순서대로 요청을 통과시킨다.

```yaml
spec:
  routes:
    - match: Host(`api.example.com`)
      kind: Rule
      middlewares:
        - name: rate-limit
          namespace: production
        - name: strip-prefix
          namespace: production
        - name: secure-headers
          namespace: production
      services:
        - name: api-service
          port: 8080
```

`namespace` 필드를 생략하면 IngressRoute와 같은 네임스페이스에서 찾는다. 다른 네임스페이스의 Middleware를 참조하려면 명시해야 하는데, 이게 기본적으로 막혀 있다. Traefik Helm values에서 `providers.kubernetescrd.allowCrossNamespace: true`를 켜야 다른 네임스페이스 참조가 열린다. 이 설정 없이 다른 네임스페이스 미들웨어를 참조하면 미들웨어를 못 찾는 에러가 나고 라우팅이 500을 반환한다.

## IngressRouteTCP와 IngressRouteUDP

HTTP가 아닌 TCP/UDP 서비스를 라우팅할 때 `IngressRouteTCP`와 `IngressRouteUDP`를 쓴다. 데이터베이스 직접 노출, 커스텀 바이너리 프로토콜, 게임 서버 UDP 트래픽 같은 경우다.

```yaml
# TCP 라우팅 — SNI 기반
apiVersion: traefik.io/v1alpha1
kind: IngressRouteTCP
metadata:
  name: postgres-route
  namespace: database
spec:
  entryPoints:
    - postgres        # 정적 설정에서 5432 포트로 열어 둔 EntryPoint
  routes:
    - match: HostSNI(`db.internal.example.com`)
      services:
        - name: postgres-service
          port: 5432
  tls:
    passthrough: true  # TLS를 Traefik가 종료하지 않고 백엔드로 그대로 넘김
```

TCP 라우팅에서 `HostSNI`는 TLS 핸드셰이크의 SNI 필드를 읽어 매칭한다. `passthrough: true`면 TLS를 Traefik가 끊지 않고 백엔드까지 터널만 뚫어 준다. 반대로 Traefik에서 TLS를 끊고 싶으면 `passthrough`를 빼고 `secretName`으로 인증서를 지정한다.

SNI 기반이 아닌 단순 TCP 포워딩은 `HostSNI(`*`)`로 모든 연결을 받을 수 있다. 단, 이 경우 해당 EntryPoint로 들어오는 모든 TCP 연결이 하나의 서비스로 간다.

```yaml
# UDP 라우팅
apiVersion: traefik.io/v1alpha1
kind: IngressRouteUDP
metadata:
  name: game-server-route
  namespace: gaming
spec:
  entryPoints:
    - game-udp    # 7777/udp 포트
  routes:
    - services:
        - name: game-server-service
          port: 7777
```

UDP는 매칭 규칙 자체가 없다. EntryPoint로 들어오는 UDP 패킷을 지정된 서비스로 포워딩하는 것이 전부다. 여러 서비스로 분기가 필요하면 EntryPoint를 각각 열어야 한다.

TCP EntryPoint는 Helm values나 정적 설정에서 미리 정의해야 한다. IngressRouteTCP를 아무리 잘 만들어도 해당 포트의 EntryPoint가 없으면 Traefik가 그 포트를 열지 않아서 연결 자체가 안 된다.

## TLSOption CRD

TLS 버전 제한, 암호화 스위트 설정, 클라이언트 인증서 검증(mTLS)을 제어하는 CRD다.

```yaml
apiVersion: traefik.io/v1alpha1
kind: TLSOption
metadata:
  name: modern-tls
  namespace: production
spec:
  minVersion: VersionTLS12
  maxVersion: VersionTLS13
  cipherSuites:
    - TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
    - TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256
    - TLS_AES_256_GCM_SHA384
  curvePreferences:
    - CurveP521
    - CurveP384
  sniStrict: true
```

```yaml
# mTLS 설정 — 클라이언트 인증서 검증
apiVersion: traefik.io/v1alpha1
kind: TLSOption
metadata:
  name: mtls-option
  namespace: production
spec:
  minVersion: VersionTLS12
  clientAuth:
    clientAuthType: RequireAndVerifyClientCert
    secretNames:
      - ca-cert-secret    # CA 인증서가 담긴 Secret
```

IngressRoute에서 TLSOption을 참조한다.

```yaml
spec:
  tls:
    secretName: api-tls-secret
    options:
      name: modern-tls
      namespace: production
```

`sniStrict: true`는 SNI 필드가 없는 TLS 연결을 거부한다. 오래된 클라이언트 중 SNI를 보내지 않는 경우가 있어서, 이 옵션을 켜면 그런 클라이언트는 연결이 끊긴다. 보안 요구가 높은 API 서버에서는 켜 두고, 레거시 클라이언트 지원이 필요하면 끄거나 TLSOption을 나눠 쓴다.

기본 TLSOption은 `default` 이름으로 `default` 네임스페이스에 만들면 클러스터 전체에 적용된다.

## cert-manager 연동

cert-manager는 쿠버네티스에서 인증서 발급과 갱신을 자동화하는 도구다. Traefik의 ACME 내장 기능 대신 cert-manager를 쓰는 이유는 인증서 관리를 한 곳에서 중앙화하고, 클러스터 내 다른 컴포넌트(Istio, 내부 서비스 간 mTLS 등)와도 같은 cert-manager로 인증서를 통일할 수 있기 때문이다. Traefik 내장 ACME는 Traefik 인스턴스마다 인증서를 따로 관리해서 Traefik를 수평 확장하면 인증서 저장소 공유 문제가 생긴다.

```yaml
# ClusterIssuer — Let's Encrypt
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - http01:
          ingress:
            class: traefik
```

```yaml
# Certificate 리소스
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: api-cert
  namespace: production
spec:
  secretName: api-tls-secret
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - api.example.com
    - www.example.com
```

cert-manager가 인증서를 발급하면 `api-tls-secret`이라는 Secret에 `tls.crt`와 `tls.key`를 넣는다. IngressRoute의 `tls.secretName`이 이 Secret을 가리키면 Traefik가 자동으로 읽어 쓴다.

와일드카드 인증서가 필요하면 DNS-01 챌린지를 써야 한다.

```yaml
solvers:
  - dns01:
      cloudflare:
        email: admin@example.com
        apiTokenSecretRef:
          name: cloudflare-api-token
          key: api-token
    selector:
      dnsNames:
        - "*.example.com"
```

cert-manager와 Traefik을 연동할 때 한 가지 주의할 점이 있다. cert-manager가 HTTP-01 챌린지를 할 때 임시로 `.well-known/acme-challenge/` 경로에 응답을 만드는데, 이 경로가 Traefik 라우터 규칙에 걸리지 않아야 한다. 이미 해당 도메인에 `PathPrefix(/)`처럼 모든 경로를 잡는 라우터가 있으면 챌린지 경로도 그쪽으로 가서 cert-manager가 만든 응답이 아닌 백엔드 응답이 반환된다. cert-manager Ingress annotation(`kubernetes.io/ingress.class: traefik`)과 기존 IngressRoute가 충돌하지 않도록 라우터 규칙을 점검한다.

## Helm으로 Traefik 설치

```bash
helm repo add traefik https://traefik.github.io/charts
helm repo update

helm install traefik traefik/traefik \
  --namespace traefik \
  --create-namespace \
  --values traefik-values.yaml
```

실무에서 자주 조정하는 values 항목들을 모아 두면 이렇다.

```yaml
# traefik-values.yaml

deployment:
  replicas: 2

# 추가 EntryPoint 정의 (TCP/UDP 포트 포함)
ports:
  web:
    port: 80
    redirectTo:
      port: websecure
  websecure:
    port: 443
    tls:
      enabled: true
  postgres:
    port: 5432
    protocol: TCP
  metrics:
    port: 9100
    expose:
      default: false    # 외부에 노출 안 함

# 네임스페이스 간 리소스 참조 허용
providers:
  kubernetescrd:
    enabled: true
    allowCrossNamespace: true
    allowExternalNameServices: true
  kubernetesingress:
    enabled: true
    allowExternalNameServices: true

# Prometheus 메트릭
metrics:
  prometheus:
    entryPoint: metrics

# 로그 설정
logs:
  general:
    level: INFO
  access:
    enabled: true
    filters:
      statusCodes:
        - "400-599"    # 에러 응답만 남기고 싶을 때

# Traefik 내장 ACME 끄기 (cert-manager 쓰는 경우)
certResolvers: {}

# 리소스 제한
resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"

# PodDisruptionBudget
podDisruptionBudget:
  enabled: true
  minAvailable: 1

# Service type 설정
service:
  type: LoadBalancer
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: nlb  # AWS NLB
```

`web` EntryPoint에 `redirectTo: websecure`를 설정하면 80 포트로 들어오는 모든 요청을 443으로 리다이렉트한다. HTTP를 받아야 하는 IngressRoute가 있으면 이 설정을 빼거나 해당 라우터에서 따로 처리해야 한다.

Helm 업그레이드 시 CRD는 자동으로 업데이트되지 않는다. Traefik 버전을 올릴 때 CRD가 바뀐 경우 별도로 적용해야 한다.

```bash
# CRD 수동 업데이트
kubectl apply -f https://raw.githubusercontent.com/traefik/traefik-helm-chart/main/traefik/crds/ingressroute.yaml
# 또는 helm repo에서 직접
helm show crds traefik/traefik | kubectl apply -f -
```

## 네임스페이스 간 리소스 참조

Traefik가 여러 네임스페이스를 관리할 때 RBAC과 참조 범위 설정이 엮여서 의외로 자주 막힌다.

Helm으로 설치하면 Traefik ServiceAccount에 클러스터 전체 권한을 주는 ClusterRole이 기본으로 붙는다. 그런데 보안 요구로 특정 네임스페이스만 접근하도록 제한했다면, 해당 네임스페이스의 IngressRoute가 다른 네임스페이스 Middleware를 참조할 때 Traefik가 그 Middleware를 읽지 못해 무시한다.

다른 네임스페이스 리소스 참조가 필요한 시나리오는 주로 공통 Middleware를 `traefik` 네임스페이스에 모아 두고 각 서비스 네임스페이스의 IngressRoute가 참조하는 구성이다. 이때 세 가지를 동시에 맞춰야 한다.

첫째, `providers.kubernetescrd.allowCrossNamespace: true` (Helm values). 둘째, Traefik ServiceAccount에 해당 네임스페이스 리소스 읽기 권한. 셋째, IngressRoute에서 참조 시 `namespace` 필드 명시.

```yaml
# Middleware를 다른 네임스페이스에서 참조
spec:
  routes:
    - match: Host(`app.example.com`)
      middlewares:
        - name: common-ratelimit
          namespace: traefik        # 반드시 명시
      services:
        - name: app-service
          port: 8080
```

`namespace`를 생략하면 IngressRoute와 같은 네임스페이스에서 찾고, 없으면 조용히 무시한다. 에러 로그가 나오기는 하지만 미들웨어가 안 걸린 채 라우팅이 되는 거라 눈치채기 어렵다. 미들웨어가 의도대로 동작하는지 반드시 확인한다.

IngressRoute가 참조하는 Service가 다른 네임스페이스에 있는 경우도 마찬가지다. `allowExternalNameServices: true`와 ExternalName Service를 조합하거나, `allowCrossNamespace`로 직접 참조하는 방법이 있다.

## 트러블슈팅

### CRD 미설치

IngressRoute를 apply하면 `no matches for kind "IngressRoute" in version "traefik.io/v1alpha1"` 에러가 난다. Traefik CRD가 설치되지 않은 것이다.

```bash
# CRD 확인
kubectl get crd | grep traefik

# Helm으로 설치했다면 CRD가 포함된 경우
helm install traefik traefik/traefik ...

# 별도 설치 시
kubectl apply -f https://raw.githubusercontent.com/traefik/traefik-helm-chart/v28.0.0/traefik/crds/ingressroute.yaml
```

Traefik 버전을 올리면서 CRD 버전이 올라갔는데 적용을 빠뜨린 경우에도 같은 현상이 생긴다. `traefik.io/v1alpha1`에서 `traefik.io/v1`으로 API 버전이 바뀐 마이너 업데이트가 있어서, 기존 YAML의 `apiVersion`을 함께 바꾸지 않으면 apply는 되어도 동작하지 않는다.

### RBAC 권한 부족

Traefik 파드 로그에 `Failed to list *v1alpha1.IngressRoute: ingressroutes.traefik.io is forbidden` 같은 메시지가 찍히면 ServiceAccount 권한 문제다.

```bash
# Traefik ServiceAccount 확인
kubectl get clusterrolebinding | grep traefik
kubectl describe clusterrole traefik

# 특정 리소스 접근 권한 확인
kubectl auth can-i list ingressroutes.traefik.io \
  --as=system:serviceaccount:traefik:traefik \
  -n production
```

네임스페이스를 제한한 RBAC 구성이라면 Traefik가 감시해야 하는 네임스페이스마다 Role과 RoleBinding을 만들어야 한다. ClusterRole을 쓰는 게 관리 부담이 적지만 보안 팀에서 클러스터 전체 읽기 권한을 문제 삼으면 네임스페이스별로 분리한다.

Helm으로 설치하면 ClusterRole과 ClusterRoleBinding이 자동으로 만들어지는데, 클러스터 권한이 제한된 환경(예: 멀티 테넌트 클러스터)에서는 Helm 설치가 실패하기도 한다. 이때는 `rbac.enabled: false`로 Helm 설치하고 RBAC 리소스만 직접 만든다.

### 인증서 미발급

cert-manager 연동 시 Certificate 리소스를 만들었는데 Secret이 생기지 않는 경우다.

```bash
# Certificate 상태 확인
kubectl describe certificate api-cert -n production

# CertificateRequest 확인
kubectl get certificaterequest -n production
kubectl describe certificaterequest api-cert-xxxxx -n production

# cert-manager 로그
kubectl logs -n cert-manager deploy/cert-manager -f
```

HTTP-01 챌린지가 실패하는 가장 흔한 원인은 두 가지다. 하나는 챌린지 경로(`.well-known/acme-challenge/`)로 외부에서 접근이 안 되는 것이다. 클러스터 외부에서 해당 도메인의 80번 포트로 HTTP 요청이 Traefik에 닿아야 하는데, 방화벽이나 LoadBalancer 설정이 안 된 경우다. 다른 하나는 앞서 언급한 것처럼 기존 IngressRoute가 챌린지 경로를 가로채는 경우다.

DNS-01 챌린지는 API 키가 올바른지, Secret 이름과 key 필드가 ClusterIssuer와 일치하는지부터 본다.

```bash
# Cloudflare API 토큰 Secret 확인
kubectl get secret cloudflare-api-token -n cert-manager -o jsonpath='{.data.api-token}' | base64 -d
```

Traefik 내장 ACME와 cert-manager를 동시에 쓰지 않도록 주의한다. 같은 도메인에 두 곳에서 발급 요청을 보내면 Let's Encrypt rate limit에 걸리고, `acme.json`과 cert-manager Secret이 충돌해서 예상치 못한 인증서가 서빙된다.

IngressRoute에서 `tls.certResolver`를 지정하면 Traefik 내장 ACME가 동작하고, `tls.secretName`만 지정하면 cert-manager가 만든 Secret을 쓴다. 둘 중 하나만 쓴다.

### 라우팅이 안 될 때

```bash
# Traefik 파드 로그 레벨 올리기
kubectl set env deployment/traefik -n traefik TRAEFIK_LOG_LEVEL=DEBUG

# 현재 로드된 라우터/서비스/미들웨어 확인 (API)
kubectl port-forward -n traefik svc/traefik 9000:9000
curl http://localhost:9000/api/http/routers | jq .
curl http://localhost:9000/api/http/middlewares | jq .

# 로그 레벨 복구
kubectl set env deployment/traefik -n traefik TRAEFIK_LOG_LEVEL=INFO
```

IngressRoute가 apply됐는데 대시보드나 API에서 라우터가 안 보이면, Traefik가 그 네임스페이스를 감시하고 있는지 확인한다. `providers.kubernetescrd.namespaces` 설정으로 특정 네임스페이스만 보도록 제한했다면 새로 만든 네임스페이스를 목록에 추가해야 한다.

라우터는 보이는데 503이 뜨면 백엔드 Service가 Endpoints를 가지고 있는지 본다.

```bash
kubectl get endpoints api-service -n production
```

Endpoints가 없으면 Selector가 Pod 라벨과 매칭이 안 된 것이다. Service와 Deployment의 라벨을 비교한다.
