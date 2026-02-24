---
title: AWS EKS (Elastic Kubernetes Service)
tags: [aws, kubernetes, containers, eks, orchestration, k8s]
updated: 2026-01-18
---

# AWS EKS (Elastic Kubernetes Service)

## 개요

AWS EKS는 AWS에서 Kubernetes 클러스터를 실행할 수 있는 관리형 서비스다. Kubernetes의 복잡한 컨트롤 플레인 관리를 AWS가 대신 해주고, 개발자는 애플리케이션 배포와 워커 노드 관리에만 집중하면 된다.

### Kubernetes가 필요한 이유

전통적인 서버 환경에서는 애플리케이션을 배포하고 관리하는 것이 복잡했다.

**과거의 문제점:**
- 여러 서버에 애플리케이션을 수동으로 배포해야 했다
- 서버 한 대가 죽으면 수동으로 복구해야 했다
- 트래픽이 증가하면 수동으로 서버를 추가해야 했다
- 서버마다 설정이 달라 관리가 어려웠다
- 리소스 활용률이 낮았다. CPU 10%만 사용하는 서버가 많았다

**컨테이너의 등장:**
Docker가 등장하면서 애플리케이션을 컨테이너로 패키징할 수 있게 되었다. 컨테이너는 애플리케이션과 필요한 모든 것(라이브러리, 설정 파일 등)을 하나로 묶는다. 어디서나 동일하게 실행된다.

**하지만 새로운 문제:**
컨테이너가 많아지면서 새로운 문제가 생겼다. 수백, 수천 개의 컨테이너를 어떻게 관리할까? 컨테이너가 죽으면 누가 다시 시작시킬까? 트래픽이 증가하면 컨테이너를 자동으로 늘릴 수 있을까?

**Kubernetes의 등장:**
Kubernetes는 이런 문제를 해결하는 컨테이너 오케스트레이션 플랫폼이다. Google이 사내에서 사용하던 Borg 시스템을 오픈소스로 공개한 것이다.

**Kubernetes가 하는 일:**
- 컨테이너를 어느 서버에 배치할지 자동으로 결정한다
- 컨테이너가 죽으면 자동으로 재시작한다
- 트래픽에 따라 컨테이너 개수를 자동으로 조절한다
- 여러 컨테이너에 트래픽을 분산한다
- 무중단 배포를 수행한다
- 설정과 비밀 정보를 안전하게 관리한다

### EKS가 해결하는 문제

Kubernetes는 강력하지만 직접 운영하기는 어렵다.

**직접 운영할 때의 어려움:**
- 마스터 노드를 3개 이상 구성해야 한다. 고가용성을 위해서다
- etcd 클러스터를 별도로 구성하고 백업해야 한다
- 마스터 노드가 죽으면 수동으로 복구해야 한다
- Kubernetes 버전 업그레이드가 복잡하다. 한 단계씩만 올릴 수 있다
- 보안 패치를 주기적으로 적용해야 한다
- 마스터 노드 모니터링과 로깅을 구성해야 한다

**EKS가 제공하는 것:**
- 마스터 노드(컨트롤 플레인)를 AWS가 관리한다. 개발자는 접근조차 할 수 없다
- 3개의 가용 영역에 자동으로 분산 배치된다
- 자동 백업과 복구를 제공한다
- Kubernetes 버전 업그레이드를 콘솔 클릭 한 번으로 수행한다
- 보안 패치를 자동으로 적용한다
- CloudWatch와 자동 연동된다

**개발자가 관리하는 것:**
- 워커 노드(실제 컨테이너가 실행되는 서버)
- 애플리케이션 배포
- Kubernetes 리소스 관리

## ECS vs EKS 비교

실무에서 ECS와 EKS 중 선택할 때 고려하는 항목들이다. 둘 다 컨테이너를 실행하는 서비스지만 접근 방식이 다르다.

### 관리 복잡도

**ECS의 경우:**
ECS는 AWS 네이티브 서비스다. AWS 콘솔에 익숙하다면 바로 사용할 수 있다. Task Definition이라는 JSON 파일만 작성하면 컨테이너를 실행할 수 있다. Kubernetes를 몰라도 된다.

예를 들어, Node.js 애플리케이션을 배포한다고 하자. ECS에서는 다음만 정의하면 된다:
- 어떤 Docker 이미지를 사용할지
- CPU와 메모리는 얼마나 필요한지
- 어떤 포트를 열지
- 환경 변수는 무엇인지

이 정보를 Task Definition에 작성하고, Service를 만들면 끝이다. AWS가 알아서 컨테이너를 실행하고 관리한다.

