---
title: "GCP IAM Deny Policy"
tags: [gcp, iam, cloud]
updated: 2026-07-23
---

# GCP IAM Deny Policy

GCP IAM의 기본 모델은 additive다. 상위 레벨에서 부여한 권한은 하위에서 뺄 수 없다. 이 구조는 "이미 조직 레벨 Editor를 받은 사람이 특정 프로젝트에서만 접근을 못 하게 하려면?" 하는 요구를 충족시킬 방법이 없다는 뜻이다. Deny 정책은 이 간극을 메우기 위해 나왔다. Allow 바인딩보다 우선 평가되므로, 어디서 어떤 권한을 받든 Deny에 걸리면 차단된다.

조직(Organization), 폴더(Folder), 프로젝트(Project) 레벨 모두에 적용할 수 있다. 단, 리소스 레벨(버킷, 인스턴스 단위)은 지원하지 않는다.

## 정책 구조

Deny 정책은 IAM Allow 정책과 완전히 별개의 API(`iam.googleapis.com/v2`)로 관리된다. `gcloud projects get-iam-policy` 결과에 나오지 않는다. 별도 명령으로 조회해야 한다.

하나의 Deny 정책은 하나 이상의 Deny rule로 구성된다. 각 rule에는 세 가지 핵심 필드가 있다.

**deniedPrincipals** — 누구를 거부할 것인지. `user:kim@example.com`, `serviceAccount:...`, `group:...`, `domain:...` 형식으로 작성한다. `principalSet://...` 형태의 Workload Identity 페더레이션 신원도 쓸 수 있다.

**deniedPermissions** — 어떤 권한을 거부할 것인지. Allow 정책에서 쓰는 권한 이름과 같은 형식이다(`storage.objects.delete`). 역할 이름이 아닌 개별 권한 이름으로 지정해야 한다.

**exceptionPrincipals** — 거부에서 제외할 신원. `deniedPrincipals` 범위에 들어가더라도 이 필드에 있으면 거부가 적용되지 않는다. 팀 전체에 deny를 걸면서 특정 계정은 예외로 둘 때 쓴다.

조건 필드(`denialCondition`)도 있다. CEL 표현식으로 특정 리소스 이름이나 요청 속성에 따라 deny를 조건부로 적용할 수 있다.

```json
{
  "name": "policies/cloudresourcemanager.googleapis.com%2Fprojects%2F123456789/denypolicies/block-gcs-delete",
  "displayName": "Prod GCS 삭제 차단",
  "rules": [
    {
      "denyRule": {
        "deniedPrincipals": [
          "principalSet://goog/group/backend-team@example.com"
        ],
        "exceptionPrincipals": [
          "principal://goog/subject/storage-admin@prod-web.iam.gserviceaccount.com"
        ],
        "deniedPermissions": [
          "storage.objects.delete",
          "storage.buckets.delete"
        ]
      }
    }
  ]
}
```

## 평가 순서

GCP가 권한을 평가하는 순서는 고정돼 있다.

```
1. Deny 정책 평가 (조직 → 폴더 → 프로젝트 순)
2. Allow 정책 평가 (조직 → 폴더 → 프로젝트 → 리소스 순)
```

Deny에 걸리면 Allow 정책이 어디서 어떻게 열려 있든 차단된다. 반대로 Deny에 걸리지 않아야 Allow에서 권한 확인이 이루어진다. 두 단계를 모두 통과해야 접근이 허용된다.

이 평가 순서 때문에, 조직 레벨 Deny는 프로젝트 레벨에서 열어준 Allow를 덮어쓴다. 프로젝트 오너가 직접 열어준 권한도 조직 레벨 Deny 앞에서는 효과가 없다.

## 적용 명령

Deny 정책은 `gcloud iam policies` 커맨드로 관리한다. `gcloud projects/folders/organizations` 커맨드가 아니다.

