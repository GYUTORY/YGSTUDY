---
title: Docker 컨테이너 보안
tags: [security, docker, kubernetes, container]
updated: 2026-03-25
---

# Docker 컨테이너 보안

## 컨테이너는 VM이 아니다

컨테이너는 커널을 호스트와 공유한다. 격리 수준이 VM보다 낮기 때문에, 컨테이너 내부에서 권한 상승이 발생하면 호스트까지 영향을 줄 수 있다. 보안 설정 없이 `docker run`만 하면 사실상 호스트에 루트 쉘을 열어두는 것과 다를 바 없는 경우가 생긴다.

---

## non-root 실행

컨테이너 내부 프로세스가 root로 돌아가면, 컨테이너 탈출(container escape) 취약점이 터졌을 때 호스트의 root 권한을 그대로 가져간다.

```dockerfile
FROM node:20-slim

# 유저 생성
RUN groupadd -r app && useradd -r -g app -d /home/app -s /sbin/nologin app

WORKDIR /home/app
COPY --chown=app:app . .

# 루트가 필요한 작업(패키지 설치 등)은 여기서 끝낸다
RUN npm ci --omit=dev

# 이후부터 app 유저로 전환
USER app

CMD ["node", "server.js"]
```

주의할 점:

- `USER` 지시자를 `RUN npm ci` 뒤에 넣어야 한다. npm 패키지 설치 시 root 권한이 필요한 경우가 있다.
- 바인드 마운트한 볼륨의 소유자가 root면 app 유저가 쓰기 실패한다. 호스트에서 미리 퍼미션을 맞춰야 한다.
- Alpine 베이스 이미지는 `addgroup`/`adduser` 명령어가 다르다.

```dockerfile
# Alpine의 경우
RUN addgroup -S app && adduser -S -G app app
```

런타임에서 강제하는 방법도 있다:

```bash
docker run --user 1000:1000 myimage
```

이미지 안에 해당 UID가 없어도 동작하지만, `/etc/passwd`에 매핑이 없어서 로그에 `I have no name!` 같은 경고가 뜬다. 기능상 문제는 없지만, 이미지 내에서 유저를 만들어두는 게 깔끔하다.

---

## read-only 파일시스템

컨테이너 내부에서 파일을 쓸 수 없게 만들면, 공격자가 악성 바이너리를 다운받거나 설정 파일을 변조하는 걸 막는다.

```bash
docker run --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --tmpfs /var/run:rw,noexec,nosuid \
  myimage
```

- `--read-only`: 컨테이너의 루트 파일시스템을 읽기 전용으로 마운트
- `--tmpfs`: 로그나 PID 파일 등 쓰기가 필요한 경로만 tmpfs로 열어준다
- `noexec`: tmpfs에서 바이너리 실행 차단. 공격자가 `/tmp`에 뭔가 다운받아 실행하는 걸 막는다

실제로 적용하면 의외로 많은 앱이 깨진다. 로그를 파일로 쓰는 앱, `/var/cache`에 뭔가 저장하는 앱 등. 하나씩 tmpfs를 추가하면서 맞춰야 한다.

---

## seccomp과 AppArmor

### seccomp

Linux 커널의 시스템콜을 필터링한다. Docker는 기본 seccomp 프로파일을 적용하는데, `ptrace`, `mount` 같은 위험한 시스템콜 약 44개를 차단한다.

```bash
# 기본 프로파일 확인 (Docker 소스에 포함)
docker run --rm --security-opt seccomp=default myimage

# 커스텀 프로파일 적용
docker run --security-opt seccomp=my-profile.json myimage
```

커스텀 프로파일 예시 — `chmod` 시스템콜을 차단하는 경우:

```json
{
  "defaultAction": "SCMP_ACT_ALLOW",
  "syscalls": [
    {
      "names": ["chmod", "fchmod", "fchmodat"],
      "action": "SCMP_ACT_ERRNO",
      "errnoRet": 1
    }
  ]
}
```

`--security-opt seccomp=unconfined`로 seccomp을 끄는 경우가 있는데, 디버깅 용도 외에는 쓰면 안 된다. CI 환경에서 "seccomp 때문에 빌드 실패한다"고 끄는 걸 자주 보는데, 프로파일을 맞추는 게 맞다.

### AppArmor

파일 접근, 네트워크, 프로세스 실행 등을 제어하는 MAC(Mandatory Access Control) 시스템이다. Docker는 기본 AppArmor 프로파일(`docker-default`)을 자동 적용한다.

```bash
# 커스텀 프로파일 적용
docker run --security-opt apparmor=my-custom-profile myimage
```

seccomp이 시스템콜 레벨, AppArmor는 리소스 접근 레벨이다. 둘 다 쓰는 게 맞다.

---

## 이미지 취약점 스캔

### Trivy

오픈소스, 로컬에서 바로 돌릴 수 있다.

