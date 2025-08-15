---
title: 스왑 메모리 (Swap Memory) 완벽 가이드
tags: [os, memory, swap-memory, virtual-memory, paging]
updated: 2024-12-19
---

# 스왑 메모리 (Swap Memory) 완벽 가이드

## 배경

### 스왑 메모리란?
스왑 메모리는 운영체제에서 사용되는 가상 메모리의 일부분으로, 주 메모리(RAM)가 가득 차거나 메모리 요구량이 증가할 때 운영체제가 일부 데이터를 주 메모리에서 디스크의 스왑 공간으로 이동시키는 메모리 영역입니다.

### 스왑 메모리의 필요성
- **메모리 부족 대응**: 물리적 메모리 부족 상황에서 추가 메모리 공간 제공
- **프로세스 우선순위 관리**: 중요한 프로세스에 더 많은 메모리 할당
- **시스템 안정성**: 메모리 부족으로 인한 시스템 크래시 방지
- **유연한 메모리 관리**: 동적인 메모리 요구량에 대응

### 기본 개념
- **스왑 인(Swap In)**: 디스크에서 메모리로 데이터를 가져오는 과정
- **스왑 아웃(Swap Out)**: 메모리에서 디스크로 데이터를 내보내는 과정
- **스왑 공간(Swap Space)**: 디스크에 할당된 스왑 메모리 영역
- **스왑 파일(Swap File)**: 스왑 공간을 위한 디스크 파일

## 핵심

### 1. 스왑 메모리 동작 원리

#### 스왑 과정
```
1. 메모리 부족 감지: OS가 메모리 부족 상황 감지
2. 페이지 선택: 스왑 아웃할 페이지 선택 (LRU, FIFO 등)
3. 스왑 아웃: 선택된 페이지를 디스크로 이동
4. 메모리 해제: 스왑 아웃된 페이지의 메모리 공간 해제
5. 스왑 인: 필요시 디스크에서 메모리로 페이지 복원
```

#### 스왑 알고리즘
- **LRU (Least Recently Used)**: 가장 오랫동안 사용되지 않은 페이지 스왑 아웃
- **FIFO (First In First Out)**: 가장 먼저 들어온 페이지 스왑 아웃
- **Clock Algorithm**: 참조 비트를 이용한 근사 LRU 알고리즘

### 2. 스왑 메모리의 장단점

#### 장점
1. **메모리 부족 대응**
   - 주 메모리의 부족한 용량을 보완
   - 운영체제가 스왑 메모리를 사용하여 추가 데이터 저장

2. **프로세스 우선순위 설정**
   - 메모리 부족 상황에서 중요한 프로세스의 데이터를 스왑 아웃
   - 필요시 다시 스왑 인하여 중요한 프로세스에 더 많은 메모리 할당

3. **유연성**
   - 물리적인 메모리 용량을 초과하는 작업 수행 가능
   - 대규모 서버 환경에서 메모리 요구량 예측이 어려운 상황에서 유용

#### 단점
1. **성능 저하**
   - 스왑 메모리는 디스크에 접근해야 하므로 주 메모리보다 느림
   - 스왑 인/아웃 작업이 빈번하게 발생하면 성능 저하

2. **디스크 사용량 증가**
   - 스왑 메모리를 사용하면 디스크 공간이 추가로 필요
   - 대규모 데이터를 스왑 영역에 저장하면 디스크 공간 차지

3. **I/O 부하**
   - 스왑 메모리는 디스크와 주 메모리 간의 데이터 전송 필요
   - 디스크 I/O 처리량 증가로 시스템 전반적인 성능 영향

4. **메모리 관리 복잡성**
   - 스왑 메모리 사용으로 메모리 관리가 더 복잡해짐
   - 적절한 스왑 메모리 크기 설정과 관리 필요

### 3. 가상 메모리와 스왑 메모리의 차이

#### 가상 메모리
- 운영체제가 사용자 프로세스에게 제공하는 추상화된 메모리 공간
- 주 메모리(RAM)와 디스크의 조합으로 구성
- 주 메모리보다 큰 용량을 가지며, 각 프로세스는 가상 주소 공간 할당
- 프로세스 간 메모리 공간 격리 제공

#### 스왑 메모리
- 주 메모리의 일부를 디스크에 사용하는 메모리 영역
- 메모리 부족 상황에서 주 메모리에 적재된 데이터를 디스크로 이동
- 운영체제가 관리하며, 스왑 인/아웃 작업으로 데이터 이동 수행

## 예시

### 1. 실제 사용 사례

#### Linux 스왑 메모리 확인
```bash
# 스왑 메모리 정보 확인
free -h

# 스왑 파티션 확인
swapon --show

# 스왑 사용량 상세 정보
cat /proc/swaps

# 스왑 통계 확인
cat /proc/vmstat | grep -i swap
```

#### 스왑 메모리 생성 및 활성화
```bash
# 스왑 파일 생성 (2GB)
sudo fallocate -l 2G /swapfile

# 스왑 파일 권한 설정
sudo chmod 600 /swapfile

# 스왑 파일 포맷
sudo mkswap /swapfile

# 스왑 활성화
sudo swapon /swapfile

# 부팅 시 자동 마운트 설정
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

#### 스왑 메모리 모니터링 스크립트
```bash
#!/bin/bash
# swap_monitor.sh

