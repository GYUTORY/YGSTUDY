---
title: "GCE (Google Compute Engine)"
tags:
  - GCP
  - Compute Engine
  - VM
  - Infrastructure
updated: 2026-04-06
---

# GCE (Google Compute Engine)

GCE는 GCP에서 제공하는 가상 머신 서비스다. AWS의 EC2에 대응한다. 인스턴스를 직접 생성하고 관리해야 하는 IaaS 서비스이므로 네트워크, 디스크, 방화벽까지 신경 써야 한다.

---

## 인스턴스 생성

### gcloud CLI로 생성

콘솔에서 클릭으로 만들 수도 있지만, 반복 작업이 많으면 CLI가 낫다.

```bash
gcloud compute instances create my-instance \
  --zone=asia-northeast3-a \
  --machine-type=e2-medium \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=50GB \
  --boot-disk-type=pd-balanced \
  --tags=http-server,https-server
```

`--zone`은 반드시 지정한다. 생략하면 기본 zone을 쓰는데, 프로젝트 설정에 따라 예상과 다른 리전에 생성될 수 있다. 한국 서비스라면 `asia-northeast3` (서울) 리전을 사용한다.

`--tags`는 방화벽 규칙과 연결된다. `http-server` 태그를 달아도 방화벽 규칙이 없으면 80포트가 열리지 않는다. 콘솔에서 "HTTP 트래픽 허용" 체크박스를 누르면 자동으로 방화벽 규칙까지 만들어주지만, CLI로 할 때는 직접 만들어야 한다.

```bash
gcloud compute firewall-rules create allow-http \
  --direction=INGRESS \
  --action=ALLOW \
  --rules=tcp:80 \
  --target-tags=http-server
```

### 자주 빠뜨리는 설정

**서비스 계정 범위(Scope)**

인스턴스 생성 시 `--scopes` 를 지정하지 않으면 기본 서비스 계정에 제한된 scope가 붙는다. 나중에 인스턴스 안에서 GCS 버킷에 접근하려고 하면 403이 뜬다. 인스턴스를 멈추고 scope를 변경한 뒤 다시 시작해야 한다.

```bash
# 생성 시 필요한 scope를 미리 지정
gcloud compute instances create my-instance \
  --scopes=cloud-platform \
  ...
```

`cloud-platform` scope는 모든 GCP API에 접근 가능하다. 보안상 꺼려지면 필요한 scope만 나열한다. 하지만 실제 권한은 서비스 계정의 IAM 역할로 제어하기 때문에, scope는 넉넉하게 주고 IAM에서 세밀하게 잡는 방식이 관리하기 편하다.

**외부 IP**

`--no-address` 옵션을 주면 외부 IP 없이 생성된다. NAT 게이트웨이를 설정하지 않은 상태에서 이렇게 만들면 인스턴스에서 인터넷 접속이 안 된다. `apt update`도 안 되고 패키지 설치도 안 된다. 개발 환경에서는 외부 IP를 붙이는 게 편하다.

---

## 머신 타입 선택

### 시리즈별 특징

| 시리즈 | 용도 | 비용 |
|--------|------|------|
| E2 | 범용, 개발/테스트 환경 | 가장 저렴 |
| N2/N2D | 범용, 프로덕션 워크로드 | E2보다 10~20% 비쌈 |
| C2/C2D | CPU 집약적 작업 (빌드 서버, 인코딩) | 높음 |
| M2/M3 | 메모리 집약적 (대용량 DB, SAP) | 매우 높음 |
| T2D | Arm 기반, 비용 효율 | N2 대비 20~30% 저렴 |

### 실무에서 선택하는 기준

**개발/스테이징 환경**: `e2-medium` (vCPU 2, 메모리 4GB)이면 대부분 충분하다. Spring Boot 애플리케이션 하나 돌리기에 적당하다. 메모리가 부족하면 `e2-standard-2` (vCPU 2, 메모리 8GB)로 올린다.

**프로덕션 환경**: `n2-standard-4` (vCPU 4, 메모리 16GB) 정도에서 시작한다. N2 시리즈는 E2보다 단일 스레드 성능이 높다. 트래픽에 따라 수평 확장을 고려한다면 인스턴스 하나를 크게 잡는 것보다 작은 인스턴스 여러 개가 낫다.

**커스텀 머신 타입**: vCPU와 메모리를 원하는 조합으로 지정할 수 있다. 메모리는 많이 필요한데 CPU는 적게 필요한 경우에 쓴다. 표준 타입보다 단가가 약간 높다.

