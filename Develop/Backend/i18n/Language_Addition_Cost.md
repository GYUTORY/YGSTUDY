---
title: 언어 추가 비용
tags: [backend, iac, performance]
updated: 2026-08-07
---

# 언어 추가 비용

새 로케일을 하나 추가하는 작업은 번역 파일 몇 개 넣는 것으로 끝나지 않는다. DB 마이그레이션은 빙산의 일각이고, 실제 비용은 애플리케이션 레이어, 인프라, 번역 파이프라인 전반에 흩어져 있다. 준비 없이 진행하면 런타임에 문제가 터진다.

---

## 애플리케이션 레이어

### URL 라우팅

로케일을 URL에 포함하는 패턴(`/ko/products`, `/ja/products`)을 쓴다면, 새 로케일 추가 시 라우터 설정을 건드려야 한다. Next.js는 `next.config.js`의 `i18n.locales` 배열에 추가하는 것만으로 끝나지만, 직접 라우터를 관리하는 프레임워크라면 로케일 검증 로직 전체를 확인해야 한다.

```typescript
// 로케일 목록을 하드코딩하지 말고 중앙 관리
const SUPPORTED_LOCALES = ['ko', 'en', 'ja', 'zh-TW'] as const;
type Locale = typeof SUPPORTED_LOCALES[number];

function isValidLocale(locale: string): locale is Locale {
  return SUPPORTED_LOCALES.includes(locale as Locale);
}
```

로케일 목록이 라우터, 미들웨어, DB 설정 등 여러 곳에 흩어져 있으면 하나 추가할 때마다 누락이 생긴다. 단일 소스를 만들고 나머지는 참조하게 한다.

### Accept-Language 파싱

`Accept-Language: zh-TW,zh;q=0.9,en;q=0.8` 같은 헤더를 제대로 파싱하지 않으면 지원하는 언어인데도 폴백으로 빠진다. `zh-TW`와 `zh-CN`은 다른 로케일이다. 브라우저가 보내는 값과 서버 내부 로케일 식별자가 일치하는지 먼저 확인해야 한다.

```python
from babel import Locale
from babel.core import UnknownLocaleError

def resolve_locale(accept_language: str, supported: list[str]) -> str:
    # Accept-Language 헤더를 파싱해 지원 목록과 매칭
    for lang_tag in parse_accept_language(accept_language):
        try:
            locale = Locale.parse(lang_tag, sep='-')
            canonical = str(locale)  # zh_TW 형식으로 정규화
            if canonical in supported:
                return canonical
        except UnknownLocaleError:
            continue
    return 'en'  # 기본값
```

중국어권을 추가할 때 가장 자주 겪는 문제다. `zh`로 들어온 요청을 `zh-CN`으로 처리할지 `zh-TW`로 처리할지 정책이 없으면 고객 민원이 생긴다.

### 로케일 감지 미들웨어

미들웨어에서 로케일 감지 우선순위를 명확히 정해야 한다. 일반적인 우선순위는 URL 경로 > 쿠키 > `Accept-Language` 헤더 > 기본값 순서다. 새 로케일 추가 시 이 파이프라인의 각 단계가 새 로케일을 인식하는지 테스트한다.

---

## 폰트·인코딩 비용

### CJK 폰트 번들 크기

일반 라틴 폰트 파일은 100~300KB 수준이다. CJK(한·중·일) 폰트는 글자 수가 많아서 전체 폰트 파일이 5~20MB에 달한다. 서브셋팅 없이 그냥 넣으면 초기 로딩 시간에 직격탄이 된다.

Google Fonts의 `&subset=korean` 파라미터나 `fonttools`로 사용할 글자만 잘라내는 서브셋팅이 필수다. 빌드 타임에 페이지별 사용 글자를 분석해 서브셋을 자동 생성하는 방식(Next.js의 `@next/font`)을 쓰면 런타임 비용을 대폭 줄일 수 있다.

```css
/* Google Fonts 서브셋 로딩 예시 */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap&subset=korean');
```

