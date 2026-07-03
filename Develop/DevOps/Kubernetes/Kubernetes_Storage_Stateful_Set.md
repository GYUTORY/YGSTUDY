---
title: Kubernetes 스토리지와 StatefulSet
tags: [devops, kubernetes, k8s, storage, pv, pvc, storageclass, statefulset, csi]
updated: 2026-06-16
---

# Kubernetes 스토리지와 StatefulSet

Kubernetes.md에서 PVC를 짧게 다뤘다. 여기서는 PV/PVC/StorageClass가 실제로 어떻게 묶이는지, StatefulSet으로 DB나 메시지 브로커처럼 상태를 가진 워크로드를 굴릴 때 막히는 지점을 정리한다. 처음 PVC 하나 붙여서 Postgres를 띄울 때는 별 문제가 없다가, Pod를 재배포하거나 스케일을 건드리는 순간 "왜 Pending에서 안 넘어가지", "왜 데이터가 사라졌지" 같은 일이 생긴다. 대부분 accessMode, reclaimPolicy, 그리고 StatefulSet의 PVC 수명 규칙을 모르고 넘어가서 터진다.

## 1. PV, PVC, StorageClass가 묶이는 방식

세 리소스의 역할은 이렇게 나뉜다.

- PV(PersistentVolume): 실제 스토리지 자원. EBS 볼륨 하나, NFS export 한 경로 같은 물리적 실체에 대응한다. 클러스터 스코프 리소스다.
- PVC(PersistentVolumeClaim): "20Gi SSD 하나 달라"는 요청. 네임스페이스 스코프다.
- StorageClass: PVC가 들어왔을 때 PV를 어떻게 만들지 정의하는 규칙. 동적 프로비저닝의 핵심이다.

```
Pod ──참조──▶ PVC ──바인딩──▶ PV ──연결──▶ 실제 스토리지 (EBS/NFS/...)
                 │
                 └─ StorageClass가 PV를 자동 생성
```

옛날 방식은 관리자가 PV를 미리 손으로 만들어두고, PVC가 들어오면 조건이 맞는 PV에 바인딩하는 정적 프로비저닝이었다. 지금은 거의 쓰지 않는다. StorageClass를 지정한 PVC를 만들면 프로비저너가 EBS 볼륨을 만들고 PV를 생성해서 바인딩까지 자동으로 한다.

### 동적 프로비저닝

StorageClass 정의 예시다. AWS EKS의 gp3 기준이다.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  encrypted: "true"
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

여기서 `volumeBindingMode: WaitForFirstConsumer`가 운영상 중요하다. 기본값인 `Immediate`로 두면 PVC를 만든 순간 볼륨이 프로비저닝된다. 문제는 그 시점에 어느 노드에 Pod가 뜰지 모른다는 것이다. EBS는 AZ에 묶이는데, 볼륨이 ap-northeast-2a에 만들어졌는데 Pod 스케줄러가 2c 노드를 골라버리면 볼륨을 붙일 수 없어서 Pod가 영원히 Pending에 걸린다. `WaitForFirstConsumer`로 두면 Pod가 스케줄될 노드가 정해진 뒤에 같은 AZ에 볼륨을 만든다. 멀티 AZ 클러스터라면 이 옵션을 반드시 켜야 한다.

### 클러스터의 기본 StorageClass

PVC에 `storageClassName`을 안 적으면 기본 StorageClass가 쓰인다. 기본이 무엇인지는 어노테이션으로 정해진다.

```bash
kubectl get storageclass
# NAME            PROVISIONER       RECLAIMPOLICY   ...
# gp2 (default)   ebs.csi.aws.com   Delete          ...
# gp3             ebs.csi.aws.com   Delete          ...
```

EKS는 한동안 gp2가 기본이었다. gp2는 용량에 IOPS가 묶여서 작은 볼륨은 느리다. 기본값을 그대로 쓰다가 DB가 느려서 보면 gp2인 경우가 있다. 기본 StorageClass를 gp3로 바꾸거나, PVC마다 명시적으로 적는 편이 낫다. `storageClassName: ""`(빈 문자열)을 적으면 동적 프로비저닝을 끄고 정적 PV에만 바인딩하라는 뜻이라 의미가 다르니 주의한다.