```bash
# 커스텀 머신 타입: vCPU 4, 메모리 24GB
gcloud compute instances create my-instance \
  --custom-cpu=4 \
  --custom-memory=24GB \
  --zone=asia-northeast3-a
```

### 잘못된 선택을 하면

머신 타입은 인스턴스를 중지한 뒤 변경할 수 있다. 운영 중인 서비스라면 다운타임이 발생한다. 처음에 적절한 타입을 고르는 게 중요한데, GCP 콘솔의 "머신 타입 추천" 기능은 최소 며칠 간의 모니터링 데이터가 쌓여야 작동한다. 신규 프로젝트에서는 도움이 안 된다.

---

## 선점형 VM (Spot VM)

### 개념

선점형 VM은 GCP의 남는 자원을 저렴하게 빌려 쓰는 인스턴스다. 일반 인스턴스 대비 60~91% 저렴하지만, GCP가 자원을 회수해야 할 때 24시간 이내에 종료될 수 있다. 기존에는 "Preemptible VM"이라고 불렀고, 현재는 "Spot VM"으로 이름이 바뀌었다. 기능은 거의 같지만 Spot VM은 24시간 제한이 없다(대신 여전히 언제든 종료될 수 있다).

```bash
gcloud compute instances create batch-worker \
  --provisioning-model=SPOT \
  --instance-termination-action=STOP \
  --zone=asia-northeast3-a \
  --machine-type=e2-standard-4
```

`--instance-termination-action`은 `STOP`과 `DELETE` 중 선택한다. 디스크를 보존해야 하면 `STOP`으로 설정한다.

### 쓸 만한 경우

- CI/CD 빌드 러너: 빌드가 중단되면 다시 돌리면 된다
- 배치 처리: 작업을 청크로 나눠서 중간 결과를 저장하는 구조라면 적합하다
- 데이터 전처리: 대량의 로그 파싱이나 ETL 작업

### 쓰면 안 되는 경우

- 사용자 요청을 직접 처리하는 웹 서버
- 상태를 로컬에 보관하는 서비스 (세션을 로컬 메모리에 저장하는 경우 등)
- SLA가 필요한 서비스

### 종료 알림 처리

Spot VM은 종료 30초 전에 메타데이터 서버를 통해 알림을 보낸다. 이 알림을 받아서 graceful shutdown을 할 수 있다.

```python
import requests
import time

METADATA_URL = "http://metadata.google.internal/computeMetadata/v1/instance/preempted"
HEADERS = {"Metadata-Flavor": "Google"}

def check_preemption():
    while True:
        resp = requests.get(METADATA_URL, headers=HEADERS)
        if resp.text == "TRUE":
            print("선점 알림 수신, 정리 작업 시작")
            # 진행 중인 작업 저장, 커넥션 정리 등
            break
        time.sleep(5)
```

실무에서는 이 코드를 직접 짜기보다 인스턴스 그룹 + 자동 복구 정책을 함께 구성하는 경우가 많다.

---

## 비용 관련 주의사항

### 중지된 인스턴스도 돈이 나간다

인스턴스를 중지(STOP)하면 CPU/메모리 요금은 안 나오지만, 디스크 요금은 계속 나간다. 100GB pd-balanced 디스크를 한 달 붙여두면 약 $10이다. 테스트용 인스턴스를 중지만 해놓고 방치하면 디스크 비용이 쌓인다. 안 쓰는 인스턴스는 삭제한다. 디스크만 남기고 싶으면 스냅샷을 찍고 디스크를 삭제하는 게 저렴하다.

### 외부 고정 IP 요금

외부 IP를 예약(static IP)해놓고 인스턴스에 연결하지 않으면 시간당 $0.01이 부과된다. 한 달이면 약 $7.2다. 인스턴스를 삭제할 때 고정 IP도 함께 해제해야 한다. 콘솔에서 인스턴스를 삭제해도 고정 IP는 남아있다.

```bash
# 사용하지 않는 고정 IP 확인
gcloud compute addresses list --filter="status=RESERVED"

# 삭제
gcloud compute addresses delete unused-ip --region=asia-northeast3
```

### 지속 사용 할인과 약정 할인

**지속 사용 할인 (Sustained Use Discount)**: 한 달 중 25% 이상 사용하면 자동 적용된다. 별도 설정 없이 알아서 할인된다. N1, N2 시리즈에 적용되고, E2 시리즈는 적용되지 않는다. 개발 서버처럼 업무 시간에만 켜는 인스턴스는 혜택이 적다.

