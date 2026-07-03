---
title: SA와 PSACCT 모니터링 도구
tags: [linux, system-monitoring, sa, psacct, sysstat, process-accounting]
updated: 2025-10-15
---

# SA와 PSACCT 모니터링 도구

## 개요

SA(System Activity)와 PSACCT(Process Accounting)는 Linux 시스템에서 성능 모니터링과 사용자 활동 추적을 위한 핵심 도구입니다. 이 두 도구는 서로 다른 관점에서 시스템을 모니터링하여 포괄적인 시스템 관리 정보를 제공합니다.

### 도구별 특징

#### SA (System Activity)
- **목적**: 시스템 전체의 성능 지표 수집 및 분석
- **데이터 범위**: CPU, 메모리, 디스크, 네트워크 등 시스템 리소스
- **수집 방식**: 주기적 자동 수집 (cron 기반)
- **저장 위치**: `/var/log/sa/` 디렉토리
- **주요 도구**: sar, iostat, mpstat

#### PSACCT (Process Accounting)
- **목적**: 개별 프로세스와 사용자 활동 상세 기록
- **데이터 범위**: 명령어 실행, 사용자별 리소스 사용량
- **수집 방식**: 실시간 프로세스 추적
- **저장 위치**: `/var/log/pacct` 파일
- **주요 도구**: accton, lastcomm, sa, dump-acct

### 모니터링 도구의 필요성

#### 1. 성능 분석 및 최적화
- 시스템 병목 현상 식별
- 리소스 사용 패턴 분석
- 성능 튜닝을 위한 데이터 제공
- 용량 계획 수립 지원

#### 2. 보안 감사 및 컴플라이언스
- 사용자 활동 추적
- 보안 사고 조사
- 규정 준수 모니터링
- 의심스러운 활동 탐지

#### 3. 운영 관리
- 시스템 상태 모니터링
- 문제 진단 및 해결
- 성능 기반 알림 설정
- 장애 예방 및 대응

### 기본 개념 정리

| 개념 | 설명 | 관련 도구 |
|------|------|-----------|
| **sar** | 시스템 활동 보고서 생성 도구 | sar, sadc, sa1, sa2 |
| **accton** | 프로세스 계정 활성화/비활성화 도구 | accton |
| **lastcomm** | 실행된 명령어 기록 조회 도구 | lastcomm |
| **sa** | 사용자별 리소스 사용 통계 도구 | sa |
| **dump-acct** | 프로세스 기록 덤프 도구 | dump-acct |

## 상세 가이드

### 1. SA (System Activity) 도구

SA는 sysstat 패키지에 포함된 도구들로, 시스템의 성능 데이터를 수집하고 분석하는 데 사용됩니다.

#### 설치 및 초기 설정

##### 패키지 설치
```bash
# Ubuntu/Debian 계열
sudo apt update
sudo apt install sysstat

# CentOS/RHEL 계열
sudo yum install sysstat
# 또는 (RHEL 8+)
sudo dnf install sysstat

# Fedora
sudo dnf install sysstat
```

##### 서비스 활성화
```bash
# sysstat 서비스 활성화 및 시작
sudo systemctl enable sysstat
sudo systemctl start sysstat

# 서비스 상태 확인
sudo systemctl status sysstat
```

##### 설정 파일 구성
```bash
# sysstat 설정 파일 편집
sudo vi /etc/default/sysstat

# 주요 설정 옵션
ENABLED="true"                    # 데이터 수집 활성화
HISTORY=28                        # 데이터 보관 기간 (일)
COMPRESSAFTER=31                  # 압축 시작 시점
SA1_OPTIONS="-S DISK"            # sa1 옵션
SA2_OPTIONS="-A"                 # sa2 옵션
```

##### cron 작업 확인
```bash
# sysstat cron 작업 확인
sudo cat /etc/cron.d/sysstat

# 기본 설정 (10분마다 데이터 수집)
#-*/10 * * * * root /usr/lib/sysstat/debian-sa1 1 1
#-*/10 * * * * root /usr/lib/sysstat/debian-sa2 -A
```

#### 주요 명령어 및 사용법

##### sar - 시스템 활동 보고서

