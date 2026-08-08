---
title: Private DNS - Split-horizon DNS와 내부 서비스 디스커버리
tags: [network, dns, aws, microservices]
updated: 2026-07-25
---

# Private DNS - Split-horizon DNS와 내부 서비스 디스커버리

내부 서비스끼리 IP로 직접 통신하다가 특정 시점에 문제가 생긴 적이 있다. 서비스 재배포로 IP가 바뀌었는데 호출하는 쪽 설정에는 옛날 IP가 박혀 있었다. 그때부터 내부 통신도 도메인으로 하기로 했고, DNS를 내부망 전용으로 따로 운영하게 됐다.

private DNS는 외부에서 조회할 수 없고 VPC 내부 또는 온프레미스 네트워크에서만 응답하는 DNS 서버다. 외부 퍼블릭 DNS와 별개로, 같은 도메인 이름이어도 내부망에서 조회하면 사설 IP를, 외부에서 조회하면 공인 IP를 반환하게 만들 수 있다.

## Split-horizon DNS

Split-horizon DNS는 같은 도메인에 대해 조회하는 위치에 따라 다른 응답을 내려주는 구성이다. Split-brain DNS라고도 부른다.

`api.example.com`을 예로 들면, 외부 인터넷에서 조회하면 공인 IP인 `203.0.113.10`이 반환되고, 내부 VPC에서 조회하면 사설 IP인 `10.0.1.50`이 반환된다.

```
외부 클라이언트 → 퍼블릭 DNS → api.example.com → 203.0.113.10 (로드밸런서 공인 IP)
내부 서비스     → 프라이빗 DNS → api.example.com → 10.0.1.50 (ALB 내부 IP 또는 직접 타겟)
```

이렇게 나누는 이유는 몇 가지다.

내부 통신이 인터넷을 경유하지 않는다. 외부 공인 IP를 타고 나갔다가 다시 들어오는 hairpin NAT 문제도 없다. NAT Gateway 비용도 줄고, 레이턴시도 낮아진다.

또 외부에서는 접근 자체를 막아야 하는 내부 서비스 URL을 만들 수 있다. `internal-admin.example.com`이 외부 DNS에는 아예 없는 도메인이면 외부에서 IP를 알아낼 방법이 없다.

## AWS Route 53 Private Hosted Zone 구성

Route 53에서 Private Hosted Zone을 만들면 특정 VPC에서만 응답하는 DNS를 구성할 수 있다.

### Private Hosted Zone 생성

콘솔에서 만들 때 중요한 설정이 두 가지다. 도메인 이름과 연결할 VPC.

```bash
aws route53 create-hosted-zone \
  --name internal.example.com \
  --vpc VPCRegion=ap-northeast-2,VPCId=vpc-0123456789abcdef0 \
  --caller-reference "$(date +%s)" \
  --hosted-zone-config PrivateZone=true
```

이 zone에 등록한 레코드는 연결된 VPC에서만 조회된다. 다른 VPC나 외부에서는 NXDOMAIN이 반환된다.

동일 도메인에 대해 퍼블릭 hosted zone과 private hosted zone이 모두 있으면, VPC 내부 리졸버는 private hosted zone을 우선한다. Split-horizon 동작이 자동으로 적용되는 것이다.

### VPC DNS 설정 확인

Route 53 private hosted zone이 동작하려면 VPC에 두 가지 설정이 켜져 있어야 한다.

```bash
aws ec2 describe-vpc-attribute \
  --vpc-id vpc-0123456789abcdef0 \
  --attribute enableDnsSupport

aws ec2 describe-vpc-attribute \
  --vpc-id vpc-0123456789abcdef0 \
  --attribute enableDnsHostnames
```

둘 다 `true`여야 한다. `enableDnsSupport`가 꺼져 있으면 VPC 내부 DNS 리졸버(169.254.169.253)가 동작하지 않는다. 이 두 설정이 꺼진 VPC에 Private Hosted Zone을 붙여도 조회가 전혀 안 된다. 트러블슈팅할 때 이 설정부터 확인한다.

### 여러 VPC를 하나의 Private Hosted Zone에 연결

Private Hosted Zone은 여러 VPC와 연결할 수 있다.

```bash
aws route53 associate-vpc-with-hosted-zone \
  --hosted-zone-id Z1234567890ABCDEFGHIJ \
  --vpc VPCRegion=ap-northeast-2,VPCId=vpc-abcdef0123456789
```

다른 계정의 VPC와 연결할 때는 절차가 다르다. zone 소유 계정에서 authorization을 만들고, 대상 계정에서 association을 수락하는 방식이다.