**약정 사용 할인 (Committed Use Discount)**: 1년 또는 3년 약정을 걸면 최대 57% 할인된다. 약정은 특정 인스턴스가 아니라 리전 단위로 vCPU/메모리 수량에 대해 건다. 프로덕션 환경처럼 항시 운영하는 인스턴스가 있다면 1년 약정은 거의 필수다.

### 네트워크 이그레스 비용

GCP에서 외부로 나가는 트래픽에 비용이 붙는다. 같은 리전 내 통신은 무료지만, 리전 간 통신이나 인터넷으로 나가는 트래픽은 GB당 $0.08~$0.12다. 로그를 외부 모니터링 서비스로 전송하거나, 큰 파일을 사용자에게 직접 서빙하면 비용이 빠르게 늘어난다. CDN(Cloud CDN)을 앞에 두면 이그레스 비용이 줄어든다.

---

## 디스크 선택

### 디스크 타입별 특성

| 타입 | IOPS (읽기) | 처리량 | 가격 (GB/월) |
|------|------------|--------|-------------|
| pd-standard (HDD) | 낮음 | 낮음 | $0.04 |
| pd-balanced (SSD) | 중간 | 중간 | $0.10 |
| pd-ssd | 높음 | 높음 | $0.17 |
| pd-extreme | 매우 높음 | 매우 높음 | $0.125 + IOPS 비용 |

**pd-balanced**가 대부분의 워크로드에 적합하다. pd-standard는 로그 저장이나 백업 용도로만 쓴다. 데이터베이스를 GCE 위에 직접 올릴 거면 pd-ssd를 쓴다.

### 디스크 크기와 성능의 관계

GCE 디스크는 크기에 비례해서 IOPS와 처리량이 올라간다. pd-balanced 10GB 디스크와 500GB 디스크의 IOPS 차이가 크다. 디스크가 작으면 성능이 낮다. "용량은 충분한데 느리다"는 상황이 생기면 디스크 크기를 늘려보는 게 해결책이 되기도 한다.

```bash
# 디스크 크기 확장 (인스턴스 중지 없이 가능)
gcloud compute disks resize my-disk --size=200GB --zone=asia-northeast3-a

# OS 안에서 파티션 확장 (리눅스)
sudo growpart /dev/sda 1
sudo resize2fs /dev/sda1
```

디스크 확장은 가능하지만 축소는 안 된다. 처음부터 필요 이상으로 크게 잡으면 비용이 낭비된다.

---

## 실무에서 자주 하는 실수

### SSH 접속이 안 되는 경우

1. **방화벽 규칙 누락**: IAP(Identity-Aware Proxy)를 통한 SSH가 기본인데, IAP 관련 방화벽 규칙(`35.235.240.0/20`에서 오는 TCP 22)이 없으면 접속이 안 된다
2. **OS Login 설정 충돌**: 프로젝트에 OS Login이 활성화되어 있으면 메타데이터 기반 SSH 키가 무시된다. OS Login을 쓸 건지 메타데이터 SSH 키를 쓸 건지 통일해야 한다
3. **VPC 네트워크 설정**: default VPC를 삭제하고 커스텀 VPC를 만들었는데 라우팅이나 방화벽을 제대로 안 잡은 경우

### 인스턴스 그룹 설정 실수

관리형 인스턴스 그룹(MIG)에서 인스턴스 템플릿을 수정하면 기존 인스턴스에는 반영되지 않는다. 새로 생성되는 인스턴스에만 적용된다. 기존 인스턴스에 적용하려면 rolling update를 실행해야 한다.

```bash
gcloud compute instance-groups managed rolling-action start-update my-mig \
  --version=template=my-new-template \
  --zone=asia-northeast3-a \
  --max-surge=1 \
  --max-unavailable=0
```

### 메타데이터 startup-script 디버깅

startup-script가 실패해도 인스턴스는 정상적으로 Running 상태가 된다. 스크립트가 제대로 실행됐는지 확인하려면 시리얼 포트 로그를 봐야 한다.

```bash
gcloud compute instances get-serial-port-output my-instance \
  --zone=asia-northeast3-a
```

startup-script에서 `apt install`을 하는 경우, 패키지 미러가 응답하지 않으면 타임아웃 때문에 10분 넘게 걸릴 수 있다. 이미지를 미리 구워놓는(custom image) 방식이 안정적이다.
