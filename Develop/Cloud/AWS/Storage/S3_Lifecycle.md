---
title: S3 라이프사이클
tags: [aws, devops, cloud]
updated: 2026-07-03
---

# S3 라이프사이클

## 라이프사이클이 필요한 이유

S3에 데이터를 쌓다 보면 오래된 객체가 계속 Standard에 남아 스토리지 요금을 갉아먹는다. 로그, 백업 덤프, 사용자 업로드 원본처럼 시간이 지나면 접근 빈도가 뚝 떨어지는 데이터가 대부분이다. 이런 객체를 사람이 손으로 삭제하거나 저렴한 클래스로 옮기는 건 불가능하다. 버킷에 수백만 개 객체가 있으면 스크립트로 돌려도 LIST/DELETE 요청 비용이 만만치 않다.

라이프사이클 정책은 버킷 단위로 "며칠 지난 객체를 어디로 옮기고 언제 지운다"는 규칙을 등록해두면 S3가 알아서 처리한다. 규칙 실행에는 별도 API 요청 비용이 붙지 않는다. 전환 요청 자체에 대한 요금(뒤에서 설명)은 있지만, LIST를 돌려 대상을 찾는 비용은 사라진다.

정책은 크게 두 종류의 액션으로 나뉜다.

- **Transition**: 객체를 다른 스토리지 클래스로 옮긴다. Standard → Standard-IA → Glacier 식으로 계단을 내려간다.
- **Expiration**: 객체를 삭제한다. 만료일이 지나면 S3가 지운다.

여기에 버전 관리 버킷을 위한 NoncurrentVersion 액션, 멀티파트 잔여물 정리, 삭제 마커 정리가 붙는다.

## 규칙 구조

라이프사이클 정책은 규칙(Rule)의 배열이다. 규칙 하나는 대략 이렇게 생겼다.

```json
{
  "Rules": [
    {
      "ID": "log-tiering",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "logs/"
      },
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 365
      }
    }
  ]
}
```

`logs/` 프리픽스 아래 객체를 만든 지 30일이 지나면 Standard-IA로, 90일이 지나면 Glacier로 옮기고, 365일이 지나면 삭제한다. `Days`는 객체 생성 시점 기준이다. 정책을 등록한 시점이 아니다. 이미 100일 지난 객체가 버킷에 있으면 정책 등록 직후 첫 실행에서 Glacier 전환 대상이 된다.

`Status`는 `Enabled` 또는 `Disabled`다. 규칙을 지우지 않고 잠시 꺼두려면 `Disabled`로 바꾼다.

`Days` 대신 `Date`로 절대 날짜를 지정할 수도 있다. 특정 날짜에 일괄 삭제해야 하는 경우 쓴다. 다만 `Date`는 한 번 지나면 이후 새로 들어오는 객체에도 계속 즉시 적용되므로, 반복 운영에는 `Days`가 맞다.

## 필터 - prefix, tag, 객체 크기

`Filter`로 규칙 적용 대상을 좁힌다.

프리픽스 하나만 걸 때는 위 예제처럼 `Prefix`를 쓴다. 버킷 전체에 적용하려면 `Filter`를 `{}`로 비워둔다.

태그로 거를 수도 있다. 특정 태그가 붙은 객체만 Glacier로 보내고 싶을 때다.

```json
"Filter": {
  "Tag": {
    "Key": "archive",
    "Value": "true"
  }
}
```

객체 크기 필터는 뒤에서 설명할 소용량 파일 전환 함정을 피할 때 중요하다. `ObjectSizeGreaterThan`과 `ObjectSizeLessThan`을 쓴다. 단위는 바이트다.

```json
"Filter": {
  "And": {
    "Prefix": "logs/",
    "ObjectSizeGreaterThan": 131072
  }
}
```

프리픽스와 크기, 태그 등 조건을 두 개 이상 조합하려면 `And` 안에 묶어야 한다. 조건 하나만 쓸 때는 `And` 없이 `Prefix`나 `Tag`를 바로 넣지만, 두 개 이상이면 반드시 `And`로 감싼다. 이걸 몰라서 JSON 검증에서 자주 막힌다.

## NoncurrentVersion - 버전 관리 버킷 정리

