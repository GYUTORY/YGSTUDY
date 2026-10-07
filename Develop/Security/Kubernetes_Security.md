---
title: 쿠버네티스 보안
tags: [security, kubernetes, docker]
updated: 2026-10-08
---

# 쿠버네티스 보안

쿠버네티스는 기본 설정으로 두면 보안 측면에서 위험한 부분이 많다. 클러스터를 처음 띄우면 default ServiceAccount가 모든 Pod에 자동 마운트되고, NetworkPolicy가 없어서 모든 Pod끼리 통신이 가능하며, etcd에는 Secret이 평문으로 저장된다. 운영 환경에서 이런 상태로 두면 Pod 하나가 뚫렸을 때 클러스터 전체가 위험해진다.

5년차 개발자로서 클러스터 운영하면서 한 번씩 사고가 나면 거의 다 권한 관련이거나, 잘못 노출된 Secret 때문이거나, NetworkPolicy 없이 측면 이동이 일어난 경우다. 여기서는 실제 운영에서 막아야 할 위협 모델과 처방을 정리한다.

## 위협 모델 — 어디서 뚫리는가

공격 경로는 Pod 침투, API Server 직접 공격, 공급망 이미지 세 입구로 갈린다. 입구마다 이어지는 단계가 달라서 막는 위치도 다르다.

```mermaid
flowchart TB
    A[외부 공격] --> B[Pod 침투]
    A --> C[API Server 직접 공격]
    A --> D[Supply Chain 이미지]
    B --> E[ServiceAccount 토큰 탈취]
    B --> F[측면 이동 Pod-to-Pod]
    E --> G[API Server 권한 상승]
    F --> H[다른 네임스페이스 Pod 침투]
    G --> I[Secret 탈취]
    I --> J[클러스터 장악]
    H --> J
    C --> J
    D --> B
```

내가 본 실제 사고 패턴은 크게 세 가지다. 첫째, 컨테이너 안 애플리케이션 취약점으로 RCE가 났는데 default ServiceAccount가 list pods 권한이 있어서 공격자가 클러스터 구조를 다 파악한 경우. 둘째, NetworkPolicy 없이 운영하다가 한 Pod에서 다른 네임스페이스의 DB Pod로 직접 접근한 경우. 셋째, etcd 백업이 평문으로 S3에 올라가 있었는데 그 버킷이 public이었던 경우.

대응은 결국 권한 최소화, 네트워크 분리, 데이터 암호화 이 세 축이다. 컨테이너 자체의 격리는 [Docker 컨테이너 보안](Container_Security.md)에서, 컨테이너 안에서 일어나는 행위 탐지는 [컨테이너 런타임 탐지와 Falco](Container_Runtime_Security_Falco.md)에서 다룬다. 이 문서는 클러스터 레벨 통제와 Pod 스펙 강제에 집중한다.

## RBAC 설계 — 권한 최소화의 출발점

RBAC는 쿠버네티스 보안의 가장 기본이다. Role과 ClusterRole, RoleBinding과 ClusterRoleBinding 네 가지 리소스를 조합한다. Role은 네임스페이스 범위, ClusterRole은 클러스터 범위다.

### 잘못된 예 — cluster-admin 남발

가장 흔한 실수가 개발자 편의를 위해 cluster-admin을 그냥 묶어주는 것이다.

```yaml
# 절대 이렇게 하지 말 것
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: dev-team-admin
subjects:
- kind: User
  name: developer@company.com
roleRef:
  kind: ClusterRole
  name: cluster-admin
  apiGroup: rbac.authorization.k8s.io
```

이렇게 묶어주면 그 사용자는 모든 네임스페이스에서 모든 리소스를 만들고 지울 수 있다. 실수로 kube-system 네임스페이스를 건드리면 클러스터가 죽는다. 실제로 신입이 잘못된 명령어 하나로 kube-proxy DaemonSet을 지운 적이 있었다.

### 올바른 RBAC 설계 — 네임스페이스 단위 권한

개발팀이 자기 네임스페이스만 만지게 하는 패턴이다.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: team-payment
  name: developer