```bash
# 이미지 스캔
trivy image myapp:latest

# HIGH, CRITICAL만 보기
trivy image --severity HIGH,CRITICAL myapp:latest

# 취약점 있으면 exit code 1 — CI에서 빌드 실패시키기 좋다
trivy image --exit-code 1 --severity CRITICAL myapp:latest

# 수정 가능한 취약점만 보기 (패치가 나온 것만)
trivy image --ignore-unfixed myapp:latest
```

### Snyk

SaaS 기반, 무료 플랜에서 월 200회 스캔 가능.

```bash
# Docker 이미지 스캔
snyk container test myapp:latest

# Dockerfile도 같이 넘기면 수정 제안까지 해준다
snyk container test myapp:latest --file=Dockerfile
```

### CI에 통합하기

GitHub Actions 예시:

```yaml
- name: Scan image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: myapp:${{ github.sha }}
    format: table
    exit-code: 1
    severity: CRITICAL,HIGH
```

실무에서 자주 하는 실수:

- 스캔은 걸어놨는데 `exit-code`를 안 넣어서 취약점이 있어도 빌드가 통과된다
- base 이미지(`node:20`, `python:3.12`)에 있는 취약점은 내가 고칠 수 없다. `-slim`이나 `-alpine` 베이스로 바꾸면 대부분 줄어든다
- 스캔 결과가 너무 많으면 팀에서 무시하기 시작한다. CRITICAL만 빌드 실패시키고, HIGH는 주간 리뷰로 돌리는 게 현실적이다

---

## 멀티스테이지 빌드

빌드 도구, 소스코드, 개발 의존성을 최종 이미지에서 제거한다. 이미지에 있는 바이너리가 적을수록 공격에 쓸 수 있는 도구가 줄어든다.

```dockerfile
# --- 빌드 스테이지 ---
FROM golang:1.22 AS builder

WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /app/server .

# --- 런타임 스테이지 ---
FROM gcr.io/distroless/static-debian12

COPY --from=builder /app/server /server

USER nonroot:nonroot

ENTRYPOINT ["/server"]
```

distroless 이미지에는 셸이 없다. 공격자가 컨테이너에 들어와도 `sh`, `bash`, `curl`, `wget` 같은 도구를 쓸 수 없다.

단점도 있다:

- 디버깅이 어렵다. `docker exec -it container sh`가 안 된다
- 디버그용 이미지를 따로 만들거나, `gcr.io/distroless/static-debian12:debug` 태그를 쓰면 busybox 셸이 포함된다. 프로덕션에는 절대 쓰지 않는다

Node.js 앱의 경우:

```dockerfile
FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-slim
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
USER node
CMD ["node", "dist/index.js"]
```

`devDependencies`에 있는 패키지(webpack, typescript, eslint 등)는 빌드 스테이지에만 존재하고 최종 이미지에는 들어가지 않는다. 다만 `node_modules` 전체를 복사하면 devDependencies도 딸려온다. 런타임 스테이지에서 `npm ci --omit=dev`를 다시 하거나, 빌드 스테이지에서 프로덕션 의존성만 따로 뽑아야 한다.

---

## Secrets 관리

### 환경변수의 위험성

```bash
# 이렇게 하면 안 된다
docker run -e DB_PASSWORD=mysecret myapp
```

문제점:

- `docker inspect`로 환경변수가 그대로 노출된다
- `/proc/1/environ` 파일에서도 읽을 수 있다
- 로그에 환경변수를 덤프하는 라이브러리가 있다 (Spring Boot Actuator의 `/env` 엔드포인트 등)

### Docker Secrets (Swarm 모드)

```bash
# 시크릿 생성
echo "mysecretpassword" | docker secret create db_password -

# 서비스에서 사용
docker service create \
  --name myapp \
  --secret db_password \
  myapp:latest
```

컨테이너 안에서는 `/run/secrets/db_password` 파일로 접근한다:

```python
def get_secret(name):
    secret_path = f"/run/secrets/{name}"
    with open(secret_path, "r") as f:
        return f.read().strip()

db_password = get_secret("db_password")
```

### 빌드 시 시크릿

Dockerfile에서 private 레지스트리 접근 등이 필요할 때:

```dockerfile
# 절대 이렇게 하면 안 된다 — 이미지 레이어에 시크릿이 남는다
# COPY .npmrc /root/.npmrc
# RUN npm ci
# RUN rm /root/.npmrc   ← 레이어에 이미 기록됨, 삭제해도 소용없다

# BuildKit secret mount를 써야 한다
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci
```

```bash
docker build --secret id=npmrc,src=.npmrc -t myapp .
```

`--mount=type=secret`은 해당 `RUN` 명령어 실행 중에만 마운트되고, 이미지 레이어에 기록되지 않는다.

---

## Kubernetes Pod Security Standards

