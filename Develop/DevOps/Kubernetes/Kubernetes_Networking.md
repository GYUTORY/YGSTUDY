---
title: Kubernetes 네트워킹 심화
tags: [devops, kubernetes, k8s, networking, cni, kube-proxy, ingress, coredns]
updated: 2026-06-16
---

# Kubernetes 네트워킹 심화

Kubernetes.md에서 Pod, Service, Deployment 같은 기본 개념을 다뤘다. 여기서는 운영하면서 실제로 막혔던 지점 위주로 정리한다. "Pod가 서로 통신이 안 돼요", "Service IP로는 되는데 DNS 이름으로는 안 돼요", "Ingress 504 떠요" 같은 상황에서 어디를 봐야 하는지가 핵심이다.

## 1. Kubernetes 네트워크 모델의 전제

Kubernetes는 네트워크에 대해 세 가지를 강제한다. CNI 플러그인을 뭘 쓰든 이건 지켜야 한다.

- 모든 Pod는 NAT 없이 다른 모든 Pod와 통신한다.
- 노드의 모든 에이전트(kubelet, 시스템 데몬)는 그 노드의 Pod와 통신한다.
- Pod가 보는 자기 IP와 다른 Pod가 보는 그 Pod의 IP가 같다.

세 번째가 의외로 중요하다. Docker 단독 환경에서는 컨테이너가 자기 IP를 `172.17.x.x`로 보지만 외부에서는 호스트 IP + 포트로 접근한다. Kubernetes는 이 불일치를 없앤다. Pod 안에서 `hostname -i` 한 결과가 다른 Pod에서 `nslookup`으로 본 IP와 같아야 한다는 뜻이다. 이게 안 맞으면 CNI 설정이 깨진 거다.

Pod IP는 노드 단위로 할당된 CIDR 대역에서 나온다. 예를 들어 노드 A가 `10.244.1.0/24`, 노드 B가 `10.244.2.0/24`를 받으면 각 노드의 Pod는 자기 노드 대역에서 IP를 받는다. 노드를 넘어가는 통신은 CNI가 처리한다.

```
Pod CIDR:     10.244.0.0/16   (Pod IP가 나오는 대역)
Service CIDR: 10.96.0.0/12    (ClusterIP가 나오는 대역, 가상 IP)
```

Service CIDR은 실제 인터페이스에 붙지 않는 가상 IP다. ping이 안 되는 게 정상이다. 이걸 모르고 ClusterIP에 ping 때려보고 "네트워크 죽었다"고 판단하는 경우가 있다.

## 2. CNI 동작 방식

CNI(Container Network Interface)는 컨테이너 런타임이 Pod를 만들 때 네트워크를 붙여주는 규격이다. kubelet이 Pod를 띄우면 pause 컨테이너(네트워크 네임스페이스를 잡아두는 컨테이너)를 만들고, CNI 플러그인을 호출해 그 네임스페이스에 인터페이스를 꽂는다.

CNI가 하는 일을 순서대로 보면:

1. Pod용 네트워크 네임스페이스 생성 (pause 컨테이너)
2. veth pair 생성 — 한쪽은 Pod 네임스페이스의 `eth0`, 다른 쪽은 호스트의 브리지나 라우팅 테이블에 연결
3. IPAM(IP Address Management)에서 Pod IP 할당
4. 라우팅 규칙 설정 — 다른 노드의 Pod 대역으로 가는 경로 추가

설정 파일은 보통 `/etc/cni/net.d/`에 있고, 바이너리는 `/opt/cni/bin/`에 있다. Pod가 `ContainerCreating`에서 안 넘어가고 `kubectl describe pod`에 `failed to setup network` 같은 메시지가 뜨면 이 두 경로부터 본다. CNI 플러그인 DaemonSet이 안 떴거나, 설정 파일이 없거나, 바이너리가 빠진 경우가 대부분이다.

```bash
# 노드에 ssh 들어가서 확인
ls /etc/cni/net.d/
ls /opt/cni/bin/

# CNI DaemonSet 상태
kubectl get pods -n kube-system -l k8s-app=calico-node -o wide
```

