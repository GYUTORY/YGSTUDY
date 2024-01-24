# pom.xml 기본 설정하기

여러분들을 위한 저를 위한 pom.xml 기본 설정

1. Mac은 ojdbc10을 사용하지만 window는 주로 ojdbc8을 사용한다.

> pom.xml
> 
    <dependencies>
		    <!-- Spring -->
		<dependency>
			<groupId>org.springframework</groupId>
			<artifactId>spring-context</artifactId>
			<version>${org.springframework-version}</version>
			<exclusions>
				<!-- Exclude Commons Logging in favor of SLF4j -->
				<exclusion>
					<groupId>commons-logging</groupId>
					<artifactId>commons-logging</artifactId>
				 </exclusion>
			</exclusions>
		</dependency>
		<dependency>
			<groupId>org.springframework</groupId>
			<artifactId>spring-webmvc</artifactId>
			<version>${org.springframework-version}</version>
		</dependency>

		<!-- AspectJ -->
		<dependency>
			<groupId>org.aspectj</groupId>
			<artifactId>aspectjrt</artifactId>
			<version>${org.aspectj-version}</version>
		</dependency>	
		
		<!-- Logging -->
		<dependency>
			<groupId>org.slf4j</groupId>
			<artifactId>slf4j-api</artifactId>
			<version>${org.slf4j-version}</version>
		</dependency>
		<dependency>
			<groupId>org.slf4j</groupId>
			<artifactId>jcl-over-slf4j</artifactId>
			<version>${org.slf4j-version}</version>
			<scope>runtime</scope>
		</dependency>
		<dependency>
			<groupId>org.slf4j</groupId>
			<artifactId>slf4j-log4j12</artifactId>
			<version>${org.slf4j-version}</version>
			<scope>runtime</scope>
		</dependency>
		<dependency>
			<groupId>log4j</groupId>
			<artifactId>log4j</artifactId>
			<version>1.2.15</version>
			<exclusions>
				<exclusion>
					<groupId>javax.mail</groupId>
					<artifactId>mail</artifactId>
				</exclusion>
				<exclusion>
					<groupId>javax.jms</groupId>
					<artifactId>jms</artifactId>
				</exclusion>
				<exclusion>
					<groupId>com.sun.jdmk</groupId>
					<artifactId>jmxtools</artifactId>
				</exclusion>
				<exclusion>
					<groupId>com.sun.jmx</groupId>
					<artifactId>jmxri</artifactId>
				</exclusion>
			</exclusions>
			<scope>runtime</scope>
		</dependency>

		<!-- oraclepki -->
		<dependency>
		    <groupId>com.oracle.database.security</groupId>
		    <artifactId>oraclepki</artifactId>
		    <version>19.10.0.0</version>
		</dependency>
				
		<!-- osdt_cert -->
		<dependency>
		    <groupId>com.oracle.database.security</groupId>
		    <artifactId>osdt_cert</artifactId>
		    <version>19.10.0.0</version>
		</dependency>
		
		<!-- osdt_core -->
		<dependency>
		    <groupId>com.oracle.database.security</groupId>
		    <artifactId>osdt_core</artifactId>
		    <version>19.10.0.0</version>
		</dependency>
		
		
		<!-- ojdbc10 -->
		<dependency>
		    <groupId>com.oracle.database.jdbc</groupId>
		    <artifactId>ojdbc10</artifactId>
		    <version>19.10.0.0</version>
		</dependency>
		
		<!--Mybatis:DB Framework -->
		<dependency>
		    <groupId>org.mybatis</groupId>
		    <artifactId>mybatis</artifactId>
		    <version>3.5.6</version>
		</dependency>
		
		<!-- Mybatis-spring -->
		<dependency>
		    <groupId>org.mybatis</groupId>
		    <artifactId>mybatis-spring</artifactId>
		    <version>2.0.6</version>
		</dependency>
		
		<!-- 상용서비스(connection pool)를 위한 POOL -->
		
		<!-- jackson: 메시지 컨버터, 초고속, 추가적인 셋팅 필요없음 -->
		<!-- https://mvnrepository.com/artifact/com.fasterxml.jackson.core/jackson-databind -->
		<dependency>
		    <groupId>com.fasterxml.jackson.core</groupId>
		    <artifactId>jackson-databind</artifactId>
		    <version>2.13.0</version>
		</dependency>
				
		
		
		
		<!-- 유틸리티 -->
		<!-- Gson -->
		<dependency>
		    <groupId>com.google.code.gson</groupId>
		    <artifactId>gson</artifactId>
		    <version>2.8.6</version>
		</dependency>
		

		
		<!-- log4jdbc -->
		<!-- https://mvnrepository.com/artifact/org.bgee.log4jdbc-log4j2/log4jdbc-log4j2-jdbc4.1 -->
		<dependency>
		    <groupId>org.bgee.log4jdbc-log4j2</groupId>
		    <artifactId>log4jdbc-log4j2-jdbc4.1</artifactId>
		    <version>1.16</version>
		</dependency>
		
		<!-- lombok -->
		<!-- https://mvnrepository.com/artifact/org.projectlombok/lombok -->
		<dependency>
		    <groupId>org.projectlombok</groupId>
		    <artifactId>lombok</artifactId>
		    <version>1.18.22</version>
		    <scope>provided</scope>
		</dependency>
		
		
		<!-- @Inject -->
		<dependency>
			<groupId>javax.inject</groupId>
			<artifactId>javax.inject</artifactId>
			<version>1</version>
		</dependency>
				
		<!-- javax.servlet-api -->
		<dependency>
		    <groupId>javax.servlet</groupId>
		    <artifactId>javax.servlet-api</artifactId>
		    <version>4.0.1</version>
		    <scope>provided</scope>
		</dependency>

		<!--  Spring JDBC -->
		<dependency>
		    <groupId>org.springframework</groupId>
		    <artifactId>spring-jdbc</artifactId>
		    <version>5.2.12.RELEASE</version>
		</dependency>
		
		<!--  파일업, 다운로드 -->
		<dependency>
		    <groupId>commons-fileupload</groupId>
		    <artifactId>commons-fileupload</artifactId>
		    <version>1.4</version>
		</dependency>
		
		<!-- 파일 입출력 -->
		<dependency>
		    <groupId>commons-io</groupId>
		    <artifactId>commons-io</artifactId>
		    <version>2.11.0</version>
		</dependency>
		
		<!-- 암호화위해 spring-security-core -->
		<dependency>
		    <groupId>org.springframework.security</groupId>
		    <artifactId>spring-security-core</artifactId>
		    <version>5.2.2.RELEASE</version>
		</dependency>
		
		<!-- HikariCP -->
		<dependency>
		    <groupId>com.zaxxer</groupId>
		    <artifactId>HikariCP</artifactId>
		    <version>4.0.3</version>
		</dependency>