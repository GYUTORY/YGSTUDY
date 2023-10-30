

# 컨테이너 오케스트레이션
- 컨테이너 기반 애플리케이션을 효율적으로 관리하고 실행하기 위한 자동화된 프로세스

## 주요 컨테이너 오케스트레이션 도구
- Kubernetes, Docker Swarm, Apache Mesos, Amazon ECS, 등이 있습니다


# Kubernetes
- 컨테이너 오케스트레이션을 위한 오픈 소스 플랫폼입니다.
- 원래 Google에서 개발한 Kubernetes는 컨테이너화된 워크로드를 관리하기 위해 기업에서 널리 채택하고 있습니다.
- 컨테이너화된 애플리케이션의 자동 롤백, Kubernetes 클러스터의 자가 복구, 비밀 및 구성 관리는 Kubernetes의 주요 이점 중 일부입니다.


## Kubernetis Concept
- 쿠버네티스에서 가장 중요한 것은 desired state - 원하는 상태 라는 개념입니다.
- 원하는 상태라 함은 관리자가 바라는 환경을 의미하고 좀 더 구체적으로는 얼마나 많은 웹서버가 떠 있으면 좋은지, 몇 번 포트로 서비스하기를 원하는지 등을 말합니다.
- 예를 들어 “nginx 컨테이너를 실행해줘. 그리고 80 포트로 오픈해줘.”는 현재 상태를 원하는 상태로 바꾸기 위한 명령이고 “80 포트를 오픈한 nginx 컨테이너를 1개 유지해줘”는 원하는 상태를 선언한 것입니다. 

![desired-state-1000-9c708dab6.webp](..%2Fetc%2Fimage%2FDevelop%2Fdesired-state-1000-9c708dab6.webp)



### 다양한 배포 방식
![workload-1000-31603c6e6.webp](..%2Fetc%2Fimage%2FDevelop%2Fworkload-1000-31603c6e6.webp)


## ingress
- 다양한 웹 애플리케이션을 하나의 로드 밸런서로 서비스하기 위해 Ingress입장기능을 제공합니다.
- 웹 애플리케이션을 배포하는 과정을 보면 외부에서 직접 접근할 수 없도록 애플리케이션을 내부망에 설치하고 외부에서 접근이 가능한 ALB나 Nginx, Apache를 프록시 서버로 활용



![ingress-1000-6431193ae.webp](..%2Fetc%2Fimage%2FDevelop%2Fingress-1000-6431193ae.webp)


# 반대로, ECS란?
- Amazon Elastic Container Service(ECS)는 컨테이너화된 애플리케이션을 확장, 배포 및 관리하기 위한 컨테이너 오케스트레이션 서비스
- ECS를 사용하면 개발자는 API 호출 및 작업 정의를 통해 클러스터라는 서버 그룹에서 실행되는 확장 가능한 응용 프로그램을 배포하고 관리할 수 있습니다.


# Kubernetes와 ECS - 주요 차이점
![points-of-differences (1).webp](..%2Fetc%2Fimage%2FDevelop%2Fpoints-of-differences%20%281%29.webp)


# ECS에서 발생하는 제한사항
## 공급업체 종속 
- 컨테이너는 Amazon에만 배포할 수 있습니다. 또한 ECS는 자신이 생성한 컨테이너만 관리할 수 있습니다.

## 제한된 스토리지 
- ECS의 주요 제한사항 중 하나는 외부 스토리지가 Amazon EBS를 포함한 Amazon으로 제한된다는 사실입니다.


### Amazon 내에서 검증됨 
- ECS는 Amazon 외부 배포에 공개적으로 사용할 수 없습니다. 
- ECS 코드의 상당 부분은 공개적으로 사용할 수 없습니다.
- 사용자 지정 스케줄러를 구축하기 위한 프레임워크인 AWS Blox와 같은 ECS의 일부 부분만 오픈 소스입니다.










> 출처 : https://subicura.com/2019/05/19/kubernetes-basic-1.html