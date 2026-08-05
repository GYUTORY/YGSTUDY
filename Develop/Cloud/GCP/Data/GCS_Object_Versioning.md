---
title: "GCS 객체 버전 관리"
tags: [GCP, Cloud Storage, GCS, versioning, lifecycle, soft-delete, terraform, Python SDK, Object Hold, Retention Policy]
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

### Terraform으로 버전 관리 설정

IaC로 버킷을 관리하는 환경이라면 Terraform에서 직접 버전 관리를 설정할 수 있다.

```hcl
resource "google_storage_bucket" "versioned_bucket" {
  name     = "my-bucket"
  location = "asia-northeast3"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      num_newer_versions = 3
      with_state         = "ARCHIVED"
    }
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
    condition {
      days_since_noncurrent_time = 7
      with_state                 = "ARCHIVED"
    }
  }
}
```

`with_state = "ARCHIVED"`는 noncurrent 버전에만 조건을 적용하는 설정이다. `LIVE`로 설정하면 current 버전에 적용되고, `ANY`면 모두 대상이 된다. 기존 JSON 라이프사이클 규칙의 `isLive: false`에 대응한다.

주의할 점은 Terraform으로 `lifecycle_rule`을 수정할 때 기존 규칙이 전부 교체된다는 것이다. 콘솔에서 수동으로 추가한 규칙이 있으면 Terraform 적용 시 사라진다. `terraform state`로 현재 상태를 먼저 확인하고 적용하는 습관이 필요하다.

## Python SDK

```python
from google.cloud import storage

client = storage.Client()
bucket = client.bucket("my-bucket")

# 버전 관리 활성화
bucket.versioning_enabled = True
bucket.patch()

# 모든 버전 조회
blobs = client.list_blobs(
    "my-bucket",
    prefix="path/to/file.txt",
    versions=True,
)
for blob in blobs:
    print(f"{blob.name} #{blob.generation} live={blob.is_live}")

# 특정 버전 복원 (noncurrent 버전을 current로 복사)
source = bucket.blob("path/to/file.txt", generation=1721100000000000)
bucket.copy_blob(source, bucket, "path/to/file.txt")

# 특정 버전 삭제
blob = bucket.blob("path/to/file.txt", generation=1721100000000000)
blob.delete()
```

`list_blobs`에 `versions=True`를 빠뜨리면 current 버전만 나온다. 삭제 마커 상태의 객체는 `is_live`가 `True`로 표시되면서 `size`가 0인 것으로 구분할 수 있다.

라이프사이클 규칙을 코드로 설정하는 경우:

```python
from google.cloud.storage import Blob

# noncurrent 버전 정리 라이프사이클 설정
bucket.add_lifecycle_delete_rule(
    number_of_newer_versions=3,
    is_live=False,
)
bucket.patch()
```

## Node.js SDK

```javascript
const { Storage } = require('@google-cloud/storage');

const storage = new Storage();
const bucket = storage.bucket('my-bucket');

// 버전 관리 활성화
await bucket.setMetadata({
  versioning: { enabled: true },
});

// 모든 버전 조회
const [files] = await bucket.getFiles({
  prefix: 'path/to/file.txt',
  versions: true,
});

files.forEach((file) => {
  console.log(
    `${file.name} #${file.metadata.generation} ` +
    `timeDeleted=${file.metadata.timeDeleted ?? 'live'}`
  );
});

// 특정 버전 복원
const source = bucket.file('path/to/file.txt', {
  generation: 1721100000000000,
});
await source.copy(bucket.file('path/to/file.txt'));

// 특정 버전 삭제
const file = bucket.file('path/to/file.txt', {
  generation: 1721100000000000,
});
await file.delete();
```

Node.js SDK에서는 삭제된 객체가 `metadata.timeDeleted` 필드가 있으면 삭제 마커 상태다. `size`가 0인 것으로도 구별할 수 있지만 `timeDeleted` 확인이 더 명확하다.

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

## 동시 쓰기와 generation 충돌

두 프로세스가 동시에 같은 객체를 업데이트하려고 할 때 버전 관리만으로는 덮어쓰기 충돌을 막지 못한다. 마지막에 쓴 쪽이 current가 되고 앞서 쓴 쪽은 noncurrent로 밀릴 뿐이다.

충돌을 감지하려면 `if_generation_match` precondition을 써야 한다. 현재 generation을 읽고, 그 generation이 바뀌지 않았을 때만 쓰기가 성공하는 방식이다. 낙관적 동시성 제어다.

```python
from google.cloud import storage
from google.api_core import exceptions

