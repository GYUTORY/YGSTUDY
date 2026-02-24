---
title: AWS S3 Glacier
tags: [aws, s3, glacier, archive, backup, storage, cold-storage]
updated: 2026-01-18
---

# AWS S3 Glacier

## 개요

Glacier는 장기 보관용 스토리지다. S3의 스토리지 클래스 중 하나다. 매우 저렴하다. 대신 데이터 복구에 시간이 걸린다. 자주 접근하지 않는 데이터를 저장한다. 규정 준수, 백업, 아카이브에 사용한다.

### S3 스토리지 클래스

**S3 Standard:**
- 자주 접근하는 데이터
- 빠른 접근 (밀리초)
- 비쌈 ($0.023/GB-월)

**S3 Intelligent-Tiering:**
- 접근 패턴에 따라 자동 이동
- 추가 비용 (모니터링)

**S3 Standard-IA (Infrequent Access):**
- 가끔 접근하는 데이터
- 빠른 접근 (밀리초)
- 저렴 ($0.0125/GB-월)
- 접근 시 비용

**S3 One Zone-IA:**
- 하나의 AZ에만 저장
- 더 저렴 ($0.01/GB-월)

**S3 Glacier Instant Retrieval:**
- 분기당 한 번 접근
- 밀리초 접근
- $0.004/GB-월

**S3 Glacier Flexible Retrieval (구 Glacier):**
- 년 1-2회 접근
- 복구 시간: 분 ~ 시간
- $0.0036/GB-월

**S3 Glacier Deep Archive:**
- 년 1회 미만 접근
- 복구 시간: 시간 ~ 일
- 가장 저렴 ($0.00099/GB-월)

## Glacier Flexible Retrieval

### 특징

**매우 저렴:**
S3 Standard의 1/6 가격.

**복구 시간:**
- Expedited: 1-5분
- Standard: 3-5시간
- Bulk: 5-12시간

**사용 사례:**
- 법적 보관 (7년 이상)
- 백업 (년 1회 복구)
- 미디어 아카이브

### 데이터 업로드

**S3 Lifecycle Policy 사용:**

자동으로 S3 Standard → Glacier로 이동한다.

**Lifecycle Rule 생성:**
```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-bucket \
  --lifecycle-configuration file://lifecycle.json
```

**lifecycle.json:**
```json
{
  "Rules": [
    {
      "Id": "Archive to Glacier",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "logs/"
      },
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "GLACIER"
        }
      ]
    }
  ]
}
```

**동작:**
- `logs/` 폴더의 파일
- 30일 후 자동으로 Glacier로 이동

**직접 업로드:**
```bash
aws s3 cp file.zip s3://my-bucket/archive/ \
  --storage-class GLACIER
```

바로 Glacier에 저장한다.

### 데이터 복구

**복구 요청:**
```bash
aws s3api restore-object \
  --bucket my-bucket \
  --key logs/2023-01-01.log \
  --restore-request '{"Days":7,"GlacierJobParameters":{"Tier":"Standard"}}'
```

**Tier 옵션:**
- **Expedited**: 1-5분, $0.03/GB
- **Standard**: 3-5시간, $0.01/GB
- **Bulk**: 5-12시간, $0.0025/GB

**Days:**
복구 후 S3 Standard-IA에 7일 동안 보관한다. 7일 후 다시 Glacier로 돌아간다.

**복구 상태 확인:**
```bash
aws s3api head-object \
  --bucket my-bucket \
  --key logs/2023-01-01.log
```

**출력:**
```json
{
  "Restore": "ongoing-request=\"true\""
}
```

복구 중이다.

**복구 완료:**
```json
{
  "Restore": "ongoing-request=\"false\", expiry-date=\"Sat, 25 Jan 2026 00:00:00 GMT\""
}
```

복구 완료. 1월 25일까지 접근 가능.

**다운로드:**
```bash
aws s3 cp s3://my-bucket/logs/2023-01-01.log ./
```

## Glacier Deep Archive

### 특징

**가장 저렴:**
S3 Standard의 1/23 가격.

**복구 시간:**
- Standard: 12시간
- Bulk: 48시간

**최소 보관 기간:**
180일. 조기 삭제 시 비용 발생.