**EKS의 경우:**
EKS는 표준 Kubernetes다. Kubernetes 지식이 필요하다. Pod, Deployment, Service, Ingress, ConfigMap, Secret 등 여러 개념을 알아야 한다.

같은 Node.js 애플리케이션을 EKS에 배포하려면:
- Deployment YAML 파일을 작성한다. 컨테이너 스펙을 정의한다
- Service YAML 파일을 작성한다. 네트워크 접근을 정의한다
- Ingress YAML 파일을 작성한다. 외부 접근을 정의한다
- ConfigMap을 만든다. 설정 값을 저장한다
- Secret을 만든다. 비밀 정보를 저장한다

kubectl 명령어로 이 파일들을 클러스터에 적용한다. ECS보다 복잡하지만, Kubernetes의 모든 기능을 사용할 수 있다.

**학습 시간:**
- ECS: AWS 경험이 있다면 1-2일이면 기본을 익힌다
- EKS: Kubernetes를 처음 배운다면 2-4주는 필요하다

**실무 팁:**
팀에 Kubernetes 경험이 없고, AWS만 사용한다면 ECS로 시작한다. 빠르게 배포할 수 있다. 나중에 필요하면 EKS로 이전할 수 있다.

### 이식성 (다른 클라우드로 옮기기)

**ECS의 제약:**
ECS는 AWS에만 존재한다. 다른 클라우드나 온프레미스로 옮기려면 전체를 다시 작성해야 한다.

예를 들어, GCP로 이전한다면:
- ECS Task Definition을 GCP Cloud Run 설정으로 변환해야 한다
- ECS Service를 GCP의 서비스로 변환해야 한다
- IAM Role을 GCP의 Service Account로 변환해야 한다
- 모든 설정을 처음부터 다시 작성한다

**EKS의 유연성:**
EKS는 표준 Kubernetes다. Kubernetes YAML 파일은 어디서나 동일하게 작동한다.

GCP로 이전한다면:
- GKE(Google Kubernetes Engine) 클러스터를 만든다
- 기존 YAML 파일을 그대로 사용한다
- kubectl apply 명령어로 배포한다
- 일부 AWS 전용 기능만 수정하면 된다

Azure, 온프레미스, 다른 Kubernetes 서비스로도 쉽게 이전할 수 있다.

**멀티 클라우드:**
여러 클라우드를 동시에 사용하는 경우 EKS가 유리하다. AWS, GCP, Azure에 동일한 애플리케이션을 배포할 수 있다. Kubernetes YAML 파일을 재사용한다.

**실무 팁:**
현재는 AWS만 사용하지만 나중에 다른 클라우드도 고려한다면 EKS를 선택한다. 하지만 대부분의 회사는 한 클라우드만 사용한다. 이식성이 중요한지 먼저 생각해본다.

### AWS 서비스 통합

**ECS의 강점:**
ECS는 AWS 네이티브 서비스다. 다른 AWS 서비스와 깊게 통합되어 있다.

**자동 연동:**
- IAM Role을 Task에 직접 부여한다. 별도 설정이 필요 없다
- ALB Target Group에 자동으로 등록된다
- CloudWatch Logs로 로그가 자동으로 전송된다
- Secrets Manager에서 비밀 정보를 자동으로 주입한다
- VPC 보안 그룹을 Task 단위로 적용한다

모든 것이 AWS 콘솔에서 설정된다. 별도 도구가 필요 없다.

**EKS의 경우:**
EKS도 AWS 서비스와 통합되지만 추가 설정이 필요하다.

**추가 설정 필요:**
- IRSA(IAM Roles for Service Accounts)를 설정해야 Pod에 IAM 역할을 부여할 수 있다
- AWS Load Balancer Controller를 설치해야 ALB를 생성할 수 있다
- Fluent Bit를 설치해야 로그를 CloudWatch Logs로 보낼 수 있다
- CSI 드라이버를 설치해야 EBS, EFS를 사용할 수 있다

Helm이나 kubectl로 이런 도구들을 설치하고 설정해야 한다. ECS보다 복잡하다.

**실무 팁:**
AWS 서비스를 많이 사용하고, 빠른 통합이 중요하다면 ECS가 편하다. EKS는 초기 설정은 복잡하지만, 한 번 설정하면 강력한 기능을 사용할 수 있다.

### 기능과 확장성

**ECS의 기능:**
ECS는 기본 기능으로 대부분의 요구사항을 충족한다. 컨테이너를 실행하고, 스케일링하고, 로드 밸런싱하는 것이 주 기능이다.

**제공하는 기능:**
- 컨테이너 실행과 관리
- Auto Scaling
- 로드 밸런싱 (ALB, NLB)
- 롤링 업데이트
- Health Check
- 로그와 모니터링

