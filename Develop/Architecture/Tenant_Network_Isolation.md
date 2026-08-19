---
title: 테넌트 네트워크 격리
tags: [architecture, kubernetes]
updated: 2026-08-04
---

# 테넌트 네트워크 격리

## 시작하기 전에

멀티테넌트 SaaS를 Kubernetes 위에서 운영하면 애플리케이션 레벨 격리만으로는 부족하다. 데이터베이스에 `tenant_id` 필터를 붙이고 RLS를 설정해도, 인프라 레벨에서 테넌트 A의 파드가 테넌트 B의 파드에 직접 네트워크 요청을 보낼 수 있다면 격리가 완전하지 않다.

Kubernetes는 기본적으로 모든 파드 간 통신을 허용한다. 네임스페이스가 달라도 마찬가지다. 테넌트 A 네임스페이스의 파드에서 테넌트 B 네임스페이스의 서비스 IP로 HTTP 요청을 보내면 응답이 온다. 이걸 막으려면 NetworkPolicy가 필요하다.

한 테넌트가 CPU를 폭발적으로 사용하면 같은 노드에 올라간 다른 테넌트 파드의 응답 속도가 눈에 띄게 느려진다. 이 노이지 네이버(noisy neighbor) 문제는 ResourceQuota와 LimitRange로 통제한다.

---

## 네임스페이스 기반 격리

테넌트마다 별도 네임스페이스를 할당하는 게 가장 기본이다. 네임스페이스는 Kubernetes 리소스의 논리적 경계이고, RBAC이나 NetworkPolicy를 적용하는 단위가 된다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-acme
  labels:
    tenant: acme
    tier: standard
```

레이블을 붙이는 게 중요하다. `tenant` 레이블은 NetworkPolicy 셀렉터로 쓰고, `tier` 레이블은 리소스 할당 기준으로 활용한다.

신규 테넌트 온보딩 시 네임스페이스 생성, RBAC 설정, NetworkPolicy 적용, ResourceQuota 설정까지 한 번에 처리하는 스크립트나 Helm 차트를 준비해두는 게 현실적이다. 수동으로 하다 보면 어느 테넌트는 NetworkPolicy가 빠지고, 어느 테넌트는 ResourceQuota가 없는 상황이 생긴다.

```bash
# 테넌트 프로비저닝 스크립트 예시
TENANT_SLUG=$1
TIER=${2:-standard}

kubectl create namespace tenant-${TENANT_SLUG}
kubectl label namespace tenant-${TENANT_SLUG} \
  tenant=${TENANT_SLUG} \
  tier=${TIER}

# Helm 차트로 NetworkPolicy, ResourceQuota, RBAC 일괄 적용
helm install tenant-${TENANT_SLUG} ./charts/tenant \
  --namespace tenant-${TENANT_SLUG} \
  --set tenant.slug=${TENANT_SLUG} \
  --set tenant.tier=${TIER}
```

---

## NetworkPolicy로 파드 간 통신 차단

NetworkPolicy는 실제 패킷 필터링을 직접 하는 게 아니다. CNI(Container Network Interface) 플러그인이 이 정책을 읽고 실제 네트워크 규칙을 만든다. Calico·Cilium 이 대표적이고, EKS 의 VPC CNI 도 1.25 부터 지원한다(애드온에서 활성화). Flannel 처럼 지원하지 않는 것도 있으니 쓰는 CNI 를 먼저 확인해야 한다. 기본 kubenet이나 flannel 일부 버전은 NetworkPolicy를 무시한다. 클러스터 CNI 설정을 먼저 확인해야 한다.

### Default Deny-All 정책

먼저 모든 인그레스/이그레스를 막는 정책을 네임스페이스에 적용한다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: tenant-acme
spec:
  podSelector: {}       # 네임스페이스의 모든 파드에 적용
  policyTypes:
    - Ingress
    - Egress
```

이 정책 하나만 적용해도 외부에서 이 네임스페이스 파드로 들어오는 트래픽과 나가는 트래픽이 모두 차단된다. 이 상태에서 필요한 통신만 추가로 허용한다.

### 필요한 통신 허용

```yaml
# 같은 네임스페이스 내 파드 간 통신 허용
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-same-namespace
  namespace: tenant-acme
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector: {}   # 같은 네임스페이스의 모든 파드
  egress:
    - to:
        - podSelector: {}
---
# DNS 쿼리 허용 (kube-dns)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: tenant-acme
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
---
# Ingress 컨트롤러에서 들어오는 트래픽 허용
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-ingress-controller
  namespace: tenant-acme
spec:
  podSelector:
    matchLabels:
      app: api-server
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
```

DNS 허용을 빠뜨리는 실수를 자주 한다. Default deny-all 적용 후 파드에서 외부 서비스명 조회가 안 되면서 연결 오류가 나는데, 처음엔 NetworkPolicy 문제라고 생각 못하고 한참 헤매게 된다.

### 공유 서비스 접근