sar(System Activity Reporter)는 시스템의 다양한 성능 지표를 수집하고 보고하는 핵심 도구입니다.

###### 기본 사용법
```bash
# 기본 문법: sar [옵션] [간격] [횟수]
sar -u 1 5    # 1초 간격으로 5번 CPU 사용률 조회
sar -r 1 5    # 1초 간격으로 5번 메모리 사용률 조회
```

###### CPU 관련 옵션
```bash
# CPU 사용률 (-u)
sar -u 1 5                    # 전체 CPU 사용률
sar -u 1 5 | grep -v "Average" # 평균값 제외하고 실시간 데이터만

# CPU 사용률 상세 정보
sar -u 1 5 | awk 'NR>3 {print "User: " $3 "%, System: " $5 "%, I/O Wait: " $6 "%"}'

# CPU 코어별 사용률 (-P)
sar -P ALL 1 5                # 모든 CPU 코어
sar -P 0 1 5                  # CPU 0번 코어만
```

###### 메모리 관련 옵션
```bash
# 메모리 사용률 (-r)
sar -r 1 5                    # 메모리 사용률
sar -r -S 1 5                 # 스왑 사용률 포함

# 메모리 사용률 해석
# kbmemfree: 사용 가능한 메모리 (KB)
# kbmemused: 사용 중인 메모리 (KB)
# %memused: 메모리 사용률 (%)
# kbbuffers: 버퍼로 사용 중인 메모리 (KB)
# kbcached: 캐시로 사용 중인 메모리 (KB)
```

###### 디스크 I/O 관련 옵션
```bash
# 디스크 I/O 통계 (-d)
sar -d 1 5                    # 모든 디스크
sar -d -p 1 5                 # 사람이 읽기 쉬운 형태
sar -d sda 1 5                # 특정 디스크만

# 디스크 I/O 상세 정보 (-x)
sar -x sda 1 5                # 특정 디스크 상세 정보
```

###### 네트워크 관련 옵션
```bash
# 네트워크 인터페이스 통계 (-n DEV)
sar -n DEV 1 5                # 모든 네트워크 인터페이스
sar -n DEV 1 5 | grep eth0    # 특정 인터페이스만

# 네트워크 오류 통계 (-n EDEV)
sar -n EDEV 1 5               # 네트워크 오류 통계

# TCP 통계 (-n TCP)
sar -n TCP 1 5                # TCP 연결 통계

# UDP 통계 (-n UDP)
sar -n UDP 1 5                # UDP 통계
```

###### 시스템 부하 관련 옵션
```bash
# 시스템 부하 평균 (-q)
sar -q 1 5                    # 로드 평균

# 프로세스 생성 및 컨텍스트 스위칭 (-w)
sar -w 1 5                    # 프로세스 생성/컨텍스트 스위칭

# 시스템 호출 통계 (-c)
sar -c 1 5                    # 시스템 호출 통계
```

###### 과거 데이터 조회
```bash
# 특정 시간대 데이터 조회
sar -u -s 10:00:00 -e 11:00:00    # 10시~11시 CPU 사용률

# 특정 날짜 데이터 조회
sar -u -f /var/log/sa/sa01        # 1일 데이터
sar -u -f /var/log/sa/sa$(date +%d)  # 오늘 데이터

# 여러 옵션 조합
sar -u -r -d 1 5                  # CPU, 메모리, 디스크 동시 조회
```

##### iostat - 디스크 I/O 및 CPU 통계

iostat은 CPU 사용률과 디스크 I/O 통계를 제공하는 도구입니다.

###### 기본 사용법
```bash
# 기본 CPU 및 디스크 통계
iostat

# 2초 간격으로 3번 출력
iostat 2 3

# 1초 간격으로 5번 출력
iostat 1 5
```

###### CPU 관련 옵션
```bash
# CPU 사용률만 표시 (-c)
iostat -c 1 5

# CPU 사용률 상세 정보
iostat -c 1 5 | awk 'NR>3 {print "User: " $1 "%, System: " $3 "%, I/O Wait: " $4 "%"}'
```