**제한사항:**
- 고급 배포 전략(Canary, Blue-Green)은 CodeDeploy와 연동해야 한다
- Service Mesh를 사용하려면 App Mesh를 별도로 설정해야 한다
- 커스터마이징 옵션이 제한적이다

**EKS의 기능:**
EKS는 Kubernetes 생태계의 모든 도구를 사용할 수 있다. 검증된 오픈소스 도구가 많다.

**사용 가능한 도구:**
- **Helm**: 패키지 관리자. 애플리케이션을 패키지로 배포한다
- **Istio, Linkerd**: Service Mesh. 트래픽 제어, 보안, 관찰성
- **Prometheus, Grafana**: 모니터링과 시각화
- **Fluentd, Fluent Bit**: 로그 수집과 전송
- **Cert-Manager**: SSL 인증서 자동 관리
- **ArgoCD, Flux**: GitOps 기반 배포
- **Keda**: 이벤트 기반 Auto Scaling
- **Kubecost**: 비용 분석

이런 도구들은 Kubernetes에서 바로 작동한다.

**커스터마이징:**
Kubernetes는 CRD(Custom Resource Definition)로 확장할 수 있다. 필요한 기능을 직접 만들 수 있다. 예를 들어, 자체 스케일링 로직이나 배포 전략을 구현할 수 있다.

**실무 팁:**
간단한 웹 애플리케이션이라면 ECS면 충분하다. 복잡한 마이크로서비스 아키텍처이거나, Service Mesh가 필요하거나, GitOps를 도입하려면 EKS가 적합하다.

### 비용

**ECS 비용:**
컨트롤 플레인 비용이 없다. 실행하는 리소스(EC2 또는 Fargate)만 비용이 발생한다.

**예시:**
- Fargate로 2 vCPU, 4GB 메모리를 24시간 실행: 약 $45/월
- EC2 t3.medium 3대를 24시간 실행: 약 $90/월
- 총: 약 $90-135/월

**EKS 비용:**
클러스터당 시간당 $0.10 비용이 발생한다. 월 약 $72다. 워커 노드 비용은 별도다.

**예시:**
- EKS 클러스터: $72/월
- EC2 t3.medium 3대를 24시간 실행: 약 $90/월
- 총: 약 $162/월

**비용 차이:**
소규모 서비스에서는 ECS가 더 저렴하다. 클러스터 비용이 없기 때문이다. 하지만 서비스가 많아지면 하나의 EKS 클러스터에 여러 서비스를 배포할 수 있어서 비용 차이가 줄어든다.

**실무 팁:**
소규모 스타트업이나 단일 서비스라면 ECS가 비용 면에서 유리하다. 여러 마이크로서비스를 운영하는 중대규모 서비스라면 EKS의 클러스터 비용이 크게 부담되지 않는다.

### 선택 기준 정리

**ECS를 선택하는 경우:**
- AWS만 사용하고 다른 클라우드로 이전할 계획이 없다
- 빠르게 시작하고 싶다. 학습 시간을 최소화하고 싶다
- 간단한 마이크로서비스 아키텍처다. 3-5개 정도의 서비스
- Kubernetes 전문 인력이 없다. 채용도 어렵다
- 소규모 팀이다. 2-5명 정도의 개발자
- 빠른 AWS 서비스 통합이 중요하다

**EKS를 선택하는 경우:**
- 멀티 클라우드 또는 하이브리드 클라우드 전략이다
- 이미 Kubernetes를 사용하고 있다. 온프레미스에서 AWS로 마이그레이션한다
- 복잡한 마이크로서비스 아키텍처다. 10개 이상의 서비스
- Service Mesh, GitOps 등 Kubernetes 생태계 도구를 사용하고 싶다
- Kubernetes 전문 인력이 있거나 채용할 수 있다
- 세밀한 제어와 커스터마이징이 필요하다

**실무 사례:**
- **스타트업 초기**: ECS로 시작한다. 빠르게 제품을 출시하는 것이 중요하다
- **성장기**: 서비스가 10개를 넘어가면 EKS 전환을 고려한다
- **대기업**: 처음부터 EKS를 선택하는 경우가 많다. 표준화와 이식성이 중요하다

## EKS 아키텍처

EKS 클러스터는 크게 컨트롤 플레인과 데이터 플레인으로 나뉜다.

### 컨트롤 플레인 (AWS가 관리)

컨트롤 플레인은 Kubernetes 클러스터의 두뇌 역할을 한다. 모든 결정을 내리고, 상태를 관리하고, 명령을 처리한다.

**주요 구성 요소:**

