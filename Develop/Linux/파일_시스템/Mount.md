---
title: Mount
tags: [linux, mount, umount, fstab, bind-mount, tmpfs, nfs, namespace, autofs, troubleshooting]
updated: 2026-05-15
---

# Mount

## 개요

리눅스의 모든 파일 시스템은 어딘가에 "붙어야" 보인다. 디스크에 ext4가 만들어져 있어도, 마운트가 안 되어 있으면 그 파일 시스템 안의 데이터에 접근할 수 없다. 마운트는 블록 디바이스(혹은 가상 디바이스)의 파일 시스템을 특정 디렉토리 경로에 부착해, 그 디렉토리 아래에서 해당 파일 시스템의 파일 트리를 탐색하게 만드는 작업이다.

운영 환경에서 마운트 관련 문제는 자잘하게 끊임없이 발생한다. 부팅 중에 fstab 한 줄을 잘못 적어서 서버가 emergency mode로 떨어진다거나, umount가 device is busy를 뱉으며 안 풀린다거나, 컨테이너 안에서 호스트 볼륨 변경이 안 보인다거나, NFS 서버가 죽어서 모든 프로세스가 D state로 멈춘다거나. 이런 상황을 빠르게 풀려면 `mount` 명령의 옵션 카탈로그만 외울 게 아니라 커널이 마운트를 어떻게 관리하는지, 그리고 마운트 네임스페이스라는 개념이 어디서 끼어드는지를 알아야 한다.

이 문서는 마운트가 무엇인지부터 시작해 fstab 작성, 바인드/루프/tmpfs/NFS 같은 특수 마운트, 마운트 네임스페이스와 전파 타입, 그리고 실제로 자주 마주치는 트러블슈팅 시나리오를 다룬다. 디스크 관리나 파일 시스템 자체에 대한 내용은 별도 문서에서 다루므로, 여기서는 "마운트"라는 행위 자체에 집중한다.

## 마운트 포인트 관례: /mnt와 /media

리눅스 표준에서 `/mnt`와 `/media`는 둘 다 외부 파일 시스템을 붙이는 자리지만 의도가 다르다. FHS(Filesystem Hierarchy Standard) 기준으로 보면 이렇다.

- `/mnt`: 시스템 관리자가 일시적으로 수동 마운트할 때 쓰는 자리. NFS 서버를 잠깐 붙여서 데이터를 옮기거나, 외장 디스크를 한 번 확인하려고 마운트할 때 쓴다.
- `/media`: 자동 마운트되는 이동식 미디어가 붙는 자리. udisks나 데스크톱 환경이 USB 메모리, CD/DVD, 외장 드라이브를 감지하면 `/media/<user>/<label>` 같은 경로에 자동으로 마운트한다.

서버 환경에서는 거의 `/mnt` 쪽만 쓰게 된다. `/media`는 데스크톱 의미가 강하다. 서비스 영구 데이터를 둘 거면 `/mnt`도 적절하지 않다. 보통 `/data`, `/var/lib/<service>`, `/srv` 같은 별도 경로를 만들어 fstab에 등록한다. `/mnt`에 운영 데이터를 두면 다른 운영자가 "임시 마운트 자리겠지" 하고 umount해 버리는 사고가 난다. 관례를 깨는 비용이 생각보다 크다.

## mount/umount 명령

가장 기본 형태는 `mount <device> <mountpoint>`다. fstab에 등록된 항목은 `mount <mountpoint>` 또는 `mount <device>` 하나만 적어도 자동으로 옵션을 끌어다 쓴다.

```bash
# 디바이스를 마운트 포인트에 붙임
mount /dev/sdb1 /mnt/data

# 파일 시스템 타입을 명시 (대부분 자동 감지되지만 명시가 안전)
mount -t ext4 /dev/sdb1 /mnt/data

# 옵션 지정
mount -t ext4 -o ro,noatime /dev/sdb1 /mnt/data

# fstab에 등록된 모든 항목 마운트 (보통 부팅 시 systemd가 수행)
mount -a

# fstab 항목을 마운트 포인트만으로 마운트
mount /mnt/data

# 이미 마운트된 것을 옵션만 바꿔서 다시 마운트 (remount)
mount -o remount,ro /mnt/data
```