**사용 사례:**
- 규제 준수 (금융, 의료)
- 장기 백업 (10년 이상)
- 역사적 기록

### 사용 방법

**Lifecycle Policy:**
```json
{
  "Rules": [
    {
      "Id": "Deep Archive",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "compliance/"
      },
      "Transitions": [
        {
          "Days": 365,
          "StorageClass": "DEEP_ARCHIVE"
        }
      ]
    }
  ]
}
```

1년 후 Deep Archive로 이동.

**복구:**
```bash
aws s3api restore-object \
  --bucket my-bucket \
  --key compliance/2020-report.pdf \
  --restore-request '{"Days":30,"GlacierJobParameters":{"Tier":"Standard"}}'
```

12시간 후 복구 완료.

## Glacier Instant Retrieval

### 특징

**밀리초 접근:**
S3 Standard와 동일한 속도.

**저렴:**
S3 Standard-IA보다 저렴.

**접근 빈도:**
분기당 한 번 정도.

**사용 사례:**
- 의료 이미지
- 뉴스 미디어 아카이브
- 사용자 생성 콘텐츠 백업

### 사용 방법

**Lifecycle Policy:**
```json
{
  "Transitions": [
    {
      "Days": 90,
      "StorageClass": "GLACIER_IR"
    }
  ]
}
```

90일 후 Instant Retrieval로 이동.

**접근:**
복구 과정 없이 바로 다운로드한다.

```bash
aws s3 cp s3://my-bucket/images/old-photo.jpg ./
```

즉시 다운로드된다.

## 비용

### 스토리지 비용

**비교 (1 TB, 1년):**

| 클래스 | 월 비용 | 년 비용 |
|--------|---------|---------|
| S3 Standard | $23.00 | $276 |
| S3 Standard-IA | $12.50 | $150 |
| Glacier Instant | $4.00 | $48 |
| Glacier Flexible | $3.60 | $43.20 |
| Glacier Deep Archive | $0.99 | $11.88 |

Deep Archive가 23배 저렴하다.

### 복구 비용

**Glacier Flexible (1 GB 복구):**
- Expedited: $0.03
- Standard: $0.01
- Bulk: $0.0025

**Deep Archive (1 GB 복구):**
- Standard: $0.02
- Bulk: $0.0025

**Glacier Instant:**
복구 비용 없음. 단, 접근당 요청 비용 ($0.01 per 1,000 requests).

### 조기 삭제 비용

**최소 보관 기간:**
- Glacier Instant: 90일
- Glacier Flexible: 90일
- Deep Archive: 180일

**예시:**
- 1 GB를 Glacier Flexible에 저장
- 30일 후 삭제
- 60일분 비용 청구 (90 - 30)

**비용:**
60일 × $0.0036/30일 = $0.0072

조기 삭제는 비효율적이다. 최소 기간을 채우고 삭제한다.

## Lifecycle Policy 전략

### 3-Tier 아카이빙

**단계별 이동:**
```json
{
  "Rules": [
    {
      "Id": "Progressive Archive",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 90,
          "StorageClass": "GLACIER_IR"
        },
        {
          "Days": 365,
          "StorageClass": "GLACIER"
        },
        {
          "Days": 1825,
          "StorageClass": "DEEP_ARCHIVE"
        }
      ],
      "Expiration": {
        "Days": 3650
      }
    }
  ]
}
```

**동작:**
- 0-30일: S3 Standard (빠른 접근)
- 31-90일: Standard-IA (가끔 접근)
- 91-365일: Glacier Instant (분기 접근)
- 366-1825일: Glacier Flexible (년 접근)
- 1826-3650일: Deep Archive (장기 보관)
- 3650일 후: 삭제 (10년)

**비용 최적화:**
접근 빈도에 맞춰 자동으로 이동한다.

### 파일 타입별 정책

**로그 파일:**
```json
{
  "Filter": {
    "Prefix": "logs/"
  },
  "Transitions": [
    {
      "Days": 7,
      "StorageClass": "STANDARD_IA"
    },
    {
      "Days": 30,
      "StorageClass": "GLACIER"
    }
  ],
  "Expiration": {
    "Days": 365
  }
}
```

1주일 후 IA, 1달 후 Glacier, 1년 후 삭제.

