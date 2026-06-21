---
title: Aurora MySQL Serverless v2 운영
tags: [aws, aurora, mysql, serverless, acu, scaling, cost, cloudwatch, rds-proxy, data-api]
updated: 2026-06-21
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

현재 ACU에서 `max_connections`가 얼마인지 DB에 직접 물어보면 된다. 부하 시간대와 한가한 시간대에 각각 찍어보면 ACU 연동으로 값이 바뀌는 게 보인다.

```sql
-- 현재 허용 커넥션 상한과 실제 사용 커넥션
SHOW VARIABLES LIKE 'max_connections';
SHOW STATUS LIKE 'Threads_connected';

-- 거절이 누적되는지 확인. 이 값이 늘고 있으면 이미 한계에 부딪힌 것
SHOW GLOBAL STATUS LIKE 'Aborted_connects';
SHOW GLOBAL STATUS LIKE 'Connection_errors_max_connections';
```

기본값을 쓰면 Aurora MySQL의 `max_connections`는 대략 `메모리(바이트) / 12582880` 공식으로 계산된다. 1 ACU(2GiB)면 170 안팎, 8 ACU(16GiB)면 1300 안팎이 나온다. min 1 ACU로 박아두면 한가한 시간대 커넥션 천장이 170까지 떨어진다는 뜻이다.

대응은 두 가지다. min ACU를 평소 커넥션 수를 감당할 수준으로 올려두거나, `max_connections`를 파라미터 그룹에서 고정값으로 박는다.

```bash
# 클러스터 파라미터 그룹에 max_connections 고정값 지정
aws rds modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name aurora-mysql8-serverless \
  --parameters "ParameterName=max_connections,ParameterValue=2000,ApplyMethod=immediate"
```

다만 고정값으로 박으면 저 ACU 구간에서 메모리 대비 과한 커넥션을 허용하게 되어 OOM 위험이 생긴다. 2GiB 메모리에 커넥션 2000개를 받으면 커넥션당 메모리만으로 buffer pool을 잠식한다. 그래서 커넥션 자체를 [DB_Proxy.md](DB_Proxy.md)로 풀링해서 백엔드 연결 수를 줄이는 쪽이 안전하다.

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

그 몇 초 동안 무슨 일이 벌어지는지 시간순으로 보면 이렇다.

```
t=0.0s  광고 푸시 발송, 트래픽 2 ACU → 5배
t=0.2s  앱 인스턴스들이 커넥션 추가 요청, max_connections는 아직 2 ACU 기준(약 340)
t=0.5s  Too many connections 거절 시작, 일부 요청 커넥션 타임아웃
t=1.5s  ACU가 부하 감지하고 상승 시작 (2 → 4 → 6 ...)
t=4.0s  필요한 ACU(약 10)에 도달, max_connections도 따라 올라옴
t=4.0s  이때 이미 앞단에서 5xx가 수천 건 나간 뒤
```

스파이크 구간의 커넥션 타임아웃은 애플리케이션에서 무한정 재시도하면 오히려 폭주를 키운다. 커넥션 획득 타임아웃을 짧게 잡고, 거절(`Too many connections`, `ER_CON_COUNT_ERROR`)에는 지수 백오프 + 지터로 물러나야 한다.

```javascript
// mysql2 커넥션 풀: 획득 대기를 짧게 끊어 큐가 무한정 쌓이는 걸 막는다
const pool = mysql.createPool({
  host: process.env.DB_HOST,
  connectionLimit: 20,        // 인스턴스당 상한을 명시. 폭주 시 백엔드 보호
  connectTimeout: 3000,       // 커넥션 수립 3초 넘으면 포기
  // 풀이 꽉 찼을 때 무한 대기 금지
  queueLimit: 50,
  waitForConnections: true,
});

const ACU_LAG_ERRORS = new Set([1040, 1203]); // ER_CON_COUNT_ERROR, max_user_connections

async function queryWithBackoff(sql, params, attempt = 0) {
  try {
    return await pool.query(sql, params);
  } catch (e) {
    if (ACU_LAG_ERRORS.has(e.errno) && attempt < 4) {
      // ACU가 따라 올라오는 몇 초를 백오프로 버틴다
      const delay = Math.min(2000, 100 * 2 ** attempt) + Math.random() * 100;
      await new Promise(r => setTimeout(r, delay));
      return queryWithBackoff(sql, params, attempt + 1);
    }
    throw e;
  }
}
```

