---
title: Amazon QuickSight
tags: [aws, quicksight, bi, spice, dashboard, embedded, access-control, analytics]
updated: 2026-07-25
---

# Amazon QuickSight

QuickSight는 AWS의 BI 서비스다. Redshift, Athena, RDS, S3 같은 AWS 데이터 소스에 연결해서 대시보드를 만들고, 그 대시보드를 웹 애플리케이션 안에 심거나 팀 내부에서 공유하는 용도로 쓴다.

Tableau나 Looker에 비하면 기능이 단순한 편이지만, AWS 데이터 소스와 연동이 쉽고 사용자 수에 따라 요금이 나가는 구조라 내부 BI 도구로 쓰기에는 무난하다.

## 데이터 소스 연결

QuickSight가 데이터를 가져오는 방식은 두 가지다. 데이터를 SPICE(Super-fast Parallel In-memory Calculation Engine)로 복사해오는 방식과, 쿼리가 들어올 때마다 원본에 직접 조회하는 방식이다.

SPICE 방식은 대시보드 로딩이 빠르다. 데이터가 이미 메모리에 올라와 있으니 Athena나 Redshift에 실시간으로 쿼리를 날리지 않는다. 대신 데이터가 실시간이 아니다. 마지막 SPICE 새로고침 시점의 스냅샷을 보여준다.

직접 쿼리 방식은 항상 최신 데이터를 보여주지만, 매 대시보드 조회마다 백엔드 데이터 소스에 쿼리가 나간다. Athena를 직접 쿼리하면 스캔 비용이 발생하고, 복잡한 집계 쿼리면 응답이 느리다.

### Athena

가장 많이 쓰는 조합이다. S3에 Parquet이나 CSV로 적재된 데이터를 Athena 테이블로 정의해두고, QuickSight에서 해당 테이블에 연결한다.

QuickSight에서 Athena 데이터 소스를 만들 때 Workgroup을 지정할 수 있다. 팀별로 Athena Workgroup을 분리해서 쿼리 비용 모니터링이나 쿼리 결과 위치를 달리 관리하고 있다면 여기서 맞춰줘야 한다.

QuickSight가 Athena를 쓰려면 QuickSight 서비스 계정에 Athena 쿼리 실행 권한과 S3 쿼리 결과 버킷 접근 권한이 있어야 한다. QuickSight 설정 > Security & Permissions에서 S3 버킷 목록을 직접 지정하는 방식이라 이 설정을 빠뜨리면 데이터 소스 연결 단계에서 권한 오류가 난다.

### S3

S3 파일을 직접 데이터 소스로 쓸 수 있는데, 이 경우 매니페스트 파일이 필요하다. JSON 형식의 매니페스트 파일에 대상 파일 경로 목록을 적어두면 QuickSight가 해당 파일들을 읽어 데이터셋을 만든다.

```json
{
  "fileLocations": [
    {
      "URIPrefixes": ["s3://my-bucket/data/2024/"]
    }
  ],
  "globalUploadSettings": {
    "format": "CSV",
    "delimiter": ",",
    "containsHeader": "true"
  }
}
```

파티션이 나뉜 S3 데이터를 쓸 때는 Athena를 중간에 두는 편이 낫다. S3 직접 연결은 파티션 프루닝이 안 되고 전체 파일을 다 읽어서 SPICE로 가져온다. 파일이 많아지면 SPICE 적재 시간이 길어진다.

### Redshift

Redshift는 JDBC로 연결한다. VPC 안에 Redshift가 있으면 QuickSight도 같은 VPC에서 접근할 수 있도록 VPC 연결을 설정해야 한다. QuickSight 설정에서 VPC Connection을 만들고, ENI가 Redshift 보안 그룹에 접근 가능하도록 인바운드 규칙을 열어줘야 한다.

Redshift Serverless를 쓰는 경우도 같은 방식이다. 엔드포인트와 포트, 데이터베이스명, 사용자 계정을 입력하면 된다.

### RDS

RDS도 VPC 연결이 필요하다. Redshift와 같은 방식으로 VPC Connection을 설정하고, RDS 보안 그룹에서 QuickSight ENI의 IP를 허용해야 한다. MySQL, PostgreSQL, Aurora 모두 지원한다.

RDS를 분석 용도로 직접 연결하는 건 권장하지 않는다. 대시보드 조회마다 운영 RDS에 집계 쿼리가 나가면 서비스 트래픽에 영향을 준다. RDS에서 DMS나 ETL로 Redshift나 S3로 데이터를 옮긴 뒤 거기서 연결하는 구조가 더 안전하다.

