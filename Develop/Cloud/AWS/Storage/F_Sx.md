---
title: AWS FSx (관리형 파일 시스템)
tags: [aws, fsx, storage, lustre, ontap, openzfs, windows-file-server, hpc]
updated: 2026-06-21
---

# AWS FSx (관리형 파일 시스템)

## 개요

FSx는 특정 파일 시스템 엔진을 AWS가 관리형으로 돌려주는 서비스다. EFS가 리눅스/NFS 한 종류만 다루는 것과 다르게, FSx는 네 종류를 따로 제공한다.

- **FSx for Windows File Server**: SMB 프로토콜, Active Directory 연동. Windows 워크로드용 공유 드라이브.
- **FSx for Lustre**: HPC용 병렬 파일 시스템. 수십~수백 GB/s 처리량. S3와 직접 연동된다.
- **FSx for NetApp ONTAP**: NetApp의 ONTAP을 그대로 돌린다. NFS/SMB/iSCSI 동시 지원, 스냅샷·복제·중복 제거 같은 ONTAP 기능을 쓴다.
- **FSx for OpenZFS**: ZFS 기반 NFS 파일 시스템. 스냅샷·클론, 낮은 지연 시간이 강점이다.

네 종류는 이름만 FSx로 묶여 있을 뿐 내부 엔진, 프로토콜, 가격 모델이 전부 다르다. "FSx를 쓴다"는 말은 의미가 없고, 항상 어느 FSx인지를 정해야 한다.

## EFS와의 차이

EFS와 FSx를 두고 고민하는 경우가 가장 많다. 둘 다 관리형 파일 시스템이지만 쓰는 자리가 다르다.

EFS는 리눅스 전용 NFS다. 프로토콜이 NFS 하나고, 리전 내 모든 AZ에서 같은 마운트 타깃으로 접근한다. 용량을 미리 잡지 않고 쓴 만큼 늘어난다. 운영 부담이 거의 없는 대신, Windows를 못 붙이고 처리량을 끌어올리는 데 한계가 있다.

FSx는 목적별로 엔진을 고른다.

| 상황 | 선택 |
|------|------|
| 리눅스 컨테이너/EC2 공유 스토리지, 운영 단순함 우선 | EFS |
| Windows EC2에서 SMB 공유 드라이브, AD 인증 필요 | FSx for Windows |
| HPC, 머신러닝 학습, 대용량 분석에서 높은 처리량 필요 | FSx for Lustre |
| 온프레미스 NetApp을 클라우드로 옮기거나 멀티 프로토콜 필요 | FSx for NetApp ONTAP |
| ZFS 스냅샷/클론, 낮은 지연 시간의 NFS | FSx for OpenZFS |

실무에서 갈리는 지점은 단순하다. Windows면 EFS가 아예 후보가 아니다. 처리량이 EFS 한계를 넘으면 Lustre로 간다. 그 외 리눅스 일반 공유는 EFS가 운영이 제일 편하다.

EFS도 Elastic 처리량 모드를 쓰면 꽤 높은 처리량이 나오지만, GB/s 단위의 지속 처리량과 수십만 IOPS가 필요한 작업에서는 Lustre를 따라오지 못한다.

## Lustre를 HPC/대용량 분석에 쓰는 경우

Lustre는 원래 슈퍼컴퓨터용 병렬 파일 시스템이다. 파일을 여러 스토리지 서버에 쪼개 분산 저장하고, 클라이언트가 동시에 여러 서버에서 읽는다. 그래서 단일 파일 시스템이 수백 GB/s까지 처리량이 나온다.

쓰는 자리는 정해져 있다.

- 머신러닝 학습에서 수 TB짜리 데이터셋을 수십 개 GPU 인스턴스가 동시에 읽을 때. EFS로 붙이면 데이터 로딩이 병목이 된다.
- 유전체 분석, 시뮬레이션, 렌더링처럼 대용량 파일을 빠르게 스캔하는 작업.
- S3에 쌓인 원본 데이터를 분석 잡 동안만 빠른 파일 시스템으로 끌어와 처리하고 다시 S3에 쓰는 경우.

