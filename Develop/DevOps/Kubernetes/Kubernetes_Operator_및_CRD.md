---
title: Kubernetes Operator 및 CRD
tags: [kubernetes, operator, crd, custom-resource, controller-runtime, operator-sdk]
updated: 2026-04-12
---

# Kubernetes Operator 및 CRD

## 1. Operator 패턴이란

Kubernetes의 기본 리소스(Deployment, Service 등)만으로는 처리하기 어려운 운영 로직이 있다. 예를 들어 MySQL 클러스터를 Kubernetes 위에 올린다고 하면, 단순히 Pod를 띄우는 것 외에 레플리카 구성, 백업 스케줄링, 페일오버 처리 같은 작업이 필요하다. 이런 걸 사람이 매번 수동으로 하면 실수가 생기고, 자동화 스크립트를 짜면 Kubernetes의 선언형 모델과 맞지 않게 된다.

Operator는 이 문제를 해결한다. **"사람이 하던 운영 작업을 코드로 만들어서 Kubernetes 컨트롤러로 돌리는 것"**이 Operator 패턴의 핵심이다.

```
일반적인 Kubernetes 동작:

사용자 → kubectl apply → API Server → Controller → 리소스 생성/관리

Operator 패턴:

사용자 → kubectl apply (Custom Resource) → API Server → Operator(Custom Controller) → 복잡한 운영 로직 자동 수행
```

### 1.1 Reconciliation Loop

Operator의 동작 원리는 **Reconciliation Loop(조정 루프)**다. 단순하게 말하면 "원하는 상태(Desired State)와 현재 상태(Current State)를 비교해서, 다르면 맞춰주는 것"을 반복한다.

```
Reconciliation Loop:

1. Watch: Custom Resource 변경 이벤트 감지
2. Read: 현재 클러스터 상태 조회
3. Compare: 원하는 상태 vs 현재 상태 비교
4. Act: 차이가 있으면 조정 (리소스 생성/수정/삭제)
5. Update Status: CR의 status 필드 업데이트
6. 1번으로 돌아감
```

여기서 중요한 점은 **멱등성(Idempotency)**이다. Reconcile 함수는 여러 번 호출되어도 결과가 같아야 한다. "이미 존재하면 생성하지 않고, 스펙이 다르면 업데이트"하는 식으로 구현해야 한다. 이걸 무시하면 리소스가 중복 생성되거나 무한 업데이트 루프에 빠진다.

### 1.2 Operator = CRD + Custom Controller

Operator는 두 가지로 구성된다.

| 구성 요소 | 역할 |
|-----------|------|
| **CRD (Custom Resource Definition)** | Kubernetes API에 새로운 리소스 타입을 등록한다 |
| **Custom Controller** | 해당 리소스의 변경을 감지하고 실제 작업을 수행한다 |

CRD 없이 Controller만 있으면 감시할 대상이 없고, CRD만 있고 Controller가 없으면 리소스를 만들 수는 있지만 아무 동작도 하지 않는다.

---

## 2. Custom Resource Definition (CRD) 작성법

### 2.1 CRD 기본 구조

CRD는 Kubernetes API에 새로운 리소스 타입을 등록하는 설정 파일이다. 예시로 `MyDatabase`라는 커스텀 리소스를 만들어 본다.

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: mydatabases.example.com   # 반드시 <plural>.<group> 형식
spec:
  group: example.com
  versions:
    - name: v1alpha1
      served: true                 # API Server가 이 버전을 서빙할지
      storage: true                # etcd에 이 버전으로 저장할지
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required: ["engine", "replicas"]
              properties:
                engine:
                  type: string
                  enum: ["mysql", "postgres"]
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 5
                storage:
                  type: string
                  default: "10Gi"
            status:
              type: object
              properties:
                phase:
                  type: string
                readyReplicas:
                  type: integer
      subresources:
        status: {}                 # status 서브리소스 활성화
      additionalPrinterColumns:    # kubectl get 할 때 보이는 컬럼
        - name: Engine
          type: string
          jsonPath: .spec.engine
        - name: Replicas
          type: integer
          jsonPath: .spec.replicas
        - name: Phase
          type: string
          jsonPath: .status.phase
  scope: Namespaced
  names:
    plural: mydatabases
    singular: mydatabase
    kind: MyDatabase
    shortNames:
      - mydb