`mount`를 인자 없이 실행하면 현재 마운트된 모든 파일 시스템 목록이 나오는데, 출력이 길고 보기 좋지 않다. 실무에서는 `findmnt`를 쓰는 쪽이 훨씬 낫다. 뒤에서 다룬다.

umount는 떼어내는 명령이다.

```bash
umount /mnt/data           # 마운트 포인트 지정
umount /dev/sdb1           # 디바이스 지정
umount -l /mnt/data        # lazy unmount (사용 중이어도 일단 분리)
umount -f /mnt/data        # 강제 (주로 NFS hung 상태에서 사용)
```

umount가 자주 실패하는 이유는 누군가 그 안에서 파일을 열고 있거나, 그 디렉토리를 cwd로 쓰고 있기 때문이다. 이 처리는 트러블슈팅 절에서 다룬다.

## mount(2) 시스템 콜과 커널 동작

`mount` 명령은 내부적으로 `mount(2)` 시스템 콜을 호출한다. 시그니처는 이렇다.

```c
int mount(const char *source, const char *target,
          const char *filesystemtype, unsigned long mountflags,
          const void *data);
```

source는 디바이스 경로(혹은 NFS면 `server:/path`, tmpfs면 무시), target은 마운트 포인트, filesystemtype은 `"ext4"`, `"xfs"`, `"tmpfs"`, `"nfs"` 같은 문자열, mountflags는 비트 플래그(`MS_RDONLY`, `MS_NOEXEC`, `MS_BIND` 등), data는 파일 시스템별 추가 옵션 문자열이다.

커널이 이 호출을 받으면 다음 절차를 거친다.

1. `target` 경로를 path lookup해서 대상 디렉토리의 dentry를 찾는다. 디렉토리가 없으면 `ENOENT`로 실패한다.
2. `filesystemtype`에 해당하는 파일 시스템 모듈이 등록되어 있는지 확인한다. 없으면 모듈 로드를 시도하고, 그래도 없으면 `ENODEV`.
3. 해당 파일 시스템의 `mount` 콜백(예: `ext4_mount`)을 호출해 `super_block`을 생성한다. 디스크 슈퍼블록을 읽고, 저널을 리플레이하고, 루트 inode를 가져오는 작업이 여기서 일어난다.
4. 새 슈퍼블록의 루트 dentry를 `target` dentry 위에 덮어씌운다. 이때부터 `target` 경로 아래로 들어가면 원래 디렉토리가 아니라 새 파일 시스템의 루트가 보인다.

핵심은 4번이다. 마운트는 "디렉토리 내용을 갈아 끼우는" 행위가 아니라, "그 dentry를 덮어쓰는" 행위다. 그래서 마운트 포인트 디렉토리 안에 원래 파일이 있어도, 마운트되어 있는 동안에는 그 파일이 보이지 않는다. umount하면 다시 보인다. 마운트 위에 또 마운트할 수도 있고(레이어처럼 쌓임), 가장 위의 마운트가 보인다. 이게 마운트 네임스페이스와 컨테이너 동작을 이해할 때 기초가 된다.

리눅스 5.2부터는 `fsopen`, `fsconfig`, `fsmount`, `move_mount` 같은 새 시스템 콜이 추가되어 마운트 작업을 단계별로 쪼개서 처리할 수 있다. systemd나 컨테이너 런타임에서 점점 활용하는 추세지만, 사용자 입장에서는 여전히 `mount(2)` 한 방으로 대부분 처리한다.

## /etc/fstab

fstab은 부팅 시 자동 마운트할 파일 시스템을 적어두는 파일이다. systemd가 부팅 과정에서 `systemd-fstab-generator`를 통해 fstab을 읽고, 각 항목을 `.mount` 유닛으로 변환해 처리한다.

기본 형태는 6개 필드다.

```
<device>  <mountpoint>  <fstype>  <options>  <dump>  <pass>
```