마지막 패턴이 Lustre의 핵심이다. Lustre는 S3 버킷을 데이터 리포지토리로 연결한다. 파일 시스템을 만들 때 S3 경로를 지정하면, S3 객체가 Lustre에 메타데이터로 먼저 보이고 실제 데이터는 처음 읽을 때 지연 로딩(lazy load)된다. 작업이 끝나면 변경분을 S3로 다시 내보낸다.

```bash
# S3 연동 Lustre 파일 시스템 생성
aws fsx create-file-system \
  --file-system-type LUSTRE \
  --storage-capacity 1200 \
  --subnet-ids subnet-0abc123 \
  --lustre-configuration '{
    "DeploymentType": "PERSISTENT_2",
    "PerUnitStorageThroughput": 250,
    "DataRepositoryConfiguration": {
      "Bucket": "s3://my-training-data",
      "AutoImportPolicy": "NEW_CHANGED"
    }
  }'
```

배포 타입을 잘못 고르면 돈만 나가고 성능이 안 나온다.

- **SCRATCH_2**: 임시 작업용. 데이터 복제가 없어서 디스크 장애 시 데이터가 날아간다. 학습 한 번 돌리고 버리는 데이터에만 쓴다. 가격이 싸다.
- **PERSISTENT_1 / PERSISTENT_2**: 복제가 있어 내구성이 있다. 오래 유지하는 파일 시스템이면 이쪽. PERSISTENT_2가 처리량 대비 가격이 더 낫다.

처리량은 `PerUnitStorageThroughput` 값으로 정한다. PERSISTENT_2는 스토리지 1TiB당 125/250/500/1000 MB/s 중에 고른다. 스토리지 용량과 처리량이 묶여 있어서, 처리량을 올리려면 용량도 같이 커진다. 이 구조 때문에 "데이터는 적은데 처리량만 높이고 싶다"가 잘 안 된다.

## 처리량 용량 산정 실패와 I/O 병목

Windows File Server와 ONTAP, OpenZFS는 처리량 용량(throughput capacity, MB/s)을 만들 때 직접 고른다. 이 값을 작게 잡으면 평소엔 멀쩡하다가 부하가 몰릴 때 I/O가 막힌다. 가장 흔하게 당하는 패턴이다.

처리량 용량은 단순히 최대 대역폭만 정하는 게 아니다. 파일 서버 인스턴스의 메모리(캐시)와 네트워크, 디스크 IOPS가 이 값에 같이 묶여 올라간다. 예를 들어 Windows File Server에서 32 MB/s로 만들면 캐시가 작아서 메타데이터가 많은 워크로드(작은 파일 수십만 개)에서 디스크까지 매번 내려가 느려진다. 처리량 숫자만 보고 "우리 트래픽은 30MB/s면 충분"이라고 잡았다가 실사용에서 막히는 경우가 여기다.

증상은 비슷하다. 클라이언트에서 `iostat`이나 애플리케이션 응답 시간이 갑자기 튀고, CloudWatch에서 보면 처리량 사용률이 100%에 붙어 있다. 이때 봐야 할 지표가 정해져 있다.

- **Windows/ONTAP/OpenZFS**: CloudWatch `ThroughputUtilization`(또는 네트워크 처리량 관련 지표)이 한계에 붙는지. 디스크 IOPS 지표가 프로비저닝 한계에 붙는지.
- **Lustre**: 클라이언트별 처리량 합이 `PerUnitStorageThroughput × 스토리지(TiB)`를 넘기는지.