**백업:**
```json
{
  "Filter": {
    "Prefix": "backups/"
  },
  "Transitions": [
    {
      "Days": 1,
      "StorageClass": "GLACIER"
    }
  ],
  "Expiration": {
    "Days": 90
  }
}
```

바로 Glacier, 90일 후 삭제.

## 규정 준수

### S3 Object Lock

**Write-Once-Read-Many (WORM):**
저장 후 수정/삭제 불가. 규정 준수에 필요하다.

**모드:**

**Governance Mode:**
- 관리자가 삭제 가능
- 일반 사용자는 삭제 불가

**Compliance Mode:**
- 아무도 삭제 불가 (AWS Support도 불가)
- 보관 기간 동안 완전히 보호

**설정:**
```bash
aws s3api put-object-lock-configuration \
  --bucket my-compliance-bucket \
  --object-lock-configuration \
    '{"ObjectLockEnabled":"Enabled","Rule":{"DefaultRetention":{"Mode":"COMPLIANCE","Years":7}}}'
```

7년 동안 삭제 불가.

**Legal Hold:**
보관 기간과 별개로 영구 잠금.

```bash
aws s3api put-object-legal-hold \
  --bucket my-bucket \
  --key document.pdf \
  --legal-hold Status=ON
```

소송 등 법적 사유로 영구 보관이 필요할 때 사용한다.

## Vault Lock (Legacy)

**참고:** 새로운 아카이브는 S3 Glacier 스토리지 클래스를 사용한다. Vault는 레거시다.

**Vault:**
구형 Glacier의 컨테이너. 현재는 S3 버킷을 사용한다.

**Vault Lock:**
S3 Object Lock과 유사. WORM 기능 제공.

**마이그레이션:**
기존 Vault 데이터를 S3로 이전하는 것을 권장한다.

## 실무 사용

### 법적 보관 (금융)

**요구사항:**
- 거래 기록 7년 보관
- 수정 불가
- 감사 추적

**구성:**
- S3 버킷
- Object Lock (Compliance, 7년)
- Lifecycle: 즉시 Deep Archive
- CloudTrail 로깅

**비용 (1 TB):**
Deep Archive: $0.99/월 × 84개월 = $83.16

S3 Standard: $23/월 × 84개월 = $1,932

**95% 절감**

### 미디어 아카이브 (방송사)

**요구사항:**
- 방송 영상 장기 보관
- 가끔 재방송
- 빠른 복구 필요 (특정 영상)

**구성:**
- 최근 1년: S3 Standard-IA
- 1-5년: Glacier Instant Retrieval
- 5년 이상: Glacier Flexible

**동작:**
- 대부분 영상: Glacier에 저장 (저렴)
- 재방송 결정: Expedited 복구 (5분)
- 복구 후 7일 동안 접근
- 다시 Glacier로 이동

### 개발 백업

**요구사항:**
- 일일 백업
- 최근 7일은 빠른 복구
- 이전 백업은 저렴하게

**Lifecycle:**
```json
{
  "Rules": [
    {
      "Prefix": "backups/",
      "Transitions": [
        {
          "Days": 7,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 90
      }
    }
  ]
}
```

7일 후 Glacier, 90일 후 삭제.

## 모니터링

### CloudWatch 메트릭

**S3 메트릭:**
- **NumberOfObjects**: 객체 수
- **BucketSizeBytes**: 버킷 크기

스토리지 클래스별로 확인 가능.

**S3 Storage Lens:**
스토리지 사용량을 시각화한다. 클래스별 비용과 사용량을 추적한다.

### 비용 추적

**Cost Explorer:**
- S3 Standard vs Glacier 비용 비교
- Lifecycle 전환 후 절감액 확인

**태그 사용:**
```bash
aws s3api put-object-tagging \
  --bucket my-bucket \
  --key file.zip \
  --tagging 'TagSet=[{Key=Department,Value=Finance},{Key=Retention,Value=7years}]'
```

부서별, 보관 기간별로 비용을 추적한다.

## 참고

- S3 스토리지 클래스: https://aws.amazon.com/s3/storage-classes/
- Glacier 요금: https://aws.amazon.com/s3/pricing/
- S3 Lifecycle: https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html
- S3 Object Lock: https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html

