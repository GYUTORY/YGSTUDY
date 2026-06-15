---
title: Aurora MySQL Serverless v2 운영
tags: [aws, aurora, mysql, serverless, acu, scaling, cost, cloudwatch]
updated: 2026-06-15
---

# Aurora MySQL Serverless v2 운영

Serverless v2는 "용량을 인스턴스 클래스로 고르지 않고 ACU라는 연속 단위로 자동 조절하는 Aurora"다. provisioned에서 `db.r6g.large` 같은 고정 클래스를 박아두던 것을, 최소~최대 범위만 정해두면 부하에 따라 그 사이를 오르내린다. 글로 보면 "알아서 늘었다 줄었다 하니 편하겠네"인데, 실제로 운영하면 스케일 타이밍과 비용 산정에서 예상과 다른 지점을 여러 번 만난다.

이 문서는 Serverless v2의 ACU 동작과 운영 시 걸리는 부분을 다룬다. 클러스터 페일오버 일반 동작은 [Aurora_DB_Cluster.md](Aurora_DB_Cluster.md), 엔진 내부 비교는 [Aurora_DB.md](Aurora_DB.md), 커넥션 풀링은 [DB_Proxy.md](DB_Proxy.md)를 같이 보면 된다.

---

## 1. ACU가 실제로 무엇인가

ACU(Aurora Capacity Unit)는 용량 단위다. 1 ACU가 대략 메모리 2GiB와 거기에 비례하는 CPU·네트워크를 묶은 양이라고 보면 된다. Serverless v2는 이 ACU를 0.5 단위로 조절한다. 즉 2.0, 2.5, 3.0 이런 식으로 움직이고 4.0과 4.7 사이 임의값으로 가지는 않는다.

설정에서 정하는 건 두 개다.

- **Minimum ACU**: 인스턴스가 내려갈 수 있는 하한
- **Maximum ACU**: 올라갈 수 있는 상한

이 범위를 클러스터가 아니라 **인스턴스(writer, reader 각각)** 에 적용한다. writer가 8 ACU까지 올라가도 reader는 자기 부하만큼만 올라간다. 둘이 같이 움직이지 않는다.

ACU가 메모리 양이라는 점이 중요하다. provisioned에서 인스턴스 클래스를 고르면 메모리가 고정이라 buffer pool 크기도 고정인데, Serverless v2는 ACU가 변하면 buffer pool도 같이 변한다. 부하가 빠져서 ACU가 4에서 1로 내려가면 buffer pool도 8GiB에서 2GiB로 줄어든다. 따뜻하게 올려둔 캐시가 스케일 다운과 함께 날아가는 셈이라, 다시 부하가 올 때 디스크에서 페이지를 끌어와야 하는 상황이 생긴다.

---

## 2. min/max ACU를 어떻게 잡는가

처음 설정할 때 가장 많이 하는 실수가 min을 너무 낮게 잡는 것이다. "안 쓸 때 돈 아끼자"고 min ACU를 0.5나 1로 박아두면 두 가지가 따라온다.

### 2.1 메모리가 작아져서 캐시 미스가 늘어난다

min 1 ACU면 메모리가 2GiB다. 데이터셋이 수십 GB인데 buffer pool이 2GiB로 쪼그라들면, 한가한 시간대에 들어온 쿼리 하나가 디스크 I/O를 쫙 일으킨다. provisioned `db.r6g.large`(16GiB)에서 멀쩡하던 쿼리가 Serverless v2 저 ACU 구간에서 갑자기 느려지는 게 이것 때문이다.

### 2.2 max_connections가 ACU에 연동된다

Aurora MySQL의 `max_connections` 기본 파라미터는 메모리 기반 공식으로 계산된다. Serverless v2에서는 메모리가 ACU에 따라 변하므로 `max_connections`도 ACU에 따라 변한다. min ACU가 낮으면 한가한 시간대에 연결 가능한 최대 커넥션 수도 같이 낮아진다.

문제는 트래픽이 튀는 순간이다. ACU는 아직 낮은데 커넥션 폭증이 먼저 도착하면, ACU가 올라가서 `max_connections`가 늘어나기 전에 `Too many connections`로 거절당하는 경우가 있다. ECS task가 한꺼번에 스케일 아웃하거나 Lambda 동시 실행이 튈 때 이 패턴을 만난다.

대응은 두 가지다. min ACU를 평소 커넥션 수를 감당할 수준으로 올려두거나, `max_connections`를 파라미터 그룹에서 고정값으로 박는다. 다만 고정값으로 박으면 저 ACU 구간에서 메모리 대비 과한 커넥션을 허용하게 되어 OOM 위험이 생기므로, 커넥션 자체를 [DB_Proxy.md](DB_Proxy.md)로 풀링해서 백엔드 연결 수를 줄이는 쪽이 안전하다.

