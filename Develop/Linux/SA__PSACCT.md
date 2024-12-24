
# SA와 PSACCT 모니터링 툴

## 개요

### SA(System Activity)
`sa`는 시스템 활동(System Activity)을 모니터링하기 위해 사용되는 Linux 기반 도구로, `sysstat` 패키지의 일부입니다. CPU, 메모리, I/O, 네트워크 사용량 등을 분석하여 성능 병목현상을 파악하거나 시스템 튜닝에 유용합니다.

### PSACCT(Process Accounting)
`psacct`는 프로세스 단위의 모니터링을 제공하며, 시스템에서 실행되는 개별 명령어 및 사용자 활동을 추적합니다. 리소스 사용량과 사용자의 작업 내역을 기록하고, 보안 감사나 사용자 활동 분석에 유용합니다.

---

## SA 사용법

### 설치
```bash
sudo apt install sysstat  # Ubuntu/Debian
sudo yum install sysstat  # CentOS/Red Hat
```

### 주요 명령어
- **sar**: 시스템 성능 데이터 조회
- **iostat**: 디스크 I/O 및 CPU 사용량 분석
- **mpstat**: CPU 코어별 사용률 출력

### 예제
1. **CPU 사용량 확인**
   ```bash
   sar -u 1 5
   ```
    - 1초 간격으로 5번 CPU 사용률 출력

2. **메모리 사용량**
   ```bash
   sar -r
   ```

3. **네트워크 상태**
   ```bash
   sar -n DEV
   ```

---

## PSACCT 사용법

### 설치
```bash
sudo apt install acct  # Ubuntu/Debian
sudo yum install psacct  # CentOS/Red Hat
```

### 주요 명령어
- **accton**: 프로세스 계정 활성화/비활성화
- **lastcomm**: 실행된 명령어 기록 확인
- **sa**: 사용자별 리소스 사용량 통계
- **dump-acct**: 프로세스 기록 덤프

### 예제
1. **psacct 활성화**
   ```bash
   sudo systemctl start psacct
   sudo systemctl enable psacct
   ```

2. **최근 실행된 명령어 확인**
   ```bash
   lastcomm
   ```

3. **사용자별 리소스 사용 통계**
   ```bash
   sa
   ```

---

## 차이점 비교

| 특징          | SA                         | PSACCT                     |
|---------------|----------------------------|----------------------------|
| 데이터 단위    | 시스템 전체                 | 개별 프로세스/사용자         |
| 주요 기능      | CPU, 메모리, 네트워크 등    | 명령어 기록 및 사용자 통계    |
| 용도          | 시스템 성능 모니터링 및 튜닝 | 보안 감사 및 사용자 활동 추적 |

---

## 결론

SA와 PSACCT는 각각 시스템과 프로세스를 모니터링하는 데 특화된 도구입니다. 두 툴을 적절히 조합하여 사용하면 시스템 성능과 사용자 활동을 효과적으로 분석할 수 있습니다.
