---
title: AWS Route 53
tags: [aws, networking, route-53, dns]
updated: 2026-05-14
---

# AWS Route 53

## Route 53의 세 가지 역할

Route 53은 한 서비스에 세 가지 기능이 묶여 있다. 셋이 서로 독립이라 따로 쓰는 경우가 많다.

- 도메인 등록 기관(Registrar): `.com`, `.net`, `.io`, `.co.kr` 등 약 400개 TLD를 직접 등록.
- 권한 있는(authoritative) DNS: Public/Private Hosted Zone에서 레코드를 응답.
- 헬스 체크와 라우팅 정책: 엔드포인트 상태를 보고 다른 IP로 응답을 바꾸거나 비율로 분배.

다른 곳에서 산 도메인도 Route 53으로 DNS만 관리하는 구성이 흔하다. 가비아·후이즈·GoDaddy에서 도메인을 사고, 호스팅 존을 생성한 뒤 발급된 4개의 네임서버를 도메인 등록 사이트에 등록하면 된다. 변경 전파는 TTL과 NS 캐시 때문에 길게는 48시간까지 본다. `dig +trace example.com NS`로 실제 권한 NS가 Route 53으로 넘어왔는지 확인하는 게 빠르다.

이 문서는 일반 DNS 개념(A·CNAME·MX·TTL이 무엇인지)은 건너뛰고 Route 53에서만 나오는 동작을 다룬다.

---

## Alias 레코드와 CNAME의 차이

Route 53에서 가장 자주 쓰는 기능이 Alias다. 표면적으로 CNAME과 비슷해 보이지만 차이가 크다.

| 항목 | CNAME | Alias (A/AAAA) |
|---|---|---|
| 루트(zone apex) 도메인 적용 | 불가능 (RFC 1034) | 가능 |
| 같은 이름에 다른 레코드 공존 | 불가능 | 가능 (예: MX와 공존) |
| 쿼리 과금 | 일반 쿼리 요금 부과 | AWS 리소스 대상이면 무과금 |
| TTL | 사용자가 지정 | Route 53이 자동 관리 |
| 응답 방식 | 별도 도메인 이름을 돌려줌 | 클라이언트에 IP를 바로 돌려줌 |
| 연결 대상 | 임의 도메인 | 정해진 AWS 리소스 또는 같은 호스팅 존 내 다른 레코드 |

Alias가 가리킬 수 있는 대상은 정해져 있다.

- CloudFront 배포
- Application/Network/Gateway Load Balancer
- API Gateway
- S3 정적 웹사이트 호스팅 버킷
- Elastic Beanstalk 환경
- VPC Interface Endpoint
- Global Accelerator
- 같은 호스팅 존 안의 다른 레코드

ALB의 DNS 이름(`my-alb-1234.ap-northeast-2.elb.amazonaws.com`)은 ALB 노드의 IP가 바뀔 때마다 내부 A 레코드도 바뀐다. CNAME으로 묶으면 한 단계 더 조회해야 하고, Alias는 Route 53이 ALB의 현재 IP를 응답에 바로 넣어준다. 응답 한 번이 줄어드는 것보다 더 큰 차이는 과금이다. Alias로 AWS 리소스를 가리키는 쿼리는 청구되지 않는다. 트래픽이 많은 사이트에서 월 청구액이 눈에 띄게 다르다.

루트 도메인(`example.com`)을 ALB나 CloudFront에 붙여야 하면 선택지는 Alias뿐이다. 콘솔에서 레코드 타입은 A로 잡고 "Alias" 토글을 켠 뒤 대상을 선택한다.

```
example.com         A     ALIAS  → d12345.cloudfront.net
www.example.com     A     ALIAS  → d12345.cloudfront.net
api.example.com     A     ALIAS  → my-alb-1234.ap-northeast-2.elb.amazonaws.com
```

같은 이름에 Alias A 레코드와 MX 레코드를 같이 둘 수 있다. 회사 도메인 루트에 웹과 메일이 같이 사는 흔한 구성에서 유용하다.

한 가지 주의할 점은 Alias 대상이 다른 계정의 리소스이면 콘솔에서 바로 선택되지 않는다. 이 경우 CloudFormation이나 CLI로 `AliasTarget.HostedZoneId`와 `DNSName`을 직접 지정해야 한다.

---

## 라우팅 정책 7종

라우팅 정책은 같은 레코드 이름에 여러 응답 후보를 두고, 쿼리마다 어느 응답을 돌려줄지 결정하는 규칙이다. Health Check를 붙이면 비정상 응답은 자동으로 제외된다.

### Simple

