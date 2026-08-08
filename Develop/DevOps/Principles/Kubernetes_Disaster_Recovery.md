---
title: 쿠버네티스 클러스터 재해 복구
tags: [kubernetes, devops]
updated: 2026-07-21
---

# 쿠버네티스 클러스터 재해 복구

## 1. 쿠버네티스 DR이 일반 인프라 DR과 다른 이유

쿠버네티스 클러스터가 무너지는 패턴은 여러 가지지만, 실무에서 가장 자주 보는 경우는 세 가지다. 노드가 줄줄이 죽어 컨트롤 플레인 쿼럼이 깨지는 경우, etcd 데이터 디렉토리가 손상되는 경우, 그리고 누군가 실수로 프로덕션 네임스페이스를 날리는 경우다.

일반 인프라 DR과 결정적으로 다른 점은 복구해야 하는 레이어가 두 개라는 점이다. 클러스터 자체(컨트롤 플레인, etcd 상태)와 워크로드(Deployment, Service, ConfigMap, PersistentVolume 위의 데이터)가 서로 다른 방식으로 손상된다. 클러스터를 살려도 워크로드 데이터가 날아갈 수 있고, 워크로드를 살려도 클러스터 설정이 달라서 그대로 못 쓰는 경우도 생긴다. 두 레이어를 각각 어떻게 백업하고 복원하는지 이해해야 DR 계획이 실제로 작동한다.

복구 전략을 한 줄로 정리하면 이렇다. etcd 스냅샷으로 클러스터 상태를 복원하고, Velero로 워크로드와 볼륨 데이터를 복원한다. 둘 다 있어야 완전한 복구가 가능하다.

---

## 2. etcd — 클러스터 상태의 유일한 저장소

etcd는 쿠버네티스 클러스터의 모든 상태를 담고 있다. Deployment 정의, Service, ConfigMap, Secret, RBAC 정책, CRD까지 전부 여기 있다. etcd가 날아가면 클러스터의 "두뇌"가 없어지는 것이므로, 실행 중인 파드가 있더라도 쿠버네티스가 그걸 관리하지 못한다. 그래서 etcd 백업은 쿠버네티스 DR의 출발점이다.

### 2.1 etcd 스냅샷 백업

etcd 스냅샷은 `etcdctl snapshot save` 명령으로 뜬다. 마스터 노드에서 직접 실행하거나, 파드로 접근해서 실행한다.

```bash
# 환경 변수를 먼저 잡는다
ETCDCTL_API=3
ETCD_ENDPOINTS=https://127.0.0.1:2379
ETCD_CACERT=/etc/kubernetes/pki/etcd/ca.crt
ETCD_CERT=/etc/kubernetes/pki/etcd/server.crt
ETCD_KEY=/etc/kubernetes/pki/etcd/server.key

# 스냅샷 저장
etcdctl snapshot save /backup/etcd-snapshot-$(date +%Y%m%d-%H%M%S).db \
  --endpoints=$ETCD_ENDPOINTS \
  --cacert=$ETCD_CACERT \
  --cert=$ETCD_CERT \
  --key=$ETCD_KEY

# 스냅샷 상태 확인 — revision과 hash가 찍히면 정상
etcdctl snapshot status /backup/etcd-snapshot-20260721-120000.db \
  --write-out=table
```

kubeadm으로 구성한 클러스터라면 etcd가 스태틱 파드로 뜬다. 이때 인증서 경로는 `/etc/kubernetes/pki/etcd/` 아래에 있고, 파드 스펙은 `/etc/kubernetes/manifests/etcd.yaml`에서 확인한다.

스냅샷 파일은 반드시 클러스터 외부에 저장해야 한다. 클러스터가 죽으면 클러스터 안의 파일도 접근 못하는 경우가 있다. S3, GCS, Azure Blob 같은 오브젝트 스토리지나, 별도 서버의 디렉토리로 옮겨 둔다. 이걸 크론잡으로 자동화하는 예시는 이렇다.