한국어 추가 시 폰트 서브셋팅 계획이 없으면 Lighthouse 점수가 한 번에 20~30점 떨어지는 경우가 있다.

### RTL 레이아웃 처리

아랍어, 히브리어 등 RTL 언어를 추가하면 CSS 레이아웃 전체를 검토해야 한다. `margin-left`, `padding-right` 같은 물리적 속성을 사용한 코드가 수백 곳이라면 하나씩 `margin-inline-start`, `padding-inline-end` 같은 논리적 속성으로 교체하는 작업이 필요하다. 컴포넌트가 많은 프로젝트에서 이 작업만 2~3주 걸리기도 한다.

```css
/* 물리적 속성 - RTL에서 레이아웃 깨짐 */
.sidebar {
  margin-left: 16px;
  text-align: left;
}

/* 논리적 속성 - RTL 자동 대응 */
.sidebar {
  margin-inline-start: 16px;
  text-align: start;
}
```

`html[dir="rtl"]` 선택자로 오버라이드하는 방식은 단기 해결책이고 장기적으로 관리 비용이 쌓인다.

---

## 로케일별 포맷 처리

날짜, 숫자, 통화는 로케일마다 형식이 다르다. `2024-01-15`를 미국은 `January 15, 2024`, 독일은 `15. Januar 2024`, 한국은 `2024년 1월 15일`로 표시한다.

### ICU 라이브러리 통합

직접 포맷 로직을 짜지 말고 ICU(International Components for Unicode) 라이브러리를 쓴다. Java는 `java.text.NumberFormat`, Python은 `babel`, JavaScript는 `Intl` 내장 객체가 있다.

```javascript
// Intl API - 로케일 추가해도 코드 변경 없음
const formatters = {
  date: (locale) => new Intl.DateTimeFormat(locale, {
    year: 'numeric', month: 'long', day: 'numeric'
  }),
  currency: (locale, currency) => new Intl.NumberFormat(locale, {
    style: 'currency', currency
  }),
  number: (locale) => new Intl.NumberFormat(locale)
};

// 사용
formatters.date('ko').format(new Date()); // 2024년 1월 15일
formatters.date('de').format(new Date()); // 15. Januar 2024
```

통화 코드(`KRW`, `JPY`, `USD`)는 로케일과 별개다. 로케일이 `ja`라도 표시 통화가 `USD`일 수 있으니 두 값을 분리해서 관리한다.

### 서버 사이드 포맷 주의

서버에서 날짜/숫자를 포맷해 HTML에 넣는 구조라면, 서버 JVM이나 Python 인터프리터의 기본 로케일 설정이 포맷 결과에 영향을 준다. 컨테이너 배포 환경에서 `LANG` 환경변수가 없으면 예상과 다른 포맷이 나올 수 있다. 포맷할 때 항상 로케일을 명시적으로 전달한다.

---

## 번역 파이프라인 비용

### 신규 문자열 수 추정

새 로케일을 추가하기 전에 번역해야 할 문자열이 몇 개인지 파악한다. i18next, react-intl 등의 키 파일을 분석하면 된다.

```bash
# i18next 기준 영어 기본 파일에서 키 수 확인
jq '[.. | strings] | length' locales/en/common.json

# 네임스페이스별 키 수
for f in locales/en/*.json; do
  echo "$f: $(jq '[.. | strings] | length' $f)"
done
```

문자열 수 × 단어 수 평균 × 단가로 번역 비용을 추산한다. 10만 단어 이상이면 외주 번역사 연계 전에 기계 번역 + 검수 워크플로를 설계하는 게 현실적이다.

### 번역 메모리 재사용률

TMS(Translation Management System)를 쓰면 이전에 번역한 문장을 재사용하는 번역 메모리(TM) 기능을 활용할 수 있다. 버튼 레이블, 공통 메시지 같은 반복 문자열은 TM 재사용률이 60~70%까지 나오기도 한다. 이 비율이 높을수록 비용과 납기가 줄어든다.

