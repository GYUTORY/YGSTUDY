---
title: Container Escape
tags: [security, docker, kubernetes, linux]
updated: 2026-10-10
---

# Container Escape

## 컨테이너는 격리 장치가 아니다

컨테이너는 가상머신이 아니다. 호스트 커널을 그대로 공유하고, 프로세스·네트워크·파일시스템 **뷰**만 네임스페이스로 갈라놓은 일반 프로세스다. 그 뷰를 유지하는 건 커널의 세 가지 장치다.

- **네임스페이스**: 무엇을 볼 수 있는지 제한한다 (PID, mount, network, user, …)
- **cgroup**: 얼마나 쓸 수 있는지 제한한다
- **capability·seccomp·LSM**: 어떤 커널 호출을 할 수 있는지 제한한다

탈출(escape)은 이 중 하나가 느슨해져 컨테이너 안의 코드가 호스트 자원에 직접 닿는 상태다. 커널 자체를 깨뜨리는 제로데이가 필요한 경우는 드물고, 대부분은 **운영자가 편의를 위해 격리를 스스로 열어둔 지점**이 통로가 된다.

그래서 탈출을 이해하는 건 공격 기법을 외우는 일이 아니라, 지금 내가 준 설정이 위 세 장치 중 무엇을 껐는지 읽는 일이다. 방어 설정 자체는 [Docker 컨테이너 보안](Container_Security.md)에서 다루고, 이 문서는 어떤 설정이 어떤 격리를 허무는지를 방어자 시점에서 정리한다.

## 어디가 뚫리는지로 나눈다

| 갈래 | 허물어지는 장치 | 대표 원인 | 커널 버그 필요 |
|---|---|---|---|
| 호스트 자원 직접 노출 | mount 네임스페이스 | docker.sock, hostPath, 호스트 `/proc` | 없음 |
| 과잉 권한 | capability·seccomp | `--privileged`, `CAP_SYS_ADMIN` | 없음 |
| 런타임 구현 결함 | 런타임 자체 | runc·containerd 취약점 | 없음(패치로 해결) |
| 커널 취약점 | 커널 | user namespace·cgroup 버그 | 있음 |

앞의 두 갈래가 실무에서 압도적으로 많다. 패치가 최신이어도 설정이 열려 있으면 그대로 뚫리는 영역이라, 방어의 중심은 패치가 아니라 설정 검토다.

## Docker 소켓 노출 — 가장 흔한 통로

CI에서 컨테이너 안에서 이미지를 빌드하려고 `/var/run/docker.sock`을 마운트하는 구성이 널리 퍼져 있다.

```bash
# 이 한 줄이 컨테이너를 호스트 관리자 콘솔로 만든다
docker run -v /var/run/docker.sock:/var/run/docker.sock my-ci-image
```

소켓은 Docker 데몬의 API 엔드포인트고, 데몬은 호스트에서 root로 돈다. 소켓에 접근할 수 있는 프로세스는 데몬에게 임의의 컨테이너 생성·호스트 경로 마운트를 요청할 수 있으므로, **소켓 접근 권한은 사실상 호스트 루트 권한과 같다.** 별도의 취약점이 필요 없다는 점이 핵심이다.

막는 방법:

- CI 빌드는 데몬이 필요 없는 **rootless 빌더**(kaniko, buildah, BuildKit rootless)로 바꾼다. 컨테이너 안에서 `docker build`를 하려는 요구 자체를 없애는 게 근본 해결이다.
- 소켓을 꼭 노출해야 하면 읽기 전용으로도 안전하지 않다 — API는 GET만으로도 정보를 충분히 흘린다. 프록시(`docker-socket-proxy`)로 허용 엔드포인트를 화이트리스트한다.
- 쿠버네티스에서는 노드의 소켓을 Pod에 `hostPath`로 넣지 않는다. 이미지 빌드는 클러스터 밖 전용 러너나 rootless 빌더로 분리한다.

## `--privileged` 와 과잉 capability

`--privileged`는 모든 capability를 부여하고 seccomp·AppArmor를 끄며 모든 호스트 디바이스 접근을 연다. 격리를 거의 전부 해제하는 플래그다. 이 상태에서는 호스트 디스크 디바이스나 커널 인터페이스에 직접 접근할 수 있어, 추가 취약점 없이도 호스트에 쓰기가 가능해진다.

개별 capability 중에서도 다음은 단독으로 탈출 경로를 연다.

- **`CAP_SYS_ADMIN`**: 마운트·네임스페이스 조작을 허용한다. "일단 되게 하려고" 가장 자주 추가되는데, 가장 위험하다.
- **`CAP_DAC_READ_SEARCH`**: 파일 권한 검사를 우회해 호스트 파일시스템을 읽을 수 있다.
- **`CAP_SYS_PTRACE` + 공유 네임스페이스**: 다른 프로세스 메모리에 접근한다.

막는 방법:

- `--privileged`를 쓰지 않는다. GPU처럼 특정 디바이스가 필요하면 `--device`로 그 디바이스만, 필요한 capability만 개별로 준다.
- 기본 capability도 넘친다. `--cap-drop=ALL` 후 꼭 필요한 것만 `--cap-add`로 되돌린다.
- `--security-opt=no-new-privileges`로 setuid를 통한 권한 상승을 봉쇄한다.
- 쿠버네티스에서는 `securityContext`에 `privileged: false`, `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]`을 명시하고, Pod Security Standards의 `restricted` 프로파일을 네임스페이스에 강제한다.

