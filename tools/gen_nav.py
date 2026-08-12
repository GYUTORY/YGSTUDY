#!/usr/bin/env python3
"""YGSTUDY .pages 전면 재생성.

원칙
  1. 파일은 절대 옮기지 않는다 (URL 보존)
  2. 유령 항목(디스크에 없는 nav 엔트리) 제거
  3. 고아 문서(디스크에 있는데 nav에 없는 것) 복구
  4. 상위 디렉터리가 이미 말하고 있는 접두사는 라벨에서 제거
  5. 부제(— 뒤)는 사이드바 라벨에서 떼어낸다 (문서 제목 자체는 그대로)
  6. 문서 1개짜리 디렉터리는 부모로 끌어올려 펼침 단계를 없앤다
  7. 기존 큐레이션 순서는 보존

사용:  python3 gen_nav.py [--write]
"""
import os, re, sys

ROOT = 'Develop'
SKIP_DIRS = {'assets', 'javascripts', 'stylesheets', '.omc', 'etc', 'images',
             'example', 'snippets', 'img'}
WRITE = '--write' in sys.argv

# 사이드바 라벨 길이 목표 (넘으면 부제를 떼어낸다)
LABEL_SOFT_MAX = 20

# 사이드바 최대 노출 깊이 (ROOT = 0 기준).
# depth > MAX_SIDEBAR_DEPTH 인 디렉터리는 index.md 하나만 .pages 에 기록한다.
# 허브 페이지(index.md)는 section_index.py 가 빌드 시점에 자동 생성한다.
# 예) Develop/Cloud/AWS/Compute = depth 3 > 2 → index.md 만 노출
MAX_SIDEBAR_DEPTH = 2

# 이 디렉터리의 .pages 는 수동으로 관리한다. gen_nav.py 가 덮어쓰지 않는다.
# Develop/.pages 는 이미 루트 스킵 로직으로 보호되므로 여기엔 포함하지 않는다.
MANUAL_DIRS = {
    'Develop/AI',   # AI 섹션은 6-그룹 구조로 수동 큐레이션
}


# ---------------------------------------------------------------- 제목 읽기

def doc_title(path):
    """MkDocs가 실제로 쓰는 제목: frontmatter title > H1 > 파일명."""
    try:
        text = open(path, encoding='utf-8').read()
    except OSError:
        return os.path.basename(path)[:-3]
    m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    if m:
        mm = re.search(r'^title:\s*(.+)$', m.group(1), re.M)
        if mm:
            return mm.group(1).strip().strip('"\'')
    hm = re.search(r'^#\s+(.+)$', text, re.M)
    if hm:
        return hm.group(1).strip()
    return os.path.basename(path)[:-3].replace('_', ' ')


# ---------------------------------------------------------------- 라벨 정리

EXTRA_PREFIXES = {
    'Go': ['Go'], 'Rust': ['Rust'], 'Python': ['Python'], 'Java': ['Java'],
    'Kotlin': ['Kotlin'], 'JavaScript': ['JavaScript', 'JS'],
    'TypeScript': ['TypeScript', 'TS'], 'Node': ['Node.js', 'Node'],
    'Claude_Code': ['Claude Code'], 'Claude': ['Claude'],
    'Cursor': ['Cursor'], 'Gemini': ['Gemini'], 'Grok': ['Grok'],
    'AWS': ['AWS', 'Amazon'], 'GCP': ['GCP', 'Google Cloud'],
    'Nginx': ['Nginx'], 'Caddy': ['Caddy'], 'Apache': ['Apache'],
    'Kubernetes': ['Kubernetes', 'K8s'], 'MSA': ['MSA'], 'Docker': ['Docker'],
    'Linux': ['Linux'], 'DevOps': ['DevOps'], 'NestJS': ['NestJS'],
    'Redis': ['Redis'], 'MongoDB': ['MongoDB'],
    'OMO': ['Online-Merge-Offline', 'OMO'],
    # 'Spring Boot X'에서 'Spring'만 떼면 'Boot X'가 되어 뜻이 깨진다
    'Spring': ['Spring Boot', 'Spring'],
}

# ---- 형제 묶기 ----------------------------------------------------------
# 같은 이름으로 시작하는 형제가 여럿이면 접기 가능한 그룹으로 묶는다.
# (AWS/Containers의 'ECS ...' 29개 같은 경우)
GROUP_MIN = 3

# 그룹 이름이 될 수 없는 말 — 제품명이 아니라 벤더/범용어라 묶으면 뜻이 깨진다
GROUP_BLOCK = {'cloud', 'aws', 'amazon', 'google', 'azure', 'microsoft',
               'apache', 'the', 'a', 'an'}

# 이 말로 시작하게 잘리면 라벨이 문장처럼 깨진다 -> 원래 라벨을 유지
BAD_HEAD = re.compile(
    r'^(vs|and|or|to|for|with|over|under|into|from|by|at|as|on|in|및|와|과)\b',
    re.I)

GROUP_NAME_OK = re.compile(r'^[A-Za-z][A-Za-z0-9.+#/-]*$')

# 최상위 섹션 순서 — 언어/프레임워크 → 백엔드 → 데이터 → 인프라 → 클라우드 → 기타
# 2026-08-05 재편성: AWS·GCP -> Cloud, Linux·Git·Infra -> DevOps, DataRepresentation -> DataBase
TOP_ORDER = [
    'index.md', '_hub',
    'Language', 'Framework', 'AI',
    'Backend', 'Architecture',
    'Cloud', 'DevOps',
    'Network', 'DataBase', 'Algorithm',
    'Security', 'WebServer', 'OS', 'Frontend',
    'tags.md',
]

# 특정 디렉터리의 자식 순서 지정 (여기 없는 항목은 뒤에 알파벳순)
ORDER_OVERRIDE = {
    # 기초를 실전보다 앞에
    # README.md는 MkDocs가 섹션 index로 매핑하므로 맨 앞에 와야 한다
    'Develop/Framework/Node': ['README.md', '함수형 프로그래밍.md',
                               'Functional_Programming.md'],
    # 개요격 문서를 맨 앞으로
    'Develop/Architecture/MSA': ['Microservices_Architecture.md'],
    'Develop/Architecture/OMO': ['Online_Merge_Offline.md', 'OMO_운영_실무.md'],
    'Develop/AI': [
        'Concepts', 'Claude', 'Claude_Code', 'Cursor', 'GitHub_Copilot',
        'Codex', 'Gemini', 'GPT', 'Grok', 'Qwen', 'DeepSeek', 'Ollama',
        'MCP', 'CodeSight', 'Clawsweeper', 'GBrain', 'OMO',
    ],
}