### 2.1 노드 간 Pod 통신을 처리하는 두 방식

CNI 플러그인이 노드를 넘는 트래픽을 처리하는 방식은 크게 두 갈래다.

**오버레이(Overlay)** — VXLAN이나 IP-in-IP로 패킷을 한 번 더 감싼다. 원본 Pod 패킷을 노드 IP를 출발지/도착지로 하는 패킷 안에 넣어서 보낸다. 받는 쪽 노드가 껍데기를 벗기고 Pod에 전달한다. 물리 네트워크가 Pod 대역을 몰라도 동작하기 때문에 설정이 단순하다. 대신 캡슐화 오버헤드가 있다(MTU 줄어들고 CPU 약간 더 씀).

**라우팅(Native routing / BGP)** — 캡슐화 없이 각 노드가 "이 Pod 대역은 저 노드로 보내라"는 라우팅 정보를 공유한다. BGP로 라우터에 광고하거나 노드끼리 직접 교환한다. 오버헤드가 없어서 빠르지만, 물리 네트워크(또는 클라우드 VPC 라우트 테이블)가 Pod 대역 라우팅을 받아줘야 한다.

같은 노드 안의 Pod끼리는 어느 방식이든 그냥 호스트 브리지나 로컬 라우팅으로 끝난다. 노드를 넘을 때만 이 차이가 의미 있다.

## 3. CNI 플러그인 비교

실무에서 마주치는 건 보통 셋 중 하나다.

### 3.1 Flannel

가장 단순하다. 기본이 VXLAN 오버레이고, 설정할 게 거의 없다. 네트워크 정책(NetworkPolicy)을 지원하지 않는다. 그래서 "Pod 통신만 되면 된다, 보안 정책은 안 쓴다"는 학습용/소규모 클러스터에 많이 쓴다.

문제는 NetworkPolicy를 적용해도 무시된다는 점이다. Flannel 쓰는 클러스터에 NetworkPolicy 매니페스트를 apply하면 에러 없이 생성되지만 아무 효과가 없다. "정책 걸었는데 왜 차단이 안 되지" 하고 한참 헤매는 경우가 있다. NetworkPolicy가 필요하면 Flannel은 후보에서 빼야 한다.

### 3.2 Calico

라우팅 방식(BGP)이 기본이고, 오버레이(IP-in-IP, VXLAN)도 지원한다. NetworkPolicy를 제대로 구현하고, Calico 자체 확장 정책(GlobalNetworkPolicy 등)도 있다. 운영 환경에서 가장 많이 본다.

기본적으로 iptables 기반으로 정책을 적용한다. 노드에 들어가서 `iptables -L`을 보면 `cali-` 접두사 붙은 체인이 잔뜩 보인다. 정책이 의도대로 동작하는지 의심될 때 이 체인을 추적하면 된다. 규모가 커지면 iptables 대신 eBPF 데이터플레인으로 전환할 수도 있다.

클라우드(AWS, GCP)에서는 오버레이를 끄고 VPC 라우팅에 맡기는 구성을 자주 쓴다. AWS EKS의 경우 아예 VPC CNI(amazon-vpc-cni-k8s)를 기본으로 쓰는데, 이건 Pod에 VPC의 실제 IP(ENI 보조 IP)를 직접 할당한다. Pod IP가 VPC 대역과 같아서 별도 라우팅이 필요 없는 대신, 노드당 Pod 수가 ENI/IP 한도에 묶인다.

### 3.3 Cilium

eBPF 기반이다. kube-proxy의 iptables를 대체할 수 있고(아래 5절), L3/L4뿐 아니라 L7(HTTP 메서드, 경로 단위) 정책까지 건다. 관측성 도구(Hubble)로 Pod 간 트래픽 흐름을 실시간으로 본다.

규모가 크거나 iptables 성능 한계에 부딪힌 클러스터에서 선택한다. 수천 개 Service가 있으면 iptables 규칙이 수만 줄로 늘어나는데, Cilium의 eBPF 맵은 이 부분에서 훨씬 낫다. 단점은 학습 곡선과 커널 버전 요구사항이다. 오래된 커널에서는 일부 기능이 안 된다.