```
# 예시
UUID=a1b2c3d4-e5f6-...  /         ext4   defaults,noatime         0 1
UUID=b2c3d4e5-f6a7-...  /home     ext4   defaults,noatime         0 2
UUID=c3d4e5f6-a7b8-...  none      swap   sw                       0 0
tmpfs                   /tmp      tmpfs  defaults,nosuid,nodev,size=2G  0 0
//fileserver/share      /mnt/smb  cifs   credentials=/etc/smb-cred,_netdev  0 0
nfs-srv:/exports/data   /mnt/nfs  nfs    rw,hard,intr,_netdev     0 0
```

- device: 보통 UUID를 쓴다. `/dev/sdb1` 같은 이름은 디스크 추가/제거에 따라 바뀌므로 위험하다. `blkid` 명령으로 UUID를 확인한다.
- mountpoint: 디렉토리 경로. 없으면 미리 만들어둬야 한다.
- fstype: `ext4`, `xfs`, `btrfs`, `tmpfs`, `nfs`, `cifs`, `auto`(자동 감지) 등.
- options: 콤마로 구분된 마운트 옵션. 아래에서 자세히.
- dump: `dump` 명령(거의 안 씀)에서 백업 대상 표시. 보통 0.
- pass: 부팅 시 `fsck` 순서. 루트는 1, 다른 로컬 파일 시스템은 2, 검사 안 함은 0. 네트워크/tmpfs는 0.

fstab을 고친 직후엔 반드시 `mount -a`로 검증한다. 재부팅을 했다가 항목이 잘못되어 있으면 부팅이 안 되는데, 그땐 emergency mode에서 복구해야 한다.

### 주요 마운트 옵션

| 옵션 | 의미 |
|---|---|
| `defaults` | `rw,suid,dev,exec,auto,nouser,async`의 묶음. 별다른 요구가 없으면 출발점. |
| `ro` / `rw` | 읽기 전용 / 읽기-쓰기. |
| `noatime` | 파일 읽을 때마다 atime을 갱신하지 않음. 디스크 I/O가 크게 줄어든다. 서버에서는 거의 기본값처럼 쓴다. |
| `nodiratime` | 디렉토리 atime만 갱신 안 함. `noatime`이 더 강력해서 보통은 `noatime`만 쓴다. |
| `relatime` | atime을 mtime/ctime보다 오래된 경우에만 갱신. 최신 커널 기본값. `noatime`이 더 빠르다. |
| `sync` | 모든 쓰기를 동기로. 안전하지만 느리다. |
| `async` | 비동기 쓰기. 기본값. 페이지 캐시를 거쳐 나중에 디스크에 반영. |
| `noexec` | 이 파일 시스템 안의 바이너리 실행 금지. `/tmp`나 업로드 디렉토리에 단다. |
| `nosuid` | setuid/setgid 비트 무시. 사용자 데이터 파일 시스템에 단다. |
| `nodev` | 디바이스 파일 무시. `/tmp`, `/home` 같은 곳에 단다. |
| `_netdev` | 네트워크가 올라온 뒤에 마운트. NFS/CIFS에 필수. |
| `x-systemd.automount` | 부팅 시 즉시 마운트하지 않고, 처음 접근될 때 자동 마운트. NFS hang 같은 부팅 지연을 피할 때 쓴다. |
| `x-systemd.device-timeout=10` | systemd가 디바이스 대기할 시간. 외장 디스크가 없을 때 부팅 지연 줄이기. |
| `nofail` | 마운트 실패해도 부팅 계속. 외장 디스크 entry에 단다. |

`noatime`은 한 번쯤 짚어둘 가치가 있다. 리눅스 기본은 `relatime`인데, 파일을 읽기만 해도 일정 조건에서 atime을 갱신한다. 즉 읽기 작업이 쓰기 I/O를 발생시킨다. 로그를 많이 읽거나 정적 파일을 자주 서빙하는 서버에서는 `noatime`을 켜면 디스크 부하가 눈에 띄게 떨어진다. atime이 필요한 워크로드는 거의 없으므로(메일 서버 일부 정도) 기본 옵션으로 깔아두는 편이 낫다.

`noexec`, `nosuid`, `nodev`는 보안 옵션의 묶음이다. `/tmp`에 누가 악성 바이너리를 던져두고 실행하는 시나리오를 막는다. `/tmp`, `/var/tmp`, `/dev/shm`, 사용자 업로드 디렉토리에는 거의 항상 켜둔다.

## 바인드 마운트