스파이크가 예측 가능하면(이벤트 시작 시각을 안다면) 그 직전에 min ACU를 임시로 올려서 미리 용량을 확보하는 식으로 대응한다. min을 올리면 그 즉시 인스턴스가 해당 ACU로 올라가므로, 이벤트 5~10분 전에 올렸다가 끝나면 되돌린다.

```bash
# 이벤트 직전: min ACU를 8로 끌어올려 용량 선확보 (즉시 반영)
aws rds modify-db-cluster \
  --db-cluster-identifier prod-aurora \
  --serverless-v2-scaling-configuration MinCapacity=8,MaxCapacity=32 \
  --apply-immediately

# 이벤트 종료 후: 원래 min으로 복귀
aws rds modify-db-cluster \
  --db-cluster-identifier prod-aurora \
  --serverless-v2-scaling-configuration MinCapacity=2,MaxCapacity=32 \
  --apply-immediately
```

예측 불가능한 스파이크가 잦은 워크로드라면 Serverless v2보다 provisioned가 맞는 경우가 많다.

### min ACU를 낮게 잡으면 콜드 상태 첫 쿼리가 느리다

스파이크와 별개로, min을 0.5~1로 박아둔 클러스터는 한가한 새벽에 첫 쿼리가 눈에 띄게 느린 경우가 있다. 콜드 스타트는 아니지만, 1절에서 말한 buffer pool 축소가 원인이다. 스케일 다운으로 ACU가 min까지 내려가면 buffer pool도 같이 쪼그라들어서 따뜻하던 페이지가 빠진다. 새벽에 들어온 첫 쿼리는 그 줄어든 캐시 위에서 디스크 I/O를 일으킨다.

같은 쿼리를 평소(따뜻한 캐시)와 새벽 첫 실행(차가운 캐시)에 각각 찍어보면 차이가 드러난다.

```sql
-- buffer pool에서 읽었는지(논리 read) 디스크에서 읽었는지(물리 read) 비교
SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_read_requests'; -- 논리
SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_reads';         -- 물리(디스크)
-- 첫 쿼리 직후 Innodb_buffer_pool_reads가 크게 튀면 캐시가 식어 있었다는 뜻
```

새벽에도 응답 시간이 중요한 서비스라면, min을 무작정 낮추지 말고 자주 쓰는 테이블이 buffer pool에 남을 만큼은 확보해야 한다. 또는 새벽 배치 직전에 워밍 쿼리(주요 테이블 `SELECT COUNT(*)`나 인덱스 스캔)를 한 번 돌려 페이지를 끌어올리는 방법도 쓴다.

---

## 4. 0 ACU(일시정지) 지원 여부

초기 Serverless v2는 부하가 없어도 min ACU 밑으로는 안 내려갔다. min을 0.5로 잡아도 트래픽이 0인 새벽에 0.5 ACU만큼은 계속 과금됐다. "Serverless인데 안 쓰면 0원 아니냐"는 기대와 어긋나는 지점이라 도입 검토할 때 자주 걸린다.

이후 엔진 버전에서 **자동 일시정지(0 ACU로 내려가는 동작)** 가 추가됐다. 일정 시간 연결이 없으면 0 ACU까지 내려가서 그 구간 컴퓨트 과금이 멈춘다. 다만 이건 특정 엔진 버전 이상에서만 동작하고, 일시정지 임계 시간을 명시적으로 켜야 하며, 그동안 연결이 단 하나도 없어야 한다. 이 조건을 못 맞추면 v2는 **0으로 안 내려가고 min ACU에서 바닥을 친다.** 운영 클러스터 대다수가 헬스체크·모니터링 에이전트·커넥션 풀 keep-alive로 항상 연결이 떠 있어서, 실제로는 0 ACU를 못 보는 경우가 많다.

이 "0으로 안 내려간다"가 바로 idle 비용의 정체다. min ACU × 24시간 × 30일은 트래픽이 0이어도 그대로 나간다. min을 무심코 높게 잡으면 한 달 내내 그 바닥 비용을 깐다.