rules:
- apiGroups: ["", "apps", "batch"]
  resources: ["pods", "deployments", "services", "configmaps", "jobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "list"]  # Secret 생성/수정은 막아둠
- apiGroups: [""]
  resources: ["pods/exec"]
  verbs: ["create"]  # kubectl exec 허용
- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get", "list"]  # 로그 조회 허용
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  namespace: team-payment
  name: developer-binding
subjects:
- kind: Group
  name: team-payment-developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer
  apiGroup: rbac.authorization.k8s.io
```

여기서 중요한 점이 몇 가지 있다. Secret은 읽기만 가능하게 했다. Secret 생성/수정은 GitOps 파이프라인이 하고, 사람이 직접 만들지 않는다. pods/exec는 디버깅용으로 허용하되, 감사 로그에 다 남는다. 운영 환경에서는 pods/exec를 막고 별도 디버깅 Pod를 쓰는 곳도 많다.

### CI/CD용 ServiceAccount 권한

CI/CD에서 쓰는 ServiceAccount는 사람과 다르게 매우 좁게 잡아야 한다. 예를 들어 Deployment만 업데이트하는 ServiceAccount라면 이렇게 한다.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: gitops-deployer
  namespace: team-payment
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: team-payment
  name: deployer
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "patch", "update"]
  resourceNames: ["payment-api", "payment-worker"]  # 특정 리소스 이름만
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]  # 배포 후 상태 확인용
```

resourceNames로 특정 이름만 잡아두면 다른 Deployment는 못 건드린다. CI 파이프라인이 털렸을 때 피해를 좁힐 수 있다.

### 권한 점검 명령어

운영하면서 자주 쓰는 명령어다.

```bash
# 특정 사용자/SA가 할 수 있는 일 확인
kubectl auth can-i --list --as=system:serviceaccount:team-payment:gitops-deployer

# 특정 동작이 가능한지 확인
kubectl auth can-i delete pods --as=system:serviceaccount:default:default -n kube-system

# ClusterRoleBinding에서 cluster-admin 묶인 거 찾기
kubectl get clusterrolebindings -o json | \
  jq '.items[] | select(.roleRef.name=="cluster-admin") | .metadata.name'

# 위험한 RBAC 권한 가진 SA 찾기 (rakkess 또는 kubectl-who-can 같은 툴)
kubectl who-can create pods --all-namespaces
```

분기마다 한 번씩 cluster-admin 묶인 거 다 훑어보고 불필요한 거 정리하는 게 좋다. 사람이 회사 나간 후에도 묶여있는 경우가 의외로 많다.

## ServiceAccount와 토큰 관리

ServiceAccount는 Pod가 API Server와 통신할 때 쓰는 신원이다. 모든 Pod는 ServiceAccount를 하나 가지고, 명시하지 않으면 default SA가 붙는다.

### default ServiceAccount 자동 마운트 끄기

기본 설정으로는 default SA의 토큰이 모든 Pod의 `/var/run/secrets/kubernetes.io/serviceaccount/token`에 마운트된다. Pod에서 API Server를 부를 일이 없는데도 토큰이 있으면 Pod가 뚫렸을 때 공격자가 그 토큰으로 API를 칠 수 있다.

네임스페이스 단위로 default SA 자동 마운트를 끄는 방법이다.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: default
  namespace: team-payment
automountServiceAccountToken: false
```

Pod에서 API를 정말 호출해야 하는 경우에만 명시적으로 ServiceAccount를 만들고 마운트한다.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: payment-api-sa
  namespace: team-payment
automountServiceAccountToken: true
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-api
spec:
  template:
    spec:
      serviceAccountName: payment-api-sa
      automountServiceAccountToken: true  # Pod 레벨에서도 명시
```

### Token 종류 — Secret 기반 토큰의 위험성

쿠버네티스 1.24 이전에는 ServiceAccount를 만들면 Secret이 자동 생성되고 그 안에 영구 토큰이 들어갔다. 1.24부터는 Projected ServiceAccount Token이 기본이다. 두 방식의 차이는 토큰이 새는 순간의 피해 범위에서 갈린다.

| 항목 | Secret 기반 토큰 (1.24 이전) | Projected 토큰 |
|---|---|---|
| 만료 | 없음 | 기본 1시간, kubelet이 갱신 |
| 수명 | SA 를 지울 때까지 | Pod 가 사라지면 무효 |
| audience | 없음 (API Server 용) | 지정 가능 |
| 유출 시 | 발견해서 Secret 을 지울 때까지 유효 | 만료나 Pod 삭제로 자연 소멸 |

Pod가 시작될 때 짧은 만료 시간을 가진 JWT를 마운트하는 스펙은 이렇게 쓴다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: example
spec:
  serviceAccountName: payment-api-sa
  containers:
  - name: app
    image: payment-api:1.0
    volumeMounts:
    - mountPath: /var/run/secrets/tokens
      name: api-token
  volumes:
  - name: api-token
    projected:
      sources:
      - serviceAccountToken:
          path: api-token
          expirationSeconds: 3600  # 1시간
          audience: payment-api
```

audience를 지정하면 그 토큰은 해당 audience를 검증하는 서비스에서만 유효하다. 외부 시스템(예: Vault, AWS IAM)과 OIDC로 연동할 때 이 방식이 필수다.

### 외부에서 ServiceAccount Token 발급받기

CI에서 클러스터에 접근할 때 영구 토큰을 만들지 말고 `kubectl create token`으로 단기 토큰을 발급받는다.

```bash
# 1시간짜리 토큰 발급
kubectl create token gitops-deployer -n team-payment --duration=1h

# audience 지정
kubectl create token gitops-deployer -n team-payment \
  --audience=https://kubernetes.default.svc \
  --duration=30m
```

CI 파이프라인이 시작될 때 단기 토큰을 발급받고, 끝나면 자연 만료되게 한다. 영구 토큰을 GitHub Secrets에 박아두면 그게 새는 순간 끝이다.

## NetworkPolicy — 동서 트래픽 제어

쿠버네티스는 기본적으로 모든 Pod가 서로 통신 가능하다. 한 Pod가 뚫리면 같은 클러스터의 모든 Pod로 접근할 수 있다는 뜻이다. NetworkPolicy는 이 동서(East-West) 트래픽을 제한한다.

NetworkPolicy는 CNI 플러그인이 구현한다. Calico, Cilium은 지원하지만 일부 클라우드 기본 CNI는 지원하지 않거나 제한적이다. 클러스터 만들 때 CNI 선택을 보고 가야 한다.

### Default Deny 정책

네임스페이스에 들어오는 모든 트래픽을 막는 정책부터 깔아둔다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: team-payment
spec:
  podSelector: {}  # 네임스페이스 내 모든 Pod
  policyTypes:
  - Ingress
  - Egress
```

이걸 적용하면 그 네임스페이스 Pod는 외부에서 들어오지도 못하고 밖으로 나가지도 못한다. 그다음 필요한 통신만 하나씩 열어준다.

### DNS 트래픽 허용 (필수)

대부분의 Pod는 kube-dns/CoreDNS를 거쳐 이름을 해석한다. DNS를 막으면 어떤 서비스도 동작하지 않는다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: team-payment
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

NetworkPolicy 깔고 서비스가 안 뜨면 일단 DNS부터 확인한다. 이 실수 정말 자주 한다.

### 특정 서비스 간 통신만 허용

payment-api가 payment-db에만 접근하게 하는 예다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: payment-db-ingress
  namespace: team-payment
spec:
  podSelector:
    matchLabels:
      app: payment-db
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: payment-api
    ports:
    - protocol: TCP
      port: 5432
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: payment-api-egress-to-db
  namespace: team-payment
spec:
  podSelector:
    matchLabels:
      app: payment-api
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: payment-db
    ports:
    - protocol: TCP
      port: 5432
```

Ingress와 Egress를 둘 다 잡아야 한다. payment-db에서 ingress를 열어줘도 payment-api에서 egress가 막혀있으면 통신이 안 된다. 처음 NetworkPolicy 설계할 때 가장 헷갈리는 부분이다.

default-deny-all 아래에서 payment-api가 나가는 경로마다 어떤 정책이 열어줘야 하는지 그림으로 보면 이렇다. payment-api에서 payment-db로 가는 화살표는 양쪽 Pod의 정책이 모두 있어야 이어진다.

```mermaid
flowchart LR
    subgraph NS["team-payment (default-deny-all 적용)"]
        API["payment-api"]
        DB["payment-db"]
    end
    DNS["CoreDNS (kube-system)"]
    EXT["외부 결제 게이트웨이 443"]
    API -->|"allow-dns: egress 53"| DNS
    API -->|"payment-api-egress-to-db 와 payment-db-ingress 둘 다 필요"| DB
    API -->|"payment-api-egress-external: egress 443"| EXT
```

### 외부 트래픽 제어

운영하다 보면 Pod에서 외부 API를 호출하는 경우가 많다. 예를 들어 결제 API에서 토스/카카오 결제 게이트웨이를 호출한다고 치자. IP CIDR 기반으로 외부 트래픽을 제어할 수 있다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: payment-api-egress-external
  namespace: team-payment
spec:
  podSelector:
    matchLabels:
      app: payment-api
  policyTypes:
  - Egress
  egress:
  - to:
    - ipBlock:
        cidr: 0.0.0.0/0
        except:
        - 10.0.0.0/8      # 사내망 차단
        - 172.16.0.0/12
        - 192.168.0.0/16
    ports:
    - protocol: TCP
      port: 443
```

이렇게 하면 외부 HTTPS는 가능하지만 사내 다른 네트워크로는 못 나간다. SSRF 공격이 들어와도 내부 서비스로 안 새어 나간다.

### Cilium의 L7 정책

기본 NetworkPolicy는 L4(IP, 포트)까지만 다룬다. Cilium을 쓰면 L7(HTTP path, method)까지 제어할 수 있다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: payment-api-l7
  namespace: team-payment
spec:
  endpointSelector:
    matchLabels:
      app: payment-api
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: web-frontend
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/api/v1/payments/.*"
        - method: "POST"
          path: "/api/v1/payments"
```

web-frontend는 payment-api의 특정 path만 호출할 수 있다. admin path를 호출하면 차단된다. 마이크로서비스 간 호출을 세밀하게 통제할 때 유용하다.

## Pod Security Standards (PSS)

PodSecurityPolicy(PSP)는 1.25에서 제거됐다. 그 자리를 Pod Security Standards가 차지했다. 기준표는 PSS이고, 이를 API Server 안에서 실행하는 내장 admission 플러그인이 Pod Security Admission(PSA)이다. 네임스페이스 레이블만 붙이면 강제된다. PSA가 요청 처리 중 어느 단계에서 도는지는 뒤의 Admission Controller 흐름 절에 시퀀스로 그려두었다.

레벨은 무엇을 허용하느냐, 모드는 위반했을 때 어떻게 하느냐를 정한다. 둘은 독립이라 네임스페이스 하나에 모드마다 다른 레벨을 걸 수 있다.

| 레벨 | 허용 범위 | 용도 |
|---|---|---|
| privileged | 제한 없음 | kube-system 같은 시스템 컴포넌트 |
| baseline | 알려진 권한 상승 경로만 차단 (privileged, hostPath, hostNetwork 등) | 이미지를 못 고치는 서드파티 |
| restricted | non-root, seccomp, capability 전부 drop 까지 요구 | 운영 워크로드 기본값 |

| 모드 | 위반 시 동작 |
|---|---|
| enforce | Pod 생성 거부 |
| audit | 감사 로그에 주석만 남기고 통과 |
| warn | kubectl 에 경고를 찍고 통과 |

### PSA 는 Pod 만 본다

enforce 는 Pod 오브젝트에만 걸린다. Deployment 는 PSA 를 위반해도 그대로 만들어지고, 문제는 ReplicaSet 이 Pod 를 만들려는 시점에 터진다. `kubectl apply` 는 성공하는데 `READY 0/3` 에서 멈추는 모양이라 처음 보면 원인 찾기가 오래 걸린다.

```bash
kubectl -n team-payment describe rs -l app=payment-api | grep -A3 FailedCreate
# Error creating: pods "payment-api-6d9f7c-" is forbidden: violates PodSecurity
# "restricted:latest": allowPrivilegeEscalation != false (container "app" must set
# securityContext.allowPrivilegeEscalation=false), unrestricted capabilities ...
```

warn 과 audit 은 Deployment 같은 워크로드 리소스에도 걸린다. 그래서 `kubectl apply` 시점에 경고가 보이려면 warn 을 같이 켜둔다.

### 네임스페이스에 PSS 적용

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-payment
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.28
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

새 네임스페이스를 만들 때부터 restricted로 잡아두는 게 좋다. 운영 중에 baseline에서 restricted로 올리면 기존 Pod가 위반해서 재배포할 때 막힐 수 있다. 올리기 전에 서버 사이드 dry-run 으로 기존 Pod 중 위반하는 것을 먼저 뽑는다.

```bash
kubectl label --dry-run=server --overwrite ns team-payment \
  pod-security.kubernetes.io/enforce=restricted
# Warning: existing pods in namespace "team-payment" violate the new PodSecurity
# enforce level "restricted:latest"
# Warning: payment-worker-7c8d-x2k9p: allowPrivilegeEscalation != false, ...
```

### restricted를 만족시키는 Pod 스펙

restricted 모드에서 통과하려면 Pod 스펙에 다음을 모두 채워야 한다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: payment-api
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: payment-api:1.0
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    volumeMounts:
    - name: tmp
      mountPath: /tmp
    - name: cache
      mountPath: /var/cache
  volumes:
  - name: tmp
    emptyDir: {}
  - name: cache
    emptyDir: {}
```

### securityContext 항목이 막는 공격

restricted 가 요구하는 항목은 각각 다른 공격 단계를 자른다. 항목 하나만 켜고 끝내면 나머지 경로가 열려 있다.

| 항목 | 막는 공격 | 막지 못하는 것 | 켜면 깨지는 것 |
|---|---|---|---|
| runAsNonRoot + runAsUser | 컨테이너 root 로 마운트된 호스트 파일 수정, root 를 전제로 한 익스플로잇. 탈출 취약점이 터져도 호스트에서 비특권 UID | 호스트의 같은 UID 사용자와 권한이 겹침 | 80 포트 바인딩, root 소유 디렉터리에 쓰는 앱 |
| readOnlyRootFilesystem | 웹셸 저장, 바이너리 교체, 설정 파일 변조 | emptyDir 에 쓴 파일의 실행, 메모리상 실행 | /tmp, 로그, 캐시 디렉터리에 쓰는 앱 |
| allowPrivilegeEscalation: false | setuid 바이너리와 file capability 로 권한 상승 (no_new_privs) | 커널 취약점 | sudo, su 를 쓰는 엔트리포인트 스크립트 |
| seccompProfile: RuntimeDefault | 위험한 syscall 호출 (bpf, keyctl, mount, unshare 등). 커널 익스플로잇 표면 축소 | 허용된 syscall 안의 취약점 | 비표준 syscall 을 쓰는 일부 프로파일러, 디버거 |
| capabilities drop ALL | NET_RAW 로 ARP 스푸핑, SYS_ADMIN 으로 마운트, 파일 소유권 변경 | 커널 취약점 | ping, 1024 미만 포트 바인딩 (NET_BIND_SERVICE 만 다시 추가) |

몇 가지는 켜기 전에 알아둬야 한다.

runAsNonRoot 는 이미지의 `USER app` 처럼 이름으로 지정된 경우 kubelet 이 UID 를 확인하지 못해 컨테이너를 시작하지 않는다. `CreateContainerConfigError: image has non-numeric user (app), cannot verify user is non-root` 가 이 경우다. `runAsUser: 1000` 처럼 숫자를 같이 적는다. 호스트 UID 와 겹치는 문제는 [Rootless 컨테이너와 User Namespace](Rootless_Containers_User_Namespaces.md)의 `hostUsers: false` 가 푸는 영역이다.

readOnlyRootFilesystem 은 RCE 후 페이로드를 떨구는 걸 막는다고 알려져 있는데, 쓰기 가능한 emptyDir 를 /tmp 에 마운트하면 거기에 내려받아 실행할 수 있다. emptyDir 는 기본적으로 noexec 가 아니다. 크립토마이너가 /tmp 에 바이너리를 받아 돌리는 사고는 이 설정을 켜둔 Pod 에서도 났다. 쓰기 경로는 최소로 줄이고, 실행까지 막으려면 [Falco](Container_Runtime_Security_Falco.md) 규칙으로 /tmp 아래 실행 파일을 탐지한다. JVM 이 /tmp 에 클래스 파일을 쓰는데 막혀서 부트가 실패해 한참 디버깅한 적도 있다. 처음 적용할 때는 warn 모드로 두고 위반 사항을 보고 고친 다음에 enforce 로 바꾸는 게 안전하다.

seccompProfile 은 Pod 스펙에 적지 않으면 Unconfined 로 뜨는 클러스터가 많다. kubelet 의 `--seccomp-default` 를 켜야 RuntimeDefault 가 기본이 되는데 기본값은 꺼져 있다. restricted 레벨이 이 필드를 요구하는 이유다. 프로파일 자체와 capability 상세는 [Docker 컨테이너 보안](Container_Security.md)에 정리해 두었다.

## RuntimeClass — 커널을 공유하지 않는 격리

securityContext 는 같은 커널을 쓰는 컨테이너끼리의 경계를 조인다. 커널 취약점이 터지면 이 경계가 통째로 뚫린다. 결제나 외부 사용자 코드 실행처럼 침해 가능성이 높은 워크로드는 커널 자체를 분리하는 런타임을 붙이고, 쿠버네티스에서는 RuntimeClass 로 Pod 단위 선택을 한다.

```mermaid
flowchart LR
    subgraph RUNC["runc (기본)"]
        direction TB
        P1["컨테이너 프로세스"] --> K1["호스트 커널"]
    end
    subgraph GV["gVisor (runsc)"]
        direction TB
        P2["컨테이너 프로세스"] --> S2["Sentry: 유저스페이스 커널"]
        S2 -->|"제한된 syscall 만"| K2["호스트 커널"]
    end
    subgraph KT["Kata Containers"]
        direction TB
        P3["컨테이너 프로세스"] --> G3["게스트 커널"]
        G3 --> H3["경량 VM 하이퍼바이저"] --> K3["호스트 커널"]
    end
```

runc 는 컨테이너가 호스트 커널의 syscall 을 직접 호출한다. gVisor 는 syscall 을 유저스페이스 Sentry 가 받아 처리하고 호스트 커널에는 좁은 syscall 만 내려보낸다. Kata 는 Pod 마다 경량 VM 을 띄워 게스트 커널을 따로 쓴다. 호스트 커널에 닿는 표면은 runc, gVisor, Kata 순으로 좁아지고, 시작 시간과 호환성 비용은 같은 순서로 커진다.

노드에는 런타임이 설치돼 있어야 하고, RuntimeClass 의 `handler` 는 containerd 설정의 런타임 이름과 같아야 한다.

```toml
# /etc/containerd/config.toml (격리 노드)
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.gvisor]
  runtime_type = "io.containerd.runsc.v1"
```

```yaml
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: gvisor
overhead:
  podFixed:
    cpu: 100m
    memory: 64Mi
scheduling:
  nodeSelector:
    runtime: gvisor
  tolerations:
  - key: runtime
    operator: Equal
    value: gvisor
    effect: NoSchedule
---
apiVersion: v1
kind: Pod
metadata:
  name: user-code-runner
spec:
  runtimeClassName: gvisor
  containers:
  - name: runner
    image: registry.company.com/app/code-runner:1.4
```

`scheduling.nodeSelector` 와 `tolerations` 는 Pod 스펙에 합쳐진다. 격리 노드에 taint 를 걸어두면 일반 Pod 가 거기 올라오지 않고, `runtimeClassName: gvisor` 를 쓴 Pod 만 그 노드로 간다. `overhead.podFixed` 는 스케줄링과 ResourceQuota 계산에 더해지므로 값을 빼먹으면 노드가 실제보다 여유 있어 보인다.

주의할 점이 있다. gVisor 는 syscall 을 재구현한 것이라 일부 syscall 과 /proc, /sys 경로, eBPF 를 쓰는 앱은 동작하지 않을 수 있다. 네트워크 성능과 파일 I/O 가 느려지는 경우도 있어서 적용 전에 실제 워크로드로 돌려본다. Kata 는 hostPath 마운트와 일부 privileged 사용 방식이 달라진다. 어느 쪽이든 RuntimeClass 는 선택 사항이라, 정책 엔진이 `runtimeClassName` 을 강제하지 않으면 개발자가 필드를 빼는 것으로 격리가 사라진다. 민감 네임스페이스는 Kyverno 나 Gatekeeper 로 `runtimeClassName` 필수를 걸어둔다.

RuntimeClass 는 컨테이너 탈출을 어렵게 하지만 불가능하게 만들지는 않는다. 어떤 경로로 탈출이 일어나는지, RuntimeClass 가 어느 경로를 막는지는 [Container Escape](Container_Escape.md)에서 다룬다. Pod 의 root 를 호스트의 비특권 UID 로 매핑하는 `hostUsers: false` 는 런타임을 바꾸지 않고도 쓸 수 있는 낮은 비용의 방법이고, [Rootless 컨테이너와 User Namespace](Rootless_Containers_User_Namespaces.md)에서 다룬다.

## OPA/Gatekeeper — 정책 엔진

PSS는 정해진 정책이지만, OPA Gatekeeper를 쓰면 임의의 정책을 강제할 수 있다. 예를 들어 "이미지는 반드시 사내 레지스트리에서 와야 한다", "모든 Pod에 cost-center 레이블이 있어야 한다" 같은 거다.

Gatekeeper는 Admission Webhook으로 동작한다. Pod가 생성될 때 API Server가 Gatekeeper에 물어보고, Gatekeeper가 Rego로 작성된 정책을 평가한다.

### ConstraintTemplate과 Constraint

Gatekeeper는 두 단계로 구성된다. ConstraintTemplate은 정책 로직을 정의하고, Constraint는 그 템플릿을 실제 클러스터에 적용한다.

이미지 레지스트리 제한 예시다.

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8sallowedrepos
spec:
  crd:
    spec:
      names:
        kind: K8sAllowedRepos
      validation:
        openAPIV3Schema:
          type: object
          properties:
            repos:
              type: array
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8sallowedrepos

        violation[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          satisfied := [good | repo = input.parameters.repos[_]
                              good = startswith(container.image, repo)]
          not any(satisfied)
          msg := sprintf("컨테이너 이미지 %v는 허용된 레지스트리에서 와야 한다", [container.image])
        }
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sAllowedRepos
metadata:
  name: allowed-repos
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    excludedNamespaces:
      - kube-system
      - gatekeeper-system
  parameters:
    repos:
      - "registry.company.com/"
      - "gcr.io/company-prod/"
```

이제 누가 `docker.io/nginx` 같은 외부 이미지로 Pod를 만들려고 하면 거부된다. 공급망 공격을 막는 1차 방어선이다.

### 흔히 쓰는 Gatekeeper 정책

| 정책 | 막는 사고 |
|---|---|
| resource limits 강제 | Pod 하나가 노드 메모리를 먹어 이웃 Pod 까지 OOM |
| privileged Pod 차단 | 노드 장악. PSS 를 안 거는 네임스페이스의 안전망 |
| hostPath 마운트 차단 | 호스트 파일, docker.sock 접근 |
| cost-center, team 레이블 필수 | 비용 귀속 불가, 장애 시 담당자 불명 |
| LoadBalancer Service 차단 | 의도치 않은 외부 노출과 비용 |
| 허용된 Ingress 호스트만 | 남의 호스트명 선점 |
| runtimeClassName 필수 | 격리 노드용 Pod 가 일반 런타임으로 뜨는 것 |

### Audit과 Dry-run

정책을 처음 적용할 때 enforcementAction을 dryrun으로 두고 위반 현황을 본 다음 deny로 바꾼다.

```yaml
spec:
  enforcementAction: dryrun  # 처음에는 이거
  match: {...}
```

```bash
# 위반 현황 조회
kubectl get k8sallowedrepos allowed-repos -o yaml
# spec.status.violations 부분 확인
```

기존 워크로드 다 정리한 다음에 enforce로 전환한다. 운영 중에 갑자기 enforce 걸면 다음 배포에서 Pod 못 만들어서 장애 난다.

## Admission Controller 흐름

Admission Controller는 API Server가 요청을 인증·인가한 뒤 etcd에 저장하기 전에 끼어드는 단계다. 두 종류가 있다.

- **Mutating Admission**: 객체를 수정한다. 사이드카 주입, 기본값 설정, 이미지 태그를 digest 로 치환
- **Validating Admission**: 객체를 검증만 한다. 통과 못 하면 거부

PSA, Kyverno, Gatekeeper 가 각각 어느 단계에서 도는지가 중요하다. 같은 Pod 를 두고 mutating 이 먼저 고치고, validating 은 고쳐진 결과를 검사한다. 사이드카를 주입하는 mutating webhook 이 있으면 validating 쪽 정책은 사이드카 컨테이너까지 보게 된다.

```mermaid
sequenceDiagram
    participant U as kubectl
    participant A as API Server
    participant M as Mutating 단계
    participant V as Validating 단계
    participant E as etcd

    U->>A: POST /api/v1/namespaces/team-payment/pods
    A->>A: 인증 (OIDC 토큰, 클라이언트 인증서)
    A->>A: 인가 (RBAC 에서 create pods 확인)
    A->>M: AdmissionReview (원본 Pod)
    Note over M: 내장 플러그인 LimitRanger, ServiceAccount<br/>Kyverno mutate, verifyImages 의 digest 치환<br/>사이드카 주입 webhook
    M-->>A: 수정된 Pod (JSON patch)
    A->>A: 스키마 검증
    A->>V: AdmissionReview (수정된 Pod)
    Note over V: PodSecurity (PSA 네임스페이스 레이블)<br/>ValidatingAdmissionPolicy<br/>Kyverno validate, Gatekeeper<br/>ResourceQuota
    alt 모든 검증 통과
        V-->>A: allowed
        A->>E: Pod 저장
        A-->>U: 201 Created
    else 하나라도 거부
        V-->>A: denied 와 사유
        A-->>U: 403 Forbidden
    end
```

시퀀스에서 볼 것은 두 가지다. 인가를 통과해도 admission 에서 막히면 etcd 에 아무것도 남지 않는다. 그리고 거부는 Validating 단계 한 곳에서 모아서 판정되므로, 정책 엔진이 여럿이어도 하나라도 denied 를 내면 요청 전체가 403 이 된다.

정책 엔진마다 되는 일이 다르다. 겹치는 부분이 많아서 처음에는 하나만 고르면 되는지 헷갈린다.

| 항목 | PSA | ValidatingAdmissionPolicy | Kyverno | Gatekeeper |
|---|---|---|---|---|
| 동작 방식 | 내장 플러그인 | 내장, CEL 표현식 | webhook | webhook |
| 정책 작성 | 네임스페이스 레이블 | YAML 안에 CEL | YAML | Rego |
| mutate | 불가 | 불가 | 가능 | 별도 Assign 리소스로 가능 |
| 이미지 서명 검증 | 불가 | 불가 | verifyImages 로 가능 | Ratify 같은 별도 구성요소 필요 |
| 정책 대상 | Pod 스펙의 고정된 항목 | 임의 리소스 | 임의 리소스 | 임의 리소스 |
| 장애 시 영향 | 없음 (API Server 안) | 없음 (API Server 안) | webhook 죽으면 failurePolicy 에 따라 | 동일 |

PSA 는 항상 깔고, 그 위에 PSA 로 표현 못 하는 조직 규칙(허용 레지스트리, 레이블, 서명)을 Kyverno 나 Gatekeeper 중 하나로 얹는 구성이 흔하다. 두 엔진을 동시에 운영하면 정책이 어느 쪽에 있는지 찾는 비용이 커지니 하나로 정한다. 이미지 서명까지 같은 엔진으로 처리하려면 Kyverno 쪽이 짧다. 이미 Rego 자산이 있는 조직은 Gatekeeper 를 쓰고 서명은 별도로 붙인다.

내장 Admission Controller가 여러 개 있는데, 운영하면서 신경 쓸 것은 다음이다.

- **NodeRestriction**: kubelet이 자기 노드 외의 리소스를 수정 못 하게 막음
- **ResourceQuota**: 네임스페이스 리소스 한도 강제
- **LimitRanger**: 컨테이너 기본 limits/requests 설정
- **PodSecurity**: PSS 강제

외부 webhook을 쓸 때 주의할 점이 있다. Webhook 서버가 죽으면 API Server가 모든 요청을 거부할 수 있다. failurePolicy를 잘못 잡으면 클러스터가 통째로 멈춘다.

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: my-webhook
webhooks:
- name: validate.example.com
  failurePolicy: Fail  # Webhook 죽으면 요청 거부 — 위험
  timeoutSeconds: 5
  namespaceSelector:
    matchExpressions:
    - key: kubernetes.io/metadata.name
      operator: NotIn
      values: ["kube-system", "kube-public"]  # 시스템 NS 제외 필수
```

namespaceSelector로 kube-system은 제외해야 한다. 그렇지 않으면 webhook 자체를 배포하는데 webhook이 막아서 영원히 못 들어간다. 이거 때문에 클러스터 망친 사례 들어본 적 있다.

## Secrets 암호화 — KMS 연동

쿠버네티스 Secret은 etcd에 base64 인코딩되어 저장된다. 인코딩일 뿐 암호화가 아니다. etcd 디스크나 백업이 새면 모든 Secret이 평문으로 노출된다.

### EncryptionConfiguration

API Server 설정에서 Secret을 저장할 때 암호화하도록 한다.

```yaml
# /etc/kubernetes/encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - kms:
          apiVersion: v2
          name: aws-kms
          endpoint: unix:///var/run/kmsplugin/socket.sock
          timeout: 3s
      - aescbc:
          keys:
            - name: key1
              secret: <base64-encoded-32-byte-key>
      - identity: {}  # 마지막은 평문 (마이그레이션용)
```

providers 순서가 중요하다. 위에서부터 시도하고, 쓰기는 첫 번째 것으로 한다. 읽기는 모든 provider로 시도한다. identity를 마지막에 두면 기존 평문 데이터도 읽을 수 있다.

KMS provider는 외부 KMS(AWS KMS, GCP KMS, HashiCorp Vault Transit)와 통신해서 DEK(Data Encryption Key)를 암호화한다. etcd에는 KMS로 암호화된 DEK와 그 DEK로 암호화된 Secret이 같이 저장된다. KMS를 거치니 키 회전, 감사 로그, 접근 제어가 다 KMS에서 관리된다. `apiVersion: v2` 를 명시하는 이유는 v1 이 1.28 에서 deprecated 됐고 1.29 부터 기본 비활성이라 옛 설정 예제를 그대로 가져오면 API Server 가 뜨지 않을 수 있어서다. v1 설정에 있던 `cachesize` 도 v2 에는 없다.

Secret 하나를 읽고 쓸 때 KMS 가 어디에 끼는지를 보면, KMS 장애가 왜 읽기에도 영향을 주는지 보인다. 쓰기는 DEK 를 KMS 가 감싸는 단계가 필요하고, 읽기는 DEK 를 풀어야 해서 캐시에 없으면 KMS 를 다시 호출한다.

```mermaid
sequenceDiagram
    participant A as kube-apiserver
    participant P as KMS plugin
    participant K as 외부 KMS
    participant E as etcd

    Note over A,E: Secret 쓰기
    A->>A: DEK 생성, DEK 로 Secret 암호화
    A->>P: Encrypt (DEK)
    P->>K: KEK 로 DEK 암호화 요청
    K-->>P: 암호화된 DEK
    P-->>A: 암호화된 DEK
    A->>E: 암호화된 DEK 와 암호문 저장

    Note over A,E: Secret 읽기
    A->>E: 조회
    E-->>A: 암호화된 DEK 와 암호문
    alt DEK 캐시에 있음
        A->>A: 캐시된 DEK 로 복호화
    else 캐시에 없음
        A->>P: Decrypt (암호화된 DEK)
        P->>K: KEK 로 복호화 요청
        K-->>P: DEK
        P-->>A: DEK
        A->>A: DEK 로 복호화
    end
```

KMS 가 일시적으로 죽어도 캐시된 DEK 로 풀리는 Secret 은 읽힌다. API Server 를 재시작한 직후처럼 캐시가 비어 있을 때 KMS 까지 죽어 있으면 Secret 을 읽지 못하고, 그 Secret 을 마운트하는 Pod 가 시작하지 못할 수 있다. KMS 쪽 접근 권한과 응답 지연이 API Server 가용성에 영향을 주니 `timeout` 값은 KMS 응답 시간을 보고 잡는다.

### 기존 Secret 재암호화

EncryptionConfiguration을 처음 적용하면 새로 만드는 Secret만 암호화된다. 기존 Secret은 평문이다. 모두 재암호화하려면 명시적으로 업데이트한다.

```bash
# 모든 네임스페이스의 모든 Secret을 다시 저장 (재암호화)
kubectl get secrets --all-namespaces -o json | \
  kubectl replace -f -
```

이 작업은 한 번에 모든 etcd 쓰기를 일으키므로 트래픽이 적을 때 한다. 그리고 백업이 평문이었다면 그 백업도 안전한 곳에 보관하거나 다시 만들어야 한다.

### Secret 사용 패턴 — 외부 비밀 저장소

Secret을 쿠버네티스에 직접 저장하지 않고 외부 비밀 저장소를 쓰는 패턴이 점점 표준이 되고 있다.

- **External Secrets Operator**: Vault, AWS Secrets Manager, GCP Secret Manager에서 가져와서 Secret 리소스로 동기화
- **Secrets Store CSI Driver**: Secret을 etcd에 넣지 않고 Pod에 직접 마운트
- **SOPS**: Git에 암호화된 Secret을 커밋, 배포 시점에 복호화

SOPS와 ArgoCD 조합이 GitOps 환경에서 인기 있다. Secret도 git에 커밋되지만 KMS로 암호화되어 있어 키 없으면 못 읽는다.

```yaml
# secrets.enc.yaml (sops로 암호화된 파일)
apiVersion: v1
kind: Secret
metadata:
  name: payment-db-secret
data:
  password: ENC[AES256_GCM,data:abc...,tag:xyz==,type:str]
sops:
  kms:
    - arn: arn:aws:kms:ap-northeast-2:123456789:key/abc-def
```

## kubeconfig 관리

kubeconfig는 클러스터 접근 정보를 담은 파일이다. 사용자별로 따로 쓰지만, 운영 클러스터의 kubeconfig가 한 번 새면 그 사람의 모든 권한이 외부로 새는 것과 같다.

### 인증 방식 선택

kubeconfig의 user 섹션에는 여러 인증 방식이 들어갈 수 있다.

```yaml
users:
- name: developer
  user:
    # 1. Static token (가장 안 좋음 — 영구 토큰)
    token: eyJhbGc...

    # 2. Client certificate (영구, 회수 어려움)
    client-certificate-data: LS0tLS1...
    client-key-data: LS0tLS1...

    # 3. Exec plugin (OIDC, AWS IAM 등 동적 인증)
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: aws
      args: ["eks", "get-token", "--cluster-name", "prod"]
```

운영 환경에서는 무조건 exec plugin 방식이다. 사용자가 AWS SSO나 OIDC로 인증하고, 그 결과로 단기 토큰을 받는다. 영구 토큰이나 클라이언트 인증서는 새면 회수가 어렵다.

### EKS의 경우 — IAM 기반

```yaml
users:
- name: arn:aws:eks:ap-northeast-2:123456789:cluster/prod
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: aws
      args:
        - eks
        - get-token
        - --cluster-name
        - prod
      env:
        - name: AWS_PROFILE
          value: prod-sso
```

이렇게 하면 사용자는 AWS SSO로 로그인하고, IAM 권한이 RBAC와 매핑된다. IAM에서 사용자를 끄면 클러스터 접근도 같이 끊긴다. 회사 입사/퇴사 프로세스와 자연스럽게 연동된다.

### kubeconfig 권한 분리

운영 클러스터 kubeconfig와 개발 클러스터 kubeconfig는 분리한다. 한 파일에 다 넣으면 context 잘못 잡고 실수로 운영에 명령 내리는 사고가 난다.

```bash
# 클러스터별 kubeconfig 파일 분리
export KUBECONFIG=~/.kube/dev:~/.kube/staging:~/.kube/prod
kubectl config get-contexts

# 또는 매번 명시
kubectl --kubeconfig ~/.kube/prod get pods
```

별칭으로 wrapping해서 운영 명령에는 항상 확인을 거치게 하는 사람도 있다.

```bash
# .zshrc
kprod() {
  read -p "운영 클러스터 명령. 정말 실행? (y/N): " confirm
  [[ $confirm == "y" ]] && KUBECONFIG=~/.kube/prod kubectl "$@"
}
```

## etcd 암호화와 보호

etcd는 쿠버네티스의 데이터베이스다. 모든 리소스, Secret, ConfigMap이 여기 저장된다. etcd가 털리면 클러스터가 통째로 털린 거다.

### etcd 클라이언트 인증

etcd는 mTLS로 통신한다. API Server는 클라이언트 인증서로 etcd에 접근한다.

```yaml
# kube-apiserver 옵션
--etcd-cafile=/etc/kubernetes/pki/etcd/ca.crt
--etcd-certfile=/etc/kubernetes/pki/apiserver-etcd-client.crt
--etcd-keyfile=/etc/kubernetes/pki/apiserver-etcd-client.key
--etcd-servers=https://etcd-0:2379,https://etcd-1:2379,https://etcd-2:2379
```

이 인증서가 새면 누구나 etcd에 접근해서 데이터를 다 읽을 수 있다. 인증서 회전 절차를 미리 마련해둬야 한다.

### etcd 저장 시 암호화

위에서 다룬 EncryptionConfiguration이 etcd 안 Secret 암호화를 책임진다. 추가로 etcd 자체의 디스크 암호화(LUKS, EBS encryption)도 적용한다. 디스크가 도난당해도 직접 읽지 못하게 한다.

### etcd 백업 보안

```bash
# etcd 스냅샷
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-snapshot.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key
```

스냅샷은 EncryptionConfiguration 적용 후라도 그 안 내용은 Secret이 KMS로 암호화된 상태로 들어간다. 다만 ConfigMap이나 다른 리소스는 평문이다. 백업 파일 자체도 별도 암호화해서 저장한다.

S3에 올린다면 SSE-KMS로 암호화하고, 버킷 정책으로 접근을 제한한다. 백업 복호화 키와 etcd 암호화 키는 별도 KMS에 둔다.

## 이미지 서명 검증

쿠버네티스 노드는 이미지 레지스트리에서 이미지를 받아와 컨테이너를 띄운다. 이미지가 신뢰할 수 있는 곳에서 왔는지, 빌드 후 변조되지 않았는지 확인해야 한다.

### Cosign으로 이미지 서명

Cosign(Sigstore)은 컨테이너 이미지에 서명하는 도구다.

```bash
# 키 페어 생성
cosign generate-key-pair

# 이미지 서명
cosign sign --key cosign.key registry.company.com/payment-api:1.0

# 서명 검증
cosign verify --key cosign.pub registry.company.com/payment-api:1.0
```

CI 파이프라인에서 이미지 빌드 직후 서명한다. 비밀 키는 KMS나 GitHub OIDC + Sigstore Fulcio로 관리한다. Keyless signing은 임시 인증서를 받아서 서명하므로 비밀 키 관리 부담이 없다.

```bash
# Keyless signing (OIDC 기반)
cosign sign --identity-token=$OIDC_TOKEN registry.company.com/payment-api:1.0
```

### 클러스터에서 서명 검증 강제

Sigstore Policy Controller나 Kyverno로 검증을 강제한다.

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signature
spec:
  validationFailureAction: Enforce
  rules:
    - name: check-signature
      match:
        resources:
          kinds:
            - Pod
      verifyImages:
      - imageReferences:
        - "registry.company.com/*"
        attestors:
        - entries:
          - keys:
              publicKeys: |-
                -----BEGIN PUBLIC KEY-----
                MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...
                -----END PUBLIC KEY-----
```

서명되지 않은 이미지로 Pod를 만들려고 하면 admission 단계에서 거부된다. 공격자가 자기 이미지를 클러스터에 띄우려고 해도 서명이 없어서 막힌다. 다만 이 정책을 처음부터 Enforce 로 적용하면 정상 배포부터 막힌다. 위 YAML 은 도착점이고, 거기까지 가는 길이 문제다.

### Enforce 로 올리기

처음 서명 검증을 켜면 거의 항상 같은 상황이 된다. 서명 도입 전에 빌드한 사내 이미지, 외부에서 미러링해 온 이미지, 애드온 이미지가 서명 없이 사내 레지스트리에 이미 있다. 이걸 모르고 Enforce 로 켜면 다음 배포나 노드 교체 때 Pod 가 안 뜬다. Audit 으로 먼저 돌려서 실패 목록을 뽑고, 유형별로 처리한 뒤에 Enforce 로 간다.

```mermaid
flowchart LR
    A["Audit 로 배포"] --> B["PolicyReport 의 fail 수집"]
    B --> C{"fail 이미지 유형"}
    C -->|"사내 빌드, 서명 없음"| D["CI 에 cosign sign 추가 후 재빌드"]
    C -->|"미러링한 외부 이미지"| E["미러 키로 서명"]
    C -->|"kube-system, 애드온"| F["exclude 로 제외"]
    D --> G{"fail 0건 유지"}
    E --> G
    F --> G
    G -->|"아니오"| B
    G -->|"예"| H["한 네임스페이스만 Enforce"]
    H --> I["전체 Enforce"]
```

Audit 단계 정책이다. 사내 빌드 이미지와 미러 이미지를 경로로 나누고 키를 따로 쓴다. 미러 이미지는 원래 서명자가 우리가 아니므로 우리가 직접 검증해서 서명했다는 별도 키를 둔다.

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signature
  annotations:
    pod-policies.kyverno.io/autogen-controllers: none
spec:
  validationFailureAction: Audit
  failurePolicy: Ignore
  webhookTimeoutSeconds: 15
  rules:
    - name: verify-app-images
      match:
        any:
        - resources:
            kinds: ["Pod"]
      exclude:
        any:
        - resources:
            namespaces: ["kube-system", "kyverno", "cert-manager"]
      verifyImages:
      - imageReferences:
        - "registry.company.com/app/*"
        mutateDigest: true
        verifyDigest: true
        required: true
        attestors:
        - entries:
          - keys:
              publicKeys: |-
                -----BEGIN PUBLIC KEY-----
                (사내 빌드 서명 공개키)
                -----END PUBLIC KEY-----
    - name: verify-mirror-images
      match:
        any:
        - resources:
            kinds: ["Pod"]
      exclude:
        any:
        - resources:
            namespaces: ["kube-system", "kyverno", "cert-manager"]
      verifyImages:
      - imageReferences:
        - "registry.company.com/mirror/*"
        required: true
        attestors:
        - entries:
          - keys:
              publicKeys: |-
                -----BEGIN PUBLIC KEY-----
                (미러 서명 공개키)
                -----END PUBLIC KEY-----
```

Audit 에서는 Pod 가 그대로 뜨고 결과가 PolicyReport 에만 fail 로 남는다. 어떤 이미지가 걸리는지 집계한다.

```bash
kubectl get policyreport -A -o json | jq -r '
  .items[].results[]?
  | select(.policy=="verify-image-signature" and .result=="fail")
  | .message' | sort | uniq -c | sort -rn
```

내부 레지스트리에 서명 없이 올라온 외부 이미지는 가져온 시점에 한 번 우리 쪽에서 서명한다. 태그가 아니라 digest 로 서명한다. 태그는 나중에 다른 이미지를 가리키도록 바뀔 수 있어서 서명이 의미를 잃는다.

```bash
crane copy docker.io/library/redis:7.2.4 registry.company.com/mirror/redis:7.2.4
DIGEST=$(crane digest registry.company.com/mirror/redis:7.2.4)
cosign sign --key mirror.key --yes registry.company.com/mirror/redis@${DIGEST}
cosign verify --key mirror.pub registry.company.com/mirror/redis@${DIGEST}
```

서명을 붙였다고 끝나지 않고, Audit 로 돌리는 동안 발견하기 어려운 문제가 몇 가지 있다.

| 증상 | 원인 | 처리 |
|---|---|---|
| Enforce 후 새벽 CronJob 만 실패 | Audit 관찰 기간 동안 한 번도 안 돈 CronJob 이 서명 이전의 오래된 태그를 참조 | 관찰 기간을 가장 긴 CronJob 주기 이상으로 잡고, 모든 CronJob 이미지를 미리 목록화 |
| Argo CD 가 Deployment 를 OutOfSync 로 표시 | autogen 규칙이 Deployment 템플릿의 이미지를 digest 로 바꿔 Git 과 달라짐 | 위 YAML 의 autogen-controllers: none 으로 Pod 만 대상으로 하거나 ignoreDifferences 로 처리 |
| 서명이 있는데 verify 실패 | Kyverno 가 사설 레지스트리의 서명을 읽을 자격이 없음 | Kyverno 에 레지스트리 pull 자격 증명을 준다. 설정 방법이 버전마다 달라 Helm 차트 values 를 확인 |
| 배포가 느리거나 timeout | Pod 생성마다 레지스트리 호출. 레지스트리 지연이 그대로 admission 지연 | webhookTimeoutSeconds 를 늘리고 레지스트리 가용성을 같이 본다 |
| 레지스트리나 Kyverno 장애 시 Pod 생성 전체 중단 | failurePolicy: Fail | 아래 설명 |

failurePolicy 는 Audit 단계에서 Ignore, Enforce 로 올릴 때 Fail 로 바꾸는 게 일반적이다. 하지만 Fail 이면 Kyverno 가 죽은 동안 노드 장애로 재스케줄되는 Pod 도 못 뜬다. Kyverno replica 를 3개 이상으로 두고 PodDisruptionBudget 을 걸며, Kyverno 자기 네임스페이스는 반드시 제외한다. 앞의 Admission 절에서 본 webhook 자기 참조 데드락과 같은 문제다.

유형 분류와 정리가 끝나서 fail 이 0건이 되면 네임스페이스 하나에서만 Enforce 로 시작한다. `validationFailureActionOverrides` 로 네임스페이스별로 올릴 수 있다.

```yaml
spec:
  validationFailureAction: Audit
  validationFailureActionOverrides:
  - action: Enforce
    namespaces: ["team-payment"]
```

Kyverno 1.13 부터 `validationFailureAction` 이 deprecated 되고 규칙 안의 `failureAction` 으로 옮겨가는 중이다. 쓰는 버전의 CRD 를 확인하고 필드명을 맞춘다. 위 YAML 은 필드가 버전에 따라 거부될 수 있어서 `kubectl apply --dry-run=server` 로 먼저 확인한다.

### SBOM과 출처 검증

SBOM(Software Bill of Materials)도 같이 생성해서 이미지에 첨부한다.

```bash
# Syft로 SBOM 생성
syft registry.company.com/payment-api:1.0 -o spdx-json > sbom.spdx.json

# 이미지에 첨부
cosign attest --predicate sbom.spdx.json \
  --type spdxjson \
  --key cosign.key \
  registry.company.com/payment-api:1.0
```

이미지 안에 어떤 라이브러리가 들었는지 추적할 수 있다. 나중에 CVE가 터졌을 때 영향받는 이미지를 빠르게 찾는다.

## 감사 로그 — 누가 무엇을 했는가

API Server 감사 로그는 사고 났을 때 유일한 단서다. 기본으로는 안 켜져 있다.

```yaml
# /etc/kubernetes/audit-policy.yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
- level: None
  users: ["system:kube-proxy"]  # 시끄러운 시스템 컴포넌트 제외
  verbs: ["watch"]
  resources:
  - group: ""
    resources: ["endpoints", "services"]

- level: RequestResponse
  resources:
  - group: ""
    resources: ["secrets", "configmaps"]

- level: Metadata
  resources:
  - group: ""
    resources: ["pods"]
  verbs: ["create", "delete", "update", "patch"]

- level: RequestResponse
  resources:
  - group: "rbac.authorization.k8s.io"
    resources: ["*"]

- level: Metadata
```

Secret과 RBAC 변경은 RequestResponse 레벨(요청과 응답 본문 전체)로 남긴다. Pod 생성/삭제는 Metadata 레벨(누가 언제 무엇을)로 충분하다. 너무 자세히 잡으면 로그가 폭발한다.

API Server 옵션에 적용한다.

```yaml
--audit-policy-file=/etc/kubernetes/audit-policy.yaml
--audit-log-path=/var/log/audit.log
--audit-log-maxage=30
--audit-log-maxbackup=10
--audit-log-maxsize=100
```

로그는 SIEM(Splunk, Elastic, Loki)으로 빨아간다. "어제 새벽 3시에 누가 prod에 cluster-admin 묶었나" 같은 질문에 답할 수 있어야 한다.

## 운영 체크 — 정기 점검 항목

운영 중 정기적으로 봐야 할 것들이다.

```bash
# 1. cluster-admin 묶인 모든 ID
kubectl get clusterrolebindings -o json | \
  jq -r '.items[] | select(.roleRef.name=="cluster-admin") |
         "\(.metadata.name): \(.subjects[]?.name)"'

# 2. default 네임스페이스에 떠 있는 워크로드 (의심)
kubectl get all -n default

# 3. NetworkPolicy 없는 네임스페이스
for ns in $(kubectl get ns -o name | cut -d/ -f2); do
  count=$(kubectl get networkpolicy -n $ns --no-headers 2>/dev/null | wc -l)
  echo "$ns: $count NetworkPolicies"
done

# 4. PSS 레이블 없는 네임스페이스
kubectl get ns -L pod-security.kubernetes.io/enforce

# 5. privileged Pod 찾기
kubectl get pods --all-namespaces -o json | \
  jq -r '.items[] |
         select(.spec.containers[]?.securityContext?.privileged==true) |
         "\(.metadata.namespace)/\(.metadata.name)"'

# 6. hostNetwork 쓰는 Pod
kubectl get pods --all-namespaces -o json | \
  jq -r '.items[] | select(.spec.hostNetwork==true) |
         "\(.metadata.namespace)/\(.metadata.name)"'

# 7. 만료 임박한 인증서
kubeadm certs check-expiration
```

이런 점검을 자동화한 도구가 많다. kube-bench는 CIS Benchmark 기준으로 클러스터를 점검하고, kube-hunter는 침투 테스트 관점에서 취약점을 찾는다. Polaris나 Trivy는 워크로드 설정을 검사한다. 분기마다 한 번씩 돌려보면 잊고 있던 구멍이 보인다.

## 정리

쿠버네티스 보안은 단일 설정이 아니라 여러 층의 방어를 쌓는 작업이다. RBAC로 권한을 좁히고, NetworkPolicy로 동서 트래픽을 막고, PSS와 OPA로 Pod 스펙을 통제하고, KMS로 Secret을 암호화하고, 이미지 서명으로 공급망을 검증하고, 감사 로그로 추적한다. 한 층이 뚫려도 다음 층에서 막을 수 있게 설계한다.

특히 새 클러스터를 띄울 때 기본 설정부터 손봐야 한다. default SA 자동 마운트 끄기, default-deny NetworkPolicy 깔기, PSS restricted 적용, EncryptionConfiguration 설정, 감사 로그 활성화. 이 다섯 가지가 운영 클러스터의 출발선이다. 운영 들어간 뒤에 뒤늦게 적용하면 기존 워크로드 깨지는 거 다 잡아야 해서 훨씬 힘들다.