모든 테넌트가 공통으로 쓰는 내부 서비스(메트릭 수집, 로그 수집 등)가 있을 때는 별도 네임스페이스를 두고 접근을 허용한다.

```yaml
# 모니터링 네임스페이스의 파드가 테넌트 파드에 접근 허용 (메트릭 스크레이핑)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-monitoring
  namespace: tenant-acme
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
      ports:
        - port: 9090    # Prometheus 메트릭 포트
```

외부 인터넷을 호출해야 하는 테넌트 파드가 있다면, 이그레스 정책에서 내부 클러스터 IP 범위만 막고 외부는 허용하는 방식으로 처리한다.

```yaml
egress:
  - to:
      - ipBlock:
          cidr: 0.0.0.0/0
          except:
            - 10.0.0.0/8       # 내부 클러스터 IP 범위 제외
            - 172.16.0.0/12
            - 192.168.0.0/16
    ports:
      - port: 443
        protocol: TCP
      - port: 80
        protocol: TCP
```

내부 IP 범위를 except에 넣으면 다른 테넌트 파드로의 직접 접근은 막고, 외부 인터넷만 허용할 수 있다.

---

## ResourceQuota와 LimitRange

### ResourceQuota

네임스페이스 전체에서 사용할 수 있는 리소스 총량을 제한한다.

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-acme
spec:
  hard:
    requests.cpu: "4"        # 네임스페이스 전체 CPU 요청 합계
    requests.memory: 8Gi     # 네임스페이스 전체 메모리 요청 합계
    limits.cpu: "8"          # 네임스페이스 전체 CPU 한도 합계
    limits.memory: 16Gi      # 네임스페이스 전체 메모리 한도 합계
    pods: "20"
    services: "10"
    persistentvolumeclaims: "5"
    requests.storage: 50Gi
```

ResourceQuota가 적용된 네임스페이스에서는 파드를 생성할 때 반드시 `resources.requests`와 `resources.limits`를 명시해야 한다. 지정하지 않으면 파드 생성이 거부된다.

### LimitRange

파드나 컨테이너 단위에서 기본값과 최대값을 설정한다.

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: tenant-limits
  namespace: tenant-acme
spec:
  limits:
    - type: Container
      default:            # limits 미지정 시 자동으로 붙는 값
        cpu: "200m"
        memory: 256Mi
      defaultRequest:     # requests 미지정 시 자동으로 붙는 값
        cpu: "100m"
        memory: 128Mi
      max:                # 컨테이너 하나의 최대값
        cpu: "2"
        memory: 4Gi
      min:
        cpu: "50m"
        memory: 64Mi
    - type: Pod
      max:
        cpu: "4"
        memory: 8Gi
```

LimitRange의 `default`가 있으면 개발자가 리소스 스펙을 생략해도 자동으로 기본값이 적용되어 ResourceQuota 검사를 통과한다. ResourceQuota 단독으로 쓰면 리소스 스펙 없는 파드가 모두 거부되니 LimitRange를 함께 설정해야 한다.

### Noisy Neighbor 문제

ResourceQuota와 LimitRange를 설정해도 노드 수준에서 CPU throttling 문제가 생길 수 있다. CPU limits를 너무 타이트하게 잡으면 파드가 CPU throttling을 받아 레이턴시가 튄다. 메모리는 limits 초과 시 OOMKilled로 파드가 죽지만, CPU는 죽지 않고 느려지기만 해서 발견이 어렵다.

`container_cpu_throttled_seconds_total` 메트릭을 테넌트 네임스페이스 단위로 모니터링해야 한다. throttle 비율이 20%를 넘어가면 limits를 올리거나 파드 수를 늘려야 한다.

테넌트 플랜에 따라 다른 ResourceQuota를 적용하는 게 일반적이다. `starter` 플랜은 CPU 2코어/4Gi, `professional`은 8코어/16Gi 이런 식으로 Helm values로 관리하면 온보딩 시 플랜명만 지정하면 된다.

---

## 서비스 계정 분리

### 테넌트별 ServiceAccount 생성

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tenant-acme-sa
  namespace: tenant-acme
automountServiceAccountToken: false    # 자동 마운트 비활성화
```

`automountServiceAccountToken: false`로 설정하면 파드에 서비스 계정 토큰이 자동으로 마운트되지 않는다. 파드 내부에서 Kubernetes API에 접근할 필요가 없다면 토큰이 컨테이너에 노출되지 않는 편이 낫다.

### RBAC으로 접근 범위 제한

```yaml
# 테넌트가 자기 네임스페이스 내 리소스만 조회 가능하도록
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-role
  namespace: tenant-acme
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments", "replicasets"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-rolebinding
  namespace: tenant-acme
subjects:
  - kind: ServiceAccount
    name: tenant-acme-sa
    namespace: tenant-acme
roleRef:
  kind: Role
  apiGroup: rbac.authorization.k8s.io
  name: tenant-role