**1. API Server:**
모든 요청이 여기로 들어온다. kubectl 명령어, 애플리케이션 배포, 설정 변경 등 모든 것이 API Server를 거친다.

**동작 과정:**
- 개발자가 `kubectl apply -f deployment.yaml` 명령을 실행한다
- kubectl이 API Server에 HTTPS 요청을 보낸다
- API Server가 요청을 검증한다. 인증, 권한, 유효성 검사
- 요청이 유효하면 etcd에 저장한다
- 다른 컴포넌트에 알림을 보낸다

API Server는 클러스터의 유일한 진입점이다. 모든 컴포넌트가 API Server를 통해 통신한다.

**2. etcd:**
클러스터의 모든 데이터를 저장하는 분산 키-값 저장소다. 클러스터의 모든 상태가 여기에 저장된다.

**저장되는 데이터:**
- 모든 Kubernetes 리소스 (Pod, Service, Deployment 등)
- 설정 정보
- 네트워크 정책
- Secret과 ConfigMap
- 클러스터 상태

etcd는 매우 중요하다. etcd가 없으면 클러스터의 모든 정보가 사라진다. EKS는 etcd를 3개의 가용 영역에 분산 배치하고 자동으로 백업한다.

**3. Scheduler:**
새로운 Pod를 어느 노드에 배치할지 결정한다.

**결정 과정:**
1. API Server가 "새 Pod가 생성되었어요"라고 알린다
2. Scheduler가 모든 노드의 상태를 확인한다
3. 각 노드의 CPU, 메모리, 디스크 사용량을 본다
4. Pod의 요구사항을 확인한다. 필요한 CPU, 메모리
5. Pod의 제약사항을 확인한다. 특정 노드에만 배치해야 하는지
6. 가장 적합한 노드를 선택한다
7. API Server에 "이 노드에 배치하세요"라고 알린다

Scheduler는 여러 요소를 고려한다:
- 리소스 사용률: CPU와 메모리가 충분한지
- Node Selector: Pod가 특정 라벨을 가진 노드에만 배치되어야 하는지
- Affinity: 특정 Pod끼리 같은 노드에 배치되어야 하는지
- Anti-Affinity: 특정 Pod끼리 다른 노드에 배치되어야 하는지
- Taints and Tolerations: 노드가 특정 Pod만 받아들이는지

**4. Controller Manager:**
클러스터를 원하는 상태로 유지한다. 여러 컨트롤러의 집합이다.

**주요 컨트롤러:**

**Deployment Controller:**
- Deployment를 모니터링한다
- 원하는 Pod 개수와 실제 Pod 개수를 비교한다
- 부족하면 새 Pod를 생성한다
- 초과하면 Pod를 삭제한다

예를 들어, Deployment에 replicas: 3이라고 설정했는데 Pod가 하나 죽었다면, Deployment Controller가 자동으로 새 Pod를 만든다.

**ReplicaSet Controller:**
- ReplicaSet을 모니터링한다
- Pod 개수를 유지한다

**Node Controller:**
- 노드를 모니터링한다
- 노드가 응답하지 않으면 NotReady로 표시한다
- 일정 시간 후 해당 노드의 Pod를 다른 노드로 옮긴다

**이 모든 것을 AWS가 관리한다:**
- 개발자는 컨트롤 플레인에 접근할 수 없다
- SSH로 로그인할 수 없다
- 직접 설정을 변경할 수 없다
- AWS가 알아서 관리한다

**고가용성:**
EKS는 컨트롤 플레인을 3개의 가용 영역에 분산 배치한다. 한 가용 영역이 죽어도 클러스터는 정상 작동한다.

**자동 복구:**
컨트롤 플레인 컴포넌트에 문제가 생기면 AWS가 자동으로 복구한다. 개발자는 알지도 못한다.

**버전 업그레이드:**
Kubernetes 버전 업그레이드는 AWS 콘솔에서 클릭 한 번이다. AWS가 안전하게 업그레이드를 수행한다. 다운타임이 없다.

### 데이터 플레인 (개발자가 관리)

데이터 플레인은 실제 애플리케이션이 실행되는 워커 노드다. 개발자가 관리한다.

**노드 타입:**

**1. 관리형 노드 그룹:**
AWS가 노드의 생명주기를 관리하지만, EC2 인스턴스는 개발자 계정에 생성된다.

**AWS가 해주는 것:**
- EC2 인스턴스를 자동으로 생성한다
- 최신 AMI를 사용한다
- Auto Scaling Group을 자동으로 구성한다
- 노드를 클러스터에 자동으로 등록한다
- 노드 업데이트를 자동화한다