while true; do
    echo "=== $(date) ==="
    echo "스왑 메모리 사용량:"
    free -h | grep -E "(Mem|Swap)"
    echo ""
    echo "스왑 사용률:"
    free | awk '/Swap/ {printf "%.2f%%\n", $3/$2*100}'
    echo ""
    echo "스왑 인/아웃 통계:"
    cat /proc/vmstat | grep -E "(pswpin|pswpout)"
    echo "================================"
    sleep 10
done
```

### 2. 운영체제별 스왑 메모리 관리

#### Windows 페이지 파일
```powershell
# 페이지 파일 정보 확인
Get-WmiObject -Class Win32_PageFileUsage | Select-Object Name, AllocatedBaseSize, CurrentUsage

# 페이지 파일 설정 확인
Get-WmiObject -Class Win32_PageFileSetting | Select-Object Name, InitialSize, MaximumSize

# 시스템 메모리 정보
Get-WmiObject -Class Win32_ComputerSystem | Select-Object TotalPhysicalMemory
```

#### macOS 스왑 메모리
```bash
# 스왑 파일 확인
sysctl vm.swapusage

# 메모리 압박 상태 확인
vm_stat

# 스왑 파일 위치 확인
ls -la /private/var/vm/
```

## 운영 팁

### 1. 스왑 메모리 최적화

#### 스왑 메모리 크기 설정
```bash
# 스왑 메모리 크기 계산 (RAM의 2배 또는 최소 4GB)
RAM_SIZE=$(free -g | awk '/^Mem:/{print $2}')
SWAP_SIZE=$((RAM_SIZE * 2))

if [ $SWAP_SIZE -lt 4 ]; then
    SWAP_SIZE=4
fi

echo "권장 스왑 크기: ${SWAP_SIZE}GB"
```

#### 스왑 사용률 최적화
```bash
# 스왑 사용률이 80% 이상일 때 경고
SWAP_USAGE=$(free | awk '/Swap/ {printf "%.0f", $3/$2*100}')

if [ $SWAP_USAGE -gt 80 ]; then
    echo "경고: 스왑 사용률이 ${SWAP_USAGE}%입니다!"
    echo "메모리 사용량이 많은 프로세스:"
    ps aux --sort=-%mem | head -5
fi
```

### 2. 성능 최적화

#### 스왑 성능 향상
```bash
# 스왑 사용률 조정 (0-100, 낮을수록 스왑 사용 적음)
echo 10 > /proc/sys/vm/swappiness

# 스왑 파일을 SSD에 위치 (더 빠른 접근)
# /etc/fstab에서 스왑 파일 경로를 SSD로 변경
```

#### 메모리 압박 해결
```bash
# 메모리 캐시 정리
echo 3 > /proc/sys/vm/drop_caches

# 불필요한 프로세스 종료
pkill -f "unnecessary_process"

# 스왑 사용량이 많은 프로세스 확인
for file in /proc/*/status ; do
    awk '/VmSwap|Name/{printf $2 " " $3}END{ print ""}' $file 2>/dev/null
done | sort -k 2 -n -r | head -10
```

### 3. 문제 해결

#### 스왑 메모리 부족 문제
```bash
# 스왑 메모리 부족 시 해결 방법
# 1. 스왑 파일 크기 증가
sudo swapoff /swapfile
sudo fallocate -l 4G /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 2. 추가 스왑 파일 생성
sudo fallocate -l 2G /swapfile2
sudo chmod 600 /swapfile2
sudo mkswap /swapfile2
sudo swapon /swapfile2
```

## 참고

### 스왑 메모리 관련 용어

| 용어 | 설명 |
|------|------|
| **스왑 인(Swap In)** | 디스크에서 메모리로 데이터를 가져오는 과정 |
| **스왑 아웃(Swap Out)** | 메모리에서 디스크로 데이터를 내보내는 과정 |
| **스왑 공간(Swap Space)** | 디스크에 할당된 스왑 메모리 영역 |
| **스왑 파일(Swap File)** | 스왑 공간을 위한 디스크 파일 |
| **스왑 파티션(Swap Partition)** | 디스크의 전용 파티션으로 할당된 스왑 공간 |
| **스왑 사용률(Swap Usage)** | 전체 스왑 공간 중 사용 중인 비율 |

### 스왑 메모리 권장 설정

| 시스템 유형 | 권장 스왑 크기 | 이유 |
|-------------|---------------|------|
| **개발 환경** | RAM의 2배 | 대용량 빌드 및 테스트 |
| **웹 서버** | RAM의 1-2배 | 트래픽 변동에 대응 |
| **데이터베이스** | RAM의 0.5-1배 | 안정성 우선 |
| **데스크톱** | RAM의 1-2배 | 멀티태스킹 지원 |

### 스왑 메모리 vs 가상 메모리

| 특징 | 스왑 메모리 | 가상 메모리 |
|------|-------------|-------------|
| **범위** | 가상 메모리의 일부 | 전체 메모리 추상화 |
| **목적** | 메모리 부족 대응 | 메모리 관리 및 보호 |
| **구성** | 디스크 기반 | RAM + 디스크 조합 |
| **관리** | OS가 자동 관리 | OS가 전체 관리 |

### 결론
스왑 메모리는 시스템의 메모리 부족 상황을 해결하는 중요한 기술이지만, 과도한 사용은 성능 저하를 야기할 수 있습니다. 적절한 스왑 메모리 크기 설정과 모니터링을 통해 시스템의 안정성과 성능을 균형있게 유지하는 것이 중요합니다.