바인드 마운트는 디스크의 한 디렉토리를 다른 경로에 또 보이게 만드는 기능이다. 새 파일 시스템을 마운트하는 게 아니라, 기존 마운트의 일부를 다른 위치에 연결한다.

```bash
mount --bind /data/uploads /var/www/uploads
mount --rbind /data /chroot/data        # 하위 마운트까지 같이
```

`--bind`는 그 디렉토리 자체만 옮긴다. 만약 `/data` 아래에 다른 파일 시스템이 마운트되어 있으면 그 마운트는 따라가지 않는다. `--rbind`(recursive bind)는 하위 마운트까지 같이 끌고 간다. chroot나 컨테이너 환경에서 호스트 디렉토리 트리를 통째로 넘겨줄 때 `--rbind`를 쓴다.

바인드 마운트가 실제로 쓰이는 곳:

- chroot 환경 구성: `/proc`, `/sys`, `/dev`를 chroot 안으로 바인드 마운트.
- 컨테이너 볼륨: 도커가 `-v /host/path:/container/path`로 볼륨을 마운트할 때 내부적으로 바인드 마운트를 쓴다.
- 디렉토리 재배치: 디스크 공간이 부족한데 애플리케이션이 특정 경로를 박아둔 경우, 데이터를 다른 디스크로 옮긴 뒤 바인드 마운트로 원래 경로에 연결한다.
- 권한 분리: 같은 데이터를 한쪽은 ro로, 한쪽은 rw로 보이게 할 때.

바인드 마운트는 원본과 같은 파일 시스템 옵션을 따른다. ro로 마운트하고 싶으면 두 번에 나눠 해야 한다.

```bash
mount --bind /data /mnt/data-ro
mount -o remount,bind,ro /mnt/data-ro
```

한 번에 `mount --bind -o ro` 식으로 적어도 기대대로 안 되는 경우가 많아서 두 단계가 안전하다.

## 루프 디바이스 마운트

ISO 파일이나 디스크 이미지를 파일 시스템처럼 마운트하려면 루프 디바이스(loop device)를 거친다. 루프 디바이스는 일반 파일을 블록 디바이스인 척 보이게 해주는 가상 디바이스다.

```bash
# ISO 마운트
mount -o loop ubuntu-22.04.iso /mnt/iso

# 이미지 파일을 만들어 ext4로 포맷한 뒤 마운트
dd if=/dev/zero of=/tmp/disk.img bs=1M count=100
mkfs.ext4 /tmp/disk.img
mount -o loop /tmp/disk.img /mnt/loopback
```

`mount -o loop`만 적으면 커널이 자동으로 빈 `/dev/loopN`을 잡아 연결한다. `losetup`으로 명시적으로 잡고 싶으면 이렇게 한다.

```bash
losetup -f                          # 빈 loop 번호 확인
losetup /dev/loop0 /tmp/disk.img
mount /dev/loop0 /mnt/loopback
# 작업 후
umount /mnt/loopback
losetup -d /dev/loop0
```

이미지 파일이 파티션 테이블을 포함한 경우(즉 raw 디스크 이미지)에는 `losetup -P`로 파티션을 자동 인식하게 해야 한다.

```bash
losetup -fP --show disk.raw         # /dev/loop0 출력
# /dev/loop0p1, /dev/loop0p2 같은 파티션 디바이스가 생긴다
mount /dev/loop0p1 /mnt/part1
```

VM 이미지 디버깅이나 백업 이미지 안 들여다볼 때 자주 쓰는 패턴이다.

## tmpfs 마운트

tmpfs는 메모리 위에 만드는 파일 시스템이다. RAM과 스왑을 backing storage로 쓰며, 재부팅하면 내용이 전부 사라진다. `/tmp`, `/run`, `/dev/shm`이 대표적으로 tmpfs로 마운트되어 있다.

```bash
mount -t tmpfs -o size=1G,nosuid,nodev,noexec tmpfs /mnt/ram
```

fstab으로 영구화하려면

```
tmpfs  /mnt/ram  tmpfs  size=1G,nosuid,nodev,noexec  0 0
```

