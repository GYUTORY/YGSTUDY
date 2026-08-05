---
title: "Cloud Storage (GCS)"
tags: [GCP, Cloud Storage, GCS, Object Storage, gsutil, Signed URL]
updated: 2026-07-03
---

# Cloud Storage (GCS)

Google Cloud의 오브젝트 스토리지다. AWS를 먼저 다뤄본 사람이라면 S3와 거의 같은 개념으로 봐도 된다. 파일 하나가 오브젝트, 오브젝트를 담는 그릇이 버킷이고, 폴더처럼 보이는 경로는 사실 오브젝트 키 안에 슬래시가 들어간 것뿐이다. 실제 디렉토리 구조는 없다.

파일 시스템이 아니라는 점을 처음에 자주 잊는다. `gs://my-bucket/logs/2026/07/app.log` 같은 경로에서 `logs/`, `2026/` 같은 중간 폴더는 실제로 존재하는 객체가 아니다. 콘솔에서 폴더처럼 보이는 건 접두어(prefix)를 UI가 폴더로 그려주는 것이다. 그래서 빈 폴더라는 게 없고, 그 안의 객체를 다 지우면 폴더도 같이 사라진다.

## 스토리지 클래스

버킷과 객체마다 스토리지 클래스를 지정한다. 클래스는 저장 단가와 접근 비용의 트레이드오프다. 자주 읽으면 저장 단가가 싼 게 손해고, 거의 안 읽으면 저장 단가가 싼 게 이득이다.

| 클래스 | 최소 저장 기간 | 성격 | 실제 용도 |
|--------|--------------|------|----------|
| Standard | 없음 | 저장 단가 높고 접근 비용 없음 | 웹 서비스 정적 파일, 자주 읽는 데이터 |
| Nearline | 30일 | 월 1회 정도 접근 | 월간 백업, 로그 아카이브 |
| Coldline | 90일 | 분기 1회 정도 접근 | 분기 백업, 재해 복구용 |
| Archive | 365일 | 연 1회 이하 접근 | 법적 보관, 장기 규정 준수 데이터 |

숫자로 감을 잡자면, Standard 저장 단가를 1이라 할 때 Archive는 대략 1/7 수준이다. 대신 Archive에서 데이터를 꺼내면 조회(retrieval) 비용이 GB당 별도로 붙는다. 클래스가 차가울수록 저장은 싸지고 조회는 비싸진다.

여기서 실무에서 자주 당하는 게 **최소 저장 기간**이다. Nearline에 올린 객체를 5일 만에 지우거나 다른 클래스로 바꾸면, 남은 25일치 저장료를 조기 삭제 요금으로 청구한다. Archive에 올렸다가 한 달 만에 지우면 남은 11개월치가 그대로 나온다. 라이프사이클 규칙을 잘못 짜서 갓 Coldline으로 내려간 객체를 다시 삭제하도록 만들면 요금이 이상하게 튀는데, 대부분 이 조기 삭제 요금이 원인이다.

클래스는 객체 단위로도 다를 수 있다. 버킷 기본 클래스가 Standard여도 개별 객체를 Coldline으로 올리거나 라이프사이클로 내릴 수 있다. 버킷 클래스는 "새로 올라오는 객체의 기본값"이지 버킷 안 전체를 고정하는 값이 아니다.

## 라이프사이클 규칙

객체를 시간에 따라 자동으로 클래스 변경하거나 삭제하는 규칙이다. 로그나 백업처럼 시간이 지나면 가치가 떨어지는 데이터에 건다.

규칙은 조건(condition)과 동작(action)으로 구성된다. 조건은 나이(age), 생성 시각, 현재 클래스, 버전 여부 등이고, 동작은 `Delete` 또는 `SetStorageClass`다.

```json
{
  "lifecycle": {
    "rule": [
      {
        "action": { "type": "SetStorageClass", "storageClass": "NEARLINE" },
        "condition": { "age": 30, "matchesStorageClass": ["STANDARD"] }
      },
      {
        "action": { "type": "SetStorageClass", "storageClass": "COLDLINE" },
        "condition": { "age": 90, "matchesStorageClass": ["NEARLINE"] }
      },
      {
        "action": { "type": "Delete" },
        "condition": { "age": 365 }
      }
    ]
  }
}
```