버전 관리를 켠 버킷은 객체를 덮어쓰거나 지워도 이전 버전이 그대로 남는다. 이걸 방치하면 겉으로 보이는 객체 수보다 실제 저장량이 몇 배로 불어난다. 콘솔에서 버킷 크기는 정상인데 요금만 계속 오르는 상황이 대부분 이 이전 버전(noncurrent version) 누적이다.

이전 버전에도 전환과 만료를 걸 수 있다.

```json
{
  "ID": "version-cleanup",
  "Status": "Enabled",
  "Filter": {},
  "NoncurrentVersionTransitions": [
    {
      "NoncurrentDays": 30,
      "StorageClass": "GLACIER"
    }
  ],
  "NoncurrentVersionExpiration": {
    "NoncurrentDays": 90,
    "NewerNoncurrentVersions": 5
  }
}
```

`NoncurrentDays`는 그 버전이 최신 버전 자리에서 밀려난(noncurrent가 된) 시점 기준이다. 객체 생성 시점이 아니다.

`NewerNoncurrentVersions`는 최근 몇 개 버전은 남긴다는 뜻이다. 위 설정은 이전 버전이 noncurrent 된 지 90일 지나면 지우되, 최신 것부터 5개는 보존한다. 롤백 여지를 남기면서 오래된 버전만 청소할 때 쓴다. 이 파라미터 없이 `NoncurrentDays`만 걸면 90일 지난 이전 버전이 전부 사라지므로, 잦은 덮어쓰기가 있는 버킷에서 최근 버전까지 날아갈 수 있다.

## AbortIncompleteMultipartUpload - 멀티파트 잔여물

멀티파트 업로드가 중간에 실패하거나 클라이언트가 끊기면 이미 올라간 파트가 버킷에 남는다. 이 파트는 LIST로 객체 목록에 안 잡힌다. `ListMultipartUploads`로 따로 조회해야 보인다. 그래서 버킷 크기와 실제 청구 용량이 안 맞는 또 다른 원인이 된다. 배치 업로드 파이프라인을 운영하다 보면 실패 케이스가 쌓여 수십 GB가 유령처럼 남아있는 경우가 있다.

정리 규칙은 짧다.

```json
{
  "ID": "abort-mpu",
  "Status": "Enabled",
  "Filter": {},
  "AbortIncompleteMultipartUpload": {
    "DaysAfterInitiation": 7
  }
}
```

업로드를 시작한 지 7일 지나도 완료(CompleteMultipartUpload)되지 않은 멀티파트 업로드를 정리한다. 어떤 버킷이든 하나 걸어두는 게 맞다. 값은 보통 7일이면 충분하고, 대용량 업로드가 며칠씩 걸리는 워크로드면 조금 늘린다.

## ExpiredObjectDeleteMarker - 삭제 마커 정리

버전 관리 버킷에서 객체를 삭제하면 실제로 지워지지 않고 삭제 마커(delete marker)가 최신 버전으로 붙는다. 이전 버전을 전부 만료시켜 지운 뒤에도, 남은 건 삭제 마커 하나뿐인 객체가 생긴다. 이 마커는 용량은 안 먹지만 개수가 쌓이면 LIST 성능과 관리에 거슬린다.

```json
{
  "ID": "clean-delete-markers",
  "Status": "Enabled",
  "Filter": {},
  "Expiration": {
    "ExpiredObjectDeleteMarker": true
  }
}
```

`ExpiredObjectDeleteMarker`는 아래 버전이 하나도 남지 않은 삭제 마커를 정리한다. 주의할 점은 이 옵션을 `NoncurrentVersionExpiration`과 같은 규칙에 넣되, `Expiration`의 `Days`와는 같은 규칙에서 함께 쓸 수 없다는 것이다. `ExpiredObjectDeleteMarker: true`와 `Days`(또는 `ExpiredObjectDeleteMarker` 없는 만료)를 한 규칙에 동시에 넣으면 검증 오류가 난다. 마커 정리는 별도 규칙으로 빼거나 NoncurrentVersion 만료와 묶는다.

## 전환 비용 함정 - 소용량 파일이 오히려 비싸진다