# 특정 파일에 대한 라벨 직접 지정 (자동 단축 규칙으로 20자 이하로 줄이기 어려운 경우)
LABEL_OVERRIDE = {
    'Develop/DevOps/Kubernetes/Docker/Jenkins와 Docker로 Git 자동 배포 시스템 구축하기.md': 'Jenkins CI/CD 구축',
    'Develop/Framework/Node/아키텍처/Event_Driven_Architecture_with_AWS.md': 'Event-Driven with AWS',
    'Develop/Language/JavaScript/09_ES6_및_고급문법/Encode_URI_Component_Decode_URI_Component.md': 'encodeURIComponent',
    'Develop/Language/JavaScript/04_심화_JavaScript/Symbol_Weak_Ref.md': 'WeakRef 심화',
    'Develop/Language/JavaScript/09_ES6_및_고급문법/Base64_Encode_URI_Component_URL_Search_Params.md': 'URL 인코딩 비교',
    'Develop/Framework/Node/모듈 시스템/npm.md': 'npm & package.json',
    'Develop/Language/JavaScript/04_심화_JavaScript/JavaScript에서 2진수, 10진수, 16진수 다루기.md': '2진수·10진수·16진수',
    'Develop/Language/JavaScript/01_기본_JavaScript/Closure/Closure_Practical_Patterns.md': '클로저 설계 패턴',
    'Develop/Cloud/AWS/Compute/EC2_Capacity_Reservation.md': 'On-Demand Capacity 예약',
    'Develop/Cloud/AWS/Compute/EC2_Instance_Metadata_Service.md': 'Instance Metadata',
    'Develop/Cloud/AWS/Containers/ECS_Task_Failure_Troubleshooting.md': 'stoppedReason 디버깅',
    'Develop/Cloud/AWS/Database/RDS_Performance_Insights.md': 'RDS Performance 진단',
    'Develop/Cloud/AWS/Application_Integration/SNS_SQS_Lambda_통합_메시지_파이프라인.md': 'SNS·SQS·Lambda 파이프라인',
    'Develop/Cloud/AWS/Load_Balancer/ALB.md': 'ALB',
    'Develop/Cloud/AWS/Load_Balancer/ALB vs API Gateway.md': 'ALB vs API Gateway 비교',
    'Develop/Cloud/AWS/Load_Balancer/GWLB.md': 'Gateway Load Balancer',
    'Develop/Cloud/AWS/Containers/ECS_DB_Connection_Pool_관리.md': 'Task DB 커넥션 풀 관리',
    'Develop/Cloud/AWS/Containers/ECS_Infrastructure_Task_Relationship.md': 'Task Definition 관계',
    'Develop/Cloud/AWS/Containers/ECS_Task_Scale_Out_부작용.md': 'Task Scale Out 부작용',
    'Develop/Cloud/AWS/Containers/App_Mesh.md': 'App Mesh',
    'Develop/AI/Concepts/Lang_Chain_vs_SDK.md': 'LangChain vs 순수 SDK',
    'Develop/AI/Concepts/RAG_Evaluation.md': 'RAG 품질 평가',
    'Develop/Backend/Messaging/Kafka_Consumer_Group_Rebalancing.md': 'Consumer Group 재조정',
    'Develop/Backend/Authentication/O_Auth2_OIDC_Flows.md': 'OAuth·OIDC Flow 심화',
    'Develop/Backend/Messaging/Kafka_Exactly_Once_Semantics.md': 'Kafka EOS',
    'Develop/Backend/Resilience/Rate_Limiting_and_Bulkhead.md': 'Rate Limiting·Bulkhead',
    'Develop/Language/Java/컬렉션 및 데이터 처리/Serialization_Deserialization.md': '직렬화·역직렬화',
    'Develop/Language/Java/자바 디자인 패턴 및 원칙/단일 책임 원칙.md': '단일 책임 원칙',
    'Develop/Language/Java/멀티스레딩 및 동시성/Java_Util_Concurrent_Sync_Utilities.md': 'concurrent 유틸리티',
    'Develop/Network/7 Layer/Network Layer/MTU_MSS_PMTUD.md': 'MTU·MSS 심화',
    'Develop/DevOps/Git/Git_Worktree_Submodule_LFS.md': 'Worktree·Submodule·LFS',
    'Develop/Language/TypeScript/타입 유틸리티/module과 moduleResolution.md': 'moduleResolution',
    'Develop/Language/TypeScript/TypeScript 기본 개념/Export_Default와_Default_New.md': 'export default 심화',
    'Develop/Language/TypeScript/프로젝트 설정 및 컴파일러/tsc-alias와 workspace 함께 사용하기.md': 'tsc-alias·workspace',
    'Develop/DataBase/DataRepresentation/엔디언과 2의 보수, IEEE 754 부동소수점.md': '엔디언·부동소수점',
    'Develop/Architecture/MSA/Expand_Migrate_Contract.md': 'EMC 패턴',
    'Develop/Architecture/Design Pattern/Abstract_Factory_Pattern.md': '추상 팩토리 패턴',
    'Develop/Framework/Node/API/Rate_Limiting.md': 'Rate Limiting·Bulkhead',
    'Develop/Backend/Standards/Instant_vs_Local_Date_Time.md': 'Instant vs LocalDT',
    'Develop/Language/Java/객체지향 프로그래밍 (OOP)/interface/Abstract Class__vs__Interface.md': 'Abstract vs Interface',
    'Develop/Framework/Node/Nodejs의 구조 및 작동 원리/Cluster와 Multi Thread.md': 'Cluster vs Worker',
    'Develop/Language/JavaScript/05_이벤트_루프_비동기/Async_Await_and_Promise.md': 'Async/Await & Promise',
    'Develop/DataBase/RDBMS/pt_online_schema_change.md': 'Online Schema Change',
    'Develop/Framework/Node/모듈 시스템/Pnpm_Lock_and_Catalog.md': 'pnpm-lock·catalog',
    'Develop/Security/Zero_Trust_Architecture.md': 'Zero Trust',
    'Develop/Algorithm/Graph_Traversal.md': '그래프 탐색 (DFS/BFS)',
    'Develop/DevOps/Kubernetes/Docker/Docker_Compose_Port_Forwarding.md': 'Port Forwarding',
    'Develop/_hub/JavaScript_TypeScript.md': 'JS & TypeScript',
    'Develop/Network/Security/Zero_Trust_CICD_Pipeline.md': 'CI/CD Zero Trust',
}

