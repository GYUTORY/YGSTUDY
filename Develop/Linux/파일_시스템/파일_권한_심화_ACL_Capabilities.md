---
title: 파일 권한 심화 - ACL, Special Permissions, Capabilities
tags: [linux, acl, capabilities, setuid, xattr, chattr, security, container]
updated: 2026-04-23
---

# 파일 권한 심화 - ACL, Special Permissions, Capabilities

## 개요

chmod/chown 기초만으로는 실제 운영에서 마주치는 권한 문제를 다 풀 수 없다. 특정 한 사람에게만 쓰기를 주고 싶을 때, 스크립트에 SetUID를 걸었는데 무시될 때, nginx가 80번 포트를 바인딩 못 할 때, 로그 파일이 갑자기 수정 불가가 될 때, 컨테이너가 mount를 못 할 때 — 이런 상황은 모두 기본 rwx 3비트 바깥 세계의 이야기다. 여기서는 ACL, Special Permissions의 내부 동작, Linux Capabilities, 확장 속성(xattr/chattr)을 실제로 디버깅할 수 있는 수준까지 다룬다.

rwx 9비트는 1970년대 Unix의 유산이다. 지금의 Linux는 그 위에 최소 네 개의 레이어가 얹혀 있다. ACL은 사용자/그룹을 더 세밀하게 나누고, Special Permissions는 프로세스의 UID/GID 전환을 다루고, Capabilities는 root 권한을 40여 개로 쪼개고, xattr은 파일 단위의 추가 메타데이터를 저장한다. 어떤 레이어에서 문제가 터졌는지 구분하는 것부터 시작해야 한다.

## ACL 심화 - mask, default ACL, chmod 충돌

### ACL mask의 역할

`getfacl` 결과에 나오는 `mask` 항목은 장식이 아니다. 이건 ACL로 부여한 모든 그룹/명명된 사용자 권한의 상한선이다. mask가 `r--`이면, 아무리 `u:john:rwx`로 권한을 줘도 john은 읽기만 가능하다.

```bash
$ setfacl -m u:john:rwx file.txt
$ getfacl file.txt
# file: file.txt
# owner: alice
# group: alice
user::rw-
user:john:rwx        #effective:rw-
group::r--
mask::rw-
other::r--
```

`#effective:rw-`를 보면 실제 적용 권한은 `rw-`다. 이게 mask 때문이다. ACL 기초 문서에서는 mask를 건너뛰기 쉬운데, 실제 운영에서 "분명 rwx 줬는데 왜 x가 안 먹냐"의 90%가 이 문제다.

mask는 setfacl 할 때 자동으로 계산된다. `setfacl -m u:john:rwx` 하면 mask도 `rwx`로 자동 갱신된다. 문제는 **그 뒤에 chmod를 실행하는 순간** 터진다.

### chmod와 ACL의 충돌

POSIX ACL이 설정된 파일에서 `chmod` 명령은 group 비트가 아니라 **mask**를 바꾼다. 이게 가장 함정이다.

```bash
$ setfacl -m u:john:rwx file.txt
$ ls -l file.txt
-rw-rwxr--+ 1 alice alice 0 Apr 23 10:00 file.txt

$ chmod 640 file.txt
$ getfacl file.txt
# file: file.txt
user::rw-
user:john:rwx        #effective:r--
group::r--
mask::r--
other::---
```

`chmod 640`을 실행하는 순간 mask가 `r--`로 줄어들었다. john에게 준 rwx가 effective `r--`로 축소된다. ACL을 건 파일에는 chmod를 쓰면 안 된다는 말이 여기서 나온다. 또는 chmod 뒤에 setfacl을 다시 실행해야 한다.

`ls -l`에서 파일 모드 끝에 붙은 `+` 기호가 "이 파일에 ACL이 있다"는 표시다. 운영 중인 서버에서 권한 문제를 볼 때 `+`가 보이면 반드시 `getfacl`로 확인해야 한다.

### default ACL과 상속

디렉토리에 default ACL을 설정하면, 그 아래 새로 만들어지는 파일/디렉토리가 ACL을 상속받는다. 여기서 상속은 "복사"지 "참조"가 아니다. 부모의 default ACL을 변경해도 이미 존재하는 자식 파일의 ACL은 바뀌지 않는다.

