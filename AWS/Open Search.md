


# 아마존 OpenSearch 서비스란?
- Amazon OpenSearch Service는 AWS 클라우드에서 OpenSearch 클러스터를 쉽게 배포, 운영 및 확장할 수 있는 관리형 서비스입니다.
- 아마존 OpenSearch 서비스는 레거시 Elasticsearch OSS (소프트웨어의 최종 오픈 소스 버전인 최대 7.10) 를 지원합니다.
-  클러스터를 생성할 때 어떤 검색 엔진을 사용할지 선택할 수 있습니다.

OpenSearch로그 분석, 실시간 애플리케이션 모니터링, 클릭스트림 분석과 같은 사용 사례를 위한 완전한 오픈 소스 검색 및 분석 엔진입니다. 자세한 내용은 설명서를 참조하십시오. OpenSearch

Amazon OpenSearch 서비스는 OpenSearch 클러스터의 모든 리소스를 프로비저닝하고 실행합니다. 또한 장애가 발생한 OpenSearch 서비스 노드를 자동으로 탐지하고 교체하여 자체 관리형 인프라와 관련된 오버헤드를 줄입니다. API를 한 번만 호출하거나 콘솔에서 몇 번만 클릭하여 클러스터를 조정할 수 있습니다.


OpenSearch 서비스 사용을 시작하려면 클러스터와 동일한 OpenSearch 서비스 도메인을 생성해야 합니다. OpenSearch 클러스터의 각 EC2 인스턴스는 하나의 OpenSearch 서비스 노드 역할을 합니다.

OpenSearch 서비스 콘솔을 사용하여 몇 분 만에 도메인을 설정하고 구성할 수 있습니다. 프로그래밍 방식 액세스를 선호하는 경우 AWS CLI 또는 AWS SDK를 사용할 수 있습니다.

아마존 OpenSearch 서비스의 특징

OpenSearch 서비스에는 다음과 같은 기능이 포함됩니다.

크기 조정

비용 효율적인 Graviton 인스턴스를 포함한 다양한 CPU, 메모리 및 스토리지 용량 구성(인스턴스 유형이라고 함)

최대 3PB의 연결된 스토리지

읽기 전용 데이터를 UltraWarm위한 비용 효율적인 콜드 스토리지

보안

AWS Identity and Access Management(IAM) 액세스 제어

Amazon VPC 및 VPC 보안 그룹을 사용하는 쉬운 통합

저장 데이터 암호화 및 node-to-node 암호화

대시보드를 위한 Amazon Cognito, HTTP 기본 또는 SAML 인증 OpenSearch

인덱스 수준, 문서 수준 및 필드 수준 보안

감사 로그

Dashboards 멀티테넌시

안정성

리소스를 위한 여러 지리적 위치(리전 및 가용 영역이라고 함)입니다.

동일한 AWS 리전의 가용 영역 두 개 또는 세 개에 노드 할당(다중 AZ)

클러스터 관리 작업 부담을 줄여주는 전용 프라이머리 노드

서비스 도메인의 백업 및 복원을 위한 자동 스냅샷 OpenSearch

유연성

비즈니스 인텔리전스(BI) 애플리케이션과의 통합을 위한 SQL 지원

검색 결과 개선을 위한 사용자 지정 패키지

유명 서비스와의 통합

대시보드를 사용한 OpenSearch 데이터 시각화

Amazon과의 통합으로 OpenSearch 서비스 도메인 CloudWatch 메트릭을 모니터링하고 경보를 설정할 수 있습니다.

서비스 도메인에 대한 구성 API 호출을 감사하기 AWS CloudTrail 위한 통합 OpenSearch

스트리밍 데이터를 서비스로 로드하기 위해 Amazon S3, Amazon Kinesis 및 Amazon DynamoDB와의 통합 OpenSearch

데이터가 특정 임계값을 초과하는 경우 SNS의 알림

아마존 서버리스 OpenSearch

Amazon OpenSearch 서버리스는 아마존 서비스를 위한 온디맨드, 자동 크기 조정, 서버리스 구성입니다. OpenSearch 서버리스는 클러스터를 프로비저닝, 구성 및 튜닝하는 데 따르는 운영상의 복잡성을 제거합니다. OpenSearch 자세한 정보는 아마존 OpenSearch 서버리스을 참조하세요.