```

ClusterRole이 아니라 네임스페이스 범위의 Role을 써야 한다. `ClusterRole + RoleBinding` 조합은 클러스터 전체 리소스에 접근 권한을 줄 수 있으니 주의해야 한다. ClusterRole을 쓰고 싶으면 ClusterRoleBinding 대신 RoleBinding으로 특정 네임스페이스에만 바인딩해야 한다.

---

## Ingress 레벨 격리

### 테넌트별 서브도메인 라우팅

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tenant-acme-ingress
  namespace: tenant-acme
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/limit-rps: "100"          # 초당 요청 제한
    nginx.ingress.kubernetes.io/limit-connections: "20"   # 동시 연결 제한
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - acme.myapp.com
      secretName: acme-tls-secret
  rules:
    - host: acme.myapp.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api-server
                port:
                  number: 8080
```

`limit-rps`와 `limit-connections` 어노테이션으로 테넌트 단위 rate limiting을 적용한다. 한 테넌트가 DDoS 공격을 받거나 버그로 인해 요청이 폭발적으로 늘어날 때 다른 테넌트에게 영향이 가지 않게 막는다.

### 와일드카드 인증서

테넌트가 수십 개를 넘어가면 테넌트별로 TLS 인증서를 발급하고 관리하는 게 번거롭다. cert-manager로 와일드카드 인증서를 발급해서 모든 테넌트 서브도메인에 쓰는 방식이 현실적이다.

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: wildcard-myapp
  namespace: ingress-nginx
spec:
  secretName: wildcard-myapp-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - "*.myapp.com"
```

Let's Encrypt 와일드카드 인증서는 DNS-01 챌린지로만 발급된다. HTTP-01 챌린지로는 와일드카드를 받지 못한다. Route53이나 Cloudflare 같은 DNS 프로바이더 API 연동이 필요하다.

---

## 실무에서 생기는 문제들

### NetworkPolicy 적용 후 특정 파드에서 503

Default deny-all 정책을 적용한 뒤 외부 API를 호출하는 파드에서 503이 나는 경우가 있다. 원인은 이그레스 정책에서 외부 IP 범위를 허용하지 않아서다. 그냥 보면 서비스 문제처럼 보이지만, `kubectl exec`으로 파드에 들어가서 `curl` 해보면 연결 자체가 안 된다.

NetworkPolicy 변경 후 항상 해당 파드에서 직접 연결 테스트를 해봐야 한다. `curl -v`로 DNS 해석까지 잘 되는지, TCP 연결이 맺어지는지 단계별로 확인한다.

### ResourceQuota로 파드 생성이 막히는 경우

기존에 돌아가던 네임스페이스에 ResourceQuota를 뒤늦게 적용하면, 이미 실행 중인 파드들의 리소스 합계가 quota를 초과하는 상황이 생길 수 있다. 기존 파드는 계속 돌아가지만 새 파드를 띄울 수 없다.

```bash
# 현재 리소스 사용량 확인
kubectl describe resourcequota tenant-quota -n tenant-acme

# 출력 예시
Name:            tenant-quota
Namespace:       tenant-acme
Resource         Used    Hard
--------         ----    ----
limits.cpu       7500m   8
limits.memory    14Gi    16Gi
pods             19      20
```

quota 적용 전에 해당 네임스페이스의 실제 리소스 사용량을 먼저 확인하고, 여유 있게 잡아야 한다.

### 테넌트 삭제 시 스토리지 잔류

테넌트 계약이 종료되어 네임스페이스를 삭제하면 대부분의 리소스는 같이 지워진다. PersistentVolume은 PVC가 삭제될 때 reclaimPolicy에 따라 다르게 동작한다. `Retain`으로 설정되어 있으면 PVC를 삭제해도 PV와 실제 스토리지 데이터가 남는다.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: tenant-storage
reclaimPolicy: Retain    # 테넌트 삭제 후에도 데이터 보존
volumeBindingMode: WaitForFirstConsumer
```

테넌트 데이터를 일정 기간 보관해야 하는 법적 의무가 있으면 `Retain`이 맞다. 실수로 `Delete`로 설정해놓으면 네임스페이스 삭제와 동시에 데이터가 날아간다.

### 멀티 테넌트 환경에서의 로그 분리

Fluent Bit을 DaemonSet으로 배포하면 클러스터 전체 로그를 수집한다. 이 로그에 테넌트 정보를 붙이지 않으면 특정 테넌트의 로그만 필터링하기 어렵다.

파드에 테넌트 레이블을 붙이고, Fluent Bit에서 쿠버네티스 메타데이터를 자동으로 추가하게 설정하면 된다.

```yaml
# 파드 템플릿에 테넌트 레이블 추가
metadata:
  labels:
    app: api-server
    tenant: acme         # 이 레이블이 로그 메타데이터에 포함됨
```

Elasticsearch나 OpenSearch에 저장할 때 테넌트별 인덱스를 분리하거나, 같은 인덱스에 `tenant` 필드를 포함시킨다. 인덱스 분리 방식은 운영이 복잡하지만 테넌트별 데이터 보존 기간 정책을 다르게 적용할 수 있다.