## 2. accessMode — 이름만 보고 오해하기 쉽다

accessMode는 셋이 있다.

- ReadWriteOnce(RWO): 하나의 노드에서 읽기/쓰기
- ReadOnlyMany(ROX): 여러 노드에서 읽기 전용
- ReadWriteMany(RWX): 여러 노드에서 읽기/쓰기

여기서 자주 틀리는 게 RWO다. "한 Pod만 붙일 수 있다"로 읽는 사람이 많은데, 정확히는 **한 노드**다. 같은 노드에 스케줄된 여러 Pod는 같은 RWO 볼륨을 동시에 마운트할 수 있다. 다른 노드의 Pod는 못 붙는다. 이 차이가 롤링 업데이트에서 문제가 된다.

Deployment에 RWO PVC를 붙여놓고 `replicas: 2`로 올리면, 두 Pod가 서로 다른 노드에 뜨는 순간 한쪽은 볼륨을 못 붙여서 ContainerCreating에 걸린다. 그래서 RWO 볼륨을 쓰는 워크로드는 사실상 단일 Pod이거나, 노드 어피니티로 같은 노드에 묶거나, StatefulSet으로 Pod마다 별도 볼륨을 줘야 한다.

RWX가 필요한 대표적인 경우는 여러 Pod가 같은 파일을 공유해야 할 때다. 예를 들어 업로드된 이미지를 여러 웹 Pod가 같이 읽고 쓰는 구조. 문제는 RWX를 지원하는 스토리지가 제한적이라는 것이다. EBS는 RWX를 못 한다(io2 멀티어태치는 블록 레벨이라 파일시스템 공유와 다르고, 일반 워크로드에서 쓸 게 못 된다). RWX를 하려면 EFS(NFS), Azure Files, CephFS 같은 파일 스토리지가 필요하다. 그래서 "여러 Pod가 파일 공유" 요구가 나오면 스토리지 종류부터 바꿔야 하는 경우가 많다.

RWX를 NFS로 붙이면 파일 락이나 fsync 동작이 로컬 디스크와 달라서, 그 위에 SQLite나 일반 DB를 올리면 깨진다. RWX 파일 스토리지는 정적 파일 공유 용도로만 쓰고, DB 데이터 디렉토리로는 쓰지 않는다.

## 3. reclaimPolicy와 데이터 유실

reclaimPolicy는 PVC가 삭제됐을 때 그에 묶인 PV와 실제 스토리지를 어떻게 처리할지 정한다.

- Delete: PVC를 지우면 PV와 실제 볼륨(EBS 등)까지 삭제된다. 동적 프로비저닝의 기본값이다.
- Retain: PVC를 지워도 PV와 실제 볼륨은 남는다. 수동으로 정리해야 한다.

동적 프로비저닝 StorageClass의 기본이 Delete라는 게 사고의 원인이 된다. 누가 PVC를 잘못 지우거나, 네임스페이스를 통째로 `kubectl delete namespace` 하면, 그 안의 PVC가 사라지면서 EBS 볼륨까지 같이 날아간다. 스냅샷이 없으면 복구가 안 된다.

운영 DB 볼륨이라면 StorageClass의 reclaimPolicy를 Retain으로 두는 걸 고려한다. 다만 Retain은 PVC를 다시 만들어도 남은 PV에 자동으로 바인딩되지 않는다. Retain된 PV는 `Released` 상태로 남는데, 이 상태의 PV는 다른 PVC가 바인딩하지 못한다. PV의 `spec.claimRef`를 손으로 비워야 다시 쓸 수 있다.

```bash
# Retain으로 남은 PV를 재사용하려면 claimRef를 제거
kubectl patch pv <pv-name> -p '{"spec":{"claimRef":null}}'
```

실수로 PVC를 지워서 PV가 Released가 됐다면, 그 PV의 실제 볼륨(EBS) 데이터는 아직 남아 있다. claimRef를 비우고 새 PVC를 같은 PV에 수동 바인딩하면 데이터를 살릴 수 있다. Delete 정책이었다면 이 단계에서 이미 데이터가 없다.

이미 만들어진 PV의 reclaimPolicy는 나중에 바꿀 수 있다.

```bash
kubectl patch pv <pv-name> -p '{"spec":{"persistentVolumeReclaimPolicy":"Retain"}}'
```

