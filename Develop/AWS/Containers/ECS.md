---
title: AWS ECS (Elastic Container Service)
tags: [aws, containers, ecs, docker, orchestration]
updated: 2025-11-25
---

# AWS ECS (Elastic Container Service)

## 개요

- **정의**
  - AWS에서 제공하는 **완전 관리형 컨테이너 오케스트레이션 서비스**
  - Docker 컨테이너를 **실행·관리·스케일링**하기 위한 AWS 네이티브 플랫폼
- **핵심 철학**
  - 인프라(서버, 클러스터, 패치)를 AWS가 관리 → **개발자는 컨테이너와 비즈니스 로직에만 집중**
- **특징 요약**
  - AWS 서비스(IAM, VPC, ALB, CloudWatch 등)와의 **깊은 통합**
  - **Fargate**를 통한 서버리스 실행 옵션
  - **사용량 기반 과금**으로 비용 효율적

## ECS vs Kubernetes 한눈에 보기

- **관리 관점**
  - ECS: AWS가 인프라를 관리 → 운영 난이도 낮음
  - K8s: 클러스터·노드·컨트롤 플레인까지 직접 관리 필요
- **AWS 통합**
  - ECS: AWS 전용, 서비스 간 통합이 매우 자연스럽고 설정이 단순
  - K8s(EKS): AWS 위에서 동작하지만, 여전히 K8s 자체 설정 필요
- **학습 곡선**
  - ECS: AWS 경험자 기준 진입장벽 낮음
  - K8s: 개념/리소스 종류가 많아 학습 비용 큼
- **유연성·멀티 클라우드**
  - ECS: AWS 전용, 커스터마이징은 AWS 범위 내
  - K8s: 멀티 클라우드/온프레미스 등 **클라우드 중립성** 강함
- **비용**
  - ECS: 관리형 서비스 특성상 운영 비용 예측이 쉬움
  - K8s: 클러스터 관리/운영 인력 비용이 추가로 발생할 수 있음

## ECS 아키텍처 구성 요소 요약

### Cluster (클러스터)
- ECS의 **최상위 논리 단위**
- 태스크·서비스가 실행되는 범위를 정의
- 하나의 클러스터 안에 여러 서비스가 공존 가능

### Task Definition (태스크 정의)
- 컨테이너 실행에 대한 **스펙(청사진)**
  - 이미지, CPU/메모리, 포트, 환경 변수, 볼륨, 네트워크 설정 등
- **버전 관리** 가능 → 새 버전 정의 후 점진적 배포(Rolling 등)에 사용

### Task (태스크)
- 태스크 정의의 **실행 인스턴스**
- 하나 이상의 컨테이너로 구성, 서로 격리된 환경에서 실행
- 서비스에 의해 유지·재시작되며, 일시적(ephemeral) 특성을 가짐

### Service (서비스)
- **원하는 태스크 개수(desired count)**를 유지하는 관리 레이어
- 주요 역할
  - 태스크 헬스 체크 및 자동 교체
  - ALB/NLB와 연동한 트래픽 분산
  - 오토 스케일링(부하 기반 태스크 수 증감)

### Container Instance (컨테이너 인스턴스)
- EC2 모드에서 태스크가 실제로 올라가는 **EC2 인스턴스**
- **ECS Agent**가 설치되어 ECS와 통신
- Fargate 사용 시에는 이 레이어가 추상화되어 직접 관리 필요 없음

## ECS 실행 모드 정리

### 1) Fargate (서버리스 모드)

- **특징**
  - 서버 띄우기·패치·보안 업데이트 등 **모든 인프라 관리를 AWS가 담당**
  - 태스크 단위로 vCPU/메모리 지정 → 그만큼만 과금
  - 태스크별로 격리된 환경 제공 → 보안성↑
- **장점**
  - 인프라를 전혀 신경 쓰고 싶지 않을 때 최적
  - 워크로드 변화에 따라 **자동 스케일링** 연계가 쉬움
- **대표 사용 사례**
  - 마이크로서비스
  - 배치 작업
  - 개발/테스트 환경
  - 중소 규모 서비스

