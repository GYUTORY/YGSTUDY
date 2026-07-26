---
title: "GCS 객체 버전 관리"
tags: [GCP, Cloud Storage, GCS, Versioning, Lifecycle, Soft Delete]
updated: 2026-07-26
---

# GCS 객체 버전 관리

GCS 버킷에 버전 관리를 켜면 객체를 덮어쓰거나 삭제해도 이전 버전이 보존된다. 데이터를 실수로 날렸을 때 복원 수단이 된다. 대신 비용이 조용히 불어나는 구조라 활성화할 때는 라이프사이클 규칙을 함께 설계해야 한다.

## 버전 활성화

버킷 단위로 켠다. 기존 버킷에 사후 적용도 된다.

```bash
# 버전 관리 활성화
gcloud storage buckets update gs://my-bucket --versioning

# 활성화 확인
gcloud storage buckets describe gs://my-bucket --format="value(versioning)"
```

gsutil을 쓰는 환경이라면:

```bash
gsutil versioning set on gs://my-bucket
gsutil versioning get gs://my-bucket
```

버전 관리가 켜진 버킷에 같은 이름의 객체를 다시 올리면, 기존 객체는 **noncurrent** 상태로 바뀌고 새 객체가 **current** 상태가 된다. 객체를 삭제하면 실제로 지워지지 않고 **삭제 마커(delete marker)**가 current 버전으로 올라간다. 이 마커 때문에 `ls`를 해도 보이지 않지만, 내부적으로는 남아 있다.

## 버전별 조회

일반 `ls` 명령으로는 current 버전만 보인다. 전체 버전을 보려면 `-a` 플래그가 필요하다.

```bash
# 모든 버전 조회 (generation 포함)
gcloud storage ls --all-versions gs://my-bucket/path/to/file.txt

# 출력 예시
# gs://my-bucket/path/to/file.txt#1721234567890000  (current)
# gs://my-bucket/path/to/file.txt#1721100000000000  (noncurrent)
# gs://my-bucket/path/to/file.txt#1720900000000000  (noncurrent)
```

`#` 뒤에 붙는 숫자가 **generation** 번호다. 버전을 특정할 때 이 번호를 쓴다. 숫자는 마이크로초 단위 타임스탬프 기반이라 시간 순으로 정렬된다.

gsutil 기준:

```bash
gsutil ls -a gs://my-bucket/path/to/file.txt
```

객체 상세 정보를 확인할 때:

```bash
gcloud storage objects describe gs://my-bucket/path/to/file.txt#1721100000000000
```

## 버전 복원

이전 버전을 되살리는 방법은 두 가지다.

**방법 1: 특정 버전을 복사해서 current로 만들기**

```bash
gcloud storage cp \
  gs://my-bucket/path/to/file.txt#1721100000000000 \
  gs://my-bucket/path/to/file.txt
```

복사하면 해당 버전의 내용이 새 current 버전으로 올라간다. 기존 current는 noncurrent로 밀린다. 삭제된 상태라면 삭제 마커 위로 새 버전이 생성되면서 파일이 복구된다.

**방법 2: 삭제 마커 제거**

삭제 마커의 generation을 직접 삭제하면 그 아래 noncurrent 버전이 다시 current로 올라온다.

```bash
# 삭제 마커 generation 확인
gcloud storage ls --all-versions gs://my-bucket/path/to/file.txt

# 삭제 마커 삭제 (generation 번호 지정)
gcloud storage rm gs://my-bucket/path/to/file.txt#1721300000000000
```

이 방법은 직전 버전으로 돌아가는 경우에 간단하다. 여러 버전 이전으로 돌아가야 한다면 방법 1이 명확하다.

## 특정 버전 삭제

```bash
# generation 지정해서 특정 버전만 삭제
gcloud storage rm gs://my-bucket/path/to/file.txt#1721100000000000

# 특정 객체의 noncurrent 버전 전체 삭제 (current는 유지)
gsutil rm -a gs://my-bucket/path/to/file.txt
```

주의할 점은 generation을 지정하지 않고 그냥 `rm`을 날리면 current 버전에 삭제 마커를 씌울 뿐이라는 것이다. 실제로 스토리지에서 객체가 사라지지 않는다.

버전 관리가 켜진 버킷에서 객체를 완전히 제거하려면 noncurrent 버전을 하나씩 지우고 마지막으로 current 버전(또는 삭제 마커)까지 generation을 지정해 삭제해야 한다.

## 스토리지 비용 문제

버전 관리를 켜두면 비용이 조용히 누적된다. noncurrent 버전도 current와 동일한 스토리지 단가가 붙기 때문이다. Standard 클래스 버킷에 1GB짜리 파일을 매일 업로드하면 한 달 후에는 약 30GB 분량의 버전이 쌓인다. 자주 교체되는 파일이나 용량이 큰 파일이 있는 버킷이라면 비용 폭탄을 맞을 수 있다.

실제로 문제가 되는 패턴은 CI/CD 파이프라인에서 아티팩트를 동일한 경로에 매번 덮어쓰는 경우다. 하루에 수십 번 빌드가 돌면 noncurrent 버전이 기하급수적으로 쌓인다. 버전 관리를 켰다는 사실을 잊고 있다가 다음 달 청구서에서 처음 알게 되는 경우가 꽤 있다.