```bash
# zone 소유 계정에서
aws route53 create-vpc-association-authorization \
  --hosted-zone-id Z1234567890ABCDEFGHIJ \
  --vpc VPCRegion=ap-northeast-2,VPCId=vpc-OTHER_ACCOUNT_VPC_ID

# 대상 계정에서
aws route53 associate-vpc-with-hosted-zone \
  --hosted-zone-id Z1234567890ABCDEFGHIJ \
  --vpc VPCRegion=ap-northeast-2,VPCId=vpc-OTHER_ACCOUNT_VPC_ID
```

cross-account private hosted zone 연결은 콘솔에서 안 된다. CLI나 SDK로만 가능하다.

### 레코드 관리

Private Hosted Zone에 레코드를 추가하는 방식은 퍼블릭 zone과 동일하다.

```json
{
  "Changes": [
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "db.internal.example.com",
        "Type": "A",
        "TTL": 60,
        "ResourceRecords": [
          { "Value": "10.0.2.50" }
        ]
      }
    },
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "db.internal.example.com",
        "Type": "CNAME",
        "TTL": 60,
        "ResourceRecords": [
          { "Value": "mydb.cluster-xyz.ap-northeast-2.rds.amazonaws.com" }
        ]
      }
    }
  ]
}
```

RDS 클러스터나 ElastiCache 같은 AWS 관리형 서비스는 엔드포인트 주소가 길고, 교체 시 바뀐다. CNAME으로 내부 별칭을 만들어두면 코드에서 `db.internal.example.com`만 참조하고 실제 엔드포인트 교체를 DNS 레벨에서 처리할 수 있다.

TTL은 짧게 잡는다. DB 엔드포인트가 장애로 바뀌는 상황에서 TTL이 3600초면 1시간 동안 캐시된 잘못된 IP로 연결을 시도한다. 내부 DNS는 60초나 300초 정도로 쓴다.

## ECS Service Discovery

ECS에서 서비스끼리 통신할 때 IP를 직접 쓰면 태스크가 재배포될 때마다 IP가 바뀐다. ECS Service Discovery는 태스크가 뜨고 내려갈 때 Route 53 Private Hosted Zone에 A 레코드를 자동으로 등록하고 삭제한다.

### 네임스페이스 생성

Service Discovery는 Cloud Map 네임스페이스를 기반으로 동작한다.

```bash
aws servicediscovery create-private-dns-namespace \
  --name service.internal \
  --vpc vpc-0123456789abcdef0 \
  --region ap-northeast-2
```

이 명령으로 Route 53에 `service.internal` private hosted zone이 자동 생성된다.

### ECS 서비스에 Service Discovery 연결

```json
{
  "serviceName": "payment-api",
  "cluster": "production",
  "taskDefinition": "payment-api:5",
  "desiredCount": 3,
  "serviceRegistries": [
    {
      "registryArn": "arn:aws:servicediscovery:ap-northeast-2:123456789012:service/srv-abc123",
      "containerName": "payment-api",
      "containerPort": 8080
    }
  ]
}
```

태스크가 실행되면 `payment-api.service.internal`에 태스크 IP가 A 레코드로 등록된다. 태스크가 3개면 레코드도 3개다.

```
payment-api.service.internal → 10.0.1.10
                              → 10.0.1.11
                              → 10.0.1.12
```

클라이언트가 `payment-api.service.internal`을 조회하면 DNS 레벨에서 여러 A 레코드 중 하나를 반환한다. 로드밸런싱이 DNS round-robin으로 처리된다.

태스크가 unhealthy 상태가 되면 Service Discovery는 Route 53에서 해당 A 레코드를 삭제한다. 삭제 후 TTL이 지나기 전까지는 클라이언트 캐시에 여전히 남아 있다. TTL을 10초 이하로 설정해야 서비스 다운 후 빠르게 트래픽이 빠진다.

```bash
aws servicediscovery create-service \
  --name payment-api \
  --namespace-id ns-abc123 \
  --dns-config "NamespaceId=ns-abc123,RoutingPolicy=MULTIVALUE,DnsRecords=[{Type=A,TTL=10}]" \
  --health-check-custom-config FailureThreshold=1
```

`RoutingPolicy=MULTIVALUE`는 조회마다 건강한 레코드를 최대 8개 반환한다. `WEIGHTED`는 가중치 기반 분산이다.

## CoreDNS로 쿠버네티스 내부 DNS