Windows와 ONTAP은 처리량 용량을 나중에 올릴 수 있다. 단, 변경 중 몇 분간 페일오버가 일어나면서 순간적으로 연결이 끊겼다 붙는다. 멀티 AZ면 그래도 견디지만 싱글 AZ에서 운영 중에 바꾸면 그 시간 동안 마운트가 끊긴다. 그래서 처리량 용량 변경은 트래픽 적은 시간에 잡는다.

Lustre는 앞서 말한 대로 스토리지 용량과 처리량이 묶여 있어서, 처리량을 올리려면 용량을 키우거나 새 파일 시스템을 만들어 데이터를 옮겨야 한다. 학습 잡을 돌려보고 데이터 로딩이 GPU를 못 따라가면 `PerUnitStorageThroughput`을 한 단계 올린 파일 시스템으로 다시 만드는 게 보통이다. 처음부터 여유 있게 잡는 편이 낫다.

## ECS/EC2 마운트 설정

### Lustre를 EC2에 마운트

Lustre는 전용 클라이언트가 필요하다. Amazon Linux 2는 패키지로 설치한다.

```bash
# Lustre 클라이언트 설치 (Amazon Linux 2)
sudo amazon-linux-extras install -y lustre

# 마운트
sudo mkdir -p /fsx
sudo mount -t lustre -o relatime,flock \
  fs-0abc123.fsx.ap-northeast-2.amazonaws.com@tcp:/mountname /fsx
```

마운트 이름(`/mountname`)은 파일 시스템마다 생성되는 값이다. 콘솔이나 `describe-file-systems`의 `MountName`에서 확인한다. 이 값을 빼먹고 `/`만 적으면 마운트가 안 된다.

커널 버전과 Lustre 클라이언트 버전이 안 맞으면 마운트가 실패하기도 한다. 커널을 올린 뒤에는 클라이언트를 다시 설치하거나 `dkms`로 재빌드해야 한다. AMI 갱신할 때 자주 걸린다.

### Windows File Server를 EC2에 마운트

Windows EC2에서는 SMB로 네트워크 드라이브에 연결한다. AD에 조인된 인스턴스여야 인증이 통과한다.

```powershell
# DNS 이름으로 네트워크 드라이브 매핑
net use Z: \\amznfsxabcd1234.example.com\share
```

### Lustre를 ECS 태스크에 마운트

ECS에서는 EFS처럼 매끄럽게 붙지 않는다. EFS는 태스크 정의에 `efsVolumeConfiguration`이 있어서 바로 마운트되지만, Lustre는 그런 네이티브 볼륨 타입이 없다.

EC2 시작 타입이면 호스트에 Lustre를 마운트해 두고, 그 디렉토리를 바인드 마운트로 컨테이너에 넣는다.

```json
{
  "volumes": [
    {
      "name": "fsx-lustre",
      "host": { "sourcePath": "/fsx" }
    }
  ],
  "containerDefinitions": [
    {
      "name": "app",
      "mountPoints": [
        { "sourceVolume": "fsx-lustre", "containerPath": "/data" }
      ]
    }
  ]
}
```

호스트 마운트는 EC2 부팅 시 user data 스크립트에서 처리한다. 위 EC2 마운트 명령을 그대로 user data에 넣으면 된다.

Fargate에서는 Lustre를 못 붙인다. Fargate는 호스트 접근이 없어서 바인드 마운트가 불가능하고, FSx for Lustre용 네이티브 볼륨 드라이버도 없다. Fargate에서 공유 파일 시스템이 필요하면 EFS를 써야 한다. 이걸 모르고 Fargate + Lustre 아키텍처를 그렸다가 갈아엎는 경우가 있다.

ONTAP과 OpenZFS는 NFS로 노출되므로 EC2에서는 일반 NFS 마운트로 붙는다.

```bash
sudo mount -t nfs svm-0abc.fs-0xyz.fsx.ap-northeast-2.amazonaws.com:/vol1 /mnt/ontap
```

## 보안 그룹 포트 누락으로 마운트가 안 될 때