# 손으로 짠 묶음.
# 자동 규칙은 crypto와 fs가 '코어 모듈'이라는 걸 알 수 없다. 낱장 문서가
# 20개 넘게 평평하게 늘어서는 곳만 여기서 직접 묶는다.
# 형식:  경로 -> [(묶음 이름, [(라벨, 상대경로), ...]), ...]
MANUAL_GROUPS = {
    'Develop/Language/Go': [
        ('동시성', [
            ('동시성 (고루틴·채널)', 'Go_Concurrency.md'),
            ('고급 동시성 패턴', 'Go_Concurrency_Patterns.md'),
            ('sync 패키지 심화', 'Go_Sync_Primitives.md'),
            ('context 패키지', 'Go_Context.md'),
            ('Context 심화', 'Go_Context_Advanced.md'),
        ]),
        ('타입 시스템', [
            ('인터페이스와 타입 시스템', 'Go_Interface.md'),
            ('제네릭', 'Go_Generics.md'),
            ('에러 처리', 'Go_Error_Handling.md'),
        ]),
        ('런타임 내부', [
            ('메모리 모델 심화', 'Go_Memory_Model.md'),
            ('런타임 스케줄러 내부 구조', 'Go_Scheduler_Internals.md'),
            ('슬라이스와 맵 내부 구조', 'Go_Slice_Map.md'),
        ]),
    ],
    'Develop/Cloud/AWS/Security': [
        ('자격 증명과 권한', [
            ('IAM', 'IAM.md'),
            ('IAM 권한 관리 심화', 'IAM_Permission_Management_Deep_Dive.md'),
            ('Cognito', 'Cognito.md'),
            ('Cognito 심화', 'Cognito_Deep_Dive.md'),
        ]),
        ('키와 시크릿', [
            ('KMS', 'KMS.md'),
            ('Secrets Manager', 'Secrets_Manager.md'),
            ('Secrets Manager vs KMS', 'Secrets_Manager_vs_KMS.md'),
            ('ACM', 'ACM.md'),
        ]),
        ('위협 탐지와 방어', [
            ('Shield', 'Shield.md'),
            ('GuardDuty', 'Guard_Duty.md'),
            ('Inspector', 'Inspector.md'),
            ('Security Hub', 'Security_Hub.md'),
        ]),
    ],
    'Develop/WebServer/Caddy': [
        ('설정', [
            ('Caddyfile 문법 심화', 'Caddyfile_Syntax.md'),
            ('Admin API와 JSON 설정', 'Admin_API.md'),
            ('정적 파일 서빙', 'Static_File_Serving.md'),
        ]),
        ('프록시와 라우팅', [
            ('reverse_proxy 디렉티브 심화', 'Reverse_Proxy.md'),
            ('서브도메인 라우팅과 와일드카드 인증서', 'Subdomain_Routing.md'),
            ('헤더 처리와 CORS', 'Headers_CORS.md'),
        ]),
        ('보안', [
            ('SSL/TLS 심화', 'SSL_TLS.md'),
            ('인증 처리', 'Authentication.md'),
            ('Rate Limiting', 'Rate_Limiting.md'),
        ]),
        ('운영', [
            ('로깅과 관찰성', 'Logging_Monitoring.md'),
            ('커스텀 xcaddy 이미지 CI/CD',
             'Docker_Caddy_Image_CICD_Pipeline.md'),
            ('Nginx에서 Caddy로 마이그레이션', 'Nginx_To_Caddy_Migration.md'),
        ]),
    ],
    'Develop/AI/Claude_Code': [
        ('기능', [
            ('모델 선택', 'Claude_Code_Model.md'),
            ('Agent 시스템', 'Claude_Code_Agent.md'),
            ('Memory 시스템', 'Claude_Code_Memory.md'),
            ('스킬과 룰 시스템', 'Claude_Code_Skill_Rule.md'),
            ('플랜모드', 'Claude_Code_Plan_Mode.md'),
            ('Auto Mode', 'Claude_Code_Auto_Mode.md'),
        ]),
        ('병렬 작업', [
            ('오케스트레이션', 'Claude_Code_Orchestration.md'),
            ('OMC', 'Claude_Code_OMC.md'),
            ('Worktree', 'Claude_Code_Worktree.md'),
            ('Worktree 병렬 스크립트', 'Claude_Code_Worktree_Script.md'),
            ('롱잡 운영', 'Claude_Code_Long_Job.md'),
        ]),
        ('실무', [
            ('개발 루틴', 'Claude_Code_Routine.md'),
            ('실전 팁', 'Claude_Code_Tips.md'),
            ('웹취약점 대응', 'Claude_Code_Web_Vulnerability.md'),
            ('Ultra Review', 'Claude_Code_Ultra.md'),
            ('트러블슈팅', 'Claude_Code_Troubleshooting.md'),
        ]),
        ('내부 동작', [
            ('하네스', 'Claude_Code_Harness.md'),
            ('Fable 5 릴리스 정리', 'Claude_Code_Fable_5.md'),
        ]),
    ],
    'Develop/WebServer/Nginx': [
        ('설정 구조', [
            ('Virtual Host 설정', 'Virtual_Host_설정.md'),
            ('location 매칭과 설정 구조', 'location_매칭과_설정_구조.md'),
            ('location 매칭 우선순위 심화', 'Location_Matching_Deep_Dive.md'),
            ('map 지시어 심화', 'Nginx_Map_Directive.md'),
            ('URL Rewrite와 Redirect', 'URL_Rewrite_and_Redirect.md'),
        ]),
        ('프록시', [
            ('리버스 프록시 & 로드밸런싱',
             'Reverse_Proxy_and_Load_Balancing.md'),
            ('WebSocket 프록시', 'Web_Socket_Proxy.md'),
            ('Stream 모듈 (TCP/UDP)', 'Stream_Module.md'),
            ('FastCGI & PHP-FPM', 'Fast_CGI_PHP_FPM.md'),
        ]),
        ('보안', [
            ('SSL/TLS 설정', 'SSL_TLS_설정.md'),
            ('보안 설정', '보안_설정.md'),
            ('CORS', 'CORS.md'),
            ('Rate Limiting', 'Rate_Limiting.md'),
        ]),
        ('운영', [
            ('성능 튜닝', '성능_튜닝.md'),
            ('로그 설정과 모니터링', '로그_설정과_모니터링.md'),
            ('트러블슈팅', '트러블슈팅.md'),
        ]),
    ],
    'Develop/Cloud/AWS/Network': [
        ('VPC 네트워킹', [
            ('Private·Public Subnet',
             'Private_Subnet__vs__Public_Subnet.md'),
            ('라우팅 테이블', 'Route_Table.md'),
            ('ENI', 'Elastic_Network_Interface.md'),
            ('NAT Gateway', 'Nat_Gateway.md'),
            ('SG vs NACLs', 'Security_Groups_vs_NACLs.md'),
            ('네트워크 구성요소 비유로 이해하기',
             'AWS_Network_Components_Analogy.md'),
        ]),
        ('연결', [
            ('Transit Gateway', 'Transit_Gateway.md'),
            ('PrivateLink', 'PrivateLink.md'),
            ('Direct Connect', 'Direct_Connect.md'),
            ('Site-to-Site VPN', 'Site_to_Site_VPN.md'),
        ]),
        ('엣지와 배포', [
            ('CloudFront', 'CDN.md'),
            ('CloudFront 캐시 무효화 정책', 'CDN 캐시 무효화 정책.md'),
            ('Global Accelerator', 'Global_Accelerator.md'),
            ('Route 53', 'Route 53.md'),
            ('API Gateway', 'API_Gateway.md'),
        ]),
        ('S3와 요청 흐름', [
            ('S3', 'S3.md'),
            ('S3 정적 웹사이트 호스팅', 'S3_Static_Website_Hosting.md'),
            ('ALB → ECS → S3 요청 흐름', 'ALB_ECS_S3_Request_Flow.md'),
        ]),
    ],
    'Develop/Framework/Java/Spring': [
        ('DI와 Bean', [
            ('Bean 개념과 사용법', 'Bean.md'),
            ('Bean 심화', 'Spring_Bean_심화.md'),
            ('AOP & 트랜잭션 심화', 'AOP_트랜잭션.md'),
            ('Profiles 심화', 'Spring Boot Profiles.md'),
        ]),
        ('웹 계층', [
            ('MVC와 REST API 설계', 'Spring_MVC_REST_API.md'),
            ('WebFlux', 'Spring_WebFlux.md'),
            ('SSE', 'Spring_SSE.md'),
            ('Security', 'Spring_Security.md'),
            ('Rate Limiting 구현', 'Rate_Limiting.md'),
        ]),
        ('데이터 접근', [
            ('Data JPA', 'Spring_Data_JPA.md'),
            ('Data JPA 심화', 'Spring_Data_JPA_Advanced.md'),
            ('JPA @Lock 어노테이션 비교', 'JPA_Lock_Annotations.md'),
            ('낙관적 락 재시도 처리', 'Optimistic_Lock_Retry_Pattern.md'),
            ('Cache', 'Spring_Cache.md'),
        ]),
        ('배치와 분산', [
            ('Batch', 'Spring_Batch.md'),
            ('Cloud MSA', 'Spring_Cloud.md'),
        ]),
        ('로깅', [
            ('Spring 로깅', 'Spring_Logging.md'),
            ('SLF4J', 'SLF4J.md'),
        ]),
        ('Lombok', [
            ('Project Lombok', 'Lombok.md'),
            ('Lombok 심화', 'Lombok_Deep_Dive.md'),
            ('보조 어노테이션', 'Lombok_Minor_Annotations.md'),
        ]),
        ('빌드와 마이그레이션', [
            ('Gradle vs Maven', 'Gradle__vs__Maven.md'),
            ('Boot 2.x vs 3.x 의사결정', 'Boot2.0__vs__Boot3.0.md'),
            ('Boot 2.x→3.x 마이그레이션',
             'Spring_Boot_Migration_2_to_3.md'),
        ]),
    ],
    'Develop/Architecture/MSA': [
        ('설계와 전환', [
            ('서비스 분해 및 도메인 설계', '서비스_분해_및_도메인_설계.md'),
            ('모놀리스 → MSA 마이그레이션', '모놀리스_to_MSA_마이그레이션.md'),
            ('모노레포 vs 멀티레포', '멀티 레포.md'),
            ('Oracle에서의 MSA', 'Oracle_MSA.md'),
            ('클라우드 선택 전략', 'MSA_클라우드_선택_전략.md'),
        ]),
        ('통신', [
            ('서버 간 통신 방식', '서버 간 통신 방식 정리.md'),
            ('서비스 디스커버리와 API Gateway',
             '서비스_디스커버리_및_API_Gateway.md'),
            ('서비스 메시와 사이드카 패턴', '서비스_메시_및_사이드카_패턴.md'),
            ('메시지 큐 및 분산 락', '메시지_큐_및_분산_락.md'),
            ('API 버전 관리', 'API_버전_관리.md'),
            ('AWS VPC 네트워크 설계', 'MSA_VPC_Network_Design.md'),
        ]),
        ('데이터 일관성', [
            ('데이터 관리 패턴', '데이터_관리_패턴.md'),
            ('Saga 패턴 및 분산 트랜잭션', 'Saga_패턴_및_분산_트랜잭션.md'),
            ('Transactional Outbox', '트랜잭셔널_아웃박스_패턴.md'),
            ('이벤트 소싱과 CQRS', '이벤트_소싱_및_CQRS.md'),
            ('분산 캐싱 패턴', '분산_캐싱_패턴.md'),
        ]),
        ('배포와 운영', [
            ('배포 패턴', '배포_패턴.md'),
            ('설정 관리 및 Secret 관리', '설정_관리_및_Secret_관리.md'),
            ('테스트 전략', 'MSA_테스트_전략.md'),
            ('분산 추적 및 Observability', '분산_추적_및_Observability.md'),
            ('장애 격리 패턴', '장애_격리_패턴.md'),
            ('운영 및 장애 대응', '마이크로서비스_운영_및_장애_대응.md'),
            ('운영 및 장애 대응 심화',
             'MSA_Operations_Incident_Response_Deep_Dive.md'),
        ]),
    ],
    'Develop/AI/Concepts': [
        ('에이전트', [
            ('Agent Harness', 'Agent_Harness.md'),
            ('멀티 에이전트 시스템', 'Multi_Agent_Systems.md'),
            ('Function Calling', 'Tool_Use.md'),
            ('Structured Output', 'Structured_Output.md'),
            ('reasoning effort', 'Effort_Mode.md'),
            ('UltraReview', 'Ultra_Review.md'),
        ]),
        ('RAG와 검색', [
            ('텍스트 임베딩 실무', 'Embeddings.md'),
            ('벡터 DB 실무 비교와 운영', 'Vector_Database.md'),
            ('RAG 파이프라인', 'RAG_Pipeline.md'),
            ('RAG for Code', 'RAG_for_Code.md'),
            ('Functional RAG', 'Functional_RAG.md'),
            ('온톨로지', 'Ontology.md'),
        ]),
        ('실무 활용', [
            ('코딩을 위한 프롬프트 엔지니어링', 'Prompt_Engineering.md'),
            ('할루시네이션', 'AI_Hallucination.md'),
            ('바이브 코딩 보안 대처법', 'Vibe_Coding_Security.md'),
            ('Obsidian 실무', 'Obsidian.md'),
            ('LLM+Obsidian 워크플로',
             'Karpathy_LLM_Obsidian.md'),
            ('팔란티어가 AI로 일하는 방식', 'Palantir_AI_Workflow.md'),
            ('로컬 구동 (unsloth/Qwen3)', 'Unsloth_Qwen3_GGUF.md'),
        ]),
    ],
    'Develop/DataBase/RDBMS': [
        ('인덱스', [
            ('RDBMS에서의 Index', 'RDBMS에서의 index.md'),
            ('B-Tree 페이지 분할', 'B_Tree_Page_Split.md'),
            ('인덱스 지역성', '인덱스_지역성.md'),
            ('쿼리 옵티마이저와 실행 계획', '쿼리_옵티마이저.md'),
        ]),
        ('트랜잭션과 동시성', [
            ('트랜잭션과 Lock', 'Transaction_and_Lock.md'),
            ('격리 수준별 이상 현상 재현', 'Isolation_Level_Anomaly_Examples.md'),
            ('MySQL InnoDB 락 심화', 'My_SQL_Inno_DB_Locking_Deep_Dive.md'),
            ('Advisory Lock', 'Postgre_SQL_Advisory_Lock.md'),
            ('분산 트랜잭션', 'Distributed_Transaction.md'),
        ]),
        ('모델링과 정규화', [
            ('DB 모델링', 'DB_Modeling.md'),
            ('Codd 12 Rules', 'Codd_12_Rules.md'),
            ('함수 종속', '함수_종속.md'),
            ('정규화', '정규화.md'),
            ('BCNF', 'BCNF.md'),
            ('갱신 이상', '갱신_이상.md'),
            ('비정규화', '비정규화.md'),
            ('계층형 데이터 모델링', 'Hierarchical_Data_Modeling.md'),
        ]),
        ('시간 데이터', [
            ('시간 데이터 모델링', 'Temporal_Data_Modeling.md'),
            ('Valid Time', 'Valid_Time.md'),
            ('Transaction Time', 'Transaction_Time.md'),
            ('Bitemporal', 'Bitemporal.md'),
        ]),
        ('키와 타입 설계', [
            ('식별자 설계', 'Identifier_Design.md'),
            ('자연키', 'Natural_Key.md'),
            ('대리키', 'Surrogate_Key.md'),
            ('AUTO_INCREMENT', 'Auto_Increment.md'),
            ('ULID', 'ULID.md'),
            ('데이터 타입 선택', 'Data_Type_Selection.md'),
        ]),
        ('무결성과 관계', [
            ('참조 무결성', 'Referential_Integrity.md'),
            ('외래키 없는 설계', 'No_FK_Design.md'),
            ('고아 레코드', 'Orphan_Record.md'),
            ('Cross-Schema 쿼리', 'Cross_Schema.md'),
            ('TypeORM 엔티티 관계 매핑 심화', 'Type_ORM_Entity_Relations.md'),
        ]),
        ('확장과 운영', [
            ('데이터베이스 성능 튜닝', '데이터베이스_성능_튜닝.md'),
            ('데이터베이스 샤딩', '데이터베이스_샤딩.md'),
            ('읽기 전용 복제본', '읽기_전용_복제본.md'),
            ('CDC 파이프라인', 'CDC_Pipeline.md'),
            ('MySQL vs PostgreSQL', 'My_SQL_vs_Postgre_SQL.md'),
            ('ClickHouse', 'ClickHouse.md'),
        ]),
    ],
    'Develop/Network': [
        ('기초', [
            ('네트워크 기초', 'Networking_Fundamentals.md'),
            ('라우팅', '라우팅.md'),
            ('네트워크 스위치', 'Network Switch.md'),
            ('리피터', 'Repeater.md'),
            ('URL과 URI의 차이', 'URL_and_URI.md'),
        ]),
        ('주소 변환과 연결', [
            ('NAT', 'NAT.md'),
            ('NAT 트래버설', 'NAT_Traversal_STUN_TURN_ICE.md'),
            ('터널링', 'Tunneling.md'),
            ('배스천 호스트', 'Bastion_Host.md'),
            ('Private DNS', 'Private_DNS.md'),
        ]),
        ('웹 전송', [
            ('CORS', 'CORS.md'),
            ('CDN 동작 원리와 실무 운영', 'CDN.md'),
        ]),
        ('분산 네트워크', [
            ('P2P 네트워크', 'P2P.md'),
            ('IPFS', 'IPFS.md'),
        ]),
        ('관측', [
            ('tcpdump 패킷 캡처와 분석',
             'Observability/Packet_Capture_tcpdump.md'),
            ('소켓 I/O 멀티플렉싱', 'IO/Socket_IO_Multiplexing.md'),
        ]),
    ],
    'Develop/Security': [
        ('API 보안', [
            ('API Security', 'API_Security.md'),
            ('Input Validation', 'API_Input_Validation.md'),
            ('Gateway Security', 'API_Gateway_Security.md'),
            ('GraphQL Security', 'Graph_QL_Security.md'),
            ('Webhook Security', 'Webhook_Security.md'),
        ]),
        ('암호화', [
            ('AES', 'AES.md'),
            ('RSA', 'RSA.md'),
            ('SHA 해시 함수', 'SHA.md'),
            ('HMAC', 'HMAC.md'),
            ('패스워드 해싱', 'Password_Hashing.md'),
            ('E2EE 종단간 암호화', 'End_to_End_Encryption.md'),
        ]),
        ('전송 구간 보안', [
            ('HTTPS & TLS', 'HTTPS_and_TLS.md'),
            ('mTLS', 'Mutual_TLS.md'),
            ('PKI와 인증서 수명주기', 'PKI_and_Certificate_Management.md'),
        ]),
        ('인증과 세션', [
            ('OAuth 2.0', 'OAuth.md'),
            ('SSO (SAML · OIDC)', 'SSO_SAML_OIDC.md'),
            ('JWT', 'JWT.md'),
            ('JWKS URL', 'JWKS_Endpoint.md'),
            ('Session Management', 'Session_Management.md'),
            ('Cookie Security', 'Cookie_Security.md'),
            ('WebAuthn·Passkeys', 'Web_Authn_Passkeys.md'),
            ('모바일 앱 토큰 저장', 'Mobile_Token_Storage.md'),
        ]),
        ('웹 취약점', [
            ('XSS', 'XSS.md'),
            ('CSRF', 'CSRF.md'),
            ('SSRF', 'SSRF.md'),
            ('Clickjacking', 'Clickjacking.md'),
            ('Command Injection', 'Command_Injection.md'),
            ('안전하지 않은 역직렬화', 'Insecure_Deserialization.md'),
            ('XXE 주입', 'XML_External_Entity.md'),
            ('Path Traversal', 'Path_Traversal.md'),
            ('Open Redirect', 'Open_Redirect.md'),
            ('Open Redirect 심화', 'Open_Redirect_Deep_Dive.md'),
            ('웹 캐시 포이즈닝', 'Web_Cache_Poisoning.md'),
            ('CORS와 브라우저 보안 헤더', 'CORS_and_Security_Headers.md'),
            ('파일 업로드 보안', 'File_Upload_Security.md'),
        ]),
        ('공격 방어', [
            ('DDoS 공격 방어', 'D_Do_S_Defense.md'),
            ('Rate Limiting', 'Rate_Limiting.md'),
            ('웹 애플리케이션 방화벽', 'Web_Application_Firewall.md'),
            ('서버 취약점 공격 방어', 'Server_Attack_Defense.md'),
            ('DNS Security', 'DNS_Security.md'),
            ('공급망 공격 방어', 'Supply_Chain_Security.md'),
        ]),
        ('인프라 보안', [
            ('Zero Trust', 'Zero_Trust_Architecture.md'),
            ('Docker 컨테이너 보안', 'Container_Security.md'),
            ('쿠버네티스 보안', 'Kubernetes_Security.md'),
            ('시크릿 관리', 'Secrets_Management.md'),
            ('SSH 키 라이프사이클 관리', 'SSH_Key_Management.md'),
        ]),
        ('운영과 컴플라이언스', [
            ('DevSecOps', 'Dev_Sec_Ops.md'),
            ('SAST / DAST / IAST', 'Security_Testing_SAST_DAST_IAST.md'),
            ('보안 로깅과 감사', 'Security_Logging_and_Auditing.md'),
            ('보안 사고 대응 절차', 'Incident_Response.md'),
            ('PII 데이터 보호', 'PII_Data_Protection.md'),
            ('GDPR 컴플라이언스', 'GDPR_and_Privacy_Compliance.md'),
            ('ISMS / ISMS-P', 'ISMS.md'),
            ('AI로 보안 강화하기', 'AI_for_Security.md'),
            ('DID', 'DID.md'),
        ]),
    ],
    'Develop/Framework/Node/NestJS': [
        ('핵심 구조', [
            ('부트스트랩과 모듈 시스템', 'Nest_JS_부트스트랩_및_모듈_시스템.md'),
            ('표준 계층 아키텍처', 'Nest_JS_Standard_Architecture.md'),
            ('Clean Architecture 적용', 'Nest_JS_Clean_Architecture.md'),
            ('데코레이터', 'Nest_JS_Decorator.md'),
            ('Dynamic Module 심화', 'Nest_JS_Dynamic_Module.md'),
            ('Provider Scope 심화', 'Nest_JS_Provider_Scope.md'),
            ('순환 의존성 해결', 'Nest_JS_Circular_Dependency.md'),
            ('라이프사이클 훅', 'Nest_JS_Lifecycle_Hooks.md'),
        ]),
        ('요청 처리', [
            ('요청 라이프사이클', 'Nest_JS_요청_라이프사이클.md'),
            ('Middleware', 'Nest_JS_Middleware.md'),
            ('Guards', 'Nest_JS_Guards.md'),
            ('Interceptor', 'Nest_JS_Interceptors.md'),
            ('Pipes', 'Nest_JS_Pipes.md'),
            ('ValidationPipe와 검증 시점', 'Nest_JS_Validation_Pipe.md'),
            ('Exception Filters', 'Nest_JS_Exception_Filters.md'),
        ]),
        ('API', [
            ('Swagger 문서 자동화', 'Nest_JS_Swagger.md'),
            ('API 버저닝', 'Nest_JS_API_Versioning.md'),
            ('GraphQL 모듈 운영기', 'Nest_JS_Graph_QL.md'),
            ('GraphQL·마이크로서비스 버전 관리',
             'Nest_JS_Graph_QL_Microservice_Versioning.md'),
            ('Server-Sent Events', 'Nest_JS_SSE.md'),
            ('WebSocket Gateway 운영기', 'Nest_JS_Web_Socket_Gateway.md'),
            ('File Upload 심화', 'Nest_JS_File_Upload.md'),
        ]),
        ('데이터', [
            ('TypeORM 연동', 'Nest_JS_Type_ORM_연동.md'),
            ('Prisma 연동', 'Nest_JS_Prisma.md'),
            ('MongoDB / Mongoose 연동', 'Nest_JS_Mongo_DB_Mongoose.md'),
            ('CacheModule 운영기', 'Nest_JS_Cache_Module.md'),
        ]),
        ('분산 처리', [
            ('마이크로서비스', 'Nest_JS_마이크로서비스.md'),
            ('gRPC 트랜스포트 심화', 'Nest_JS_g_RPC.md'),
            ('Event Emitter·CQRS', 'Nest_JS_Event_Emitter_CQRS.md'),
            ('작업 큐 (BullMQ) 운영기', 'Nest_JS_작업_큐_Bull_MQ.md'),
            ('Schedule Module 심화', 'Nest_JS_Schedule_Module.md'),
        ]),
        ('운영', [
            ('설정 관리', 'Nest_JS_설정_관리.md'),
            ('ConfigService 타입안전', 'Type_Safe_Config_Service.md'),
            ('Secrets Manager·KMS', 'Nest_JS_AWS_Secrets_Manager_KMS.md'),
            ('인증 (JWT · Passport)', 'Nest_JS_인증_JWT_Passport.md'),
            ('Throttler 심화', 'Nest_JS_Throttler.md'),
            ('로깅 실무', 'Nest_JS_Logging.md'),
            ('OpenTelemetry 분산 추적', 'Nest_JS_Open_Telemetry.md'),
            ('Health Check 심화', 'Nest_JS_Health_Check.md'),
            ('테스트', 'Nest_JS_테스트.md'),
        ]),
    ],
    'Develop/Framework/Node': [
        ('프레임워크', [
            ('개요', 'Nodejs_Framework_Overview.md'),
            ('프레임워크 비교', 'Nest_Hapi_Express_fastify.md'),
            ('애플리케이션 라우팅', 'Application_Routing.md'),
            ('뷰 엔진 (Handlebars)', 'View_Engine/Handlebars.md'),
        ]),
        ('코어 모듈', [
            ('HTTP / HTTPS', 'HTTP_Module.md'),
            ('fs', 'File_System.md'),
            ('net (TCP)', 'Net_Module.md'),
            ('Stream', '데이터 처리 및 통신/스트림(Stream).md'),
            ('crypto', 'Crypto_Module.md'),
            ('child_process', 'Child_Process.md'),
            ('AbortController', 'Abort_Controller.md'),
            ('perf_hooks', 'Performance_Hooks.md'),
            ('diagnostics_channel', 'Diagnostics_Channel.md'),
            ('Permission Model', 'Permission_Model.md'),
            ('node:test 러너', 'Node_Test_Runner.md'),
        ]),
        ('함수형 프로그래밍', [
            ('기초', '함수형 프로그래밍.md'),
            ('실전', 'Functional_Programming.md'),
        ]),
        ('운영', [
            ('에러 처리', 'Error_Handling.md'),
            ('에러 처리 심화', '에러_핸들링/에러_핸들링_전략.md'),
            ('그레이스풀 셧다운', 'Graceful_Shutdown.md'),
            ('로깅 전략', '로깅/로깅_전략.md'),
            ('Observability 전략', '모니터링/Observability_전략.md'),
            ('성능 최적화와 프로파일링',
             'Performance/Node.js_성능_최적화_및_프로파일링.md'),
            ('부하 테스트 전략', '성능/부하_테스트_전략.md'),
            ('보안 모범사례', '보안/Node.js_보안_모범사례.md'),
            ('JWT 구현과 보안', '인증/JWT_구현_및_보안.md'),
            ('작업 큐 처리', '백그라운드_작업/작업_큐_처리.md'),
            ('파일 업로드와 처리', '파일_처리/파일_업로드_및_처리.md'),
        ]),
    ],
}