**개발자가 하는 것:**
- 인스턴스 타입을 선택한다
- 최소/최대 노드 개수를 설정한다
- SSH 키를 설정한다 (선택)
- 보안 그룹을 설정한다

**노드 업그레이드 과정:**
1. AWS가 새 AMI로 새 노드를 시작한다
2. 새 노드가 클러스터에 등록된다
3. 기존 노드의 Pod를 새 노드로 이동시킨다 (drain)
4. 기존 노드를 종료한다
5. 다음 노드로 반복한다

이 과정이 자동으로 진행된다. 다운타임이 없다.

**2. 자체 관리형 노드:**
EC2 인스턴스를 직접 생성하고 클러스터에 등록한다.

**언제 사용하나:**
- 특수한 AMI가 필요한 경우. 커스텀 소프트웨어가 설치된 AMI
- GPU 인스턴스가 필요한 경우. 머신러닝 워크로드
- 특수한 하드웨어가 필요한 경우
- 세밀한 제어가 필요한 경우

**단점:**
- 직접 관리해야 한다
- 업데이트를 수동으로 해야 한다
- 문제가 생기면 직접 해결해야 한다

대부분의 경우 관리형 노드 그룹을 사용한다. 자체 관리형 노드는 특수한 경우에만 사용한다.

**3. Fargate:**
노드를 관리할 필요가 없다. 서버리스 컴퓨팅이다.

**동작 방식:**
- Fargate Profile을 생성한다. 어떤 Pod를 Fargate에서 실행할지 정의한다
- 조건에 맞는 Pod가 생성되면 자동으로 Fargate에서 실행된다
- AWS가 필요한 리소스를 자동으로 할당한다
- Pod가 종료되면 리소스가 반환된다

**장점:**
- 노드를 관리할 필요가 없다
- Pod 단위로 격리된다. 보안이 강화된다
- 사용한 만큼만 비용을 지불한다

**단점:**
- 모든 Kubernetes 기능을 지원하지 않는다
- DaemonSet을 사용할 수 없다
- HostPath를 사용할 수 없다
- GPU를 사용할 수 없다

**언제 사용하나:**
- 배치 작업. 주기적으로 실행되는 작업
- 개발 환경. 비용을 절감하고 싶은 경우
- 격리가 중요한 워크로드

대부분의 프로덕션 워크로드는 관리형 노드 그룹을 사용한다. Fargate는 특정 용도로 사용한다.

### 네트워킹

EKS의 네트워킹은 조금 복잡하다. AWS VPC와 Kubernetes 네트워킹이 결합되어 있다.

**VPC CNI 플러그인:**
EKS의 기본 네트워킹 플러그인이다. 각 Pod에 VPC IP 주소를 직접 할당한다.

**동작 방식:**
1. 노드가 시작되면 VPC CNI가 ENI(Elastic Network Interface)를 생성한다
2. ENI에 여러 IP 주소를 할당한다
3. Pod가 생성되면 ENI의 IP 주소를 Pod에 할당한다
4. Pod는 VPC의 일반 IP 주소를 가진다
5. Pod가 VPC 내의 다른 리소스와 직접 통신할 수 있다

**장점:**
- Pod가 VPC의 다른 리소스와 직접 통신한다
- 보안 그룹을 Pod 단위로 적용할 수 있다 (Security Groups for Pods)
- 네트워크 성능이 좋다. 오버헤드가 적다

**ENI 제한:**
각 EC2 인스턴스 타입마다 ENI 개수와 IP 주소 개수가 제한된다.

**예시:**
- t3.small: ENI 3개, IP 4개/ENI = 최대 12개 Pod
- t3.medium: ENI 3개, IP 6개/ENI = 최대 18개 Pod
- t3.large: ENI 3개, IP 12개/ENI = 최대 36개 Pod

큰 클러스터를 운영하려면 적절한 인스턴스 타입을 선택해야 한다. Pod가 많으면 ENI와 IP가 많은 인스턴스를 선택한다.

**실무 팁:**
노드에 Pod가 스케줄되지 않고 "Too many pods" 에러가 나면 ENI 제한 때문이다. 더 큰 인스턴스 타입을 사용하거나, 노드를 추가한다.

## 핵심 개념

Kubernetes의 핵심 개념들을 처음 배우는 사람도 이해할 수 있게 설명한다.

### Pod

Pod는 Kubernetes의 가장 작은 배포 단위다. 하나 이상의 컨테이너를 묶은 것이다.

**왜 Pod가 필요할까:**
Docker에서는 컨테이너 하나만 실행하면 된다. 그런데 Kubernetes는 왜 Pod라는 개념이 필요할까?

