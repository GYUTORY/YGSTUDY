---
title: 프라이빗 컨테이너 레지스트리 구축과 운영
tags:
  - infra
  - container-registry
  - harbor
  - docker-registry
  - trivy
  - cosign
updated: 2026-06-24
---

# 프라이빗 컨테이너 레지스트리 구축과 운영

## 왜 자체 레지스트리를 두는가

처음엔 Docker Hub에 이미지를 올려서 썼다. 무료고 설정도 필요 없으니 편했다. 문제가 터진 건 서비스가 커지고 배포가 잦아진 다음이다. 어느 날 오토스케일링으로 노드가 한꺼번에 뜨면서 같은 이미지를 동시에 수십 번 pull 했더니 `toomanyrequests: You have reached your pull rate limit` 에러가 떨어지고 신규 파드가 ImagePullBackOff로 멈췄다. Docker Hub의 익명 pull은 IP당 6시간에 100회, 인증해도 200회로 제한된다. 노드가 NAT 게이트웨이 한 개를 공유하면 클러스터 전체가 하나의 IP로 보여서 이 한도가 순식간에 찬다.

자체 레지스트리를 두면 이 한도에서 벗어나고, 이미지가 외부망을 타지 않으니 pull 속도도 빨라진다. 사내 정책상 소스나 빌드 산출물을 외부에 두면 안 되는 경우에도 선택지가 없다. 운영하는 레지스트리는 크게 두 부류다. 단순히 이미지를 저장하고 내려주기만 하면 되는 `distribution`(예전 이름 Docker Registry)과, 인증·권한·취약점 스캔·서명·복제까지 묶은 Harbor다.

## distribution과 Harbor 중 무엇을 쓸까

distribution은 CNCF 프로젝트로, 레지스트리 API v2를 구현한 단일 바이너리다. 띄우는 건 1분이면 된다.

```bash
docker run -d -p 5000:5000 --name registry \
  -v /opt/registry/data:/var/lib/registry \
  registry:2.8
```

이게 전부다. 푸시하려면 `myhost:5000/myapp:1.0`처럼 호스트를 붙여 태그하고 push 하면 된다. 가볍고 의존성이 없어서 빌드 캐시 저장소나 폐쇄망 미러로 쓰기 좋다. 대신 인증은 basic auth 한 겹뿐이고, UI도 없고, 취약점 스캔이나 사용자별 권한 같은 건 전혀 없다. 누가 어떤 이미지를 올렸는지 추적할 방법이 없으니 여러 팀이 공유하는 순간 관리가 안 된다.

Harbor는 distribution을 저장 엔진으로 깔고 그 위에 운영에 필요한 것들을 얹은 제품이다. 프로젝트 단위로 이미지를 격리하고, LDAP·OIDC 연동, RBAC, Trivy 스캔, cosign 서명 검증, 다른 레지스트리와의 복제를 다 내장한다. 혼자 쓰거나 CI 캐시 용도면 distribution으로 충분하고, 여러 팀이 함께 쓰고 보안 요건이 있으면 Harbor를 쓴다. 아래 운영 얘기는 대부분 Harbor 기준이다.

## Harbor 설치

Harbor는 컴포넌트가 여럿이라 docker-compose로 묶어 배포하는 게 표준이다. 오프라인 설치 패키지를 받아서 `harbor.yml`을 채우고 설치 스크립트를 돌린다.

```yaml
# harbor.yml 핵심 부분
hostname: registry.example.com

https:
  port: 443
  certificate: /data/cert/registry.example.com.crt
  private_key: /data/cert/registry.example.com.key

harbor_admin_password: <초기-admin-비번>

data_volume: /data

trivy:
  enabled: true

# 기본 PostgreSQL/Redis는 내장. 외부 DB를 쓰려면 external_database 섹션 사용
```

```bash
./prepare
./install.sh --with-trivy
```

여기서 가장 자주 막히는 게 HTTPS다. Harbor를 HTTP로 띄우면 docker가 push/pull을 거부한다. docker는 기본적으로 레지스트리가 TLS를 쓴다고 가정하기 때문이다. 사내 CA로 발급한 인증서를 쓰면 클라이언트마다 그 CA를 신뢰 목록에 넣어줘야 한다.

```bash
# 각 docker 데몬 호스트에서
mkdir -p /etc/docker/certs.d/registry.example.com
cp ca.crt /etc/docker/certs.d/registry.example.com/ca.crt
```

이걸 빼먹으면 `x509: certificate signed by unknown authority`가 뜬다. 테스트 환경이라 인증서 검증을 건너뛰고 싶으면 `/etc/docker/daemon.json`에 `insecure-registries`로 호스트를 등록하는 방법도 있지만, 운영에서는 절대 쓰지 않는다. 한 번 열어두면 중간자 공격에 그대로 노출된다.