EKS나 자체 구성 쿠버네티스에서는 CoreDNS가 클러스터 내부 DNS를 담당한다. 서비스가 생성되면 `<service>.<namespace>.svc.cluster.local` 형식으로 DNS에 등록된다.

### CoreDNS 기본 동작

```
payment-api.default.svc.cluster.local → 클러스터 내부 ClusterIP
```

같은 네임스페이스 안에서는 서비스 이름만으로도 조회된다. `payment-api`만 써도 `payment-api.default.svc.cluster.local`로 검색한다. 다른 네임스페이스 서비스는 `payment-api.payment.svc.cluster.local`처럼 전체 이름을 써야 한다.

### CoreDNS Corefile 설정

CoreDNS는 Corefile로 설정한다. 클러스터 내부 DNS와 외부 DNS를 구분해서 처리할 수 있다.

```
.:53 {
    errors
    health {
        lameduck 5s
    }
    ready
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
        ttl 30
    }
    prometheus :9153
    forward . /etc/resolv.conf {
        max_concurrent 1000
    }
    cache 30
    loop
    reload
    loadbalance
}
```

`kubernetes` 플러그인이 클러스터 내부 레코드를 처리한다. `cluster.local`로 끝나는 쿼리는 여기서 응답한다.

`forward . /etc/resolv.conf`는 클러스터 내부에 없는 이름을 상위 DNS로 넘기는 설정이다. 노드의 `/etc/resolv.conf`에 설정된 DNS로 전달한다. EKS라면 Route 53 VPC 리졸버(169.254.169.253)로 넘어간다.

### 외부 도메인을 CoreDNS에서 처리

특정 도메인을 내부 DNS로 처리하고 싶을 때가 있다. 예를 들어 `internal.example.com`은 Route 53 Private Hosted Zone에서 조회해야 하는데, CoreDNS 기본 설정으로는 외부 DNS로 포워딩돼서 응답을 못 받는 경우다.

```
internal.example.com:53 {
    errors
    cache 30
    forward . 10.0.0.2 {
        prefer_udp
    }
}

.:53 {
    errors
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
    }
    forward . /etc/resolv.conf
    cache 30
}
```

`10.0.0.2`는 VPC DNS 리졸버 주소다. AWS에서 VPC DNS 리졸버는 항상 VPC CIDR의 두 번째 IP다. `10.0.0.0/16` VPC라면 `10.0.0.2`다.

이 설정으로 `internal.example.com` 하위 쿼리는 Route 53 Private Hosted Zone에서 응답하고, 나머지는 기존 경로로 처리된다.

CoreDNS 설정은 ConfigMap으로 관리된다.

```bash
kubectl edit configmap coredns -n kube-system
```

변경 후 CoreDNS Pod를 재시작해야 적용된다.

```bash
kubectl rollout restart deployment coredns -n kube-system
```

## DNS 설정 실수로 인한 내부 통신 장애

DNS는 실수가 생겨도 즉각적으로 드러나지 않는다. 캐시가 살아 있는 동안은 정상처럼 보이다가 TTL이 만료되는 시점에 장애가 터진다.

### 장애 유형 1: VPC DNS 설정이 꺼진 상태

Private Hosted Zone을 만들고 레코드도 등록했는데 내부에서 조회가 전혀 안 되는 경우, VPC의 `enableDnsSupport`가 꺼져 있을 가능성이 높다. 새로 만든 VPC나 설정을 건드린 VPC에서 자주 발생한다.

```bash
# 진단
dig @169.254.169.253 db.internal.example.com

# VPC 설정 확인
aws ec2 describe-vpc-attribute \
  --vpc-id vpc-0123456789abcdef0 \
  --attribute enableDnsSupport

# 수정
aws ec2 modify-vpc-attribute \
  --vpc-id vpc-0123456789abcdef0 \
  --enable-dns-support
```

`169.254.169.253`은 AWS VPC 내부 DNS 리졸버 주소다. 이 주소로 직접 조회했을 때 응답이 오면 리졸버 자체는 살아 있는 것이다.

### 장애 유형 2: Private Hosted Zone이 VPC에 연결 안 됨

Private Hosted Zone을 만들 때 VPC를 잘못 연결하거나, 나중에 VPC를 추가하지 않은 경우다. Zone 자체는 존재하지만 특정 VPC에서는 조회가 안 된다.

```bash
# zone에 연결된 VPC 목록 확인
aws route53 get-hosted-zone --id Z1234567890ABCDEFGHIJ \
  --query 'VPCs'
```

