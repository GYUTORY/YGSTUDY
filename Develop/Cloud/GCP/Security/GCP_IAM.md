---
title: "GCP IAM (Identity and Access Management)"
tags: [GCP, iam, Service Account, Workload Identity, Custom Role, 최소 권한, 감사 로그]
updated: 2026-07-14
---

# GCP IAM

GCP에서 권한을 틀리면 배포가 막히거나, 더 나쁘게는 과도하게 열어두고 보안 사고가 난다. IAM의 구조를 제대로 이해해야 양쪽 실수를 모두 피할 수 있다. 이 문서는 리소스 계층부터 실무에서 자주 틀리는 케이스까지 순서대로 다룬다.

## 리소스 계층과 정책 상속

GCP의 리소스는 트리 구조로 묶인다. 맨 위가 조직(Organization), 그 아래 폴더(Folder), 그 아래 프로젝트(Project), 그 아래 실제 리소스(GCE 인스턴스, GCS 버킷 등)다.

```
조직 (example.com)
├── 폴더: prod
│   ├── 프로젝트: prod-web
│   │   ├── Cloud Run 서비스
│   │   └── GCS 버킷
│   └── 프로젝트: prod-batch
│       └── BigQuery 데이터셋
└── 폴더: dev
    └── 프로젝트: dev-sandbox
```

IAM 정책은 이 트리 구조를 따라 위에서 아래로 상속된다. 조직 레벨에서 역할을 주면 그 아래 모든 리소스에서 유효하다. 프로젝트 레벨이면 그 프로젝트 안에서만 유효하다.

여기서 반드시 알아야 할 게 있다. **상속된 권한은 하위에서 뺄 수 없다**. GCP IAM은 합집합(additive) 모델이다. 조직 레벨에서 편집자 권한을 받았으면, 특정 프로젝트에서만 뷰어로 낮추는 게 불가능하다. 하위에서 더 추가하는 건 되지만 빼는 건 안 된다.

이걸 무시하고 "일단 팀 전체에 조직 레벨 Editor 줘" 하면 나중에 prod 프로젝트만 접근을 막으려 할 때 방법이 없다. 권한은 항상 필요한 가장 낮은 계층에 붙이는 게 원칙이다. 상속을 이용해 상위에 붙이면 범위 조정이 사실상 불가능해진다. 팀 단위 접근 관리가 필요하다면 폴더로 묶고 폴더 레벨에 붙인다.

deny 정책(IAM Deny)을 걸면 상위 권한을 하위에서 막을 수 있긴 한데, 이건 나중에 도입된 기능이고 GA 전에 제약이 많다. 대부분의 팀에서 실무적으로 "처음부터 상위에 헤프게 주지 않는" 방식을 택한다.

### 정책 조회와 상속 추적

직접 붙은 정책과 상속받은 정책은 따로 관리된다.

```bash
# 프로젝트에 직접 붙은 바인딩만 보인다
gcloud projects get-iam-policy prod-web --format=json

# 폴더에 직접 붙은 정책
gcloud resource-manager folders get-iam-policy FOLDER_ID --format=json

# 특정 사용자가 실제로 가진 권한(상속 포함)
# get-iam-policy 하나로는 알 수 없고 Policy Analyzer를 써야 한다
gcloud asset analyze-iam-policy \
  --organization=123456789 \
  --identity="user:kim@example.com" \
  --full-resource-name="//cloudresourcemanager.googleapis.com/projects/prod-web"
```

`get-iam-policy`가 상속분을 보여주지 않는다는 게 함정이다. "왜 이 사람이 접근되지?" 하고 프로젝트 정책만 봐선 답이 안 나오는 경우가 생기는 이유다. 폴더나 조직 상위 레벨을 직접 찾아봐야 한다. Policy Analyzer는 asset inventory API가 활성화돼 있어야 동작한다.

## Principal 종류

IAM에서 권한을 받는 주체(Principal)는 네 가지다.