tmpfs는 "RAM에 박힌다"는 오해가 있는데, 실제로는 페이지 캐시처럼 동작한다. 사용 안 하는 페이지는 스왑으로 빠질 수 있고, 사용량만큼만 메모리를 차지한다. `size=1G`로 잡아도 실제로 50MB만 쓰면 50MB만 점유한다.

서비스 워크로드에서 임시 작업 영역, 빠른 IPC, 컨테이너 안의 `/tmp` 같은 곳에 자주 쓴다. 단, 데이터 영속성이 필요한 곳에는 절대 쓰면 안 된다(재부팅 사라짐, 메모리 부족 시 OOM 발생 위험).

## NFS/SMB 원격 마운트와 _netdev

원격 파일 시스템 마운트는 네트워크 의존성 때문에 로컬 마운트와 운영 특성이 많이 다르다.

NFS 마운트는 이렇게 적는다.

```bash
mount -t nfs -o rw,hard,intr,_netdev nfs-srv:/exports/data /mnt/nfs
```

```
# fstab
nfs-srv:/exports/data  /mnt/nfs  nfs  rw,hard,intr,_netdev,vers=4  0 0
```

핵심 옵션:

- `hard` vs `soft`: NFS 서버가 응답이 없을 때 동작. `hard`는 무한 재시도(프로세스가 D state로 멈춤), `soft`는 일정 횟수 후 I/O 에러 반환. 데이터 무결성이 중요하면 `hard`, 죽지 않는 게 더 중요하면 `soft`. 보통 `hard`.
- `intr`: `hard` 마운트 상태에서 시그널로 중단 가능(최근 커널에선 거의 무시됨, 형식적으로 적음).
- `bg`: 백그라운드로 마운트 재시도. 부팅 시 NFS 서버가 늦게 올라와도 부팅이 멈추지 않게 한다.
- `_netdev`: 네트워크 인터페이스가 올라온 뒤에 마운트하라고 systemd에 알리는 옵션. 안 적으면 부팅이 멈춘다.
- `vers=4`: NFS 프로토콜 버전. v3는 stateless, v4는 stateful + 락 + ACL 통합.

SMB/CIFS(Windows 공유 마운트)는 이렇게 적는다.

```
//fileserver/share  /mnt/smb  cifs  credentials=/etc/smb-cred,_netdev,uid=1000,gid=1000  0 0
```

`credentials` 파일에는 `username=`, `password=`, `domain=`을 적어두고 파일 권한을 `chmod 600`으로 잠근다. fstab에 평문으로 적지 않는다.

원격 마운트의 가장 큰 운영 이슈는 서버가 다운됐을 때 클라이언트 프로세스가 hang 걸리는 현상이다. `hard` 마운트는 `df` 같은 명령조차 응답을 못 받고 멈춘다. 이때는 `umount -f -l` 조합으로 강제로 떼어내야 한다. 부팅 시 NFS 서버가 안 떠 있어서 부팅이 멈추는 사고도 흔하다. `_netdev`와 `nofail`, 그리고 가능하면 `x-systemd.automount`까지 같이 적어서 처음 접근될 때만 마운트되게 만드는 쪽이 안전하다.

## 마운트 네임스페이스와 전파 타입

리눅스 마운트는 네임스페이스 단위로 격리된다. 마운트 네임스페이스(mount namespace)는 프로세스가 보는 마운트 테이블을 따로 분리해주는 커널 기능이다. 컨테이너가 호스트와 다른 파일 시스템 트리를 보는 것도, chroot보다 훨씬 강력한 이 격리 덕분이다.

```bash
# 새 마운트 네임스페이스를 만들어 그 안에서 셸 실행
unshare -m bash

# 이 셸 안에서 마운트하면 호스트에선 안 보임
mount -t tmpfs none /mnt/tmpfs
ls /mnt/tmpfs              # 보임

# 다른 터미널에서
ls /mnt/tmpfs              # 안 보임
```

여기서 헷갈리는 게 "전파(propagation)" 개념이다. 부모 네임스페이스에서 새 마운트를 추가하면, 그게 자식 네임스페이스에도 보일까? 자식에서 마운트를 추가하면 부모로 전파될까? 이건 마운트의 전파 타입(propagation type)에 따라 다르다.

전파 타입은 마운트마다 따로 설정되며, 종류는 네 가지다.