client = storage.Client()
bucket = client.bucket("my-bucket")
blob = bucket.blob("path/to/config.json")

# 현재 generation 확인
blob.reload()
current_generation = blob.generation

# 다른 프로세스가 먼저 쓰면 PreconditionFailed
try:
    blob.upload_from_string(
        b'{"key": "new_value"}',
        content_type="application/json",
        if_generation_match=current_generation,
    )
except exceptions.PreconditionFailed:
    # 이미 다른 쪽이 업데이트함
    # blob.reload()로 최신 버전을 다시 읽어 재시도
    pass
```

새로 만드는 객체라면 `if_generation_match=0`으로 설정한다. generation 0은 아직 존재하지 않는 상태를 의미해서, 같은 이름의 객체가 이미 있으면 업로드가 실패한다.

```python
# 객체가 존재하지 않을 때만 업로드
blob.upload_from_string(
    b"initial content",
    if_generation_match=0,
)
```

분산 환경에서 설정 파일이나 상태 파일을 GCS에 저장하는 경우, precondition 없이 쓰면 레이스 컨디션이 생긴다. 특히 여러 Cloud Functions 인스턴스가 동시에 같은 파일을 갱신하는 패턴에서 자주 문제가 된다.

## 서명된 URL과 특정 generation

특정 generation에 대한 서명된 URL을 발급하면 외부 사용자에게 특정 버전의 객체를 시간 제한으로 공유할 수 있다. 다운로드 링크가 항상 같은 버전을 가리켜야 하는 경우에 쓴다.

```bash
gcloud storage sign-url \
  "gs://my-bucket/path/to/file.txt#1721100000000000" \
  --duration=1h \
  --private-key-file=key.json \
  --service-account=sa@project.iam.gserviceaccount.com
```

Python SDK에서는 `generation`을 지정한 blob 객체로 서명하면 된다:

```python
import datetime
from google.cloud import storage

client = storage.Client()
bucket = client.bucket("my-bucket")

# 특정 generation의 blob 지정
blob = bucket.blob("path/to/file.txt", generation=1721100000000000)

url = blob.generate_signed_url(
    expiration=datetime.timedelta(hours=1),
    method="GET",
    version="v4",
)
print(url)
```

생성된 URL에는 generation 번호가 쿼리 파라미터로 포함된다. 이후 current 버전이 바뀌어도 URL이 가리키는 버전은 그대로 유지된다. 배포 아티팩트를 특정 버전으로 고정해 공유할 때 유용하다.

주의할 점은 noncurrent 버전에 서명된 URL을 발급하더라도 해당 버전을 삭제하면 URL이 404를 반환한다는 것이다. 라이프사이클 규칙이 해당 버전을 정리하기 전에 URL 유효 기간이 만료되도록 duration을 짧게 설정하는 편이 안전하다.

## 오브젝트 홀드와 버전 관리 상호작용

GCS 오브젝트 홀드는 두 종류가 있다: temporary hold와 event-based hold다. 둘 다 홀드가 걸린 동안은 해당 객체를 삭제하거나 덮어쓸 수 없다.

**temporary hold**

직접 해제하기 전까지 삭제와 교체가 막힌다.

```bash
# 홀드 설정
gcloud storage objects update gs://my-bucket/file.txt --temporary-hold

# 홀드 해제
gcloud storage objects update gs://my-bucket/file.txt --no-temporary-hold
```

버전 관리가 켜진 버킷에서 홀드가 걸린 객체는 generation을 지정해도 삭제가 안 된다. 403 에러가 난다. noncurrent 버전에도 홀드가 걸려 있으면 마찬가지다. 라이프사이클 규칙도 홀드 걸린 버전은 건너뛴다.

```bash
# 홀드가 걸린 noncurrent 버전 삭제 시도 → 403
gcloud storage rm gs://my-bucket/file.txt#1721100000000000
# ERROR: (gcloud.storage.rm) 403: Object is under temporary hold
```

**event-based hold**

버킷에 보존 정책이 설정된 경우, 이벤트 기반 홀드가 걸린 객체는 홀드가 해제된 시점부터 보존 기간을 계산하기 시작한다. 계약서나 감사 기록처럼 특정 이벤트(계약 종료, 감사 완료) 이후 일정 기간 보존해야 하는 객체에 쓴다.

```bash
# event-based hold 설정
gcloud storage objects update gs://my-bucket/contract.pdf --event-based-hold

