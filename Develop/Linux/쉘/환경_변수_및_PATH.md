---
title: 환경 변수 및 PATH
tags: [linux, environment-variable, path, bashrc, profile]
updated: 2025-12-08
---

# 환경 변수 및 PATH

## 개요

환경 변수 설정 및 PATH 관리 방법. 환경 변수는 애플리케이션 설정과 동작에 영향을 준다.

## 환경 변수 확인

### env

모든 환경 변수를 확인한다.

```bash
env
env | grep PATH
```

### printenv

환경 변수를 출력한다.

```bash
printenv
printenv PATH
printenv HOME
```

### echo

특정 환경 변수를 출력한다.

```bash
echo $PATH
echo ${PATH}                     # 명시적 형식 (권장)
echo $HOME
```

변수명이 명확하지 않을 때는 `${VARIABLE}` 형식을 사용한다.

## 환경 변수 설정

### 임시 설정

```bash
export VAR="value"               # 현재 세션에만 적용
VAR="value"                      # 현재 쉘에만 적용
```

터미널을 닫으면 사라진다. 테스트할 때 사용한다.

### 영구 설정

```bash
# ~/.bashrc에 추가
export VAR="value"

# 적용
source ~/.bashrc
# 또는
. ~/.bashrc
```

## 주요 환경 변수

### PATH

명령어를 찾는 경로.

```bash
echo $PATH
# /usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin
```

**PATH 추가:**
```bash
export PATH=$PATH:/new/path       # 기존 PATH에 추가
export PATH=/new/path:$PATH       # 앞에 추가 (우선순위 높음)
```

PATH 앞에 추가하면 우선순위가 높다. 시스템 명령어를 덮어쓰지 않도록 주의한다.

### HOME

사용자의 홈 디렉토리.

```bash
echo $HOME
# /home/username
```

### USER / USERNAME

현재 사용자 이름.

```bash
echo $USER
echo $USERNAME
```

### SHELL

현재 쉘 경로.

```bash
echo $SHELL
# /bin/bash
```

### PWD

현재 작업 디렉토리.

```bash
echo $PWD
```

### LANG / LC_ALL

언어 설정.

```bash
export LANG=ko_KR.UTF-8
export LC_ALL=ko_KR.UTF-8
```

## 쉘 설정 파일

### 로그인 쉘 vs 비로그인 쉘

**로그인 쉘:**
- SSH로 접속
- `su -`로 전환
- 읽는 파일: `~/.bash_profile`, `~/.profile`

**비로그인 쉘:**
- 새 터미널 창
- `su`로 전환
- 읽는 파일: `~/.bashrc`

### 설정 파일 순서

**로그인 쉘:**
1. `/etc/profile`
2. `~/.bash_profile` (있으면)
3. `~/.profile` (bash_profile 없으면)

**비로그인 쉘:**
1. `~/.bashrc`
2. `/etc/bashrc` (일부 시스템)

일반적으로 `~/.bashrc`에 설정하고, `~/.bash_profile`에서 `~/.bashrc`를 source한다.

### 설정 파일 예시

```bash
# ~/.bashrc
# PATH 추가
export PATH=$PATH:/usr/local/bin

# 환경 변수
export EDITOR=vim
export LANG=ko_KR.UTF-8

# 별칭
alias ll='ls -lh'
alias la='ls -lah'

# 함수
myfunction() {
    echo "Hello"
}
```

```bash
# ~/.bash_profile
# bashrc 로드
if [ -f ~/.bashrc ]; then
    . ~/.bashrc
fi

# 로그인 쉘 전용 설정
export PATH=$PATH:$HOME/bin
```

## 시스템 전체 설정

### /etc/profile

모든 사용자에게 적용되는 설정.

```bash
# /etc/profile
export PATH=$PATH:/usr/local/bin
```

시스템 전체 설정은 신중하게 수정한다. 모든 사용자에게 영향을 준다.

### /etc/environment

시스템 전체 환경 변수.

```bash
# /etc/environment
PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
```

일부 시스템에서만 사용된다. Debian/Ubuntu에서 주로 사용한다.

## PATH 관리

### PATH 확인

```bash
echo $PATH | tr ':' '\n'
which command
whereis command
```

### PATH 추가

```bash
# 현재 세션에만
export PATH=$PATH:/new/path

# 영구적으로 (~/.bashrc)
echo 'export PATH=$PATH:/new/path' >> ~/.bashrc
source ~/.bashrc
```

### PATH 우선순위

```bash
# 앞에 추가 (우선순위 높음)
export PATH=/new/path:$PATH

# 뒤에 추가 (우선순위 낮음)
export PATH=$PATH:/new/path
```

시스템 명령어를 덮어쓰지 않도록 PATH 앞에 추가할 때 주의한다.

## 애플리케이션별 환경 변수

### Node.js

```bash
export NODE_ENV=production
export NODE_PATH=/usr/lib/node_modules
```

### Python

```bash
export PYTHONPATH=/usr/lib/python3.9
export PYTHONUNBUFFERED=1
```

### Java

```bash
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk
export PATH=$PATH:$JAVA_HOME/bin
```

### Docker

```bash
export DOCKER_HOST=tcp://192.168.1.1:2376
```

## 환경 변수 사용

### 스크립트에서

```bash
#!/bin/bash
echo "User: $USER"
echo "Home: $HOME"
echo "Path: $PATH"
```

### 조건부 사용

```bash
# 기본값 설정
${VAR:-default}                   # VAR가 없으면 default
${VAR:=default}                   # VAR가 없으면 default로 설정
${VAR:+value}                     # VAR가 있으면 value
```

**예시:**
```bash
echo ${EDITOR:-vim}               # EDITOR가 없으면 vim
```

## 환경 변수 보안

### 민감한 정보

```bash
# 나쁜 예 (히스토리에 저장됨)
export PASSWORD="secret"

# 좋은 예 (환경 변수 파일 사용)
# ~/.env
export PASSWORD="secret"

# 로드
source ~/.env
```

비밀번호나 API 키는 환경 변수 파일로 관리하고, 파일 권한을 제한한다.

### 환경 변수 파일 권한

```bash
chmod 600 ~/.env                  # 소유자만 읽기/쓰기
chown $USER:$USER ~/.env
```

## 문제 해결

### 환경 변수가 적용되지 않을 때

```bash
# 설정 파일 확인
cat ~/.bashrc
cat ~/.bash_profile

# 수동으로 적용
source ~/.bashrc

# 쉘 재시작
exec bash
```

### PATH 문제

```bash
# 명령어를 찾을 수 없을 때
which command
echo $PATH
export PATH=$PATH:/correct/path
```

### 환경 변수 확인

```bash
# 특정 변수 확인
echo $VARIABLE
printenv VARIABLE

# 모든 변수에서 검색
env | grep VARIABLE
```

환경 변수 문제는 설정 파일과 현재 세션을 모두 확인한다.
