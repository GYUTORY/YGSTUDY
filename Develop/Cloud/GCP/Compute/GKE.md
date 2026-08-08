---
title: "GKE (Google Kubernetes Engine)"
tags: [gcp, kubernetes, docker, cloud]
updated: 2026-08-05
---

# GKE (Google Kubernetes Engine)

GKE는 GCP에서 관리형 쿠버네티스를 돌리는 서비스다. 컨트롤 플레인(마스터)을 구글이 대신 관리해주고, 워커 노드는 GCE VM 위에 뜬다. 직접 kubeadm으로 클러스터를 구축해본 경험이 있으면 GKE가 얼마나 손이 덜 가는지 바로 체감된다. etcd 백업, apiserver 인증서 갱신, 컨트롤 플레인 HA 구성 같은 걸 신경 쓸 필요가 없다.

EKS를 써봤다면 비슷하게 느껴지겠지만, GKE는 컨트롤 플레인 업그레이드나 노드 자동 복구 같은 부분에서 자동화 수준이 좀 더 높다. 그만큼 GKE가 알아서 하는 일이 많아서, 모르고 있다가 새벽에 노드가 갑자기 재생성되는 걸 보고 놀라는 경우가 있다.

---

## Standard와 Autopilot

GKE 클러스터를 만들 때 제일 먼저 정해야 하는 게 운영 모드다. 한번 정하면 나중에 바꿀 수 없어서 처음에 잘 골라야 한다.

Standard 모드는 노드풀을 직접 관리한다. VM 타입, 노드 개수, 디스크 크기를 내가 정하고, 그 노드에 대한 비용을 낸다. 노드가 비어 있어도 켜져 있으면 돈이 나간다. 대신 노드에 SSH로 들어가거나, DaemonSet을 깔거나, 특정 머신 타입을 지정하는 게 다 된다.

Autopilot 모드는 노드라는 개념을 사용자에게서 숨긴다. Pod을 배포하면 그 Pod이 요청한 CPU/메모리만큼만 과금된다. 노드 관리를 아예 안 해도 되지만, 제약이 많다. DaemonSet 일부가 안 되고, privileged 컨테이너가 막혀 있고, 노드에 직접 접근이 안 된다. hostPath 볼륨도 제한된다.

실무에서 겪은 판단 기준은 이렇다. 워크로드가 예측 가능하고 노드를 꽉 채워 쓸 수 있으면 Standard가 싸다. 트래픽이 들쭉날쭉하고 Pod 밀도가 낮으면 Autopilot이 관리 부담 대비 낫다. 다만 Autopilot은 Pod마다 리소스 request에 프리미엄이 붙어서, 노드를 잘 채우는 팀이 Standard로 돌리면 30~40% 정도 더 쌌던 경우가 있다.

Autopilot에서 특히 조심할 부분은 리소스 request를 안 적으면 GKE가 기본값을 강제로 넣는다는 점이다. request를 0으로 두거나 안 적은 컨테이너가 있으면 예상보다 큰 값이 붙어서 비용이 튀는 걸 뒤늦게 발견하는 일이 있다.

```bash
# Standard 클러스터 생성
gcloud container clusters create my-cluster \
  --zone asia-northeast3-a \
  --num-nodes 3 \
  --machine-type e2-standard-4 \
  --release-channel regular

# Autopilot 클러스터 생성
gcloud container clusters create-auto my-auto-cluster \
  --region asia-northeast3 \
  --release-channel regular
```

`--release-channel`은 컨트롤 플레인 버전을 어느 속도로 따라갈지 정한다. rapid는 최신, stable은 가장 보수적이다. 프로덕션은 regular나 stable을 쓴다. rapid로 뒀다가 검증 안 된 버전으로 자동 업그레이드돼서 문제가 생기는 걸 본 적이 있다.

zonal 클러스터(`--zone`)는 컨트롤 플레인이 한 존에만 있어서 그 존이 죽으면 apiserver에 접근이 안 된다. 프로덕션은 `--region`으로 regional 클러스터를 만들어서 컨트롤 플레인을 3개 존에 분산시켜야 한다. 노드도 여러 존에 퍼진다.