## SPICE 인메모리 엔진

SPICE는 QuickSight의 자체 인메모리 데이터 저장소다. 데이터 소스에서 데이터를 복사해와서 QuickSight 내부에 저장하고, 이 데이터를 기반으로 대시보드를 렌더링한다.

### 용량 제한

SPICE 용량은 계정 단위로 할당된다. Standard 플랜은 사용자 1명당 10 GB, Enterprise는 사용자 1명당 10 GB를 기본으로 제공하지만 추가 구매가 가능하다. 용량이 부족하면 SPICE 새로고침이 실패한다.

데이터셋이 SPICE 용량을 얼마나 쓰는지는 데이터셋 상세 화면에서 확인할 수 있다. 원본 CSV가 1 GB여도 SPICE에 올리면 압축과 컬럼 기반 저장 덕분에 실제 점유는 훨씬 작은 경우가 많다. 반대로 텍스트 컬럼이 많으면 압축 효율이 떨어진다.

### 새로고침 주기

SPICE는 수동으로 즉시 새로고침하거나, 스케줄을 설정해서 주기적으로 새로고침할 수 있다.

스케줄은 15분 단위가 최소다. 단, 15분 새로고침은 Enterprise 플랜에서만 된다. Standard는 1시간이 최소 주기다.

새로고침 방식은 전체 갱신(Full refresh)이 기본이다. 데이터 소스에서 데이터 전체를 다시 가져와서 기존 SPICE 데이터를 덮어쓴다. 행 수가 적을 때는 괜찮지만 수억 건이 넘어가면 새로고침 한 번에 시간이 꽤 걸린다.

증분 새로고침(Incremental refresh)을 쓰면 지정한 날짜/시간 컬럼 기준으로 변경된 데이터만 가져온다. 단, Athena, Redshift, Aurora 같은 SQL 기반 데이터 소스에서만 지원한다. 설정할 때 어떤 컬럼을 기준으로 할지, 얼마나 되돌아가서 가져올지 (lookback window) 지정해야 한다. 소스 데이터에서 레코드가 수정되는 경우가 있다면 lookback window를 충분히 잡아야 누락이 없다.

### SPICE와 직접 쿼리 비교

대시보드 접속 빈도가 낮고 데이터 실시간성이 중요하지 않으면 SPICE를 쓰는 게 Athena 스캔 비용을 절약하는 데 유리하다. 반대로 데이터가 항상 최신이어야 하고 쿼리가 간단하다면 직접 쿼리가 낫다. Redshift에 직접 연결하는 경우엔 SPICE 없이도 응답이 빠른 편이라 직접 쿼리로 쓰는 경우가 많다.

## 임베디드 대시보드

QuickSight 대시보드를 자사 웹 애플리케이션 안에 심는 기능이다. 고객에게 자체 대시보드를 제공하거나, 내부 어드민에 분석 화면을 붙이는 용도로 쓴다.

임베딩 방식은 크게 두 가지다.

**등록 사용자 임베딩**: QuickSight에 사용자 계정이 있는 경우다. 서버에서 `GenerateEmbedUrlForRegisteredUser` API를 호출해서 임시 URL을 발급받고, 클라이언트에 전달해서 iframe에 넣는다. 임시 URL은 발급 후 5분 내로 사용해야 하고, 세션은 최대 10시간 유지된다.

**익명 사용자 임베딩**: QuickSight 계정 없이 대시보드를 볼 수 있는 방식이다. `GenerateEmbedUrlForAnonymousUser` API를 사용한다. Enterprise 플랜에서만 가능하다.

```python
import boto3

client = boto3.client('quicksight', region_name='ap-northeast-2')

# 등록 사용자 임베딩 URL 발급
response = client.generate_embed_url_for_registered_user(
    AwsAccountId='123456789012',
    SessionLifetimeInMinutes=60,
    UserArn='arn:aws:quicksight:ap-northeast-2:123456789012:user/default/user@example.com',
    ExperienceConfiguration={
        'Dashboard': {
            'InitialDashboardId': 'dashboard-id-here',
            'FeatureConfigurations': {
                'StatePersistence': {'Enabled': True}
            }
        }
    },
    AllowedDomains=['https://myapp.example.com']
)

embed_url = response['EmbedUrl']
```

클라이언트에서는 QuickSight Embedding SDK를 쓰면 iframe을 직접 다루는 것보다 편하다.

