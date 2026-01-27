# ============================================
# 后端 Dockerfile (Spring Boot 3.x)
# ============================================

# 阶段1: 构建阶段
FROM maven:3.9-eclipse-temurin-21 AS builder

WORKDIR /app

# 复制 Maven 配置和 pom.xml
COPY settings.xml /root/.m2/settings.xml
COPY pom.xml .

# 下载依赖（利用 Docker 缓存，使用阿里云镜像）
RUN mvn dependency:go-offline -B

# 复制源代码
COPY src ./src

# 构建应用
RUN mvn clean package -DskipTests

# 阶段2: 运行阶段
FROM eclipse-temurin:21-jre-alpine

WORKDIR /app

# 创建非 root 用户
RUN addgroup -S spring && adduser -S spring -G spring

# 复制构建产物
COPY --from=builder /app/target/*.jar app.jar

# 修改权限
RUN chown -R spring:spring /app

USER spring

# 暴露端口
EXPOSE 8080

# JVM 优化参数
ENV JAVA_OPTS="-XX:+UseContainerSupport \
               -XX:MaxRAMPercentage=75.0 \
               -XX:InitialRAMPercentage=50.0 \
               -XX:+UseG1GC \
               -Djava.security.egd=file:/dev/./urandom"

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/actuator/health || exit 1

# 启动应用
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