| 타입 | 동작 |
|---|---|
| `shared` | 양방향. 부모/자식 어느 쪽에서 마운트해도 서로 보임. |
| `private` | 격리. 어느 쪽 변경도 다른 쪽에 안 보임. |
| `slave` | 단방향. 부모 → 자식 전파만 받음. 자식에서 한 마운트는 부모에 안 감. |
| `unbindable` | 바인드 마운트 자체가 안 됨. |

전파 타입을 바꾸는 명령은 이렇다.

```bash
mount --make-shared /mnt/data
mount --make-private /mnt/data
mount --make-slave /mnt/data
mount --make-rshared /        # 재귀적으로 적용
```

systemd는 부팅 시 루트(`/`)를 `shared`로 만들어둔다. 그래서 호스트에서 새 디스크를 마운트하면 모든 컨테이너가 자동으로 그걸 볼 수 있다(컨테이너 측 마운트가 shared인 경우). 도커는 일반적으로 `/`를 `slave`나 `private`로 다시 설정해 컨테이너 내부 마운트가 호스트로 새지 않게 한다.

이 동작을 모르면 디버깅이 어려운 사례가 있다. 컨테이너에서 NFS를 마운트했는데 호스트에선 `findmnt`로 안 보인다거나, 호스트에서 디스크를 갈아 끼웠는데 일부 컨테이너만 갱신이 안 된다거나. `cat /proc/self/mountinfo`에 보면 각 마운트의 전파 타입(`shared:N`, `master:N` 같은 표시)이 나오므로 그걸 보고 원인을 추적한다.

## mountpoint 명령

특정 경로가 마운트 포인트인지 확인할 때 쓴다. 스크립트에서 자주 쓴다.

```bash
mountpoint /mnt/data
# /mnt/data is a mountpoint   (반환값 0)

mountpoint /tmp/random
# /tmp/random is not a mountpoint   (반환값 1)

# 스크립트에서
if mountpoint -q /mnt/data; then
  echo "이미 마운트됨"
else
  mount /mnt/data
fi
```

backup 스크립트나 init 스크립트에서 "마운트가 안 되어 있는데 백업 시작" 같은 사고를 막을 때 유용하다. `mountpoint -q`로 조용히 검사하고 결과를 분기하는 패턴이 자주 쓰인다.

## /proc/mounts와 /proc/self/mountinfo 차이

마운트 정보를 보는 파일이 여러 개 있는데, 차이를 알아야 한다.

- `/etc/mtab`: 옛날 방식. 사용자 공간에서 mount 명령이 직접 갱신하던 파일. 요즘은 `/proc/self/mounts`의 심볼릭 링크인 경우가 많다.
- `/proc/mounts`: 커널이 보여주는 마운트 목록. 마운트 시점에 자동 갱신. 형식은 fstab과 비슷한 6필드.
- `/proc/self/mountinfo`: 커널이 보여주는 더 자세한 마운트 정보. 마운트 ID, 부모 ID, 전파 타입, 마운트 옵션, 슈퍼블록 옵션 등이 모두 들어 있다.

```
# /proc/self/mountinfo 한 줄 예시
36 35 8:1 / / rw,relatime shared:1 - ext4 /dev/sda1 rw,errors=remount-ro
```

필드 의미: 마운트 ID, 부모 마운트 ID, major:minor, 마운트 source의 root, 마운트 포인트, 마운트 옵션, 옵션 필드들(전파 타입 포함), `-` 구분자, 파일 시스템 타입, source, 슈퍼블록 옵션.

전파 타입(`shared:1`)이나 부모 관계가 필요한 디버깅에는 `/proc/self/mountinfo`를 봐야 한다. `/proc/mounts`로는 부족하다. 컨테이너 안에서 보면 컨테이너의 마운트 네임스페이스 기준으로 출력되므로, 호스트와 다르게 보일 수 있다.

## findmnt

`mount` 명령의 출력이나 `/proc/mounts`를 직접 보는 것보다 `findmnt`가 훨씬 보기 좋다.