### 3.4 선택 기준

| 항목 | Flannel | Calico | Cilium |
|------|---------|--------|--------|
| 기본 방식 | VXLAN 오버레이 | BGP 라우팅 | eBPF |
| NetworkPolicy | 미지원 | 지원 | 지원 (L7까지) |
| kube-proxy 대체 | 불가 | 부분 | 가능 |
| 설정 복잡도 | 낮음 | 중간 | 높음 |
| 관측성 | 약함 | 중간 | 강함 (Hubble) |

정책이 필요 없는 학습용이면 Flannel, 일반적인 프로덕션이면 Calico, 대규모거나 L7 정책/관측성이 중요하면 Cilium으로 간다. 클러스터 만든 다음에 CNI 바꾸는 건 사실상 재구축에 가까우니 처음에 정하는 게 낫다.

## 4. Service의 실체와 트래픽 흐름

Service는 Pod 앞에 붙는 가상 IP + 로드밸런싱 규칙이다. 실제 프로세스가 있는 게 아니라, 각 노드의 kube-proxy(또는 CNI)가 만든 iptables/IPVS/eBPF 규칙으로 구현된다. 이게 헷갈리는 핵심이다 — ClusterIP로 패킷을 보내면 커널의 NAT 규칙이 그 패킷의 목적지를 실제 Pod IP 중 하나로 바꿔치기한다.

Service와 Pod를 잇는 건 라벨 셀렉터이고, 실제 연결된 Pod IP 목록은 Endpoints(또는 EndpointSlice) 오브젝트에 들어있다. Service가 트래픽을 못 보내면 제일 먼저 볼 게 Endpoints다.

```bash
kubectl get endpoints my-service
# 또는
kubectl get endpointslices -l kubernetes.io/service-name=my-service
```

여기가 비어 있으면(`<none>`) 셀렉터가 Pod와 안 맞거나, Pod가 Ready 상태가 아니라는 뜻이다. readinessProbe 실패한 Pod는 Endpoints에서 빠진다. "Service 만들었는데 연결이 안 돼요"의 절반은 Endpoints가 비어 있는 경우다.

### 4.1 ClusterIP

기본 타입. 클러스터 내부에서만 접근 가능한 가상 IP를 받는다. 외부에서는 못 들어온다.

```
Pod A → ClusterIP(10.96.0.10:80)
         │
         │ kube-proxy가 심은 DNAT 규칙
         ▼
   목적지를 실제 Pod IP로 변경
   10.244.1.5:8080 / 10.244.2.7:8080 중 하나로
```

DNAT는 패킷 단위가 아니라 연결(conntrack) 단위로 이뤄진다. 한 번 연결이 어느 Pod로 잡히면 그 연결 동안은 같은 Pod로 간다. 그래서 ClusterIP의 로드밸런싱은 연결 단위지 요청 단위가 아니다. HTTP keep-alive로 커넥션을 오래 유지하면 한 Pod에 트래픽이 몰릴 수 있다. gRPC가 대표적인데, 단일 커넥션에 다중 요청을 태우니 Service 로드밸런싱이 거의 안 먹는다. 이 경우 헤드리스 Service + 클라이언트 사이드 LB나 서비스 메시를 쓴다.

### 4.2 NodePort

모든 노드의 같은 포트(기본 30000~32767)를 열고, 그 포트로 들어온 트래픽을 Service로 전달한다. 어느 노드의 NodePort로 들어와도 된다 — 해당 노드에 Pod가 없으면 다른 노드의 Pod로 다시 넘긴다.

```
외부 → 노드B:31000 (노드B엔 Pod 없음)
        │
        │ kube-proxy가 노드A의 Pod로 전달 (추가 홉 발생)
        ▼
      노드A의 Pod
```