### 2.3 max는 피크의 1.5~2배 여유로

max ACU는 트래픽 피크에 도달했을 때 올라갈 천장이다. 피크 CPU·메모리를 provisioned에서 측정했다면 그에 해당하는 ACU에 여유를 1.5~2배 줘서 잡는다. max를 피크에 딱 맞춰두면 갑자기 평소의 2배 트래픽이 왔을 때 더 못 올라가서 스로틀이 걸린다. max는 어차피 안 쓰면 과금되지 않으므로 넉넉하게 잡아도 손해가 없다. 천장만 높이고 실제 과금은 사용한 ACU만큼이다.

---

## 3. 스케일링은 콜드 스타트가 아니라 점진 증가다

Lambda 콜드 스타트를 떠올리고 "Serverless면 처음 요청이 느리겠네"라고 오해하는 경우가 있는데, Serverless v2는 그런 방식이 아니다. 인스턴스가 항상 떠 있고 ACU만 위아래로 조절된다. 요청이 들어와서 컨테이너를 새로 띄우는 콜드 스타트는 없다.

대신 스케일은 **점진적**이다. 부하가 올라가면 ACU가 한 번에 min에서 max로 점프하지 않고, 현재 부하를 보면서 단계적으로 올린다. AWS 문서 기준으로 스케일 업은 수 초 단위로 빠르게 따라오지만, 그래도 "0초"는 아니다.

이 점진 특성이 운영에서 한 가지 함정을 만든다.

### 순간 스파이크에 ACU가 못 따라간다

평소 2 ACU로 잘 돌다가, 광고 푸시 같은 걸로 트래픽이 1~2초 안에 5배로 튀는 상황을 보자. ACU는 부하를 감지하고 올라가기 시작하지만, 5배 부하를 감당할 ACU에 도달하기까지 몇 초가 걸린다. 그 몇 초 동안은 부족한 용량으로 버텨야 해서 쿼리 지연이 튀고, 최악의 경우 커넥션이 밀린다.

즉 Serverless v2의 자동 스케일은 **완만하게 오르내리는 트래픽**에 맞다. 분 단위로 서서히 변하는 패턴이면 ACU가 자연스럽게 따라온다. 반면 초 단위로 수직 상승하는 스파이크는 ACU 증가가 부하를 못 쫓아가서, 그 구간만 보면 provisioned로 미리 띄워둔 것보다 응답이 나쁘다.

스파이크가 예측 가능하면(이벤트 시작 시각을 안다면) 그 직전에 min ACU를 임시로 올려서 미리 용량을 확보하는 식으로 대응한다. 예측 불가능한 스파이크가 잦은 워크로드라면 Serverless v2보다 provisioned가 맞는 경우가 많다.

---

## 4. 0 ACU(일시정지) 지원 여부

초기 Serverless v2는 부하가 없어도 min ACU 밑으로는 안 내려갔다. min을 0.5로 잡아도 트래픽이 0인 새벽에 0.5 ACU만큼은 계속 과금됐다. "Serverless인데 안 쓰면 0원 아니냐"는 기대와 어긋나는 지점이라 도입 검토할 때 자주 걸린다.

이후 엔진 버전에서 **자동 일시정지(0 ACU로 내려가는 동작)** 가 추가됐다. 일정 시간 연결이 없으면 0 ACU까지 내려가서 그 구간 컴퓨트 과금이 멈춘다. 다만 이건 특정 엔진 버전 이상에서만 동작하므로, 쓰려는 클러스터의 엔진 버전이 이 기능을 지원하는지 먼저 확인해야 한다. 구버전에서 돌고 있으면 아무리 한가해도 min ACU만큼은 계속 나간다.

일시정지를 쓸 때 주의할 점은 0 ACU에서 깨어날 때 약간의 재개 지연이 있다는 것이다. 개발·스테이징처럼 밤에 아무도 안 쓰는 환경에는 잘 맞지만, 새벽에도 헬스체크나 배치가 가끔 들어오는 운영 환경이면 그때마다 깨어나느라 0 ACU에 오래 머물지 못해 절감 효과가 생각보다 작다. 헬스체크 주기와 일시정지 임계 시간을 같이 봐야 한다.

---

## 5. Serverless v1과 뭐가 다른가

v1을 써본 사람이면 v2를 같은 것의 개선판으로 생각하기 쉬운데, 동작 방식이 꽤 다르다.