## 인증과 접근 제어

Harbor의 권한 모델은 프로젝트 → 멤버 → 역할 구조다. 프로젝트는 이미지를 담는 네임스페이스고, 각 프로젝트에 사용자나 그룹을 멤버로 넣으면서 역할을 준다. 역할은 게스트(읽기), 개발자(읽기·푸시), 마스터(+스캔·삭제), 프로젝트 관리자(+멤버 관리)로 나뉜다.

사람 계정은 보통 LDAP이나 OIDC로 연동한다. 사내 IdP에 OIDC를 붙여두면 Harbor에서 별도로 비밀번호를 관리할 필요가 없고, 퇴사자 처리도 IdP에서 끝난다.

CI 파이프라인이나 쿠버네티스가 이미지를 받을 때는 사람 계정을 쓰면 안 된다. 사람 계정의 비밀번호를 CI 시크릿에 박아두면 그 사람이 비번을 바꾸거나 퇴사하는 순간 파이프라인이 깨진다. 이럴 때 쓰는 게 robot account다. 특정 프로젝트에 한정해서 push/pull 권한만 가진 전용 계정을 만들고, 만료일을 박아둔다.

```bash
# robot account 토큰으로 로그인 (이름은 robot$프로젝트+이름 형식)
docker login registry.example.com \
  -u 'robot$ci+deployer' \
  -p '<robot-token>'
```

robot account의 토큰은 생성 시점에 한 번만 보여준다. 그 자리에서 시크릿 매니저에 저장하지 않으면 다시 못 보고 새로 만들어야 한다. 권한은 프로젝트별·동작별로 잘게 줄 수 있으니, 배포용은 pull만, 빌드용은 push만 주는 식으로 분리한다. CI가 통째로 탈취돼도 pull 전용 토큰이면 이미지를 덮어쓰지는 못한다.

쿠버네티스에서 프라이빗 레지스트리 이미지를 받으려면 pull 시크릿을 만들어 ServiceAccount에 붙인다.

```bash
kubectl create secret docker-registry harbor-pull \
  --docker-server=registry.example.com \
  --docker-username='robot$prod+puller' \
  --docker-password='<robot-token>' \
  -n prod
```

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: default
  namespace: prod
imagePullSecrets:
  - name: harbor-pull
```

## 이미지 취약점 스캔 (Trivy 연동)

Harbor는 Trivy를 스캐너로 내장한다. 설치 때 `--with-trivy`를 주면 같이 뜨고, 이미지를 push 하면 자동으로 스캔하거나(프로젝트 설정의 "Automatically scan images on push") 수동으로 스캔을 돌릴 수 있다. 스캔 결과는 CVE 목록과 심각도(Critical/High/Medium/Low)로 나온다.

운영에서 진짜 쓸모 있는 건 배포 차단이다. 프로젝트 설정에서 "Prevent vulnerable images from running"을 켜고 임계치를 Critical로 잡으면, Critical 취약점이 있는 이미지는 pull 자체가 막힌다. 다만 이 차단은 Harbor가 pull 요청을 거부하는 방식이라, 이미지를 노드가 이미 캐시하고 있으면 우회된다는 점은 알아둬야 한다.

처음 이걸 켜면 멀쩡히 돌던 배포가 갑자기 막혀서 당황한다. 베이스 이미지에 깔린 OS 패키지에서 Critical이 줄줄이 나오는 경우가 많다. 현실적으로는 베이스 이미지를 slim이나 distroless로 바꿔서 패키지 표면을 줄이는 게 먼저다. 당장 패치가 없는 CVE는 Harbor의 CVE allowlist에 등록해 예외 처리하되, 만료일을 걸어서 방치되지 않게 한다.

Trivy DB는 주기적으로 갱신돼야 의미가 있다. 폐쇄망이면 Trivy가 취약점 DB를 외부에서 못 받아와서 스캔 결과가 텅 비거나 오래된 상태로 남는다. 이때는 `trivy-db`를 사내 미러에 받아두고 Harbor의 Trivy가 그쪽을 바라보게 설정해야 한다.

## 이미지 서명 (cosign)

스캔이 "이 이미지에 알려진 취약점이 있나"를 본다면, 서명은 "이 이미지가 우리가 만든 그 이미지가 맞나"를 본다. 누군가 레지스트리에 침투해 이미지를 바꿔치기해도, 서명이 안 맞으면 배포 단계에서 걸러낸다.

cosign은 sigstore 프로젝트의 서명 도구다. 키 쌍을 만들고 이미지에 서명한다.

```bash
cosign generate-key-pair          # cosign.key / cosign.pub 생성

# 이미지 다이제스트에 서명 (태그가 아니라 다이제스트로 거는 게 안전)
cosign sign --key cosign.key \
  registry.example.com/prod/app@sha256:<digest>