이 "다른 노드로 다시 넘김" 때문에 클라이언트 IP가 SNAT로 가려진다. Pod 입장에서 출발지 IP가 진짜 클라이언트가 아니라 노드 IP로 보인다. 클라이언트 IP를 보존하려면 `externalTrafficPolicy: Local`을 준다. 대신 트래픽 받은 노드에 해당 Pod가 없으면 그 노드로 온 요청은 그냥 버려진다(다른 노드로 안 넘김). 그래서 로드밸런서 헬스체크와 함께 써야 한다.

### 4.3 LoadBalancer

NodePort 위에 클라우드 로드밸런서를 얹은 형태다. Service를 LoadBalancer 타입으로 만들면 클라우드 컨트롤러가 실제 LB(AWS ELB/NLB, GCP LB 등)를 프로비저닝하고, 그 LB가 각 노드의 NodePort로 트래픽을 분산한다.

```
인터넷 → 클라우드 LB → 노드들의 NodePort → Service → Pod
```

온프레미스에는 클라우드 LB가 없어서 LoadBalancer 타입을 만들면 EXTERNAL-IP가 `<pending>`에 영원히 멈춘다. MetalLB 같은 걸 깔아야 IP가 할당된다. 이걸 모르고 베어메탈에서 `<pending>` 보고 당황하는 경우가 흔하다.

`externalTrafficPolicy: Local`은 여기서도 의미가 크다. Local로 두면 클라이언트 IP가 보존되고 불필요한 노드 간 홉이 사라지지만, LB 헬스체크가 Pod 없는 노드를 빼주도록 설정돼 있어야 한다.

### 4.4 Headless Service

`clusterIP: None`으로 만든다. 가상 IP를 안 받는다. DNS로 Service 이름을 조회하면 ClusterIP 하나가 아니라 연결된 모든 Pod IP가 A 레코드로 돌아온다.

```bash
# 일반 Service
nslookup my-service
# → 10.96.0.10 (ClusterIP 하나)

# Headless Service
nslookup my-headless-service
# → 10.244.1.5, 10.244.2.7, 10.244.3.2 (Pod IP 전부)
```

StatefulSet에서 각 Pod를 개별 주소로 접근해야 할 때 쓴다. 예를 들어 카산드라/카프카처럼 각 인스턴스가 고유 정체성을 가지는 경우, `pod-0.my-headless-service.namespace.svc.cluster.local` 형태로 특정 Pod에 직접 붙는다. 앞서 말한 gRPC/keep-alive 로드밸런싱 문제도 헤드리스로 Pod IP 목록을 받아 클라이언트에서 분산하는 식으로 푼다.

## 5. kube-proxy 모드

kube-proxy는 각 노드에서 돌면서 Service → Pod의 DNAT 규칙을 관리한다. 모드가 세 가지다.

### 5.1 iptables 모드 (기본)

Service마다 iptables 규칙을 만든다. 패킷이 들어오면 규칙 체인을 순서대로 매칭한다. Pod 선택은 통계 모듈로 확률 분배한다(첫 규칙 33%, 안 걸리면 다음 50%, 식으로).

문제는 규칙이 선형으로 늘어난다는 거다. Service와 Endpoint가 많아지면 규칙 수가 수만 개가 되고, 규칙 갱신(Service 추가/삭제 시 전체 재작성)이 느려진다. 수천 Service 규모에서 Service 하나 바꿀 때 수 초씩 걸리는 걸 본 적 있다. 소규모~중규모에서는 충분하다.

```bash
# 특정 Service의 iptables 규칙 추적
iptables -t nat -L KUBE-SERVICES -n | grep my-service
```

### 5.2 IPVS 모드

리눅스 커널의 IPVS(IP Virtual Server)를 쓴다. 해시 테이블 기반이라 Service가 많아져도 룩업이 O(1)에 가깝다. 규칙 갱신도 증분으로 처리한다. rr(라운드로빈), lc(least connection), sh(source hashing) 등 로드밸런싱 알고리즘을 고를 수 있다.

수천 개 이상 Service가 있으면 iptables보다 확실히 낫다. 활성화하려면 노드에 `ip_vs` 커널 모듈이 로드돼 있어야 한다. 모듈 없이 IPVS 모드로 켜면 kube-proxy가 조용히 iptables로 폴백하는 경우가 있어서, 실제로 IPVS로 동작하는지 확인해야 한다.

