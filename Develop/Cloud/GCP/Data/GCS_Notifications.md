---
title: "GCS 이벤트 알림"
tags: [gcp, event-driven, cloud]
updated: 2026-07-26
---

# GCS 이벤트 알림

GCS 버킷에서 객체가 생성되거나 삭제될 때 외부 시스템에 알림을 보낼 수 있다. 방법이 두 가지다. 하나는 Pub/Sub 토픽으로 직접 메시지를 발행하는 방식이고, 다른 하나는 Eventarc를 거쳐 Cloud Run이나 Cloud Functions를 트리거하는 방식이다. 구조가 비슷해 보이지만 목적이 다르다. Pub/Sub은 여러 소비자가 같은 이벤트를 처리해야 할 때 쓰고, Eventarc는 이벤트 하나당 컨테이너 하나를 바로 실행시킬 때 쓴다.

## Pub/Sub 알림 설정

버킷에 알림을 연결하려면 먼저 Pub/Sub 토픽이 있어야 한다.

```bash
# 토픽 생성
gcloud pubsub topics create gcs-events

# 버킷에 알림 연결
gcloud storage buckets notifications create gs://my-bucket \
  --topic=projects/my-project/topics/gcs-events \
  --event-types=OBJECT_FINALIZE,OBJECT_DELETE \
  --object-prefix=images/ \
  --payload-format=JSON_API_V1

# 현재 설정된 알림 목록 확인
gcloud storage buckets notifications list gs://my-bucket
```

`--event-types`를 지정하지 않으면 모든 이벤트가 발행된다. 필요 없는 이벤트까지 토픽으로 넘어오면 소비자 쪽에서 필터링 로직이 늘어나기 때문에 처음부터 좁혀두는 게 낫다.

`--object-prefix`는 특정 경로 하위 객체만 알림을 발생시키고 싶을 때 쓴다. `images/`로 설정하면 `images/` 로 시작하는 객체에 대해서만 이벤트가 나간다. 버킷 전체를 감시하면 불필요한 이벤트가 많아져서 Pub/Sub 비용과 처리 부하가 올라간다.

알림 설정을 삭제할 때는:

```bash
# 알림 ID 확인
gcloud storage buckets notifications list gs://my-bucket

# 특정 알림 삭제
gcloud storage buckets notifications delete gs://my-bucket \
  --notification=1
```

## 이벤트 타입

GCS가 발행하는 이벤트는 네 가지다.

| 이벤트 | 발생 시점 |
|--------|----------|
| `OBJECT_FINALIZE` | 객체 업로드 완료, 기존 객체 덮어쓰기 |
| `OBJECT_DELETE` | 객체 삭제, 버전 관리 버킷에서 noncurrent 버전 삭제 |
| `OBJECT_ARCHIVE` | 버전 관리 버킷에서 객체가 noncurrent로 바뀔 때 |
| `OBJECT_METADATA_UPDATE` | 메타데이터만 변경될 때 |

`OBJECT_FINALIZE`가 가장 많이 쓰인다. 파일 업로드 완료 시점에 처리를 트리거할 때는 이걸 쓴다. 주의할 점은 기존 객체를 덮어쓸 때도 `OBJECT_FINALIZE`가 발생한다는 것이다. 처리 로직에서 새 업로드와 덮어쓰기를 구분해야 한다면 페이로드의 `generation`과 `metageneration`을 보면 된다.

`OBJECT_METADATA_UPDATE`는 `gsutil setmeta`나 API로 Content-Type 같은 메타데이터만 수정해도 발생한다. 이 이벤트를 구독하는 파이프라인이 있다면 예상치 못한 트리거가 생길 수 있다.

## Pub/Sub 메시지 페이로드

`--payload-format=JSON_API_V1`로 설정하면 메시지 본문에 객체 정보가 담긴다.

```json
{
  "kind": "storage#object",
  "id": "my-bucket/images/photo.jpg/1721234567890000",
  "name": "images/photo.webp",
  "bucket": "my-bucket",
  "generation": "1721234567890000",
  "metageneration": "1",
  "contentType": "image/jpeg",
  "size": "1234567",
  "updated": "2024-07-17T12:34:56.789Z",
  "storageClass": "STANDARD"
}
```