## 4. PVC 확장

용량이 모자라면 PVC를 키울 수 있다. 단 StorageClass에 `allowVolumeExpansion: true`가 있어야 한다. 확장은 키우는 방향만 된다. 줄이는 건 안 된다.

```bash
# PVC의 요청 용량을 수정
kubectl edit pvc db-storage
# spec.resources.requests.storage 를 20Gi -> 50Gi 로 변경
```

확장이 바로 끝나지 않는 경우가 있다. CSI 드라이버가 두 단계로 처리하기 때문이다. 먼저 클라우드 쪽 볼륨 크기를 키우고(이건 온라인으로 됨), 그다음 파일시스템을 늘린다. 파일시스템 확장은 볼륨이 노드에 마운트된 상태에서 일어나는데, 드라이버나 커널 버전에 따라 Pod 재시작이 필요할 때가 있다. PVC를 키웠는데 `df -h`로 보면 그대로면, Pod를 한 번 재시작해보면 반영된다.

PVC 상태에서 진행 상황을 볼 수 있다.

```bash
kubectl describe pvc db-storage
# Conditions:
#   Type                      Status
#   FileSystemResizePending   True   <- 파일시스템 확장 대기 중
```

확장이 자주 필요하면 처음부터 넉넉하게 잡는 게 낫다. 한번 키운 볼륨은 못 줄이니, 줄이려면 새 볼륨 만들어서 데이터 복사밖에 방법이 없다.

## 5. StatefulSet

Deployment는 Pod를 서로 구분하지 않는다. 이름도 랜덤 해시가 붙고, 죽으면 새 이름으로 뜨고, 어느 Pod가 먼저 떠야 한다는 순서도 없다. 웹 서버처럼 상태가 없는 워크로드엔 맞다. 하지만 DB 클러스터, Kafka, ZooKeeper처럼 각 인스턴스가 고유한 정체성을 가져야 하는 경우엔 안 맞는다. StatefulSet은 그 정체성을 보장한다.

StatefulSet이 Deployment와 다른 점은 셋이다.

1. 안정적인 네트워크 ID: Pod 이름이 `<statefulset>-0`, `<statefulset>-1` 처럼 순번으로 고정된다. 재시작해도 같은 이름으로 돌아온다.
2. 안정적인 스토리지: 각 Pod가 자기만의 PVC를 갖고, Pod가 죽었다 살아나도 같은 PVC에 다시 붙는다.
3. 순차 배포/스케일: 0번이 Ready가 돼야 1번을 만든다. 삭제는 역순으로 한다.

### Headless Service와 Pod DNS

StatefulSet은 Headless Service(`clusterIP: None`)와 짝으로 쓴다. 그래야 각 Pod에 고정 DNS 이름이 생긴다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
spec:
  clusterIP: None        # Headless
  selector:
    app: postgres
  ports:
    - port: 5432
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres  # 위 Headless Service 이름과 일치해야 함
  replicas: 3
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:16
          ports:
            - containerPort: 5432
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: gp3
        resources:
          requests:
            storage: 20Gi