```bash
# IPVS 규칙 확인 (ipvsadm 설치 필요)
ipvsadm -Ln
```

### 5.3 eBPF (kube-proxy 대체)

Cilium이나 Calico의 eBPF 데이터플레인을 쓰면 kube-proxy 자체를 안 띄운다. iptables/IPVS를 거치지 않고 커널 eBPF 프로그램이 직접 DNAT를 처리한다. 가장 빠르고, 규칙 수에 따른 성능 저하가 거의 없다. 대신 CNI를 거기에 맞춰 깔아야 하고 커널 버전을 탄다.

### 5.4 어느 걸 쓰나

- 수백 Service 이하 일반 클러스터: iptables 기본으로 충분
- 수천 Service 이상, iptables 갱신이 느려짐: IPVS
- 최대 성능 + 관측성, 커널 신버전 가능: Cilium eBPF

## 6. Ingress와 nginx-ingress

LoadBalancer Service는 Service 하나당 LB 하나가 필요하다. 도메인 100개를 호스팅하면 LB 100개가 된다. Ingress는 LB 하나(또는 nginx Pod 묶음) 뒤에서 호스트/경로 기준으로 여러 Service에 트래픽을 나눠준다. L7(HTTP) 라우팅이다.

Ingress는 두 부분으로 나뉜다. **Ingress 리소스**(라우팅 규칙을 적은 YAML)와 **Ingress Controller**(그 규칙을 실제로 실행하는 프로세스). 규칙만 만들고 컨트롤러를 안 깔면 아무 일도 안 일어난다. "Ingress 만들었는데 접속이 안 돼요"의 흔한 원인이 컨트롤러 미설치다.

nginx-ingress(ingress-nginx)가 가장 많이 쓰인다. nginx Pod들이 Ingress 리소스를 읽어서 nginx 설정으로 변환하고, 그 설정으로 라우팅한다.

### 6.1 host / path 라우팅

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /users
        pathType: Prefix
        backend:
          service:
            name: user-service
            port:
              number: 80
      - path: /orders
        pathType: Prefix
        backend:
          service:
            name: order-service
            port:
              number: 80
  - host: admin.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: admin-service
            port:
              number: 80
```

`api.example.com/users`는 user-service로, `/orders`는 order-service로, `admin.example.com`은 전부 admin-service로 간다. host는 HTTP `Host` 헤더로 구분하니까, 같은 IP에 여러 도메인을 DNS로 물려둬야 동작한다.

`pathType`이 함정이다. `Prefix`는 경로 세그먼트 단위 매칭이고 `Exact`는 정확히 일치, `ImplementationSpecific`은 컨트롤러마다 다르게 해석한다. 경로가 안 잡히면 pathType부터 확인한다.

`rewrite-target` 어노테이션도 주의한다. 위 예시는 `/users`로 들어온 걸 백엔드에 `/`로 넘긴다. 백엔드 앱이 `/users` 프리픽스를 기대하는데 rewrite를 걸면 404가 난다. 반대로 rewrite 없이 정규식 경로를 쓰면 백엔드가 못 받는다. 이 조합 때문에 404를 자주 본다.

### 6.2 자주 보는 에러

- **502 Bad Gateway**: 백엔드 Service/Pod가 죽었거나 Endpoints가 비었다. nginx가 upstream에 연결을 못 한다.
- **504 Gateway Timeout**: 백엔드가 살아있지만 응답이 느리다. `nginx.ingress.kubernetes.io/proxy-read-timeout` 어노테이션으로 타임아웃을 늘리거나 백엔드를 고친다.
- **413 Request Entity Too Large**: 업로드 크기 제한. `nginx.ingress.kubernetes.io/proxy-body-size`를 키운다. 기본 1m이라 파일 업로드에서 자주 막힌다.
- **404 (컨트롤러 기본 페이지)**: host/path 규칙이 요청과 안 맞는다. Ingress 규칙과 실제 요청 Host 헤더를 대조한다.

nginx-ingress 로그가 1차 진단 도구다.

```bash
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller -f
```

여기에 어떤 요청이 어떤 upstream으로 갔고 응답 코드가 뭔지 다 찍힌다. 502/504 원인을 여기서 좁힌다.

## 7. NetworkPolicy

기본적으로 모든 Pod는 서로 통신할 수 있다(allow-all). NetworkPolicy는 이걸 제한한다. 단, CNI가 NetworkPolicy를 지원해야 한다(Calico/Cilium은 되고 Flannel은 안 됨, 3절 참고).

NetworkPolicy의 핵심 함정: **특정 Pod에 정책이 하나라도 걸리면, 그 Pod는 그 방향(ingress/egress)에 대해 기본 거부로 바뀐다.** 정책에 명시한 것만 허용되고 나머지는 다 막힌다. 정책 없을 땐 다 열려있다가, 정책 하나 걸자마자 명시 안 한 트래픽이 전부 끊긴다. 이걸 모르고 ingress 규칙 하나 추가했다가 다른 통신이 다 죽는 경우가 있다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-allow-from-api
  namespace: prod
spec:
  podSelector:
    matchLabels:
      app: postgres
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 5432
```