---

## 노드풀 구성

Standard 클러스터는 노드풀 단위로 노드를 묶는다. 노드풀 하나는 같은 설정(머신 타입, 디스크, 라벨, taint)을 가진 노드 그룹이다. 하나의 클러스터에 성격이 다른 워크로드를 돌릴 때 노드풀을 나눈다.

예를 들어 일반 API 서버는 e2 노드풀에, GPU가 필요한 배치 작업은 GPU 노드풀에, 비용에 민감한 비동기 작업은 스팟 노드풀에 배치하는 식이다. 노드풀마다 taint를 걸고, Pod에 toleration과 nodeSelector를 줘서 원하는 노드풀로 스케줄링을 유도한다.

```bash
# 배치 작업용 노드풀 추가 (taint 포함)
gcloud container node-pools create batch-pool \
  --cluster my-cluster \
  --zone asia-northeast3-a \
  --machine-type c2-standard-8 \
  --num-nodes 2 \
  --node-taints workload=batch:NoSchedule \
  --node-labels pool=batch

# 노드풀 목록 확인
gcloud container node-pools list --cluster my-cluster --zone asia-northeast3-a
```

taint를 건 노드풀에 Pod을 올리려면 이렇게 toleration과 nodeSelector를 맞춰줘야 한다.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: nightly-report
spec:
  template:
    spec:
      nodeSelector:
        pool: batch
      tolerations:
        - key: workload
          operator: Equal
          value: batch
          effect: NoSchedule
      containers:
        - name: report
          image: asia-northeast3-docker.pkg.dev/my-project/apps/report:latest
      restartPolicy: Never
```

노드풀을 나눌 때 흔히 하는 실수가 taint만 걸고 toleration을 안 맞추는 것이다. 그러면 그 Pod이 어디에도 스케줄링 안 되고 Pending에 걸린다. 반대로 toleration만 있고 nodeSelector가 없으면, Pod이 taint 없는 다른 노드풀로 새어나가서 의도한 곳에 안 뜬다. 두 개를 같이 봐야 한다.

노드풀 업그레이드는 노드풀 단위로 따로 한다. 컨트롤 플레인을 먼저 올리고 노드풀을 뒤따라 올리는 게 순서다. 컨트롤 플레인보다 노드가 2개 마이너 버전 이상 뒤처지면 GKE가 강제로 업그레이드를 걸어서, 미뤄두면 원치 않는 타이밍에 노드가 재생성되는 일이 있다.

---

## Workload Identity로 GCP 서비스 인증

Pod에서 Cloud Storage나 Pub/Sub 같은 GCP 서비스를 호출할 때, 예전에는 서비스 계정 키(JSON)를 시크릿으로 넣어서 썼다. 이 방식은 키가 노출되면 그대로 뚫리고, 키 로테이션도 수동이라 관리가 나빴다. 키를 Git에 실수로 커밋해서 사고가 나는 일도 있었다.

Workload Identity는 키 파일 없이 쿠버네티스 서비스 계정(KSA)을 GCP 서비스 계정(GSA)에 연결한다. Pod은 GKE 메타데이터 서버에서 단기 토큰을 받아서 인증한다. 키 파일이 아예 없으니 유출될 게 없다.

설정 순서는 이렇다. 먼저 클러스터에 Workload Identity를 켜고, GSA를 만들고, KSA를 만들고, 둘을 IAM 바인딩으로 묶은 다음, KSA에 GSA를 어노테이션으로 연결한다.

```bash
# 클러스터에 Workload Identity 활성화 (기존 클러스터)
gcloud container clusters update my-cluster \
  --zone asia-northeast3-a \
  --workload-pool my-project.svc.id.goog

# 노드풀도 메타데이터 모드를 켜야 함
gcloud container node-pools update default-pool \
  --cluster my-cluster \
  --zone asia-northeast3-a \
  --workload-metadata GKE_METADATA