###### 디스크 관련 옵션
```bash
# 디스크 통계만 표시 (-d)
iostat -d 1 5

# 특정 디스크만 모니터링
iostat -x sda 1 5

# 확장된 디스크 통계 (-x)
iostat -x 1 5

# 사람이 읽기 쉬운 형태 (-h)
iostat -h 1 5

# JSON 형태로 출력 (-j)
iostat -j ID 1 5
```

###### iostat 출력 해석
```bash
# 디스크 I/O 지표 설명
# tps: 초당 전송 요청 수
# kB_read/s: 초당 읽기 데이터량 (KB)
# kB_wrtn/s: 초당 쓰기 데이터량 (KB)
# kB_read: 총 읽기 데이터량 (KB)
# kB_wrtn: 총 쓰기 데이터량 (KB)

# 확장 통계 (-x 옵션)
# rrqm/s: 초당 읽기 요청 병합 수
# wrqm/s: 초당 쓰기 요청 병합 수
# r/s: 초당 읽기 요청 수
# w/s: 초당 쓰기 요청 수
# rkB/s: 초당 읽기 데이터량 (KB)
# wkB/s: 초당 쓰기 데이터량 (KB)
# avgrq-sz: 평균 요청 크기
# avgqu-sz: 평균 큐 길이
# await: 평균 대기 시간 (ms)
# r_await: 평균 읽기 대기 시간 (ms)
# w_await: 평균 쓰기 대기 시간 (ms)
# svctm: 평균 서비스 시간 (ms)
# %util: 디스크 사용률 (%)
```

##### mpstat - CPU 코어별 통계

mpstat은 CPU 코어별 상세 통계를 제공하는 도구입니다.

###### 기본 사용법
```bash
# 모든 CPU 코어 통계
mpstat -P ALL 1 5

# 특정 CPU 코어 통계
mpstat -P 0 1 5

# CPU 사용률 상세 정보
mpstat -u 1 5
```

###### CPU 코어별 옵션
```bash
# 모든 CPU 코어 (-P ALL)
mpstat -P ALL 1 5

# 특정 CPU 코어 (-P 0,1,2)
mpstat -P 0,1,2 1 5

# CPU 사용률만 표시 (-u)
mpstat -u 1 5

# 인터럽트 통계 (-I)
mpstat -I ALL 1 5
```

###### mpstat 출력 해석
```bash
# CPU 사용률 지표 설명
# %usr: 사용자 모드에서의 CPU 사용률
# %nice: nice 값이 설정된 프로세스의 CPU 사용률
# %sys: 시스템 모드에서의 CPU 사용률
# %iowait: I/O 대기 중인 CPU 사용률
# %irq: 하드웨어 인터럽트 처리 중인 CPU 사용률
# %soft: 소프트웨어 인터럽트 처리 중인 CPU 사용률
# %steal: 가상화 환경에서 다른 VM에 할당된 CPU 시간
# %guest: 가상 머신에서 실행되는 프로세스의 CPU 사용률
# %gnice: nice 값이 설정된 가상 머신 프로세스의 CPU 사용률
# %idle: 유휴 상태인 CPU 사용률
```

#### 고급 사용법
```bash
# 특정 시간대 데이터 조회
sar -u -s 10:00:00 -e 11:00:00

# 특정 날짜 데이터 조회
sar -u -f /var/log/sa/sa01

# CPU 사용률 그래프 생성
sar -u 1 60 | awk '{print $1, $3}' > cpu_usage.txt

# 메모리 사용률 모니터링 스크립트
#!/bin/bash
while true; do
    echo "$(date): $(sar -r 1 1 | tail -1 | awk '{print $3}')" >> memory_usage.log
    sleep 60
done
```

### 2. PSACCT (Process Accounting) 도구

PSACCT는 개별 프로세스와 사용자의 활동을 상세히 기록하는 도구입니다. 시스템 관리자가 사용자 활동을 추적하고 보안 감사를 수행하는 데 필수적입니다.

#### 설치 및 초기 설정

##### 패키지 설치
```bash
# Ubuntu/Debian 계열
sudo apt update
sudo apt install acct

# CentOS/RHEL 계열
sudo yum install psacct
# 또는 (RHEL 8+)
sudo dnf install psacct

# Fedora
sudo dnf install psacct
```