# 파일명이 디렉터리명과 같아도 '개요'가 아닌 문서
# (Static/static.md 는 개요가 아니라 실무 패턴 문서다)
NO_OVERVIEW = {
    'Develop/Language/Java/객체지향 프로그래밍 (OOP)/Static/static.md',
}

# 디렉터리 .pages의 title 을 강제로 바꾼다
# (자식의 title 이 부모 nav 라벨보다 우선하므로 여기서 지정해야 한다)
TITLE_OVERRIDE = {
    'Develop/_hub': '주제별 가이드',
    'Develop/Framework/Node/Nodejs의 구조 및 작동 원리': '런타임 구조',
    'Develop/Framework/Node/Testing': '테스트',
}

# 디렉터리 자체의 표시 이름
DIR_LABEL = {
    'Develop/AI/Concepts': '개념',
    'Develop/_hub': '주제별 가이드',
    'Develop/Framework/Node/Nodejs의 구조 및 작동 원리': '런타임 구조',
    'Develop/Framework/Node/Process Management Tool': '프로세스 관리',
    'Develop/Framework/Node/Testing': '테스트',
    'Develop/Framework/Node/데이터베이스': '데이터베이스',
    'Develop/Cloud/AWS/Application_Integration': '메시징 연동',
    'Develop/DevOps/Infrastructure_as_Code': 'IaC',
    'Develop/DataBase/DataRepresentation': '데이터 표현',
}