```python
# min ACU 설정값에 따른 월 idle 바닥 비용 (us-east-1, $0.12/ACU-hour 기준)
ACU_PRICE = 0.12          # ACU-hour 단가, 리전마다 다름
HOURS_PER_MONTH = 730

for min_acu in [0.5, 1, 2, 4, 8]:
    idle_cost = min_acu * ACU_PRICE * HOURS_PER_MONTH
    print(f"min {min_acu:>4} ACU → 월 idle 바닥 ${idle_cost:>7.2f}")

# min  0.5 ACU → 월 idle 바닥 $  43.80
# min  1   ACU → 월 idle 바닥 $  87.60
# min  2   ACU → 월 idle 바닥 $ 175.20
# min  4   ACU → 월 idle 바닥 $ 350.40
# min  8   ACU → 월 idle 바닥 $ 700.80
```

min 8 ACU면 트래픽이 전혀 없어도 월 $700이 깔린다. "Serverless니까 안 쓰면 싸겠지"가 어긋나는 지점이 이것이다.

자동 일시정지를 쓸 때 주의할 점은 0 ACU에서 깨어날 때 약간의 재개 지연이 있다는 것이다. 개발·스테이징처럼 밤에 아무도 안 쓰는 환경에는 잘 맞지만, 새벽에도 헬스체크나 배치가 가끔 들어오는 운영 환경이면 그때마다 깨어나느라 0 ACU에 오래 머물지 못해 절감 효과가 생각보다 작다. 헬스체크 주기와 일시정지 임계 시간을 같이 봐야 한다.

```bash
# 자동 일시정지 임계 시간 설정 (예: 연결 없이 1시간 지나면 0 ACU)
# SecondsUntilAutoPause는 지원 엔진 버전에서만 적용된다
aws rds modify-db-cluster \
  --db-cluster-identifier dev-aurora \
  --serverless-v2-scaling-configuration \
      MinCapacity=0,MaxCapacity=8,SecondsUntilAutoPause=3600 \
  --apply-immediately
```

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

RDS Proxy를 Serverless v2 앞에 둘 때 한 가지 함정이 있다. Proxy의 `MaxConnectionsPercent`는 **타깃 DB의 `max_connections`에 대한 비율**이다. 그런데 Serverless v2는 ACU에 따라 `max_connections`가 변하므로, 한가한 시간대에 ACU가 내려가면 Proxy가 열 수 있는 백엔드 커넥션 상한도 같이 내려간다. min ACU가 낮으면 Proxy가 확보한 풀이 갑자기 작아지면서, Proxy 단에서 커넥션 대기(`borrow timeout`)가 길어진다.

```bash
# RDS Proxy 풀 설정. MaxConnectionsPercent는 타깃의 max_connections 기준 비율
aws rds modify-db-proxy-target-group \
  --db-proxy-name aurora-proxy \
  --target-group-name default \
  --connection-pool-config 'MaxConnectionsPercent=75,MaxIdleConnectionsPercent=50,ConnectionBorrowTimeout=20'
```

`MaxConnectionsPercent`를 너무 높게(예: 100) 잡으면 ACU가 낮을 때 Proxy가 백엔드를 꽉 채워서 다른 직결 커넥션(마이그레이션 도구, 관리 접속)이 들어갈 자리가 없어진다. Proxy를 쓰면서도 min ACU를 어느 정도 받쳐줘야 풀이 의미 있게 유지된다. Proxy가 커넥션 폭증은 막아주지만, ACU 연동으로 풀 자체가 줄어드는 건 못 막는다.

### 7.3 비용 계산의 함정 — 평균이 아니라 적분

Serverless v2 비용은 "평균 ACU × 시간"이 아니라 매 순간 ACU를 시간으로 적분한 값이다. 평균만 보고 "어차피 평균 3 ACU니까 싸겠지" 하면 어긋난다. 피크에 16 ACU로 몇 시간씩 머무는 패턴이면, 그 구간이 비용의 대부분을 차지한다. CloudWatch에서 ACU 추이를 시간축으로 보고, 높은 ACU에 오래 머무는 구간이 있으면 그건 쿼리 튜닝으로 ACU 자체를 낮춰야 할 신호다. 인덱스 안 타는 풀 스캔 하나가 buffer pool과 CPU를 끌어올려서 ACU를 상시 높게 유지시키는 경우가 실제로 있다.