Kubernetes 1.25부터 PodSecurityPolicy(PSP)가 제거되고, Pod Security Standards(PSS)로 대체됐다. 네임스페이스 레벨에서 레이블로 적용한다.

### 세 가지 레벨

| 레벨 | 설명 |
|------|------|
| Privileged | 제한 없음. 시스템 컴포넌트용 |
| Baseline | 알려진 위험한 설정 차단. hostNetwork, hostPID, privileged 컨테이너 등 |
| Restricted | 가장 엄격. non-root 필수, 볼륨 타입 제한, seccomp 프로파일 필수 |

```bash
# 네임스페이스에 restricted 적용
kubectl label namespace myapp \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/warn=restricted \
  pod-security.kubernetes.io/audit=restricted
```

- `enforce`: 위반 시 Pod 생성 거부
- `warn`: 위반 시 경고 메시지 표시, 생성은 허용
- `audit`: 감사 로그에 기록

처음 적용할 때는 `warn`으로 시작해서 어떤 Pod이 걸리는지 확인하고, 수정 후 `enforce`로 올리는 게 안전하다.

### Restricted 레벨을 만족하는 Pod 스펙

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
  namespace: myapp
spec:
  securityContext:
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: app
      image: myapp:latest
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        runAsNonRoot: true
        capabilities:
          drop:
            - ALL
      volumeMounts:
        - name: tmp
          mountPath: /tmp
  volumes:
    - name: tmp
      emptyDir:
        sizeLimit: 64Mi
```

`capabilities.drop: ALL`은 Linux capability를 전부 제거한다. 대부분의 앱은 capability 없이 동작한다. 특정 capability가 필요한 경우(예: 포트 80 바인딩에 `NET_BIND_SERVICE`)만 `add`로 추가한다.

---

## NetworkPolicy

기본적으로 Kubernetes Pod은 클러스터 내 모든 Pod과 통신할 수 있다. 하나의 Pod이 뚫리면 횡이동(lateral movement)이 가능하다는 뜻이다.

### 기본 차단 후 필요한 것만 허용

```yaml
# 모든 인바운드 트래픽 차단 (default deny)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
  namespace: myapp
spec:
  podSelector: {}
  policyTypes:
    - Ingress
```

```yaml
# 특정 Pod 간 통신만 허용
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-to-db
  namespace: myapp
spec:
  podSelector:
    matchLabels:
      app: postgres
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: api-server
      ports:
        - protocol: TCP
          port: 5432
```

이 설정은 `app: api-server` 레이블이 붙은 Pod만 postgres의 5432 포트로 접근할 수 있게 한다. 다른 Pod에서 postgres에 접근하면 패킷이 드롭된다.

주의사항:

- NetworkPolicy는 CNI 플러그인이 지원해야 동작한다. Calico, Cilium은 지원하지만, 기본 kubenet은 지원하지 않는다. EKS는 VPC CNI 기본 설정에서 NetworkPolicy를 지원하지 않았는데, 1.25부터 지원이 추가됐다
- 이그레스(outbound) 정책도 걸어야 한다. 공격자가 Pod 안에서 외부로 데이터를 빼내는 걸 막으려면 이그레스도 default deny 후 필요한 것만 열어야 한다
- DNS(UDP 53)를 이그레스에서 허용하지 않으면 서비스 디스커버리가 깨진다. 이그레스 정책 적용 시 kube-dns 접근은 반드시 열어둬야 한다

```yaml
# 이그레스 default deny + DNS 허용
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: restrict-egress
  namespace: myapp
spec:
  podSelector:
    matchLabels:
      app: api-server
  policyTypes:
    - Egress
  egress:
    # DNS 허용
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
    # postgres만 허용
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - protocol: TCP
          port: 5432
```

---

## 실무에서 자주 놓치는 것들

**Docker Socket 마운트**: CI에서 Docker-in-Docker를 위해 `/var/run/docker.sock`을 마운트하는 경우가 많다. 이 소켓에 접근하면 호스트의 모든 컨테이너를 제어할 수 있다. 사실상 호스트 루트 권한이다. CI에서는 kaniko 같은 rootless 빌드 도구를 쓰는 게 낫다.

**latest 태그**: `image: myapp:latest`는 어떤 버전이 배포됐는지 추적이 안 된다. 취약점이 있는 이미지가 배포돼도 롤백할 수 없다. SHA digest를 쓰거나, 최소한 버전 태그를 써야 한다.

```yaml
# 이렇게
image: myapp@sha256:abc123...
# 또는 이렇게
image: myapp:1.2.3
```

**`--privileged` 플래그**: 모든 Linux capability를 부여하고, 모든 디바이스에 접근 가능하게 하며, seccomp과 AppArmor를 비활성화한다. 컨테이너 격리가 사실상 없어진다. GPU 사용이나 특수한 하드웨어 접근이 필요한 경우가 아니면 쓰지 않는다.