Pub/Sub 메시지 자체에는 `attributes`도 붙는다. 이벤트 타입 구분은 페이로드 본문보다 `attributes`에서 꺼내는 게 더 간단하다.

```json
{
  "eventType": "OBJECT_FINALIZE",
  "bucketId": "my-bucket",
  "objectId": "images/photo.webp",
  "objectGeneration": "1721234567890000",
  "payloadFormat": "JSON_API_V1"
}
```

`--payload-format=NONE`으로 설정하면 메시지 본문 없이 `attributes`만 전달된다. 객체 내용이나 메타데이터가 필요 없고 이벤트 발생 사실만 감지하면 되는 경우에 쓴다. 메시지 크기가 작아서 처리량이 높은 버킷에 유리하다.

## Eventarc 연동

Eventarc는 GCS 이벤트를 Cloud Run이나 Cloud Functions에 직접 라우팅한다. Pub/Sub 구독 설정을 별도로 만들 필요 없이 트리거 하나로 연결된다.

```bash
# Cloud Run 서비스 트리거 생성
gcloud eventarc triggers create thumbnail-trigger \
  --location=asia-northeast3 \
  --destination-run-service=thumbnail-service \
  --destination-run-region=asia-northeast3 \
  --event-filters="type=google.cloud.storage.object.v1.finalized" \
  --event-filters="bucket=my-image-bucket" \
  --service-account=eventarc-sa@my-project.iam.gserviceaccount.com
```

`--event-filters`에서 `type` 값은 Eventarc 이벤트 타입 형식을 쓴다. Pub/Sub 알림에서 쓰는 `OBJECT_FINALIZE`와 다르다.

| Pub/Sub 이벤트 타입 | Eventarc 이벤트 타입 |
|---------------------|---------------------|
| `OBJECT_FINALIZE` | `google.cloud.storage.object.v1.finalized` |
| `OBJECT_DELETE` | `google.cloud.storage.object.v1.deleted` |
| `OBJECT_ARCHIVE` | `google.cloud.storage.object.v1.archived` |
| `OBJECT_METADATA_UPDATE` | `google.cloud.storage.object.v1.metadataUpdated` |

Eventarc가 Cloud Run을 호출할 때는 HTTP POST 요청으로 CloudEvents 형식의 페이로드를 전달한다. Cloud Run 핸들러에서 이를 파싱한다.

```python
import functions_framework
from cloudevents.http import from_http
import json

@functions_framework.http
def handle_gcs_event(request):
    event = from_http(request.headers, request.data)
    
    data = event.data
    bucket_name = data.get("bucket")
    object_name = data.get("name")
    content_type = data.get("contentType", "")
    
    if not content_type.startswith("image/"):
        return "skip", 200
    
    # 썸네일 생성 처리
    process_image(bucket_name, object_name)
    return "ok", 200
```

Eventarc 트리거에 사용하는 서비스 계정에는 `roles/run.invoker`가 필요하다. 이 권한이 없으면 Cloud Run 호출이 403으로 실패한다. 처음 설정할 때 트리거가 만들어져도 이벤트가 안 들어오는 원인 1순위가 이것이다.

## Cloud Functions Gen2 연동

Cloud Functions 2세대는 내부적으로 Cloud Run 위에서 동작하기 때문에 Eventarc 트리거를 쓴다.

```bash
gcloud functions deploy thumbnail-generator \
  --gen2 \
  --runtime=python311 \
  --region=asia-northeast3 \
  --trigger-event-filters="type=google.cloud.storage.object.v1.finalized" \
  --trigger-event-filters="bucket=my-image-bucket" \
  --entry-point=generate_thumbnail \
  --service-account=functions-sa@my-project.iam.gserviceaccount.com
```

1세대 Cloud Functions는 `--trigger-resource`와 `--trigger-event`로 설정했지만, 2세대는 Eventarc 필터 방식으로 바뀌었다. 1세대 문서와 혼용하면 배포가 실패한다.

## 이미지 업로드 → 썸네일 생성 파이프라인

실무에서 자주 구현하는 패턴이다. 사용자가 이미지를 업로드하면 자동으로 썸네일을 생성해서 별도 경로에 저장하는 구조다.

```
Client → GCS(images/) → OBJECT_FINALIZE → Cloud Run → GCS(thumbnails/)
```