DASHES = [' — ', ' – ', ' - ']


def split_subtitle(label):
    """'Redis — 내부 동작 원리' -> ('Redis', '내부 동작 원리')"""
    for d in DASHES:
        if d in label:
            head, tail = label.split(d, 1)
            return head.strip(), tail.strip()
    return label, None


# 조상 이름 자체가 실제 제품명 접두사인 경우 후보에서 제외한다.
# 'Cloud'를 조상으로 두면 'Cloud Run' → 'Run', 'Cloud SQL' → 'SQL' 처럼
# GCP 제품명 앞부분이 통째로 깎인다. CloudFormation/CloudTrail/CloudWatch 는
# 구분자(' '등)가 없어서 원래 매칭이 안 되므로 여기 넣을 필요 없다.
NEVER_STRIP = {'Cloud'}


def strip_prefix(title, ancestors, report=False):
    cands = []
    for a in ancestors:
        cands.extend(EXTRA_PREFIXES.get(a, []))
        if a not in NEVER_STRIP:
            cands.append(a.replace('_', ' '))
    cands = sorted({c for c in cands if c}, key=len, reverse=True)
    out = title
    # 접두사는 한 번만 뗀다. 두 번 떼면 'Network Gateway 심화'가
    # (Network, GateWay 둘 다 조상이라) '심화'만 남아 뜻이 사라진다.
    changed = True
    while changed:
        changed = False
        for c in cands:
            for sep in [' — ', ' - ', ': ', ' ']:
                pre = c + sep
                if out.lower().startswith(pre.lower()):
                    rest = out[len(pre):].strip()
                    # 여는 괄호로 시작하면 그 이름의 부연설명을 잘라낸 것이다
                    # ('Online-Merge-Offline (OMO) 아키텍처' -> '(OMO) 아키텍처')
                    if rest and not looks_broken(rest):
                        return (rest, True) if report else rest
            if changed:
                break
    return (out, False) if report else out