반환된 VPC 목록에 현재 인스턴스가 속한 VPC ID가 없으면 연결이 빠진 것이다.

```bash
aws route53 associate-vpc-with-hosted-zone \
  --hosted-zone-id Z1234567890ABCDEFGHIJ \
  --vpc VPCRegion=ap-northeast-2,VPCId=vpc-0123456789abcdef0
```

### 장애 유형 3: TTL이 길어서 변경이 반영 안 됨

DB 엔드포인트가 교체됐는데 CNAME 레코드는 옛날 주소를 가리키고, TTL이 3600초라서 1시간 동안 장애가 지속되는 경우다. 이 경우 DNS 레코드를 수정해도 캐시가 살아 있는 서비스들은 1시간 동안 기존 주소로 연결 시도를 계속한다.

즉각적인 해결은 없다. 캐시 DNS는 강제로 flush할 수 없다. 서비스 재시작으로 DNS 캐시를 초기화하거나, 캐시 만료를 기다리는 것 외에 선택지가 없다.

예방이 답이다. 내부 DNS 레코드 TTL은 60~300초로 유지한다. 장기적으로 바뀌지 않는 레코드(사무실 내부 서버 IP 등)만 긴 TTL을 쓰고, 교체 가능성이 있는 엔드포인트는 짧게 잡는다.

### 장애 유형 4: CoreDNS 포워딩 루프

CoreDNS에서 포워딩 설정을 잘못하면 DNS 쿼리가 루프를 돈다. `forward . /etc/resolv.conf`로 설정했는데 노드의 `/etc/resolv.conf`가 CoreDNS 자신을 가리키는 경우다. EKS 노드에서 이 상황이 생기면 클러스터 전체 DNS가 마비된다.

```bash
# CoreDNS 로그 확인
kubectl logs -n kube-system -l k8s-app=kube-dns

# 루프 감지 로그
# [ERROR] loop detected: request from 127.0.0.1
```

`loop` 플러그인이 Corefile에 있으면 CoreDNS가 루프를 감지하고 자신을 종료한다. CoreDNS Pod가 `CrashLoopBackOff`로 계속 재시작된다면 루프 가능성을 먼저 본다.

해결은 `/etc/resolv.conf` 대신 VPC DNS 리졸버 IP를 직접 지정하는 것이다.

```
forward . 10.0.0.2 {
    prefer_udp
}
```

### 장애 유형 5: ECS Service Discovery 레코드 찌꺼기

ECS 태스크가 비정상 종료되면 Route 53에서 레코드가 삭제되지 않는 경우가 있다. 태스크는 이미 죽었는데 DNS에는 그 IP가 남아서 다른 서비스가 죽은 IP로 연결을 시도한다.

```bash
# Route 53에서 해당 service의 레코드 확인
aws route53 list-resource-record-sets \
  --hosted-zone-id Z1234567890ABCDEFGHIJ \
  --query "ResourceRecordSets[?Name=='payment-api.service.internal.']"
```

살아 있는 태스크 IP 목록과 DNS 레코드를 비교해서 죽은 IP 레코드를 수동으로 삭제한다. Cloud Map 콘솔에서 서비스 인스턴스 목록을 직접 확인하고 삭제하는 게 더 빠르다.

근본적인 원인은 태스크가 graceful shutdown 없이 강제 종료되면 Service Discovery 해제 API 호출이 실패하는 것이다. 헬스 체크 설정에서 `FailureThreshold`를 1로 설정하면 태스크 이상 감지 후 레코드 삭제가 빨라진다.

### 진단 명령어 정리

내부 DNS 문제를 파악할 때 쓰는 명령어들이다.

```bash
# VPC 내부 리졸버로 직접 조회
dig @169.254.169.253 db.internal.example.com

# 특정 레코드 타입 조회
dig @169.254.169.253 payment-api.service.internal A

# 응답 시간 확인
dig @169.254.169.253 api.internal.example.com | grep "Query time"

# CoreDNS를 통한 조회 (쿠버네티스 Pod 내부에서)
dig @10.96.0.10 payment-api.default.svc.cluster.local

# nslookup으로 역방향 조회
nslookup 10.0.1.50 169.254.169.253

# TTL 확인
dig @169.254.169.253 db.internal.example.com | grep -A1 "ANSWER SECTION"
```

DNS 문제인지 네트워크 문제인지 구분이 먼저다. `dig`로 IP를 확인하고, 그 IP로 직접 `curl`이나 `telnet`이 되면 DNS가 문제다. IP로도 안 되면 네트워크 레벨 문제다.