가장 단순한 형태. 한 레코드에 응답 하나(혹은 여러 IP를 라운드로빈)만 둔다. Health Check를 붙일 수 없다. Route 53을 그냥 DNS로만 쓰는 경우.

사용 시점: 트래픽이 한 곳으로만 가고, 장애 시 다른 곳으로 돌릴 필요가 없을 때.

### Weighted

같은 이름에 여러 레코드를 만들고 각자에 0~255의 weight를 준다. 응답 비율은 `해당 weight / 전체 weight 합`이다.

```
api.example.com  A  10.0.1.1   weight=90   set-id="prod"
api.example.com  A  10.0.1.2   weight=10   set-id="canary"
```

위 설정이면 약 10%가 canary로 간다. 점진 배포(canary → 25% → 50% → 100%)나 A/B 테스트에 쓴다. weight 0으로 두면 응답에서 빠진다(완전 차단).

실무에서 흔히 빠지는 함정은 TTL이다. 60초로 두지 않으면 비율 조정이 천천히 반영된다. 또 클라이언트 DNS 캐시가 우리 손을 떠나 있어서 정확한 90/10이 나오지 않는다. 큰 표본에서만 비율에 수렴한다.

### Latency

리전마다 같은 이름으로 레코드를 만들고 `region`을 지정한다. 사용자의 DNS 리졸버 위치를 기준으로 가장 지연이 적은 리전이 응답으로 돌아간다.

```
app.example.com  A  ALIAS → alb-tokyo     region=ap-northeast-1
app.example.com  A  ALIAS → alb-virginia  region=us-east-1
app.example.com  A  ALIAS → alb-frankfurt region=eu-central-1
```

사용 시점: 같은 애플리케이션을 멀티 리전에 배포해 사용자별로 가까운 리전에 붙이고 싶을 때. 단, 기준이 사용자의 IP가 아니라 사용자가 쓰는 리졸버의 IP라 ISP에 따라 엉뚱한 리전이 나올 수 있다. 정확한 위치 기반 분배가 필요하면 Geolocation을 쓴다.

### Failover

Primary와 Secondary 두 레코드를 만든다. Primary에 붙인 Health Check가 정상이면 Primary, 비정상이면 Secondary가 응답된다.

```
www.example.com  A  ALIAS → alb-primary   failover=PRIMARY   hc=health-check-id
www.example.com  A  ALIAS → s3-maintenance failover=SECONDARY
```

Primary가 ALB, Secondary가 S3 정적 사이트("점검 중입니다" 페이지)인 구성이 흔하다. Primary와 Secondary가 둘 다 비정상이면 Route 53은 Primary로 응답한다(아무것도 안 돌려주는 것보다 낫다는 판단).

### Geolocation

사용자의 IP가 속한 대륙·국가·미국 주(state) 단위로 응답을 분리한다. 매칭 안 되는 트래픽을 위해 `Default` 레코드를 반드시 만들어야 한다. 만들지 않으면 매칭 실패한 지역은 NXDOMAIN을 받는다.

```
www.example.com  A → ip-korea   geolocation=KR
www.example.com  A → ip-japan   geolocation=JP
www.example.com  A → ip-eu      geolocation=continent-EU
www.example.com  A → ip-default geolocation=Default
```

사용 시점: 컴플라이언스(EU 트래픽은 EU에서만 처리), 언어별 사이트 분기, 특정 국가 차단(NXDOMAIN 의도). Latency와 달리 사용자 IP의 GeoIP 매핑 기준이라 더 결정적이다.

### Geoproximity

지리적으로 가까운 리소스로 보내되, 각 리소스에 `bias`(-99 ~ +99)를 줘서 영향 반경을 늘리거나 줄일 수 있다. 일반 콘솔에서는 보이지 않고 Traffic Flow(트래픽 정책 시각 편집기) 안에서 쓴다.

```
서울 리소스: bias=+30   → 서울이 더 멀리까지 트래픽을 끌어옴
도쿄 리소스: bias=0
```

사용 시점: 단순한 거리 계산만으로는 잘못 분배되는 경우. 서울 리전 용량을 늘려서 더 많은 트래픽을 끌어와야 할 때 bias를 양수로 올린다. 반대로 트래픽을 줄여야 하면 음수로.

비AWS 리소스도 위경도(latitude/longitude)로 직접 좌표를 넣어 등록할 수 있다.

### Multi-Value Answer

같은 이름에 최대 8개의 레코드를 두고, Route 53이 응답할 때 그중 정상인 것들을 무작위로 골라서 반환한다. 클라이언트는 받은 IP 중 하나에 붙는다. Health Check가 가능한 Simple이라고 보면 된다.