# 항상 떼는 상투어 — 어떤 문서에나 붙을 수 있어 변별력이 없다
FILLER_ALWAYS = re.compile(
    r'\s*('
    r'사용법 및 핵심 개념|모델 패밀리 개요와 실무 사용|모델 종합 가이드|'
    r'개요와 실무 사용|종합 가이드|완벽 가이드|실전 가이드|실무 가이드|'
    r'핵심 개념|사용법|모범사례|완벽 정리|총정리|허브'
    r')$'
)

# 라벨이 길 때만 떼는 상투어 — 짧을 땐 남겨두는 편이 구별에 도움이 된다
FILLER_IF_LONG = re.compile(
    r'\s*('
    r'개념과 예제|완전 정복|개념과 활용|상세 비교|한눈에 보기|'
    r'정리와 활용|이해하기|알아보기|다루기|살펴보기'
    r')$'
)


# 잘라내다 이런 꼴이 되면 라벨이 깨진 것이다 -> 자르기 전으로 되돌린다
DANGLING = re.compile(
    r'('
    r'(과|와|및|의|에서|으로|로|이나|에|를|을|은|는|이|가)$'   # 매달린 조사·접속
    r'|[,\-+/&·|]$'                                        # 매달린 기호
    r'|\b(vs|and|or|to|for|with|in|on|의)$'                 # 매달린 영어 접속사
    r')'
)


def looks_broken(label):
    """축약 결과가 말이 안 되는 꼴인지."""
    if not label or len(label.strip()) < 2:
        return True
    s = label.strip()
    if DANGLING.search(s):
        return True
    if BAD_HEAD.match(s):
        return True
    if s[0] in '([{)]}':
        return True
    return False


def safe(new, old):
    """새 후보가 깨졌으면 이전 값을 유지한다."""
    return old if looks_broken(new) else new


def _strip_repeat(label, pattern):
    prev = None
    while prev != label:
        prev = label
        cut = pattern.sub('', label).strip()
        label = safe(cut, prev) if cut else prev
        if label == prev:
            break
    return label


def shorten(label):
    """사이드바 라벨 축약: 부제 -> 괄호 부연 -> 상투어 순으로 떼어낸다."""
    label = _strip_repeat(label, FILLER_ALWAYS)
    # 부제('제목 — 부제')는 사이드바에서 항상 떼어낸다. 본문 제목은 그대로 남는다.
    head, _ = split_subtitle(label)
    if head:
        label = safe(head, label)
    if len(label) > LABEL_SOFT_MAX:
        # 끝에 붙은 괄호 부연 (안쪽에 괄호가 또 있어도 잡도록 greedy)
        label = safe(re.sub(r'\s*\(.*\)\s*$', '', label).strip(), label)
    if len(label) > LABEL_SOFT_MAX:
        # 중간에 낀 괄호 부연:  'SHA (Secure Hash Algorithm) 해시 함수'
        label = safe(re.sub(r'\s*\([^()]*\)\s*', ' ', label).strip(), label)
    if len(label) > LABEL_SOFT_MAX:
        label = _strip_repeat(label, FILLER_IF_LONG)
    return re.sub(r'\s{2,}', ' ', label).strip()


def label_ladder(path, ancestors):
    """가장 짧은 후보부터 원제목까지, 축약 단계별 라벨 후보들.

    형제끼리 겹치지 않는 '가장 짧은' 후보를 고르기 위한 사다리다.
    """
    base, stripped = strip_prefix(doc_title(path), ancestors, report=True)
    first = shorten(base)
    if not stripped:
        # 축약하고 나서야 접두사가 드러나는 경우가 있다
        # ('Online-Merge-Offline (OMO) 아키텍처' -> 'OMO 아키텍처' -> '아키텍처')
        first = strip_prefix(first, ancestors)
    cands = [first]

    # 부제만 떼어낸 중간 단계
    head, tail = split_subtitle(base)
    if tail:
        cands.append(head)
        cands.append(f'{head} — {tail}' if len(base) > len(head) else base)

    # 괄호 부연만 떼어낸 중간 단계
    nop = re.sub(r'\s*\(.*\)\s*$', '', base).strip()
    if nop and nop != base:
        cands.append(nop)

    cands.append(base)
    cands.append(os.path.basename(path)[:-3].replace('_', ' '))

    out = []
    for c in cands:
        c = re.sub(r'\s{2,}', ' ', (c or '').strip())
        if c and c not in out:
            out.append(c)
    return out


