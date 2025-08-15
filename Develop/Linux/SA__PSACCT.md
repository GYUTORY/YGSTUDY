---
title: SA와 PSACCT 모니터링 도구 완벽 가이드
tags: [linux, system-monitoring, sa, psacct, sysstat, process-accounting]
updated: 2025-08-10
---

# SA와 PSACCT 모니터링 도구 완벽 가이드

## 배경

SA(System Activity)와 PSACCT(Process Accounting)는 Linux 시스템에서 성능 모니터링과 사용자 활동 추적을 위한 핵심 도구입니다. SA는 시스템 전체의 성능 지표를 제공하고, PSACCT는 개별 프로세스와 사용자 활동을 상세히 기록합니다.

### 모니터링 도구의 필요성
- **성능 분석**: 시스템 병목 현상 파악 및 최적화
- **보안 감사**: 사용자 활동 추적 및 보안 사고 조사
- **리소스 관리**: CPU, 메모리, 디스크 사용량 모니터링
- **용량 계획**: 시스템 리소스 사용 패턴 분석
- **문제 진단**: 시스템 문제 발생 시 원인 분석

### 기본 개념
- **SA (System Activity)**: sysstat 패키지의 일부로 시스템 성능 데이터 수집
- **PSACCT (Process Accounting)**: 프로세스 단위의 상세한 활동 기록
- **sar**: 시스템 활동 보고서 생성 도구
- **accton**: 프로세스 계정 활성화/비활성화 도구
- **lastcomm**: 실행된 명령어 기록 조회 도구

## 핵심

### 1. SA (System Activity) 도구

#### 설치 및 설정
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install sysstat

# CentOS/RHEL
sudo yum install sysstat

# 데이터 수집 활성화
sudo systemctl enable sysstat
sudo systemctl start sysstat

# 설정 파일 확인
sudo vi /etc/default/sysstat
```

#### 주요 명령어

##### sar - 시스템 활동 보고서
```bash
# CPU 사용률 (1초 간격, 5번)
sar -u 1 5

# 메모리 사용률
sar -r 1 5

# 디스크 I/O 통계
sar -d 1 5

# 네트워크 인터페이스 통계
sar -n DEV 1 5

# 네트워크 오류 통계
sar -n EDEV 1 5

# 프로세스 생성 및 컨텍스트 스위칭
sar -w 1 5

# 시스템 부하 평균
sar -q 1 5
```

##### iostat - 디스크 I/O 및 CPU 통계
```bash
# 기본 CPU 및 디스크 통계
iostat

# 2초 간격으로 3번 출력
iostat 2 3

# 특정 디스크만 모니터링
iostat -x sda 1 5

# CPU 사용률 상세 정보
iostat -c 1 5
```

##### mpstat - CPU 코어별 통계
```bash
# 모든 CPU 코어 통계
mpstat -P ALL 1 5

# 특정 CPU 코어 통계
mpstat -P 0 1 5

# CPU 사용률 상세 정보
mpstat -u 1 5
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

#### 설치 및 설정
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install acct

# CentOS/RHEL
sudo yum install psacct

# 서비스 활성화
sudo systemctl enable psacct
sudo systemctl start psacct

# 프로세스 계정 활성화
sudo accton /var/log/pacct
```

#### 주요 명령어

##### accton - 프로세스 계정 제어
```bash
# 프로세스 계정 활성화
sudo accton /var/log/pacct

# 프로세스 계정 비활성화
sudo accton off

# 계정 파일 크기 확인
ls -lh /var/log/pacct
```

##### lastcomm - 실행된 명령어 기록
```bash
# 모든 명령어 기록
sudo lastcomm

# 특정 사용자의 명령어 기록
sudo lastcomm username

# 특정 명령어의 실행 기록
sudo lastcomm command_name

# 최근 10개 명령어만 표시
sudo lastcomm | head -10

# 특정 시간대 명령어 기록
sudo lastcomm | grep "2024-01-15"
```

##### sa - 사용자별 리소스 사용 통계
```bash
# 사용자별 통계 요약
sudo sa

# 상세한 사용자별 통계
sudo sa -u

# 특정 사용자 통계
sudo sa -u username

# 명령어별 통계
sudo sa -c

# CPU 시간 기준 정렬
sudo sa -s cpu

# 실시간 사용자별 통계
sudo sa -m
```

##### dump-acct - 프로세스 기록 덤프
```bash
# 계정 파일 덤프
sudo dump-acct /var/log/pacct

# 사람이 읽기 쉬운 형태로 출력
sudo dump-acct /var/log/pacct | head -20

# 특정 사용자 필터링
sudo dump-acct /var/log/pacct | grep username
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
적절한 설정과 로그 관리를 통해 시스템 성능과 보안을 효과적으로 모니터링하세요.
실시간 모니터링과 정기적인 보안 감사를 통해 시스템의 안정성과 보안을 확보하세요.