마운트가 안 되는 신고의 절반은 보안 그룹이다. 명령은 맞는데 `mount`가 타임아웃으로 멈춰 있거나, `net use`가 "네트워크 경로를 찾을 수 없습니다"로 떨어진다. DNS는 풀리는데 포트가 막혀 있는 상태다.

FSx는 파일 시스템(또는 ENI)에 붙은 보안 그룹과 클라이언트(EC2)의 보안 그룹 양쪽을 본다. 클라이언트에서 FSx로 나가는 길과 FSx에서 클라이언트로 들어오는 길이 둘 다 열려 있어야 한다. 종류별로 열어야 할 포트가 다르다.

| 종류 | 프로토콜 | 포트 |
|------|----------|------|
| Windows File Server | SMB | TCP 445 |
| Lustre | Lustre | TCP 988 (PERSISTENT_2는 1018–1023 범위도) |
| ONTAP / OpenZFS | NFS | TCP/UDP 2049, 111, 마운트 데몬 포트 등 |

Windows는 TCP 445만 막혀도 마운트가 안 된다. 사내망에서 ISP가 445를 차단하는 경우가 있어서, 온프레미스에서 Direct Connect로 붙일 때 특히 자주 걸린다. AD 인증까지 가려면 도메인 컨트롤러로 가는 포트(Kerberos 88, LDAP 389 등)도 따로 열려 있어야 한다.

Lustre는 클라이언트와 FSx 사이에 TCP 988이 핵심이다. PERSISTENT_2 배포 타입은 988 외에 1018–1023 범위 포트를 추가로 쓰므로 이 범위를 빼먹으면 마운트는 되는데 데이터 전송이 안 되는 이상한 상태가 된다.

진단은 단순하다. FSx ENI의 IP로 해당 포트가 열리는지 확인한다.

```bash
# Lustre 포트 확인
nc -zv fs-0abc123.fsx.ap-northeast-2.amazonaws.com 988

# Windows 쪽에서 SMB 포트 확인 (PowerShell)
Test-NetConnection -ComputerName amznfsxabcd1234.example.com -Port 445
```

`nc`가 막히면 mount를 아무리 다시 쳐도 소용없다. 보안 그룹부터 고쳐야 한다. 같은 보안 그룹 안에서 FSx와 EC2가 통신해야 하면 인바운드 규칙의 소스를 보안 그룹 ID 자기 자신으로 지정하는 식으로 푼다.

서브넷 NACL을 따로 건드린 환경이면 NACL도 본다. NACL은 상태를 기억하지 않아서, 응답 트래픽을 위한 임시 포트(ephemeral port, 1024–65535) 아웃바운드를 막아두면 핸드셰이크가 반만 되고 멈춘다.

## 백업과 스냅샷 운영

FSx는 종류마다 백업·스냅샷 모델이 다르다.

Windows File Server와 Lustre(PERSISTENT만), ONTAP, OpenZFS는 FSx 백업을 지원한다. 자동 일일 백업과 수동 백업이 있고, 백업은 별도 스토리지로 잡혀 따로 과금된다. 자동 백업 보존 기간은 기본값을 그대로 두면 며칠 단위로 쌓이므로, 보존 기간을 정해두지 않으면 백업 스토리지 비용이 조용히 늘어난다.

```bash
# 수동 백업 생성
aws fsx create-backup --file-system-id fs-0abc123 \
  --tags Key=reason,Value=before-migration

# 백업에서 새 파일 시스템 복원 (기존 파일 시스템을 덮어쓰지 않는다)
aws fsx create-file-system-from-backup \
  --backup-id backup-0xyz789 \
  --subnet-ids subnet-0abc123
```

복원은 항상 새 파일 시스템을 만드는 방식이다. 기존 것을 그 자리에서 되돌리지 못한다. 그래서 복원 후에는 클라이언트 마운트 대상(DNS 이름)이 바뀐다. 운영 중인 마운트를 복원본으로 갈아끼우려면 마운트를 다시 잡아야 한다는 걸 염두에 둬야 한다.