```

이렇게 띄우면 각 Pod에 다음 DNS 이름이 생긴다.

```
postgres-0.postgres.<namespace>.svc.cluster.local
postgres-1.postgres.<namespace>.svc.cluster.local
postgres-2.postgres.<namespace>.svc.cluster.local
```

`serviceName`을 Headless Service 이름과 다르게 적으면 이 DNS가 안 생긴다. 처음 셋업할 때 자주 빠뜨리는 부분이다. DB 복제 구성에서 "postgres-0을 프라이머리로 보고 나머지가 붙어라" 같은 설정을 할 때 이 고정 이름이 필요하다.

### volumeClaimTemplates

`volumeClaimTemplates`가 StatefulSet의 핵심이다. Deployment처럼 PVC를 따로 만들어서 참조하는 게 아니라, 템플릿을 주면 Pod마다 PVC를 자동으로 만든다. 위 예시면 PVC가 이렇게 생긴다.

```bash
kubectl get pvc
# NAME              STATUS   VOLUME    CAPACITY   ...
# data-postgres-0   Bound    pvc-...   20Gi
# data-postgres-1   Bound    pvc-...   20Gi
# data-postgres-2   Bound    pvc-...   20Gi
```

PVC 이름이 `<템플릿명>-<statefulset>-<순번>`으로 고정된다. postgres-1 Pod가 죽어서 다른 노드에서 다시 떠도 `data-postgres-1`에 다시 붙는다. 그래서 1번 인스턴스의 데이터는 1번을 따라다닌다. 이게 DB를 StatefulSet으로 굴리는 이유다.

### 순차 배포가 주는 함정

StatefulSet은 0 → 1 → 2 순서로 뜬다. 0번이 Ready가 안 되면 1번은 아예 생성되지 않는다. 의도된 동작이지만, 0번 Pod의 readinessProbe가 잘못 잡혀 있으면 전체가 0번에서 멈춘다. 처음 배포했는데 postgres-0만 뜨고 1, 2가 안 보이면 0번이 Ready가 아닌 거다. `kubectl describe pod postgres-0`로 프로브 상태부터 본다.

순서가 꼭 필요 없으면 `podManagementPolicy: Parallel`로 바꿔서 동시에 띄울 수 있다. 다만 마스터-슬레이브 순서가 중요한 DB라면 기본값(OrderedReady)을 그대로 둔다.

스케일 다운도 역순이라, `replicas: 3`을 `1`로 줄이면 2번, 1번이 차례로 죽는다. 여기서 중요한 게 **PVC는 같이 안 지워진다는 점**이다.

## 6. StatefulSet에서 PVC 삭제는 자동이 아니다

StatefulSet을 스케일 다운하거나 통째로 지워도 `volumeClaimTemplates`로 만들어진 PVC는 남는다. 이게 안전장치다. DB Pod가 사라졌다고 데이터까지 날리면 안 되니까. 스케일을 다시 올리면 남아 있던 PVC에 그대로 다시 붙는다.

문제는 정리할 때다. StatefulSet을 지워도 PVC가 남으니, 진짜로 데이터까지 없애려면 PVC를 따로 지워야 한다.

```bash
kubectl delete statefulset postgres
kubectl get pvc        # data-postgres-0 ~ 2 가 그대로 남아있음
kubectl delete pvc data-postgres-0 data-postgres-1 data-postgres-2
```

그리고 이 PVC를 지우는 순간, StorageClass가 Delete 정책이면 EBS 볼륨까지 사라진다(3절 참고). "StatefulSet 지웠으니 PVC도 정리하자"고 무심코 지웠다가 데이터를 날리는 경우가 여기서 나온다.

1.23부터 `persistentVolumeClaimRetentionPolicy`로 이 동작을 조절할 수 있다.

```yaml
spec:
  persistentVolumeClaimRetentionPolicy:
    whenDeleted: Retain    # StatefulSet 삭제 시 PVC 유지 (기본값)
    whenScaled: Delete     # 스케일 다운 시 줄어든 Pod의 PVC 삭제