```

### 2.2 CRD 작성 시 주의할 점

**metadata.name 규칙**: `<plural>.<group>` 형식을 따라야 한다. 이 규칙을 어기면 CRD 등록 자체가 실패한다.

**버전 관리**: 처음에는 `v1alpha1`으로 시작하고, 안정화되면 `v1beta1` → `v1`으로 올린다. `storage: true`는 하나의 버전에만 설정할 수 있다. 여러 버전을 동시에 서빙하려면 Conversion Webhook을 구현해야 하는데, 이건 상당히 복잡하다. 가능하면 버전을 하나로 유지하는 게 낫다.

**스키마 검증**: `openAPIV3Schema`에 타입, 필수 필드, enum, 범위 등을 꼼꼼하게 정의해야 한다. 스키마가 느슨하면 잘못된 값이 들어와도 API Server가 통과시키고, 그 에러는 Controller 쪽에서 처리해야 한다.

**status 서브리소스**: `subresources.status`를 설정하면 `/status` 엔드포인트가 별도로 생긴다. 사용자가 `spec`을 수정할 때 `status`가 같이 덮어씌워지는 문제를 방지할 수 있다. Operator를 만든다면 거의 필수다.

### 2.3 Custom Resource 생성

CRD를 등록한 후에는 해당 타입의 리소스를 만들 수 있다.

```yaml
apiVersion: example.com/v1alpha1
kind: MyDatabase
metadata:
  name: my-mysql
  namespace: default
spec:
  engine: mysql
  replicas: 3
  storage: "20Gi"
```

```bash
kubectl apply -f mydatabase-crd.yaml    # CRD 먼저 등록
kubectl apply -f my-mysql.yaml          # CR 생성
kubectl get mydb                        # shortName으로 조회
```

---

## 3. controller-runtime 기반 구현

Go로 Operator를 만들 때는 대부분 [controller-runtime](https://github.com/kubernetes-sigs/controller-runtime) 라이브러리를 사용한다. client-go를 직접 쓰는 것보다 보일러플레이트가 훨씬 적다.

### 3.1 프로젝트 구조

```
my-operator/
├── api/
│   └── v1alpha1/
│       ├── mydatabase_types.go      # CR의 Go 타입 정의
│       ├── groupversion_info.go     # GVK 등록
│       └── zz_generated.deepcopy.go # 자동 생성
├── controllers/
│   └── mydatabase_controller.go     # Reconcile 로직
├── config/
│   ├── crd/                         # CRD YAML (자동 생성)
│   ├── rbac/                        # RBAC 설정
│   └── manager/                     # Manager 배포 설정
├── main.go
├── go.mod
└── Makefile
```

### 3.2 타입 정의 (api/v1alpha1/mydatabase_types.go)

```go
package v1alpha1

