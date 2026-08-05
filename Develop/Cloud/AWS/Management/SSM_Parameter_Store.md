---
title: SSM Parameter Store
tags: [aws, ssm, parameter-store, secrets, kms, configuration, iam]
updated: 2026-06-21
---

# SSM Parameter Store

설정값과 비밀값을 한 군데 모아두고 애플리케이션이 런타임에 읽어가게 하는 서비스다. RDS 엔드포인트, API 키, 외부 서비스 토큰처럼 환경마다 달라지는 값을 코드나 `.env` 파일에 박지 않고 여기에 넣는다. 이름이 `SSM`(Systems Manager) 하위 기능이라 처음 보면 Run Command나 Session Manager 같은 것들과 묶여 있어 헷갈리는데, Parameter Store는 그 안에서 독립적으로 쓰이는 키-값 저장소다.

비슷한 일을 하는 Secrets Manager가 따로 있어서 둘을 두고 매번 고민하게 된다. 결론부터 말하면 자동 로테이션이 꼭 필요한 게 아니면 Parameter Store로 충분하고, 비용도 0원이다. 선택 기준은 아래에서 따로 정리한다.

---

## Standard와 Advanced 파라미터

파라미터를 만들 때 티어를 고른다. 처음 시작하면 Standard로 충분하지만 한도를 넘기는 순간 Advanced로 올려야 한다.

| 구분 | Standard | Advanced |
|------|----------|----------|
| 값 크기 | 4KB | 8KB |
| 계정·리전당 개수 | 10,000개 | 100,000개 |
| 파라미터 정책(만료, 변경 알림) | 불가 | 가능 |
| 비용 | 무료 | 파라미터당 월 $0.05 + API 호출 과금 |
| 처리량(higher throughput) | 옵션으로 켜야 함 | 기본 포함 |

Standard는 무료지만 한 계정 한 리전에서 10,000개를 넘으면 더 못 만든다. 마이크로서비스가 늘고 환경(dev/staging/prod)이 갈리면서 파라미터가 의외로 빨리 쌓인다. 서비스 30개 × 환경 3개 × 파라미터 20개면 벌써 1,800개다. 10,000개에 닿기 전에 경로 설계를 잘 해두는 게 낫다.

값 크기 4KB는 짧아 보여도 인증서 PEM 전체를 넣으려다 막히는 경우가 있다. 인증서나 큰 JSON 설정은 8KB Advanced로도 모자랄 수 있으니 그런 건 S3에 두고 경로만 파라미터에 넣는 식으로 우회한다.

티어는 한 번 Advanced로 올리면 Standard로 못 내린다(값 크기가 4KB를 넘었을 수 있으니 당연하다). 그래서 처음부터 다 Advanced로 만드는 사람도 있는데, 파라미터당 월 $0.05가 개수 늘면 무시 못 한다. 필요한 것만 올린다.

`Intelligent-Tiering`이라는 설정이 있어서, 값이 4KB를 넘거나 정책을 붙이는 순간 자동으로 Advanced로 승격시켜준다. 어느 게 Advanced여야 하는지 일일이 신경 쓰기 싫으면 이걸 켜둔다.

```bash
# 계정·리전 기본 티어를 Intelligent-Tiering으로
aws ssm update-service-setting \
  --setting-id /ssm/parameter-store/default-parameter-tier \
  --setting-value Intelligent-Tiering
```

---

## 파라미터 타입 — String, StringList, SecureString

타입은 세 가지다.

- `String` — 평문 문자열 하나. 엔드포인트, 포트, 피처 플래그 같은 안 민감한 값.
- `StringList` — 콤마로 구분된 문자열 목록. `a.example.com,b.example.com` 처럼 저장하면 읽을 때 리스트로 다룰 수 있다. 단 값 자체에 콤마가 들어가면 깨지니 주의한다.
- `SecureString` — KMS로 암호화해서 저장하는 값. 비밀번호, API 키, 토큰은 전부 이걸 쓴다.

```bash
# 평문
aws ssm put-parameter \
  --name "/app/prod/db/host" \
  --value "prod-db.cluster-xxxx.ap-northeast-2.rds.amazonaws.com" \
  --type String

# 리스트
aws ssm put-parameter \
  --name "/app/prod/allowed-origins" \
  --value "https://app.example.com,https://admin.example.com" \
  --type StringList

# 암호화 (KMS 기본 키 aws/ssm 사용)
aws ssm put-parameter \
  --name "/app/prod/db/password" \
  --value "S3cr3t-P@ss" \
  --type SecureString
```

