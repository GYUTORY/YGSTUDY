---
title: Reconciliation Loop
tags: [kubernetes, controller, operator, reconciliation, controller-runtime]
updated: 2026-07-30
---

# Reconciliation Loop

Kubernetes의 모든 자원 관리는 reconciliation loop로 돌아간다. Pod 하나가 죽었을 때 ReplicaSet이 새 Pod를 띄우고, 노드 하나가 사라졌을 때 스케줄러가 다시 배치하는 것도 모두 같은 원리다.

핵심은 "지금 상태가 원하는 상태와 다르면 맞춰라"다. 이걸 반복한다.

## Observe-Diff-Act 패턴

컨트롤러는 세 단계를 순환한다.

**Observe**: API 서버에서 현재 상태를 읽는다. 직접 폴링하지 않고 Informer가 etcd 이벤트를 watch해서 로컬 캐시(indexer)에 반영한다. 컨트롤러는 이 캐시를 읽는다.

**Diff**: `spec`(원하는 상태)와 실제 상태를 비교한다. 실제 상태는 `status` 필드이거나 외부 시스템의 상태(AWS EC2 인스턴스 상태 등)일 수 있다.

**Act**: 차이가 있으면 행동한다. API 서버에 자원을 만들거나 수정하고, 외부 API를 호출하고, 결과를 `status`에 기록한다.

이벤트 기반처럼 보이지만 실제로는 상태 기반이다. 특정 이벤트(Pod 삭제됨)에 반응하는 게 아니라, 매번 전체 desired state를 기준으로 현재 상태와 비교한다. 컨트롤러가 재시작해도, 이벤트를 놓쳐도 결국 수렴한다.

## controller-manager 내부 구조

`kube-controller-manager`는 단일 바이너리지만 30개 이상의 컨트롤러를 묶어서 실행한다.

- **Deployment 컨트롤러**: Deployment spec을 보고 ReplicaSet을 만들거나 수정한다.
- **ReplicaSet 컨트롤러**: ReplicaSet의 `replicas`를 보고 Pod를 추가/삭제한다.
- **Node 컨트롤러**: 노드 하트비트가 끊기면 NotReady 상태로 바꾸고, 일정 시간 후 Pod를 evict한다.
- **Endpoint 컨트롤러**: Service와 Pod를 매핑해서 Endpoints 객체를 업데이트한다.
- **Service Account 컨트롤러**: 새 Namespace에 default 서비스 어카운트를 자동 생성한다.

각 컨트롤러는 독립적으로 동작하지만 모두 같은 API 서버를 통해 통신한다. Deployment를 수정하면 Deployment 컨트롤러가 ReplicaSet을 수정하고, ReplicaSet 컨트롤러가 Pod를 수정하는 식으로 체인이 이어진다.

## Work Queue와 Requeue

Informer가 이벤트를 감지하면 컨트롤러의 work queue에 해당 자원의 key(`namespace/name`)를 넣는다. 컨트롤러는 이 큐에서 꺼내서 처리한다.

work queue의 특성이 몇 가지 있다.

- **중복 제거**: 같은 key가 여러 번 들어와도 하나로 합친다. 이벤트가 몰려도 한 번만 처리한다.
- **레이트 리미팅**: 처리가 실패하면 지수 백오프(exponential backoff)로 재시도 간격을 늘린다. 기본값은 5ms~1000s 범위다.
- **병렬 처리**: 큐에서 동시에 여러 worker가 꺼내서 처리할 수 있다.

reconcile이 실패하면 두 가지 선택이 있다.

```go
// 에러를 반환하면 자동으로 requeue (지수 백오프 적용)
return ctrl.Result{}, err

// 명시적으로 특정 시간 후 재시도
return ctrl.Result{RequeueAfter: 30 * time.Second}, nil

// 성공. 다음 이벤트까지 대기
return ctrl.Result{}, nil
```

외부 리소스(DB 연결, 클라우드 API)가 일시적으로 실패했을 때는 에러를 반환해서 자동 requeue를 쓰는 편이 낫다. "30초 후에 상태를 다시 확인해야 한다" 같은 경우엔 `RequeueAfter`를 쓴다.

## 커스텀 컨트롤러(Operator) 작성

`controller-runtime` 라이브러리로 Operator를 작성할 때 reconciliation의 핵심은 `Reconcile` 함수다.