def make_label(path, ancestors, is_overview=False):
    if is_overview:
        return '개요'
    key = path.replace(os.sep, '/')
    if key in LABEL_OVERRIDE:
        return LABEL_OVERRIDE[key]
    return label_ladder(path, ancestors)[0]


def hoisted_label(subdir, solo, ancestors):
    """문서 1개짜리 디렉터리를 부모로 끌어올릴 때의 라벨.

    디렉터리명이 제목 안에 들어있으면 그건 제품/기술 이름이므로
    디렉터리명을 쓴다 (Codex, Grok, GitHub Copilot ...).
    아니면 디렉터리명은 그냥 분류함이므로 문서 제목을 쓴다
    (Secrets/HashiCorp Vault, Infrastructure_as_Code/Terraform ...).
    """
    dname = os.path.basename(subdir)
    title = strip_prefix(doc_title(os.path.join(subdir, solo)), ancestors)
    if norm(dname) and norm(dname) in norm(title):
        return dname.replace('_', ' ')
    label = shorten(title)
    if len(label) > LABEL_SOFT_MAX:
        return dname.replace('_', ' ')
    return label


def norm(s):
    return re.sub(r'[\s_\-\.]+', '', s).strip().lower()


# ---------------------------------------------------------------- 디렉터리 스캔

def children(dirpath):
    files, dirs = [], []
    try:
        entries = sorted(os.listdir(dirpath))
    except OSError:
        return files, dirs
    for e in entries:
        full = os.path.join(dirpath, e)
        if e.startswith('.'):
            continue
        if os.path.isdir(full):
            if e in SKIP_DIRS:
                continue
            if any(f.endswith('.md') for _, _, fs in os.walk(full) for f in fs):
                dirs.append(e)
        elif e.endswith('.md'):
            files.append(e)
    return files, dirs


def only_md(dirpath):
    """디렉터리가 md 파일 딱 하나뿐이면 그 파일명, 아니면 None."""
    files, dirs = children(dirpath)
    if len(files) == 1 and not dirs:
        return files[0]
    return None


def old_order(dirpath):
    """기존 .pages의 나열 순서 (정렬 기준으로만 쓴다)."""
    p = os.path.join(dirpath, '.pages')
    order = []
    if not os.path.exists(p):
        return order
    in_nav = False
    for line in open(p, encoding='utf-8'):
        raw = line.rstrip('\n')
        if re.match(r'^nav:\s*$', raw):
            in_nav = True
            continue
        if in_nav:
            m = re.match(r'^\s+-\s+(.*)$', raw)
            if not m:
                if raw.strip():
                    in_nav = False
                continue
            item = m.group(1).strip()
            if ': ' in item:
                item = item.split(': ', 1)[1].strip()
            order.append(item.strip())
    return order


def existing_title(dirpath):
    p = os.path.join(dirpath, '.pages')
    if not os.path.exists(p):
        return None
    for line in open(p, encoding='utf-8'):
        if line.startswith('title:'):
            return line.split(':', 1)[1].strip()
    return None


# ---------------------------------------------------------------- nav 생성

def build(dirpath, ancestors):
    """이 디렉터리의 nav 엔트리 목록 [(label, target)] 을 만든다."""
    files, dirs = children(dirpath)
    dirname = os.path.basename(dirpath)
    key = dirpath.replace(os.sep, '/')
    # override는 '앞에 오길 바라는 것'만 적는 힌트다.
    # 나머지는 기존 .pages 순서를 그대로 따른다.
    prev = old_order(dirpath)
    hint = ORDER_OVERRIDE.get(key, [])
    order = hint + [o for o in prev if norm(o) not in {norm(h) for h in hint}]

    def rank(name):
        for i, o in enumerate(order):
            if norm(o) == norm(name):
                return i
        return len(order) + 1000

    entries = []

    # 0) 손으로 짠 묶음이 있으면 거기 들어간 문서는 따로 배치하지 않는다
    manual = MANUAL_GROUPS.get(key, [])
    taken = {rel for _, members in manual for _, rel in members}
    taken_top = {rel.split('/', 1)[0] for rel in taken}
    files = [f for f in files if f not in taken]
    dirs = [d for d in dirs
            if d not in taken_top or any(
                m for m in children(os.path.join(dirpath, d))[0]
                if f'{d}/{m}' not in taken)]

    # 1) 디렉터리 대표 문서를 맨 앞에
    overview = None
    for f in files:
        if norm(f[:-3]) == norm(dirname):
            if f'{key}/{f}' in NO_OVERVIEW:
                continue
            overview = f
            break
    if overview:
        entries.append(('개요', overview))

    # 2) 'DDD/' 와 형제 'DDD.md' 처럼 짝이 지는 건 하나로 합친다
    merged = {}
    for d in dirs:
        sibling = f'{d}.md'
        match = next((f for f in files if norm(f[:-3]) == norm(d)), None)
        if match and match != overview:
            merged[d] = match

    rest = [f for f in files if f != overview and f not in merged.values() and f != 'index.md']
    # 문서를 먼저, 하위 섹션을 뒤로. 섞여 있으면 사이드바가 어수선해진다.
    # (각 묶음 안에서는 기존 큐레이션 순서를 지킨다)
    fitems = sorted((('f', f) for f in rest), key=lambda t: (rank(t[1]), t[1]))
    ditems = sorted((('d', d) for d in dirs), key=lambda t: (rank(t[1]), t[1]))
    items = fitems + ditems

    for kind, name in items:
        if kind == 'f':
            entries.append((make_label(os.path.join(dirpath, name),
                                       ancestors + [dirname]), name))
        else:
            sub = os.path.join(dirpath, name)
            solo = only_md(sub)
            if solo:
                # 문서 1개짜리 디렉터리 -> 부모로 끌어올린다
                lbl = hoisted_label(sub, solo, ancestors + [dirname])
                entries.append((lbl, f'{name}/{solo}'))
            elif name in merged:
                # 개요 파일 + 하위 디렉터리를 한 그룹으로 묶는다 (파일 이동 없이)
                sub_entries = [('개요', merged[name])]
                for sf in sorted(children(sub)[0]):
                    sub_entries.append(
                        (make_label(os.path.join(sub, sf),
                                    ancestors + [dirname, name]),
                         f'{name}/{sf}'))
                for sd in sorted(children(sub)[1]):
                    sub_entries.append((sd.replace('_', ' '), f'{name}/{sd}'))
                entries.append((name.replace('_', ' '), sub_entries))
            else:
                sub_key = f'{key}/{name}'
                entries.append((DIR_LABEL.get(sub_key, name.replace('_', ' ')),
                                name))

    entries = dedupe(entries, dirpath, ancestors + [dirname])
    entries = group_siblings(entries, dirname)

    # 손으로 짠 묶음은 낱장 문서 뒤, 하위 섹션 앞에 놓는다
    if manual:
        groups = [(gl, [(ml, rel) for ml, rel in members
                        if os.path.exists(os.path.join(dirpath, rel))])
                  for gl, members in manual]
        groups = [(gl, ms) for gl, ms in groups if ms]
        head = [e for e in entries if not isinstance(e[1], list)
                and str(e[1]).endswith('.md')]
        tail = [e for e in entries if e not in head]
        entries = head + groups + tail
    return entries