```

`whenScaled: Delete`로 두면 스케일 다운할 때 줄어든 순번의 PVC가 자동으로 지워진다. 임시 클러스터나 테스트 환경에서 PVC가 쌓이는 걸 막을 때 쓴다. 운영 DB라면 기본값인 Retain을 유지하는 게 안전하다.

## 7. CSI 드라이버

예전엔 스토리지 연동 코드가 쿠버네티스 본체(in-tree)에 들어 있었다. AWS EBS, GCE PD 같은 게 코어 코드에 박혀 있어서, 스토리지 벤더가 뭘 고치려면 쿠버네티스 릴리스를 기다려야 했다. CSI(Container Storage Interface)는 이걸 밖으로 빼서 표준 인터페이스로 만든 것이다. 지금은 in-tree 드라이버가 대부분 제거됐고, EKS에서 EBS를 쓰려면 `aws-ebs-csi-driver`를 애드온으로 깔아야 한다.

CSI 드라이버는 보통 두 부분으로 돈다. Controller(프로비저닝, 어태치/디태치, 스냅샷 담당)와 각 노드의 Node 컴포넌트(마운트 담당)다. 흔히 겪는 문제 두 가지가 있다.

EKS에서 PVC가 계속 Pending이면 CSI 드라이버 컨트롤러의 IAM 권한부터 본다. EBS 볼륨을 만들려면 드라이버에 IRSA(서비스 어카운트 IAM 역할)로 EC2 권한이 붙어 있어야 한다. 권한이 없으면 PVC가 Pending에 머물고, CSI 컨트롤러 Pod 로그에 `UnauthorizedOperation` 같은 게 찍힌다.

```bash
kubectl describe pvc <name>      # Events에서 ProvisioningFailed 확인
kubectl logs -n kube-system -l app=ebs-csi-controller -c csi-provisioner
```

노드를 갈아끼울 때 볼륨 디태치가 안 끝나서 새 Pod가 ContainerCreating에 오래 걸리는 경우도 있다. 노드가 갑자기 죽으면(스팟 인스턴스 회수 등) 컨트롤 플레인이 그 노드에서 볼륨을 떼어내는 데 시간이 걸린다. 멀티어태치 안 되는 EBS는 옛 노드에서 디태치가 끝나야 새 노드에 붙는다. `Multi-Attach error` 메시지가 보이면 이 상황이다. 대개 시간이 지나면 풀리지만, 안 풀리면 VolumeAttachment 리소스를 봐야 한다.

```bash
kubectl get volumeattachment
```

## 8. DB를 StatefulSet으로 운영할 때 실제로 겪는 것

StatefulSet이 DB를 위한 것처럼 보이지만, StatefulSet은 스토리지와 네트워크 정체성만 보장한다. 그 위의 복제, 페일오버, 백업은 전부 직접 해야 한다. postgres-0이 죽으면 쿠버네티스는 postgres-0을 같은 PVC로 다시 띄울 뿐, "1번을 프라이머리로 승격해라" 같은 건 안 해준다. 이 로직은 애플리케이션이나 오퍼레이터가 담당한다.

그래서 운영 DB는 직접 StatefulSet을 짜기보다 오퍼레이터를 쓰는 경우가 많다. CloudNativePG, Zalando Postgres Operator, Strimzi(Kafka) 같은 게 복제 구성과 페일오버, 백업을 자동화한다. 오퍼레이터도 내부적으로는 StatefulSet(또는 그에 준하는 컨트롤러)을 만들지만, 그 위의 운영 로직을 얹어준다. 오퍼레이터 개념은 Kubernetes_Operator_및_CRD.md에서 다룬다.

직접 StatefulSet으로 DB를 굴린다면 부딪히는 것들이다.

- 스토리지 성능: gp3 기본 IOPS(3000)로는 부하 큰 DB가 버겁다. iops/throughput을 StorageClass에서 올리거나, io2 같은 등급을 쓴다. PVC를 만든 뒤엔 성능 등급을 못 바꾸는 경우가 있어서 처음에 정해야 한다.
- AZ 고정: EBS는 AZ에 묶인다. postgres-0의 볼륨이 2a에 있으면 postgres-0은 항상 2a 노드에만 뜬다. 2a의 노드가 부족하면 Pod가 스케줄이 안 된다. 멀티 AZ로 분산하려면 `WaitForFirstConsumer`와 토폴로지 인식이 같이 받쳐줘야 한다.
- 백업: PVC 스냅샷(VolumeSnapshot)으로 볼륨 단위 백업은 되지만, 트랜잭션 일관성까지 보장하려면 DB 레벨 백업(pg_dump, WAL 아카이빙)이 따로 필요하다. 볼륨 스냅샷만 믿다가 복구 시점에 깨진 데이터를 만나는 경우가 있다.
- 버전 업그레이드: StatefulSet의 롤링 업데이트는 순번 역순으로 Pod를 하나씩 교체한다. DB 메이저 버전 업그레이드는 데이터 디렉토리 포맷이 바뀌는 경우가 있어서, 단순 이미지 태그 변경만으로는 안 되고 별도 마이그레이션 절차가 필요하다.

정리하면, StatefulSet은 DB를 올리기 위한 토대를 깔아줄 뿐 DB 운영을 대신해주지 않는다. 관리형 DB(RDS, Aurora 등)를 쓸 수 있는 상황이면 그쪽이 운영 부담이 훨씬 적다. 쿠버네티스 안에 DB를 둬야 하는 이유가 명확할 때(온프렘, 비용, 특정 확장 요구 등) StatefulSet이나 오퍼레이터를 선택한다.