GCS 콘솔에서 버킷 단위로 사용량을 볼 때 current 버전과 noncurrent 버전의 용량이 따로 표시되지 않아 처음에는 파악하기 어렵다. Cloud Monitoring에서 `storage.googleapis.com/storage/object_count` 메트릭에 `is_live` 레이블로 필터링하거나, BigQuery로 스토리지 사용 로그를 내보내서 분석하는 게 정확하다.

## noncurrentVersions 라이프사이클 규칙

noncurrent 버전을 자동으로 정리하는 규칙이다. current가 아닌 버전에만 적용된다는 점이 일반 `age` 조건과 다르다.

```json
{
  "lifecycle": {
    "rule": [
      {
        "action": { "type": "Delete" },
        "condition": {
          "numNewerVersions": 3,
          "isLive": false
        }
      },
      {
        "action": { "type": "Delete" },
        "condition": {
          "daysSinceNoncurrentTime": 30,
          "isLive": false
        }
      }
    ]
  }
}
```

`numNewerVersions: 3`은 더 최신 버전이 3개 이상 존재하면 해당 noncurrent 버전을 삭제한다는 뜻이다. 최근 3개 버전만 유지하고 싶을 때 쓴다.

`daysSinceNoncurrentTime: 30`은 noncurrent 상태가 된 지 30일이 넘으면 삭제한다. 날짜 기준으로 관리할 때 쓴다.

두 조건을 함께 걸면 OR 조건이 아니라 각각 별도의 규칙으로 동작한다. 즉, 두 규칙 중 하나라도 해당되면 삭제된다.

실제로 적용할 때는 JSON을 파일로 저장해서 버킷에 적용한다:

```bash
# lifecycle.json 파일 작성 후
gcloud storage buckets update gs://my-bucket \
  --lifecycle-file=lifecycle.json

# 현재 적용된 규칙 확인
gcloud storage buckets describe gs://my-bucket \
  --format="value(lifecycle)"
```

규칙이 적용된 직후에 바로 삭제가 일어나지는 않는다. GCS가 내부적으로 라이프사이클 규칙을 평가하는 주기가 있고, 최대 24~48시간 정도 지연이 생길 수 있다. 스크립트로 즉각 정리가 필요한 경우라면 라이프사이클 규칙 대신 직접 삭제 명령을 쓰는 편이 낫다.

noncurrent 버전만 Coldline으로 내리는 것도 가능하다. 복원 가능성을 남기되 비용을 줄이는 방식이다:

```json
{
  "action": { "type": "SetStorageClass", "storageClass": "COLDLINE" },
  "condition": {
    "daysSinceNoncurrentTime": 7,
    "isLive": false
  }
}
```

7일이 지난 noncurrent 버전을 Coldline으로 내리면 저장 비용이 줄어들고, 실제로 복원이 필요한 경우에는 여전히 접근할 수 있다. Coldline 최소 저장 기간(90일)이 있어서 이후 다시 삭제할 때 조기 삭제 요금이 붙을 수 있다는 점은 고려해야 한다.

## 소프트 삭제와 버전 관리의 차이

2024년부터 GCS에 **소프트 삭제(Soft Delete)** 기능이 추가됐다. 기존 버전 관리와 목적이 비슷해 보이지만 동작 방식이 다르다.

| | 객체 버전 관리 | 소프트 삭제 |
|--|--|--|
| 적용 대상 | 버전 관리가 켜진 버킷 | 모든 버킷 (기본 활성화) |
| 보존 대상 | noncurrent 버전 객체 | 삭제된 객체 (버킷 포함) |
| 보존 기간 | 라이프사이클 규칙으로 조정 | 7일 기본, 최대 90일 설정 가능 |
| 복원 방법 | generation 지정해서 cp | `restore` 명령 |
| 비용 | 저장 비용 동일하게 부과 | 삭제 기간 동안 저장 비용 부과 |

소프트 삭제는 버전 관리가 꺼진 버킷에서도 동작한다는 점이 핵심 차이다. 버킷 자체를 실수로 삭제한 경우에도 소프트 삭제 기간 내라면 복구할 수 있다. 버전 관리는 버킷이 삭제되면 함께 사라진다.

소프트 삭제로 복원하는 명령:

```bash
# 소프트 삭제된 객체 목록 조회
gcloud storage ls --soft-deleted gs://my-bucket/

# 소프트 삭제된 객체 복원
gcloud storage restore gs://my-bucket/path/to/file.txt

# 소프트 삭제된 버킷 복원
gcloud storage restore gs://my-bucket
```

소프트 삭제도 비용이 붙는다. 삭제한 객체가 보존 기간 동안 유지되면서 저장 비용이 나온다. 버전 관리가 켜진 버킷에서 소프트 삭제까지 활성화되어 있으면 삭제된 noncurrent 버전이 소프트 삭제 보존 기간 동안 추가로 보관될 수 있다. 두 기능을 함께 쓸 때는 이중으로 비용이 발생한다는 점을 감안해야 한다.

소프트 삭제 보존 기간을 줄이거나 끄는 방법:

```bash
# 보존 기간을 0으로 설정하면 소프트 삭제 비활성화
gcloud storage buckets update gs://my-bucket \
  --soft-delete-duration=0

# 보존 기간 7일로 설정
gcloud storage buckets update gs://my-bucket \
  --soft-delete-duration=7d
```

버전 관리를 쓰는 버킷이라면 소프트 삭제의 추가 보호 효과는 크지 않다. noncurrent 버전이 이미 복원 수단이 되기 때문이다. 비용 최적화 관점에서 버전 관리 버킷에는 소프트 삭제 기간을 줄이는 경우가 많다.