이 규칙을 파일로 저장하고 적용한다.

```bash
gcloud storage buckets update gs://my-bucket --lifecycle-file=lifecycle.json
```

주의할 점 몇 가지가 있다.

라이프사이클은 실시간이 아니다. 하루 한 번 정도 배치로 도는데, `age: 30` 조건이 정확히 30일 0시에 실행되지 않는다. 하루 이틀 정도 늦게 처리되는 경우가 흔하다. 정밀한 만료 시각이 필요한 데이터에 라이프사이클 삭제를 믿으면 안 된다.

`age`는 객체 생성 시각 기준이다. 클래스를 바꿔도 age는 리셋되지 않는다. Standard로 30일 지나 Nearline이 된 객체는 여전히 생성 후 30일이 지난 상태고, 90일 조건이 되려면 60일을 더 기다린다.

조건이 여러 개면 AND로 묶인다. 한 규칙 안에 `age: 30`과 `matchesStorageClass: ["STANDARD"]`를 같이 쓰면 둘 다 만족해야 동작한다. OR로 걸고 싶으면 규칙을 따로 나눠야 한다.

`SetStorageClass`로 더 차가운 클래스에 내렸다가 다시 위로 올리는 규칙은 만들지 않는 게 좋다. 클래스 변경도 최소 저장 기간 대상이라 조기 삭제 요금이 붙을 수 있다.

## 균일한 버킷 수준 액세스

GCS 권한 모델은 두 가지가 공존한다. IAM(버킷·프로젝트 단위 정책)과 ACL(객체 하나하나에 붙는 접근 목록)이다. 이 둘이 동시에 켜져 있으면 권한 계산이 복잡해지고, "분명 IAM으로 막았는데 특정 객체만 공개돼 있더라" 같은 사고가 난다. 옛날 객체에 붙은 ACL을 아무도 기억 못 하는 경우다.

이걸 막는 게 **균일한 버킷 수준 액세스**(Uniform Bucket-Level Access, UBLA)다. 켜면 객체 ACL을 완전히 무시하고 IAM만으로 권한을 판단한다. 신규 버킷은 이 옵션을 켜고 시작하는 걸 기본으로 두는 게 낫다.

```bash
# 버킷 생성 시 UBLA 활성화
gcloud storage buckets create gs://my-bucket \
  --location=asia-northeast3 \
  --uniform-bucket-level-access

# 기존 버킷에 활성화
gcloud storage buckets update gs://my-bucket --uniform-bucket-level-access
```

한 가지 걸리는 부분: UBLA를 켜면 객체별 ACL로 하던 "이 파일 하나만 공개" 같은 세밀한 공개 설정을 못 한다. 특정 객체를 외부에 공유해야 하면 ACL 대신 서명된 URL을 쓴다.

UBLA를 켠 지 90일이 지나면 되돌릴 수 없다. 90일 안이면 끌 수 있으니, 켜고 나서 ACL 기반 로직이 깨지는지 초반에 확인해야 한다.

## 서명된 URL

버킷을 비공개로 두고도 특정 객체를 일정 시간 동안만 접근하게 하는 방법이다. URL에 서명(signature)과 만료 시각을 붙여서, 그 URL을 가진 사람은 GCP 계정 없이도 만료 전까지 객체를 읽거나 쓸 수 있다.

전형적인 용도는 이렇다. 서비스 백엔드가 비공개 버킷의 이미지에 대한 서명된 URL을 만들어서 프론트에 내려주면, 브라우저가 그 URL로 이미지를 직접 받는다. 파일 트래픽이 백엔드를 거치지 않는다. 사용자 업로드도 마찬가지로, 업로드용 서명된 URL(PUT)을 발급하면 클라이언트가 버킷에 직접 올린다.

```bash
gcloud storage sign-url gs://my-bucket/private/report.pdf \
  --duration=15m \
  --private-key-file=service-account-key.json
```