# GCP 서비스 계정 생성 및 권한 부여
gcloud iam service-accounts create app-gsa
gcloud projects add-iam-policy-binding my-project \
  --member "serviceAccount:app-gsa@my-project.iam.gserviceaccount.com" \
  --role roles/storage.objectViewer

# KSA와 GSA를 바인딩 (workloadIdentityUser)
gcloud iam service-accounts add-iam-policy-binding \
  app-gsa@my-project.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:my-project.svc.id.goog[default/app-ksa]"
```

`default/app-ksa`는 `네임스페이스/KSA이름` 형식이다. 여기가 실제 Pod이 뜨는 네임스페이스와 다르면 인증이 안 되는데, 에러 메시지가 불친절해서 원인을 찾는 데 시간을 쓰는 경우가 많다. 네임스페이스를 꼭 맞춰야 한다.

쿠버네티스 쪽에서는 KSA를 만들고 어노테이션을 단다.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-ksa
  namespace: default
  annotations:
    iam.gke.io/gcp-service-account: app-gsa@my-project.iam.gserviceaccount.com
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      serviceAccountName: app-ksa   # 여기에 KSA를 지정해야 함
      containers:
        - name: my-app
          image: asia-northeast3-docker.pkg.dev/my-project/apps/my-app:latest
```

Pod의 `serviceAccountName`을 지정 안 하면 default KSA로 뜨는데, default에는 어노테이션이 없어서 인증이 안 된다. 배포는 됐는데 GCS 접근만 403이 나면 대부분 이 지점이다.

설정이 맞는지 확인하려면 Pod 안에서 메타데이터 서버로 어떤 계정이 잡히는지 찍어본다.

```bash
kubectl run -it --rm check --image google/cloud-sdk:slim \
  --overrides='{"spec":{"serviceAccountName":"app-ksa"}}' -- \
  curl -s -H "Metadata-Flavor: Google" \
  "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email"
```

기대한 GSA 이메일이 나오면 연결이 된 것이다. default 컴퓨트 서비스 계정이 나오면 어딘가 연결이 끊긴 것이다.

---

## 오토스케일링

GKE에서 스케일링은 층위가 두 개다. HPA는 Pod 개수를 늘리고, 클러스터 오토스케일러는 Pod을 올릴 노드가 부족하면 노드를 늘린다. 이 둘은 별개라서 같이 이해해야 한다.

### HPA (Horizontal Pod Autoscaler)

HPA는 CPU나 메모리, 커스텀 메트릭을 보고 Pod 레플리카 수를 조정한다. CPU 기준 스케일링은 Deployment에 resource request가 반드시 있어야 동작한다. request가 없으면 사용률을 계산할 기준이 없어서 HPA가 `unknown`을 뱉고 스케일이 안 된다. 이걸 모르고 HPA만 붙였다가 안 늘어나서 한참 헤매는 경우가 있다.

```bash
# CPU 50% 기준으로 2~10개 사이 스케일
kubectl autoscale deployment my-app --cpu-percent=50 --min=2 --max=10
```

매니페스트로 관리할 때는 이렇게 쓴다.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 50
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300   # 스케일 다운은 5분 안정화
```

`behavior.scaleDown`을 안 건드리면 트래픽이 살짝 빠질 때 Pod을 너무 빨리 줄였다가, 다시 몰리면 늘리는 플래핑이 생긴다. 안정화 윈도우를 넉넉히 줘서 진동을 막는다.

### 클러스터 오토스케일러

HPA가 Pod을 10개로 늘리려는데 노드에 자리가 없으면 Pod이 Pending에 걸린다. 클러스터 오토스케일러는 이 Pending Pod을 감지해서 노드풀에 노드를 추가한다. 노드풀 단위로 min/max를 걸어야 동작한다.

```bash
# 노드풀에 오토스케일 범위 지정 (1~5개)
gcloud container clusters update my-cluster \
  --zone asia-northeast3-a \
  --enable-autoscaling \
  --node-pool default-pool \
  --min-nodes 1 \
  --max-nodes 5