**Google Account** — 개인 Gmail 또는 Google Workspace 계정. `user:kim@example.com` 형태. 실제 사람에게 직접 권한을 주는 방식이다. 개인별 관리가 필요할 때 쓰지만, 퇴사자 처리나 대규모 권한 변경에서 관리 비용이 커진다.

**Service Account** — 사람이 아닌 워크로드(애플리케이션, VM, 배치 잡)를 위한 계정. `serviceAccount:deploy-bot@prod-web.iam.gserviceaccount.com` 형태. GCP 서비스들이 API를 호출할 때 이 신원을 쓴다. 서비스 계정은 "멤버"로서 권한을 받기도 하고, "리소스"로서 누가 이것을 흉내낼(impersonate) 수 있는지 관리되기도 한다. 이 이중 역할을 헷갈리면 권한 설계가 꼬인다.

**Google Group** — Google Workspace의 그룹. `group:backend-team@example.com` 형태. 팀 단위로 권한을 관리할 때 쓴다. 사람이 팀에 합류하거나 떠날 때 IAM 정책 자체는 안 건드리고 그룹 멤버십만 변경하면 된다. 실무에서 가장 권장되는 방식이다. 개인별로 IAM 바인딩을 만들면 나중에 감사나 정리가 힘들다.

**Domain** — Google Workspace 도메인 전체. `domain:example.com` 형태. 그 도메인의 모든 사용자에게 적용된다. 사내 모든 임직원에게 특정 리소스 읽기 권한을 줄 때 쓰는데, 범위가 넓어서 실수하기 쉽다. 외부 계정 발급 가능한 Workspace 도메인이라면 더 위험하다.

한 가지 더 있다. `allUsers`와 `allAuthenticatedUsers`는 멤버 유형이지 Principal 유형은 아닌데, GCS 버킷 같은 곳에서 공개 접근을 허용할 때 쓴다. `allUsers`는 인증 없는 접근까지 허용하므로 실수로 붙이면 버킷 데이터가 공개된다. GCP가 경고를 띄우지만 무시하고 붙이는 경우가 있다.

## Role 유형

### 기본 역할 (Basic Role)

`roles/owner`, `roles/editor`, `roles/viewer` 세 가지다. GCP 초창기부터 있던 것으로 프로젝트 전체에 걸친 광범위한 권한을 준다. `owner`는 IAM 정책 자체를 수정할 수 있고, `editor`는 거의 모든 리소스를 만들고 고칠 수 있다.

실무에서 기본 역할은 되도록 쓰지 않는다. 특히 서비스 계정에 `editor`를 붙이는 건 최소 권한 원칙을 완전히 포기하는 것과 같다. 빠르게 프로토타입 만들 때 편의상 쓰다가 그대로 prod에 올라가는 케이스가 실제로 많다.

### 사전 정의 역할 (Predefined Role)

`roles/storage.objectViewer`, `roles/cloudsql.client`처럼 서비스별로 GCP가 미리 만들어 둔 역할이다. 대부분의 경우 여기서 맞는 걸 찾을 수 있다.

역할 이름만 보고 안전하다고 방심하면 안 된다. `roles/storage.admin`은 버킷 삭제와 IAM 정책 변경까지 포함한다. 어떤 권한이 들어있는지 확인하는 습관이 필요하다.

```bash
# 역할에 포함된 권한 목록 확인
gcloud iam roles describe roles/storage.objectAdmin

# 특정 권한이 어떤 역할에 포함됐는지 역방향 검색
# 콘솔의 IAM > 역할 > 권한으로 필터링하는 게 빠르다
```

권한 목록이 수십 개씩 나오는 역할도 흔하다. 위험한 건 보통 `.setIamPolicy`(권한 위임), `.delete`(삭제), `.admin` 접미사가 붙은 권한들이다.

### 커스텀 역할 (Custom Role)

사전 정의 역할이 너무 넓거나 딱 맞는 게 없을 때 권한을 직접 골라 만든다.

```yaml
# uploader-role.yaml
title: "GCS Uploader"
description: "버킷에 객체 업로드/조회만"
stage: "GA"
includedPermissions:
  - storage.objects.create
  - storage.objects.get
  - storage.objects.list
```