import (
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// MyDatabaseSpec은 사용자가 정의하는 원하는 상태
type MyDatabaseSpec struct {
    Engine   string `json:"engine"`
    Replicas int32  `json:"replicas"`
    Storage  string `json:"storage,omitempty"`
}

// MyDatabaseStatus는 Controller가 업데이트하는 현재 상태
type MyDatabaseStatus struct {
    Phase         string `json:"phase,omitempty"`
    ReadyReplicas int32  `json:"readyReplicas,omitempty"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:printcolumn:name="Engine",type=string,JSONPath=`.spec.engine`
// +kubebuilder:printcolumn:name="Replicas",type=integer,JSONPath=`.spec.replicas`
// +kubebuilder:printcolumn:name="Phase",type=string,JSONPath=`.status.phase`

type MyDatabase struct {
    metav1.TypeMeta   `json:",inline"`
    metav1.ObjectMeta `json:"metadata,omitempty"`

    Spec   MyDatabaseSpec   `json:"spec,omitempty"`
    Status MyDatabaseStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true
type MyDatabaseList struct {
    metav1.TypeMeta `json:",inline"`
    metav1.ListMeta `json:"metadata,omitempty"`
    Items           []MyDatabase `json:"items"`
}

func init() {
    SchemeBuilder.Register(&MyDatabase{}, &MyDatabaseList{})
}
```

`+kubebuilder:` 주석은 코드 생성기가 참조하는 마커다. 이걸로 CRD YAML, DeepCopy 메서드, RBAC 설정이 자동 생성된다.

### 3.3 Reconcile 로직 (controllers/mydatabase_controller.go)

```go
package controllers

import (
    "context"
    "fmt"

    appsv1 "k8s.io/api/apps/v1"
    corev1 "k8s.io/api/core/v1"
    "k8s.io/apimachinery/pkg/api/errors"
    "k8s.io/apimachinery/pkg/api/resource"
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/apimachinery/pkg/runtime"
    "k8s.io/apimachinery/pkg/types"
    ctrl "sigs.k8s.io/controller-runtime"
    "sigs.k8s.io/controller-runtime/pkg/client"
    "sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
    "sigs.k8s.io/controller-runtime/pkg/log"

    examplev1 "my-operator/api/v1alpha1"
)

type MyDatabaseReconciler struct {
    client.Client
    Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=example.com,resources=mydatabases,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=example.com,resources=mydatabases/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=apps,resources=statefulsets,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups="",resources=services,verbs=get;list;watch;create;update;patch;delete

func (r *MyDatabaseReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    logger := log.FromContext(ctx)

    // 1. CR 조회
    var db examplev1.MyDatabase
    if err := r.Get(ctx, req.NamespacedName, &db); err != nil {
        if errors.IsNotFound(err) {
            // CR이 삭제된 경우. 소유 리소스는 OwnerReference로 자동 정리됨
            return ctrl.Result{}, nil
        }
        return ctrl.Result{}, err
    }

    // 2. StatefulSet 생성 또는 업데이트
    sts := &appsv1.StatefulSet{
        ObjectMeta: metav1.ObjectMeta{
            Name:      db.Name,
            Namespace: db.Namespace,
        },
    }

    result, err := controllerutil.CreateOrUpdate(ctx, r.Client, sts, func() error {
        // StatefulSet 스펙 설정
        replicas := db.Spec.Replicas
        sts.Spec.Replicas = &replicas
        sts.Spec.Selector = &metav1.LabelSelector{
            MatchLabels: map[string]string{"app": db.Name},
        }
        sts.Spec.Template = corev1.PodTemplateSpec{
            ObjectMeta: metav1.ObjectMeta{
                Labels: map[string]string{"app": db.Name},
            },
            Spec: corev1.PodSpec{
                Containers: []corev1.Container{
                    {
                        Name:  "database",
                        Image: getImage(db.Spec.Engine),
                        Ports: []corev1.ContainerPort{
                            {ContainerPort: getPort(db.Spec.Engine)},
                        },
                    },
                },
            },
        }
        sts.Spec.VolumeClaimTemplates = []corev1.PersistentVolumeClaim{
            {
                ObjectMeta: metav1.ObjectMeta{Name: "data"},
                Spec: corev1.PersistentVolumeClaimSpec{
                    AccessModes: []corev1.PersistentVolumeAccessMode{
                        corev1.ReadWriteOnce,
                    },
                    Resources: corev1.VolumeResourceRequirements{
                        Requests: corev1.ResourceList{
                            corev1.ResourceStorage: resource.MustParse(db.Spec.Storage),
                        },
                    },
                },
            },
        }

        // OwnerReference 설정 — CR 삭제 시 StatefulSet도 같이 삭제됨
        return controllerutil.SetControllerReference(&db, sts, r.Scheme)
    })

    if err != nil {
        return ctrl.Result{}, fmt.Errorf("StatefulSet 처리 실패: %w", err)
    }
    logger.Info("StatefulSet 처리 완료", "result", result)

    // 3. Headless Service 생성 (StatefulSet에 필요)
    svc := &corev1.Service{
        ObjectMeta: metav1.ObjectMeta{
            Name:      db.Name + "-headless",
            Namespace: db.Namespace,
        },
    }

    _, err = controllerutil.CreateOrUpdate(ctx, r.Client, svc, func() error {
        svc.Spec.ClusterIP = "None"
        svc.Spec.Selector = map[string]string{"app": db.Name}
        svc.Spec.Ports = []corev1.ServicePort{
            {Port: getPort(db.Spec.Engine)},
        }
        return controllerutil.SetControllerReference(&db, svc, r.Scheme)
    })

    if err != nil {
        return ctrl.Result{}, fmt.Errorf("Service 처리 실패: %w", err)
    }

    // 4. Status 업데이트
    db.Status.Phase = "Running"
    db.Status.ReadyReplicas = sts.Status.ReadyReplicas
    if err := r.Status().Update(ctx, &db); err != nil {
        return ctrl.Result{}, fmt.Errorf("Status 업데이트 실패: %w", err)
    }

    return ctrl.Result{}, nil
}

func getImage(engine string) string {
    switch engine {
    case "mysql":
        return "mysql:8.0"
    case "postgres":
        return "postgres:15"
    default:
        return "mysql:8.0"
    }
}

func getPort(engine string) int32 {
    switch engine {
    case "mysql":
        return 3306
    case "postgres":
        return 5432
    default:
        return 3306
    }
}

func (r *MyDatabaseReconciler) SetupWithManager(mgr ctrl.Manager) error {
    return ctrl.NewControllerManagedBy(mgr).
        For(&examplev1.MyDatabase{}).
        Owns(&appsv1.StatefulSet{}).    // StatefulSet 변경도 감지
        Owns(&corev1.Service{}).        // Service 변경도 감지
        Complete(r)
}
```

### 3.4 Reconcile 구현 시 흔한 실수

**상태 업데이트 충돌**: `Status().Update()` 호출 시 conflict 에러가 나는 경우가 많다. 다른 곳에서 같은 리소스를 수정했기 때문인데, 이때는 최신 객체를 다시 가져와서 업데이트해야 한다. `retry.RetryOnConflict`를 쓰는 것도 방법이다.

**무한 루프**: Reconcile 안에서 리소스를 수정하면 다시 이벤트가 발생해서 Reconcile이 호출된다. `CreateOrUpdate`는 실제로 변경이 없으면 업데이트하지 않기 때문에 대부분 괜찮지만, Status를 매번 덮어쓰면 루프가 돌 수 있다. 현재 값과 비교해서 달라졌을 때만 업데이트하는 게 안전하다.

**OwnerReference 빠뜨림**: `SetControllerReference`를 안 하면 CR을 삭제해도 하위 리소스(StatefulSet, Service 등)가 남는다. 수동으로 정리해야 하는 상황이 생긴다.

**에러 시 재시도**: Reconcile에서 에러를 리턴하면 controller-runtime이 exponential backoff로 재시도한다. `ctrl.Result{RequeueAfter: time.Minute}`를 리턴하면 지정한 시간 후에 다시 호출된다. 외부 시스템과 연동하는 경우 일정 간격으로 상태를 확인하는 패턴으로 쓸 수 있다.

---

## 4. Operator SDK 사용법

[Operator SDK](https://sdk.operatorframework.io/)는 Operator를 빠르게 만들 수 있는 CLI 도구다. 프로젝트 스캐폴딩, 코드 생성, 테스트, 배포까지 한 번에 처리한다.

### 4.1 프로젝트 생성

```bash
# Operator SDK 설치 (macOS)
brew install operator-sdk

# 프로젝트 초기화
mkdir my-operator && cd my-operator
operator-sdk init --domain example.com --repo my-operator

# API 및 Controller 생성
operator-sdk create api \
  --group database \
  --version v1alpha1 \
  --kind MyDatabase \
  --resource --controller
```

이 명령어를 실행하면 앞서 설명한 프로젝트 구조가 자동으로 만들어진다. `api/v1alpha1/mydatabase_types.go`에 타입을 정의하고, `controllers/mydatabase_controller.go`에 Reconcile 로직을 채우면 된다.

### 4.2 개발 → 테스트 → 배포 흐름

```bash
# 1. 타입 정의 후 코드 생성
make generate    # DeepCopy 메서드 생성
make manifests   # CRD, RBAC YAML 생성

# 2. 로컬에서 테스트 (클러스터에 CRD만 설치하고, Controller는 로컬에서 실행)
make install     # CRD를 클러스터에 설치
make run         # Controller를 로컬에서 실행

# 3. 이미지 빌드 및 배포
make docker-build docker-push IMG=myregistry/my-operator:v0.1.0
make deploy IMG=myregistry/my-operator:v0.1.0

# 4. 정리
make undeploy
make uninstall
```

`make run`으로 로컬 실행하면 디버거를 붙일 수 있어서 개발 중에는 이 방식이 편하다. kubeconfig의 권한을 그대로 쓰기 때문에 RBAC 문제도 없다.

### 4.3 Operator SDK가 생성하는 Makefile 타겟

| 타겟 | 동작 |
|------|------|
| `make generate` | `controller-gen`으로 DeepCopy 등 코드 생성 |
| `make manifests` | CRD, RBAC, Webhook YAML 생성 |
| `make install` | CRD를 현재 클러스터에 설치 |
| `make run` | Controller를 로컬에서 실행 |
| `make docker-build` | Operator 이미지 빌드 |
| `make deploy` | Operator를 클러스터에 배포 (Deployment + RBAC) |
| `make bundle` | OLM 번들 생성 (카탈로그 배포 시 필요) |

### 4.4 테스트 작성

Operator SDK는 envtest을 사용한 통합 테스트 환경을 기본으로 제공한다. 실제 etcd와 API Server를 로컬에 띄워서 테스트한다.

```go
var _ = Describe("MyDatabase Controller", func() {
    const (
        name      = "test-db"
        namespace = "default"
    )

    Context("MyDatabase CR을 생성하면", func() {
        It("StatefulSet이 만들어져야 한다", func() {
            ctx := context.Background()

            // CR 생성
            db := &examplev1.MyDatabase{
                ObjectMeta: metav1.ObjectMeta{
                    Name:      name,
                    Namespace: namespace,
                },
                Spec: examplev1.MyDatabaseSpec{
                    Engine:   "mysql",
                    Replicas: 3,
                    Storage:  "10Gi",
                },
            }
            Expect(k8sClient.Create(ctx, db)).Should(Succeed())

            // StatefulSet 생성 확인
            stsKey := types.NamespacedName{Name: name, Namespace: namespace}
            sts := &appsv1.StatefulSet{}

            Eventually(func() error {
                return k8sClient.Get(ctx, stsKey, sts)
            }, timeout, interval).Should(Succeed())

            Expect(*sts.Spec.Replicas).Should(Equal(int32(3)))
        })
    })
})
```

`Eventually`로 비동기 상태를 기다리는 패턴은 Operator 테스트에서 자주 쓴다. Reconcile이 비동기로 동작하기 때문에 `Get` 직후에 리소스가 있을 거라 가정하면 테스트가 깨진다.

---

## 5. Operator를 직접 만들어야 하는 경우 vs 기존 Operator를 쓰는 경우

### 5.1 기존 Operator를 쓰는 경우

대부분의 상황에서는 이미 만들어진 Operator를 쓰는 게 맞다. [OperatorHub.io](https://operatorhub.io/)에서 검색하면 주요 미들웨어나 데이터베이스 Operator가 다 있다.

실무에서 자주 쓰는 Operator 목록:

| 이름 | 용도 | 관리 주체 |
|------|------|-----------|
| **cert-manager** | TLS 인증서 자동 발급/갱신 | CNCF |
| **Prometheus Operator** | 모니터링 스택 관리 | CoreOS/Red Hat |
| **Strimzi** | Kafka 클러스터 관리 | CNCF Sandbox |
| **CloudNativePG** | PostgreSQL 클러스터 관리 | CNCF Sandbox |
| **MySQL Operator** | MySQL InnoDB Cluster 관리 | Oracle |
| **Redis Operator** | Redis Sentinel/Cluster 관리 | Spotahome 등 |
| **ArgoCD** | GitOps CD 파이프라인 | CNCF |

기존 Operator를 도입할 때 확인해야 할 것:

- **성숙도**: GitHub 스타 수보다는 릴리스 히스토리와 이슈 대응 속도를 본다. 1년 넘게 릴리스가 없으면 사실상 방치된 프로젝트일 수 있다.
- **CRD 호환성**: Kubernetes 버전 업그레이드 시 CRD API 버전이 맞는지 확인한다. `apiextensions.k8s.io/v1beta1`만 지원하는 Operator는 K8s 1.22 이상에서 동작하지 않는다.
- **RBAC 범위**: 클러스터 전체 권한을 요구하는 Operator가 있다. 네임스페이스 단위로 격리해야 하는 환경에서는 문제가 된다.
- **업그레이드 경로**: Operator 자체를 업그레이드할 때 CRD 스키마 마이그레이션이 필요한 경우가 있다. 릴리스 노트에서 breaking change를 확인해야 한다.

### 5.2 직접 만들어야 하는 경우

다음 상황에서는 직접 만드는 것을 고려한다.

**회사 내부 인프라 자동화**: 예를 들어 내부 인증 시스템과 연동해서 서비스 계정을 자동 프로비저닝하거나, 사내 네트워크 정책을 애플리케이션별로 자동 적용하는 경우. 이런 건 범용 Operator가 없다.

**멀티 리소스 오케스트레이션**: 하나의 CR로 Deployment + Service + ConfigMap + Ingress + NetworkPolicy를 한 번에 만들고 관리하고 싶은 경우. Helm으로도 할 수 있지만, 배포 후 상태 관리(자동 복구, 스케일링 조건 등)까지 포함하면 Operator가 맞다.

**기존 Operator의 커스터마이징 한계**: 예를 들어 Prometheus Operator를 쓰는데, 특정 메트릭에 따라 자동으로 AlertRule을 생성/삭제하는 로직이 필요한 경우. 기존 Operator를 포크하는 것보다 위에 얹는 Operator를 하나 더 만드는 게 유지보수하기 쉽다.

**외부 시스템 연동**: AWS RDS 인스턴스를 Kubernetes CR로 관리하거나, 사내 CMDB와 동기화하는 경우. ACK(AWS Controllers for Kubernetes) 같은 게 있긴 하지만, 자체 시스템과의 연동은 직접 만들 수밖에 없다.

### 5.3 직접 만들 때 고려할 점

**Finalizer 처리**: CR 삭제 시 외부 리소스(클라우드 리소스, 외부 API 등)를 정리해야 하면 Finalizer를 구현해야 한다. Finalizer가 걸려 있으면 Kubernetes가 CR을 바로 삭제하지 않고, Controller가 정리 작업을 마치고 Finalizer를 제거할 때까지 기다린다.

```go
const finalizerName = "database.example.com/finalizer"

func (r *MyDatabaseReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    var db examplev1.MyDatabase
    if err := r.Get(ctx, req.NamespacedName, &db); err != nil {
        return ctrl.Result{}, client.IgnoreNotFound(err)
    }

    // 삭제 중인 경우
    if !db.DeletionTimestamp.IsZero() {
        if controllerutil.ContainsFinalizer(&db, finalizerName) {
            // 외부 리소스 정리
            if err := r.cleanupExternalResources(&db); err != nil {
                return ctrl.Result{}, err
            }
            // Finalizer 제거
            controllerutil.RemoveFinalizer(&db, finalizerName)
            if err := r.Update(ctx, &db); err != nil {
                return ctrl.Result{}, err
            }
        }
        return ctrl.Result{}, nil
    }

    // Finalizer 등록
    if !controllerutil.ContainsFinalizer(&db, finalizerName) {
        controllerutil.AddFinalizer(&db, finalizerName)
        if err := r.Update(ctx, &db); err != nil {
            return ctrl.Result{}, err
        }
    }

    // ... 이하 일반 Reconcile 로직
    return ctrl.Result{}, nil
}
```

**Leader Election**: Operator를 여러 인스턴스로 띄울 때 하나만 활성화되도록 해야 한다. controller-runtime의 Manager에 LeaderElection 옵션이 있다.

```go
mgr, err := ctrl.NewManager(ctrl.GetConfigOrDie(), ctrl.Options{
    LeaderElection:   true,
    LeaderElectionID: "my-operator-lock",
})
```

**리소스 캐싱**: controller-runtime은 내부적으로 informer 캐시를 사용한다. 모든 네임스페이스의 모든 리소스를 캐싱하면 메모리를 많이 쓴다. 특정 네임스페이스만 감시하거나, 필요한 필드만 캐싱하도록 설정하는 게 좋다.

```go
mgr, err := ctrl.NewManager(ctrl.GetConfigOrDie(), ctrl.Options{
    Cache: cache.Options{
        DefaultNamespaces: map[string]cache.Config{
            "target-namespace": {},
        },
    },
})
```

---

## 6. 정리

Operator는 Kubernetes의 선언형 모델을 확장해서 복잡한 운영 로직을 자동화하는 패턴이다. CRD로 API를 정의하고, Controller로 원하는 상태를 유지하는 구조다.

직접 만들 때는 Operator SDK로 스캐폴딩하고, controller-runtime의 `CreateOrUpdate`, `SetControllerReference`, Finalizer 같은 유틸리티를 적극 활용한다. Reconcile 함수는 반드시 멱등하게 구현하고, 무한 루프와 상태 업데이트 충돌에 주의해야 한다.

기존 Operator가 있으면 먼저 써보고, 정말 필요한 경우에만 직접 만드는 게 운영 부담을 줄이는 길이다. Operator를 만드는 건 쉽지만, 장기적으로 유지보수하고 버전 호환성을 관리하는 건 생각보다 손이 많이 간다.
