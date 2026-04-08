---
title: Ansible
tags: [ansible, iac, configuration-management, devops, ssh, automation]
updated: 2026-04-08
---

# Ansible

## Ansible이 뭔가

Red Hat이 관리하는 서버 구성 관리 도구다. YAML로 작성한 Playbook을 SSH로 원격 서버에 실행해서 패키지 설치, 설정 변경, 서비스 재시작 같은 작업을 자동화한다.

Chef, Puppet 같은 도구와 비교하면 가장 큰 차이는 **에이전트가 필요 없다**는 점이다. 대상 서버에 별도 데몬을 설치하지 않는다. SSH 접속만 되면 바로 쓸 수 있다. 서버 100대에 에이전트를 깔고 관리하는 것 자체가 이미 운영 부담인데, Ansible은 그 부담이 없다.

Python으로 만들어졌고, 대상 서버에도 Python이 설치되어 있어야 한다. 대부분의 리눅스 배포판에 Python이 기본 설치되어 있어서 실무에서 문제가 되는 경우는 드물지만, 최소 설치 이미지를 쓰는 경우 `raw` 모듈로 Python부터 설치해야 하는 상황이 생긴다.

## 핵심 구성 요소

### Inventory

Ansible이 관리할 서버 목록이다. INI 형식이나 YAML로 작성한다.

```ini
# inventory/production.ini

[web]
web-01.example.com
web-02.example.com

[db]
db-01.example.com ansible_port=2222

[web:vars]
ansible_user=deploy
ansible_python_interpreter=/usr/bin/python3
```

그룹으로 묶어서 특정 그룹에만 Playbook을 실행할 수 있다. 실무에서는 환경별로 inventory 파일을 분리한다. `inventory/production.ini`, `inventory/staging.ini` 이런 식이다.

Dynamic Inventory라는 것도 있다. AWS EC2 인스턴스 목록을 태그 기반으로 자동으로 가져오는 플러그인이 있어서, 서버가 오토스케일링으로 늘었다 줄었다 하는 환경에서 inventory를 수동으로 관리하지 않아도 된다.

```yaml
# inventory/aws_ec2.yml
plugin: amazon.aws.aws_ec2
regions:
  - ap-northeast-2
filters:
  tag:Environment: production
keyed_groups:
  - key: tags.Role
    prefix: role
```

### Playbook

실행할 작업을 정의하는 YAML 파일이다. "어떤 서버에, 어떤 순서로, 뭘 할 것인가"를 기술한다.

```yaml
# playbooks/setup-web.yml
---
- name: 웹 서버 설정
  hosts: web
  become: true

  vars:
    nginx_version: "1.24"
    app_port: 8080

  tasks:
    - name: nginx 설치
      apt:
        name: "nginx={{ nginx_version }}.*"
        state: present
        update_cache: true

    - name: nginx 설정 파일 배포
      template:
        src: templates/nginx.conf.j2
        dest: /etc/nginx/sites-available/default
        owner: root
        group: root
        mode: "0644"
      notify: restart nginx

    - name: nginx 서비스 활성화
      systemd:
        name: nginx
        state: started
        enabled: true

  handlers:
    - name: restart nginx
      systemd:
        name: nginx
        state: restarted
```

`become: true`는 sudo 권한으로 실행한다는 뜻이다. `notify`와 `handlers`는 설정 파일이 변경됐을 때만 서비스를 재시작하는 구조다. 매번 재시작하면 서비스 다운타임이 생기니까, 변경이 있을 때만 재시작하는 게 맞다.

### Module

Ansible이 실제로 서버에서 실행하는 단위다. `apt`, `yum`, `copy`, `template`, `systemd`, `user` 같은 수백 개의 내장 모듈이 있다.

`shell`이나 `command` 모듈로 임의의 명령어를 실행할 수도 있지만, 가능하면 전용 모듈을 써야 한다. 전용 모듈은 멱등성을 보장하는데, `shell`은 매번 실행되기 때문이다.

```yaml
# 나쁜 예 - 멱등성 없음
- name: 유저 추가
  shell: useradd deploy

# 좋은 예 - 이미 있으면 건너뜀
- name: 유저 추가
  user:
    name: deploy
    state: present
    shell: /bin/bash
```