```bash
gcloud iam roles create gcsUploader \
  --project=prod-web \
  --file=uploader-role.yaml

# 조직 레벨 커스텀 역할 (여러 프로젝트에서 재사용하려면)
gcloud iam roles create gcsUploader \
  --organization=123456789 \
  --file=uploader-role.yaml
```

커스텀 역할의 실무 문제 두 가지가 있다. 하나는 GCP가 새 API를 내면서 권한 이름을 추가하거나 바꾸는데 커스텀 역할은 자동으로 안 따라온다. 서비스가 업데이트되면서 새 권한이 생겼는데 커스텀 역할에 없어서 갑자기 에러가 나는 경우가 있다. 커스텀 역할은 만들고 방치하면 안 되고 주기적으로 점검해야 한다.

다른 하나는 프로젝트 레벨 커스텀 역할은 다른 프로젝트에서 못 쓴다. 여러 프로젝트에서 같은 커스텀 역할을 재사용하려면 조직 레벨에 만들어야 한다. 조직 레벨 커스텀 역할을 만들고 관리할 권한이 필요하기 때문에, 보통 플랫폼 팀이나 보안 팀에서 중앙 관리한다.

## IAM Policy 바인딩 구조

IAM 정책의 구조는 간단하다. 하나의 정책이 여러 바인딩(binding)으로 이루어지고, 각 바인딩은 `멤버(들) + 역할 + 조건(선택)`의 세 쌍이다.

```json
{
  "bindings": [
    {
      "role": "roles/storage.objectViewer",
      "members": [
        "user:kim@example.com",
        "serviceAccount:api-server@prod-web.iam.gserviceaccount.com"
      ]
    },
    {
      "role": "roles/storage.objectAdmin",
      "members": [
        "serviceAccount:deploy-bot@prod-web.iam.gserviceaccount.com"
      ],
      "condition": {
        "title": "prod_bucket_only",
        "expression": "resource.name.startsWith('projects/_/buckets/prod-')"
      }
    }
  ]
}
```

정책 바인딩을 추가하고 제거하는 기본 명령이다.

```bash
# 단일 바인딩 추가
gcloud projects add-iam-policy-binding prod-web \
  --member="serviceAccount:api-server@prod-web.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 단일 바인딩 제거
gcloud projects remove-iam-policy-binding prod-web \
  --member="serviceAccount:api-server@prod-web.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 정책 전체를 JSON으로 받아 수정 후 다시 설정 (여러 바인딩을 한 번에)
gcloud projects get-iam-policy prod-web --format=json > policy.json
# policy.json 편집
gcloud projects set-iam-policy prod-web policy.json
```

`add-iam-policy-binding`은 기존 정책을 read-modify-write한다. 동시에 여러 명령이 실행되면 충돌이 날 수 있다. 대규모 권한 변경은 `get-iam-policy`로 받아 수정 후 `set-iam-policy`로 한 번에 설정하는 게 안전하다.

### 조건부 IAM (IAM Condition)

조건(Condition)을 붙이면 특정 리소스, 시간, 요청 속성에 따라 권한을 조건부로 적용할 수 있다. Common Expression Language(CEL)로 작성한다.

```bash
# 특정 버킷에만 적용되는 조건부 역할 부여
gcloud storage buckets add-iam-policy-binding gs://prod-assets \
  --member="serviceAccount:cdn-bot@prod-web.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer" \
  --condition='title=cdn_only,expression=resource.name.startsWith("projects/_/buckets/prod-assets")'

# 특정 기간만 유효한 임시 권한
gcloud projects add-iam-policy-binding prod-web \
  --member="user:contractor@external.com" \
  --role="roles/viewer" \
  --condition='title=temp_access,expression=request.time < timestamp("2026-08-01T00:00:00Z")'
```