```bash
findmnt                            # 트리 형태로 전체 출력
findmnt /mnt/data                  # 특정 경로
findmnt -t ext4                    # 타입으로 필터
findmnt -n -o SOURCE /mnt/data     # 디바이스만 출력 (스크립트용)
findmnt --verify                   # fstab 항목 사전 검증 (부팅 전 체크)
findmnt --poll /mnt/data           # 마운트 변경 이벤트 모니터링
```

`findmnt --verify`는 fstab을 고친 뒤에 부팅 전에 한 번 돌려봐야 하는 명령이다. UUID가 없는 디바이스를 가리키거나, 마운트 포인트 디렉토리가 없거나, 옵션 문법이 잘못되어 있으면 잡아준다. 이걸 안 하고 재부팅했다가 emergency mode로 떨어진 사람이 많다.

## autofs와 systemd automount

자주 안 쓰는 마운트를 부팅 시 다 붙여두는 건 낭비다. 특히 NFS 서버가 여러 개거나 외장 디스크가 가끔 붙는 환경에서는 "필요할 때만 자동 마운트"되는 게 낫다. 이걸 해주는 게 autofs와 systemd automount다.

전통적으로는 autofs 패키지를 썼다. `/etc/auto.master`와 맵 파일을 만들어 데몬이 마운트 요청을 가로채는 방식이다.

```
# /etc/auto.master
/mnt/nfs  /etc/auto.nfs  --timeout=60
```

```
# /etc/auto.nfs
data  -rw,hard  nfs-srv:/exports/data
```

이렇게 해두면 `/mnt/nfs/data`에 처음 접근할 때 자동 마운트되고, 60초 안 쓰면 자동 umount된다.

요즘은 systemd가 같은 기능을 제공한다. fstab에 `x-systemd.automount`만 적으면 된다.

```
nfs-srv:/exports/data  /mnt/nfs  nfs  rw,hard,_netdev,x-systemd.automount,x-systemd.idle-timeout=60  0 0
```

systemd automount는 별도 데몬이 필요 없고 fstab 한 줄로 끝나서 신규 환경에서는 거의 systemd 쪽으로 통일된다. autofs는 레거시 환경이나 NIS/LDAP 기반 동적 맵을 쓰는 환경에서만 유지된다.

## 트러블슈팅

### umount: target is busy

가장 자주 보는 에러다. 누군가 그 디렉토리 안에서 파일을 열고 있거나 cwd로 쓰고 있다는 뜻이다.

```bash
umount /mnt/data
# umount: /mnt/data: target is busy.
```

원인을 찾는 도구는 `lsof`와 `fuser`다.

```bash
lsof +D /mnt/data                  # 그 디렉토리 안에서 열린 파일 전부
lsof /mnt/data                     # 마운트 포인트 자체

fuser -mv /mnt/data                # 그 마운트를 쓰는 프로세스 PID + 사용자
fuser -km /mnt/data                # 그 프로세스들을 모두 KILL (위험)
```

`lsof +D`는 디렉토리 안을 재귀적으로 뒤지므로 큰 디렉토리에선 느리다. `fuser -m`이 더 빠르다.

찾은 프로세스를 정상적으로 종료시키고 다시 umount하는 게 정공법이다. 못 죽이거나 시간이 없을 때는 lazy unmount를 쓴다.

```bash
umount -l /mnt/data
```

`-l`(lazy)은 마운트를 파일 시스템 트리에서 즉시 분리하지만, 그 마운트를 쓰는 기존 프로세스의 파일 핸들은 살려둔다. 그래서 `df`나 `ls`에서는 사라지지만, 백그라운드에서 그 파일을 쓰던 프로세스는 계속 쓴다. 그 프로세스가 끝나야 진짜 마운트가 해제된다. NFS hang 같은 상황에서 일단 시스템을 풀어주려고 자주 쓰지만, "마운트 됐는지 안 됐는지" 상태가 애매해지므로 디버깅이 어려워질 수 있다.

`-f`(force)는 NFS 같은 원격 파일 시스템에서 서버가 응답을 안 할 때 쓴다. 로컬 파일 시스템에는 거의 효과가 없다.

### 디스크가 떨어진 상황

물리 디스크 또는 USB 외장 디스크가 갑자기 빠지면 마운트는 "유령" 상태로 남는다. 디바이스는 사라졌지만 마운트 테이블에는 항목이 있고, 그 마운트에 접근하는 프로세스는 I/O 에러를 받거나 D state로 멈춘다.