| 항목 | Serverless v1 | Serverless v2 |
|------|---------------|---------------|
| 스케일 방식 | 통째로 다른 용량 인스턴스로 교체 | 같은 인스턴스의 ACU를 0.5 단위로 조절 |
| 스케일 중 영향 | 스케일 포인트 찾느라 끊김/지연 발생 | 무중단 점진 조절 |
| 스케일 속도 | 분 단위, 느림 | 초 단위, 빠름 |
| reader 지원 | 없음(단일 인스턴스) | 있음, 클러스터 구성 가능 |
| Multi-AZ | 제한적 | 지원 |
| provisioned 혼합 | 불가 | 가능 |

v1은 부하가 바뀌면 "스케일 포인트"를 찾아서 통째로 다른 크기의 인스턴스로 갈아탔다. 이 과정에서 진행 중인 트랜잭션이 없는 순간을 기다리거나 강제로 끊는 동작이 있어서, 스케일이 일어날 때 순간적인 끊김이 생겼다. 그래서 v1은 사실상 "가끔 쓰는 개발 DB" 외에는 운영에 넣기 부담스러웠다.

v2는 같은 인스턴스의 용량만 조절하므로 스케일 중에 연결이 끊기지 않는다. reader를 붙여 클러스터를 구성할 수 있고 Multi-AZ도 되니, 운영 워크로드에 올릴 수 있는 수준이 됐다. 새로 도입한다면 v1을 고를 이유는 거의 없다.

---

## 6. provisioned writer + serverless reader 혼합 클러스터

Serverless v2의 실전 구성에서 자주 쓰는 패턴이다. 한 클러스터 안에서 인스턴스마다 provisioned와 serverless를 섞을 수 있다.

대표적인 조합은 **writer는 provisioned, reader는 serverless**다.

```
[Aurora Cluster]
 ├─ writer  : db.r6g.xlarge (provisioned, 고정 용량)
 ├─ reader1 : Serverless v2 (min 2 / max 16 ACU)
 └─ reader2 : Serverless v2 (min 2 / max 16 ACU)
```

writer는 쓰기 부하가 비교적 일정하고, 스파이크에 ACU가 못 따라가는 위험을 쓰기 경로에서는 피하고 싶으니 provisioned로 고정한다. 반면 reader는 읽기 트래픽이 시간대별로 출렁이는 경우가 많아서, 한가하면 ACU를 낮춰 비용을 아끼고 피크면 올라가게 serverless로 둔다.

반대 조합(serverless writer + provisioned reader)도 가능은 하지만 덜 쓴다. 쓰기 경로가 스파이크에 취약해지기 때문이다.

혼합 구성에서 신경 쓸 부분은 **페일오버 시 승격 대상**이다. provisioned writer가 죽으면 reader 중 하나가 writer로 승격되는데, 이때 승격되는 serverless reader가 쓰기 부하를 감당할 만큼 ACU 상한이 충분한지 봐야 한다. reader의 max ACU를 너무 낮게 잡아두면, 페일오버로 writer가 된 순간 쓰기 부하를 못 받아서 또 문제가 생긴다. 페일오버 우선순위(promotion tier)와 reader의 max ACU를 같이 설계해야 한다. 페일오버 동작 자체는 [Aurora_DB_Cluster.md](Aurora_DB_Cluster.md)에서 다룬다.

---

## 7. ECS·Lambda 트래픽 패턴별 ACU 튜닝과 비용 함정

### 7.1 ECS 상시 트래픽

ECS로 상시 API를 띄우는 경우, 트래픽이 낮 동안 완만하게 변하고 새벽에 떨어지는 패턴이 흔하다. 이 패턴은 Serverless v2가 잘 맞는다. 낮 피크에 ACU가 올라가고 새벽에 내려가서 비용이 트래픽을 따라간다.

비용 함정은 **min ACU를 습관적으로 높게 잡는 것**이다. 안정성 걱정에 min을 8쯤 박아두면, 새벽에 트래픽이 거의 없어도 8 ACU가 24시간 과금된다. 이러면 사실상 provisioned `db.r6g.2xlarge`를 상시 켜둔 것과 비용이 비슷해지면서, 스케일 다운으로 아낄 수 있던 부분을 다 날린다. min은 "이 밑으로 내려가면 캐시 미스나 커넥션 문제가 생기는 선"까지만 낮추고, 그 이하 안정성은 max 여유와 [DB_Proxy.md](DB_Proxy.md) 풀링으로 받친다.

### 7.2 Lambda 산발 트래픽

Lambda는 동시 실행이 갑자기 튀는 특성이 있어서 두 함정이 겹친다. 하나는 3절의 스파이크 지연, 다른 하나는 커넥션 폭증이다. Lambda 인스턴스가 한꺼번에 깨어나면 각자 DB 연결을 열어서 순식간에 커넥션이 치솟는데, 이때 ACU가 낮으면 `max_connections`도 낮아서 거절이 난다.