조건부 IAM은 권한을 좁히는 좋은 도구지만 주의할 점이 있다. 조건을 잘못 작성하면 원하는 리소스에 접근이 아예 안 될 수 있다. 특히 버킷 이름 비교에서 `resource.name` 형식이 생각한 것과 다를 수 있다. 콘솔의 Policy Troubleshooter로 실제 조건이 어떻게 평가되는지 테스트하고 적용한다.

또한 조건부 바인딩이 걸린 역할은 `gcloud projects get-iam-policy` 결과에서 `condition` 필드로 식별 가능한데, 조건을 만족하지 못해 거부될 때 에러 메시지가 다소 불친절하다. 디버깅할 때 혼동하기 쉽다.

## 서비스 계정 생성과 키 관리

서비스 계정은 프로젝트 안에서 만든다.

```bash
# 서비스 계정 생성
gcloud iam service-accounts create api-server \
  --display-name="API Server" \
  --project=prod-web

# 서비스 계정에 역할 부여 (프로젝트 레벨)
gcloud projects add-iam-policy-binding prod-web \
  --member="serviceAccount:api-server@prod-web.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 특정 리소스에 직접 역할 부여 (버킷 레벨)
gcloud storage buckets add-iam-policy-binding gs://prod-data \
  --member="serviceAccount:api-server@prod-web.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

# Cloud Run 서비스에 서비스 계정 연결
gcloud run services update api-service \
  --service-account=api-server@prod-web.iam.gserviceaccount.com \
  --region=asia-northeast3
```

서비스 계정 키(JSON 키 파일)는 만들지 않는 게 원칙이다. 키를 만들면 만료 없는 영구 자격증명이 파일로 남는다. GitHub에 실수로 커밋되거나 이미지 레이어에 박히거나 슬랙에 붙여넣기 되는 사고가 실제로 많다. 봇들이 공개 리포지토리를 긁어서 키를 찾아 암호화폐 채굴 인스턴스를 대량으로 띄우는데, 아침에 출근해서 수천 달러짜리 청구서를 보는 케이스가 실제로 있다.

GCP 안에서 도는 워크로드(GCE, GKE, Cloud Run)는 키가 필요 없다. 리소스에 서비스 계정을 연결하면 메타데이터 서버에서 자동으로 토큰을 받는다. Application Default Credentials(ADC)가 이걸 처리해서, 코드에서 별도 인증 설정 없이 클라이언트 라이브러리가 알아서 가져온다.

이미 키를 쓰고 있다면 발급된 키 목록부터 파악한다.

```bash
# 서비스 계정에 발급된 키 목록
gcloud iam service-accounts keys list \
  --iam-account=api-server@prod-web.iam.gserviceaccount.com

# USER_MANAGED 키 삭제 (SYSTEM_MANAGED는 건드리지 않는다)
gcloud iam service-accounts keys delete KEY_ID \
  --iam-account=api-server@prod-web.iam.gserviceaccount.com
```

조직 정책으로 키 생성 자체를 막는 것도 방법이다.

```bash
# 프로젝트에서 서비스 계정 키 생성 금지
gcloud org-policies set-policy --project=prod-web \
  constraints/iam.disableServiceAccountKeyCreation=true
```

키 없이 서비스 계정을 흉내내는(impersonate) 방식으로 로컬 개발이나 임시 작업을 처리할 수 있다.

```bash
# 서비스 계정 흉내내서 명령 실행 (임시 토큰 1시간)
gcloud storage ls gs://prod-data \
  --impersonate-service-account=api-server@prod-web.iam.gserviceaccount.com
```

이게 되려면 실행하는 계정에 해당 서비스 계정에 대한 `roles/iam.serviceAccountTokenCreator`가 있어야 한다. 이 역할 자체가 강력해서 누구에게 줄지 신중하게 결정해야 한다.

## Workload Identity Federation

GCP 밖 워크로드가 키 없이 GCP에 인증하는 방법이다. 외부 신원 공급자(IdP)가 발급한 토큰을 GCP가 신뢰하고, 그 토큰을 GCP 임시 토큰으로 교환해 주는 구조다.

