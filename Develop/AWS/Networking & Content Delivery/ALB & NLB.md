# AWS Application Load Balancer(ALB) & Network Load Balancer(NLB)

## ✨ 로드 밸런서란?
로드 밸런서는 **여러 서버로 트래픽을 분산시켜 성능을 최적화하고 가용성을 높이는 역할**을 합니다.  
AWS에서는 주로 **Application Load Balancer(ALB)**와 **Network Load Balancer(NLB)**를 사용합니다.

---

## 🚀 AWS 로드 밸런서 종류
AWS에서 제공하는 로드 밸런서의 종류는 다음과 같습니다.

| 로드 밸런서 | 설명 |
|------------|------|
| **ALB (Application Load Balancer)** | **애플리케이션 계층(7계층)에서 동작**하며, HTTP/HTTPS 요청을 처리 |
| **NLB (Network Load Balancer)** | **전송 계층(4계층)에서 동작**하며, TCP/UDP 트래픽을 빠르게 분산 |
| **CLB (Classic Load Balancer)** | 기존 로드 밸런서로, 현재는 ALB/NLB 사용이 권장됨 |

---

## 👉🏻 ALB(Application Load Balancer)
**ALB는 HTTP/HTTPS 트래픽을 처리하는 7계층 로드 밸런서**입니다.

### 🔹 ALB 주요 특징
- 경로 기반 및 호스트 기반 라우팅 가능
- SSL/TLS 종료 지원
- WebSocket 및 HTTP/2 지원
- 가중치 기반 라우팅 가능

### 🔹 ALB 설정 방법
1. AWS 콘솔에서 **EC2 서비스**로 이동 후 `로드 밸런서 생성` 클릭
2. `Application Load Balancer` 선택
3. 리스너(Listener) 설정 (예: HTTP:80, HTTPS:443)
4. 서브넷 및 보안 그룹 설정
5. 대상 그룹(Target Group) 생성 후 EC2 인스턴스 등록
6. ALB와 대상 그룹 연결 후 생성 완료

### 🔹 ALB 리스너 규칙 예제
- `/api/*` 요청은 `API 서버 그룹`으로 전달
- `/admin/*` 요청은 `관리자 서버 그룹`으로 전달

---

## 👉🏻 NLB(Network Load Balancer)
**NLB는 TCP 및 UDP 트래픽을 처리하는 4계층 로드 밸런서**입니다.

### 🔹 NLB 주요 특징
- 초당 수백만 개의 요청 처리 가능
- 낮은 지연 시간 및 높은 성능 제공
- 고정 IP 주소 할당 가능
- TLS 패스스루(Pass-through) 지원

### 🔹 NLB 설정 방법
1. AWS 콘솔에서 **EC2 서비스**로 이동 후 `로드 밸런서 생성` 클릭
2. `Network Load Balancer` 선택
3. 리스너(Listener) 설정 (예: TCP:443)
4. 서브넷 및 고정 IP 주소 설정
5. 대상 그룹(Target Group) 생성 후 EC2 인스턴스 등록
6. NLB와 대상 그룹 연결 후 생성 완료

---

## 🎯 ALB vs NLB 비교

| 기능 | ALB | NLB |
|------|----|----|
| **계층** | 7계층 (HTTP/HTTPS) | 4계층 (TCP/UDP) |
| **라우팅** | 경로 기반, 호스트 기반 라우팅 지원 | TCP/UDP 포트 기반 라우팅 |
| **TLS 처리** | ALB에서 종료 가능 | 패스스루(Pass-through) 지원 |
| **IP 주소** | 변경될 수 있음 | 고정 IP 가능 |
| **성능** | 대규모 트래픽 처리 가능 | 초당 수백만 개의 요청 처리 가능 |
| **사용 사례** | 웹 애플리케이션, API 서버 | 게임 서버, IoT, 금융 서비스 |

---

## 🛠️ Terraform을 이용한 ALB/NLB 설정 예제

### 📝 ALB 설정 예제
```hcl
resource "aws_lb" "example_alb" {
  name               = "example-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets           = aws_subnet.public[*].id
}

resource "aws_lb_target_group" "example_tg" {
  name     = "example-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.example_alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.example_tg.arn
  }
}
```

---

### 📝 NLB 설정 예제
```hcl
resource "aws_lb" "example_nlb" {
  name               = "example-nlb"
  internal           = false
  load_balancer_type = "network"
  subnets           = aws_subnet.public[*].id
}

resource "aws_lb_target_group" "example_tg" {
  name     = "example-tg"
  port     = 443
  protocol = "TCP"
  vpc_id   = aws_vpc.main.id
}

resource "aws_lb_listener" "tcp" {
  load_balancer_arn = aws_lb.example_nlb.arn
  port              = 443
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.example_tg.arn
  }
}
```

