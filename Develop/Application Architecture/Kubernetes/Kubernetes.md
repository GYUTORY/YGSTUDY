
## 배경지식 
- Kubernetes Q&A를 참고하도록 하자.

---

# 쿠버네티스란?
- 오픈소스로 만들어진 컨테이너 오케스트레이션 도구
  => 컨테이너 오케스트레이션 도구 :  <span style="color: red;">수십~수백 개의 컨테이너를 잘 관리하기 위한 툴</span>
- 컨테이너화된 어플리케이션을 자동으로 배포, 스케일링 하는 등의 관리 기능 제공
  => 각기 다른 환경 (온프레미스 서버, VM, 클라우드)에 대응 가능
<Br>



# 쿠버네티스의 핵심 설계 사상 5가지

---

### 1. 선언적 구성 기반의 배포 환경
- 쿠버네티스에서는 동작을 지시하는 개념(예: 레플리카를 5개 만들어라)보다는 원하는 상태를 선언하는 개념(예: 내 호스트의 레플리카를 항상 5개로 유지하라)을 주로 사용한다.
- 쿠버네티스는 원하는 상태(Desired state)와 현재의 상태(Current state)가 상호 일치하는지를 지속적으로 체크하고 업데이트한다. 
- 따라서 내게 필요한 요소에 대해 원하는 상태를 설정하는 것만으로도 호스트의 리소스 현황에 맞춰 최적의 배치로 배포되거나 변경된다. 
- 만약 특정 요소에 문제가 생겼을 경우, 쿠버네티스는 해당 요소가 원하는 상태로 다시 복구될 수 있도록 필요한 조치를 자동으로 취한다.

![쿠버네티스.jpeg](..%2F..%2F..%2Fetc%2Fimage%2FApplication%20Architecture%2FKubernetes%2F%EC%BF%A0%EB%B2%84%EB%84%A4%ED%8B%B0%EC%8A%A4.jpeg)

### 2. 기능 단위의 분산
- 쿠버네티스에서는 각각의 기능들이 개별적인 구성 요소로서 독립적으로 분산되어 있다. 
- 실제로 노드(Node), 레플리카셋(ReplicaSet), 디플로이먼트(Deployment), 네임스페이스(Namespace) 등 클러스터를 구성하는 주요 요소들이 모두 컨트롤러(Controller)로서 구성되어 있으며, 이들은 Kube Controller Manager 안에 패키징 되어 있다.

![기능단위의 분산.png](..%2F..%2F..%2Fetc%2Fimage%2FApplication%20Architecture%2FKubernetes%2F%EA%B8%B0%EB%8A%A5%EB%8B%A8%EC%9C%84%EC%9D%98%20%EB%B6%84%EC%82%B0.png)

### 3. 클러스터 단위 중앙 제어
- 쿠버네티스에서는 전체 물리 리소스를 클러스터 단위로 추상화하여 관리한다. 
- 클러스터 내부에는 클러스터의 구성 요소들에 대해 제어 권한을 가진 컨트롤 플레인(Control Plane) 역할의 마스터 노드(Master Node)를 두게 되며, 관리자는 이 마스터 노드를 이용하여 클러스터 전체를 제어한다.

![클러스터 단위 중앙 제어.png](..%2F..%2F..%2Fetc%2Fimage%2FApplication%20Architecture%2FKubernetes%2F%ED%81%B4%EB%9F%AC%EC%8A%A4%ED%84%B0%20%EB%8B%A8%EC%9C%84%20%EC%A4%91%EC%95%99%20%EC%A0%9C%EC%96%B4.png)

### 4. 동적 그룹화
- 쿠버네티스의 구성 요소들에는 쿼리 가능한 레이블(Label)과 메타데이터용 어노테이션(Annotation)에 임의로 키-값 쌍을 삽입할 수 있다.
- 관리자는 selector를 이용해서 레이블 기준으로 구성 요소들을 유연하게 관리할 수 있고, 어노테이션에 기재된 내용을 참고하여 해당 요소의 특징적인 내역을 추적할 수 있다.

![동적 그룹화.png](..%2F..%2F..%2Fetc%2Fimage%2FApplication%20Architecture%2FKubernetes%2F%EB%8F%99%EC%A0%81%20%EA%B7%B8%EB%A3%B9%ED%99%94.png)

### 5. API 기반 상호작용
- 쿠버네티스의 구성 요소들은 오직 Kubernetes API server(kube-apiserver)를 통해서만 상호 접근이 가능한 구조를 가진다.
- 마스터 노드에서 kubectl을 거쳐 실행되는 모든 명령은 이 API 서버를 거쳐 수행되며, 컨트롤 플레인(Control Plane)에 포함된 클러스터 제어 요소나 워커 노드(Worker Node)에 포함된 kubelet, 프록시 역시 API 서버를 항상 바라보게 되어 있다.

![API 기반 상호작용.png](..%2F..%2F..%2Fetc%2Fimage%2FApplication%20Architecture%2FKubernetes%2FAPI%20%EA%B8%B0%EB%B0%98%20%EC%83%81%ED%98%B8%EC%9E%91%EC%9A%A9.png)

```
출처 
https://subicura.com/2019/05/19/kubernetes-basic-1.html
https://seongjin.me/kubernetes-core-concepts/
```