이 정책은 prod 네임스페이스의 `app: postgres` Pod에 대해, `app: api` 라벨을 가진 Pod에서 오는 TCP 5432만 허용한다. 그 외 모든 ingress는 차단된다. postgres Pod로 들어오던 다른 트래픽(모니터링, 백업 잡 등)이 갑자기 막히면 이 정책 때문이다.

네임스페이스를 넘는 트래픽을 허용하려면 `namespaceSelector`를 쓴다. 같은 네임스페이스 안만 보는 `podSelector`와 헷갈리면 안 된다.

```yaml
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          team: backend
      podSelector:
        matchLabels:
          app: api
```

`namespaceSelector`와 `podSelector`를 한 `from` 항목 안에 같이 쓰면 AND다(그 네임스페이스 + 그 라벨). 별도 항목으로 분리하면 OR가 된다. 들여쓰기 한 칸 차이로 의미가 완전히 바뀌니까 주의한다.

egress 정책을 걸 때는 DNS를 빠뜨리기 쉽다. egress를 제한하면 CoreDNS(53번 포트)로 가는 트래픽도 막혀서 이름 해석이 전부 실패한다. 그러면 Pod가 외부는커녕 클러스터 내부 Service 이름도 못 찾는다. egress 정책에는 거의 항상 kube-system의 DNS로 가는 UDP/TCP 53을 열어줘야 한다.

```yaml
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
```

## 8. DNS (CoreDNS)

클러스터 안 DNS는 CoreDNS가 담당한다. kube-system 네임스페이스에 Deployment로 떠 있고, `kube-dns`라는 이름의 ClusterIP Service(보통 `10.96.0.10`)로 노출된다. 각 Pod의 `/etc/resolv.conf`에 이 IP가 nameserver로 들어간다.

```
# Pod 안의 /etc/resolv.conf
nameserver 10.96.0.10
search myns.svc.cluster.local svc.cluster.local cluster.local
options ndots:5
```

Service의 FQDN 규칙은 `<service>.<namespace>.svc.cluster.local`이다.

- 같은 네임스페이스: `my-service`만 써도 됨 (search 도메인이 붙여줌)
- 다른 네임스페이스: `my-service.other-namespace` 또는 풀 FQDN
- 다른 네임스페이스 Service를 짧은 이름으로 부르면 못 찾는다 — 흔한 실수다.

### 8.1 ndots:5 함정

`options ndots:5`는 "점이 5개 미만인 이름은 먼저 search 도메인을 붙여서 시도하라"는 뜻이다. `google.com`(점 1개)을 조회하면 CoreDNS가 먼저 `google.com.myns.svc.cluster.local`, `google.com.svc.cluster.local`... 순으로 다 실패한 뒤 마지막에 `google.com`을 시도한다. 외부 도메인 조회 한 번에 DNS 쿼리가 5~6번씩 나간다.