### Role

Playbook이 커지면 Role로 분리한다. 디렉토리 구조 자체가 규칙이다.

```
roles/
  nginx/
    tasks/
      main.yml       # 실행할 태스크
    handlers/
      main.yml       # 핸들러
    templates/
      nginx.conf.j2  # Jinja2 템플릿
    files/
      ssl.crt         # 정적 파일
    vars/
      main.yml       # 변수
    defaults/
      main.yml       # 기본값 (우선순위 가장 낮음)
    meta/
      main.yml       # 의존성
```

Role을 Playbook에서 사용하는 방법:

```yaml
---
- name: 웹 서버 구성
  hosts: web
  become: true

  roles:
    - common
    - nginx
    - role: app
      vars:
        app_port: 8080
```

Ansible Galaxy에서 커뮤니티가 만든 Role을 받아 쓸 수 있다. `ansible-galaxy install geerlingguy.docker` 같은 식이다. 다만 프로덕션에서 외부 Role을 그대로 쓰면 버전 업데이트 시 예상치 못한 변경이 생길 수 있어서, `requirements.yml`에 버전을 고정해야 한다.

```yaml
# requirements.yml
roles:
  - name: geerlingguy.docker
    version: "6.1.0"
  - name: geerlingguy.nginx
    version: "3.2.0"
```

## SSH 기반 에이전트리스 구조

Ansible의 실행 흐름을 좀 더 구체적으로 보면 이렇다:

1. 컨트롤 노드(Ansible이 설치된 머신)에서 Playbook 파싱
2. 각 태스크를 Python 스크립트로 변환
3. SSH로 대상 서버에 스크립트 전송
4. 대상 서버에서 Python 스크립트 실행
5. 결과를 JSON으로 컨트롤 노드에 반환

이 구조 때문에 생기는 실무 이슈가 있다.

**SSH 연결 수 문제**

서버가 많으면 SSH 연결을 동시에 여는 수가 문제가 된다. 기본값은 5개(`forks = 5`)인데, 서버 50대에 배포하면 한 번에 5대씩 처리해서 시간이 오래 걸린다.

```ini
# ansible.cfg
[defaults]
forks = 20

[ssh_connection]
pipelining = True
ssh_args = -o ControlMaster=auto -o ControlPersist=60s
```

`pipelining = True`는 SSH 세션 하나에서 여러 명령을 실행해서 연결 오버헤드를 줄인다. 다만 대상 서버의 `/etc/sudoers`에 `requiretty` 설정이 있으면 pipelining이 실패한다. CentOS 7 이하에서 이 문제를 겪는 경우가 있다.

**Pull 모드**

기본은 Push 모드(컨트롤 노드에서 서버로 밀어넣기)지만, `ansible-pull`이라는 Pull 모드도 있다. 서버가 직접 Git에서 Playbook을 받아서 실행하는 방식이다. 서버가 수백 대 이상이거나 네트워크 환경이 복잡할 때 쓴다.

## Terraform과의 차이

둘 다 IaC 도구지만 담당하는 영역이 다르다.

| 구분 | Terraform | Ansible |
|------|-----------|---------|
| 주요 역할 | 인프라 프로비저닝 | 서버 구성 관리 |
| 방식 | 선언적(declarative) | 절차적(procedural) |
| 상태 관리 | tfstate 파일로 상태 추적 | 상태 파일 없음 |
| 대상 | 클라우드 리소스(EC2, VPC, RDS 등) | 서버 내부(패키지, 설정, 서비스) |
| 에이전트 | 불필요 (API 호출) | 불필요 (SSH) |

Terraform은 "EC2 인스턴스 3대, RDS 1개, VPC 1개를 만들어라"를 담당한다. Ansible은 "그 EC2에 nginx 설치하고, 설정 파일 넣고, 서비스 시작해라"를 담당한다.

Terraform의 선언적 방식은 `terraform plan`으로 변경사항을 미리 확인할 수 있다. Ansible은 `--check` 모드가 있긴 하지만, 실제 실행과 결과가 다른 경우가 꽤 있다. 특히 `shell` 모듈이 섞여 있으면 `--check`로는 정확한 예측이 안 된다.

### Terraform + Ansible 조합 패턴