```yaml
# 마스터 노드에 배치하는 크론잡 (스태틱 파드로 관리하거나 crontab에 등록)
# /etc/cron.d/etcd-backup
0 */6 * * * root /usr/local/bin/etcd-backup.sh >> /var/log/etcd-backup.log 2>&1
```

```bash
#!/bin/bash
# /usr/local/bin/etcd-backup.sh
SNAPSHOT_FILE="/tmp/etcd-snapshot-$(date +%Y%m%d-%H%M%S).db"
BUCKET="s3://my-cluster-backup/etcd"

etcdctl snapshot save "$SNAPSHOT_FILE" \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# 저장 성공 시에만 업로드
if [ $? -eq 0 ]; then
  aws s3 cp "$SNAPSHOT_FILE" "$BUCKET/"
  rm -f "$SNAPSHOT_FILE"
else
  echo "etcd snapshot failed at $(date)"
  exit 1
fi

# 7일 이상 된 스냅샷 정리
aws s3 ls "$BUCKET/" | awk '{print $4}' | while read f; do
  date_part=$(echo "$f" | grep -oP '\d{8}')
  if [[ ! -z "$date_part" ]]; then
    file_date=$(date -d "$date_part" +%s 2>/dev/null)
    cutoff=$(date -d "7 days ago" +%s)
    if [[ "$file_date" -lt "$cutoff" ]]; then
      aws s3 rm "$BUCKET/$f"
    fi
  fi
done
```

6시간 간격이 기본이지만, RPO를 1시간 이하로 잡아야 한다면 더 짧게 돌린다. etcd 스냅샷 자체는 수백 MB 수준이라 빈번하게 떠도 부담이 크지 않다.

### 2.2 etcd 스냅샷 복원

복원은 백업보다 훨씬 조심스럽다. 잘못 복원하면 기존에 살아 있던 데이터도 날아간다. 순서를 정확히 지켜야 한다.

**복원 전 필수 확인 사항**

- 복원할 스냅샷의 revision이 현재 etcd revision보다 오래된 것인지 확인한다. 최신 스냅샷 기준으로 복원해야 데이터 손실이 최소화된다.
- etcd 클러스터 멤버가 몇 개인지 확인한다. 멤버가 3개면 세 곳 모두 동시에 복원해야 한다. 하나만 복원하면 나머지 두 멤버가 쿼럼을 유지하면서 복원된 멤버를 뒤집어 버린다.
- 복원 중에는 API 서버를 내려야 한다. API 서버가 떠 있으면 복원 중인 etcd에 변경이 들어와 복원이 꼬인다.

```bash
# 1. API 서버 정지 (kubeadm 기준 — 스태틱 파드 매니페스트를 임시 이동)
mv /etc/kubernetes/manifests/kube-apiserver.yaml /tmp/
mv /etc/kubernetes/manifests/kube-controller-manager.yaml /tmp/
mv /etc/kubernetes/manifests/kube-scheduler.yaml /tmp/
mv /etc/kubernetes/manifests/etcd.yaml /tmp/

# 잠깐 기다려서 컨테이너가 실제로 내려가는지 확인
sleep 10
crictl ps | grep -E "apiserver|etcd|controller|scheduler"

# 2. 기존 etcd 데이터 백업 (혹시 몰라서)
mv /var/lib/etcd /var/lib/etcd.bak

# 3. 스냅샷 복원
etcdctl snapshot restore /backup/etcd-snapshot-20260721-120000.db \
  --name=master-1 \
  --initial-cluster=master-1=https://192.168.1.10:2380 \
  --initial-cluster-token=etcd-cluster-1 \
  --initial-advertise-peer-urls=https://192.168.1.10:2380 \
  --data-dir=/var/lib/etcd

# 4. 소유권 복구 (etcd 프로세스가 읽을 수 있어야 한다)
chown -R etcd:etcd /var/lib/etcd

# 5. 컨트롤 플레인 다시 올리기
mv /tmp/etcd.yaml /etc/kubernetes/manifests/
mv /tmp/kube-apiserver.yaml /etc/kubernetes/manifests/
mv /tmp/kube-controller-manager.yaml /etc/kubernetes/manifests/
mv /tmp/kube-scheduler.yaml /etc/kubernetes/manifests/

# 6. 복구 확인
kubectl get nodes
kubectl get pods -A
```