**실제 상황:**
웹 애플리케이션을 실행한다고 하자. 메인 컨테이너 하나만 있으면 될 것 같지만, 실제로는 여러 컨테이너가 필요한 경우가 많다.

**예시:**
- 메인 컨테이너: Node.js 애플리케이션
- 로그 수집 컨테이너: 로그를 CloudWatch로 전송
- 프록시 컨테이너: TLS 암호화 처리
- 설정 동기화 컨테이너: S3에서 설정 파일을 주기적으로 가져옴

이런 컨테이너들은 함께 배포되고, 함께 삭제되어야 한다. 같은 서버에 있어야 하고, 같은 네트워크를 공유해야 한다. Pod가 이를 가능하게 한다.

**Pod의 특징:**

**1. 네트워크 공유:**
같은 Pod 내의 컨테이너는 localhost로 서로 통신할 수 있다.

예를 들어, 메인 컨테이너가 8080 포트로 실행되고, 프록시 컨테이너가 443 포트로 실행된다. 프록시 컨테이너는 localhost:8080으로 메인 컨테이너에 접근할 수 있다.

**2. 스토리지 공유:**
같은 Pod 내의 컨테이너는 볼륨을 공유할 수 있다.

예를 들어, 메인 컨테이너가 /var/log에 로그를 쓴다. 로그 수집 컨테이너도 같은 /var/log를 읽을 수 있다. 볼륨을 공유하기 때문이다.

**3. 고유한 IP 주소:**
각 Pod는 고유한 IP 주소를 가진다. 클러스터 내의 다른 Pod는 이 IP로 접근할 수 있다.

**4. 임시적 (Ephemeral):**
Pod는 언제든 삭제되고 재생성될 수 있다. 노드가 죽거나, 리소스가 부족하거나, 배포가 업데이트되면 Pod가 재생성된다. 새 Pod는 새 IP 주소를 받는다.

**실무에서 Pod 사용:**

**대부분의 경우:**
Pod에 컨테이너 하나만 넣는다. 메인 애플리케이션 컨테이너만 있으면 충분하다.

**Sidecar 패턴:**
메인 컨테이너를 보조하는 컨테이너를 함께 배치한다.
- 로그 수집: Fluent Bit 컨테이너
- 메트릭 수출: Prometheus Exporter 컨테이너
- 프록시: Envoy 프록시 컨테이너

**실무 팁:**
처음에는 Pod에 컨테이너 하나만 넣는다. 나중에 필요하면 Sidecar 컨테이너를 추가한다. Service Mesh를 사용하면 자동으로 Sidecar가 주입된다.

### Deployment

Deployment는 Pod의 선언적 업데이트를 관리한다. 실무에서 가장 많이 사용하는 리소스다.

**왜 Deployment가 필요할까:**
Pod를 직접 생성할 수도 있다. 하지만 여러 문제가 있다.

**Pod만 사용하면:**
- Pod가 죽으면 다시 시작되지 않는다
- 여러 개의 Pod를 수동으로 관리해야 한다
- 업데이트할 때 다운타임이 발생한다
- 롤백이 어렵다

Deployment가 이런 문제를 해결한다.

**Deployment가 하는 일:**

**1. 원하는 Pod 개수 유지:**
replicas: 3이라고 설정하면, 항상 3개의 Pod가 실행된다.

**동작 과정:**
- 현재 Pod 개수를 확인한다
- 3개보다 적으면 새 Pod를 만든다
- 3개보다 많으면 Pod를 삭제한다
- Pod가 죽으면 자동으로 새 Pod를 만든다

**2. 무중단 배포 (Rolling Update):**
새 버전을 배포할 때 다운타임 없이 점진적으로 업데이트한다.

**동작 과정:**
1. 현재 v1 Pod 3개가 실행 중이다
2. v2 이미지로 Deployment를 업데이트한다
3. v2 Pod 하나를 새로 만든다
4. v2 Pod가 Ready 상태가 되면 v1 Pod 하나를 삭제한다
5. 다시 v2 Pod 하나를 만든다
6. 모든 Pod가 v2가 될 때까지 반복한다

이 과정에서 서비스는 계속 실행된다. 사용자는 업데이트를 느끼지 못한다.

**3. 롤백:**
새 버전에 문제가 있으면 이전 버전으로 쉽게 되돌린다.

```bash
# 롤백
kubectl rollout undo deployment/my-app

# 특정 버전으로 롤백
kubectl rollout undo deployment/my-app --to-revision=2
```

Deployment는 이전 ReplicaSet을 유지한다. 롤백하면 이전 ReplicaSet을 다시 활성화한다.

**4. 스케일링:**
Pod 개수를 쉽게 조절한다.