SecureString을 만들면 KMS 키로 값을 암호화한다. `--key-id`를 안 주면 계정 기본 키인 `alias/aws/ssm`을 쓴다. 기본 키는 무료지만 키 정책을 내가 못 건드린다. 크로스 계정 접근이나 키 단위 권한 분리가 필요하면 고객 관리형 키(CMK)를 만들어서 지정한다.

```bash
aws ssm put-parameter \
  --name "/app/prod/payment/api-key" \
  --value "sk_live_xxxx" \
  --type SecureString \
  --key-id "alias/app-prod-secrets"
```

읽을 때 SecureString은 기본적으로 암호문 그대로 나온다. 복호화하려면 `--with-decryption`을 붙여야 하고, 그러면 호출자 IAM이 해당 KMS 키에 `kms:Decrypt` 권한을 가지고 있어야 한다. 권한이 없으면 파라미터는 읽히는데 값이 안 풀리는 상황이 생긴다. SecureString을 못 읽겠다고 할 때 십중팔구 KMS 권한 문제다.

```bash
aws ssm get-parameter \
  --name "/app/prod/db/password" \
  --with-decryption \
  --query "Parameter.Value" --output text
```

---

## 계층 경로 설계

파라미터 이름은 `/`로 구분하는 경로 형태로 짓는다. 단순히 보기 좋으라고 하는 게 아니라, 경로가 IAM 권한 분리와 일괄 조회의 단위가 되기 때문에 처음부터 신중히 정한다.

자주 쓰는 형태는 `/{app}/{env}/{group}/{key}`다.

```
/app/prod/db/host
/app/prod/db/password
/app/prod/redis/host
/app/staging/db/host
/payment/prod/stripe/secret-key
```

이렇게 두면 `GetParametersByPath`로 prefix 하나를 통째로 읽을 수 있다. 애플리케이션이 부팅할 때 `/app/prod/`만 재귀로 긁어오면 그 환경 설정이 전부 들어온다.

```bash
aws ssm get-parameters-by-path \
  --path "/app/prod/" \
  --recursive \
  --with-decryption
```

경로 설계에서 실수하는 부분이 환경 위치다. `/db/prod/...` 처럼 env를 안쪽에 두면 "prod 환경 전체"를 IAM으로 묶기가 어려워진다. env를 앞쪽 레벨에 두면 `/app/prod/*` 한 줄로 prod 권한을 통제할 수 있다. 환경 격리가 권한의 첫 번째 경계이므로 env를 app 바로 다음에 두는 편이 관리하기 편하다.

이름은 만든 뒤 못 바꾼다. 바꾸려면 새로 만들고 지워야 하는데 그러면 버전 이력이 끊긴다. 경로 규칙은 팀에서 합의하고 시작한다.

---

## Secrets Manager와의 선택 기준

둘 다 비밀값을 암호화해서 저장하고 IAM·KMS로 보호한다. 갈리는 지점은 명확하다.

| 항목 | Parameter Store (SecureString) | Secrets Manager |
|------|-------------------------------|-----------------|
| 비용 | Standard 무료 | 비밀당 월 $0.40 + API 호출 과금 |
| 자동 로테이션 | 없음 (직접 구현) | Lambda 기반 내장 |
| RDS/Redshift 통합 로테이션 | 없음 | 기본 제공 |
| 크로스 리전 복제 | 없음 (직접 복사) | 기본 제공 |
| 값 크기 | 4KB / 8KB | 64KB |

정리하면, **자동 로테이션이 필요 없고 비용을 아끼려면 Parameter Store**다. RDS 자격증명을 주기적으로 자동 교체해야 한다거나, 로테이션 Lambda를 직접 짜기 싫으면 Secrets Manager를 쓴다.

비밀 100개를 Secrets Manager에 두면 월 $40이지만 Parameter Store SecureString이면 0원이다(KMS 기본 키 사용 시). 스타트업 초기엔 이 차이가 크다. 그래서 로테이션이 강제되는 DB 비밀번호만 Secrets Manager에 두고 나머지 API 키·설정은 Parameter Store에 두는 식으로 섞어 쓰는 경우가 많다.

서비스별 본질적 차이와 KMS와의 관계는 [Secrets Manager vs KMS](../Security/Secrets_Manager_vs_KMS.md)와 [Secrets Manager](../Security/Secrets_Manager.md)에 더 자세히 정리해뒀다.

---

## ECS Task Definition에 주입

