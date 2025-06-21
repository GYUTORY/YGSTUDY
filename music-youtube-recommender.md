# 🎵 추억 음악 소환기 (NestJS, Node 20)

## 1. 프로젝트 개요
- YouTube Data API v3를 활용하여 특정 연도대의 인기 음악을 추천하는 CLI 애플리케이션
- NestJS CLI 기반으로 구현하여 커맨드 라인에서 실행 가능
- 메모리 기반으로 동작하며, 별도의 데이터베이스 없이 구현
- 향수를 자극하는 음악 큐레이션 기능 제공

## 2. 기술 스택 상세 명세

### 2.1. 핵심 기술
- Node.js 20 LTS
- NestJS 10.x
- TypeScript 5.x
- YouTube Data API v3

### 2.2. 주요 패키지
- @nestjs/cli: NestJS CLI 도구
- @nestjs/config: 환경 변수 관리
- axios: HTTP 클라이언트
- commander: CLI 커맨드 구현
- inquirer: CLI 인터랙티브 프롬프트
- dotenv: 환경 변수 로딩
- class-validator: DTO 유효성 검증
- class-transformer: 객체 변환

## 3. 상세 기능 명세

### 3.1. YouTube API 연동
- [필수] YouTube Data API v3를 통한 연도별 인기 음악 검색
  - `search.list` 엔드포인트 사용
  - 연도 기반 검색 쿼리 생성
  - 필요한 필드: snippet.title, snippet.channelTitle, id.videoId
- [필수] API 키는 .env 파일에서 관리
- [필수] 검색 키워드 템플릿은 .env 파일에서 설정 가능