## 호스트 경로·`/proc` 노출

호스트 디렉터리를 컨테이너에 마운트하면 그 경로에 대한 격리가 사라진다. 특히 다음은 탈출로 직결된다.

- **호스트 `/` 또는 `/etc`, `/root` 마운트**: 설정·크론·인증키를 직접 수정할 수 있다.
- **호스트 `/proc`나 `/sys` 마운트**: 커널 파라미터와 다른 프로세스 정보에 접근한다. 과거 `core_pattern`을 통한 탈출이 여기서 나왔다.
- **쿠버네티스 `hostPath` 볼륨**: 노드의 임의 경로를 Pod에 연결한다. 노드의 kubelet 설정이나 다른 Pod의 데이터에 닿는다.

막는 방법:

- 호스트 경로 마운트는 원칙적으로 금지하고, 필요하면 최소 하위 경로만 읽기 전용(`:ro`)으로 한다.
- 쿠버네티스에서는 `hostPath`를 admission 정책(OPA/Gatekeeper, Kyverno)으로 차단하고, 영속 저장소는 PV/PVC나 CSI 드라이버로 대체한다.
- 컨테이너 파일시스템은 `--read-only`로 올리고, 쓰기가 필요한 곳만 `tmpfs`나 명시적 볼륨으로 연다.

## 런타임 구현 결함

설정을 올바르게 해도 런타임(runc, containerd) 자체의 버그로 탈출이 일어난 사례가 주기적으로 나온다. 대표적으로 runc의 파일 디스크립터 처리 결함(CVE-2019-5736 계열)은 컨테이너가 호스트의 runc 바이너리를 덮어써 다음 실행 때 호스트에서 코드가 돌게 만들었다.

이 갈래는 설정으로 막을 수 없고 **패치가 유일한 방어**다.

- runc·containerd·Docker를 보안 공지에 맞춰 즉시 올린다. 노드 OS의 자동 보안 업데이트를 켠다.
- 런타임 이상 동작을 탐지하도록 [컨테이너 런타임 탐지와 Falco](Container_Runtime_Security_Falco.md)를 함께 둔다. 탈출 시도는 대개 비정상적인 `execve`·마운트·파일 쓰기로 드러난다.

## 커널 취약점과 user namespace

마지막 갈래는 커널 자체의 버그다. user namespace는 컨테이너 안의 root를 호스트의 비특권 UID로 매핑해 공격 표면을 줄이는 좋은 장치지만, 역설적으로 비특권 사용자가 커널의 특권 코드 경로에 닿게 해 과거 여러 LPE(로컬 권한 상승) 취약점의 입구가 되기도 했다.

균형은 이렇게 잡는다.

- user namespace 자체는 켜는 쪽이 낫다. 컨테이너 root가 곧 호스트 root가 되는 것을 막아준다. 쿠버네티스 1.30+의 `hostUsers: false`가 이를 런타임 교체 없이 제공한다.
- 그 위에 seccomp 기본 프로파일을 유지해 커널 공격 표면(접근 가능한 syscall 수)을 줄인다. `--privileged`가 이걸 끄는 것이 위험한 이유다.
- 민감한 멀티테넌트 워크로드는 커널 공유 자체를 줄이는 샌드박스 런타임(gVisor, Kata Containers)으로 격리 수준을 한 단계 올린다. [쿠버네티스 보안](Kubernetes_Security.md)의 RuntimeClass로 워크로드별로 지정한다.

## 방어를 한 장으로

탈출의 거의 전부는 "격리를 스스로 열었는가"로 수렴한다. 아래를 기본값으로 두면 설정 기인 탈출은 대부분 닫힌다.

1. `--privileged` 금지. capability는 `drop ALL` 후 최소만 추가.
2. `no-new-privileges` 켜기, 컨테이너 파일시스템 read-only.
3. docker.sock·호스트 경로·`hostPath` 마운트 금지. 빌드는 rootless 빌더로.
4. seccomp·AppArmor 기본 프로파일 유지.
5. 런타임·커널 패치 최신 유지, Falco로 런타임 이상 탐지.
6. 멀티테넌트는 user namespace + gVisor/Kata로 커널 공유 축소.

설정으로 막는 1~4가 가장 비용이 낮고 효과가 크다. 5~6은 설정으로 막을 수 없는 나머지를 위한 층이다.

## 참고

- [Docker 컨테이너 보안](Container_Security.md)
- [쿠버네티스 보안](Kubernetes_Security.md)
- [컨테이너 런타임 탐지와 Falco](Container_Runtime_Security_Falco.md)
- [Rootless 컨테이너와 User Namespace](Rootless_Containers_User_Namespaces.md)
- [NIST SP 800-190 — Application Container Security Guide](https://csrc.nist.gov/publications/detail/sp/800-190/final)
- [Docker — Runtime privilege and Linux capabilities](https://docs.docker.com/engine/containers/run/#runtime-privilege-and-linux-capabilities)
- [Kubernetes — Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