```bash
$ setfacl -d -m u:deploy:rwx /srv/app
$ getfacl /srv/app
# file: srv/app
user::rwx
group::r-x
other::r-x
default:user::rwx
default:user:deploy:rwx
default:group::r-x
default:mask::rwx
default:other::r-x

$ touch /srv/app/new_file
$ getfacl /srv/app/new_file
# file: srv/app/new_file
user::rw-
user:deploy:rwx      #effective:rw-
group::r--
mask::rw-
other::r--
```

새 파일에 default ACL이 그대로 복사된 걸 볼 수 있다. 실제 파일 권한(access ACL)은 default에 umask를 반영해서 결정된다. 위에서 deploy에게 rwx를 줬는데 effective가 rw-인 이유는, 새 파일의 기본 mask가 파일 모드(umask 적용 결과)를 따라가기 때문이다.

이게 웹 서버 배포 디렉토리에서 자주 문제가 된다. deploy 사용자가 `/srv/app` 아래에 파일을 만들 때마다 실행 권한을 줘야 하는데 default ACL만 설정하고 umask를 022로 두면 실행 비트가 사라진다. 해결은 deploy 프로세스의 umask를 002로 바꾸거나, 배포 후 명시적으로 setfacl을 다시 거는 것이다.

default ACL을 일괄 제거하려면 `setfacl -k`를 쓴다. access ACL까지 싹 지우려면 `-b`다. 헷갈리면 `getfacl -R /path`로 먼저 현재 상태를 덤프해서 diff 뜨는 게 안전하다.

### ACL이 먹히는지 확인

ACL은 파일시스템이 지원해야 한다. ext4/xfs는 기본 지원하지만 마운트 옵션을 확인해야 한다.

```bash
$ mount | grep ' on /srv '
/dev/sdb1 on /srv type ext4 (rw,relatime,acl)

$ tune2fs -l /dev/sdb1 | grep "Default mount options"
Default mount options:    user_xattr acl
```

커널 6.x에서는 ext4의 acl이 기본 활성이라 굳이 명시 안 해도 되지만, 구버전 RHEL/CentOS에서는 `/etc/fstab`에 `acl` 옵션이 필요하다. NFS는 별도로 `nfs4_acl`을 쓴다. POSIX ACL과 호환되지만 표현이 다르고, `setfacl` 대신 `nfs4_setfacl`을 쓴다.

## Special Permissions의 실제 동작

### SetUID가 스크립트에서 무시되는 이유