GitHub Actions를 예로 들면 흐름이 이렇다.

```
GitHub Actions 실행
    → GitHub이 서명한 OIDC 토큰 발급 (repo, branch, workflow 등 포함)
    → GCP STS에 토큰 제시
    → STS가 신뢰 조건 검증 (어느 repo, 어느 branch인지)
    → GCP 임시 액세스 토큰 발급
    → GCP API 호출
```

이 과정 어디에도 파일로 저장되는 영구 키가 없다.

```bash
# Workload Identity 풀 생성
gcloud iam workload-identity-pools create github-pool \
  --location=global \
  --display-name="GitHub Actions Pool"

# OIDC 공급자 생성 (GitHub)
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location=global \
  --workload-identity-pool=github-pool \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository=='myorg/myrepo' && assertion.ref=='refs/heads/main'"

# 외부 신원이 서비스 계정을 흉내낼 수 있게 연결
gcloud iam service-accounts add-iam-policy-binding \
  deploy-bot@prod-web.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/123456789/locations/global/workloadIdentityPools/github-pool/attribute.repository/myorg/myrepo"
```

`--attribute-condition`을 반드시 걸어야 한다. 조건 없이 풀을 만들면 어느 GitHub 리포에서 온 토큰이든 다 받아버린다. 이 경우 남의 리포에서도 서비스 계정을 흉내낼 수 있게 되므로 키보다 오히려 위험해진다. prod 배포는 `assertion.ref=='refs/heads/main'`까지 좁히고, 스테이징과 분리한다.

GitHub Actions 워크플로에서는 이렇게 쓴다.

```yaml
permissions:
  id-token: write   # OIDC 토큰 발급 권한 명시 필수
  contents: read

steps:
  - uses: google-github-actions/auth@v2
    with:
      workload_identity_provider: "projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
      service_account: "deploy-bot@prod-web.iam.gserviceaccount.com"
```

`id-token: write` 권한을 명시하지 않으면 OIDC 토큰이 발급되지 않아 인증 자체가 안 된다. 이 설정을 빠뜨리는 실수가 꽤 흔하다.

설정하다 자주 막히는 부분이 몇 개 있다.

`principalSet` 경로에 프로젝트 이름이 아니라 프로젝트 번호를 써야 한다. 이름을 쓰면 조용히 매칭이 안 된다. 프로젝트 번호는 `gcloud projects describe prod-web --format='value(projectNumber)'`로 확인한다.

`attribute-mapping`에 정의하지 않은 속성을 `attribute-condition`에서 참조하면 에러가 난다. `assertion.ref`를 조건에 쓰려면 매핑에 `attribute.ref=assertion.ref`가 있어야 한다.

## 실무에서 자주 틀리는 권한 케이스

### Cloud Run → Secret Manager

Cloud Run 서비스에서 Secret Manager의 시크릿을 읽으려면 Cloud Run에 연결된 서비스 계정에 `roles/secretmanager.secretAccessor`가 있어야 한다. 콘솔에서 Cloud Run 서비스를 만들 때 별도로 서비스 계정을 지정하지 않으면 Compute Engine 기본 서비스 계정을 쓴다. 이 기본 계정에 Secret Manager 권한이 없어서 런타임에 403이 난다.

더 흔한 실수는 프로젝트 레벨이 아니라 특정 시크릿에만 접근 권한을 주려고 시크릿 레벨 IAM을 쓰는데, 프로젝트 레벨에도 아무 권한이 없어서 안 된다고 착각하는 경우다. 시크릿 레벨 IAM 바인딩만으로도 충분하다. 프로젝트 레벨에 넣을 필요 없다.

```bash
# 특정 시크릿에만 접근 허용 (권장)
gcloud secrets add-iam-policy-binding my-api-key \
  --project=prod-web \
  --member="serviceAccount:api-server@prod-web.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### GKE Workload Identity

GKE에서 파드가 GCP API를 쓰려면 Workload Identity를 설정해야 한다. 클러스터에 Workload Identity를 활성화하고, Kubernetes 서비스 계정과 GCP 서비스 계정을 연결하는 과정이 필요하다.

```bash
# 클러스터에서 Workload Identity 활성화
gcloud container clusters update my-cluster \
  --workload-pool=prod-web.svc.id.goog \
  --region=asia-northeast3