```go
func (r *MyAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    log := log.FromContext(ctx)

    // 1. Observe: 현재 자원 상태 읽기
    myApp := &appsv1.MyApp{}
    if err := r.Get(ctx, req.NamespacedName, myApp); err != nil {
        if apierrors.IsNotFound(err) {
            // 자원이 삭제됨. 정리 작업이 필요하면 여기서 처리
            return ctrl.Result{}, nil
        }
        return ctrl.Result{}, err
    }

    // 2. Diff: 원하는 상태와 현재 상태 비교
    deployment := &appsv1.Deployment{}
    err := r.Get(ctx, types.NamespacedName{Name: myApp.Name, Namespace: myApp.Namespace}, deployment)

    if apierrors.IsNotFound(err) {
        // 3. Act: Deployment가 없으면 생성
        newDeployment := r.buildDeployment(myApp)
        if err := r.Create(ctx, newDeployment); err != nil {
            return ctrl.Result{}, err
        }
        return ctrl.Result{}, nil
    }

    // Deployment가 있으면 spec 비교 후 업데이트
    if !reflect.DeepEqual(deployment.Spec, r.buildDeployment(myApp).Spec) {
        deployment.Spec = r.buildDeployment(myApp).Spec
        if err := r.Update(ctx, deployment); err != nil {
            return ctrl.Result{}, err
        }
    }

    // 4. Status 업데이트
    myApp.Status.Ready = deployment.Status.ReadyReplicas == *deployment.Spec.Replicas
    if err := r.Status().Update(ctx, myApp); err != nil {
        return ctrl.Result{}, err
    }

    return ctrl.Result{}, nil
}
```

`Reconcile` 함수는 멱등성(idempotency)이 있어야 한다. 같은 자원으로 몇 번 호출되어도 결과가 동일해야 한다. 자원을 생성하기 전에 반드시 존재 여부를 확인하고, 업데이트 전에 실제로 변경이 필요한지 확인한다.

## 무한 루프 문제

reconcile에서 자원을 수정하면, 그 수정이 이벤트를 발생시키고, 다시 reconcile이 트리거된다. 잘못되면 무한 루프에 빠진다.

흔한 실수는 `status`를 업데이트할 때 메인 자원 전체를 업데이트하는 것이다.

```go
// 잘못된 방식 - spec과 status를 같이 업데이트하면 루프 발생
myApp.Status.Ready = true
r.Update(ctx, myApp) // spec 변경도 이벤트 트리거 -> 재진입 발생

// 올바른 방식 - status 서브리소스만 업데이트
r.Status().Update(ctx, myApp) // status 변경만 이벤트 트리거
```

`Status().Update()`는 status 서브리소스만 건드려서 불필요한 이벤트를 줄인다. CRD에 `status` 서브리소스를 정의해야 동작한다.

또 다른 루프 원인은 `Generation` 체크를 빠뜨리는 것이다. `metadata.generation`은 spec이 바뀔 때만 증가한다. status 변경으로 인한 이벤트는 generation이 같으므로 무시할 수 있다.

```go
// status 업데이트로 인한 불필요한 reconcile 건너뛰기
if myApp.Generation == myApp.Status.ObservedGeneration {
    return ctrl.Result{}, nil
}
```

## 충돌과 낙관적 잠금

여러 컨트롤러가 같은 자원을 동시에 수정하면 충돌이 난다. Kubernetes는 낙관적 잠금(optimistic locking)을 쓰는데, `resourceVersion` 필드가 버전 토큰 역할을 한다.

```
Error: Operation cannot be fulfilled on deployments.apps "my-app":
the object has been modified; please apply your changes to the latest version
and try again
```

이 에러가 나오면 최신 버전을 다시 읽어서 재시도해야 한다. `controller-runtime`은 에러를 반환하면 자동으로 requeue하므로, 단순히 에러를 반환하면 된다.

```go
if err := r.Update(ctx, deployment); err != nil {
    if apierrors.IsConflict(err) {
        return ctrl.Result{}, err // 자동 requeue
    }
    return ctrl.Result{}, err
}
```

Server-Side Apply를 쓰면 이 문제를 완화할 수 있다. 필드 소유권을 명시해서 같은 컨트롤러가 관리하는 필드끼리만 충돌이 난다.

## 재진입(Re-entrancy) 문제

`Reconcile`이 실행 중인데 같은 자원에 대한 이벤트가 또 들어오면 어떻게 될까?

work queue는 처리 중인 아이템을 큐에서 꺼내 놓는다(processing 상태). 처리 중에 들어온 새 이벤트는 큐에 쌓여 대기한다. 현재 `Reconcile`이 끝난 후에 다음 이벤트를 처리한다. 즉, 같은 자원에 대한 `Reconcile`은 동시에 실행되지 않는다.

다만 worker 수를 늘리면 다른 자원은 병렬 처리된다.

