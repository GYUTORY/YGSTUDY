---
title: BFF 부분 실패 처리
tags: [BFF, MSA, 장애처리, Promise.allSettled, Fallback, Circuit Breaker]
updated: 2026-07-25
---

# BFF 부분 실패 처리

BFF가 하위 서비스 5개를 병렬 호출할 때, 하나가 죽으면 전체 응답을 실패로 내려야 할까. 대부분의 경우 그렇지 않다. 상품 상세 페이지에서 리뷰 서비스가 응답하지 않아도 상품 정보, 가격, 재고는 보여줄 수 있다.

이 판단을 BFF에서 명확하게 구현하지 않으면 두 가지 상황이 생긴다. 하나는 선택적인 서비스 하나가 죽었는데 전체가 500으로 터지는 것이고, 다른 하나는 절반만 채워진 데이터를 받은 클라이언트가 어디가 빠진지 모르는 것이다. 둘 다 실무에서 자주 겪는 문제다.

## 필수 서비스와 선택 서비스 분리

서비스 호출 전에 페이지 렌더링의 필수 여부를 먼저 결정해야 한다.

**필수 서비스**는 실패하면 해당 페이지 자체를 보여줄 수 없는 서비스다. 상품 상세 페이지에서 상품 정보 서비스가 여기 해당한다. 가격 서비스도 결제 플로우가 연결돼 있으면 필수로 분류한다.

**선택 서비스**는 실패해도 페이지는 보여줄 수 있는 서비스다. 추천 상품, 리뷰, 최근 본 상품, 연관 태그 등이다.

```typescript
const REQUIRED_SERVICES = ['product', 'pricing'] as const;
const OPTIONAL_SERVICES = ['inventory', 'review', 'recommendation'] as const;
```

이 구분이 없으면 어떤 실패가 치명적인지 코드 레벨에서 표현할 방법이 없다. 팀에서 구분 기준을 먼저 합의하고 코드에 반영해야 한다.

처음에는 명확해 보여도 기능이 추가되면서 경계가 흐려지는 경우가 많다. 쿠폰 서비스가 처음에는 선택이었다가 "쿠폰 자동 적용" 기능이 생기면서 사실상 필수가 된다. 서비스 분류를 코드 상수로만 관리하지 말고, 실패 시 동작 명세를 팀 내에서 정기적으로 검토하는 게 필요하다.

## Promise.allSettled로 부분 성공 처리

`Promise.all`은 하나라도 reject되면 전체가 reject된다. BFF에서 쓰면 안 되는 이유다. `Promise.allSettled`는 모든 프로미스가 settled될 때까지 기다리고, 각각의 상태를 배열로 돌려준다.

```typescript
async function fetchProductPageData(productId: string) {
  const [productResult, pricingResult, inventoryResult, reviewResult, recommendResult] =
    await Promise.allSettled([
      productService.get(productId),
      pricingService.get(productId),
      inventoryService.get(productId),
      reviewService.list(productId),
      recommendationService.get(productId),
    ]);

  // 필수 서비스 실패 시 전체 실패로 처리
  if (productResult.status === 'rejected') {
    throw new ServiceUnavailableError('product', productResult.reason);
  }
  if (pricingResult.status === 'rejected') {
    throw new ServiceUnavailableError('pricing', pricingResult.reason);
  }

  const failedOptionalServices: string[] = [];
  if (inventoryResult.status === 'rejected') failedOptionalServices.push('inventory');
  if (reviewResult.status === 'rejected') failedOptionalServices.push('review');
  if (recommendResult.status === 'rejected') failedOptionalServices.push('recommendation');

  return {
    data: {
      product: productResult.value,
      pricing: pricingResult.value,
      inventory: inventoryResult.status === 'fulfilled' ? inventoryResult.value : null,
      reviews: reviewResult.status === 'fulfilled' ? reviewResult.value : [],
      recommendations: recommendResult.status === 'fulfilled' ? recommendResult.value : [],
    },
    meta: {
      degraded: failedOptionalServices.length > 0,
      failedServices: failedOptionalServices,
    },
  };
}
```

선택 서비스 실패 시 null이나 빈 배열로 처리하는 게 일반적이다. 중요한 건 클라이언트에 "실패했다"는 사실을 명시적으로 알리는 것이다.

## 클라이언트에 degraded 상태 전달

실패한 서비스 목록을 응답 메타에 포함시킨다. 클라이언트가 어떤 기능이 지금 안 되는지 알아야 UI에서 처리할 수 있다.

```typescript
interface PageResponse<T> {
  data: T;
  meta: {
    degraded: boolean;
    failedServices: string[];
  };
}
```

클라이언트에서는 `meta.degraded`가 true면 리뷰 섹션 대신 "일시적으로 표시할 수 없습니다"를 보여주거나, `meta.failedServices`를 보고 어떤 섹션을 숨길지 결정한다. HTTP 상태코드는 200을 유지하는 게 맞다. 207 Multi-Status를 쓰는 팀도 있는데, HTTP 클라이언트 라이브러리 대부분이 2xx를 일괄 정상 처리하는 방식이라 200 + meta 구조가 실용적으로 더 낫다.

## 타임아웃별 fallback 처리

`Promise.allSettled` 자체는 타임아웃을 다루지 않는다. 리뷰 서비스가 10초 동안 응답 안 하면 그만큼 기다린다. 서비스별 타임아웃을 직접 구현해야 한다.