```

오토스케일러는 노드를 늘리는 건 빠른데 줄이는 건 보수적이다. 노드에 Pod이 하나라도 남아 있으면 그 노드를 못 줄인다. 특히 로컬 스토리지를 쓰는 Pod이나 PodDisruptionBudget에 막히는 Pod이 있으면 노드가 비질 않아서 계속 켜져 있는다. 비용이 안 줄어서 이상하다 싶으면 노드에 뭐가 남아 있는지부터 본다.

```bash
# 특정 노드에 어떤 Pod이 붙어 있는지 확인
kubectl get pods --all-namespaces -o wide --field-selector spec.nodeName=<노드이름>
```

kube-system의 로그 수집기나 모니터링 DaemonSet은 오토스케일러가 노드 축소를 판단할 때 무시하도록 어노테이션을 달아둬야, 노드가 정상적으로 비워진다.

---

## 스팟 VM 노드풀로 비용 절감

스팟 VM은 구글이 남는 용량을 싸게 파는 인스턴스다. 온디맨드 대비 60~90%까지 싸다. 대신 구글이 용량이 필요하면 30초 통보 후 회수해간다. 언제든 죽을 수 있는 노드라서 어디에 쓰느냐가 중요하다.

배치 작업, 비동기 워커, 재시도 가능한 작업, 스테이트리스한 API 서버 일부는 스팟에 올려도 된다. 반대로 상태를 들고 있거나 중단되면 안 되는 결제 처리 같은 건 스팟에 올리면 안 된다. 실무에서는 온디맨드 노드풀과 스팟 노드풀을 같이 두고, 워크로드 성격에 따라 나눠 배치한다.

```bash
# 스팟 노드풀 생성
gcloud container node-pools create spot-pool \
  --cluster my-cluster \
  --zone asia-northeast3-a \
  --machine-type e2-standard-4 \
  --spot \
  --enable-autoscaling \
  --min-nodes 0 \
  --max-nodes 10 \
  --node-labels cloud.google.com/gke-spot=true
```

스팟 노드에는 GKE가 자동으로 `cloud.google.com/gke-spot=true:NoSchedule` taint를 건다. 그래서 스팟에 올릴 Pod에는 toleration을 붙여야 한다.

```yaml
spec:
  tolerations:
    - key: cloud.google.com/gke-spot
      operator: Equal
      value: "true"
      effect: NoSchedule
  nodeSelector:
    cloud.google.com/gke-spot: "true"
```

스팟 노드가 회수될 때는 노드에 SIGTERM이 가고 Pod이 종료된다. 이 30초 안에 정리를 끝내야 하니, Pod의 `terminationGracePeriodSeconds`를 짧게 잡고, 처리 중이던 작업을 큐로 되돌리는 로직을 넣어둔다. graceful shutdown이 안 된 워커는 스팟 회수 때 작업을 그냥 날려먹는다.

한 노드풀 안에서 온디맨드와 스팟을 섞고 싶으면 안 된다. 노드풀은 한 종류만 담는다. 대신 스팟이 부족해서 스케줄이 안 될 때 온디맨드로 넘어가게 하려면, 온디맨드 노드풀을 백업으로 두고 Pod의 스케줄링 우선순위나 노드 어피니티를 `preferredDuringScheduling`으로 잡아서 스팟을 우선하되 없으면 온디맨드로 가게 구성한다.

---

## 롤링 업데이트 중 겪는 문제

Deployment를 롤링 업데이트하면 새 Pod을 띄우면서 옛 Pod을 하나씩 내린다. 여기서 문제가 몇 가지 반복적으로 나온다.

### readiness probe 없이 배포하면 트래픽이 죽은 Pod으로 간다

readinessProbe가 없으면 컨테이너가 뜨자마자 Ready로 잡히고 서비스가 트래픽을 보낸다. 애플리케이션이 아직 커넥션 풀이나 캐시를 데우는 중이면 이 트래픽이 다 에러가 난다. 배포할 때마다 잠깐 5xx가 튀는 게 대부분 이 원인이다.

```yaml
readinessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 3
```

`/healthz`는 진짜로 요청 처리가 가능한 상태만 200을 줘야 한다. DB 연결이 안 됐는데 200을 주면 readiness의 의미가 없다.

### 옛 Pod이 죽을 때 처리 중이던 요청이 끊긴다

Pod을 내릴 때 쿠버네티스는 SIGTERM을 보내고 나서 엔드포인트에서 뺀다. 그런데 이 두 동작이 완전히 동기화되진 않아서, SIGTERM을 받았는데도 서비스에서 아직 이 Pod으로 트래픽이 오는 짧은 순간이 있다. 이때 앱이 바로 죽어버리면 그 요청들이 끊긴다.

preStop 훅에 짧은 sleep을 넣어서, 엔드포인트에서 빠질 시간을 벌어준다.

```yaml
lifecycle:
  preStop:
    exec:
      command: ["sh", "-c", "sleep 10"]