##### 서비스 활성화
```bash
# psacct 서비스 활성화 및 시작
sudo systemctl enable psacct
sudo systemctl start psacct

# 서비스 상태 확인
sudo systemctl status psacct
```

##### 프로세스 계정 활성화
```bash
# 프로세스 계정 활성화
sudo accton /var/log/pacct

# 계정 파일 권한 설정
sudo chown root:root /var/log/pacct
sudo chmod 644 /var/log/pacct

# 계정 파일 크기 확인
ls -lh /var/log/pacct
```

##### 설정 파일 구성
```bash
# psacct 설정 파일 확인
sudo vi /etc/psacct.conf

# 주요 설정 옵션
ACCT_FILE="/var/log/pacct"        # 계정 파일 경로
ACCTON_ENABLED="yes"              # accton 자동 시작
SAVE_CORE="yes"                   # 코어 덤프 저장
```

#### 주요 명령어 및 사용법

##### accton - 프로세스 계정 제어

accton은 프로세스 계정 기능을 활성화하거나 비활성화하는 도구입니다.

###### 기본 사용법
```bash
# 프로세스 계정 활성화
sudo accton /var/log/pacct

# 프로세스 계정 비활성화
sudo accton off

# 계정 상태 확인
sudo accton /var/log/pacct && echo "Accounting enabled" || echo "Accounting disabled"
```

###### 고급 사용법
```bash
# 백업 파일로 계정 활성화
sudo accton /var/log/pacct.backup

# 계정 파일 크기 확인
ls -lh /var/log/pacct

# 계정 파일 권한 확인
ls -la /var/log/pacct
```

##### lastcomm - 실행된 명령어 기록

lastcomm은 실행된 명령어의 상세 기록을 조회하는 도구입니다.

###### 기본 사용법
```bash
# 모든 명령어 기록 (최신순)
sudo lastcomm

# 특정 사용자의 명령어 기록
sudo lastcomm username

# 특정 명령어의 실행 기록
sudo lastcomm command_name

# 최근 10개 명령어만 표시
sudo lastcomm | head -10
```

###### 고급 사용법
```bash
# 특정 시간대 명령어 기록
sudo lastcomm | grep "2024-01-15"

# 특정 사용자의 최근 명령어
sudo lastcomm username | head -20

# 특정 명령어의 실행 횟수
sudo lastcomm command_name | wc -l

# sudo 명령어만 필터링
sudo lastcomm | grep sudo

# 특정 시간 이후의 명령어
sudo lastcomm | awk '$3 >= "10:00:00"'
```

###### lastcomm 출력 해석
```bash
# 출력 형식: 명령어 사용자 터미널 플래그 시간
# 예: ls root pts/0 S 10:30:15
# 
# 플래그 의미:
# S: 명령어가 실행됨
# F: 명령어가 포크됨 (자식 프로세스)
# D: 명령어가 종료됨
# X: 명령어가 신호에 의해 종료됨
```

##### sa - 사용자별 리소스 사용 통계

sa는 사용자별 리소스 사용 통계를 제공하는 도구입니다.

###### 기본 사용법
```bash
# 사용자별 통계 요약
sudo sa

# 상세한 사용자별 통계
sudo sa -u

# 특정 사용자 통계
sudo sa -u username

# 명령어별 통계
sudo sa -c
```

###### 정렬 옵션
```bash
# CPU 시간 기준 정렬 (-s cpu)
sudo sa -s cpu

# 실시간 기준 정렬 (-s real)
sudo sa -s real

# 사용자 기준 정렬 (-s user)
sudo sa -s user

# 명령어 기준 정렬 (-s command)
sudo sa -s command
```

###### 출력 옵션
```bash
# 사용자별 요약 (-m)
sudo sa -m

# 명령어별 요약 (-c)
sudo sa -c

# 상세 정보 (-u)
sudo sa -u

# 백분율 표시 (-p)
sudo sa -p

# 시간 형식 지정 (-t)
sudo sa -t
```

###### sa 출력 해석
```bash
# 출력 형식 설명
# 1234    45.67re    12.34cp    username    command
# 
# 1234: 명령어 실행 횟수
# 45.67re: 총 실시간 (초)
# 12.34cp: 총 CPU 시간 (초)
# username: 사용자명
# command: 명령어명
```

