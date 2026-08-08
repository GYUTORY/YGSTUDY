#!/usr/bin/env python3
"""문서 프론트매터의 tags 를 통제 어휘(tools/tags.yml)로 정규화한다.

왜 필요한가: 태그가 3,038종까지 늘어났고 그중 1,955종이 문서 1개짜리였다.
태그 페이지가 항목 하나짜리로 파편화되면 탐색 장치로 쓸모가 없다.

방식은 세 단계다.
  1) 별칭 표(ALIASES)로 흔한 표기를 어휘에 매핑한다.
  2) 매핑되지 않은 태그는 버린다. 세부 키워드는 본문 검색에 맡긴다.
  3) 그 결과가 비면 문서 경로에서 태그를 유도한다. 경로는 가장 신뢰할 수 있는 신호다.

사용법:
  python3 tools/normalize_tags.py --dry-run   # 변경 없이 결과만 출력
  python3 tools/normalize_tags.py             # 실제 적용
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
DOCS = ROOT / "Develop"
MAX_TAGS = 4

FM_RE = re.compile(r"^(---\s*\n)(.*?)(\n---\s*\n)", re.S)
TAGS_INLINE_RE = re.compile(r"^tags\s*:\s*\[([^\]]*)\]\s*$", re.M)
TAGS_BLOCK_RE = re.compile(r"^tags\s*:\s*\n((?:[ \t]*-[ \t]*.+\n?)+)", re.M)

# 흔한 표기 → 통제 어휘. 여기 없는 태그는 버린다.
ALIASES = {
    # 언어 / 런타임
    "node": "nodejs", "node.js": "nodejs", "nestjs": "nodejs", "express": "nodejs",
    "npm": "nodejs", "event-loop": "nodejs", "closure": "javascript", "scope": "javascript",
    "es6": "javascript", "primitive-types": "javascript", "prototype": "javascript",
    "golang": "go", "jvm": "java", "hibernate": "java", "jpa": "java", "spring-boot": "spring",
    "spring-security": "spring", "object-types": "typescript", "typescript-types": "typescript",
    "generics": "typescript", "tsconfig": "typescript", "oop": "language",
    "functional-programming": "language", "class": "language", "interface": "language",
    # 데이터
    "innodb": "mysql", "aurora": "rdbms", "typeorm": "rdbms", "prisma": "rdbms",
    "index": "rdbms", "normalization": "rdbms", "transaction": "rdbms", "lock": "rdbms",
    "deadlock": "rdbms", "replication": "database", "partitioning": "database",
    "connection-pool": "database", "cdc": "database", "storage": "database",
    "encoding": "database", "datarepresentation": "database", "scylladb": "nosql",
    "valkey": "redis", "caching": "cache",
    # 클라우드 / 인프라
    "ecs": "aws", "eks": "aws", "ec2": "aws", "s3": "aws", "rds": "aws", "lambda": "aws",
    "fargate": "aws", "alb": "aws", "elb": "load-balancer", "cloudwatch": "aws",
    "cloudfront": "cdn", "route53": "dns", "kms": "encryption", "secrets-manager": "security",
    "ssm": "aws", "eni": "vpc", "rds-proxy": "aws", "sqs": "messaging", "sns": "messaging",
    "infrastructure": "iac", "infra": "iac", "serverless": "cloud", "automation": "devops",
    "deployment": "devops", "blue-green": "devops", "canary": "devops", "pipeline": "ci-cd",
    "cicd": "ci-cd", "ci": "ci-cd", "cd": "ci-cd", "gitops": "devops", "cluster": "kubernetes",
    "container": "docker", "containers": "docker", "k8s": "kubernetes",
    "service-mesh": "kubernetes", "envoy": "proxy", "service-discovery": "microservices",
    "graceful-shutdown": "devops", "health-check": "monitoring", "batch": "backend",
    # 네트워크 / 보안
    "networking": "network", "7-layer": "network", "transport-layer": "network",
    "application-layer": "network", "socket": "network", "websocket": "network",
    "https": "http", "ssl": "encryption", "tls": "encryption", "mtls": "encryption",
    "certificate": "encryption", "reverse-proxy": "proxy", "api-gateway": "api",
    "cors": "security", "ssrf": "security", "waf": "security", "ddos": "security",
    "firewall": "security", "zero-trust": "security", "audit": "security",
    "compliance": "security", "authorization": "auth", "authentication": "auth",
    "oauth2": "auth", "oidc": "auth", "vpn": "network", "ssh": "linux",
    "multi-tenancy": "architecture", "rate-limiting": "performance", "throttling": "performance",
    # 아키텍처
    "msa": "microservices", "ddd": "architecture", "domain": "architecture",
    "saga": "architecture", "idempotency": "architecture", "design-pattern": "design-patterns",
    "kafka": "messaging", "rabbitmq": "messaging", "queue": "messaging",
    "event-driven-architecture": "event-driven", "streaming": "messaging",
    "distributed-lock": "architecture", "workflow": "architecture",
    # 운영 / 품질
    "logging": "observability", "metrics": "monitoring", "tracing": "observability",
    "opentelemetry": "observability", "prometheus": "monitoring", "grafana": "monitoring",
    "troubleshooting": "observability", "error-handling": "backend", "validation": "backend",
    "migration": "devops", "versioning": "api", "lifecycle": "devops",
    "configuration": "devops", "cost": "cloud",
    # AI
    "claude": "ai", "claude-code": "ai", "anthropic": "ai", "gemini": "ai", "gpt": "ai",
    "agent": "ai", "prompt": "llm", "embedding": "rag", "vector": "rag",
    # 기타
    "webserver": "web-server", "nginx": "web-server", "caddy": "web-server",
    "apache": "web-server", "process": "os", "thread": "os", "concurrency": "os",
    "memory": "os", "scheduling": "os", "async": "language", "json": "api",
    "uuid": "backend", "timezone": "backend", "stream": "language", "cli": "devops",
    "git": "git", "algorithm": "algorithm",
}

# 경로 유도 규칙 — 위에서부터 먼저 맞는 것을 쓴다. (경로 접두사, 태그들)
PATH_RULES = [
    ("AI/MCP", ["ai", "mcp"]),
    ("AI/Concepts", ["ai", "llm"]),
    ("AI", ["ai"]),
    ("Language/Java", ["java", "language"]),
    ("Language/JavaScript", ["javascript", "language"]),
    ("Language/TypeScript", ["typescript", "language"]),
    ("Language/Go", ["go", "language"]),
    ("Language/Rust", ["rust", "language"]),
    ("Language/Python", ["python", "language"]),
    ("Language/Kotlin", ["kotlin", "language"]),
    ("Language", ["language"]),
    ("Framework/Java/Spring", ["spring", "java"]),
    ("Framework/Java", ["java"]),
    ("Framework/Node", ["nodejs"]),
    ("Framework", ["backend"]),
    ("Cloud/AWS", ["aws", "cloud"]),
    ("Cloud/GCP", ["gcp", "cloud"]),
    ("Cloud", ["cloud"]),
    ("DevOps/Kubernetes", ["kubernetes", "devops"]),
    ("DevOps/Docker", ["docker", "devops"]),
    ("DevOps/CI_CD", ["ci-cd", "devops"]),
    ("DevOps/Linux", ["linux", "devops"]),
    ("DevOps/Monitoring", ["monitoring", "devops"]),
    ("DevOps/Infrastructure_as_Code", ["iac", "devops"]),
    ("DevOps/Git", ["git", "devops"]),
    ("DevOps/Load_Balancer", ["load-balancer", "devops"]),
    ("DevOps", ["devops"]),
    ("DataBase/RDBMS", ["rdbms", "database"]),
    ("DataBase/NoSQL", ["nosql", "database"]),
    ("DataBase", ["database"]),
    ("Network", ["network"]),
    ("Security", ["security"]),
    ("Backend/Authentication", ["auth", "backend"]),
    ("Backend/API", ["api", "backend"]),
    ("Backend/Caching", ["cache", "backend"]),
    ("Backend/Messaging", ["messaging", "backend"]),
    ("Backend/Performance", ["performance", "backend"]),
    ("Backend/Logging", ["observability", "backend"]),
    ("Backend", ["backend"]),
    ("Architecture/MSA", ["microservices", "architecture"]),
    ("Architecture/Design Pattern", ["design-patterns", "architecture"]),
    ("Architecture", ["architecture"]),
    ("WebServer", ["web-server"]),
    ("OS", ["os"]),
    ("Algorithm", ["algorithm"]),
    ("Frontend", ["frontend"]),
    ("_hub", ["architecture"]),
]


def load_allowed() -> set:
    return set(yaml.safe_load((ROOT / "tools" / "tags.yml").read_text(encoding="utf-8"))["allowed"])


def normalize(tag: str) -> str:
    t = tag.strip().strip("\"'").lower()
    t = t.replace("_", "-").replace(" ", "-")
    return re.sub(r"-+", "-", t).strip("-")


def parse_tags(fm: str) -> list:
    m = TAGS_INLINE_RE.search(fm)
    if m:
        return [x.strip().strip("\"'") for x in m.group(1).split(",") if x.strip()]
    m = TAGS_BLOCK_RE.search(fm)
    if m:
        return [l.strip().lstrip("-").strip().strip("\"'")
                for l in m.group(1).splitlines() if l.strip().startswith("-")]
    return []


def derive_from_path(rel: str) -> list:
    for prefix, tags in PATH_RULES:
        if rel == prefix or rel.startswith(prefix + "/"):
            return list(tags)
    return []


def map_tags(raw: list, rel: str, allowed: set) -> list:
    out = []
    for t in raw:
        n = normalize(t)
        if n in allowed:
            mapped = n
        elif n in ALIASES:
            mapped = ALIASES[n]
        else:
            continue
        if mapped in allowed and mapped not in out:
            out.append(mapped)
    # 경로 유도분을 뒤에 붙여 섹션 성격이 항상 남게 한다.
    for t in derive_from_path(rel):
        if t in allowed and t not in out:
            out.append(t)
    return out[:MAX_TAGS]


def render(tags: list) -> str:
    return "tags: [" + ", ".join(tags) + "]"


def replace_tags(fm: str, tags: list) -> str:
    line = render(tags)
    if TAGS_INLINE_RE.search(fm):
        return TAGS_INLINE_RE.sub(line, fm, count=1)
    if TAGS_BLOCK_RE.search(fm):
        return TAGS_BLOCK_RE.sub(line + "\n", fm, count=1)
    return fm + "\n" + line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    allowed = load_allowed()
    changed = untouched = notag = 0
    before_kinds, after_kinds = set(), set()

    for path in sorted(DOCS.rglob("*.md")):
        rel = str(path.relative_to(DOCS))
        text = path.read_text(encoding="utf-8")
        m = FM_RE.match(text)
        if not m:
            continue
        head, fm, tail = m.group(1), m.group(2), m.group(3)
        raw = parse_tags(fm)
        before_kinds.update(normalize(t) for t in raw)
        new = map_tags(raw, rel, allowed)
        after_kinds.update(new)
        if not new:
            notag += 1
        if [normalize(t) for t in raw] == new:
            untouched += 1
            continue
        changed += 1
        if not args.dry_run:
            path.write_text(head + replace_tags(fm, new) + tail + text[m.end():], encoding="utf-8")

    print(f"{'[dry-run] ' if args.dry_run else ''}변경 {changed} · 유지 {untouched} · 결과 무태그 {notag}")
    print(f"태그 종류 {len(before_kinds)} → {len(after_kinds)}")
    missing = after_kinds - allowed
    if missing:
        print("어휘 밖 잔존:", sorted(missing)[:10])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