ECS에서 컨테이너 환경변수로 파라미터를 넣을 때 `secrets` 필드를 쓴다. `environment`에 값을 직접 박으면 Task Definition JSON에 평문이 남아 콘솔에서 다 보인다. `secrets`로 넣으면 ECS가 태스크 시작 시점에 Parameter Store에서 값을 읽어 컨테이너 환경변수로 꽂아준다. SecureString은 자동으로 복호화된다.

```json
{
  "containerDefinitions": [
    {
      "name": "api",
      "secrets": [
        {
          "name": "DB_PASSWORD",
          "valueFrom": "arn:aws:ssm:ap-northeast-2:123456789012:parameter/app/prod/db/password"
        },
        {
          "name": "DB_HOST",
          "valueFrom": "/app/prod/db/host"
        }
      ]
    }
  ]
}
```

`valueFrom`은 전체 ARN이나 파라미터 이름 둘 다 받는다. 여기서 두 가지 IAM 권한이 필요하다. 태스크 실행 역할(`executionRole`)에 `ssm:GetParameters`가 있어야 하고, SecureString이면 KMS `kms:Decrypt`도 있어야 한다. 둘 중 하나라도 빠지면 태스크가 `ResourceInitializationError`로 죽는다. 컨테이너 로그도 안 남고 태스크가 바로 멈추니 처음엔 원인 찾기가 까다롭다. 이 에러를 보면 실행 역할 권한부터 확인한다.

ECS 비밀 주입의 세부 동작은 [ECS Secrets 관리](../Containers/ECS_Secrets_관리.md)에 더 있다.

---

## Lambda에서 읽기

Lambda는 ECS 같은 `secrets` 주입 필드가 없어서 코드에서 직접 SDK로 읽거나, Lambda Extension(AWS Parameters and Secrets Lambda Extension)을 붙여 로컬 캐시 엔드포인트로 읽는다.

SDK로 직접 읽는 기본 형태:

```javascript
import { SSMClient, GetParametersCommand } from "@aws-sdk/client-ssm";

const ssm = new SSMClient({});

// 핸들러 바깥에서 한 번만 읽어 캐시 (콜드 스타트 1회만 호출)
let cachedConfig;

async function loadConfig() {
  if (cachedConfig) return cachedConfig;

  const res = await ssm.send(new GetParametersCommand({
    Names: [
      "/app/prod/db/host",
      "/app/prod/db/password",
    ],
    WithDecryption: true,
  }));

  cachedConfig = Object.fromEntries(
    res.Parameters.map(p => [p.Name, p.Value])
  );
  return cachedConfig;
}

export const handler = async (event) => {
  const config = await loadConfig();
  // config["/app/prod/db/password"] 사용
};
```

핸들러 안에서 매번 `GetParameters`를 호출하면 호출량이 폭발한다. 트래픽 많은 Lambda면 throttling에 걸린다. 핸들러 바깥(모듈 스코프)에서 한 번 읽어 변수에 담아두면 같은 실행 환경이 살아있는 동안 재사용된다. 다만 이러면 파라미터를 바꿔도 기존 실행 환경은 옛 값을 계속 쓴다. 값이 자주 바뀐다면 TTL을 둬서 일정 시간마다 다시 읽는다.

Lambda Extension을 쓰면 익스텐션이 파라미터를 캐시하고 `http://localhost:2773`로 로컬 HTTP 엔드포인트를 열어준다. 코드에서 SDK 대신 이 로컬 주소로 요청하면 캐시된 값을 받는다. 캐시 TTL은 환경변수로 조절한다.

---

## 버전 관리와 라벨

`put-parameter`로 같은 이름에 값을 덮어쓰면(`--overwrite`) 새 버전이 생긴다. 버전은 1부터 정수로 올라가고 이전 값이 남는다. 잘못 바꿨을 때 되돌릴 수 있다.

```bash
# 버전 지정 조회
aws ssm get-parameter --name "/app/prod/db/password:3"

# 버전 이력 보기
aws ssm get-parameter-history --name "/app/prod/db/password"
```

문제는 버전 번호가 배포할 때마다 바뀐다는 거다. "지금 prod가 쓰는 버전"을 코드에서 숫자로 박을 수 없다. 그래서 라벨을 붙인다. 라벨은 특정 버전을 가리키는 별칭이라, 검증 끝난 버전에 `production`이라는 라벨을 달아두고 애플리케이션은 항상 `이름:production`을 읽게 한다.

```bash
# 5번 버전에 production 라벨 달기
aws ssm label-parameter-version \
  --name "/app/prod/db/password" \
  --parameter-version 5 \
  --labels production

# 라벨로 조회
aws ssm get-parameter \
  --name "/app/prod/db/password:production" \
  --with-decryption
```