### 2) EC2 모드 (인프라 관리 모드)

- **특징**
  - ECS는 오케스트레이션만, **EC2 인프라는 직접 관리**
  - 인스턴스 타입/AMI/네트워크/스토리지 등을 모두 커스터마이징 가능
- **장점**
  - 예약 인스턴스·스팟 인스턴스로 **공격적인 비용 최적화** 가능
  - GPU/특수 하드웨어, 커스텀 에이전트/드라이버 등 특수 요구사항 대응
- **단점**
  - 패치, 용량 계획, 모니터링 등 운영 부담이 큼
- **대표 사용 사례**
  - 장기 실행/대용량 워크로드
  - 특수 하드웨어 요구
  - 비용 최적화가 매우 중요한 환경

### 3) ECS Anywhere (하이브리드 모드)

- **역할**
  - 온프레미스나 다른 클라우드의 서버에 **ECS 태스크를 배치**할 수 있게 함
- **장점**
  - 기존 인프라를 유지하면서도 ECS의 관리 경험 활용
  - AWS 콘솔에서 온프레미스·클라우드를 일관되게 관리
- **사용 사례**
  - 데이터 거버넌스/규제 등으로 데이터가 온프레미스에 있어야 하는 경우
  - 레거시 시스템과 클라우드 간 **하이브리드 아키텍처** 구성

## ECS의 핵심 장점 요약

### 1) AWS 생태계와의 깊은 통합

- **IAM**
  - 태스크 단위 IAM Role 부여 가능
  - 최소 권한 원칙(least privilege)을 구현하기 용이
- **VPC 네트워킹**
  - 태스크별 ENI 할당 가능 → 네트워크 격리 강화
  - 보안 그룹/서브넷과 자연스럽게 연동
- **로드 밸런서(ALB/NLB)**
  - 서비스 생성 시 자동으로 타겟 그룹/헬스 체크 연계
  - 포트 매핑/동적 포트에도 적합
- **CloudWatch**
  - 메트릭·로그·알람을 기본적으로 연동
  - 별도 에이전트 구축 없이도 기본 모니터링 가능

### 2) 간편한 배포·운영

- **배포**
  - Docker 이미지 빌드 → 태스크 정의 업데이트 → 서비스에 적용
  - 콘솔·CLI·CD 파이프라인 어디서든 쉽게 구성
- **기존 Docker 환경 재사용**
  - Docker Compose 파일을 ECS로 변환(ECS CLI 등)해 마이그레이션 가능
- **무중단 배포**
  - Rolling / Blue-Green 배포 전략을 쉽게 적용 가능

### 3) 비용 효율성

- **Fargate Spot**
  - 중단 허용 워크로드에 대해 최대 약 70% 수준까지 비용 절감
- **오토 스케일링**
  - 실제 트래픽 기반으로 태스크 수 조절 → 유휴 리소스 비용 감소
- **EC2 예약 인스턴스/스팟**
  - 장기 실행 서비스에 대해 큰 폭의 비용 절감

### 4) 보안·컴플라이언스

- **IAM + VPC + SG 조합으로 다층 방어**
- **Secrets Manager/Parameter Store**와 연동한 시크릿 관리
- AWS가 제공하는 각종 컴플라이언스(SOC, PCI DSS, HIPAA 등)를 그대로 활용 가능

## ECS 사용 시나리오 정리

### 마이크로서비스 아키텍처

- 각 마이크로서비스를 **별도 ECS 서비스**로 분리
- Service Connect / AWS Cloud Map으로 **서비스 디스커버리·통신 관리**
- 독립 배포·독립 스케일링·장애 격리 구현이 쉬움

### 웹 애플리케이션 호스팅

- ALB + ECS 조합이 기본 패턴
  - ALB → 여러 태스크로 트래픽 분산
  - 헬스 체크 실패 태스크는 자동 제외

### 배치 작업 처리

- Fargate 기반으로 **필요할 때만 태스크 실행 → 종료 후 비용 0**
- EventBridge 스케줄러와 연동해 크론성 배치 작업 구현

### CI/CD 파이프라인