```typescript
function withTimeout<T>(promise: Promise<T>, ms: number, service: string): Promise<T> {
  return Promise.race([
    promise,
    new Promise<never>((_, reject) =>
      setTimeout(() => reject(new TimeoutError(`${service} timed out after ${ms}ms`)), ms),
    ),
  ]);
}

const [productResult, pricingResult, inventoryResult, reviewResult, recommendResult] =
  await Promise.allSettled([
    withTimeout(productService.get(productId), 2000, 'product'),
    withTimeout(pricingService.get(productId), 2000, 'pricing'),
    withTimeout(inventoryService.get(productId), 1000, 'inventory'),
    withTimeout(reviewService.list(productId), 800, 'review'),
    withTimeout(recommendationService.get(productId), 500, 'recommendation'),
  ]);
```

선택 서비스일수록 타임아웃을 짧게 잡는다. 추천 서비스가 500ms 내에 응답 안 하면 빈 배열로 내려보내는 게 전체 응답 시간을 지키는 방법이다.

필수 서비스 타임아웃은 신중하게 설정해야 한다. 너무 짧으면 정상 상황에서도 타임아웃이 나고, 너무 길면 장애 시 응답이 느려진다. p99 레이턴시 기준으로 2~3배 정도가 실무적인 기준점이다.

cascading timeout 문제도 있다. 필수 서비스 타임아웃을 2초로 잡았는데 BFF HTTP 서버 타임아웃이 3초면, 타임아웃이 발동하기 전에 503이 나간다. 각 레이어의 타임아웃 설정이 `BFF 타임아웃 > 하위 서비스 타임아웃 합계`가 되도록 맞춰야 한다.

## fallback 데이터 활용

선택 서비스 실패 시 캐시된 데이터를 fallback으로 쓰는 경우가 있다. 추천 서비스가 죽어도 Redis에 캐시된 어제 추천 데이터를 보여주는 식이다.

```typescript
private async fetchRecommendationsWithFallback(productId: string): Promise<Recommendation[]> {
  try {
    const result = await withTimeout(
      this.recommendationService.get(productId),
      500,
      'recommendation',
    );
    await this.redis.set(`recommendations:${productId}`, JSON.stringify(result), { ttl: 3600 });
    return result;
  } catch {
    const cached = await this.redis.get(`recommendations:${productId}`);
    return cached ? JSON.parse(cached) : [];
  }
}
```

이 패턴은 선택 서비스에만 적용해야 한다. 필수 서비스를 오래된 캐시로 대체하면 재고가 0인 상품 결제가 통과되는 식의 데이터 정합성 문제가 생긴다.

## 실패 로깅

선택 서비스 실패를 조용히 fallback 처리하면 장애를 놓친다. 실패한 서비스는 warn 레벨로 반드시 로깅해야 한다.

```typescript
if (reviewResult.status === 'rejected') {
  logger.warn('Optional service failed', {
    service: 'review',
    productId,
    error: reviewResult.reason?.message,
    isTimeout: reviewResult.reason instanceof TimeoutError,
  });
  failedOptionalServices.push('review');
}
```

로깅은 하되 응답에서 차단하지 않는 것이다. 일정 기간 동안 실패율이 임계치를 넘으면 알림이 오도록 별도로 구성해야 한다. 선택 서비스라도 지속적으로 실패하면 Circuit Breaker를 붙여서 장애 서비스로 불필요한 요청을 막는 게 맞다.

## NestJS 구현 패턴

NestJS에서 위 구조를 서비스 클래스로 정리하면 아래처럼 된다.

```typescript
@Injectable()
export class ProductBffService {
  constructor(
    private readonly productService: ProductHttpService,
    private readonly pricingService: PricingHttpService,
    private readonly reviewService: ReviewHttpService,
    private readonly redis: RedisService,
    private readonly logger: Logger,
  ) {}

  async getProductPage(productId: string): Promise<ProductPageResponse> {
    const [productResult, pricingResult, reviewResult] = await Promise.allSettled([
      withTimeout(this.productService.get(productId), 2000, 'product'),
      withTimeout(this.pricingService.get(productId), 2000, 'pricing'),
      withTimeout(this.reviewService.list(productId), 800, 'review'),
    ]);

    if (productResult.status === 'rejected') {
      throw new ServiceUnavailableException('Product service unavailable');
    }

    const failedOptionalServices: string[] = [];

    if (reviewResult.status === 'rejected') {
      this.logger.warn('Review service failed', {
        productId,
        error: reviewResult.reason?.message,
      });
      failedOptionalServices.push('review');
    }

    return {
      data: {
        product: productResult.value,
        pricing: pricingResult.status === 'fulfilled'
          ? pricingResult.value
          : await this.getPricingFallback(productId),
        reviews: reviewResult.status === 'fulfilled' ? reviewResult.value : [],
      },
      meta: {
        degraded: failedOptionalServices.length > 0,
        failedServices: failedOptionalServices,
      },
    };
  }

  private async getPricingFallback(productId: string): Promise<Pricing | null> {
    const cached = await this.redis.get(`pricing:${productId}`);
    return cached ? JSON.parse(cached) : null;
  }
}
```

가격 서비스는 필수와 선택 사이 어딘가로 취급하는 케이스가 있다. 가격이 없으면 구매는 못하지만, 캐시된 가격을 임시로 보여주면서 결제 버튼만 비활성화하는 방식이다. 이런 경우 `meta.failedServices`에 `pricing`을 포함시켜서 클라이언트가 결제 버튼 상태를 조건부로 처리하도록 한다.