```
api.example.com  A  10.0.1.1  hc=hc-1
api.example.com  A  10.0.1.2  hc=hc-2
api.example.com  A  10.0.1.3  hc=hc-3
```

ALB만큼은 아니지만 DNS 단에서 가벼운 분산과 장애 격리가 필요할 때. ALB가 못 들어가는 환경(예: TCP가 아닌 UDP 서비스, 또는 멀티 리전에서 ALB 앞단을 두고 싶을 때)에 쓴다.

---

## Health Check

Route 53 Health Check는 3가지 형태로 만든다.

### 엔드포인트 모니터

전 세계 Route 53 healthchecker 노드(15개 이상의 위치)에서 지정한 엔드포인트로 주기적으로 요청을 보낸다.

- 프로토콜: HTTP, HTTPS, HTTP STR MATCH, HTTPS STR MATCH, TCP
- 요청 간격: 30초(Standard) 또는 10초(Fast, 비용 추가)
- 실패 임계값: 1~10회 연속 실패하면 Unhealthy로 전환
- 위치별 다수결: 18% 이상의 위치에서 정상이면 정상 판정

`STR MATCH`는 응답 본문에 특정 문자열이 있어야 정상으로 친다. `/health`가 200을 돌려줘도 본문이 `{"db":"down"}`이면 비정상으로 잡는 식. 단순한 200 체크보다 한 단계 더 정확하다.

엔드포인트가 사설 IP에 있으면 헬스체커가 접근할 수 없다. 사설 리소스를 보려면 CloudWatch 알람 기반 헬스 체크를 쓰거나, NLB·ALB의 외부 리스너를 통해 우회한다.

### CloudWatch Alarm 기반

이미 만들어 둔 CloudWatch 알람의 상태를 Health Check로 가져다 쓴다. RDS 연결 수, Lambda 에러율, 사용자 정의 메트릭 등 엔드포인트 직접 호출로는 알 수 없는 신호를 헬스로 만들 때 쓴다. 사설 VPC 안 리소스를 모니터링하려면 사실상 이 방법이다.

알람이 `ALARM` 상태면 헬스도 Unhealthy. 데이터 부족 시 동작은 옵션으로 정한다(`Healthy`, `Unhealthy`, `Last known status`).

### Calculated

여러 Health Check를 부울식으로 결합한다. "Primary DB가 정상이고, ALB도 정상일 때만 Primary 리전을 정상으로 친다" 같은 복합 조건을 만든다.

```
calculated-hc = (db-hc 정상) AND (alb-hc 정상) AND (cache-hc 정상)
```

최대 256개의 child health check 중 N개 이상 정상이면 통과, 같은 조합을 표현할 수 있다. Failover Routing에 이 calculated 결과를 연결하면 의존 서비스 전체가 살아 있을 때만 Primary를 응답하게 된다.

### Failover와의 동작

Health Check가 Unhealthy로 바뀌어도 즉시 페일오버되는 게 아니다. 시퀀스는 다음과 같다.

1. 헬스체커 위치들에서 요청 실패가 누적 → 실패 임계값 도달 → Health Check가 Unhealthy로 전환
2. Route 53 권한 응답이 해당 레코드를 후보에서 제외
3. 클라이언트가 다음 DNS 쿼리를 보낼 때 새 응답(Secondary)을 받음
4. 단, 클라이언트와 중간 리졸버에 캐시된 응답은 TTL이 끝나야 새로 묻는다

페일오버 체감 시간은 `Health Check 감지 시간 + DNS TTL`이다. 30초 간격×3회 실패 + TTL 60초면 최악의 경우 약 3분 반. Health Check를 Fast(10초)로 두고 TTL을 60초로 줄이는 게 일반적인 튜닝이다. 단 둘 다 비용이 늘어난다.

---

## Private Hosted Zone과 VPC Resolver

### VPC DNS Resolver

VPC를 만들면 자동으로 부여되는 DNS 리졸버가 있다. 두 가지 주소로 접근한다.

- VPC CIDR의 `.2` 주소: VPC CIDR이 `10.0.0.0/16`이면 `10.0.0.2`
- 링크-로컬 주소: `169.254.169.253`

EC2의 `/etc/resolv.conf`에 들어가는 nameserver가 이 주소다. 인스턴스가 어떤 도메인을 물으면 이 리졸버가 처리한다. 처리 순서는 다음과 같다.