# 검증
cosign verify --key cosign.pub \
  registry.example.com/prod/app@sha256:<digest>
```

서명은 태그가 아니라 다이제스트에 거는 게 핵심이다. 태그는 나중에 다른 이미지를 가리키게 옮길 수 있어서, 태그에 서명하면 의미가 약해진다.

서명을 만들기만 하고 검증하지 않으면 아무 의미가 없다. 검증은 배포 게이트에서 강제해야 한다. 쿠버네티스라면 admission controller(Kyverno나 sigstore policy-controller)를 붙여서, 서명이 검증되지 않은 이미지는 클러스터에 아예 못 뜨게 막는다. Harbor 자체도 cosign 서명 존재 여부를 확인해 미서명 이미지의 pull을 막는 설정이 있다.

CI에서 키 파일을 다루는 게 부담이면 keyless 서명을 쓴다. OIDC 신원으로 단기 인증서를 발급받아 서명하므로 장기 비밀키를 보관할 필요가 없다. 다만 검증 시 신뢰할 발급자와 신원을 명시해야 해서 설정이 한 단계 더 들어간다.

## GC와 스토리지 백엔드

레지스트리를 운영하면서 가장 흔하게 겪는 사고가 디스크 폭증이다. 이미지를 push 할 때마다 레이어가 쌓이는데, 태그를 덮어쓰거나 삭제해도 실제 blob 데이터는 디스크에 그대로 남는다. CI가 하루에도 수십 번 같은 태그로 push 하면, 참조가 끊긴 레이어가 계속 누적돼서 어느 날 디스크가 꽉 찬다.

이 끊긴 데이터를 지우는 게 garbage collection이다. distribution에서는 이렇게 돈다.

```bash
# 먼저 무엇이 지워질지 확인 (dry-run)
docker exec registry \
  registry garbage-collect --dry-run /etc/docker/registry/config.yml

# 실제 삭제
docker exec registry \
  registry garbage-collect /etc/docker/registry/config.yml
```

GC에서 반드시 알아야 할 건, 표준 GC가 mark-and-sweep 방식이라 그동안 push가 들어오면 정합성이 깨질 수 있다는 점이다. 그래서 distribution GC는 레지스트리를 읽기 전용으로 돌리거나 잠깐 멈춘 상태에서 하는 게 안전하다. Harbor는 GC를 작업 큐로 관리하면서 그 시간 동안 push를 막아주므로, Harbor UI에서 스케줄을 걸어 새벽 시간대에 돌리는 게 낫다.

또 하나, GC는 "참조 끊긴 blob"만 지운다. 태그가 살아있는 한 그 이미지는 안 지워진다. 오래된 태그 자체를 정리하려면 Harbor의 tag retention 정책을 따로 걸어야 한다. "최근 10개만 남기고 나머지 삭제" 같은 규칙을 프로젝트별로 설정한다. retention으로 태그를 정리한 뒤 GC를 돌려야 실제 디스크가 빈다. 이 순서를 헷갈리면 retention만 돌리고 디스크는 그대로라 당황한다.

스토리지가 커지면 로컬 디스크 대신 S3 같은 오브젝트 스토리지를 백엔드로 쓴다. config.yml에서 storage driver를 바꾼다.

```yaml
storage:
  s3:
    region: ap-northeast-2
    bucket: my-registry-bucket
    rootdirectory: /registry
    # 인스턴스 프로파일(IAM Role)을 쓰면 accesskey/secretkey 생략 가능
  delete:
    enabled: true   # 이게 false면 이미지 삭제·GC가 동작 안 한다
  redirect:
    disable: false  # S3 presigned URL로 클라이언트가 직접 받게 함