기초 문서에서 "SetUID를 걸면 파일 소유자 권한으로 실행된다"고 설명하지만, 이 규칙은 **바이너리에만 적용**된다. 스크립트(#!로 시작하는 파일)에는 SetUID가 무시된다.

```bash
$ cat /tmp/whoami.sh
#!/bin/bash
whoami
id

$ sudo chown root:root /tmp/whoami.sh
$ sudo chmod 4755 /tmp/whoami.sh
$ ls -l /tmp/whoami.sh
-rwsr-xr-x 1 root root 27 Apr 23 10:15 /tmp/whoami.sh

$ ./whoami.sh
alice
uid=1000(alice) gid=1000(alice) ...
```

분명 `s` 비트가 걸려 있는데 root로 실행되지 않는다. 이건 버그가 아니라 의도된 보안 정책이다. 리눅스 커널은 인터프리터 스크립트의 SetUID를 의도적으로 무시한다. 이유는 race condition 때문이다 — 커널이 shebang을 읽고 `/bin/bash`를 SetUID된 UID로 실행하려는 사이에 공격자가 스크립트 파일을 바꿔치기할 수 있다.

그래서 "특정 명령만 다른 사용자로 실행시키고 싶다"는 요구는 세 가지 방법 중 하나로 풀어야 한다.

첫째, sudoers에 NOPASSWD로 등록한다. 가장 흔한 해법이다.

```
alice ALL=(root) NOPASSWD: /usr/local/bin/restart_app
```

둘째, C 래퍼를 만들어서 그걸 SetUID로 건다. 래퍼가 execve로 스크립트를 호출한다. 과거에 흔했지만 유지보수 부담 때문에 요즘은 잘 안 쓴다.

셋째, 스크립트가 특정 작업만 필요하면 Capability로 해결한다. 이게 다음 주제다.

### SetUID 대신 Capability로 가는 흐름

전통적으로 ping 명령은 ICMP 소켓을 열기 위해 root 권한이 필요했고, 그래서 `/bin/ping`은 SetUID root였다. 문제는 ping에 버그가 하나 터지면 전체 root 권한이 탈취된다는 점이다.

```bash
# 예전 방식 - 지금도 일부 배포판은 이렇다
$ ls -l /bin/ping
-rwsr-xr-x 1 root root ... /bin/ping

# 요즘 방식 - Ubuntu 22.04 이후
$ ls -l /bin/ping
-rwxr-xr-x 1 root root ... /bin/ping
$ getcap /bin/ping
/bin/ping cap_net_raw=ep
```

SetUID가 사라지고 대신 `cap_net_raw`라는 capability만 붙어 있다. ping은 ICMP 소켓 열 때 필요한 최소 권한만 갖고, 나머지는 일반 사용자 권한이다. 버그가 터져도 피해 범위가 줄어든다.

### SetGID 디렉토리와 group 상속의 함정

디렉토리에 SetGID를 걸면 그 아래 만들어지는 파일이 디렉토리의 그룹을 상속받는다. 공유 디렉토리에 흔히 쓴다.

```bash
$ sudo mkdir /shared/team
$ sudo chgrp developers /shared/team
$ sudo chmod 2775 /shared/team
$ ls -ld /shared/team
drwxrwsr-x 2 root developers 4096 Apr 23 /shared/team
```

여기서 자주 놓치는 건, SetGID는 **파일의 그룹만 상속**한다는 점이다. 파일의 group 권한(rw나 rwx)은 상속하지 않는다. 그건 umask가 결정한다. umask가 022면 group은 `r-x`가 되고, 002여야 `rwx`가 된다.

그래서 공유 디렉토리는 SetGID + default ACL + umask 002를 세트로 쓴다. 하나만 빠지면 "A가 만든 파일을 B가 수정 못한다"는 문의가 매주 올라온다.

### Sticky Bit의 숨은 효과

`/tmp`의 Sticky bit(`+t`)는 "자기가 만든 파일만 삭제 가능"으로 알려져 있다. 정확하게는 "디렉토리 쓰기 권한이 있어도, 파일 소유자나 디렉토리 소유자나 root가 아니면 삭제/이름변경 불가"다. 실무에서 `/tmp`에 다른 사용자 파일을 rm 하려다 안 되면 이거다.

한 가지 덜 알려진 동작이 있다. Linux 커널에 `fs.protected_regular`, `fs.protected_symlinks`, `fs.protected_hardlinks`, `fs.protected_fifos` sysctl이 있는데, 이게 Sticky bit가 걸린 디렉토리에서 특정 파일 타입의 열기/따라가기를 제한한다. `/tmp`에서 심볼릭 링크 공격을 막는 기본 보호 장치다. 보통 활성돼 있지만 컨테이너나 오래된 시스템에선 꺼져 있을 수 있다.

```bash
$ sysctl fs.protected_symlinks fs.protected_hardlinks
fs.protected_symlinks = 1
fs.protected_hardlinks = 1
```

## Linux Capabilities

### 왜 필요한가

Unix 전통에서 "root냐 아니냐"는 이진 판단이다. 프로세스가 root면 뭐든 할 수 있고, 아니면 권한 검사에 걸린다. 이게 1999년 POSIX.1e 초안에서 쪼개지기 시작했다. 현재 리눅스는 root의 권한을 40여 개의 capability로 나눈다.

대표적인 것들:

- `cap_net_bind_service`: 1024 미만 포트 바인딩
- `cap_net_raw`: raw/ICMP 소켓 열기 (ping, nmap)
- `cap_net_admin`: 네트워크 설정 변경 (ip, iptables)
- `cap_sys_admin`: 거의 root에 가까운 만능 권한 (mount, quotactl 등)
- `cap_sys_ptrace`: 다른 프로세스 추적 (strace, gdb)
- `cap_chown`: 파일 소유자 변경
- `cap_dac_override`: 파일 권한 무시하고 읽기/쓰기
- `cap_kill`: 다른 사용자 프로세스에 시그널 보내기

`cap_sys_admin`은 별명이 "the new root"다. mount, swapon, 네임스페이스 생성 등 너무 많은 권한이 묶여 있어서 실질적으로 root와 다름없다. 그래서 "최소 권한"을 논할 때 `cap_sys_admin`을 drop하는 게 컨테이너 보안의 첫 단추다.

### setcap/getcap 기본

파일 capability는 xattr로 파일에 저장된다. setcap으로 붙이고 getcap으로 읽는다.

```bash
# nginx가 80번을 바인딩하되 root로 안 뜨고 싶다
$ sudo setcap 'cap_net_bind_service=+ep' /usr/sbin/nginx
$ getcap /usr/sbin/nginx
/usr/sbin/nginx cap_net_bind_service=ep

# 여러 개 동시에
$ sudo setcap 'cap_net_bind_service,cap_net_admin=+ep' /usr/local/bin/myapp

# 제거
$ sudo setcap -r /usr/sbin/nginx
```

`=ep`의 의미는 permitted + effective다. capability에는 플래그가 세 개 있다.

- **Permitted(P)**: 프로세스가 사용할 수 있는 권한의 상한
- **Effective(E)**: 현재 활성화된 권한 (실제 권한 검사에 쓰인다)
- **Inheritable(I)**: exec 시 자식에게 물려줄 권한

단순 바이너리는 `=ep`로 붙이면 대부분 동작한다. effective까지 올라가 있으니 실행하는 순간 권한이 활성화된다. `=p`만 붙이면 permitted만 있고 effective는 꺼져 있어서, 프로그램이 명시적으로 `cap_set_proc`로 올려야 한다. libcap을 이해하는 프로그램이 아니면 대부분 동작하지 않는다.

### ping의 cap_net_raw

ping은 raw socket이 필요하다. 보통 배포판은 두 가지 방식 중 하나를 쓴다.

```bash
# 방식 A: file capability
$ getcap /bin/ping
/bin/ping cap_net_raw=ep

# 방식 B: unprivileged ICMP
$ sysctl net.ipv4.ping_group_range
net.ipv4.ping_group_range = 0 2147483647
```

B 방식은 커널이 지정된 gid 범위의 사용자에게 ICMP echo 전용 소켓(IPPROTO_ICMP)을 허용한다. 이건 진짜 raw socket이 아니라 echo request/reply만 가능한 제한된 소켓이다. 일반 ping엔 충분하다. 컨테이너에서 `ping: socket: Operation not permitted`가 나면 이 두 방식 모두 차단된 상황이다.

### nginx 80번 포트 바인딩

운영에서 가장 흔한 사례가 1024 미만 포트 바인딩이다. nginx, haproxy 같은 데몬이 80/443을 직접 열어야 할 때 root로 띄우고 나서 worker만 nobody로 내리는 전통 방식이 있었다. 요즘은 아예 처음부터 non-root로 띄우고 capability만 준다.

```bash
$ sudo useradd -r -s /sbin/nologin nginx
$ sudo setcap 'cap_net_bind_service=+ep' /usr/sbin/nginx
$ sudo -u nginx /usr/sbin/nginx
```

systemd를 쓰면 유닛 파일에 `AmbientCapabilities=CAP_NET_BIND_SERVICE`를 쓰는 방식이 더 깔끔하다. 파일에 capability를 박지 않아도 실행 시점에 주입된다.

```ini
[Service]
User=nginx
ExecStart=/usr/sbin/nginx
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
```

`CapabilityBoundingSet`은 상한이다. 이 프로세스 트리에서 아무리 exec해도 이 집합을 벗어나는 capability는 못 얻는다. 보안 강화 용도로 필수다.

### file capabilities vs ambient capabilities

여기서 헷갈리기 쉬운 부분이다. capability를 "어디에 저장하느냐"에 따라 구분한다.

**File capability**는 파일의 xattr(`security.capability`)에 박힌다. setcap으로 박고, 해당 바이너리를 exec하면 자동으로 프로세스에 얹힌다. 단점은 파일을 복사하면 capability가 빠진다(cp는 xattr을 기본으로 복사 안 한다. `cp --preserve=all`이 필요). 패키지 업데이트로 바이너리가 교체되면 setcap을 다시 해야 한다.

**Ambient capability**는 프로세스에 직접 얹힌다. 부모 프로세스가 `prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_RAISE, ...)`로 설정하면, 그 프로세스가 exec할 때 자식에게 전달된다. file capability가 없는 바이너리도 ambient로 받을 수 있다. systemd의 `AmbientCapabilities`가 이 메커니즘이다.

셋째로 **inheritable**이 있는데, 이건 exec 시 permitted로 자동 승격되지 않는다. file capability에 설정된 inheritable과 프로세스의 inheritable이 AND 연산된다. 이름이 오해를 부르는데, 실제로는 "자동 상속"이 아니라 "상속 허용 후보"다. 대부분의 실무에서는 ambient로 대체해서 쓴다. 커널 4.3 이전에는 ambient가 없었기 때문에 inheritable을 쓸 수밖에 없었다.

### 프로세스의 capability 확인

실행 중인 프로세스의 capability를 보려면 `getpcaps`나 `/proc/<pid>/status`를 본다.

```bash
$ pgrep nginx
1234
$ getpcaps 1234
1234: cap_net_bind_service=ep

$ cat /proc/1234/status | grep Cap
CapInh: 0000000000000000
CapPrm: 0000000000000400
CapEff: 0000000000000400
CapBnd: 0000000000000400
CapAmb: 0000000000000000
```

`CapBnd`(bounding set)는 이 프로세스가 얻을 수 있는 최대 집합이다. `CapEff`는 현재 활성화된 집합. 16진 비트맵을 읽으려면 `capsh --decode=0x400` 하면 된다.

```bash
$ capsh --decode=0000000000000400
0x0000000000000400=cap_net_bind_service
```

### capability 디버깅 - 실전

"왜 안 되지?"를 추적할 때 순서가 있다. 첫째, 프로세스가 가진 capability를 본다. 둘째, bounding set이 막고 있는지 본다. 셋째, SELinux/AppArmor가 추가로 막는지 본다.

```bash
# 바이너리에 뭐가 붙어 있는지
$ getcap /usr/sbin/nginx

# 시스템 전체에서 capability 붙은 파일 찾기
$ sudo getcap -r / 2>/dev/null

# 프로세스 상태
$ getpcaps $(pgrep -f nginx)
$ grep ^Cap /proc/$(pgrep -f nginx)/status

# 컨테이너 내부에서
$ capsh --print
```

`capsh --print`는 현재 셸이 가진 capability를 사람이 읽을 수 있게 덤프한다. 컨테이너 안에서 뭐가 켜져 있는지 확인할 때 가장 빠르다.

## Extended Attributes (xattr, chattr)

### xattr의 개념

xattr은 파일에 붙는 임의의 key-value 메타데이터다. 네임스페이스가 네 개 있다.

- `user.*`: 일반 사용자가 쓸 수 있는 메타데이터
- `trusted.*`: root만 접근 가능
- `security.*`: SELinux 라벨, file capability가 여기 저장된다
- `system.*`: ACL이 여기 저장된다

file capability(`security.capability`)와 POSIX ACL(`system.posix_acl_access`, `system.posix_acl_default`)이 모두 xattr이라는 걸 이해하면 "백업/복원 시 권한이 왜 사라지냐" 같은 질문이 풀린다. tar는 기본으로 xattr을 포함하지 않는다. `tar --xattrs --xattrs-include='*'`가 필요하다. rsync도 `-X` 옵션이 필요하다.

```bash
# 파일의 xattr 보기
$ getfattr -d -m - /usr/sbin/nginx
# file: usr/sbin/nginx
security.capability=0sAQAAAgAQAAAAAAAAAAAAAAAAAAAAAAAA

# user 네임스페이스에 직접 저장
$ setfattr -n user.comment -v "deployed by kevin" myfile.txt
$ getfattr -n user.comment myfile.txt
```

ACL과 capability를 직접 손댈 일은 드물지만, 백업/배포 파이프라인에서 xattr 보존을 빼먹어서 사고 나는 경우는 흔하다.

### chattr과 파일 속성

`chattr`는 ext4/xfs 고유의 파일 속성을 설정한다. xattr와는 다른 메커니즘이다 — 파일시스템 고유의 플래그를 inode에 직접 박는다.

가장 많이 쓰는 속성 두 개:

**`+i` (immutable)**: 파일을 수정/삭제/이름변경/링크 불가로 만든다. root도 막힌다(단, `CAP_LINUX_IMMUTABLE`을 가진 프로세스만 설정/해제 가능하니 root가 해제 후 수정은 가능).

```bash
$ sudo chattr +i /etc/resolv.conf
$ lsattr /etc/resolv.conf
----i---------e------- /etc/resolv.conf

$ sudo rm /etc/resolv.conf
rm: cannot remove '/etc/resolv.conf': Operation not permitted

$ sudo chattr -i /etc/resolv.conf   # 해제
```

`/etc/resolv.conf`가 systemd-resolved나 NetworkManager로 자꾸 덮어쓰이는 걸 막을 때 흔히 쓴다. 다만 이게 걸려 있으면 package update가 실패한다. "설치가 되다가 중간에 Permission denied로 뻗는다"의 원인이 chattr +i인 경우가 종종 있다.

**`+a` (append-only)**: 쓰기는 append만 허용. 로그 파일에 쓴다.

```bash
$ sudo chattr +a /var/log/audit.log
$ echo "overwrite" > /var/log/audit.log    # 실패
-bash: /var/log/audit.log: Operation not permitted
$ echo "appended" >> /var/log/audit.log    # 성공
```

공격자가 침투해서 로그를 지우는 걸 막고 싶을 때 `+a`를 건다. 단, `CAP_LINUX_IMMUTABLE`을 탈취하면 해제 가능하니 만능은 아니다.

**`lsattr`**로 현재 속성을 본다. 사람이 읽을 수 있는 출력이 `------` 형태라 뭐가 뭔지 헷갈리는데, 자주 나오는 것만 기억해두면 된다:

- `i`: immutable
- `a`: append-only
- `A`: atime 업데이트 안 함
- `d`: dump 제외
- `e`: extent 사용 중 (ext4 기본, 무시)
- `c`: 압축
- `j`: 데이터 저널링

"파일을 못 지우겠다"고 할 때 `ls -l`에는 rwx가 멀쩡한데 `lsattr`에 `i`가 박혀 있는 경우가 꽤 있다. 권한 디버깅할 때 stat, getfacl, getcap, lsattr을 순서대로 확인하는 습관을 들이면 진단이 빨라진다.

## ACL, Capability 디버깅

### 한 파일에 뭐가 걸려 있는지 전부 보기

파일 하나에 대해 권한 관련 정보를 다 덤프하려면 네 개 명령을 조합한다.

```bash
$ stat /usr/sbin/nginx
$ getfacl /usr/sbin/nginx 2>/dev/null
$ getcap /usr/sbin/nginx
$ lsattr /usr/sbin/nginx
$ getfattr -d -m - /usr/sbin/nginx
```

stat은 모드, 소유자, atime/mtime/ctime을 본다. `ls -l`의 `+`가 있으면 getfacl을 본다. 실행 파일이면 getcap 반드시 확인. 설정 파일이면 lsattr. xattr 자체가 궁금하면 getfattr.

### 시스템 전체 audit

SetUID 바이너리 목록과 capability 붙은 바이너리 목록은 침해 분석의 기본이다.

```bash
# SetUID 바이너리 전수
$ sudo find / -xdev -type f -perm -4000 2>/dev/null

# SetGID 바이너리 전수
$ sudo find / -xdev -type f -perm -2000 2>/dev/null

# Capability 붙은 바이너리 전수
$ sudo getcap -r / 2>/dev/null

# immutable 속성이 걸린 파일 (ext4/xfs만)
$ sudo lsattr -R / 2>/dev/null | grep '^....i'

# 최근 변경된 SetUID 파일 (공격 후 뒷문 탐지)
$ sudo find / -xdev -type f -perm -4000 -newer /tmp/reference 2>/dev/null
```

`-xdev`는 다른 파일시스템으로 내려가지 않게 막는다. `/proc`, `/sys`, 네트워크 마운트로 내려가면 오래 걸리거나 뻗는다. `-newer /tmp/reference`는 기준 파일의 mtime보다 새로운 파일만 필터링한다. "지난주 설치 이후 추가된 SetUID 파일이 있는가"를 볼 때 쓴다.

### 운영 중 문제 진단 순서

권한 에러가 났을 때 내가 실무에서 쓰는 순서가 있다.

1. `strace -e openat,read,write <cmd>`로 어떤 파일에서 EACCES/EPERM이 터지는지 확인
2. 그 파일에 `ls -l`, `stat` — 기본 권한 OK?
3. `ls -l`에 `+`가 있으면 `getfacl` — ACL mask 확인
4. 실행 에러면 `getcap` — capability 누락 확인
5. 수정 에러인데 권한은 멀쩡하면 `lsattr` — immutable 확인
6. 컨테이너면 `capsh --print` + seccomp/AppArmor 프로파일 확인
7. 그래도 안 풀리면 `/var/log/audit/audit.log` (SELinux) 또는 `dmesg | grep apparmor`

EACCES는 "권한 부족", EPERM은 "권한 자체가 없다"는 뜻이다. strace에서 이 두 에러 코드를 구분해서 보면 원인 좁히기 쉽다.

## 컨테이너 환경에서의 Capability

### Docker의 기본 capability set

Docker 컨테이너는 기본으로 14개의 capability만 남기고 나머지를 drop한다. 허용된 것들:

```
CAP_CHOWN, CAP_DAC_OVERRIDE, CAP_FSETID, CAP_FOWNER,
CAP_MKNOD, CAP_NET_RAW, CAP_SETGID, CAP_SETUID,
CAP_SETFCAP, CAP_SETPCAP, CAP_NET_BIND_SERVICE,
CAP_SYS_CHROOT, CAP_KILL, CAP_AUDIT_WRITE
```

여기서 빠진 대표적인 것들: `CAP_SYS_ADMIN`, `CAP_SYS_PTRACE`, `CAP_NET_ADMIN`, `CAP_SYS_MODULE`, `CAP_SYS_TIME`. 그래서 컨테이너 안에서 mount, iptables, strace(다른 프로세스), date 명령으로 시스템 시간 변경 등이 안 된다.

```bash
# 현재 컨테이너의 capability 보기
$ docker run --rm alpine sh -c 'apk add -q libcap && capsh --print'
Current: cap_chown,cap_dac_override,cap_fowner,cap_fsetid,cap_kill,
cap_setgid,cap_setuid,cap_setpcap,cap_net_bind_service,cap_net_raw,
cap_sys_chroot,cap_mknod,cap_audit_write,cap_setfcap=ep
```

### --cap-add, --cap-drop

필요한 capability만 추가하거나 빼는 방식이 권장된다.

```bash
# 네트워크 관리 툴이 필요한 컨테이너
$ docker run --cap-add=NET_ADMIN --rm alpine ip addr add 10.0.0.1/24 dev eth0

# tcpdump를 위한 최소 권한
$ docker run --cap-add=NET_RAW --cap-add=NET_ADMIN --rm alpine tcpdump

# 모든 기본 capability 제거 후 필요한 것만 추가
$ docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE nginx
```

`--cap-drop=ALL --cap-add=<필요한 것>` 패턴을 쓰는 게 보안 기준이다. `--cap-drop=ALL`만 걸면 chown도 안 되고 setuid도 안 되니까, 컨테이너 내부에서 USER 지시어로 이미 non-root로 떨어졌다면 대부분 문제없다. nginx 공식 이미지처럼 entrypoint에서 내려가는 구조면 SETUID/SETGID는 남겨둬야 한다.

### --privileged와 --cap-add=SYS_ADMIN

두 개가 같은 줄 알고 혼용하는데 다르다. `--privileged`는 모든 capability를 켜고, device cgroup 제약을 풀고, AppArmor/SELinux 프로파일을 unconfined로 바꾸고, seccomp 필터도 해제한다. 호스트와 거의 같은 수준이다.

`--cap-add=SYS_ADMIN`은 그 중 capability 한 개만 추가한다. seccomp 필터는 그대로 유지된다. mount 같은 걸 하려면 SYS_ADMIN만으로 충분한 경우가 대부분이다. `--privileged`는 "임시 디버깅용"이다. 프로덕션에 절대 남기면 안 된다.

### Kubernetes securityContext

k8s는 같은 개념을 Pod/Container spec의 securityContext로 노출한다.

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  capabilities:
    drop:
      - ALL
    add:
      - NET_BIND_SERVICE
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
```

`allowPrivilegeEscalation: false`는 프로세스가 exec 시 capability를 더 얻을 수 없게 막는다. 커널의 `no_new_privs` 비트를 세팅하는 것과 같다. SetUID 바이너리가 컨테이너 내부에 있어도 권한 상승이 안 된다. 이게 켜져 있으면 `sudo`도 의미가 없다.

`readOnlyRootFilesystem`은 capability는 아니지만 세트로 쓴다. 루트 파일시스템이 읽기 전용이면 공격자가 바이너리를 쓸 곳이 없다. /tmp, /var/run 같은 쓰기 필요한 곳만 emptyDir로 마운트한다.

### rootless 컨테이너의 권한

Podman의 rootless 모드, Docker의 rootless 모드는 호스트의 일반 사용자 권한으로 컨테이너를 띄운다. 이때 컨테이너 내부의 root(uid 0)는 호스트의 어떤 uid에 매핑된다. 매핑은 `/etc/subuid`, `/etc/subgid`로 설정한다.

```
alice:100000:65536
```

alice가 띄운 컨테이너 안의 uid 0은 호스트의 uid 100000이다. 컨테이너에서 아무리 root라도 호스트의 alice 권한을 넘을 수 없다. 1024 미만 포트 바인딩이 기본으로 안 되는데, 이건 호스트에서 alice가 일반 사용자이기 때문이다. 해결은 `sysctl net.ipv4.ip_unprivileged_port_start=80`처럼 커널이 허용하는 비특권 포트 하한을 낮추는 것이다.

rootless 환경에서는 file capability도 제한이 있다. `security.capability` xattr을 쓰려면 user 네임스페이스 안에서 유효한 capability로 변환돼야 하는데, 커널 4.14 이후의 namespaced file capability가 필요하다. 구버전에서는 setcap이 컨테이너 내부에서 실패하거나 무시된다.

## 실무 정리

rwx 9비트 바깥 세계는 복잡해 보이지만 실제로 기억할 건 몇 개 안 된다.

ACL은 mask에서 막히고 chmod로 또 망가진다. `+` 기호 보이면 getfacl부터. 공유 디렉토리는 SetGID + default ACL + umask 002 세트. Special permission은 스크립트에 안 먹고, 요즘은 capability로 대체되는 추세. SetUID 파일은 공격 표면이니 주기적으로 감사한다.

Capability는 root를 40조각으로 쪼갠 것. nginx/ping에 붙어 있는 게 전형적. file capability와 ambient capability는 "어디 저장하냐"의 차이고, `CAP_SYS_ADMIN`은 사실상 root니까 컨테이너에선 빼는 게 기본.

chattr +i는 rm도 막는다. 권한 멀쩡한데 삭제/수정 안 되면 lsattr 확인. tar/rsync/cp에서 xattr 보존 옵션 까먹으면 capability와 ACL이 증발한다.

컨테이너는 기본으로 capability가 drop된 상태. 필요한 것만 add. privileged는 디버깅용. k8s에서는 securityContext에 `drop: ALL`, `allowPrivilegeEscalation: false`가 시작점.

권한 문제 디버깅 순서: strace → stat → getfacl → getcap → lsattr → (컨테이너면) capsh → (보안 모듈) audit.log/dmesg.