멀티 마스터(3개 이상)라면 각 마스터에서 `--name`과 `--initial-advertise-peer-urls`를 해당 노드에 맞게 바꿔서 동시에 실행한다. 순서는 상관없지만 전원 완료 전에 etcd를 시작하면 안 된다.

---

## 3. Velero — 워크로드와 볼륨 백업

etcd 스냅샷은 클러스터 상태를 복원하지만, 퍼시스턴트 볼륨(PV) 안의 데이터는 복원하지 못한다. 데이터베이스 파일, 업로드된 파일, 상태가 있는 서비스의 데이터는 PV 안에 있어서 etcd와 별개로 백업해야 한다. Velero는 쿠버네티스 리소스(네임스페이스 단위)와 PV 스냅샷을 함께 백업/복원하는 도구다.

### 3.1 Velero 설치

```bash
# AWS S3 백업 스토리지 기준 예시
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.9.0 \
  --bucket my-velero-backup \
  --backup-location-config region=ap-northeast-2 \
  --snapshot-location-config region=ap-northeast-2 \
  --secret-file ./credentials-velero

# credentials-velero 파일 형식
# [default]
# aws_access_key_id=AKIAIOSFODNN7EXAMPLE
# aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

설치 후 백업 스토리지가 정상인지 확인한다.

```bash
velero backup-location get
# NAME      PROVIDER   BUCKET/PREFIX           PHASE       LAST VALIDATED   ACCESS MODE
# default   aws        my-velero-backup        Available   10s ago          ReadWrite
```

### 3.2 스케줄 백업 설정

수동으로 백업을 뜨는 건 실수하기 쉬우므로 스케줄을 걸어 두는 게 기본이다.

```bash
# 전체 클러스터 백업 (모든 네임스페이스)
velero schedule create full-cluster-backup \
  --schedule="0 2 * * *" \
  --ttl 168h \
  --include-cluster-resources=true

# 특정 네임스페이스만 (production 네임스페이스)
velero schedule create production-backup \
  --schedule="0 */6 * * *" \
  --include-namespaces production \
  --ttl 72h \
  --snapshot-volumes=true

# 스케줄 목록 확인
velero schedule get
```

`--ttl`은 백업 보관 기간이다. 168h = 7일. 이 기간이 지나면 Velero가 자동으로 오래된 백업을 지운다. 오브젝트 스토리지 비용을 제어하려면 이 값을 목적에 맞게 설정해야 한다.

### 3.3 수동 백업과 복원

배포 직전이나 대규모 변경 전에는 수동으로 백업을 뜬다.

```bash
# 즉시 백업
velero backup create pre-deploy-backup-20260721 \
  --include-namespaces production \
  --snapshot-volumes=true \
  --wait

# 백업 상태 확인
velero backup describe pre-deploy-backup-20260721 --details

# 백업 목록
velero backup get
```

복원은 백업 이름을 지정해서 한다.

```bash
# 네임스페이스 전체 복원
velero restore create --from-backup pre-deploy-backup-20260721

# 특정 리소스만 복원 (ConfigMap만)
velero restore create --from-backup pre-deploy-backup-20260721 \
  --include-resources configmaps

# 다른 이름의 네임스페이스로 복원 (원본 유지하면서 복원 테스트)
velero restore create --from-backup pre-deploy-backup-20260721 \
  --namespace-mappings production:production-restore

