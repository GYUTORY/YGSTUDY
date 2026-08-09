---
title: NodeLocal DNSCache
tags: [kubernetes, dns, microservices, devops]
updated: 2026-07-04
---

# NodeLocal DNSCache

클러스터 규모가 커지면 CoreDNS가 먼저 흔들린다. Pod 수백 개가 동시에 DNS 조회를 날리면 CoreDNS Pod 몇 개가 그 트래픽을 전부 받아야 하는데, 특히 `conntrack` 테이블 고갈 문제가 불거지면 DNS 응답이 간헐적으로 실패하기 시작한다. NodeLocal DNSCache는 이 문제를 각 노드에 캐시 에이전트를 두는 방식으로 해결한다.

## 동작 원리

각 노드에 `node-local-dns` DaemonSet을 배포하면, 해당 에이전트가 링크로컬 주소 `169.254.20.10`을 노드 네트워크 인터페이스에 바인딩한다. kubelet은 이 주소를 각 Pod의 `resolv.conf`에 nameserver로 주입한다.

```bash
# Pod 내부 /etc/resolv.conf 예시
nameserver 169.254.20.10
search default.svc.cluster.local svc.cluster.local cluster.local
options ndots:5
```

DNS 조회 흐름은 다음과 같다.

```
sequenceDiagram
    participant Pod
    participant NodeLocalDNS as NodeLocal DNSCache (169.254.20.10)
    participant CoreDNS as CoreDNS (kube-dns ClusterIP)
    participant Upstream as Upstream DNS

    Pod->>NodeLocalDNS: DNS Query
    alt 캐시 히트
        NodeLocalDNS-->>Pod: Cached Response
    else 캐시 미스 (cluster.local)
        NodeLocalDNS->>CoreDNS: Forward (TCP)
        CoreDNS-->>NodeLocalDNS: Response
        NodeLocalDNS-->>Pod: Response
    else 캐시 미스 (외부 도메인)
        NodeLocalDNS->>Upstream: Forward
        Upstream-->>NodeLocalDNS: Response
        NodeLocalDNS-->>Pod: Response
    end
```

클러스터 내부 도메인(`cluster.local`)은 CoreDNS로 포워딩하고, 외부 도메인은 업스트림 DNS로 직접 보낸다. 중요한 점은 NodeLocal DNSCache에서 CoreDNS로 가는 트래픽은 UDP가 아닌 TCP를 사용한다는 것이다. 이게 `conntrack` 문제를 해결하는 핵심이다.

## conntrack 타임아웃 문제

NodeLocal DNSCache를 도입하는 가장 큰 이유 중 하나다.

kube-proxy가 iptables 모드로 동작할 때, UDP DNS 패킷은 NAT를 거쳐 CoreDNS로 전달된다. Linux 커널의 `conntrack` 모듈이 이 연결 상태를 추적하는데, 문제는 두 가지다.

첫째, UDP conntrack 항목의 기본 타임아웃이 30초인데, DNS 조회는 짧고 잦다. 고부하 상황에서 `conntrack` 테이블이 가득 차면 새로운 UDP 패킷을 추적할 수 없어 패킷이 드롭된다.

둘째, 더 심각한 문제는 race condition이다. 같은 소스 포트에서 동시에 A 레코드와 AAAA 레코드를 각각 조회할 때, 두 응답이 동시에 도착하면 conntrack이 두 응답 모두를 같은 5-tuple로 매핑하려 하면서 하나가 버려진다. `ndots:5` 설정 때문에 각 도메인 조회마다 여러 번의 DNS 쿼리가 발생하는 쿠버네티스 환경에서 이 race condition은 꽤 자주 발생한다.

NodeLocal DNSCache는 CoreDNS와의 통신에 TCP를 사용하기 때문에 conntrack race condition을 피한다. Pod에서 NodeLocal DNSCache까지는 링크로컬 주소라 NAT 자체가 없다.

## DaemonSet 배포 구조

NodeLocal DNSCache는 DaemonSet으로 배포된다. `hostNetwork: true`를 사용하지 않고, 대신 링크로컬 주소를 직접 노드 인터페이스에 추가하는 방식으로 동작한다.