서비스 계정 키가 필요하다는 게 서명된 URL의 핵심이자 골칫거리다. 서명은 서비스 계정의 개인 키로 만든다. 애플리케이션 코드에서 발급할 때는 보통 SDK가 이 과정을 처리하는데, 실행 환경의 서비스 계정에 `iam.serviceAccountTokenCreator` 권한이 있어야 키 파일 없이도 IAM 기반으로 서명할 수 있다.

```java
// Java 예: 15분짜리 읽기 서명 URL 생성
Storage storage = StorageOptions.getDefaultInstance().getService();
BlobInfo blobInfo = BlobInfo.newBuilder(
        BlobId.of("my-bucket", "private/report.pdf")).build();

URL signedUrl = storage.signUrl(
        blobInfo,
        15, TimeUnit.MINUTES,
        Storage.SignUrlOption.withV4Signature());

System.out.println(signedUrl);
```

실무에서 겪는 문제 두 가지.

만료 시간을 길게 잡으면 URL이 유출됐을 때 그 시간 내내 열려 있다. 15분~1시간 정도가 무난하고, 하루 이상은 되도록 피한다. 링크를 로그에 남기거나 캐시에 저장하면 그게 곧 유출 경로가 된다.

서버 시각이 어긋나면 서명이 깨진다. V4 서명은 요청 시각을 포함해서 검증하는데, 발급 서버의 시계가 실제 시각과 몇 분 이상 벌어져 있으면 만료 전인데도 `SignatureDoesNotMatch`가 뜬다. 컨테이너 환경에서 NTP 동기화가 안 된 노드를 만나면 이 증상이 나온다.

## gsutil과 gcloud storage

CLI가 두 개다. 예전부터 쓰던 `gsutil`과 새로 밀고 있는 `gcloud storage`다. 문서나 스택오버플로에는 `gsutil`이 아직 많은데, 신규 작업은 `gcloud storage`로 하는 걸 권한다. 대용량 전송 속도가 더 빠르고 명령 체계가 gcloud와 일관된다.

```bash
# 업로드/다운로드
gcloud storage cp ./local.txt gs://my-bucket/path/
gcloud storage cp gs://my-bucket/path/remote.txt ./

# 디렉토리 재귀 복사
gcloud storage cp -r ./dist gs://my-bucket/static/

# 동기화 (양쪽 diff만 전송, S3의 aws s3 sync 같은 것)
gcloud storage rsync -r ./build gs://my-bucket/site/

# 목록
gcloud storage ls gs://my-bucket/logs/

# 삭제
gcloud storage rm gs://my-bucket/path/old.txt
gcloud storage rm -r gs://my-bucket/tmp/
```

`gsutil`을 계속 쓴다면 명령이 조금 다르다. `gsutil cp`, `gsutil rsync`, `gsutil ls`처럼 접두어만 바꾼 형태라 옮겨 쓰기 어렵지 않다.

`rsync`에서 조심할 게 있다. `--delete-unmatched-destination-objects`(gsutil의 `-d`) 옵션을 붙이면 소스에 없는 대상 객체를 지운다. 소스 경로를 잘못 넣은 상태로 이 옵션을 쓰면 버킷을 통째로 비운다. CI 배포 스크립트에 무심코 넣었다가 사고 나는 대표 케이스다. 지우는 옵션은 넣기 전에 `--dry-run`으로 뭐가 지워지는지 먼저 본다.

## 버킷 이름 전역 유일성

버킷 이름은 GCP 전체에서 유일해야 한다. 내 프로젝트 안이 아니라 전 세계 모든 GCP 사용자를 통틀어 유일하다. `data`, `backup`, `images` 같은 이름은 이미 다 누가 쓰고 있어서 못 만든다.

```bash
gcloud storage buckets create gs://data
# ERROR: The requested bucket name is not available.
```

그래서 회사·프로젝트 접두어를 붙이는 규칙을 정해두는 게 낫다. `mycompany-prod-user-uploads`, `ygstudy-staging-logs` 같은 식이다. 이름에 프로젝트 ID나 도메인을 넣으면 충돌을 거의 피한다.

이름 규칙에서 걸리는 지점 몇 개.