```bash
# 수동 스케일링
kubectl scale deployment/my-app --replicas=5

# Auto Scaling
kubectl autoscale deployment/my-app --min=2 --max=10 --cpu-percent=70
```

**실무 예시:**

**배포 과정:**
1. 개발자가 코드를 수정한다
2. Docker 이미지를 빌드하고 ECR에 푸시한다
3. Deployment YAML 파일의 이미지 태그를 변경한다
4. kubectl apply로 Deployment를 업데이트한다
5. Kubernetes가 자동으로 롤링 업데이트를 수행한다
6. 모든 Pod가 새 버전으로 업데이트된다

**배포 전략 설정:**
Deployment에서 배포 속도를 조절할 수 있다.

```yaml
spec:
  replicas: 10
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 2        # 최대 2개까지 추가 Pod 생성
      maxUnavailable: 1  # 최대 1개까지 동시에 업데이트
```

- maxSurge: 2 → 한 번에 2개 Pod를 추가로 만든다. 빠르게 배포된다
- maxUnavailable: 1 → 한 번에 1개 Pod만 업데이트한다. 안정적이다

**실무 팁:**
프로덕션에서는 maxUnavailable을 낮게 설정한다. 1 또는 0으로 설정해서 가용성을 유지한다. 개발 환경에서는 높게 설정해 빠르게 배포한다.

### Service

Service는 Pod에 대한 안정적인 네트워크 엔드포인트를 제공한다.

**왜 Service가 필요할까:**

**문제 상황:**
Deployment로 3개의 Pod를 실행했다. 다른 Pod나 외부에서 이 Pod에 어떻게 접근할까?

**Pod IP를 직접 사용하면:**
- Pod는 임시적이다. 언제든 삭제되고 재생성된다
- 새 Pod는 새 IP를 받는다
- IP가 계속 바뀐다
- 3개의 Pod에 어떻게 트래픽을 분산할까?

Service가 이 문제를 해결한다.

**Service가 하는 일:**

**1. 고정된 IP와 DNS 이름 제공:**
Service를 만들면 고정된 ClusterIP를 받는다. 클러스터 내에서 이 IP로 항상 접근할 수 있다.

**예시:**
- Service 이름: my-app
- ClusterIP: 10.100.200.50
- DNS 이름: my-app.default.svc.cluster.local

다른 Pod는 `my-app`이라는 이름으로 접근할 수 있다. Kubernetes DNS가 자동으로 해결한다.

**2. 로드 밸런싱:**
Service는 여러 Pod에 트래픽을 자동으로 분산한다.

**동작 과정:**
1. 클라이언트가 Service IP로 요청을 보낸다
2. Service가 대상 Pod 목록을 확인한다
3. 랜덤하게 하나의 Pod를 선택한다
4. 해당 Pod로 요청을 전달한다

**3. Pod 선택:**
Service는 Label Selector로 Pod를 선택한다.

**예시:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app
spec:
  selector:
    app: my-app  # 이 라벨을 가진 Pod를 선택
  ports:
  - port: 80
    targetPort: 8080