실무에서 가장 많이 쓰는 조합이다. 인프라 생성은 Terraform, 서버 설정은 Ansible로 나눈다.

**패턴 1: Terraform output을 Ansible inventory로 사용**

```hcl
# terraform/outputs.tf
output "web_server_ips" {
  value = aws_instance.web[*].private_ip
}
```

Terraform으로 서버를 만들고, output에서 IP를 뽑아서 Ansible의 Dynamic Inventory로 넘긴다.

```bash
# deploy.sh
cd terraform && terraform apply -auto-approve
WEB_IPS=$(terraform output -json web_server_ips | jq -r '.[]')

# Dynamic inventory 생성
echo "[web]" > ../ansible/inventory/hosts
for ip in $WEB_IPS; do
  echo "$ip" >> ../ansible/inventory/hosts
done

cd ../ansible && ansible-playbook -i inventory/hosts playbooks/setup-web.yml
```

**패턴 2: Terraform의 provisioner로 Ansible 실행**

```hcl
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.medium"

  provisioner "local-exec" {
    command = "ansible-playbook -i '${self.private_ip},' playbooks/setup-web.yml"
  }
}
```

`provisioner`는 Terraform에서 공식적으로 권장하지 않는 기능이다. 인스턴스 생성과 설정이 강하게 결합되어서, provisioner가 실패하면 인스턴스를 `taint`해서 다시 만들어야 한다. 패턴 1처럼 분리하는 게 낫다.

**패턴 3: Packer + Terraform (Ansible은 이미지 빌드 시)**

```json
// packer/web.pkr.hcl
source "amazon-ebs" "web" {
  ami_name      = "web-{{timestamp}}"
  instance_type = "t3.medium"
  source_ami    = "ami-base"
}

build {
  sources = ["source.amazon-ebs.web"]

  provisioner "ansible" {
    playbook_file = "../ansible/playbooks/setup-web.yml"
  }
}
```

Packer로 AMI를 만들 때 Ansible로 서버 설정을 미리 넣고, Terraform은 그 AMI로 인스턴스만 띄운다. 배포 속도가 빠르고, 모든 인스턴스가 동일한 상태를 보장한다. Immutable Infrastructure 패턴이다.

## 멱등성 문제와 해결

Ansible의 모듈 대부분은 멱등성을 보장한다. `apt` 모듈은 패키지가 이미 설치되어 있으면 건너뛴다. `template` 모듈은 파일 내용이 같으면 "changed"가 아닌 "ok"를 반환한다.

문제는 멱등성이 깨지는 상황이다.

### shell/command 모듈

가장 흔한 원인이다. 이 모듈은 Ansible이 결과를 판단할 수 없어서 매번 "changed"로 처리한다.

```yaml
# 문제 - 매번 실행됨
- name: 데이터베이스 초기화
  shell: /opt/app/init-db.sh

# 해결 - creates로 멱등성 확보
- name: 데이터베이스 초기화
  shell: /opt/app/init-db.sh
  args:
    creates: /opt/app/.db-initialized
```

`creates`는 해당 파일이 존재하면 태스크를 건너뛴다. 비슷하게 `removes`는 파일이 없으면 건너뛴다.

더 정확하게 하려면 `changed_when`을 쓴다.

```yaml
- name: 마이그레이션 실행
  shell: /opt/app/migrate.sh
  register: migration_result
  changed_when: "'No migrations to apply' not in migration_result.stdout"
```

### 파일 권한 문제

`copy`나 `template`로 파일을 배포할 때, 모드를 문자열로 지정하지 않으면 예상과 다르게 동작한다.

```yaml
# 문제 - 숫자 0644가 8진수가 아닌 10진수로 해석될 수 있음
- name: 설정 파일 배포
  copy:
    src: app.conf
    dest: /etc/app/app.conf
    mode: 0644

# 해결 - 문자열로 지정
- name: 설정 파일 배포
  copy:
    src: app.conf
    dest: /etc/app/app.conf
    mode: "0644"
```

YAML에서 `0644`는 파서에 따라 8진수 정수(`420`)로 해석되기도 한다. 문자열로 쓰면 이 문제를 피할 수 있다.

### 서비스 재시작 중복