```bash
# Deny 정책 JSON 파일 준비
cat > deny-policy.json <<'EOF'
{
  "displayName": "Prod GCS 삭제 차단",
  "rules": [
    {
      "denyRule": {
        "deniedPrincipals": [
          "principalSet://goog/group/backend-team@example.com"
        ],
        "deniedPermissions": [
          "storage.objects.delete",
          "storage.buckets.delete"
        ]
      }
    }
  ]
}
EOF

# 프로젝트 레벨에 Deny 정책 생성
gcloud iam policies create block-gcs-delete \
  --attachment-point="cloudresourcemanager.googleapis.com/projects/123456789" \
  --policy-file=deny-policy.json

# 조직 레벨에 적용
gcloud iam policies create block-gcs-delete \
  --attachment-point="cloudresourcemanager.googleapis.com/organizations/123456789" \
  --policy-file=deny-policy.json

# 폴더 레벨에 적용
gcloud iam policies create block-gcs-delete \
  --attachment-point="cloudresourcemanager.googleapis.com/folders/FOLDER_ID" \
  --policy-file=deny-policy.json

# Deny 정책 목록 조회
gcloud iam policies list \
  --attachment-point="cloudresourcemanager.googleapis.com/projects/123456789"

# 특정 Deny 정책 내용 조회
gcloud iam policies get block-gcs-delete \
  --attachment-point="cloudresourcemanager.googleapis.com/projects/123456789"

# Deny 정책 삭제
gcloud iam policies delete block-gcs-delete \
  --attachment-point="cloudresourcemanager.googleapis.com/projects/123456789"
```

`--attachment-point` 값에 프로젝트 이름이 아닌 프로젝트 번호를 써야 한다. 이름을 쓰면 동작하지 않는 경우가 있다. 번호는 `gcloud projects describe prod-web --format='value(projectNumber)'`로 확인한다.

## 감사 로그에서 Deny 이벤트 식별

Allow 기반 거부(`status.code=7`)와 Deny 정책으로 인한 거부는 감사 로그에서 다르게 나온다. Deny 정책이 작동한 경우 `protoPayload.policyViolationInfo` 필드가 생긴다.

```bash
# Deny 정책으로 막힌 요청 조회
gcloud logging read \
  'protoPayload.policyViolationInfo.orgPolicyViolationInfo.violations:*' \
  --project=prod-web \
  --limit=20 \
  --format="table(timestamp, protoPayload.authenticationInfo.principalEmail, protoPayload.methodName)"
```

로그 항목에서 확인할 수 있는 필드 구조다.

```json
{
  "protoPayload": {
    "authenticationInfo": {
      "principalEmail": "kim@example.com"
    },
    "methodName": "storage.objects.delete",
    "status": {
      "code": 7,
      "message": "PERMISSION_DENIED"
    },
    "policyViolationInfo": {
      "orgPolicyViolationInfo": {
        "violations": [
          {
            "constraint": "projects/123456789/denypolicies/block-gcs-delete",
            "errorMessage": "...",
            "checkedValue": "..."
          }
        ]
      }
    }
  }
}
```

`policyViolationInfo`가 있으면 Deny 정책에 걸린 것이고, 없으면 Allow 정책에서 권한이 없는 것이다. 이걸 구분하지 않으면 "Allow에서 열어줬는데 왜 안 돼?"라는 디버깅 루프에 빠진다.

Cloud Logging 콘솔에서 `protoPayload.policyViolationInfo!=""`로 필터링하면 Deny 정책 관련 이벤트만 걸러낼 수 있다.

## 기본 역할 상속 차단 패턴

조직 레벨에서 실수로 `roles/owner`나 `roles/editor`를 받은 계정이 있고, 단기간에 정리할 수 없는 상황에서 쓸 수 있는 패턴이다.

특정 개발자가 조직 레벨 `roles/editor`를 받았고, prod 폴더에서만 write 권한을 막아야 하는 상황을 예로 든다. Allow 정책만으로는 불가능하다. Deny 정책으로 이렇게 처리한다.

```json
{
  "displayName": "Prod 폴더 쓰기 차단",
  "rules": [
    {
      "denyRule": {
        "deniedPrincipals": [
          "principal://goog/subject/dev-user@example.com"
        ],
        "exceptionPrincipals": [],
        "deniedPermissions": [
          "compute.instances.create",
          "compute.instances.delete",
          "storage.objects.create",
          "storage.objects.delete",
          "cloudsql.instances.create"
        ]
      }
    }
  ]
}
```

