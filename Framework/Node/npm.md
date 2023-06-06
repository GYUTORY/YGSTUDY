
# npm
- Node.js에서 사용되는 패키지 관리자입니다.
- "npm"은 "Node Package Manager"의 약자로, Node.js 애플리케이션에서 필요한 외부 모듈을 설치, 관리 및 업데이트할 수 있도록 도와줍니다.
- npm을 사용하면 패키지를 검색하고 설치하고 삭제하는 등의 작업을 쉽게 수행할 수 있습니다.


# npm의 옵션
install
- npm install 명령은 패키지를 설치하는데 사용됩니다. 
- 일반적으로 npm install <package> 형식으로 사용되며, <package>는 설치할 패키지의 이름입니다. 
- 이 명령은 패키지를 현재 프로젝트의 node_modules 폴더에 설치합니다.


uninstall
- npm uninstall 명령은 패키지를 제거하는데 사용됩니다.
- 일반적으로 npm uninstall <package> 형식으로 사용되며, <package>는 제거할 패키지의 이름입니다.


update
- npm update 명령은 패키지를 업데이트하는데 사용됩니다.
- npm update <package> 형식으로 사용되며, <package>는 업데이트할 패키지의 이름입니다.
- 패키지의 새 버전이 설치되고, package.json 파일에 업데이트된 버전이 기록됩니다.


search
- npm search 명령은 npm 레지스트리에서 패키지를 검색하는데 사용됩니다.
- npm search <keyword> 형식으로 사용되며, <keyword>는 검색할 키워드입니다. 
- 이 명령은 키워드와 일치하는 패키지를 찾아 출력합니다.


list
- npm list 명령은 현재 프로젝트의 종속성 트리를 보여줍니다. 
- npm list 명령을 실행하면 프로젝트의 종속성 트리가 표시되고, 설치된 패키지들의 계층 구조와 버전 정보를 확인할 수 있습니다.


# npm install 옵션
npm install 명령은 패키지를 설치하는데 사용되며, 다양한 옵션을 지원하여 설치 과정을 제어할 수 있습니다. 

--save 또는 -S
- npm install <package> --save 명령은 패키지를 설치하면서 package.json 파일에 해당 패키지를 종속성(dependency)으로 추가합니다. 
- 이를 통해 프로젝트를 다른 환경이나 다른 개발자와 공유할 때 패키지 종속성을 쉽게 관리할 수 있습니다. -S 옵션은 --save의 축약형입니다.


--save-dev 또는 -D
- npm install <package> --save-dev 명령은 개발 종속성(devDependency)으로 패키지를 설치하고, package.json 파일에 해당 패키지를 추가합니다. 
- 개발 종속성은 주로 개발 시에만 필요한 도구나 라이브러리로, 프로덕션 환경에서는 사용되지 않습니다.
- 예를 들어, 테스트 프레임워크나 빌드 도구 등이 개발 종속성으로 설치될 수 있습니다. -D 옵션은 --save-dev의 축약형입니다.


--global 또는 -g
- npm install <package> --global 명령은 전역적으로 패키지를 설치합니다.
- 이는 특정 프로젝트에 종속되지 않고 시스템 전체에서 사용할 수 있는 패키지를 설치할 때 사용됩니다.
- 전역 패키지는 터미널에서 실행 가능한 명령어나 도구로 사용될 수 있습니다. -g 옵션은 --global의 축약형입니다.

--production
- npm install --production 명령은 프로덕션 환경에서 필요한 종속성만 설치합니다. 개발 종속성은 설치되지 않으며, devDependencies 필드에 명시된 패키지들은 무시됩니다. 
- 이 옵션은 프로덕션 배포 시에 필요한 패키지만 설치하고 싶을 때 사용됩니다.

--no-save
- npm install <package> --no-save 명령은 패키지를 설치할 때 package.json 파일을 업데이트하지 않습니다. 
- 종속성을 자동으로 추가하지 않고, 패키지를 설치한 후에도 package.json 파일은 변경되지 않습니다.