1. VPC에 연결된 Private Hosted Zone에 매칭되는 레코드가 있으면 그것을 응답
2. 아니면 Resolver Outbound 규칙에 매칭되는지 확인 → 매칭되면 지정한 외부 리졸버로 포워딩
3. 아니면 퍼블릭 DNS로 재귀 해석

VPC 단위 옵션 두 개를 켜야 정상 동작한다.

- `enableDnsSupport`: VPC의 DNS 리졸버를 사용할지
- `enableDnsHostnames`: EC2에 퍼블릭 DNS 이름을 부여할지

콘솔에서 만들면 보통 켜져 있지만, Terraform이나 CloudFormation으로 만든 VPC가 둘 다 꺼져 있어서 Private Hosted Zone이 해석이 안 되는 사고가 종종 난다.

### Private Hosted Zone

특정 VPC에서만 응답하는 호스팅 존이다. `internal.company.com` 같은 사내용 도메인을 외부에 노출하지 않고 쓰고 싶을 때 사용한다.

```
internal.company.com         (Private Hosted Zone)
  ├─ db.internal.company.com       A → 10.0.1.50
  ├─ cache.internal.company.com    A → 10.0.1.51
  └─ kafka.internal.company.com    A → 10.0.1.52  (CNAME으로 NLB 가능)
```

같은 도메인 이름을 Public과 Private 둘 다에 만들 수 있다(Split-View DNS). 같은 `api.example.com`이 VPC 안에서는 사설 IP를, 인터넷에서는 ALB의 퍼블릭 IP를 응답하게 한다.

여러 VPC에 같은 PHZ를 연결할 수 있다. 다른 계정의 VPC도 가능한데, 이 경우 `CreateVPCAssociationAuthorization`을 먼저 호출해야 한다.

주의할 점: PHZ는 VPC 외부에서 보이지 않는다. 온프레미스 사무실 PC가 VPN으로 VPC에 들어와도 자신의 PC는 회사 DNS를 쓰므로 PHZ 도메인을 못 푼다. 이를 풀려면 Resolver Endpoint가 필요하다.

---

## Resolver Endpoint (Inbound / Outbound)

온프레미스와 AWS 사이의 DNS 해석을 양방향으로 잇는 기능이다. VPC 안에 ENI를 만들어 그 IP가 DNS 서버 역할을 한다. AZ당 최소 2개 ENI를 두라고 권장한다.

### Inbound Resolver Endpoint

방향: 온프레미스 → AWS

VPC 안에 ENI를 만들고, 그 IP를 온프레미스 DNS에 conditional forwarder로 등록한다. 사내 PC가 `db.internal.company.com`을 물으면 사내 DNS가 inbound endpoint로 포워딩 → endpoint가 VPC의 Resolver를 거쳐 PHZ에서 응답.

```
[온프레 PC] → [사내 DNS]
              "internal.company.com이면 10.0.1.10, 10.0.1.11로 포워딩"
            → [Inbound Endpoint ENI 10.0.1.10] → [VPC Resolver] → [PHZ]
```

### Outbound Resolver Endpoint

방향: AWS → 온프레미스

VPC 안의 EC2가 `corp.local`(사내 AD 도메인)을 물어야 할 때 사용한다. Resolver Rule을 만들어 `corp.local` 도메인은 사내 DNS IP(예: `192.168.1.10`)로 포워딩하도록 등록한다.

```
[EC2] → [VPC Resolver]
        Resolver Rule: "corp.local이면 192.168.1.10으로 포워딩"
      → [Outbound Endpoint ENI] → [VPN/Direct Connect] → [사내 DNS]
```

Resolver Rule은 여러 VPC, 다른 계정과 RAM(Resource Access Manager)으로 공유 가능하다. 조직 전체가 같은 규칙으로 사내 DNS를 바라보게 만든다.

가격은 ENI당 시간 과금($0.125/시간, AZ 2개면 시간당 $0.25, 월 약 $180)이라 작은 환경에서는 부담이다. 트래픽이 적으면 EC2 위에 BIND나 Unbound를 직접 띄우는 게 더 싸다.

---

## Route 53 Application Recovery Controller (ARC)

멀티 리전 페일오버를 정밀하게 통제하는 별도 서비스다. 일반 Failover Routing보다 비싸지만, "Health Check 자동 판정"이 아니라 "사람 또는 자동화가 결정하는 명시적 스위치"가 필요한 환경에 쓴다. 금융권에서 자주 본다.

### Routing Control

리전마다 ON/OFF 스위치를 만든다. Route 53의 일반 레코드 위에 이 스위치를 얹어, ON인 리전만 트래픽을 받게 한다. 스위치를 사람이 직접 토글하거나 람다로 토글한다.

