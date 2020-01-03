FROM maven:3.6.0-jdk-8-alpine AS MAVEN_TOOL_CHAIN
COPY pom.xml /tmp/
COPY src /tmp/src/
WORKDIR /tmp/
RUN mvn clean install
 
FROM tomcat:9.0-jre8-alpine
COPY --from=MAVEN_TOOL_CHAIN /tmp/target/odata-server*.war $CATALINA_HOME/webapps/odata-server.war

EXPOSE 8080

CMD ["catalina.sh", "run"]