```html
<script src="https://unpkg.com/amazon-quicksight-embedding-sdk@2.7.0/dist/quicksight-embedding-js-sdk.min.js"></script>
<div id="dashboardContainer"></div>

<script>
  const { createEmbeddingContext } = QuickSightEmbedding;

  async function embed(url) {
    const embeddingContext = await createEmbeddingContext();
    const dashboard = await embeddingContext.embedDashboard({
      url,
      container: '#dashboardContainer',
      height: '700px',
      width: '100%',
    });
  }

  embed('서버에서 발급받은 embed_url');
</script>
```

임베딩 설정에서 `AllowedDomains`를 반드시 지정해야 한다. 지정하지 않거나 요청 도메인이 목록에 없으면 iframe에서 대시보드가 로드되지 않는다. QuickSight 관리 콘솔의 Manage QuickSight > Domains and Embedding에서도 도메인을 등록해야 한다. 두 곳 모두 설정해야 정상 작동한다.

## 접근 제어

### 사용자와 그룹

QuickSight는 IAM과 별개로 자체 사용자 관리 체계를 가진다. QuickSight에 초대된 사용자만 대시보드에 접근할 수 있다.

사용자 역할은 Admin, Author, Reader 세 가지다. Admin은 QuickSight 설정과 사용자 관리까지 할 수 있다. Author는 데이터셋과 대시보드를 만들고 수정할 수 있다. Reader는 공유받은 대시보드를 볼 수만 있다.

요금 계산 방식이 역할마다 다르다. Author는 월정액이고, Reader는 세션 기반 과금이다. 대시보드 조회만 하는 사람이 많으면 Reader로 관리하는 게 비용을 줄이는 데 유리하다.

그룹을 만들어서 그룹 단위로 대시보드 권한을 줄 수 있다. 사용자가 많아지면 개별 권한 관리보다 그룹으로 묶어서 관리하는 게 낫다. Enterprise에서는 Active Directory 그룹이나 SAML IdP 그룹을 QuickSight 그룹에 매핑할 수 있다.

### 행 수준 보안 (RLS)

같은 대시보드를 보더라도 사용자마다 볼 수 있는 데이터 범위를 다르게 하고 싶을 때 쓴다. 부서별로 자신의 부서 데이터만 보이게 하거나, 영업 담당자마다 자신이 담당하는 지역 데이터만 보이도록 제한할 수 있다.

RLS는 데이터셋 레벨에서 설정한다. 별도 규칙 테이블을 만들어서 사용자(또는 그룹)와 해당 사용자가 볼 수 있는 필터 값을 정의한다. 예를 들어 `region` 컬럼으로 제한하면, 규칙 테이블에 `username: alice, region: Seoul`이라고 적으면 alice는 Seoul 데이터만 볼 수 있다.

```
규칙 테이블 예시:
UserName    | region
------------|--------
alice       | Seoul
bob         | Busan
carol       | Seoul
```

규칙 테이블 자체는 S3나 Redshift 등 데이터 소스에 저장하고, QuickSight에서 그걸 참조하도록 설정한다. 규칙 테이블에 없는 사용자는 기본적으로 아무것도 볼 수 없다. 모두 볼 수 있는 관리자 계정은 규칙 테이블에 포함시키지 않거나, RLS 규칙 자체를 그 사용자에게 적용 안 되도록 예외 처리해야 한다.

RLS는 Enterprise 플랜에서만 된다.

## Standard vs Enterprise

| 항목 | Standard | Enterprise |
|---|---|---|
| SPICE 최소 새로고침 주기 | 1시간 | 15분 |
| AD / SAML SSO | 지원 안 함 | 지원 |
| 행 수준 보안 (RLS) | 지원 안 함 | 지원 |
| 익명 임베딩 | 지원 안 함 | 지원 |
| ML Insights (이상 탐지, 예측) | 지원 안 함 | 지원 |
| QuickSight Q (자연어 질의) | 지원 안 함 | 지원 |
| 전송 중 암호화 | 지원 | 지원 |
| 저장 시 암호화 | 지원 안 함 | 지원 (AWS KMS) |

내부 팀 대시보드 정도면 Standard로도 충분하다. 외부 고객에게 대시보드를 임베딩해서 제공하거나, SSO 연동이 필요하거나, 조직 단위 데이터 접근 제어가 필요하면 Enterprise를 써야 한다.

비용은 Author 1명 기준 Standard가 월 $18, Enterprise가 월 $24다 (서울 리전 기준, 변동 가능). Reader는 Standard가 세션당 $0.30, Enterprise도 동일하게 세션당 $0.30인데 월 최대 $5로 캡이 있다.