```bash
gcloud iam policies create prod-write-block \
  --attachment-point="cloudresourcemanager.googleapis.com/folders/PROD_FOLDER_ID" \
  --policy-file=prod-write-block.json
```

`deniedPermissions`에 막을 권한을 하나씩 열거해야 한다. `roles/editor` 자체를 지정하는 게 아니다. `roles/editor`에 포함된 수천 개 권한을 전부 막으려면 그 목록을 다 넣어야 한다는 뜻이다. 현실적으로 특정 액션(인스턴스 삭제, 데이터 수정 등)만 좁혀서 막는 방식이 관리 가능하다.

권한 와일드카드는 일부 지원한다. `storage.objects.*`처럼 서비스 내 모든 권한을 묶어서 지정할 수 있다.

```json
{
  "deniedPermissions": [
    "storage.objects.*",
    "storage.buckets.*"
  ]
}
```

와일드카드를 `cloudresourcemanager.*`처럼 IAM 자체를 건드리는 권한에 쓰면 본인도 정책을 수정할 수 없게 되는 상황이 생길 수 있다. `exceptionPrincipals`에 관리 계정을 반드시 넣어두어야 한다.

## Deny를 남발하면 안 되는 이유

Deny는 권한 평가에서 최우선이다. 이 특성 때문에 잘못 쓰면 정상적인 운영 작업까지 막히고, 막힌 이유를 찾는 데 시간이 많이 걸린다.

**디버깅이 어렵다.** `gcloud projects get-iam-policy`에 나오지 않는다. Deny 정책은 별도 API로 조회해야 하고, 조직·폴더·프로젝트 각 레벨을 따로 확인해야 한다. "권한이 있는데 왜 막히지?" 하는 상황에서 Deny 정책을 모르는 팀원이 원인을 찾지 못하는 경우가 생긴다.

**exceptionPrincipals 관리가 복잡해진다.** Deny 범위가 넓을수록 예외 목록도 길어진다. 예외 목록이 길어질수록 Deny를 거는 의미가 줄어든다. 결국 Allow 정책만 잘 관리하는 것보다 복잡한 구조만 남는다.

**긴급 상황에서 리스크가 커진다.** 장애 복구 중에 필요한 작업이 Deny에 막히면 복구 시간이 늘어난다. Deny 정책 자체를 수정할 권한이 있는 계정이 없거나 온콜 담당자가 IAM Deny에 익숙하지 않으면 더 위험하다.

Deny가 적합한 케이스는 한정적이다.

조직 레벨에서 과도하게 부여된 기본 역할(owner/editor)을 단기간에 정리할 수 없을 때 임시 차단 수단으로 쓰는 게 현실적이다. 근본 해결은 그 역할을 회수하는 것이고, Deny는 그 사이를 버티는 용도다.

규정 준수 요구사항으로 특정 지역 외 리소스 생성을 막아야 하는 경우, `denialCondition`에 리소스 위치 조건을 걸어서 지역 단위로 제한할 수 있다.

보안 사고 발생 시 특정 계정의 액션을 즉시 차단해야 하는 상황에서도 쓸 수 있다. 계정 비활성화(Google Workspace에서 계정 정지)가 더 확실하지만, GCP IAM 레벨에서만 빠르게 차단이 필요하다면 유용하다.

```bash
# 특정 계정 즉시 차단 (보안 사고 대응)
cat > emergency-block.json <<'EOF'
{
  "displayName": "보안 사고 임시 차단",
  "rules": [
    {
      "denyRule": {
        "deniedPrincipals": [
          "principal://goog/subject/compromised-user@example.com"
        ],
        "deniedPermissions": [
          "storage.objects.*",
          "compute.instances.*",
          "bigquery.tables.*"
        ]
      }
    }
  ]
}
EOF

gcloud iam policies create emergency-block \
  --attachment-point="cloudresourcemanager.googleapis.com/organizations/123456789" \
  --policy-file=emergency-block.json
```

일반적인 접근 제어에 Deny를 쓰는 건 권하지 않는다. Allow 정책을 처음부터 최소 권한으로 설계하고 필요한 레벨에 붙이는 게 장기적으로 유지보수하기 쉽다. Deny는 그 설계가 실패했을 때의 수습 도구에 가깝다.