##### dump-acct - 프로세스 기록 덤프

dump-acct는 프로세스 계정 파일의 원시 데이터를 덤프하는 도구입니다.

###### 기본 사용법
```bash
# 계정 파일 덤프
sudo dump-acct /var/log/pacct

# 사람이 읽기 쉬운 형태로 출력
sudo dump-acct /var/log/pacct | head -20

# 특정 사용자 필터링
sudo dump-acct /var/log/pacct | grep username
```

###### 고급 사용법
```bash
# 특정 시간대 필터링
sudo dump-acct /var/log/pacct | awk '$4 >= "10:00:00" && $4 <= "11:00:00"'

# 특정 명령어 필터링
sudo dump-acct /var/log/pacct | grep "sudo"

# 출력을 파일로 저장
sudo dump-acct /var/log/pacct > /tmp/accounting_dump.txt

# 압축된 계정 파일 덤프
sudo dump-acct /var/log/pacct.1.gz
```

###### dump-acct 출력 해석
```bash
# 출력 형식 설명
# 명령어 사용자 터미널 시작시간 종료시간 CPU시간 실시간 메모리 사용량
# 
# 예: ls root pts/0 10:30:15 10:30:15 0.00 0.00 1024
```

#### 고급 사용법
```bash
# 프로세스 계정 로테이션 스크립트
#!/bin/bash
LOG_FILE="/var/log/pacct"
BACKUP_DIR="/var/log/pacct_backup"
DATE=$(date +%Y%m%d_%H%M%S)

# 현재 계정 비활성화
sudo accton off

# 백업 생성
sudo cp $LOG_FILE $BACKUP_DIR/pacct_$DATE

# 새 계정 파일 생성
sudo touch $LOG_FILE
sudo chown root:root $LOG_FILE
sudo chmod 644 $LOG_FILE

# 계정 재활성화
sudo accton $LOG_FILE

echo "Process accounting rotated: $DATE"
```

## 예시

### 1. 실제 사용 사례

#### 시스템 성능 모니터링 스크립트
```bash
#!/bin/bash
# system_monitor.sh

LOG_DIR="/var/log/system_monitor"
DATE=$(date +%Y%m%d)
TIME=$(date +%H:%M:%S)

# 디렉토리 생성
mkdir -p $LOG_DIR

# CPU 사용률 기록
echo "$TIME - CPU Usage:" >> $LOG_DIR/cpu_$DATE.log
sar -u 1 1 | tail -1 >> $LOG_DIR/cpu_$DATE.log

# 메모리 사용률 기록
echo "$TIME - Memory Usage:" >> $LOG_DIR/memory_$DATE.log
sar -r 1 1 | tail -1 >> $LOG_DIR/memory_$DATE.log

# 디스크 I/O 기록
echo "$TIME - Disk I/O:" >> $LOG_DIR/disk_$DATE.log
iostat -x 1 1 | tail -2 >> $LOG_DIR/disk_$DATE.log

# 네트워크 사용률 기록
echo "$TIME - Network Usage:" >> $LOG_DIR/network_$DATE.log
sar -n DEV 1 1 | tail -1 >> $LOG_DIR/network_$DATE.log

# 로그 파일 크기 제한 (1MB)
find $LOG_DIR -name "*.log" -size +1M -exec truncate -s 1M {} \;
```

#### 사용자 활동 모니터링 스크립트
```bash
#!/bin/bash
# user_monitor.sh

LOG_FILE="/var/log/user_activity.log"
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M:%S)

# 현재 활성 사용자 확인
ACTIVE_USERS=$(who | awk '{print $1}' | sort | uniq)

echo "$DATE $TIME - Active Users: $ACTIVE_USERS" >> $LOG_FILE

# 각 사용자의 최근 명령어 확인
for user in $ACTIVE_USERS; do
    echo "$DATE $TIME - Recent commands for $user:" >> $LOG_FILE
    sudo lastcomm $user | head -5 >> $LOG_FILE
    echo "---" >> $LOG_FILE
done

# 사용자별 리소스 사용 통계
echo "$DATE $TIME - User Resource Usage:" >> $LOG_FILE
sudo sa -m >> $LOG_FILE
echo "---" >> $LOG_FILE
```