이 스위치는 5개 리전에 분산된 클러스터 엔드포인트로 동작한다. 5개 중 3개 이상이 살아 있으면 토글이 작동하므로, 리전 장애 자체로 페일오버 명령이 막히는 일을 줄인다.

### Safety Rule

"Primary와 Secondary를 동시에 OFF로 만들지 못한다" 같은 안전 규칙을 걸어둔다. 운영자가 실수로 모든 리전을 닫는 사고를 막는다.

### Readiness Check

각 리전이 페일오버를 받을 준비가 되었는지(스케일링, RDS 복제 지연, ECS 태스크 수 등) 자동으로 검증한다. Routing Control과 별개로 동작하고, 검증 결과를 콘솔에서 본다.

### Zonal Shift / Zonal Autoshift

AZ 단위로 트래픽을 빼는 기능. AZ 한 곳에 문제가 생긴 게 의심되면 명령 한 줄로 ALB·NLB에서 해당 AZ를 빼서 회피한다. Autoshift는 AWS가 내부적으로 회색 장애를 감지했을 때 자동으로 옮긴다.

---

## 비용 구조

US 리전 기준 2024년 가격. 정확한 금액은 매년 조금씩 바뀐다.

### Hosted Zone

- 호스팅 존당 월 $0.50 (Public/Private 동일)
- 25개 초과분은 호스팅 존당 월 $0.10
- 호스팅 존을 만든 시점에 일할 계산되지 않고 그 달 전체 요금이 부과된다. 테스트로 잠깐 만들었다 지우면 그 달 분은 그대로 청구된다.

### DNS 쿼리

- Standard 쿼리: 백만 건당 $0.40 (월 10억 건까지)
- 10억 건 초과: 백만 건당 $0.20
- Latency / Geolocation / Geoproximity / Multi-Value Routing 쿼리: 백만 건당 $0.60 (10억 초과 $0.30)
- Alias가 가리키는 대상이 AWS 리소스이면 그 쿼리는 무료

쿼리 비용 절감은 TTL 늘리기가 핵심이다. 같은 도메인에 하루 1억 건이 들어오는 사이트라면 TTL 60초보다 TTL 300초가 단순히 다음 쿼리까지의 간격을 5배로 늘려 비용도 1/5에 가깝게 떨어진다. 단 IP 변경 시 반영 지연이 그만큼 길어지니 운영 정책과 조정한다.

### Health Check

- AWS 엔드포인트 기준 헬스 체크: 월 $0.50
- AWS 외부 엔드포인트(인터넷 IP): 월 $0.75
- Fast Interval(10초): 위 금액에 $1.00 추가
- HTTPS, STR MATCH, Latency 측정 옵션: 각각 $1.00 추가

여러 ALB를 가리키는 헬스 체크 100개면 월 $50이다. 그렇게 큰 금액은 아니지만, 검증용으로 만들었던 헬스 체크가 안 지워져서 쌓이는 경우가 흔하다. 분기마다 사용하지 않는 헬스 체크는 정리한다.

### Resolver Endpoint

- ENI당 시간 $0.125 (AZ 두 개면 시간당 $0.25, 월 약 $180)
- Resolver 쿼리 처리: 1억 건까지 백만 건당 $0.40

### ARC

- Routing Control 클러스터: 월 $2.50
- Routing Control 자체는 별도 과금 없음
- Readiness Check, Safety Rule도 별도 과금 없음

### TTL과 캐싱으로 비용 줄이기

쿼리는 클라이언트 → ISP 리졸버 → 권한 NS(Route 53) 순으로 흐른다. Route 53에 청구되는 건 ISP 리졸버까지 도달한 쿼리뿐이다. ISP 리졸버가 캐시를 가지고 있으면 우리에게는 비용이 발생하지 않는다.

- 자주 안 바뀌는 레코드: TTL 3600~86400
- 페일오버 대상 레코드: TTL 60~120 (Health Check 감지 시간 + α)
- 가중치/카나리 레코드: TTL 60 (비율 조정 반영 지연이 영향)

CloudFront 같은 Alias 대상은 어차피 무료이므로 TTL을 신경 쓸 이유가 없다. 비AWS IP를 가리키는 A 레코드, 외부 도메인을 가리키는 CNAME이 비용 절감의 주 대상이다.

---

## 참고

- Route 53 공식 문서: https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/
- Resolver Endpoint 가이드: https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html
- Application Recovery Controller: https://docs.aws.amazon.com/r53recovery/latest/dg/
- Route 53 가격: https://aws.amazon.com/route53/pricing/
