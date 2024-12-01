
# AWS Fargate와 Amazon EKS

AWS Fargate와 Amazon EKS는 각각 서버리스 컨테이너 실행 및 Kubernetes 관리 서비스를 제공하며, 상호 보완적인 관계를 가집니다. 이 문서에서는 두 서비스의 개념, 상관관계, 그리고 이를 활용하는 방법에 대해 설명합니다.

## Amazon EKS란?

Amazon Elastic Kubernetes Service(EKS)는 완전 관리형 **Kubernetes 서비스**로, 사용자가 Kubernetes 클러스터를 손쉽게 배포, 관리, 확장할 수 있도록 지원합니다.

### 주요 특징
1. **Kubernetes 표준 준수**:
    - 오픈 소스 Kubernetes를 기반으로 하며, 기존 Kubernetes 워크플로우 및 도구와 호환됩니다.

2. **관리형 서비스**:
    - 컨트롤 플레인, 노드 그룹, 네트워킹 등을 AWS가 관리합니다.

3. **고가용성 및 보안**:
    - 다중 가용 영역(Multi-AZ)에 걸친 내결함성을 제공하며, IAM 통합 및 네트워크 보안 설정이 가능합니다.

## AWS Fargate와 Amazon EKS의 상관관계

AWS Fargate는 **Amazon EKS의 실행 환경** 중 하나로 사용될 수 있습니다. EKS는 Kubernetes 클러스터의 오케스트레이션 및 관리를 담당하며, Fargate는 개별 Pod를 실행하기 위한 서버리스 컴퓨팅 환경을 제공합니다.

### EKS에서 Fargate 사용의 장점

1. **서버리스 Kubernetes**:
    - Kubernetes 워커 노드를 직접 관리하지 않고, Fargate를 통해 Pod를 서버리스로 실행할 수 있습니다.

2. **세밀한 리소스 관리**:
    - Fargate는 Pod 단위로 vCPU 및 메모리 리소스를 정의할 수 있어, 리소스 사용을 최적화합니다.

3. **격리된 보안 환경**:
    - Fargate는 각 Pod를 별도의 격리된 환경에서 실행하므로, 노드 공유로 인한 보안 리스크를 줄입니다.

### 작동 방식

1. **클러스터 생성**:
    - Amazon EKS를 통해 Kubernetes 클러스터를 생성합니다.

2. **Fargate 프로필 설정**:
    - 특정 네임스페이스나 태그를 기반으로 Fargate에서 실행할 Pod를 지정합니다.

3. **Pod 실행**:
    - 지정된 Pod는 Fargate에 의해 서버리스로 실행되며, 사용자는 노드 프로비저닝 및 관리를 할 필요가 없습니다.

## Fargate와 EKS의 비교

| 특징                       | AWS Fargate                            | Amazon EKS                              |
|----------------------------|-----------------------------------------|-----------------------------------------|
| 관리 대상                  | 서버리스 (노드 관리 불필요)             | 노드 그룹 관리 필요 (또는 Fargate 사용 가능) |
| 리소스 정의                | Pod 단위                                | 클러스터 및 노드 단위                   |
| 적합한 사용 사례           | 단일 서비스, 간단한 애플리케이션       | 복잡한 마이크로서비스, 대규모 워크로드  |
| 확장성                    | 자동으로 Pod에 필요한 리소스 제공       | 클러스터와 노드 크기에 따라 확장 가능    |

## 활용 사례

### Fargate를 사용한 서버리스 Kubernetes
- EKS에서 관리형 Kubernetes의 이점을 누리면서, 서버리스 방식으로 Pod를 실행하여 노드 관리 부담을 줄이고 싶을 때 적합합니다.

### EKS와 Fargate의 조합으로 애플리케이션 실행
- 복잡한 애플리케이션의 일부는 EC2 노드 그룹에서 실행하고, 특정 작업은 Fargate에서 실행하도록 설정하여 비용과 성능을 최적화할 수 있습니다.

## 요약

AWS Fargate와 Amazon EKS는 각각의 강점을 결합하여, 사용자가 Kubernetes 클러스터를 더욱 유연하고 비용 효율적으로 관리할 수 있도록 돕습니다. Fargate는 서버리스 컴퓨팅을 제공하며, EKS는 Kubernetes 관리와 오케스트레이션을 책임집니다.

## 참고 자료

- [AWS Fargate](https://aws.amazon.com/fargate/)
- [Amazon EKS](https://aws.amazon.com/eks/)
- [EKS Fargate Profiles](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