### 3.2. 연도별 음악 추천 로직
- [필수] 입력된 연도대에 해당하는 인기 음악 검색
- [필수] 검색 결과에서 랜덤으로 곡 선택
- [필수] 선택된 곡의 메타데이터 추출
  - 제목 (snippet.title)
  - 채널명 (snippet.channelTitle)
  - 영상 URL (https://youtube.com/watch?v={videoId})
  - 발매 연도 정보

### 3.3. CLI 인터페이스
- [필수] NestJS CLI 커맨드 구현
  - `nest recommend` 명령어로 실행
  - 추천 결과를 콘솔에 포맷팅하여 출력
- [선택] 인터랙티브 모드 지원
  - inquirer를 사용한 대화형 인터페이스
  - 연도대 선택 옵션 (90년대, 2000년대 등)
  - 재추천 기능

### 3.4. 에러 처리
- [필수] YouTube API 호출 실패 시 적절한 에러 메시지 출력
- [필수] 검색 결과 없음 처리
- [필수] API 할당량 초과 시 에러 처리
- [필수] 환경 변수 누락 시 안내 메시지

## 4. 코드 구조

```
src/
  ├── app.module.ts                 # 루트 모듈
  ├── youtube/
  │     ├── dto/
  │     │     ├── search.dto.ts     # 검색 응답 DTO
  │     │     └── video.dto.ts      # 비디오 정보 DTO
  │     ├── youtube.service.ts      # YouTube API 연동 서비스
  │     └── youtube.module.ts       # YouTube 모듈
  ├── cli/
  │     ├── commands/
  │     │     └── recommend.command.ts  # 추천 커맨드
  │     └── cli.module.ts          # CLI 모듈
  └── config/
        └── configuration.ts        # 설정 관리
```

## 5. 환경 변수 설정

```env
# YouTube API 설정
YOUTUBE_API_KEY=your_api_key_here

# 검색 설정
YOUTUBE_SEARCH_QUERY_TEMPLATE="{year}년대 인기곡"
YOUTUBE_API_BASE_URL=https://www.googleapis.com/youtube/v3
YOUTUBE_API_MAX_RESULTS=50
```

## 6. 실행 방법

1. 프로젝트 설정
```bash
# 의존성 설치
npm install

# 환경 변수 설정
cp .env.example .env
# .env 파일에 API 키 입력
```

2. 개발 모드 실행
```bash
npm run start:dev
```

3. 추천 명령어 실행
```bash
# 기본 실행
nest recommend --year 2000

# 인터랙티브 모드
nest recommend --interactive
```

## 7. 출력 예시

```
🎵 2000년대 추억의 음악 🎵

제목: [노래 제목]
아티스트: [아티스트명]
발매년도: 2005
URL: https://youtube.com/watch?v=xxxxxxx

실행 시간: 2024-03-21 15:30:45
```

## 8. 향후 확장 계획
- [ ] 장르별 필터링 기능
- [ ] 아티스트별 추천 기능
- [ ] 플레이리스트 생성 기능
- [ ] 음악 차트 연동
- [ ] 사용자 히스토리 관리

## AI에게 단계별로 요청할 수 있는 20단계 명령어 가이드

1. **NestJS 기반 Node.js 20 TypeScript 프로젝트 초기화**
   - nostalgia-music-recommender라는 이름으로 NestJS 프로젝트를 TypeScript로 생성하고, package.json의 engines에 node 20 이상을 명시해줘.

2. **프로젝트 환경설정 파일 및 패키지 준비**
   - .env, .env.example 파일을 만들고, .gitignore에 .env와 .env.*를 추가해줘. @nestjs/config, dotenv 패키지를 설치해줘.

3. **YouTube API 연동 구조 생성**
   - src/youtube 디렉토리와 youtube.module.ts, youtube.service.ts, dto 폴더 및 DTO 파일을 생성해줘. youtube.service.ts에 YouTube Data API v3로 연도별 음악을 검색하는 메서드의 뼈대를 만들어줘.

4. **CLI 명령어 구조 생성**
   - src/cli/commands/recommend.command.ts 파일을 만들고, nest recommend 명령어로 실행할 수 있도록 커맨드 뼈대를 만들어줘. 추천 결과를 콘솔에 출력하는 기본 코드를 작성해줘.

5. **환경변수 유효성 검사 및 설정 관리**
   - 환경변수 누락 시 에러를 출력하도록 설정하고, config/configuration.ts 파일을 만들어 환경설정 모듈을 구성해줘.

6. **YouTube API 실제 데이터 연동 구현**
   - youtube.service.ts에서 실제로 YouTube Data API를 호출해 연도별 인기 음악을 검색하는 기능을 완성해줘. (axios 사용)

7. **연도별 음악 추천 로직 구현**
   - 검색된 음악 목록에서 랜덤으로 1개를 추출하는 메서드를 youtube.service.ts에 구현해줘.

8. **CLI 추천 결과 포맷팅 및 출력 개선**
   - recommend.command.ts에서 추천 결과를 예쁘게 포맷팅해서 출력하도록 개선해줘.

9. **연도대 선택 기능 구현**
   - inquirer로 CLI에서 연도대를 선택할 수 있게 해줘.

10. **에러 처리 및 사용자 친화적 메시지 구현**
    - API 호출 실패, 할당량 초과, 검색 결과 없음 등 다양한 에러 상황에 대해 사용자에게 친절한 메시지를 출력하도록 해줘.

11. **단위 테스트 환경 구축**
    - Jest를 사용해 단위 테스트 환경을 구축하고, youtube.service.ts의 주요 메서드에 대한 테스트 코드를 작성해줘.

12. **통합 테스트 환경 구축**
    - e2e 테스트 폴더를 만들고, CLI 명령어 전체 플로우에 대한 통합 테스트 코드를 작성해줘.

13. **테스트 커버리지 리포트 설정**
    - Jest 커버리지 리포트가 나오도록 설정하고, npm script에 커버리지 명령어를 추가해줘.

14. **Prettier, ESLint 등 코드 스타일 도구 적용**
    - Prettier, ESLint를 설치하고, 기본 설정 파일(.prettierrc, .eslintrc.js 등)을 추가해줘.

15. **커밋 메시지 규칙 및 husky/lint-staged 적용**
    - Conventional Commits 규칙을 적용하고, husky와 lint-staged로 커밋 전 코드 스타일 체크를 자동화해줘.

16. **Dockerfile 및 .dockerignore 작성**
    - NestJS 앱을 위한 Dockerfile과 .dockerignore 파일을 작성해줘. (환경변수는 빌드 타임에 주입)

17. **도커 컴포즈(docker-compose.yml) 작성**
    - 개발 및 테스트를 위한 docker-compose.yml 파일을 작성해줘.

18. **GitHub Actions를 활용한 CI 파이프라인 작성**
    - GitHub Actions 워크플로우 파일(.github/workflows/ci.yml)을 만들어, PR/Push 시 테스트와 린트가 자동으로 실행되게 해줘.

19. **CD(배포) 파이프라인 예시 작성**
    - Docker Hub로 이미지를 푸시하고, 서버에 배포하는 CD 워크플로우 예시 파일(.github/workflows/cd.yml)을 작성해줘.

20. **README.md 작성 및 프로젝트 사용법 문서화**
    - 프로젝트 개요, 설치, 실행, 테스트, 배포, 환경변수 등 모든 내용을 정리한 README.md를 작성해줘. 