
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

# package.json과 package-lock.json의 차이

package.json
1. 프로젝트의 메타데이터를 포함하는 파일입니다.
2. 프로젝트의 이름, 버전, 저작권 정보 등과 함께 의존성 패키지 목록을 정의합니다.
3. 프로젝트 개발자가 의존하는 패키지의 목록과 버전을 기술합니다.
4. 의존성 관리를 위해 npm (Node Package Manager) 명령어를 사용할 수 있습니다.
5. npm install 명령어를 실행하면 package.json 파일을 기반으로 의존성 패키지를 설치합니다.
6. 의존성 패키지 목록은 "dependencies"와 "devDependencies"라는 두 가지 섹션으로 구분될 수 있습니다. "dependencies"는 프로덕션 환경에서 필요한 패키지를, "devDependencies"는 개발 및 테스트에 필요한 패키지를 정의합니다.

package-lock.json
1. 의존성 패키지의 정확한 버전 및 의존 관계를 포함하는 자동 생성된 파일입니다.
2. package.json 파일에 명시된 의존성 패키지의 구체적인 버전 정보를 담고 있습니다.
3. package-lock.json은 프로젝트의 의존성 트리를 잠금(lock)하는 역할을 합니다. 이는 모든 개발자들이 동일한 패키지 버전을 사용하고, 의존성 충돌을 방지하기 위함입니다.
4. package-lock.json 파일은 일반적으로 프로젝트 루트 디렉토리에 저장되며, 버전 관리 시스템(Git 등)에 포함시키는 것이 좋습니다.
5. npm install 명령어를 실행할 때, package-lock.json 파일을 참조하여 의존성 패키지를 설치합니다. 이는 동일한 의존성 트리를 생성하여 패키지 버전을 일관되게 유지합니다.
6. package.json 파일이 수정되지 않는 한, package-lock.json 파일은 자동으로 업데이트되지 않습니다. 따라서 의존성 패키지를 추가하거나 업데이트할 때는 package.json 파일을 직접 수정하고 npm install 명령어를 실행하여 package-lock.json을 갱신해야 합니다.

정리
1. npm install 명령어를 실행할 때, npm은 먼저 package-lock.json 파일을 확인하여 의존성 패키지의 구체적인 버전과 의존 관계를 기반으로 패키지를 설치합니다.
2. package-lock.json 파일이 없을 경우에는 package.json 파일의 의존성 목록을 기반으로 패키지를 설치합니다.
3. package.json은 프로젝트의 의존성 패키지 목록과 메타데이터를 정의하고, package-lock.json은 의존성 패키지의 구체적인 버전 및 의존 관계를 포함하여 일관성과 안정성을 유지합니다.

