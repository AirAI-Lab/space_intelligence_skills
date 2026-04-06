# ============================================
# C-RADIOv4 云端推理服务 Dockerfile
# 基础镜像: nvidia/cuda:12.8.0-runtime-ubuntu22.04
# 功能: MQTT 推理服务，接收关键帧执行开放词汇分割
# ============================================

FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04

# 环境变量
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai

# 系统依赖 (含中文字体)
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3-venv \
    libgl1-mesa-glx \
    libglib2.0-0 \
    fonts-noto-cjk \
    fontconfig \
    && ln -snf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && rm -rf /var/lib/apt/lists/*

# 虚拟环境
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 安装 PyTorch (CUDA 12.8)
RUN pip install --no-cache-dir torch==2.10.0+cu128 torchvision==0.25.0+cu128 \
    --index-url https://download.pytorch.org/whl/cu128

# 安装依赖
COPY cloud_requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/cloud_requirements.txt

# 工作目录
WORKDIR /app

# 复制项目代码
COPY cloud/ /app/cloud/
COPY models/water_inspection/ /app/models/water_inspection/

# 模型权重通过 volume 挂载，不打入镜像
# 挂载点: /app/models/water_inspection/checkpoints/

EXPOSE 5003

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python3 -c "import paho.mqtt.client; print('ok')" || exit 1

CMD ["python3", "cloud/radio_infer_server.py"]