OpenSearch 아마존 인제스티션

Amazon OpenSearch Ingestion은 데이터 프레퍼 기반의 완전 관리형 데이터 수집기로, Amazon OpenSearch 서비스 도메인과 서버리스 컬렉션에 실시간 로그 및 추적 데이터를 제공합니다. OpenSearch 이를 통해 다운스트림 분석 및 시각화를 위해 데이터를 필터링, 강화, 변환, 정규화 및 집계할 수 있습니다. 자세한 내용은 Amazon Ingestion을 참조하십시오. OpenSearch

지원되는 버전의 OpenSearch 및 Elasticsearch는

OpenSearch 서비스는 현재 다음 OpenSearch 버전을 지원합니다.

2.9, 2.7, 2.5, 2.3, 1.3, 1.2, 1.1, 1.0

OpenSearch 이 서비스는 다음과 같은 레거시 Elasticsearch OSS 버전도 지원합니다.

7.10, 7.9, 7.8, 7.7, 7.4, 7.1

6.8, 6.7, 6.5, 6.4, 6.3, 6.2, 6.0

5.6, 5.5, 5.3, 5.1

2.3

1.5

자세한 내용은 아마존 OpenSearch 서비스에서 지원되는 작업, 아마존 서비스의 엔진 버전별 기능 OpenSearch , 아마존 OpenSearch 서비스의 엔진 버전별 플러그인 섹션을 참조하세요.

새 OpenSearch 서비스 프로젝트를 시작하는 경우 지원되는 최신 버전을 선택하는 것이 좋습니다. OpenSearch Elasticsearch 구 버전을 사용하는 기존 도메인이 있으면 그 도메인을 유지하거나 데이터를 마이그레이션할 수 있습니다. 자세한 정보는 아마존 OpenSearch 서비스 도메인 업그레이드을 참조하세요.

아마존 OpenSearch 서비스 요금

OpenSearch 서비스의 경우 EC2 인스턴스 사용 시간당 및 인스턴스에 연결된 EBS 스토리지 볼륨의 누적 크기에 대해 요금을 지불합니다. 이때 표준 AWS 데이터 전송 요금도 적용됩니다.

하지만 알아둘 만한 데이터 전송 예외가 몇 가지 존재합니다. 도메인이 여러 가용 영역을 사용하는 경우 OpenSearch 서비스는 가용 영역 간 트래픽에 대해 요금을 청구하지 않습니다. 샤드 할당 및 재조정 중에 도메인 내에서 상당한 데이터 전송이 발생합니다. OpenSearch 서비스는 이 트래픽에 대한 계량기나 청구서를 제공하지 않습니다. 마찬가지로, OpenSearch 서비스에서는 UltraWarm/cold 노드와 Amazon S3 간의 데이터 전송에 대해 요금을 청구하지 않습니다.

전체 요금 세부 정보는 Amazon OpenSearch 서비스 요금을 참조하십시오. 구성 변경 도중 발생하는 변경 사항에 대한 자세한 내용은 구성 변경 비용 섹션을 참조하세요.

아마존 OpenSearch 서비스 시작하기

아직 계정이 없는 경우 AWS 계정에 가입하여 시작합니다. 계정을 설정한 후 Amazon OpenSearch 서비스 시작 자습서를 완료하십시오. 이 서비스에 대해 알아보는 중 추가 정보가 필요한 경우 다음 소개 주제를 참조하세요.

도메인 생성

워크로드에 맞게 도메인 크기 조정

도메인 액세스 정책 또는 세분화된 액세스 제어를 사용하여 도메인에 대한 액세스 제어

수동으로 또는 다른 AWS 서비스로부터 데이터 인덱싱

OpenSearch 대시보드를 사용하여 데이터를 검색하고 시각화를 생성할 수 있습니다.

자체 OpenSearch 관리형 클러스터에서 OpenSearch 서비스로 마이그레이션하는 방법에 대한 자세한 내용은 을 참조하십시오. 자습서: Amazon으로 마이그레이션OpenSearch서비스

``
출처
https://docs.aws.amazon.com/ko_kr/opensearch-service/latest/developerguide/what-is.html
``