Cloud Run 코드 예시:

```python
import os
import io
from PIL import Image
from google.cloud import storage

storage_client = storage.Client()

def generate_thumbnail(bucket_name: str, object_name: str) -> None:
    if not object_name.startswith("images/"):
        return
    
    # 파일명만 추출
    filename = object_name.split("/")[-1]
    thumbnail_path = f"thumbnails/{filename}"
    
    bucket = storage_client.bucket(bucket_name)
    source_blob = bucket.blob(object_name)
    
    image_data = source_blob.download_as_bytes()
    image = Image.open(io.BytesIO(image_data))
    
    image.thumbnail((300, 300), Image.LANCZOS)
    
    output = io.BytesIO()
    image.save(output, format=image.format or "JPEG", quality=85)
    output.seek(0)
    
    dest_blob = bucket.blob(thumbnail_path)
    dest_blob.upload_from_file(
        output,
        content_type=source_blob.content_type
    )
```

이 구조에서 주의해야 할 점이 있다. 썸네일 결과물을 같은 버킷의 `thumbnails/` 경로에 저장하면, 그 업로드도 `OBJECT_FINALIZE`를 발생시킨다. `thumbnails/`로 시작하는 객체는 처리를 건너뛰도록 코드에서 걸러내야 한다. 안 그러면 썸네일 저장 → 이벤트 발생 → 썸네일 재처리 → 이벤트 발생 루프가 생긴다.

처리할 수 있는 파일 형식을 명시적으로 제한하는 것도 중요하다. 누군가 `.pdf`나 `.csv`를 업로드했을 때 PIL이 예외를 뱉으면서 함수가 실패하고, Pub/Sub 재시도나 Eventarc 재전달이 반복된다.

```python
SUPPORTED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

def handle_gcs_event(request):
    event = from_http(request.headers, request.data)
    data = event.data
    
    content_type = data.get("contentType", "")
    if content_type not in SUPPORTED_CONTENT_TYPES:
        return "unsupported content type", 200  # 200으로 ack
    
    generate_thumbnail(data["bucket"], data["name"])
    return "ok", 200
```

처리하지 않을 이벤트에 대해 200을 반환하는 게 맞다. 4xx나 5xx를 반환하면 Eventarc가 재시도 대상으로 판단해서 같은 이벤트를 계속 보낸다.

## 알림 지연

GCS 알림은 보통 수 초 이내에 도달하지만, 실제로는 편차가 있다. 부하가 높은 시간대나 리전 간 복제가 걸린 버킷에서는 수십 초까지 늦어지는 경우가 있다.

실시간 처리가 필요한 경우라면 알림 도착까지 몇 초의 여유를 두는 게 현실적이다. 예를 들어 업로드 완료 후 즉시 썸네일이 응답으로 내려가야 하는 API라면, GCS 알림 기반 비동기 처리는 맞지 않는다. 그 경우에는 업로드 완료 후 클라이언트가 직접 썸네일 생성 API를 호출하는 방식이 낫다.

Pub/Sub의 경우 메시지가 토픽에 발행된 이후 구독자가 받기까지도 지연이 생길 수 있다. `ackDeadline` 내에 처리를 못 하면 재전달이 발생한다. 기본 `ackDeadline`은 10초인데, 이미지 처리처럼 작업 시간이 길다면 늘려야 한다.

```bash
# 구독 생성 시 ackDeadline 설정
gcloud pubsub subscriptions create gcs-events-sub \
  --topic=gcs-events \
  --ack-deadline=60 \
  --message-retention-duration=7d
```

## 중복 수신 처리

Pub/Sub은 at-least-once 전달을 보장한다. 한 번만 처리되는 게 아니라 최소 한 번 이상 전달된다. 같은 이벤트가 두 번 이상 들어오는 상황을 반드시 처리해야 한다.

중복을 처리하는 방법은 멱등(idempotent) 처리다. 같은 입력에 대해 몇 번을 실행해도 결과가 같게 만드는 것이다.

썸네일 파이프라인에서 멱등성을 확보하는 방식:

```python
def generate_thumbnail(bucket_name: str, object_name: str) -> None:
    filename = object_name.split("/")[-1]
    thumbnail_path = f"thumbnails/{filename}"
    
    bucket = storage_client.bucket(bucket_name)
    
    # 이미 썸네일이 있으면 건너뜀
    thumbnail_blob = bucket.blob(thumbnail_path)
    if thumbnail_blob.exists():
        return
    
    source_blob = bucket.blob(object_name)
    # ... 썸네일 생성 로직
```

단순 존재 여부 확인은 완벽하지 않다. 두 처리가 동시에 실행되면 둘 다 썸네일이 없다고 판단하고 동시에 생성에 들어간다. 엄밀한 중복 방지가 필요하다면 Firestore나 Redis에 처리 상태를 기록하는 방식을 쓴다.

```python
from google.cloud import firestore

db = firestore.Client()

def generate_thumbnail(bucket_name: str, object_name: str, generation: str) -> None:
    # 처리 이력 조회
    doc_id = f"{bucket_name}_{object_name}_{generation}".replace("/", "_")
    doc_ref = db.collection("processed_events").document(doc_id)
    
    doc = doc_ref.get()
    if doc.exists:
        return  # 이미 처리됨
    
    # 처리 시작 마킹
    doc_ref.set({"status": "processing", "started_at": firestore.SERVER_TIMESTAMP})
    
    try:
        # ... 썸네일 생성 로직
        doc_ref.update({"status": "done", "completed_at": firestore.SERVER_TIMESTAMP})
    except Exception as e:
        doc_ref.update({"status": "failed", "error": str(e)})
        raise
```

`generation` 값을 포함해서 문서 ID를 만드는 게 핵심이다. 같은 파일을 덮어써도 `generation`이 다르므로 별도의 처리 건으로 취급된다. `generation` 없이 파일명만으로 만들면 파일을 교체했을 때 새 버전의 썸네일이 생성되지 않는다.

Eventarc 기반 Cloud Run은 Pub/Sub보다 재시도 정책이 단순하다. 기본 설정에서는 재시도를 비활성화할 수도 있고, 재시도 횟수와 최소 백오프를 설정할 수 있다.

```bash
gcloud eventarc triggers update thumbnail-trigger \
  --location=asia-northeast3 \
  --event-filters="type=google.cloud.storage.object.v1.finalized" \
  --event-filters="bucket=my-image-bucket"
```

Cloud Run이 500을 반환하면 Eventarc가 지수 백오프로 재시도한다. 처리가 실패했을 때 4xx와 5xx를 구분하는 게 중요하다. 4xx는 재시도해도 같은 결과가 나오는 오류(잘못된 파일 형식 등)이므로 재시도를 유도하면 안 된다. 5xx는 일시적 오류(외부 서비스 타임아웃 등)라서 재시도로 해결될 수 있다.

## 알림 수신 확인

설정이 제대로 됐는지 확인할 때 쓰는 방법이다.

```bash
# 구독 만들고 메시지 직접 당겨보기
gcloud pubsub subscriptions create test-sub \
  --topic=gcs-events

# 테스트 파일 업로드
gcloud storage cp test.webp gs://my-image-bucket/images/test.webp

# 메시지 확인 (최대 5개, 5초 대기)
gcloud pubsub subscriptions pull test-sub \
  --limit=5 \
  --auto-ack

# 확인 후 구독 삭제
gcloud pubsub subscriptions delete test-sub
```

메시지가 안 들어온다면 확인해야 할 것이 두 가지다. 하나는 GCS 서비스 계정에 Pub/Sub 발행 권한이 있는지다. `gcloud storage buckets notifications create` 명령 자체는 성공해도 이벤트가 발행되지 않는 경우가 있다. `roles/pubsub.publisher`가 GCS 서비스 계정(`service-PROJECT_NUMBER@gs-project-accounts.iam.gserviceaccount.com`)에 부여돼 있어야 한다.

```bash
# GCS 서비스 계정 확인
gcloud storage service-agent --project=my-project

# Pub/Sub 발행 권한 부여
gcloud pubsub topics add-iam-policy-binding gcs-events \
  --member="serviceAccount:service-123456@gs-project-accounts.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher"
```

다른 하나는 `--event-types`나 `--object-prefix` 필터가 의도한 대로 맞춰져 있는지다. prefix 설정이 대소문자를 구분하기 때문에 `Images/`와 `images/`는 다른 경로로 취급된다.