### 7.4 상시 부하면 provisioned가 더 싸다 — 비용 역전

ACU-hour 단가는 같은 용량의 provisioned 인스턴스 시간 단가보다 비싸다. 탄력성에 프리미엄이 붙어 있다. 그래서 부하가 출렁이면 스케일 다운으로 그 프리미엄을 상쇄하고도 남지만, **부하가 상시 높게 깔리면 역전된다.**

us-east-1 대략 단가로 비교하면(리전·시점마다 다르므로 직접 확인 필요):

| 구성 | 메모리 | 시간 단가 | 월 비용(730h, 상시) |
|------|--------|-----------|----------------------|
| provisioned `db.r6g.large` | 16 GiB | ~$0.29 | ~$212 |
| Serverless v2 상시 8 ACU | 16 GiB | 8 × $0.12 = $0.96 | ~$700 |

같은 16GiB를 상시로 쓰면 Serverless v2가 provisioned의 3배 가까이 나온다. 24시간 부하가 거의 평탄한 워크로드를 "Serverless가 요즘 트렌드니까"로 v2에 올려두면 이렇게 손해를 본다.

```python
# 평균 ACU 기준 손익분기. 평균 ACU가 이 선을 넘으면 provisioned가 싸다
ACU_PRICE = 0.12
PROVISIONED_HOURLY = 0.29   # db.r6g.large (16GiB ≈ 8 ACU)

break_even_acu = PROVISIONED_HOURLY / ACU_PRICE
print(f"손익분기 평균 ACU: {break_even_acu:.2f}")
# 손익분기 평균 ACU: 2.42
# 24시간 평균 ACU가 2.4를 꾸준히 넘으면 동급 provisioned로 바꾸는 게 싸다
# (단, reader 자동 확장·페일오버 무중단 같은 운영 이점은 비용 밖의 판단)
```

판단 기준은 단순하다. CloudWatch에서 `ServerlessDatabaseCapacity`의 24시간 평균을 뽑아, 그 값이 동급 provisioned 시간단가 ÷ ACU 단가(여기선 약 2.4)를 상시 넘으면 provisioned 전환을 검토한다. 반대로 피크와 바닥의 차이가 커서 평균이 그 선 밑이면 Serverless v2가 이긴다.

---

## 8. Data API를 쓸 때 제약

Serverless v2는 Data API(HTTP로 SQL을 던지는 인터페이스)를 지원한다. Lambda에서 커넥션 관리 없이 HTTPS로 쿼리를 보내고 IAM으로 인증하므로, 커넥션 폭증 문제를 원천적으로 피하는 선택지로 보인다. 실제로 매 호출이 독립 HTTP 요청이라 ACU 연동 `max_connections`에 걸리지 않는다. 다만 일반 커넥션 방식과 동작이 달라서 그대로 옮기면 걸리는 지점이 있다.

```javascript
import { RDSDataClient, ExecuteStatementCommand } from "@aws-sdk/client-rds-data";

const client = new RDSDataClient({ region: "us-east-1" });

await client.send(new ExecuteStatementCommand({
  resourceArn: "arn:aws:rds:us-east-1:111122223333:cluster:prod-aurora",
  secretArn:   "arn:aws:secretsmanager:us-east-1:111122223333:secret:db-cred",
  database:    "app",
  sql:         "SELECT id, name FROM users WHERE status = :status",
  parameters:  [{ name: "status", value: { stringValue: "active" } }],
}));
```

운영에서 부딪히는 제약은 이렇다.

