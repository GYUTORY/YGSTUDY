---
title: YGSTUDY
hide:
  - toc
  - navigation
---

<div class="yg-home" markdown="0">

<section class="yg-hero">
  <div class="yg-hero-kicker">BACKEND ENGINEER'S NOTES</div>
  <h1 class="yg-hero-title">SYSTEMS, INFRASTRUCTURE<br>& EVERYTHING IN BETWEEN</h1>
  <p class="yg-hero-sub">Kang Young Gyu · Backend Engineer</p>
</section>

<nav class="yg-tabs">
  <a href="#featured" class="active">Featured</a>
  <a href="#categories">Categories</a>
  <a href="#projects">Projects</a>
</nav>

<section id="featured" class="yg-grid">

  <a class="yg-card" href="DevOps/Kubernetes/Kubernetes/">
    <div class="yg-thumb yg-thumb-k8s">K8s</div>
    <div class="yg-card-body">
      <div class="yg-meta">DEVOPS · INFRASTRUCTURE</div>
      <h3>Kubernetes 운영의 핵심 패턴</h3>
      <p>실제 프로덕션 환경에서 마주친 K8s 운영 이슈와 해결 방법을 정리합니다.</p>
    </div>
  </a>

  <a class="yg-card" href="DataBase/NoSQL/Redis/Redis_Cache_Strategy/">
    <div class="yg-thumb yg-thumb-redis">REDIS</div>
    <div class="yg-card-body">
      <div class="yg-meta">DATABASE · CACHING</div>
      <h3>Redis 캐시 전략 비교</h3>
      <p>Cache-Aside, Write-Through, Write-Behind 패턴의 차이와 선택 기준.</p>
    </div>
  </a>

  <a class="yg-card" href="Security/Zero_Trust_Architecture/">
    <div class="yg-thumb yg-thumb-sec">SECURITY</div>
    <div class="yg-card-body">
      <div class="yg-meta">SECURITY · ARCHITECTURE</div>
      <h3>Zero Trust 보안 모델</h3>
      <p>경계 기반 보안의 한계와 Zero Trust 아키텍처로의 전환 사례.</p>
    </div>
  </a>

  <a class="yg-card" href="GCP/Data/Big_Query/">
    <div class="yg-thumb yg-thumb-bq">BIGQUERY</div>
    <div class="yg-card-body">
      <div class="yg-meta">GCP · DATA</div>
      <h3>BigQuery로 로그 분석하기</h3>
      <p>GCP BigQuery를 활용한 대규모 로그 분석 파이프라인 구축기.</p>
    </div>
  </a>

  <a class="yg-card" href="AI/Claude_Code/Claude_Code_Worktree/">
    <div class="yg-thumb yg-thumb-ai">AI</div>
    <div class="yg-card-body">
      <div class="yg-meta">AI · TOOLING</div>
      <h3>Claude Code 워크트리 활용</h3>
      <p>병렬 작업을 위한 git worktree와 Claude Code의 시너지.</p>
    </div>
  </a>

  <a class="yg-card" href="DevSecOps/Dev_Sec_Ops/">
    <div class="yg-thumb yg-thumb-devops">DEVSECOPS</div>
    <div class="yg-card-body">
      <div class="yg-meta">DEVOPS · SECURITY</div>
      <h3>DevSecOps 도입 가이드</h3>
      <p>개발 파이프라인에 보안을 자연스럽게 녹여내는 방법.</p>
    </div>
  </a>

</section>

<section id="categories" class="yg-cats">
  <h2 class="yg-section-title">CATEGORIES</h2>
  <div class="yg-cats-grid">
    <a class="yg-cat" data-cat="language" href="Language/Java/Java 기본 개념/String 불변 객체/"><span></span>Language</a>
    <a class="yg-cat" data-cat="framework" href="Framework/Java/Spring/Bean/"><span></span>Framework</a>
    <a class="yg-cat" data-cat="arch" href="Application Architecture/Clean_Architecture/"><span></span>Architecture</a>
    <a class="yg-cat" data-cat="backend" href="Backend/API/API_Design_Patterns/"><span></span>Backend</a>
    <a class="yg-cat" data-cat="database" href="DataBase/NoSQL/NoSQL/"><span></span>Database</a>
    <a class="yg-cat" data-cat="aws" href="AWS/Compute/Auto_Scaling/"><span></span>AWS</a>
    <a class="yg-cat" data-cat="devops" href="DevOps/Kubernetes/Kubernetes/"><span></span>DevOps</a>
    <a class="yg-cat" data-cat="linux" href="Linux/기본_명령어/기본_명령어/"><span></span>Linux</a>
    <a class="yg-cat" data-cat="webserver" href="WebServer/Nginx/Definition/"><span></span>Web Server</a>
    <a class="yg-cat" data-cat="ai" href="AI/Claude_Code/Claude_Code/"><span></span>AI</a>
    <a class="yg-cat" data-cat="network" href="Network/Protocol/Protocol/"><span></span>Network</a>
    <a class="yg-cat" data-cat="security" href="Security/HTTPS_and_TLS/"><span></span>Security</a>
  </div>
</section>

<section id="projects" class="yg-projects">
  <h2 class="yg-section-title">PROJECTS</h2>
  <div class="yg-proj-grid">
    <a class="yg-proj" href="http://gyutory.co.kr/momo" target="_blank">
      <img src="assets/images/momo_assistant.png" alt="MOMO Assistant">
      <div class="yg-proj-body">
        <h3>MOMO Assistant</h3>
        <p>페르소나 기반 AI 어시스턴트. 코딩 멘토, 번역가, 자소서 첨삭 등 역할별 전문 대화 지원.</p>
      </div>
    </a>
    <a class="yg-proj" href="http://gyutory.co.kr/momo_editor/" target="_blank">
      <img src="assets/images/momo_editor.png" alt="MOMO Editor">
      <div class="yg-proj-body">
        <h3>MOMO Editor</h3>
        <p>동영상 편집 데스크톱 애플리케이션. 타임라인 기반 편집, 미디어 라이브러리, 실시간 프리뷰 지원.</p>
      </div>
    </a>
    <div class="yg-proj wip">
      <img src="assets/images/trip_planner.png" alt="AI Trip Planner">
      <div class="yg-proj-body">
        <h3>AI Trip Planner</h3>
        <p>AI 기반 여행 일정 생성 앱. 도시를 선택하면 맛집, 관광지, 카페 일정을 자동으로 구성.</p>
      </div>
    </div>
  </div>
</section>

</div>
