
# Docker에서 파일 마운트하기

Docker에서 파일 마운트는 컨테이너와 호스트 간에 파일을 공유하거나 데이터를 유지하기 위해 사용하는 기능입니다. 이를 통해 호스트 시스템의 디렉터리 또는 파일을 컨테이너 내부에 연결할 수 있습니다.

---

## 파일 마운트란?

파일 마운트는 컨테이너 내부에서 사용할 파일을 외부(호스트 시스템)에서 제공하는 것을 의미합니다. 마운트된 파일은 컨테이너가 종료되더라도 데이터가 유지됩니다.

---

## 파일 마운트 방법

Docker에서는 두 가지 방법으로 파일을 마운트할 수 있습니다:

1. **바인드 마운트(Bind Mount)**
2. **볼륨 마운트(Volume Mount)**

---

### 1. 바인드 마운트(Bind Mount)

바인드 마운트는 호스트 시스템의 특정 디렉터리나 파일을 컨테이너 내부에 연결하는 방식입니다.

#### 명령어 예시

```bash
docker run -v /호스트/경로:/컨테이너/경로 이미지명
```

#### 옵션 설명

- `/호스트/경로` : 호스트 시스템의 디렉터리 또는 파일 경로
- `/컨테이너/경로` : 컨테이너 내부에서 접근할 경로
- `-v` 또는 `--mount` 옵션 사용 가능

#### 예제

```bash
docker run -it --name my-container -v /home/user/data:/app/data ubuntu
```

- 호스트 경로 `/home/user/data`가 컨테이너 내부 경로 `/app/data`에 마운트됩니다.
- 컨테이너 내부에서 `/app/data`를 수정하면 호스트의 `/home/user/data`에도 반영됩니다.

#### 주의점

- 마운트할 디렉터리나 파일이 호스트에 존재하지 않으면 생성되지 않습니다.
- 보안 이슈: 호스트의 중요한 디렉터리를 마운트하면 컨테이너가 직접 접근할 수 있습니다.

---

### 2. 볼륨 마운트(Volume Mount)

볼륨 마운트는 Docker가 관리하는 전용 저장소를 사용하는 방식으로, 컨테이너 간 데이터 공유 및 영구 저장소로 활용됩니다.

#### 명령어 예시

```bash
docker run -v 볼륨명:/컨테이너/경로 이미지명
```

또는

```bash
docker run --mount source=볼륨명,target=/컨테이너/경로 이미지명
```

#### 예제

```bash
docker volume create my-volume
docker run -it --name my-container -v my-volume:/app/data ubuntu
```

- `my-volume`이라는 Docker 볼륨이 `/app/data`에 마운트됩니다.
- 볼륨은 컨테이너가 삭제되어도 데이터가 유지됩니다.

#### 볼륨 관리 명령어

- 볼륨 목록 확인:
  ```bash
  docker volume ls
  ```

- 볼륨 삭제:
  ```bash
  docker volume rm 볼륨명
  ```

---

## `-v`와 `--mount` 차이

| 옵션         | `-v`                           | `--mount`                      |
|--------------|--------------------------------|--------------------------------|
| 사용 방식    | 간단한 구문                    | 더 명확하고 세부적인 설정 가능 |
| 지원 기능    | 바인드 마운트, 볼륨 마운트      | 바인드 마운트, 볼륨 마운트, tmpfs |
| 추천 상황    | 빠르고 간단한 설정             | 명확한 설정이 필요한 경우      |

---

## 사용 사례

1. **바인드 마운트**
    - 개발 중 소스 코드를 컨테이너에 연결
    - 로그 파일을 컨테이너에서 호스트로 저장

2. **볼륨 마운트**
    - 데이터베이스 컨테이너의 데이터 영구 저장
    - 컨테이너 간 데이터 공유

---

## 예제: 파일 마운트

호스트의 `config.json` 파일을 컨테이너 내부 `/app/config.json`에 마운트하는 예제:

```bash
docker run -it -v /path/to/config.json:/app/config.json ubuntu
```

---

## 참고 사항

- 마운트된 디렉터리나 파일은 컨테이너가 종료되어도 호스트에서 유지됩니다.
- 권한 문제를 방지하려면 적절한 파일 및 디렉터리 권한을 설정하세요.
- 볼륨을 사용하는 경우 Docker CLI로 쉽게 관리할 수 있습니다.