# 복원 상태 확인
velero restore describe <restore-name>
velero restore logs <restore-name>
```

PV 복원 시 주의할 점: Velero는 PV를 스냅샷으로 찍고, 복원 시 그 스냅샷에서 새 PV를 만든다. 기존 PVC가 살아 있는 상태에서 같은 이름의 PVC를 복원하면 충돌이 난다. 기존 것을 먼저 지우거나 네임스페이스 매핑으로 다른 이름으로 복원해야 한다.

---

## 4. 스테이트풀 워크로드 복구 순서

StatefulSet, 특히 데이터베이스나 메시지 큐는 복구 순서가 틀리면 데이터가 더 날아가거나 서비스가 뒤틀린다. 순서가 중요한 이유는 이렇다.

첫째, StatefulSet의 파드는 순서가 있다 (pod-0, pod-1, pod-2). 첫 번째 파드가 Primary고 나머지가 Replica인 경우, Primary 없이 Replica가 먼저 뜨면 Replica가 잘못된 노드에 연결을 시도하거나 자기 자신을 Primary로 선출해 split-brain을 만든다.

둘째, PVC가 먼저 살아 있어야 파드가 붙을 수 있다. 파드 먼저 띄우고 PVC를 나중에 만들면 파드가 Pending 상태로 계속 기다린다.

실제 복구 순서는 이렇다.

```
1. PersistentVolumeClaim 복원 확인
2. ConfigMap / Secret 복원 확인
3. Service (Headless 포함) 복원 확인
4. StatefulSet 복원 (replicas=0으로 먼저)
5. Primary 파드(pod-0)만 수동으로 먼저 기동
6. Primary 상태 확인 후 나머지 파드 순차 기동
```

```bash
# 1. Velero로 네임스페이스 복원 후 PVC 상태 확인
kubectl get pvc -n production
# 모두 Bound 상태여야 한다

# 2. ConfigMap, Secret 복원 확인
kubectl get configmap,secret -n production

# 3. StatefulSet을 replicas=0으로 시작 (파드는 아직 안 뜨게)
kubectl scale statefulset postgres --replicas=0 -n production

# 4. Pod-0 하나만 먼저 띄우기
kubectl scale statefulset postgres --replicas=1 -n production

# Primary 상태 확인 (postgres 예시)
kubectl exec -n production postgres-0 -- psql -U postgres -c "SELECT pg_is_in_recovery();"
# f (false) 면 Primary. t 면 Replica 모드 — 이 경우 Primary가 없는 상태다.

# 5. 나머지 복제본 순차 기동
kubectl scale statefulset postgres --replicas=3 -n production
```

복구 순서에서 자주 놓치는 게 의존 관계다. 예를 들어 애플리케이션 Deployment가 DB의 Headless Service DNS 이름으로 연결한다면, DB Service가 복구되기 전에 앱이 먼저 뜨면 연결 실패로 크래시 루프에 빠진다. 앱보다 DB가 먼저 Ready 상태여야 한다.

이 순서를 보장하는 방법 중 하나는 Helm 차트에 `initContainer`를 넣어서 의존 서비스가 뜰 때까지 기다리게 하는 것이다.

```yaml
initContainers:
  - name: wait-for-postgres
    image: busybox:1.36
    command:
      - sh
      - -c
      - |
        until nc -z postgres-headless.production.svc.cluster.local 5432; do
          echo "Waiting for postgres..."
          sleep 2
        done
```

---

## 5. 클러스터 재구성 시 의존성 누락 문제

가장 시간을 많이 잡아먹는 부분이 여기다. etcd를 복원하고 Velero로 워크로드를 복원해도 서비스가 안 뜨는 경우가 자주 있다. 원인은 거의 항상 클러스터 내부 또는 외부의 의존성이 빠진 것이다.

### 5.1 흔히 빠지는 클러스터 내부 의존성

**Custom Resource Definition (CRD)**: CRD가 없으면 그 타입의 CR을 복원해도 "unknown resource" 오류가 난다. Prometheus의 `ServiceMonitor`, Istio의 `VirtualService`, cert-manager의 `Certificate` 같은 것들이 여기 해당한다. Velero가 CRD도 백업하긴 하지만, CRD를 별도로 설치해야 하는 경우 순서가 꼬인다. `--include-cluster-resources=true` 옵션을 명시하지 않으면 Velero가 CRD를 건너뛴다.

```bash
# 복원 후 CRD 확인
kubectl get crd | grep -E "cert-manager|istio|monitoring"