```

`delete.enabled: true`를 빼먹으면 삭제 API가 막혀서 GC도 안 되고 디스크(버킷)만 계속 큰다. 자주 놓치는 부분이다. `redirect`를 켜두면 클라이언트가 레지스트리를 거치지 않고 S3에서 직접 레이어를 받으므로 레지스트리 서버의 대역폭 부담이 줄지만, 클라이언트가 S3 엔드포인트에 직접 닿을 수 있어야 한다. VPC 안에서만 도는 폐쇄망이면 S3 VPC 엔드포인트가 필요하다.

## 레플리케이션

Harbor는 다른 레지스트리와 이미지를 복제하는 기능을 내장한다. 쓰는 상황은 대개 두 가지다. 하나는 멀티 리전 배포에서 서울 레지스트리의 이미지를 다른 리전 레지스트리로 복제해 pull 지연을 줄이는 경우, 다른 하나는 Docker Hub나 외부 레지스트리의 이미지를 사내로 끌어와 캐시하는 경우다.

복제는 endpoint(대상 레지스트리)를 등록하고, rule(어떤 이미지를 어느 방향으로 복제할지)을 만든다. push-based(원본에서 push 시점에 밀어줌)와 pull-based(주기적으로 당겨옴) 두 모드가 있다. 외부에서 끌어오는 미러 용도는 pull-based로 패턴 매칭(`library/**` 같은)을 걸어둔다.

여기서 주의할 건 복제도 결국 한도와 대역폭을 쓴다는 점이다. Docker Hub에서 pull-based로 너무 광범위한 패턴을 걸면 그쪽 rate limit에 걸려서 복제가 계속 실패한다. 필요한 이미지만 좁게 거는 게 맞다.

## ECR·GCR 같은 매니지드와의 비교

직접 Harbor를 세우는 대신 클라우드 매니지드 레지스트리를 쓰는 선택지도 있다. AWS는 ECR, GCP는 Artifact Registry(예전 GCR), Azure는 ACR이다.

매니지드의 장점은 운영 부담이 거의 없다는 것이다. 디스크 관리, GC, 가용성, 백업을 클라우드가 알아서 한다. ECR은 IAM으로 권한을 관리하니 클러스터가 같은 계정에 있으면 pull 시크릿을 따로 안 만들고 노드의 IAM Role로 바로 받는다. 스캔도 기본으로 들어있고(ECR은 Basic은 Clair류, Enhanced는 Inspector 연동), lifecycle policy로 오래된 이미지 자동 삭제도 된다.

직접 구축이 나은 경우는 폐쇄망이라 외부 클라우드에 못 붙거나, 멀티 클라우드라 특정 벤더에 묶이기 싫거나, Harbor의 RBAC·복제·서명 검증을 한 곳에서 통합 관리하고 싶을 때다. 비용 구조도 다르다. 매니지드는 저장 용량과 데이터 전송(특히 리전 밖으로 나가는 트래픽)에 과금되므로, 이미지가 크고 pull이 잦으면 전송 비용이 의외로 크다. 같은 클라우드 안에서 pull 하면 전송비가 없거나 싸지만, 다른 리전이나 온프렘으로 끌어오면 비용이 붙는다.

ECR도 IAM 인증 토큰의 유효기간이 12시간이라, CI가 `aws ecr get-login-password`로 토큰을 받아 docker login 하는 흐름을 자동화해두지 않으면 토큰 만료로 push가 실패한다. 매니지드라고 신경 쓸 게 없는 건 아니다.

## 실무에서 자주 터지는 문제

**pull rate limit.** 앞서 말한 Docker Hub 한도가 가장 흔하다. 해결은 사내 레지스트리에 자주 쓰는 베이스 이미지를 미러로 받아두고, 빌드와 배포가 그 미러를 바라보게 하는 것이다. 쿠버네티스라면 `registry-mirror`를 설정하거나, 이미지 태그를 사내 레지스트리 주소로 바꿔서 쓴다. 인증된 Docker Hub 계정을 pull 시크릿으로 붙이는 것만으로도 익명 한도(100)에서 인증 한도(200)로 늘어나 급한 불은 끈다.

**디스크 폭증.** GC 미설정, retention 미설정, `delete.enabled: false`가 겹치면 반드시 터진다. retention으로 오래된 태그를 정리하고, GC를 새벽에 정기적으로 돌리고, 스토리지 사용량에 알람을 건다. 어느 프로젝트가 디스크를 먹는지 모르겠으면 blob 사용량을 프로젝트별로 본다.

**태그 immutable 미설정.** `app:latest`나 `app:1.0`을 매 배포마다 덮어쓰면 나중에 "그때 배포한 1.0이 정확히 어떤 이미지였나"를 못 찾는다. 롤백할 때 같은 태그가 이미 다른 이미지로 바뀌어 있으면 재현이 안 된다. Harbor 프로젝트 설정에서 tag immutability 규칙을 걸어두면, 한 번 push 된 태그는 덮어쓸 수 없게 된다. 더 확실한 건 배포에 태그 대신 다이제스트(`@sha256:...`)를 쓰는 것이다. 다이제스트는 내용이 바뀌면 값 자체가 바뀌므로 같은 다이제스트는 항상 같은 이미지를 가리킨다. CI가 push 후 출력하는 다이제스트를 받아 배포 매니페스트에 박아두면 롤백과 재현이 명확해진다.

**ImagePullBackOff인데 원인이 안 보일 때.** 노드에서 직접 `crictl pull` 또는 `docker pull`을 쳐보면 진짜 에러 메시지가 나온다. 쿠버네티스 이벤트는 메시지가 잘려서 인증 문제인지 인증서 문제인지 네트워크 문제인지 구분이 안 될 때가 많다. 인증서(`x509`), 인증(`unauthorized`), 한도(`toomanyrequests`), 네임 해석 실패가 대부분이다.
