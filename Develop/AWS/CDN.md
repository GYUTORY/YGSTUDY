
# AWS CDN (Content Delivery Network) 설정 가이드

AWS의 Content Delivery Network (CDN)는 전 세계적으로 분산된 서버 네트워크를 활용하여 웹 콘텐츠를 사용자에게 신속하게 전달하는 서비스입니다. Amazon CloudFront는 AWS에서 제공하는 CDN 서비스로, 고성능과 보안성을 제공합니다.

## CDN의 주요 개념

### CDN이란?
CDN은 콘텐츠를 사용자와 가까운 서버에서 제공하여 대기 시간을 줄이고, 네트워크 성능을 개선하며, 대규모 트래픽에도 안정적으로 콘텐츠를 제공하는 기술입니다.

### Amazon CloudFront란?
Amazon CloudFront는 AWS의 글로벌 엣지 로케이션 네트워크를 이용하여 콘텐츠를 빠르고 안전하게 전달합니다. 주로 다음과 같은 콘텐츠에 사용됩니다:
- 정적 콘텐츠 (HTML, CSS, JS, 이미지)
- 동적 콘텐츠
- 스트리밍 비디오 및 오디오
- API 응답

## CloudFront 구성 요소
- **배포(Distribution)**: CloudFront 서비스를 통해 콘텐츠를 제공하는 설정 단위.
    - **웹(Web) 배포**: 웹 사이트 콘텐츠 배포.
    - **RTMP 배포**: 스트리밍 미디어 배포.
- **오리진(Origin)**: 콘텐츠 소스 서버로, S3 버킷, HTTP 서버, 또는 ALB 등이 가능합니다.
- **엣지 로케이션(Edge Location)**: 사용자에게 가장 가까운 CDN 서버 위치.

## Amazon CloudFront 설정 방법

### 1. S3 버킷 생성
1. AWS Management Console에 로그인합니다.
2. **S3** 서비스를 선택하고 새 버킷을 생성합니다.
    - 이름: `my-website-bucket`
    - 퍼블릭 액세스 설정: 퍼블릭 액세스를 허용합니다.
3. 정적 웹 사이트 콘텐츠를 S3 버킷에 업로드합니다.

### 2. CloudFront 배포 생성
1. **CloudFront** 서비스를 선택합니다.
2. **배포 생성(Create Distribution)** 버튼을 클릭합니다.
3. **오리진 설정**:
    - **오리진 도메인**: S3 버킷 URL 입력.
    - **오리진 액세스 제어(Origin Access Control)**: 퍼블릭 액세스 대신 CloudFront에 권한 위임을 설정할 수 있습니다.
4. **캐싱 설정**:
    - TTL(Time To Live): 캐시의 만료 시간을 설정합니다.
    - 사용자 지정 HTTP 헤더를 추가하거나 특정 파일 형식에 대해 규칙을 정의합니다.
5. **배포 생성** 버튼을 클릭하여 설정을 완료합니다.

### 3. 도메인 이름 연결
CloudFront 배포 생성 후, 할당된 도메인 이름을 Route 53 또는 다른 DNS 서비스에서 사용자 도메인에 연결합니다.

### 4. 테스트
브라우저에서 CloudFront 도메인을 통해 웹 콘텐츠에 액세스하여 설정이 올바르게 작동하는지 확인합니다.

## 예시: 정적 웹 사이트 배포
1. **S3 버킷 설정**:
    - `example-bucket`에 `index.html` 및 `style.css` 업로드.
    - S3 버킷 정책을 통해 퍼블릭 읽기 권한 부여.

2. **CloudFront 배포**:
    - 오리진 도메인: `example-bucket.s3.amazonaws.com`
    - 기본 캐시 동작: GET 및 HEAD 요청 허용.

3. **DNS 설정**:
    - Route 53에서 사용자 도메인(`www.example.com`)을 CloudFront 도메인(`d1234567890.cloudfront.net`)에 매핑.

4. **결과 확인**:
    - `www.example.com`에 접속하여 웹 사이트가 올바르게 표시되는지 확인.

## 주요 고려 사항
- **보안**: CloudFront는 AWS WAF 및 인증서를 활용하여 보안을 강화할 수 있습니다.
- **비용**: 사용량에 따라 과금되므로, 예상 트래픽을 고려한 예산 관리가 필요합니다.
- **지역 선택**: CloudFront는 전 세계에 분산된 엣지 로케이션을 사용하지만, 특정 지역에서만 콘텐츠를 제공하도록 제한할 수 있습니다.

---

AWS CloudFront는 확장성과 성능, 보안성을 제공하여 웹 애플리케이션 및 콘텐츠 전달에 필수적인 도구로 자리 잡고 있습니다. 위 가이드를 따라 CDN 설정을 시작해 보세요!