Lambda + Serverless v2 조합은 거의 항상 [DB_Proxy.md](DB_Proxy.md)를 끼고 가야 한다. Proxy가 커넥션을 풀링해서 백엔드 연결 수를 평탄하게 만들면, ACU가 커넥션 폭증에 휘둘리지 않고 실제 쿼리 부하만큼만 움직인다. Proxy 없이 Lambda를 Serverless v2에 직결하면 커넥션 스파이크 때마다 ACU와 `max_connections`가 부족해서 에러가 난다.

### 7.3 비용 계산의 함정 — 평균이 아니라 적분

Serverless v2 비용은 "평균 ACU × 시간"이 아니라 매 순간 ACU를 시간으로 적분한 값이다. 평균만 보고 "어차피 평균 3 ACU니까 싸겠지" 하면 어긋난다. 피크에 16 ACU로 몇 시간씩 머무는 패턴이면, 그 구간이 비용의 대부분을 차지한다. CloudWatch에서 ACU 추이를 시간축으로 보고, 높은 ACU에 오래 머무는 구간이 있으면 그건 쿼리 튜닝으로 ACU 자체를 낮춰야 할 신호다. 인덱스 안 타는 풀 스캔 하나가 buffer pool과 CPU를 끌어올려서 ACU를 상시 높게 유지시키는 경우가 실제로 있다.

---

## 8. CloudWatch 모니터링

Serverless v2에서 꼭 봐야 하는 지표는 두 개다.

### 8.1 ServerlessDatabaseCapacity

현재 인스턴스가 쓰고 있는 ACU 값이다. 이 값을 시간축으로 보면 ACU가 언제 올라가고 내려가는지, min·max에 닿는지가 보인다.

확인할 패턴은 이렇다.

- **계속 max에 붙어 있다**: max가 부족하다는 신호. 천장을 올리거나 쿼리를 튜닝해서 부하를 낮춰야 한다.
- **계속 min에 붙어 있다**: 부하가 min을 못 채운다는 뜻. min을 더 낮춰 비용을 아낄 여지가 있다. 단, 캐시 미스·커넥션 한계를 같이 확인한다.
- **톱니처럼 자주 오르내린다**: 트래픽이 출렁이는 정상 패턴일 수 있지만, 스케일 다운으로 buffer pool이 비워졌다가 다시 채워지는 낭비가 반복되는 거라면 min을 약간 올려 진폭을 줄이는 게 나을 때가 있다.

### 8.2 ACUUtilization

`ServerlessDatabaseCapacity`를 현재 max ACU로 나눈 사용률(%)이다. 즉 "지금 천장 대비 얼마나 쓰고 있나"를 본다.

- 이 값이 100%에 자주 닿으면 max ACU가 부족한 것이다.
- 항상 낮게(예: 20% 밑) 깔려 있으면 max를 과하게 잡아둔 것이다. max 자체는 안 쓰면 과금되지 않지만, 너무 높게 잡으면 폭주 쿼리가 났을 때 ACU가 끝까지 치솟아 비용이 크게 튀는 사고로 이어질 수 있어서 적정선으로 내려두는 게 안전하다.

알람은 보통 `ACUUtilization`이 일정 시간 90% 이상 유지될 때, 그리고 `ServerlessDatabaseCapacity`가 max에 장시간 붙어 있을 때를 건다. 둘 다 "용량이 모자라기 시작했다"는 선행 신호라, CPU 100%가 찍히고 쿼리가 밀린 뒤에 알아채는 것보다 먼저 손쓸 수 있다.

함께 보면 좋은 지표는 provisioned와 동일하다. `DatabaseConnections`로 커넥션이 ACU 연동 `max_connections`에 근접하는지, `CPUUtilization`으로 ACU 대비 CPU가 포화인지, `FreeableMemory`로 ACU에 묶인 메모리가 빠듯한지를 같이 본다.

---

## 9. 정리

Serverless v2는 완만하게 변하는 트래픽에서 비용을 트래픽에 맞춰 흘려보내는 구성이다. ACU가 메모리·CPU·커넥션을 한 번에 묶어 움직이므로, min을 너무 낮추면 캐시 미스와 커넥션 한계가 같이 따라오고, 초 단위 스파이크에는 ACU 증가가 부하를 못 쫓아간다. Lambda처럼 커넥션이 튀는 워크로드는 [DB_Proxy.md](DB_Proxy.md)를 끼고, writer를 안정적으로 두고 싶으면 provisioned writer + serverless reader 혼합으로 간다. 운영 중에는 `ServerlessDatabaseCapacity`와 `ACUUtilization`을 시간축으로 보면서 min/max를 조정하면 된다.