이름에 회사 내부 정보를 그대로 넣으면 안 된다. 버킷 이름은 URL과 DNS에 노출된다. `acme-secret-project-x` 같은 이름은 그 자체로 정보 유출이다.

이름은 나중에 못 바꾼다. 바꾸려면 새 버킷을 만들어 데이터를 통째로 옮겨야 한다. 그래서 처음 정할 때 명명 규칙을 확정하고 시작한다.

점(`.`)이 들어간 이름은 도메인 소유권 검증을 요구한다. `assets.example.com` 같은 버킷을 만들려면 Search Console로 그 도메인 소유를 증명해야 한다. 일반 버킷에는 점을 안 쓰는 게 편하다.

## 대용량 업로드와 병렬 컴포짓 업로드

수 GB짜리 파일 하나를 올릴 때, 한 스트림으로 순차 전송하면 네트워크를 다 못 쓴다. 이때 파일을 여러 조각으로 쪼개 병렬로 올리고 서버에서 합치는 방식이 병렬 컴포짓 업로드(parallel composite upload)다. 큰 파일 업로드 속도가 확 올라간다.

```bash
# 150MiB 넘는 파일은 32개 조각으로 쪼개 병렬 업로드
gcloud storage cp big-dump.tar.gz gs://my-bucket/ \
  --content-type=application/gzip
```

`gcloud storage`는 조건이 맞으면 자동으로 병렬 컴포짓 업로드를 시도한다. 설정으로 임계값과 조각 수를 조정한다.

```bash
gcloud config set storage/parallel_composite_upload_enabled True
gcloud config set storage/parallel_composite_upload_threshold 150M
```

속도는 좋은데, 여기에 함정이 하나 있다. 병렬 컴포짓 업로드로 만든 객체는 **CRC32C 체크섬만 있고 MD5 해시가 없다.** 조각들을 서버에서 합쳐서(compose) 만든 객체라 전체 MD5를 계산하지 않기 때문이다.

이게 왜 문제냐면, 다운로드하는 쪽이나 다른 시스템이 MD5로 무결성을 검증하도록 짜여 있으면 검증 자체가 안 된다. `gcloud storage cp`로 받을 때 MD5 검증을 기대하는 도구는 해시가 없다고 경고하거나 실패한다. 다른 클라우드나 온프레미스로 이 파일을 옮기면서 MD5를 대조하는 파이프라인이면 거기서 막힌다.

그래서 병렬 컴포짓 업로드는 이런 경우에 끈다.

- 받는 쪽이 MD5 무결성 검증을 요구할 때
- 업로드 대상 버킷·객체 클래스에서 compose가 제약될 때
- 조각으로 쪼갠 임시 객체가 라이프사이클 규칙에 걸려 애매하게 처리될 우려가 있을 때

끄는 법.

```bash
gcloud config set storage/parallel_composite_upload_enabled False
# 또는 명령 단위로
gcloud storage cp big.tar.gz gs://my-bucket/ \
  --no-parallel-composite-upload
```

한 가지 더. 병렬 컴포짓 업로드는 조각 객체를 잠깐 만들었다가 합친 뒤 지운다. 업로드가 중간에 끊기면 이 조각 객체가 버킷에 남는 경우가 있다. `gcloud storage ls`로 봤을 때 낯선 임시 객체가 쌓여 있으면 이게 원인일 수 있으니, 실패한 대용량 업로드 후에는 잔여 조각이 남았는지 확인한다.

## 정리

GCS를 처음 붙일 때 실무에서 자주 부딪히는 지점만 추리면 이렇다. 버킷 이름은 전역 유일이라 접두어 규칙부터 정하고, 신규 버킷은 UBLA를 켜서 ACL 관리를 없애고, 특정 객체 공유는 서명된 URL로 처리한다. 라이프사이클은 배치로 늦게 도는 걸 감안하고, 최소 저장 기간 때문에 클래스를 성급하게 내리면 조기 삭제 요금을 문다. 대용량 업로드는 병렬 컴포짓으로 빨라지지만 MD5가 사라지니 받는 쪽 검증 방식을 먼저 확인한다.