def build_top():
    """최상위 Develop/.pages — 유령 항목 제거 + 주제 순서 정렬."""
    files, dirs = children(ROOT)
    have = set(files) | set(dirs)
    entries = []
    for name in TOP_ORDER:
        if name not in have:
            continue
        if name.endswith('.md'):
            entries.append((None, name))          # index.md / tags.md 는 라벨 없이
        else:
            entries.append((DIR_LABEL.get(f'Develop/{name}',
                                          name.replace('_', ' ')), name))
    # TOP_ORDER에 없는 게 새로 생기면 뒤에 붙인다 (다시는 고아가 되지 않도록)
    for name in sorted(have - set(TOP_ORDER)):
        if name == '_hub':
            continue
        entries.append((None, name) if name.endswith('.md')
                       else (name.replace('_', ' '), name))
    return entries


def group_siblings(entries, dirname=''):
    """같은 이름으로 시작하는 형제들을 접기 가능한 그룹으로 묶는다.

    'ECS', 'ECS Exec', 'ECS Task Placement', ... 30여 개가 평평하게 늘어서 있으면
    사이드바에서 읽히지 않는다. 'ECS' 그룹 하나로 접고 접두사는 떼어낸다.
    'ECS에서 ...'처럼 조사가 바로 붙은 것도 같은 그룹으로 본다.
    """
    flat = [(i, l, t) for i, (l, t) in enumerate(entries)
            if not isinstance(t, list) and l]

    # 그룹 이름 후보: 라벨의 첫 낱말 (영문 고유명사만)
    cands = set()
    for _, label, _ in flat:
        words = label.split()
        if not words or not GROUP_NAME_OK.match(words[0]):
            continue
        if words[0].lower() in GROUP_BLOCK:
            # 'Cloud SQL'처럼 벤더 공통어는 두 낱말까지 붙여야 제품이 된다
            if len(words) > 1 and words[1].lower() not in GROUP_BLOCK:
                cands.add(' '.join(words[:2]))
        else:
            cands.add(words[0])

    def members_of(name):
        pat = re.compile(re.escape(name) + r'(\s|[가-힣])')
        return [i for i, label, _ in flat
                if label == name or pat.match(label)]

    def extend(name, idxs):
        """'SQL' 3개가 전부 'SQL Injection ...' 이면 그룹 이름을 늘린다."""
        toks = [entries[i][0].split() for i in idxs]
        pre = []
        for k in range(min(len(x) for x in toks)):
            words = {x[k] for x in toks}
            if len(words) != 1:
                break
            pre.append(words.pop())
            if any(len(x) == k + 1 for x in toks):
                break      # 한 항목을 통째로 삼켰다 -> 그게 그룹의 개요다
        return ' '.join(pre) if pre else name

    # 부모 섹션과 같은 이름으로는 묶지 않는다.
    # NestJS 디렉터리 안에 다시 'NestJS' 묶음이 생기면 계층만 늘어난다.
    cands = {c for c in cands if norm(c) != norm(dirname)}

    plan = {}
    for name in sorted(cands, key=len, reverse=True):
        idxs = [i for i in members_of(name)
                if not any(i in v for v in plan.values())]
        if len(idxs) >= GROUP_MIN:
            plan[extend(name, idxs)] = idxs
    if not plan:
        return entries

    out, consumed = [], set()
    for idx, (label, target) in enumerate(entries):
        if idx in consumed:
            continue
        owner = next((p for p, idxs in plan.items() if idx in idxs), None)
        if owner is None:
            out.append((label, target))
            continue
        members = []
        for j in plan[owner]:
            consumed.add(j)
            jl, jt = entries[j]
            rest = jl[len(owner):]
            if not rest.strip():
                rest = '개요'
            elif not rest.startswith(' '):
                rest = jl          # 조사가 바로 붙은 경우는 원래 라벨을 유지
            else:
                rest = rest.strip()
                if looks_broken(rest):
                    rest = jl
            members.append((rest, jt))
        members.sort(key=lambda m: 0 if m[0] == '개요' else 1)
        out.append((owner, members))
    return out


def dedupe(entries, dirpath, ancestors):
    """형제끼리 라벨이 겹치면, 겹치지 않는 '가장 짧은' 후보로 올라간다."""
    taken = set()
    for i, (lbl, tgt) in enumerate(entries):
        if lbl.lower() not in taken:
            taken.add(lbl.lower())
            continue
        if isinstance(tgt, list) or not tgt.endswith('.md'):
            taken.add(lbl.lower())
            continue
        for cand in label_ladder(os.path.join(dirpath, tgt), ancestors):
            if cand.lower() not in taken:
                entries[i] = (cand, tgt)
                lbl = cand
                break
        else:
            # 사다리를 다 올라가도 겹치면 파일명으로 구분
            entries[i] = (os.path.basename(tgt)[:-3].replace('_', ' '), tgt)
            lbl = entries[i][0]
        taken.add(lbl.lower())
    return entries


def write_pages(dirpath, entries, title=None, root=False):
    lines = []
    if title:
        lines.append(f'title: {title}')
    lines.append('nav:')
    for label, target in entries:
        if isinstance(target, list):
            lines.append(f'  - {label}:')
            for sl, st in target:
                lines.append(f'    - {sl}: {st}')
            continue
        # 라벨이 target에서 자연스럽게 나오면 굳이 적지 않는다
        if label is None or label == target.replace('_', ' '):
            lines.append(f'  - {target}')
        else:
            lines.append(f'  - {label}: {target}')
    if root:
        lines.append('  - ...')
    content = '\n'.join(lines) + '\n'
    path = os.path.join(dirpath, '.pages')
    if WRITE:
        open(path, 'w', encoding='utf-8').write(content)
    return path, content


def walk_and_generate():
    generated = {}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        parts = dirpath.split(os.sep)
        if any(p in SKIP_DIRS for p in parts) or any(p.startswith('.') for p in parts[1:]):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and not d.startswith('.')]
        if dirpath == ROOT:
            # 루트 .pages는 7개 최상위 그룹 구조로 수동 관리한다.
            # gen_nav.py가 덮어쓰지 않도록 스킵. (Develop/.pages 참고)
            continue
        if dirpath.replace(os.sep, '/') in MANUAL_DIRS:
            # 수동 관리 디렉터리 — .pages 를 건드리지 않는다
            continue
        # 문서 1개짜리 디렉터리는 부모가 흡수했으므로 .pages 불필요.
        # 단 최상위 섹션은 흡수 대상이 아니므로 그대로 둔다.
        if only_md(dirpath) and os.path.dirname(dirpath) != ROOT:
            p = os.path.join(dirpath, '.pages')
            if os.path.exists(p) and WRITE:
                os.remove(p)
            generated[dirpath] = None
            continue
        ancestors = parts[1:-1]
        depth = len(parts) - 1  # ROOT = 0, ROOT/child = 1, ...
        if depth > MAX_SIDEBAR_DEPTH:
            # depth 3+ 는 sidebar 에서 제거: index.md(허브) 하나만 노출.
            # 이 index.md 는 section_index.py 가 빌드 시점에 자동 생성한다.
            index_exists = os.path.exists(os.path.join(dirpath, 'index.md'))
            if index_exists:
                entries = [(None, 'index.md')]
            else:
                # index.md 아직 없음(첫 실행) → 파일 목록 그대로, 서브디렉터리는 제외
                files, _ = children(dirpath)
                dirname = os.path.basename(dirpath)
                overview_f = next(
                    (f for f in files if f != 'index.md' and
                     os.path.splitext(f)[0].replace('_', '').lower() ==
                     dirname.replace('_', '').lower()), None)
                entries = []
                for f in files:
                    if f == overview_f:
                        entries.insert(0, ('개요', f))
                    else:
                        entries.append((make_label(os.path.join(dirpath, f),
                                                    ancestors + [dirname]), f))
        else:
            entries = build(dirpath, ancestors)
        key = dirpath.replace(os.sep, '/')
        title = TITLE_OVERRIDE.get(key, existing_title(dirpath))
        generated[dirpath] = write_pages(dirpath, entries, title)[1]
    return generated


if __name__ == '__main__':
    gen = walk_and_generate()
    n = sum(1 for v in gen.values() if v)
    rm = sum(1 for v in gen.values() if v is None)
    print(f"{'작성' if WRITE else '미리보기'}: .pages {n}개 생성, {rm}개 제거(1문서 디렉터리)")