# hold 해제 (이 시점부터 보존 기간 카운트 시작)
gcloud storage objects update gs://my-bucket/contract.pdf --no-event-based-hold
```

버전 관리와 함께 쓸 때 주의할 점은, 객체를 덮어쓰면 새 current 버전에는 홀드가 적용되지 않는다는 것이다. 홀드는 각 버전 단위로 관리된다. 이전 버전에만 홀드가 걸려 있어도 그 버전은 홀드가 해제되기 전까지 삭제할 수 없다.

## 보존 정책과 버전 관리 충돌

보존 정책(Retention Policy)은 버킷 수준에서 설정하며, 설정된 기간 내에는 어떤 버전도 삭제할 수 없다.

```bash
# 365일 보존 정책 설정
gcloud storage buckets update gs://my-bucket \
  --retention-period=365d

# 보존 정책 잠금 (한 번 잠그면 해제 불가)
gcloud storage buckets update gs://my-bucket \
  --lock-retention-policy
```

버전 관리와 보존 정책을 함께 쓰면 여러 가지 충돌 상황이 생긴다.

**라이프사이클 규칙이 보존 기간을 지키지 못하는 경우**

`numNewerVersions: 3`으로 설정했는데 보존 기간이 365일이라면, 최신 버전이 4개 이상 쌓여도 가장 오래된 버전의 보존 기간이 끝나지 않으면 삭제가 일어나지 않는다. 라이프사이클 규칙이 조건을 만족해도 보존 기간이 우선이다. 규칙이 조용히 무시되는 것처럼 보여서 처음에는 라이프사이클 설정이 잘못된 줄 안다.

**보존 기간 내 버전 삭제 시도**

```bash
gcloud storage rm gs://my-bucket/file.txt#1721100000000000
# ERROR: 403 Object 'my-bucket/file.txt' is subject to a retention policy
# and cannot be deleted until 2027-07-26T00:00:00Z
```

에러 메시지에 삭제 가능 시점이 포함되어 나온다.

**보존 기간과 noncurrent 버전 관계**

보존 정책은 noncurrent 버전에도 그대로 적용된다. current가 바뀌어 noncurrent로 밀린 버전도 원래 생성 시점부터 보존 기간이 끝나기 전까지는 지울 수 없다. 하루에 수십 번 업데이트되는 파일에 1년 보존 정책을 걸면, 그 파일의 모든 버전이 1년 동안 쌓인다. 비용이 어마어마하게 나온다.

Python SDK에서 보존 기간을 확인하는 방법:

```python
from google.cloud import storage

client = storage.Client()
blob = client.bucket("my-bucket").blob("file.txt")
blob.reload()

if blob.retention_expiration_time:
    print(f"삭제 가능 시점: {blob.retention_expiration_time}")
```

보존 정책이 잠금 상태(locked)가 아니라면 기간을 늘릴 수는 있지만 줄일 수는 없다. 잠금 후에는 버킷 자체를 삭제하지 않는 이상 정책을 없앨 수 없다. 컴플라이언스 목적으로 잠금하는 경우가 많지만, 운영 편의 목적으로 잠그는 것은 피해야 한다.

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

두 조건을 함께 걸면 OR 조건이 아니라 각각 별도의 규칙으로 동작한다. 두 규칙 중 하나라도 해당되면 삭제된다.

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

7일이 지난 noncurrent 버전을 Coldline으로 내리면 저장 비용이 줄고, 실제로 복원이 필요한 경우에는 여전히 접근할 수 있다. Coldline 최소 저장 기간(90일)이 있어서 이후 다시 삭제할 때 조기 삭제 요금이 붙을 수 있다는 점은 고려해야 한다.

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