여기가 실무에서 가장 많이 데는 지점이다. Standard에서 IA나 Glacier로 옮기면 GB당 저장 단가는 분명히 내려간다. 그런데 전환 자체가 공짜가 아니다.

두 가지 비용이 붙는다.

**전환 요청 요금.** 객체 1건을 Glacier로 옮기는 데 요청 비용이 든다. Glacier Flexible/Deep Archive 전환은 1,000건당 요금이 IA 전환보다 훨씬 비싸다. 객체가 수백만 개면 이 전환 요청 요금만으로 몇 달치 저장 절감분이 날아간다.

**최소 스토리지 기간.** Standard-IA와 One Zone-IA는 최소 30일, Glacier 계열은 최소 90일(Deep Archive는 180일) 요금을 문다. 옮긴 지 얼마 안 돼 지우거나 다시 꺼내도 최소 기간만큼은 무조건 청구된다.

**최소 과금 용량.** IA 클래스는 객체 하나를 128KB로 간주해 요금을 매긴다. 실제 크기가 10KB여도 128KB 요금이다.

이걸 종합하면 작은 파일을 IA/Glacier로 옮기는 게 손해다. 예를 들어 평균 5KB짜리 로그 조각 수백만 개를 IA로 전환하면, 128KB 최소 과금 때문에 실제 저장 요금이 오히려 오르고 전환 요청 요금까지 더 나온다. Standard에 그냥 두는 게 쌌던 경우를 여러 번 봤다.

그래서 전환 규칙에는 객체 크기 하한을 거의 항상 건다. 앞의 필터 예제에서 `ObjectSizeGreaterThan: 131072`(128KB)를 넣은 게 이 이유다. 128KB보다 작은 객체는 전환 대상에서 빼서 Standard에 남긴다.

```json
{
  "ID": "large-object-tiering",
  "Status": "Enabled",
  "Filter": {
    "And": {
      "Prefix": "data/",
      "ObjectSizeGreaterThan": 131072
    }
  },
  "Transitions": [
    { "Days": 30, "StorageClass": "STANDARD_IA" },
    { "Days": 180, "StorageClass": "GLACIER" }
  ]
}
```

작은 객체가 많고 접근 패턴을 예측하기 어렵다면 라이프사이클 전환 대신 Intelligent-Tiering을 검토한다. Intelligent-Tiering은 128KB 미만 객체를 자동으로 자주-접근 계층에 두고 전환하지 않는다. 다만 객체당 모니터링 요금이 별도로 붙으니, 이것도 객체 수가 극단적으로 많으면 다시 계산해봐야 한다.

## 전환 순서 제약

전환에는 방향 제약이 있다. 스토리지 계층을 거꾸로(더 비싼 쪽으로) 라이프사이클로 올릴 수는 없다. Standard-IA에서 Standard로 되돌리는 전환 규칙은 만들 수 없다.

같은 규칙 안에서 Standard-IA로 갔다가 Glacier로 가는 건 되지만, 두 전환의 `Days` 간격이 최소 30일 이상이어야 하는 조합이 있다. Standard → Standard-IA(30일) → Glacier로 갈 때 IA 전환 후 곧바로 Glacier로 보내면 IA 최소 저장 기간 30일을 채우지 못해 규칙이 거부되거나 비용이 이상하게 나온다. 계단 간격은 넉넉히 둔다.

## 실행이 하루 단위로 지연된다

라이프사이클은 실시간이 아니다. S3가 하루에 한 번 UTC 자정 기준으로 규칙을 평가하고 비동기로 실행한다. `Days: 30`이라고 걸어도 정확히 30일째 0시에 옮겨지지 않는다. 조건 충족 후 실행까지 몇 시간, 길게는 하루 이상 걸릴 수 있다.

여기서 오해가 생긴다.

- 정책을 방금 등록하고 콘솔에서 객체 클래스를 확인하면 아직 Standard다. 정상이다. 다음 실행 주기를 기다려야 한다.
- 만료(Expiration) 규칙도 마찬가지다. `Days: 1`로 걸어도 등록 즉시 지워지지 않는다. 만료 대상으로 표시된 뒤 실제 삭제까지 시차가 있다. 다만 만료 대상이 된 객체는 삭제 전이라도 요금이 청구되지 않는다.
- 요금 청구 시점은 전환/만료 조건 충족일 기준이지 실제 처리 완료일 기준이 아니다. 그래서 요금은 정확히 30일째부터 IA 단가로 바뀌지만, 콘솔 객체 상태는 그보다 늦게 바뀐 것처럼 보인다.