새 값을 넣고 검증한 뒤 라벨만 옮기면 애플리케이션 코드 변경 없이 전환되고, 문제가 생기면 라벨을 이전 버전으로 다시 옮겨 즉시 롤백한다. 라벨 하나는 동시에 한 버전만 가리키므로 옮기면 자동으로 이전 버전에서 떨어진다.

---

## Throttling과 캐싱

기본 throughput 한도가 낮다. `GetParameters`는 기본 40 TPS다. 인스턴스 100대가 부팅하면서 동시에 파라미터를 긁으면 `ThrottlingException`이 터진다. 오토스케일링으로 한꺼번에 뜰 때 자주 겪는다.

대응은 세 가지다.

첫째, 매 요청마다 읽지 말고 애플리케이션 기동 시 한 번 읽어 메모리에 캐시한다. 설정값은 요청마다 바뀌지 않으니 부팅 때 `GetParametersByPath`로 한 번에 받아 들고 있는다. `GetParameters`는 한 번에 최대 10개까지 받으니 개수가 많으면 경로 조회를 쓴다.

둘째, throughput 한도를 올린다. Advanced 파라미터이거나 Standard에서 higher throughput 옵션을 켜면 호출 한도가 올라간다. 다만 이건 호출 건당 과금이 붙으니 캐싱으로 먼저 줄이고 그래도 모자라면 켠다.

```bash
aws ssm update-service-setting \
  --setting-id /ssm/parameter-store/high-throughput-enabled \
  --setting-value true
```

셋째, SDK 호출에 지수 백오프 재시도를 둔다. AWS SDK 기본 재시도가 어느 정도 막아주지만, 동시 부팅이 몰리면 기본값으로 부족할 수 있어 재시도 횟수를 늘리거나 기동 시점을 살짝 흩뿌린다(jitter).

순간 폭주가 아니라 평상시 읽기량 자체가 많다면 설계가 잘못된 거다. Parameter Store는 자주 읽는 캐시가 아니라 가끔 읽는 설정 저장소로 본다.

---

## IAM 경로 기반 권한 분리

경로를 잘 설계하는 진짜 이유가 여기 있다. IAM 정책의 리소스 ARN에 와일드카드를 쓰면 경로 단위로 권한을 끊을 수 있다.

prod 서비스 역할이 prod 파라미터만 읽게 하는 정책:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ssm:GetParameters", "ssm:GetParametersByPath"],
      "Resource": "arn:aws:ssm:ap-northeast-2:123456789012:parameter/app/prod/*"
    },
    {
      "Effect": "Allow",
      "Action": ["kms:Decrypt"],
      "Resource": "arn:aws:kms:ap-northeast-2:123456789012:key/xxxx-key-id"
    }
  ]
}
```

이러면 prod 역할은 staging 파라미터(`/app/staging/*`)를 못 읽는다. 환경을 경로 앞쪽에 둔 설계가 여기서 값을 한다. env가 경로 안쪽에 있으면 이런 와일드카드 분리가 안 된다.

주의할 점이 ARN 경로 표기다. 파라미터 이름이 `/app/prod/db/host`면 ARN은 `parameter/app/prod/db/host`로 슬래시가 하나로 이어진다. `parameter//app...`처럼 슬래시를 두 개 쓰면 매칭이 안 돼서 권한이 안 먹는다. 권한이 분명히 맞는데 AccessDenied가 나면 이 슬래시부터 확인한다.

SecureString을 읽는 역할이면 KMS `kms:Decrypt`를 빼먹지 않는다. 앞서 말했듯 SSM 권한만 있고 KMS 권한이 없으면 파라미터는 읽히는데 복호화에서 막힌다. 두 권한은 항상 짝으로 본다.

`GetParametersByPath` 권한을 줄 때는 해당 경로뿐 아니라 그 prefix 자체에 대한 권한이 필요하니, `/app/prod/*`처럼 별표를 붙여 하위 전체를 포함시킨다.

---

## 정리

설정과 비밀값은 Parameter Store에 모으고, 안 민감한 값은 String, 비밀값은 SecureString으로 둔다. 경로는 `/{app}/{env}/{group}/{key}` 형태로 env를 앞쪽에 두어 IAM과 일괄 조회의 경계로 삼는다. 자동 로테이션이 필요하면 그 비밀만 Secrets Manager로 보내고 나머지는 Parameter Store에 둬서 비용을 0원으로 유지한다. 읽기는 기동 시 한 번 캐시해서 40 TPS throttling을 피하고, 배포 전환은 라벨로 처리해 롤백을 빠르게 한다.