# CRD가 없으면 직접 적용
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.crds.yaml
```

**Admission Webhook**: ValidatingWebhookConfiguration, MutatingWebhookConfiguration이 복원됐는데 해당 웹훅 서버가 아직 안 떴으면, 모든 리소스 생성이 막힌다. 웹훅이 unavailable 상태면 쿠버네티스는 기본 동작에 따라 허용하거나 거부한다. 거부로 설정된 웹훅이 죽어 있으면 아무것도 만들 수가 없다. 이 상황에서는 웹훅을 먼저 살리거나, 임시로 웹훅 오브젝트를 지우고 의존 파드를 띄운 다음 다시 등록한다.

```bash
# 웹훅 목록 확인
kubectl get validatingwebhookconfigurations
kubectl get mutatingwebhookconfigurations

# 웹훅 서비스가 Ready인지
kubectl get pods -n cert-manager
kubectl get pods -n istio-system
```

**StorageClass**: PVC가 복원됐는데 참조하는 StorageClass가 없으면 PVC가 Pending으로 멈춘다. 새 클러스터에는 StorageClass가 기본으로 안 설치되어 있을 수 있다. 특히 cloud-provider-aws나 cloud-provider-gcp 같은 CSI 드라이버를 별도 설치해야 하는 환경에서 자주 발생한다.

```bash
kubectl get storageclass
# 비어 있으면 CSI 드라이버 설치부터
```

### 5.2 외부 의존성

**이미지 레지스트리**: 사설 레지스트리를 쓴다면 새 클러스터에서도 그 레지스트리에 접근할 수 있어야 한다. ImagePullSecret이 복원됐는지, 그리고 그 Secret에 담긴 자격증명이 아직 유효한지 확인한다. 자격증명이 만료됐거나 레지스트리 자체가 새 클러스터 IP를 모르면 이미지를 못 당긴다.

```bash
# ImagePullSecret 확인
kubectl get secret regcred -n production -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d

# 파드 이벤트 확인 (이미지 풀 실패 시 여기 나온다)
kubectl describe pod <pod-name> -n production | grep -A 5 Events
```

**외부 시크릿 매니저**: Vault, AWS Secrets Manager, GCP Secret Manager 같은 곳에서 시크릿을 당겨오는 구성이라면, 새 클러스터의 서비스 어카운트가 해당 시크릿에 접근 권한이 있는지 확인해야 한다. IRSA(IAM Roles for Service Accounts)나 Workload Identity를 쓴다면 새 클러스터의 OIDC provider를 등록해야 한다.

**외부 서비스 연결 허용**: DB, 캐시, 외부 API에 IP 화이트리스트가 걸려 있다면, 새 클러스터의 노드 IP를 등록해야 한다. 노드 IP가 바뀌었는데 화이트리스트에 없는 경우 연결이 묵묵히 거부된다.

---

## 6. 멀티 클러스터 페일오버

단일 클러스터 DR은 클러스터가 통째로 죽는 상황을 상정한다. 멀티 클러스터 페일오버는 Primary 클러스터가 죽었을 때 Secondary 클러스터로 트래픽을 넘기는 구성이다. 쿠버네티스에서 이걸 구성하는 방법은 크게 두 가지다.

### 6.1 DNS 기반 페일오버

가장 단순한 방법이다. Primary 클러스터의 인그레스 IP와 Secondary 클러스터의 인그레스 IP를 각각 DNS 레코드에 등록하고, 헬스체크로 Primary가 죽으면 Secondary로 자동 전환한다.

AWS Route 53의 Failover Routing, GCP의 Cloud DNS + 헬스체크 조합이 대표적이다.

```
클라이언트
    │
    ▼