Phrase, Lokalise, Crowdin 같은 SaaS TMS를 쓰면 개발자-번역사 간 워크플로 설정에 시간이 들지만, 스프레드시트로 주고받는 것보다 누락과 버전 불일치가 훨씬 줄어든다.

---

## 인프라 비용

### CDN 언어별 라우팅 설정

CDN에서 언어별로 다른 캐시를 사용하려면 `Accept-Language` 헤더나 URL 경로를 기준으로 캐시 키를 나눠야 한다. 기본 설정으로는 언어 상관없이 같은 캐시를 돌려줄 수 있다.

CloudFront 기준으로는 Cache Policy에 `Accept-Language` 헤더를 포함시키거나, Lambda@Edge에서 로케일 쿠키를 읽어 Origin으로 전달하는 방식을 쓴다.

```
# CloudFront Cache Key 예시 (terraform)
resource "aws_cloudfront_cache_policy" "locale_aware" {
  name = "LocaleAwareCachePolicy"
  
  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "whitelist"
      cookies { items = ["locale"] }
    }
    headers_config {
      header_behavior = "whitelist"
      headers { items = ["Accept-Language"] }
    }
    query_strings_config {
      query_string_behavior = "none"
    }
  }
}
```

로케일 수만큼 캐시 공간이 늘어난다. 트래픽이 낮은 로케일은 캐시 히트율이 떨어져 오리진 요청 빈도가 올라간다.

### Redis 캐시 키 증가 예측

번역 결과나 로케일별 데이터를 Redis에 캐싱하는 구조라면, 로케일을 캐시 키에 포함시키는 패턴이 일반적이다.

```
product:detail:{id}:ko
product:detail:{id}:en
product:detail:{id}:ja
```

로케일이 N개 추가되면 캐시 키 수는 N배로 늘어난다. 현재 캐시 메모리 사용량과 키 TTL을 기반으로 로케일 추가 후 메모리 증가분을 미리 계산해야 한다. Redis 메모리 초과는 eviction으로 이어지고, 캐시 히트율 급락으로 DB에 부하가 몰린다.

```python
# 로케일 추가 후 캐시 메모리 증가 추산 예시
current_keys = redis.dbsize()
current_locales = 3
new_locales = 5

estimated_keys_after = current_keys * (new_locales / current_locales)
avg_value_size_bytes = 2048  # 실측 값으로 교체

estimated_memory_mb = (estimated_keys_after * avg_value_size_bytes) / (1024 * 1024)
print(f"예상 메모리 사용량: {estimated_memory_mb:.1f} MB")
```

### 스토리지 성장

번역 파일, 로케일별 이미지, 문서 등을 오브젝트 스토리지에 저장하면 로케일 수에 비례해 용량이 늘어난다. 텍스트 번역 파일 자체는 크지 않지만, 각 언어별 마케팅 이미지나 PDF 문서가 있다면 S3 비용이 선형 증가한다. 로케일별 에셋 관리 정책(공용 에셋 최대화, 언어별 에셋 최소화)을 미리 정해 두는 게 낫다.

---

## 성능 영향 측정

### 쿼리 플랜 변화

다국어 데이터를 별도 테이블로 관리하는 구조(번역 테이블 패턴)에서는 로케일 수가 늘어날수록 번역 테이블 행 수가 증가한다. 이 경우 JOIN 쿼리의 실행 계획이 바뀔 수 있다. 특히 번역 테이블에 복합 인덱스(`(entity_id, locale)`)가 없거나 통계가 오래됐으면 풀 스캔으로 빠지기도 한다.

```sql
-- 로케일 추가 후 실행 계획 확인
EXPLAIN (ANALYZE, BUFFERS)
SELECT p.id, pt.name, pt.description
FROM products p
JOIN product_translations pt 
  ON pt.product_id = p.id AND pt.locale = 'ja'
WHERE p.category_id = 5
ORDER BY p.created_at DESC
LIMIT 20;
```