외부 API를 자주 호출하는 Pod라면 이게 지연과 CoreDNS 부하로 이어진다. 끝에 점을 찍어서 FQDN으로 만들면(`google.com.`) search 도메인을 건너뛴다. 또는 Pod의 dnsConfig로 ndots를 낮춘다. CoreDNS CPU가 튀거나 외부 호출 레이턴시가 들쭉날쭉하면 이걸 의심한다.

### 8.2 DNS 디버깅

```bash
# 디버그용 Pod 띄워서 안에서 조회
kubectl run -it --rm debug --image=nicolaka/netshoot --restart=Never -- bash

# Pod 안에서:
nslookup kubernetes.default          # 가장 기본, 이게 안 되면 DNS 자체가 문제
nslookup my-service.my-namespace
cat /etc/resolv.conf                  # nameserver, search, ndots 확인

# CoreDNS Pod 상태와 로그
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl logs -n kube-system -l k8s-app=kube-dns
```

`nslookup kubernetes.default`조차 안 되면 CoreDNS Pod가 죽었거나, kube-dns Service Endpoints가 비었거나, NetworkPolicy가 53번을 막은 거다. 특정 Service만 안 잡히면 그 Service의 Endpoints(4절)를 본다.

CoreDNS가 OOM이나 부하로 죽으면 클러스터 전체에서 이름 해석이 깨진다. 증상이 "전부 느림 + 간헐적 연결 실패"로 나타나서 원인 찾기 어렵다. 의심되면 CoreDNS Pod 리소스와 재시작 횟수부터 본다.

## 9. Pod 간 통신 트러블슈팅 순서

"Pod A에서 Pod B로 통신이 안 된다"를 만났을 때 보는 순서다. 위에서부터 하나씩 좁힌다.

**1단계 — Pod IP로 직접 되나**

```bash
kubectl get pod target-pod -o wide   # Pod B의 IP 확인
kubectl exec -it source-pod -- curl -m 3 <Pod B IP>:<port>
```

Pod IP로 직접 되면 네트워크(CNI)는 정상이고 Service/DNS 문제다. Pod IP로도 안 되면 CNI나 NetworkPolicy 문제다.

**2단계 — Service IP로 되나**

```bash
kubectl get svc target-service                       # ClusterIP 확인
kubectl exec -it source-pod -- curl -m 3 <ClusterIP>:<port>
```

Pod IP는 되는데 ClusterIP가 안 되면 kube-proxy 규칙이나 Endpoints 문제다. Endpoints를 본다.

```bash
kubectl get endpoints target-service
```

비어 있으면 셀렉터 불일치 또는 readinessProbe 실패다.

**3단계 — DNS 이름으로 되나**

```bash
kubectl exec -it source-pod -- nslookup target-service
kubectl exec -it source-pod -- curl -m 3 http://target-service:<port>
```

ClusterIP는 되는데 이름이 안 되면 DNS 문제(8절). 네임스페이스를 빠뜨린 짧은 이름인지, ndots 문제인지, CoreDNS가 죽었는지 본다.

**4단계 — NetworkPolicy 확인**

Pod IP로도 안 되는데 CNI는 멀쩡해 보이면 정책을 본다.

```bash
kubectl get networkpolicy -n <namespace>
kubectl describe networkpolicy <name> -n <namespace>
```

source/target Pod에 걸린 정책이 있는지, egress 막혔는지, DNS 53번 열렸는지 확인한다.

이 순서대로 가면 "어디서 끊겼는지"가 거의 항상 나온다. Pod IP → ClusterIP → DNS 이름으로 한 단계씩 올라가면서, 어느 단계에서 실패하는지가 곧 원인 위치다. 처음부터 `curl http://my-service`로 시작해서 안 되면 원인이 CNI인지 Service인지 DNS인지 구분이 안 되니까, 항상 제일 아래(Pod IP)부터 올라간다.

netshoot 이미지(`nicolaka/netshoot`)에 디버깅 도구(curl, dig, tcpdump, nslookup, ipvsadm 등)가 다 들어있어서 디버그 Pod로 자주 쓴다. 진단할 때 일단 이걸 띄우고 시작하면 편하다.