```bash
ls /mnt/usb
# ls: cannot access '/mnt/usb': Input/output error

dmesg | tail
# [12345.678] sd 0:0:0:1: rejecting I/O to offline device
```

이 상태에서 정상적인 `umount`는 보통 실패한다.

```bash
umount /mnt/usb
# umount: /mnt/usb: target is busy
```

처리는 이렇다.

```bash
fuser -mv /mnt/usb                 # 남은 프로세스 확인
fuser -km /mnt/usb                 # 강제 종료가 필요하면
umount -l /mnt/usb                 # lazy umount
```

이렇게 풀고 나면 `findmnt`에서 그 항목이 사라진다. 디스크를 다시 꽂으면 보통 다른 디바이스 이름(`/dev/sdc` 대신 `/dev/sdd`)으로 잡히므로 fstab은 UUID로 적어두는 게 안전하다.

### fstab 오타로 부팅 실패

가장 무서운 사고는 fstab을 고쳐놓고 재부팅했는데 부팅이 안 되는 상황이다. 옵션 오타, UUID 오타, 존재하지 않는 마운트 포인트 등이 원인이다.

부팅이 멈추면 systemd가 `emergency.target`으로 들어가 root 비밀번호를 묻는다. 여기까지 못 가면 GRUB에서 커널 라인을 편집해 `single`이나 `init=/bin/bash`를 넣고 부팅한다.

```
# GRUB 메뉴에서 e 키
# 커널 라인 끝에 추가
systemd.unit=emergency.target

# 또는 더 강제로
init=/bin/bash
```

`init=/bin/bash`로 들어가면 루트 파일 시스템이 보통 ro로 마운트되어 있다. fstab을 고치려면 rw로 다시 마운트해야 한다.

```bash
mount -o remount,rw /
vi /etc/fstab                      # 문제 줄을 # 로 주석 처리 또는 수정
mount -a                           # 즉시 검증
sync
reboot -f
```

문제 항목을 일단 주석 처리한 뒤 부팅 성공시키고, 디스크가 살아있다면 그 다음에 차근차근 해결하는 쪽이 안전하다. 평소에 fstab을 고친 직후 `findmnt --verify`와 `mount -a`로 검증하는 습관이 있으면 이 사고를 거의 다 막을 수 있다.

`nofail` 옵션을 외장 디스크나 비필수 마운트에 미리 적어두는 것도 같은 맥락이다. 그 항목 때문에 부팅이 멈추지 않게 한다.

### NFS 서버 다운으로 hang

NFS를 `hard` 마운트한 상태에서 서버가 다운되면, 그 마운트에 접근하는 모든 프로세스가 D state(uninterruptible sleep)로 멈춘다. D state는 시그널도 안 먹어서 `kill -9`로도 안 죽는다.

```bash
ps auxf | grep " D "               # D state 프로세스 확인
cat /proc/<pid>/wchan              # 어디서 멈췄는지
```

처리:

```bash
umount -f /mnt/nfs                 # 강제 umount 시도 (서버가 응답 안 해도 시도)
umount -f -l /mnt/nfs              # 강제 + lazy
```

`umount -f`는 NFS에 특화된 옵션이다. 그래도 안 풀리면 시스템 재부팅 외에는 답이 없는 경우도 있다. 그래서 NFS 마운트는 `hard,intr` 또는 `soft,timeo=30` 같은 옵션 조합을 신중하게 골라야 한다. 데이터 무결성이 절대적인 곳은 `hard`, 가용성이 더 중요한 곳(예: 로그 수집)은 `soft`.

## 정리

마운트는 단순한 명령이 아니라 커널의 파일 시스템 추상화와 네임스페이스 격리가 만나는 지점이다. fstab 한 줄을 적을 때도 옵션 의미, 부팅 시 의존성, 디스크 사라짐 시 동작까지 같이 생각해야 한다. 평소에 `findmnt --verify`로 검증하고, UUID 기반으로 적고, 외장/네트워크 마운트엔 `nofail`과 `_netdev`(혹은 `x-systemd.automount`)를 붙이는 정도만 지켜도 운영 사고는 크게 줄어든다.