테스트할 때 `Days: 1`로 걸고 몇 분 뒤 확인하면 아무 일도 안 일어나 규칙이 잘못됐다고 착각하기 쉽다. 하루 이상 기다려보고 판단해야 한다.

## put-bucket-lifecycle-configuration 실전

정책 등록은 CLI로 한다. 여러 규칙을 한 JSON 파일에 담아 통째로 올린다.

`lifecycle.json`:

```json
{
  "Rules": [
    {
      "ID": "log-tiering",
      "Status": "Enabled",
      "Filter": {
        "And": {
          "Prefix": "logs/",
          "ObjectSizeGreaterThan": 131072
        }
      },
      "Transitions": [
        { "Days": 30, "StorageClass": "STANDARD_IA" },
        { "Days": 90, "StorageClass": "GLACIER" }
      ],
      "Expiration": { "Days": 365 }
    },
    {
      "ID": "version-cleanup",
      "Status": "Enabled",
      "Filter": {},
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 90,
        "NewerNoncurrentVersions": 5
      }
    },
    {
      "ID": "abort-mpu",
      "Status": "Enabled",
      "Filter": {},
      "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
    }
  ]
}
```

등록:

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-bucket \
  --lifecycle-configuration file://lifecycle.json
```

확인:

```bash
aws s3api get-bucket-lifecycle-configuration --bucket my-bucket
```

여기서 반드시 알아야 할 점이 있다. `put-bucket-lifecycle-configuration`은 **전체 교체**다. 기존 규칙에 하나를 추가하는 게 아니라 버킷의 라이프사이클 설정을 통째로 덮어쓴다. 규칙 하나만 추가하려고 그 규칙 하나만 담긴 JSON을 올리면 기존 규칙이 전부 사라진다. 운영 버킷에서 이걸로 사고가 난다. 항상 `get`으로 현재 설정을 받아 편집한 뒤 전체를 다시 올린다.

```bash
# 현재 설정 백업 후 편집
aws s3api get-bucket-lifecycle-configuration --bucket my-bucket > current.json
# current.json에서 "Rules" 부분만 추출해 편집, 규칙 추가 후 put
```

`get` 결과에는 최상위에 `Rules` 외에 다른 필드가 붙어 나올 수 있으니, `put` 할 때는 `{ "Rules": [...] }` 형태로 맞춰야 한다.

삭제:

```bash
aws s3api delete-bucket-lifecycle --bucket my-bucket
```

## 자주 막히는 지점 정리

**`ID` 중복.** 규칙 배열 안에서 `ID`가 겹치면 등록이 거부된다. 규칙마다 고유한 이름을 준다.

**빈 `Filter`.** 버킷 전체 적용이라도 `Filter`를 아예 빼면 안 되는 조합이 있다. `"Filter": {}`로 명시한다.

**`And` 누락.** 필터 조건 두 개 이상은 `And`로 감싸야 한다. `Prefix`와 `ObjectSizeGreaterThan`을 `And` 없이 나란히 넣으면 검증 오류다.

**전환 대상 클래스 오타.** `STANDARD_IA`, `ONEZONE_IA`, `GLACIER`, `GLACIER_IR`(Instant Retrieval), `DEEP_ARCHIVE`가 정확한 값이다. `GLACIER`는 Flexible Retrieval을 가리킨다. 콘솔 표기와 API 값이 달라 헷갈린다.

**최소 기간 미충족 전환.** IA 전환 후 30일 안에 다시 Glacier로 보내는 규칙은 IA 최소 저장 기간 때문에 손해거나 거부된다. 계단 간격을 최소 저장 기간 이상으로 둔다.

## 관련 문서

전환 목적지인 Glacier 스토리지 클래스별 복구 방식과 요금은 [S3 Glacier](S3_Glacier.md) 문서를 본다. 멀티파트 업로드 자체의 동작과 파트 관리는 [S3 Multipart Upload](S3_Multipart_Upload.md)를 참고한다.