handler를 쓰지 않고 매번 서비스를 재시작하는 패턴을 자주 본다.

```yaml
# 문제 - 설정 변경이 없어도 매번 재시작
- name: 설정 파일 배포
  template:
    src: app.conf.j2
    dest: /etc/app/app.conf

- name: 서비스 재시작
  systemd:
    name: app
    state: restarted

# 해결 - handler로 변경 시에만 재시작
- name: 설정 파일 배포
  template:
    src: app.conf.j2
    dest: /etc/app/app.conf
  notify: restart app

# handlers/main.yml
- name: restart app
  systemd:
    name: app
    state: restarted
```

### 패키지 버전 고정

`state: latest`를 쓰면 실행할 때마다 패키지가 업데이트된다. 같은 Playbook을 한 달 뒤에 실행하면 다른 버전이 설치될 수 있다.

```yaml
# 문제 - 실행 시점에 따라 다른 버전 설치
- name: nginx 설치
  apt:
    name: nginx
    state: latest

# 해결 - 버전 고정
- name: nginx 설치
  apt:
    name: nginx=1.24.0-1~jammy
    state: present
```

## 디렉토리 구조 실무 예시

프로젝트가 커지면 이런 구조로 관리한다.

```
ansible/
  ansible.cfg
  inventory/
    production/
      hosts.yml
      group_vars/
        all.yml
        web.yml
        db.yml
      host_vars/
        web-01.yml
    staging/
      hosts.yml
      group_vars/
        all.yml
  playbooks/
    setup-web.yml
    deploy-app.yml
    db-backup.yml
  roles/
    common/
    nginx/
    app/
    monitoring/
  requirements.yml
```

`group_vars`와 `host_vars`로 환경별, 서버별 변수를 분리한다. Playbook 자체는 환경에 독립적으로 작성하고, 변수만 바꿔서 staging과 production에서 같은 Playbook을 실행한다.

```bash
# staging에 배포
ansible-playbook -i inventory/staging/hosts.yml playbooks/deploy-app.yml

# production에 배포
ansible-playbook -i inventory/production/hosts.yml playbooks/deploy-app.yml
```

## 실무에서 주의할 점

**Ansible Vault로 비밀 관리**

비밀번호, API 키 같은 값을 평문으로 넣으면 안 된다. Ansible Vault로 암호화한다.

```bash
# 파일 암호화
ansible-vault encrypt inventory/production/group_vars/db.yml

# 암호화된 변수 사용
ansible-playbook playbooks/setup-db.yml --ask-vault-pass

# 비밀번호 파일 지정 (CI/CD에서 사용)
ansible-playbook playbooks/setup-db.yml --vault-password-file ~/.vault_pass
```

**태스크 실행 순서**

Ansible은 Playbook에 쓴 순서대로 태스크를 실행한다. 한 서버의 모든 태스크가 끝나야 다음 서버로 넘어가는 게 아니라, 한 태스크를 모든 서버에서 실행한 뒤 다음 태스크로 넘어간다. 이 동작 방식을 모르면 "왜 1번 서버에서 nginx 설치와 설정이 연속으로 안 되지?"라고 혼란스러울 수 있는데, 기본 동작이 그렇다. `serial` 키워드로 한 번에 처리할 서버 수를 제한하면 롤링 배포가 가능하다.

```yaml
- name: 롤링 배포
  hosts: web
  serial: 2  # 한 번에 2대씩
  become: true

  tasks:
    - name: 로드밸런서에서 제거
      uri:
        url: "http://lb.internal/api/deregister/{{ inventory_hostname }}"
        method: POST

    - name: 앱 배포
      # ...

    - name: 로드밸런서에 재등록
      uri:
        url: "http://lb.internal/api/register/{{ inventory_hostname }}"
        method: POST
```

**디버깅**

실행이 실패하면 `-vvv` 옵션으로 상세 로그를 볼 수 있다. SSH 연결 문제인지, 모듈 실행 문제인지 구분이 된다.

```bash
ansible-playbook playbooks/setup-web.yml -vvv

# 특정 태스크만 실행
ansible-playbook playbooks/setup-web.yml --start-at-task="nginx 설치"

# 특정 서버만 대상
ansible-playbook playbooks/setup-web.yml --limit web-01.example.com
```