- **요청·응답 크기 상한이 있다.** 결과 집합이 큰 쿼리(수만 행, 큰 BLOB)는 Data API로 가져오면 크기 제한에 걸려 잘리거나 에러가 난다. 대량 결과는 페이지네이션으로 끊거나 일반 커넥션을 써야 한다.
- **세션 상태가 호출 간에 유지되지 않는다.** 각 `ExecuteStatement`가 독립이라 `SET` 세션 변수, 임시 테이블, 수동 트랜잭션이 호출을 넘어 살아남지 않는다. 트랜잭션이 필요하면 `BeginTransaction`으로 받은 `transactionId`를 매 호출에 명시적으로 넘겨야 한다.
- **지연(latency)이 일반 커넥션보다 높다.** HTTP·IAM·Secrets Manager를 매번 거치므로 단건 쿼리 왕복이 직결보다 느리다. 짧은 쿼리를 루프로 수만 번 날리는 패턴이면 이 오버헤드가 누적된다.
- **파라미터 타입을 명시적으로 지정해야 한다.** 위 예처럼 `stringValue`·`longValue` 등 타입 필드를 직접 골라야 하고, 타입을 잘못 매핑하면 캐스팅 에러가 난다. ORM이 만들어주던 바인딩을 손으로 짜는 셈이라 코드가 장황해진다.

Data API는 "가끔 호출되는 Lambda에서 가벼운 쿼리"에 잘 맞는다. 대량 조회나 복잡한 트랜잭션, 낮은 지연이 필요한 경로면 [DB_Proxy.md](DB_Proxy.md)를 낀 일반 커넥션이 낫다.

---

## 9. CloudWatch 모니터링

Serverless v2에서 꼭 봐야 하는 지표는 두 개다.

### 9.1 ServerlessDatabaseCapacity

현재 인스턴스가 쓰고 있는 ACU 값이다. 이 값을 시간축으로 보면 ACU가 언제 올라가고 내려가는지, min·max에 닿는지가 보인다.

확인할 패턴은 이렇다.

- **계속 max에 붙어 있다**: max가 부족하다는 신호. 천장을 올리거나 쿼리를 튜닝해서 부하를 낮춰야 한다.
- **계속 min에 붙어 있다**: 부하가 min을 못 채운다는 뜻. min을 더 낮춰 비용을 아낄 여지가 있다. 단, 캐시 미스·커넥션 한계를 같이 확인한다.
- **톱니처럼 자주 오르내린다**: 트래픽이 출렁이는 정상 패턴일 수 있지만, 스케일 다운으로 buffer pool이 비워졌다가 다시 채워지는 낭비가 반복되는 거라면 min을 약간 올려 진폭을 줄이는 게 나을 때가 있다.

### 9.2 ACUUtilization

`ServerlessDatabaseCapacity`를 현재 max ACU로 나눈 사용률(%)이다. 즉 "지금 천장 대비 얼마나 쓰고 있나"를 본다.

- 이 값이 100%에 자주 닿으면 max ACU가 부족한 것이다.
- 항상 낮게(예: 20% 밑) 깔려 있으면 max를 과하게 잡아둔 것이다. max 자체는 안 쓰면 과금되지 않지만, 너무 높게 잡으면 폭주 쿼리가 났을 때 ACU가 끝까지 치솟아 비용이 크게 튀는 사고로 이어질 수 있어서 적정선으로 내려두는 게 안전하다.

이 두 지표를 시간 지연 없이 잡으려면 `ACUUtilization`이 오래 90%를 넘거나 `ServerlessDatabaseCapacity`가 max에 장시간 붙는 순간을 알람으로 건다. 둘 다 "용량이 모자라기 시작했다"는 선행 신호라, CPU 100%가 찍히고 쿼리가 밀린 뒤에 알아채는 것보다 먼저 손쓸 수 있다. 알람 설정은 9.3에서 같이 다룬다.

함께 보면 좋은 지표는 provisioned와 동일하다. `DatabaseConnections`로 커넥션이 ACU 연동 `max_connections`에 근접하는지, `CPUUtilization`으로 ACU 대비 CPU가 포화인지, `FreeableMemory`로 ACU에 묶인 메모리가 빠듯한지를 같이 본다.

### 9.3 min/max 튜닝 실측 — 지표로 값을 정한다

min/max를 감으로 잡지 말고 `ServerlessDatabaseCapacity`의 분포를 뽑아서 정한다. 2주치 ACU를 1시간 단위로 받아 평균·최댓값을 보면 현재 설정이 맞는지 드러난다.