```yaml
# node-local-dns DaemonSet 핵심 부분
spec:
  template:
    spec:
      hostNetwork: false
      containers:
      - name: node-cache
        image: registry.k8s.io/dns/k8s-dns-node-cache:1.23.0
        resources:
          requests:
            cpu: 25m
            memory: 5Mi
        args:
        - -localip
        - "169.254.20.10,<kube-dns-cluster-ip>"  # 두 주소 모두 바인딩
        - -conf
        - /etc/Corefile
        - -upstreamsvc
        - kube-dns-upstream
        ports:
        - containerPort: 53
          name: dns
          protocol: UDP
        - containerPort: 53
          name: dns-tcp
          protocol: TCP
        securityContext:
          privileged: true  # 노드 네트워크 설정 변경을 위해 필요
```

`localip` 인수에 kube-dns ClusterIP도 함께 지정한다. 이렇게 하면 기존에 kube-dns ClusterIP로 직접 DNS 조회하던 컴포넌트도 NodeLocal DNSCache를 거치게 된다. 이를 위해 노드의 iptables에 NOTRACK 규칙도 함께 추가된다.

에이전트가 시작될 때 노드에 `nodelocaldns` 인터페이스를 생성하고 `169.254.20.10`을 바인딩한다. 에이전트가 종료될 때는 이 인터페이스를 제거한다. 따라서 배포 중 롤링 업데이트 시 잠깐의 공백이 생길 수 있다.

## CoreDNS Corefile 설정

NodeLocal DNSCache의 Corefile은 도메인별로 다르게 동작한다.

```
# cluster.local 도메인 처리
cluster.local:53 {
    errors
    cache {
        success 9984 30
        denial 9984 5
    }
    reload
    loop
    bind 169.254.20.10
    forward . <kube-dns-cluster-ip> {
        force_tcp  # CoreDNS와의 통신은 반드시 TCP
    }
    prometheus :9253
    health 169.254.20.10:8080
}

# 외부 도메인 처리
.:53 {
    errors
    cache 30
    reload
    loop
    bind 169.254.20.10
    forward . /etc/resolv.conf  # 노드의 resolv.conf로 포워딩
    prometheus :9253
}
```

`success 9984 30`은 성공 응답을 최대 9984개까지 30초간 캐시하겠다는 설정이다. `denial 9984 5`는 NXDOMAIN 응답을 5초간 캐시한다. denial 캐시 TTL을 너무 짧게 잡으면 외부 도메인 오타 같은 상황에서 불필요한 CoreDNS 부하가 생긴다.

## 도입 시 주의사항

**kubelet 설정 확인**

NodeLocal DNSCache를 배포했다고 Pod `resolv.conf`가 자동으로 바뀌지는 않는다. kubelet의 `--cluster-dns` 플래그가 `169.254.20.10`을 가리켜야 한다.

```yaml
# kubelet 설정 (kubeadm 기준)
# /var/lib/kubelet/config.yaml
clusterDNS:
- 169.254.20.10
```

기존에 실행 중인 Pod는 이 설정이 변경돼도 `resolv.conf`가 바뀌지 않는다. 노드를 drain하고 Pod를 재스케줄해야 반영된다. 대규모 클러스터에서 이 작업을 롤링으로 진행할 계획을 세워야 한다.

**노드 업그레이드와 롤링 업데이트**

DaemonSet Pod가 종료되면 `169.254.20.10` 인터페이스가 사라진다. 새 Pod가 뜨기 전까지 해당 노드의 모든 Pod의 DNS 조회가 실패한다. 이 시간이 보통 수 초 이내지만, 애플리케이션이 DNS 실패에 얼마나 민감한지 확인해야 한다.

해결 방법으로는 DaemonSet의 `updateStrategy`를 `OnDelete`로 설정하고 직접 롤링 타이밍을 제어하거나, 새 버전의 node-local-dns가 기존 Pod가 종료되기 전에 준비되도록 처리하는 방법이 있다.

**CNI 호환성**

Calico, Cilium 같은 CNI와 함께 쓸 때 주의할 점이 있다. Cilium을 eBPF 모드로 사용하면 iptables 규칙을 Cilium이 관리하기 때문에 NodeLocal DNSCache가 추가하는 NOTRACK 규칙과 충돌할 수 있다. Cilium 문서에서 NodeLocal DNSCache 호환 설정을 확인하고 `--local-redirect-policy`나 `--dnsproxy` 옵션을 검토해야 한다.