# GCP 서비스 계정 생성
gcloud iam service-accounts create k8s-app-sa \
  --project=prod-web

# GCP 서비스 계정이 Kubernetes 서비스 계정으로 사용될 수 있도록 바인딩
gcloud iam service-accounts add-iam-policy-binding \
  k8s-app-sa@prod-web.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="serviceAccount:prod-web.svc.id.goog[my-namespace/my-k8s-sa]"
```

Kubernetes 서비스 계정에는 GCP 서비스 계정을 가리키는 어노테이션을 붙인다.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-k8s-sa
  namespace: my-namespace
  annotations:
    iam.gke.io/gcp-service-account: k8s-app-sa@prod-web.iam.gserviceaccount.com
```

이 설정을 해도 안 되는 경우가 몇 가지 있다. 노드 풀에서 Workload Identity가 비활성화돼 있거나, 파드 스펙에서 `serviceAccountName`을 지정하지 않아 `default` 서비스 계정으로 돌거나, 어노테이션의 서비스 계정 이메일에 오타가 있거나. 마지막 케이스는 어노테이션을 조용히 무시하기 때문에 디버깅이 까다롭다.

```bash
# 파드 안에서 신원 확인
kubectl exec -it my-pod -- curl -H "Metadata-Flavor: Google" \
  "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email"
```

이 명령 결과가 기대한 서비스 계정이 맞는지 먼저 확인한다.

### BigQuery job 실행

BigQuery에서 쿼리를 실행하려면 `bigquery.jobs.create` 권한이 있어야 한다. 이 권한은 `roles/bigquery.jobUser`에 포함돼 있다. 데이터 읽기 권한(`roles/bigquery.dataViewer`)만 줬는데 쿼리가 안 된다는 경우가 자주 있다.

```bash
# BigQuery 쿼리 실행에 필요한 최소 권한
# 1. 잡 실행 권한 (프로젝트 레벨)
gcloud projects add-iam-policy-binding prod-web \
  --member="serviceAccount:batch-worker@prod-web.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"

# 2. 데이터 읽기 권한 (데이터셋 레벨)
bq query --use_legacy_sql=false "
  GRANT \`roles/bigquery.dataViewer\`
  ON SCHEMA prod-web.analytics
  TO 'serviceAccount:batch-worker@prod-web.iam.gserviceaccount.com'
"
```

쿼리 결과를 다른 테이블에 쓰거나 외부 데이터를 읽는다면 추가 권한이 필요하다. `bigquery.tables.create`, `bigquery.tables.updateData` 등이다. 권한 에러 메시지에서 필요한 권한 이름이 정확히 나오므로 그걸 보고 추가한다.

BigQuery는 잡을 실행하는 프로젝트 레벨의 `jobUser`와 데이터가 있는 프로젝트·데이터셋 레벨의 데이터 권한을 분리해서 관리한다. 크로스 프로젝트 쿼리를 할 때 이 두 레벨을 각각 확인해야 한다.

## gcloud CLI로 권한 감사

정기적으로 누가 어떤 권한을 갖는지 감사하는 건 운영의 기본이다.

```bash
# 특정 역할을 가진 멤버 목록
gcloud projects get-iam-policy prod-web \
  --flatten="bindings[].members" \
  --format="table(bindings.role, bindings.members)" \
  --filter="bindings.role:roles/editor"

# 특정 멤버가 가진 역할 목록
gcloud projects get-iam-policy prod-web \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:api-server@prod-web.iam.gserviceaccount.com"

# 프로젝트 내 모든 서비스 계정 목록
gcloud iam service-accounts list --project=prod-web

# 서비스 계정에 발급된 키 현황 전체 조회
for sa in $(gcloud iam service-accounts list --project=prod-web --format="value(email)"); do
  keys=$(gcloud iam service-accounts keys list --iam-account=$sa --filter="keyType=USER_MANAGED" --format="value(name)" 2>/dev/null)
  if [ -n "$keys" ]; then
    echo "SA: $sa has USER_MANAGED keys"
  fi
done
```