Route 53 (Failover Routing)
    ├── PRIMARY: ap-northeast-2 클러스터 인그레스 (헬스체크 통과 시)
    └── SECONDARY: us-east-1 클러스터 인그레스 (PRIMARY 실패 시)
```

설계 시 고려할 점:
- DNS TTL을 짧게 (60초 이하) 유지해야 전환이 빠르다. 기본 TTL이 300초면 최대 5분간 죽은 클러스터로 요청이 간다.
- 헬스체크 주기와 실패 임계값을 조절해야 한다. 헬스체크 10초 주기, 실패 3회 기준이면 최소 30초 후에 전환이 시작된다. 그 후 DNS TTL이 소요된다.
- Secondary 클러스터가 평소에도 워크로드를 갖추고 있어야 한다. Secondary가 콜드 스탠바이라면 트래픽이 넘어와도 파드가 없다.

### 6.2 Federation과 GitOps 기반 동기화

멀티 클러스터를 운영할 때 두 클러스터를 항상 같은 상태로 유지하는 게 핵심이다. 수동으로 맞추는 건 금세 어긋난다. ArgoCD나 Flux 같은 GitOps 도구를 쓰면 Git 레포지토리를 단일 진실 출처(single source of truth)로 두고, 두 클러스터가 모두 거기서 동기화된다.

```
Git 레포지토리 (애플리케이션 매니페스트)
    │
    ├── ArgoCD (Primary 클러스터)  →  Primary 클러스터에 적용
    └── ArgoCD (Secondary 클러스터) →  Secondary 클러스터에 적용
```

이 구성에서 Secondary는 Primary와 동일한 워크로드가 항상 배포된 상태다. 페일오버는 트래픽만 넘기면 된다. 배포 지연도 없고, 의존성 누락도 없다. 대신 Secondary에도 컴퓨팅 비용이 발생한다.

ArgoCD ApplicationSet을 쓰면 여러 클러스터에 같은 앱을 배포하는 설정을 한 번에 관리할 수 있다.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: production-apps
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - cluster: primary
            url: https://primary-cluster.example.com
          - cluster: secondary
            url: https://secondary-cluster.example.com
  template:
    metadata:
      name: "{{cluster}}-production-apps"
    spec:
      project: default
      source:
        repoURL: https://github.com/myorg/k8s-manifests
        targetRevision: HEAD
        path: production/
      destination:
        server: "{{url}}"
        namespace: production
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

### 6.3 스테이트풀 워크로드의 멀티 클러스터 데이터 동기화

무상태(stateless) 워크로드는 멀티 클러스터 배포가 단순하다. 문제는 데이터가 있는 것들이다. DB를 두 클러스터에 각각 두면 데이터가 달라진다.

일반적으로 쓰는 방법은 두 가지다.

첫 번째는 데이터베이스를 클러스터 밖에 두는 것이다. RDS, Cloud SQL 같은 매니지드 DB를 쓰고, 두 클러스터가 같은 DB 엔드포인트를 바라보게 한다. 클러스터가 죽어도 DB는 살아 있으므로 Secondary 클러스터가 트래픽을 받으면 바로 같은 데이터를 쓴다. 이게 가장 단순하고 안전한 방법이다.

두 번째는 클러스터 내 DB를 리전 간 복제로 연결하는 것이다. MySQL의 비동기 replication, PostgreSQL의 streaming replication을 리전 간에 구성한다. 비동기라서 복제 지연이 있고, 페일오버 시 그 지연만큼 데이터가 유실될 수 있다. 구성도 복잡하다. 데이터를 클러스터 안에 두어야 하는 규정 때문이 아니라면, 매니지드 DB를 쓰는 게 낫다.

```
[외부 DB 활용 패턴]