로케일 추가 전후로 EXPLAIN 결과를 비교하고, 행 수 증가로 인해 Seq Scan이 Index Scan을 밀어내는지 확인한다. 필요하면 `ANALYZE product_translations;`로 통계를 갱신한다.

### 캐시 히트율 변화

로케일이 추가되면 캐시 키 공간이 넓어지고 각 키의 히트 빈도가 떨어진다. 특히 꼬리 로케일(트래픽이 적은 언어)은 캐시가 TTL 내에 재사용되지 않아 사실상 캐시 효과가 없다.

Redis에서 히트율 변화는 `INFO stats` 명령의 `keyspace_hits`와 `keyspace_misses`로 추적한다.

```bash
redis-cli INFO stats | grep -E 'keyspace_hits|keyspace_misses'
# keyspace_hits:8432100
# keyspace_misses:412300
# 히트율 = 8432100 / (8432100 + 412300) = 95.3%
```

새 로케일 트래픽이 늘어나는 기간에 이 수치를 모니터링한다. 히트율이 10% 이상 떨어지면 TTL 조정이나 캐시 워밍 전략을 검토한다.

---

## 점진적 언어 활성화

### Feature Flag per Locale

번역이 100% 완료되지 않은 상태에서 로케일을 전부 열면 빈 문자열이나 영어 폴백이 그대로 노출된다. 로케일 단위 feature flag로 활성화 범위를 제어한다.

```typescript
// 로케일별 활성화 상태 관리
interface LocaleConfig {
  code: string;
  enabled: boolean;
  completionRate: number;  // 번역 완료율 0~1
  enabledAt?: Date;
}

async function isLocaleEnabled(locale: string, userId?: string): Promise<boolean> {
  const config = await getLocaleConfig(locale);
  
  if (!config.enabled) return false;
  
  // 베타 테스터에게만 먼저 오픈하는 경우
  if (config.completionRate < 0.9 && userId) {
    return isBetaTester(userId);
  }
  
  return config.completionRate >= 0.95;
}
```

### 번역 완료율 기반 오픈

번역 완료율을 자동으로 계산해 임계값 도달 시 자동 활성화하는 파이프라인을 만들어 두면 수동 배포 없이 점진적 오픈이 된다.

```python
def calculate_completion_rate(locale: str) -> float:
    base_keys = load_keys('en')  # 기준 로케일 키 목록
    target_keys = load_keys(locale)
    
    total = len(base_keys)
    if total == 0:
        return 0.0
    
    translated = sum(1 for k in base_keys if k in target_keys and target_keys[k].strip())
    return translated / total

def sync_locale_status():
    for locale in ALL_LOCALES:
        rate = calculate_completion_rate(locale)
        
        if rate >= 0.95:
            enable_locale(locale)
        elif rate < 0.50:
            disable_locale(locale)
        # 0.50~0.95 구간은 베타 유저만 접근 가능
        
        update_locale_config(locale, completion_rate=rate)
```

번역 완료율 50% 미만은 비활성, 50~95%는 베타, 95% 이상에서 전체 오픈하는 구간을 프로젝트 상황에 맞게 조정한다. 미번역 문자열을 영어로 폴백할지, 아예 오류 페이지로 보낼지도 명확히 정책을 정해야 한다.

---

## 실제로 드는 비용 요약

새 로케일 하나를 제대로 추가하면 예상보다 훨씬 많은 곳을 건드리게 된다. 번역 자체가 가장 큰 비용이지만, 폰트 서브셋팅, CDN 캐시 정책, Redis 메모리 계획, 쿼리 플랜 검증이 모두 따라온다. RTL 언어라면 CSS 전면 검토까지 추가된다.

각 비용을 미리 추산하고 순서를 잡아야 오픈일에 화재가 나지 않는다. 번역 파이프라인과 feature flag 인프라는 첫 번째 로케일 추가 때 만들어 두면 두 번째부터는 비용이 절반으로 줄어든다.