Cloud Audit Logs를 켜두면 어떤 신원이 어떤 API를 불렀고 결과가 뭐였는지 다 남는다. 권한 거부 케이스를 찾을 때 가장 확실한 방법이다.

```bash
# 특정 서비스 계정의 권한 거부 이력
gcloud logging read \
  'protoPayload.authenticationInfo.principalEmail="api-server@prod-web.iam.gserviceaccount.com"
   AND protoPayload.status.code=7' \
  --project=prod-web \
  --limit=20 \
  --format="table(timestamp, protoPayload.methodName, protoPayload.status.message)"

# IAM 정책 변경 이력 (누가 언제 권한을 바꿨는지)
gcloud logging read \
  'protoPayload.methodName="SetIamPolicy"' \
  --project=prod-web \
  --limit=10 \
  --format="table(timestamp, protoPayload.authenticationInfo.principalEmail, protoPayload.methodName)"
```

`status.code=7`이 PERMISSION_DENIED다. 이 로그가 나오면 `protoPayload.methodName`에 어떤 API 메서드에서 막혔는지 나온다. 그 메서드에 필요한 권한을 역할에 추가하면 된다.

## 최소 권한 적용과 커스텀 역할로 좁히기

사전 정의 역할이 너무 광범위해서 커스텀 역할로 좁혀야 하는 상황은 꽤 자주 생긴다.

예를 들어 Cloud Run 서비스를 배포하는 CI/CD 파이프라인에 필요한 권한만 뽑으면 이렇다.

```bash
# Cloud Run 서비스 배포에 필요한 권한 확인
gcloud iam roles describe roles/run.admin
# 100개 가까이 나오는데 배포에 실제로 필요한 건 10개 내외다
```

실제 배포에 필요한 권한만 골라낸 커스텀 역할을 만든다.

```yaml
# cloudrun-deployer.yaml
title: "Cloud Run Deployer"
description: "Cloud Run 서비스 배포에 필요한 최소 권한"
stage: "GA"
includedPermissions:
  - run.services.create
  - run.services.update
  - run.services.get
  - run.services.list
  - run.operations.get
  - iam.serviceAccounts.actAs
```

`iam.serviceAccounts.actAs`는 Cloud Run 서비스에 서비스 계정을 연결할 때 필요하다. 이걸 빠뜨리면 서비스 계정 지정이 안 된다는 에러가 나는데, 에러 메시지가 직관적이지 않아서 처음엔 왜 안 되는지 모르는 경우가 있다.

처음부터 커스텀 역할로 딱 맞게 좁히려 하면 자꾸 권한 에러가 나서 진도가 안 나간다. 현실적인 순서는, 일단 사전 정의 역할 중 넓은 걸 주고 배포를 돌린 다음, IAM Recommender나 감사 로그로 실제 사용된 권한만 뽑아 커스텀 역할로 좁히는 것이다.

```bash
# IAM Recommender로 초과 권한 제안 받기
gcloud recommender recommendations list \
  --project=prod-web \
  --recommender=google.iam.policy.Recommender \
  --location=global \
  --format="table(name, description, stateInfo.state)"
```

Recommender 제안을 그대로 다 반영하면 주기적으로만 쓰는 배치 잡 같은 게 90일 안에 안 돌았다면 그 권한도 잘라버릴 수 있다. 제안을 검토하고 실제 워크로드 특성을 고려해 선택적으로 반영한다.

권한 디버깅할 때 추측으로 역할을 붙였다 뗐다 하는 것보다, 감사 로그에서 어떤 메서드가 막혔는지 정확히 확인하고 그 메서드에 필요한 권한만 추가하는 게 최소 권한에 도달하는 가장 빠른 방법이다.