```

`app: my-app` 라벨을 가진 모든 Pod가 이 Service의 대상이 된다. Pod가 추가되거나 제거되면 Service가 자동으로 업데이트된다.

**Service 타입:**

**1. ClusterIP (기본값):**
클러스터 내부에서만 접근 가능하다.

**사용 사례:**
- 백엔드 API
- 데이터베이스
- 캐시 서버

외부에 노출할 필요가 없는 서비스에 사용한다.

**2. NodePort:**
각 노드의 특정 포트로 Service를 노출한다.

**동작 방식:**
- Kubernetes가 각 노드에 동일한 포트를 연다. 예: 30080
- 어느 노드의 IP:30080으로 접근해도 Service로 연결된다
- Service가 다시 Pod로 트래픽을 전달한다

**사용 사례:**
- 개발 환경에서 테스트
- 온프레미스 환경

프로덕션에서는 잘 사용하지 않는다. 포트 범위가 제한적이고, 관리가 어렵다.

**3. LoadBalancer:**
클라우드 로드 밸런서를 자동으로 생성한다. AWS에서는 NLB가 생성된다.

**동작 방식:**
1. Service를 만들면 AWS가 NLB를 생성한다
2. NLB가 외부 트래픽을 받는다
3. NLB가 노드로 트래픽을 전달한다
4. 노드가 다시 Pod로 전달한다

**사용 사례:**
- 간단한 외부 노출
- TCP/UDP 트래픽

HTTP/HTTPS는 Ingress를 사용하는 것이 더 좋다.

**4. ExternalName:**
외부 DNS 이름을 Service로 매핑한다.

**사용 사례:**
- 외부 데이터베이스 접근
- 외부 API 접근

클러스터 내에서 `my-external-db`라고 호출하면 실제로는 `mydb.abc123.us-west-2.rds.amazonaws.com`에 접근한다.

**실무 팁:**
- 내부 서비스: ClusterIP
- 외부 HTTP/HTTPS: Ingress
- 외부 TCP/UDP: LoadBalancer

대부분의 서비스는 ClusterIP를 사용하고, 외부 접근이 필요한 일부 서비스만 Ingress나 LoadBalancer를 사용한다.

### ConfigMap과 Secret

애플리케이션 설정을 관리하는 방법이다.

**왜 ConfigMap과 Secret이 필요할까:**

**과거 방식:**
설정 값을 Docker 이미지에 넣거나, 환경 변수로 하드코딩했다.

**문제점:**
- 설정을 변경하려면 이미지를 다시 빌드해야 한다
- 환경마다 다른 이미지가 필요하다 (개발, 스테이징, 프로덕션)
- 비밀번호 같은 민감한 정보가 이미지에 포함된다
- Git에 비밀번호가 커밋된다

ConfigMap과 Secret이 이 문제를 해결한다.

**ConfigMap:**

**언제 사용하나:**
일반 설정 데이터를 저장한다. 민감하지 않은 정보다.

**저장하는 데이터:**
- 애플리케이션 설정
- API 엔드포인트
- Feature Flag
- 환경 설정

**사용 방법:**

**1. ConfigMap 생성:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_ENV: "production"
  API_URL: "https://api.example.com"
  LOG_LEVEL: "info"
  config.json: |
    {
      "timeout": 30,
      "retries": 3
    }
```

**2. Pod에서 사용:**

**환경 변수로 주입:**
```yaml
spec:
  containers:
  - name: app
    image: my-app:1.0
    envFrom:
    - configMapRef:
        name: app-config
```

이제 Pod 내에서 `process.env.APP_ENV`로 접근할 수 있다.

**파일로 마운트:**
```yaml
spec:
  containers:
  - name: app
    image: my-app:1.0
    volumeMounts:
    - name: config
      mountPath: /etc/config
  volumes:
  - name: config
    configMap:
      name: app-config
```

이제 `/etc/config/config.json` 파일로 접근할 수 있다.

**Secret:**

**언제 사용하나:**
민감한 정보를 저장한다.

**저장하는 데이터:**
- 데이터베이스 비밀번호
- API 키
- TLS 인증서
- OAuth 토큰

**사용 방법:**

**1. Secret 생성:**
```bash
# 명령어로 생성
kubectl create secret generic db-secret \
  --from-literal=username=admin \
  --from-literal=password=supersecret

# YAML로 생성 (Base64 인코딩 필요)
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  username: YWRtaW4=       # "admin"을 Base64 인코딩
  password: c3VwZXJzZWNyZXQ=  # "supersecret"을 Base64 인코딩
```

**2. Pod에서 사용:**
```yaml
spec:
  containers:
  - name: app
    image: my-app:1.0
    env:
    - name: DB_USERNAME
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: username
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: password
```

**실무에서 주의사항:**

**1. Secret은 암호화되지 않는다:**
Secret은 Base64로 인코딩만 되어 있다. etcd에 평문으로 저장된다. 누군가 etcd에 접근하면 Secret을 볼 수 있다.

**해결 방법:**
- EKS에서 KMS 암호화를 활성화한다
- AWS Secrets Manager나 Parameter Store를 사용한다
- External Secrets Operator를 사용한다

**2. ConfigMap/Secret 변경은 자동 반영되지 않는다:**
ConfigMap이나 Secret을 변경해도 실행 중인 Pod는 영향을 받지 않는다.

**환경 변수로 주입한 경우:**
- Pod를 재시작해야 한다
- Deployment를 롤링 업데이트한다

**파일로 마운트한 경우:**
- 파일 내용은 자동으로 업데이트된다 (몇 분 소요)
- 애플리케이션이 파일을 다시 읽어야 한다

**실무 팁:**
- ConfigMap은 자주 변경되지 않는 설정에 사용한다
- 민감한 정보는 반드시 Secret을 사용한다
- 프로덕션에서는 Secrets Manager를 사용하는 것을 권장한다
- Secret 변경 후에는 반드시 Pod를 재시작한다

## 참고

- AWS EKS 사용자 가이드: https://docs.aws.amazon.com/eks/
- Kubernetes 공식 문서: https://kubernetes.io/docs/
- EKS Workshop: https://www.eksworkshop.com/
- AWS EKS 모범 사례: https://aws.github.io/aws-eks-best-practices/