Primary 클러스터   Secondary 클러스터
     앱 파드  ←───→  앱 파드
       │                │
       └────────┬───────┘
                ▼
         RDS Multi-AZ
         (두 클러스터가 공유)
```

---

## 7. 복구 리허설과 검증

DR 계획을 문서로만 두면 실제 사고 때 절반은 안 된다. 쿠버네티스 DR에서는 최소 두 가지 리허설을 정기적으로 해야 한다.

**Velero 복원 테스트**: 월 1회 이상, staging 환경에 production 백업을 복원해 본다. PV까지 포함해서 실제로 데이터가 살아나는지, 복원 시간이 RTO 안인지를 잰다.

```bash
# production 백업을 staging 네임스페이스로 복원
velero restore create dr-test-$(date +%Y%m%d) \
  --from-backup production-backup-latest \
  --namespace-mappings production:staging-dr-test

# 복원 완료 확인
velero restore describe dr-test-$(date +%Y%m%d)

# 데이터 확인 (예: postgres)
kubectl exec -n staging-dr-test postgres-0 -- \
  psql -U postgres -c "SELECT count(*) FROM orders;"
```

**etcd 복원 테스트**: 6개월에 한 번 이상, 별도 테스트 클러스터에 etcd 스냅샷을 복원해 본다. 운영 클러스터에서 직접 하면 위험하므로 동일 버전의 테스트 클러스터를 준비한다. 복원 절차 자체가 문서대로 작동하는지, 인증서 경로가 맞는지, 복원 후 API 서버가 뜨는지를 확인한다.

리허설에서 자주 나오는 문제:

- etcd 스냅샷 파일은 있는데 복원 시 "snapshot file doesn't exist or corrupt" 오류가 난다. 백업 자동화 스크립트에서 저장 성공 여부를 확인하지 않아 빈 파일이 업로드된 경우다. 백업 완료 후 `etcdctl snapshot status`로 검증하는 단계를 반드시 넣어야 한다.
- Velero 복원이 성공했는데 파드가 안 뜬다. ImagePullSecret이 복원됐지만 자격증명이 만료된 경우, 또는 CRD가 없어서 CR 리소스를 못 만드는 경우다.
- PVC는 복원됐는데 PV가 Released 상태여서 재바인딩이 안 된다. 기존 PVC를 지우지 않고 복원을 시도할 때 발생한다. PV의 `spec.claimRef`를 지우면 Available 상태로 돌아온다.

```bash
# Released PV를 재바인딩 가능하게 만들기
kubectl patch pv <pv-name> -p '{"spec":{"claimRef": null}}'
```

---

## 8. 정리

쿠버네티스 DR은 etcd와 워크로드 데이터라는 두 레이어를 각각 다른 방법으로 보호해야 완성된다. etcd 스냅샷은 클러스터 상태 전체를 되살리지만 PV 안의 데이터는 못 살린다. Velero는 PV까지 포함한 워크로드를 복원하지만 클러스터 자체가 죽으면 먼저 etcd를 살린 다음에야 쓸 수 있다.

복구 순서를 잘못 잡으면 StatefulSet이 split-brain 상태가 되거나, 의존성 누락으로 파드가 뜨지 않는다. Admission Webhook, CRD, StorageClass, ImagePullSecret — 이런 클러스터 인프라 요소들은 애플리케이션 파드보다 먼저 살아 있어야 한다.

멀티 클러스터 페일오버는 GitOps로 두 클러스터를 항상 동기화된 상태로 유지하는 게 가장 확실하다. 스테이트풀 워크로드는 가능하면 클러스터 밖의 매니지드 서비스에 두는 게 복잡도를 크게 줄인다.

리허설 없는 DR 계획은 계획이 아니다. etcd 스냅샷 복원과 Velero 복원을 정기적으로 테스트해야 실제 사고 때 쓸 수 있다.