ONTAP과 OpenZFS는 ZFS/ONTAP 자체 스냅샷이 따로 있다. 이건 FSx 백업과 다른 물건이다. 스냅샷은 파일 시스템 안에서 순간 복사를 만들고, 사용자가 `.snapshot`(ONTAP)이나 `.zfs/snapshot`(OpenZFS) 디렉토리에서 직접 옛 버전 파일을 꺼낼 수 있다. 실수로 지운 파일 하나 복구하는 데는 전체 백업 복원보다 스냅샷이 훨씬 빠르다. 단, 스냅샷은 같은 파일 시스템 안에 사니까 파일 시스템 자체가 날아가면 같이 사라진다. 재해 복구용으로는 백업이 따로 있어야 한다.

Lustre SCRATCH는 백업이 없다. 앞에서 말한 대로 내구성 자체가 없으니 복구 수단도 없다. SCRATCH에 둔 데이터는 S3 연동으로 원본을 S3에 두는 게 사실상 유일한 보호책이다.

## 처리량 모드와 비용 구조

FSx는 종류마다 가격 모델이 다르다. 하나로 묶어서 이해하면 틀린다.

### Lustre

비용은 스토리지 + 처리량으로 묶인다. 앞에서 말한 대로 `PerUnitStorageThroughput`이 TiB당 처리량을 정하고, 이게 가격에 직접 반영된다. SCRATCH는 처리량 단가가 없는 대신 내구성이 없다. PERSISTENT는 처리량 단가가 붙는다.

S3 연동에서 데이터를 지연 로딩하면, 처음 읽을 때만 S3에서 가져오므로 자주 안 쓰는 데이터는 Lustre 스토리지 비용을 아낀다. 대신 콜드 데이터를 처음 읽을 때 지연이 생긴다.

### Windows / OpenZFS

처리량 용량(MB/s)을 직접 고른다. SSD/HDD 스토리지 타입에 따라 단가가 갈리고, 처리량 용량이 클수록 비싸다. Windows는 멀티 AZ로 만들면 단일 AZ보다 비용이 약 2배다. 스탠바이를 다른 AZ에 두기 때문이다. 가용성이 필요 없는 개발 환경까지 멀티 AZ로 만들면 돈이 샌다.

### ONTAP

스토리지를 SSD 프로비저닝 용량 + 용량 풀(자동 계층화된 콜드 데이터)로 나눠 과금한다. 자주 안 읽는 데이터를 자동으로 저렴한 용량 풀로 내려서 SSD 비용을 줄이는 게 ONTAP의 장점이다. 처리량 용량도 따로 고른다.

### 공통 주의사항

- 용량을 줄이는 건 대부분 안 된다. 늘리는 건 되지만 한 번 키운 스토리지는 못 줄인다. 처음에 크게 잡으면 계속 그 비용이 나간다.
- 백업과 스냅샷은 별도 과금이다. 자동 백업 보존 기간을 길게 잡아두고 잊으면 백업 스토리지 비용이 쌓인다.
- Lustre SCRATCH는 싸다고 운영 데이터에 쓰면 안 된다. 장애 한 번에 전부 날아가고 복구 수단이 없다.

## 정리

FSx는 단일 서비스가 아니라 엔진 네 개를 묶은 이름이다. Windows 공유는 Windows File Server, HPC·대용량 분석은 Lustre, 멀티 프로토콜·온프레미스 마이그레이션은 ONTAP, ZFS 기능이 필요하면 OpenZFS로 간다. 리눅스 일반 공유라면 굳이 FSx를 쓸 이유가 없고 EFS가 운영이 편하다. Lustre는 처리량과 스토리지 용량이 묶여 있고 Fargate에 못 붙는다는 제약을 먼저 확인하고 아키텍처를 잡아야 한다.