### 2. 고급 패턴

#### 실시간 모니터링 대시보드
```bash
#!/bin/bash
# realtime_dashboard.sh

clear
echo "=== System Performance Dashboard ==="
echo "Press Ctrl+C to exit"
echo

while true; do
    # 현재 시간
    echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "----------------------------------------"
    
    # CPU 사용률
    echo "CPU Usage:"
    sar -u 1 1 | tail -1 | awk '{print "  User: " $3 "% | System: " $5 "% | I/O Wait: " $6 "%"}'
    
    # 메모리 사용률
    echo "Memory Usage:"
    sar -r 1 1 | tail -1 | awk '{print "  Used: " $3 "KB | Free: " $4 "KB | Available: " $7 "KB"}'
    
    # 디스크 사용률
    echo "Disk I/O:"
    iostat -x 1 1 | tail -2 | awk 'NR==2 {print "  " $1 ": " $3 " tps | " $4 " KB/s"}'
    
    # 네트워크 사용률
    echo "Network Usage:"
    sar -n DEV 1 1 | grep -E "(eth0|wlan0)" | tail -1 | awk '{print "  " $2 ": " $5 " pkt/s | " $6 " KB/s"}'
    
    # 활성 사용자 수
    echo "Active Users: $(who | wc -l)"
    
    echo "----------------------------------------"
    sleep 5
    clear
done
```

#### 보안 감사 스크립트
```bash
#!/bin/bash
# security_audit.sh

AUDIT_LOG="/var/log/security_audit.log"
DATE=$(date +%Y-%m-%d)

echo "=== Security Audit Report - $DATE ===" >> $AUDIT_LOG

# 의심스러운 명령어 실행 확인
echo "Suspicious Commands:" >> $AUDIT_LOG
sudo lastcomm | grep -E "(sudo|su|passwd|chmod|chown)" >> $AUDIT_LOG

# 높은 CPU 사용 프로세스 확인
echo "High CPU Usage Processes:" >> $AUDIT_LOG
ps aux --sort=-%cpu | head -10 >> $AUDIT_LOG

# 높은 메모리 사용 프로세스 확인
echo "High Memory Usage Processes:" >> $AUDIT_LOG
ps aux --sort=-%mem | head -10 >> $AUDIT_LOG

# 네트워크 연결 확인
echo "Network Connections:" >> $AUDIT_LOG
netstat -tuln >> $AUDIT_LOG

# 로그인 시도 확인
echo "Recent Login Attempts:" >> $AUDIT_LOG
last | head -20 >> $AUDIT_LOG

echo "=== End of Report ===" >> $AUDIT_LOG
```

## 운영 팁

### 성능 최적화

#### 데이터 수집 주기 조정
```bash
# sysstat 설정 최적화
sudo vi /etc/cron.d/sysstat

# 기본값: 10분마다 수집
#-*/10 * * * * root /usr/lib/sysstat/debian-sa1 1 1

# 5분마다 수집으로 변경
#-*/5 * * * * root /usr/lib/sysstat/debian-sa1 1 1

# 1분마다 수집 (고성능 모니터링)
#-* * * * * root /usr/lib/sysstat/debian-sa1 1 1
```

#### 로그 파일 관리
```bash
# 로그 로테이션 설정
sudo vi /etc/logrotate.d/sysstat

/var/log/sa/sa* {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}
```

### 에러 처리

#### 모니터링 도구 상태 확인
```bash
#!/bin/bash
# check_monitoring_tools.sh

# sysstat 서비스 상태 확인
if ! systemctl is-active --quiet sysstat; then
    echo "ERROR: sysstat service is not running"
    sudo systemctl start sysstat
fi

# psacct 서비스 상태 확인
if ! systemctl is-active --quiet psacct; then
    echo "ERROR: psacct service is not running"
    sudo systemctl start psacct
fi

# 계정 파일 존재 확인
if [ ! -f /var/log/pacct ]; then
    echo "ERROR: Process accounting file not found"
    sudo touch /var/log/pacct
    sudo accton /var/log/pacct
fi

# 디스크 공간 확인
DISK_USAGE=$(df /var/log | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 90 ]; then
    echo "WARNING: Disk usage is high: ${DISK_USAGE}%"
fi
```