terminationGracePeriodSeconds: 30
```

sleep 동안 SIGTERM은 아직 앱에 안 가고, 그 사이 서비스에서 이 Pod이 빠진다. 그 후 앱이 in-flight 요청을 마저 처리하고 종료한다. 이 preStop 하나로 배포 중 끊김이 눈에 띄게 줄어든다.

### PodDisruptionBudget 없이 노드 업그레이드하면 전부 동시에 죽는다

노드 업그레이드나 오토스케일 축소로 노드가 drain될 때, 그 노드의 Pod이 한꺼번에 evict된다. 레플리카가 다 같은 노드에 있었으면 서비스가 통째로 내려간다. PodDisruptionBudget으로 최소 살아 있어야 할 개수를 못 박아둔다.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: my-app-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: my-app
```

`minAvailable: 1`이면 노드 drain 시에도 최소 1개는 유지된다. 다만 이 값을 레플리카 수와 똑같게 잡으면(예: replicas 2, minAvailable 2) 노드가 영영 drain이 안 돼서 오토스케일러도 못 줄이고 업그레이드도 멈춘다. 레플리카보다 작게 잡아야 한다.

### maxSurge/maxUnavailable로 배포 속도 조절

롤링 업데이트 기본값은 maxSurge 25%, maxUnavailable 25%다. 레플리카가 적으면 이 비율이 애매하게 걸려서 순간적으로 가용 Pod이 줄기도 한다. 무중단이 중요하면 maxUnavailable을 0으로 두고 maxSurge를 올려서, 새 Pod이 다 뜬 다음 옛 Pod을 내리게 한다.

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
```

이러면 항상 원래 레플리카 수 이상을 유지하면서 교체된다. 대신 노드 여유가 없으면 새 Pod이 Pending에 걸려서 배포가 느려지니, 오토스케일러 여유와 같이 봐야 한다.

---

## 자주 쓰는 명령어

클러스터 접속 자격을 로컬 kubeconfig에 등록한다.

```bash
gcloud container clusters get-credentials my-cluster \
  --zone asia-northeast3-a \
  --project my-project
```

노드와 Pod 상태를 빠르게 훑을 때.

```bash
# 노드별 리소스 사용량
kubectl top nodes

# Pending Pod이 왜 안 뜨는지 (스케줄 실패 원인이 이벤트에 찍힌다)
kubectl describe pod <pod이름> | grep -A 20 Events

# 최근 클러스터 이벤트 시간순
kubectl get events --sort-by='.lastTimestamp' -A
```

노드가 자꾸 재생성되거나 업그레이드가 도는 게 의심되면 GKE 오퍼레이션 로그를 본다.

```bash
gcloud container operations list --zone asia-northeast3-a
```

여기에 UPGRADE_NODES, REPAIR_NODES 같은 게 찍혀 있으면 GKE가 자동으로 노드를 손댄 것이다. 자동 복구(auto-repair)나 자동 업그레이드(auto-upgrade)가 켜져 있으면 이런 게 새벽에도 돈다. 유지보수 시간대(maintenance window)를 정해두면 이런 작업이 트래픽 적은 시간에만 돌게 묶을 수 있다.