## 모니터링 메트릭

NodeLocal DNSCache는 `:9253/metrics`로 Prometheus 메트릭을 노출한다.

```yaml
# ServiceMonitor 또는 PodMonitor 설정
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: node-local-dns
  namespace: kube-system
spec:
  selector:
    matchLabels:
      k8s-app: node-local-dns
  podMetricsEndpoints:
  - port: metrics
    interval: 30s
```

실무에서 주로 보는 메트릭은 다음과 같다.

| 메트릭 | 설명 |
|--------|------|
| `coredns_cache_hits_total` | 캐시 히트 수. 이 값이 낮으면 캐시 TTL이나 사이즈를 검토한다 |
| `coredns_cache_misses_total` | 캐시 미스 수. CoreDNS로 포워딩된 요청 수를 추정할 수 있다 |
| `coredns_dns_requests_total` | 전체 DNS 요청 수 |
| `coredns_dns_responses_total` | 응답 수. `rcode` 레이블로 NXDOMAIN, SERVFAIL 등을 구분한다 |
| `coredns_forward_request_duration_seconds` | CoreDNS로의 포워딩 레이턴시 |

캐시 히트율을 계산하려면 `coredns_cache_hits_total / (coredns_cache_hits_total + coredns_cache_misses_total)`로 계산한다. 80% 이상이면 정상적으로 동작하는 것이다.

## 실무 트러블슈팅

**DNS 조회가 여전히 실패한다**

NodeLocal DNSCache를 배포한 직후에도 DNS 실패가 계속되면 Pod의 `resolv.conf`를 먼저 확인한다.

```bash
kubectl exec -it <pod-name> -- cat /etc/resolv.conf
```

`nameserver 169.254.20.10`이 보이지 않으면 kubelet 설정이 아직 적용되지 않은 것이다. 노드를 drain하고 Pod를 재배포해야 한다.

`169.254.20.10`이 nameserver로 잡혔는데도 실패한다면 node-local-dns Pod가 해당 노드에서 실행 중인지 확인한다.

```bash
kubectl get pod -n kube-system -l k8s-app=node-local-dns -o wide
```

Pod가 `Running` 상태가 아니거나, 해당 노드에 Pod가 없으면 DaemonSet 이벤트를 확인한다.

**CoreDNS 부하가 줄지 않는다**

node-local-dns Pod는 떠 있고 Pod `resolv.conf`도 `169.254.20.10`을 가리키는데 CoreDNS 부하가 기대만큼 줄지 않는 경우가 있다. 캐시 히트율을 먼저 확인한다.

캐시 히트율이 낮다면 애플리케이션이 매 요청마다 DNS 조회를 하거나 TTL을 무시하고 계속 조회하는 상황일 수 있다. 애플리케이션 레벨에서 DNS 결과를 캐싱하는지 확인해야 한다.

`ndots:5` 설정도 확인할 만하다. `ndots:5`이면 `api.example.com`을 조회할 때 `api.example.com.default.svc.cluster.local`, `api.example.com.svc.cluster.local` 등을 순서대로 조회하다가 마지막에 `api.example.com`을 조회한다. 외부 도메인 조회가 많은 애플리케이션이라면 Pod spec에 `dnsConfig`를 설정해 `ndots`를 낮추는 것도 방법이다.

```yaml
spec:
  dnsConfig:
    options:
    - name: ndots
      value: "3"  # 기본값 5에서 낮춤
```

**노드 재시작 후 DNS 불통**

노드 재시작 시 node-local-dns Pod가 뜨기 전에 다른 Pod들이 먼저 스케줄되면, 그 Pod들은 `169.254.20.10`이 없는 상태로 DNS 조회를 시도하다 실패한다. 이 경우 `priorityClassName: system-node-critical`을 node-local-dns DaemonSet에 설정해 다른 Pod보다 먼저 스케줄되도록 해야 한다.

공식 배포 yaml에는 이미 `system-node-critical`이 설정돼 있으니, 자체 커스텀 yaml을 쓴다면 이 설정을 빠뜨리지 않도록 주의한다.