## 참고

### SA vs PSACCT 비교

| 측면 | SA (System Activity) | PSACCT (Process Accounting) |
|------|---------------------|----------------------------|
| **데이터 단위** | 시스템 전체 | 개별 프로세스/사용자 |
| **주요 기능** | CPU, 메모리, 네트워크 등 | 명령어 기록 및 사용자 통계 |
| **용도** | 시스템 성능 모니터링 및 튜닝 | 보안 감사 및 사용자 활동 추적 |
| **데이터 수집** | 자동 (cron) | 실시간 |
| **저장 공간** | 적음 | 많음 |
| **성능 영향** | 낮음 | 중간 |

### 모니터링 도구 선택 가이드

| 상황 | 권장 도구 | 이유 |
|------|-----------|------|
| **시스템 성능 분석** | SA (sar, iostat, mpstat) | 시스템 전체 성능 지표 제공 |
| **사용자 활동 추적** | PSACCT (lastcomm, sa) | 개별 사용자 활동 상세 기록 |
| **보안 감사** | PSACCT | 명령어 실행 이력 추적 |
| **용량 계획** | SA | 장기간 성능 데이터 수집 |
| **문제 진단** | SA + PSACCT | 시스템 및 프로세스 레벨 분석 |

### 결론

SA와 PSACCT는 Linux 시스템 모니터링의 핵심 도구로, 각각 시스템 성능과 사용자 활동을 추적하는 데 특화되어 있습니다. 

#### 주요 포인트
- **SA**: 시스템 전체 성능 모니터링에 최적화된 도구
- **PSACCT**: 사용자 활동 추적 및 보안 감사에 특화된 도구
- **통합 활용**: 두 도구를 함께 사용하여 포괄적인 시스템 관리 가능
- **정기 관리**: 적절한 설정과 로그 관리를 통한 효과적인 모니터링
- **보안 강화**: 실시간 모니터링과 정기적인 보안 감사로 시스템 안정성 확보

---

## 참조

### 공식 문서
- [sysstat 공식 문서](https://github.com/sysstat/sysstat)
- [psacct 공식 문서](https://www.gnu.org/software/acct/)
- [Linux man pages - sar](https://man7.org/linux/man-pages/man1/sar.1.html)
- [Linux man pages - iostat](https://man7.org/linux/man-pages/man1/iostat.1.html)
- [Linux man pages - mpstat](https://man7.org/linux/man-pages/man1/mpstat.1.html)
- [Linux man pages - accton](https://man7.org/linux/man-pages/man8/accton.8.html)
- [Linux man pages - lastcomm](https://man7.org/linux/man-pages/man1/lastcomm.1.html)
- [Linux man pages - sa](https://man7.org/linux/man-pages/man1/sa.1.html)

### 관련 리소스
- [Red Hat Enterprise Linux Performance Tuning Guide](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/monitoring_and_managing_system_status_and_performance/)
- [Ubuntu Server Guide - System Monitoring](https://ubuntu.com/server/docs/monitoring)
- [Linux Performance and Tuning Guidelines](https://www.ibm.com/docs/en/linux-on-systems?topic=linux-performance-tuning-guidelines)

### 추가 학습 자료
- [Linux System Administration](https://www.linux.org/forums/linux-system-administration/)
- [Linux Performance Monitoring Tools](https://www.tecmint.com/linux-performance-monitoring-tools/)
- [Process Accounting in Linux](https://www.linuxjournal.com/article/6144)

### 도구 및 스크립트
- [sysstat GitHub Repository](https://github.com/sysstat/sysstat)
- [psacct Source Code](https://www.gnu.org/software/acct/)
- [Linux Performance Tools](https://github.com/brendangregg/perf-tools)

### 커뮤니티 및 지원
- [Linux Questions](https://www.linuxquestions.org/)
- [Stack Overflow - Linux](https://stackoverflow.com/questions/tagged/linux)
- [Red Hat Customer Portal](https://access.redhat.com/)
- [Ubuntu Forums](https://ubuntuforums.org/)

---
*문서 작성일: 2025-09-20*  
*최종 수정일: 2025-09-20*