```go
ctrl.NewControllerManagedBy(mgr).
    For(&appsv1.MyApp{}).
    WithOptions(controller.Options{MaxConcurrentReconciles: 5}).
    Complete(r)
```

같은 자원 타입의 서로 다른 인스턴스는 병렬로 reconcile된다. 같은 인스턴스는 직렬화된다.

## Leader Election과 Reconciliation

컨트롤러를 HA(고가용성)로 구성하면 여러 인스턴스가 실행된다. reconciliation은 한 인스턴스만 해야 한다. 여러 인스턴스가 동시에 같은 자원을 수정하면 충돌이 반복된다.

`controller-runtime`은 leader election을 내장 지원한다.

```go
mgr, err := ctrl.NewManager(ctrl.GetConfigOrDie(), ctrl.Options{
    LeaderElection:          true,
    LeaderElectionID:        "my-operator-leader",
    LeaderElectionNamespace: "default",
})
```

내부적으로 Lease 자원을 사용한다. leader가 주기적으로 Lease를 갱신하고, follower는 Lease가 만료될 때까지 대기한다. leader가 죽으면 Lease가 만료되고, follower 중 하나가 새 leader가 된다.

leader election이 걸려 있는 동안 non-leader 인스턴스는 HTTP 서버(healthz, readyz)만 실행한다. reconciliation은 완전히 멈춘다.

failover 시 새 leader는 처음부터 전체 자원 목록을 sync한다(full resync). 이때 이벤트가 한꺼번에 큐에 들어오므로 처음 구동 시 부하가 몰릴 수 있다.

## Argo CD Sync와의 차이

Argo CD의 sync는 Kubernetes reconciliation loop와 다른 레벨이다.

Kubernetes controller의 reconciliation은 클러스터 내부 상태를 수렴시킨다. Deployment spec에 맞춰 ReplicaSet을 만드는 것처럼 API 서버의 desired state를 인프라에 반영한다.

Argo CD sync는 Git 저장소의 매니페스트를 클러스터에 적용하는 것이다. Git을 source of truth로 보고, Git 상태와 클러스터 상태를 비교한다.

| | Kubernetes Reconciliation | Argo CD Sync |
|---|---|---|
| 비교 기준 | API 서버 spec vs 실제 인프라 | Git 매니페스트 vs 클러스터 자원 |
| 실행 주체 | controller-manager | Argo CD Application Controller |
| 주기 | 이벤트 기반 (즉시) | 폴링 기반 (기본 3분) |
| 범위 | 단일 자원 타입 | 애플리케이션 전체 |

Argo CD가 sync를 하면 kubectl apply와 유사하게 매니페스트를 API 서버에 넣는다. 그 뒤 Kubernetes controller가 실제 인프라로 reconcile하는 식이다. Argo CD는 두 번째 단계를 직접 하지 않는다.

Argo CD의 `OutOfSync` 상태는 Git과 클러스터가 다르다는 뜻이고, Kubernetes의 `NotReady`나 `Progressing`은 클러스터 내부 reconciliation이 진행 중이라는 뜻이다. 둘은 다른 레이어의 상태다.

## 트러블슈팅

**컨트롤러가 이벤트를 받지 못하는 경우**

Informer 캐시가 아직 sync되지 않았을 수 있다. 컨트롤러 시작 로그에 "Starting workers"가 찍혀 있으면 캐시 sync가 완료된 것이다.

```bash
kubectl logs -n kube-system kube-controller-manager-... | grep "reconcil"
```

**reconcile이 계속 실패하는 경우**

work queue의 base delay는 5ms지만 최대 1000초까지 늘어난다. 이 상태가 되면 자원 상태가 수렴하지 못하고 stuck 상태가 된다. 에러 원인을 찾아서 수정하거나, 컨트롤러를 재시작해서 delay를 초기화한다.

**status가 업데이트되지 않는 경우**

CRD에 status 서브리소스가 정의되어 있어야 `Status().Update()`가 동작한다.

```yaml
spec:
  subresources:
    status: {}  # 이게 없으면 Status().Update()가 동작 안 함
```

**자원이 삭제되지 않는 경우**

finalizer가 남아 있으면 자원이 삭제되지 않는다. 컨트롤러가 죽어서 finalizer를 제거하지 못한 경우다.

```bash
# finalizer 강제 제거 (임시방편)
kubectl patch myapp my-resource -p '{"metadata":{"finalizers":[]}}' --type=merge
```

컨트롤러가 정상 동작하면 스스로 finalizer를 제거해야 한다. 강제 제거는 정리 로직이 실행되지 않으므로 외부 리소스가 남을 수 있다.