- CodePipeline + CodeBuild + CodeDeploy 조합으로
  - 코드 변경 → 이미지 빌드 → ECR 푸시 → ECS 서비스 업데이트까지 자동화

## ECS 운영 모범 사례 (Best Practices)

### 아키텍처 설계

- **단일 책임 원칙**
  - 하나의 태스크 정의/서비스는 하나의 역할에 집중
- **Stateless 설계**
  - 애플리케이션 컨테이너는 상태를 가지지 않도록
  - 상태는 DB, 캐시, 외부 스토리지(S3 등)에 저장
- **헬스 체크**
  - 애플리케이션 레벨 `/health` 엔드포인트 등 제공
  - ECS/ALB가 이를 기반으로 정상/비정상 판단

### 보안

- **IAM 최소 권한**
  - 태스크 Role에 필요한 권한만 부여
- **네트워크 격리**
  - 퍼블릭/프라이빗 서브넷 분리
  - 보안 그룹으로 인바운드/아웃바운드 최소화
- **시크릿 관리**
  - 앱 코드에 비밀번호/키를 하드코딩하지 않고
  - Secrets Manager / SSM Parameter Store에서 주입

### 모니터링·관찰 가능성

- **Container Insights**
  - CPU/메모리/네트워크/디스크 메트릭 수집
- **구조화 로그(JSON)**
  - 로그 분석/검색에 유리하도록 필드 단위 로그 작성
- **알람 설정**
  - CPU/메모리 사용률, 에러율, 태스크 재시작 횟수 등에 임계값 지정

### 비용 최적화

- Fargate Spot, 스팟 인스턴스 적극 활용 (중단 허용 워크로드)
- CloudWatch 기반으로 **리소스 할당량 지속 조정**
- 오토 스케일링 정책을 실제 트래픽 패턴에 맞게 튜닝

## ECS 고급 기능 한 줄 요약

- **Service Connect**: 서비스 간 통신/서비스 디스커버리 단순화
- **ECS Exec**: 실행 중 컨테이너에 직접 접속해 디버깅
- **Capacity Providers**: Fargate + Fargate Spot 등 여러 용량 소스를 조합해 사용
- **Task Placement Strategies**: 태스크를 어떤 인스턴스에 어떻게 분배할지 전략적으로 제어

## 결론·요약

- **ECS는 "AWS에서 컨테이너를 가장 쉽게 운영하는 방법"에 가까운 서비스**
- Kubernetes보다 **운영 난이도가 낮고**, AWS 서비스와의 통합이 강력함
- 인프라 관리 부담을 줄이고 싶고, AWS 중심으로 운영한다면 ECS/Fargate 조합이 매우 실용적
- 멀티 클라우드·고도의 커스터마이징이 필요하면 Kubernetes(EKS)도 함께 비교 검토

## 참조

### 관련 문서

- [Kubernetes 심화 전략](../../DevOps/Kubernetes/Kubernetes_심화_전략.md) - Kubernetes와 ECS 비교
- [배포 전략](../../Framework/Node/배포/배포_전략.md) - 컨테이너 배포 전략
- [Docker Compose](../../DevOps/Kubernetes/Docker/Docker_Compose.md) - 로컬 개발 환경 구성
- [CI/CD 고급 패턴](../../DevOps/CI_CD/고급_CI_CD_패턴.md) - ECS 배포 파이프라인
- [AWS 고가용성 설계 전략](../고가용성/고가용성_설계_전략.md) - ECS 고가용성 구성
- [AWS 모니터링 및 알람 전략](../모니터링/모니터링_및_알람_전략.md) - ECS 모니터링

---

### 참고 자료

- AWS ECS 공식 문서: https://docs.aws.amazon.com/ecs/
- AWS ECS 가격 정책: https://aws.amazon.com/ecs/pricing/
- ECS 모범 사례 가이드: https://docs.aws.amazon.com/ecs/latest/bestpracticesguide/
- AWS Well-Architected Framework - 컨테이너: https://aws.amazon.com/architecture/well-architected/
- ECS Workshop: https://ecsworkshop.com/
- AWS Fargate 가이드: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html
- ECS Service Connect: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-connect.html
- ECS Exec: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-exec.html
