- First created By KYG at 2022-12-27

# Migration의 필요성
- 데이터베이스에 테이블을 생성 후 나중에 테이블 내 정보를 수정(테이블 컬럼명 수정, 테이블이름 수정,테이블제거....) 할때에 
- index.js, user.js, ....) 안에 파일을 바꾼다고 하여 그대로 반영되지는 않습니다.

# Migration 해결 방법

여기서는 마이그레이션을 이용하여 테이블의 내용을 바꿔서 DB에 적용을 해보도록 해보겠습니다.

마이그레이션을 적용하기 위해선 몇가지 모듈들을 설치를 진행해야 됩니다.

> npm i sequelize
![](../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_DFjtWM/스크린샷 2023-01-01 오후 3.30.50.png)

> npm i mysql2
> ![](../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_6bHg6l/스크린샷 2023-01-01 오후 3.31.48.png)

> npm i sequelize-cli
![](../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_1qa2Nj/스크린샷 2023-01-01 오후 3.33.32.png)


- mysql2란?
    - 데이터베이스와 서버 중간 사이 연결장치 (컴퓨터에 있는 키보드 마우스 드라이버 등)


# Migration의 심화 과정은 다음에 시간날 때 추가하도록 하겠습니다.. 