```bash
# 최근 14일 ACU 추이를 1시간(3600초) 단위로 평균·최대·p99 추출
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name ServerlessDatabaseCapacity \
  --dimensions Name=DBClusterIdentifier,Value=prod-aurora \
  --start-time "$(date -u -v-14d '+%Y-%m-%dT%H:%M:%SZ')" \
  --end-time   "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  --period 3600 \
  --statistics Average Maximum \
  --extended-statistics p99 \
  --query 'Datapoints[].[Timestamp,Average,Maximum]' \
  --output text | sort
```

실제로 겪은 튜닝 한 건을 정리하면 이렇다. 초기 설정이 min 2 / max 16이었는데 지표를 뽑아 보니:

| 구간 | ACU 평균 | ACU 최대 | 관찰 |
|------|----------|----------|------|
| 새벽 02~06시 | 2.0 | 2.0 | 계속 min에 붙어 있음. 부하가 min을 한참 못 채움 |
| 낮 피크 13~15시 | 7.5 | 16.0 | 가끔 max(16)에 닿아 `ACUUtilization` 100% 스파이크 |
| 그 외 | 4~5 | 9 | 정상 |

새벽이 상시 2.0에 붙어 있어 min을 1로 내렸다. 단, 1로 내리면 buffer pool이 2GiB로 줄어 새벽 첫 쿼리 캐시 미스가 늘 위험이 있어서, `Innodb_buffer_pool_reads`를 같이 보며 디스크 read가 튀지 않는 선까지만 내렸다. 결과적으로 새벽 idle 비용이 절반(2 ACU → 1 ACU)으로 줄었다.

낮 피크가 max에 닿는 건 `ACUUtilization` 100% 알람으로 확인됐는데, 이건 쿼리 한 개가 풀 스캔으로 ACU를 끌어올린 거라 max를 올리는 대신 인덱스를 추가해서 잡았다. 인덱스 추가 뒤 피크 평균 ACU가 7.5에서 5로 떨어졌고, max 16에 닿는 빈도가 사라졌다. **max를 올리는 게 답이 아니라 ACU를 끌어올리는 쿼리를 잡는 게 답인 경우가 많다.**

알람은 보통 `ACUUtilization`이 일정 시간 90% 이상 유지될 때, 그리고 `ServerlessDatabaseCapacity`가 max에 장시간 붙어 있을 때를 건다. 둘 다 "용량이 모자라기 시작했다"는 선행 신호다.

```bash
# ACUUtilization 90% 이상이 15분(3 × 5분) 지속되면 알람
aws cloudwatch put-metric-alarm \
  --alarm-name aurora-acu-saturation \
  --namespace AWS/RDS \
  --metric-name ACUUtilization \
  --dimensions Name=DBClusterIdentifier,Value=prod-aurora \
  --statistic Average --period 300 --evaluation-periods 3 \
  --threshold 90 --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:111122223333:db-alerts
```

---

## 10. 정리

Serverless v2는 완만하게 변하는 트래픽에서 비용을 트래픽에 맞춰 흘려보내는 구성이다. ACU가 메모리·CPU·커넥션을 한 번에 묶어 움직이므로, min을 너무 낮추면 캐시 미스와 커넥션 한계가 같이 따라오고, 초 단위 스파이크에는 ACU 증가가 부하를 못 쫓아간다. Lambda처럼 커넥션이 튀는 워크로드는 [DB_Proxy.md](DB_Proxy.md)를 끼고, writer를 안정적으로 두고 싶으면 provisioned writer + serverless reader 혼합으로 간다.

비용은 두 곳에서 어긋난다. 하나는 idle 바닥이다. v2는 조건이 안 맞으면 0으로 안 내려가고 min ACU에서 멈추므로, min × 24시간이 트래픽 0이어도 깔린다. 다른 하나는 상시 부하 역전이다. 24시간 평균 ACU가 동급 provisioned 손익분기를 꾸준히 넘으면 provisioned가 더 싸다. 가벼운 산발 쿼리는 Data API로 커넥션 문제를 피할 수 있지만 크기·세션·지연 제약이 있어 대량·트랜잭션 경로엔 안 맞는다. 운영 중에는 `ServerlessDatabaseCapacity`와 `ACUUtilization`을 시간축으로 뽑아 평균·피크를 보고 min/max를 조정하고, max에 자주 닿으면 천장을 올리기 전에 ACU를 끌어올리는 쿼리부터 잡는다.
