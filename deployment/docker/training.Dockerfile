# ============================================
# 训练服务 Dockerfile (PyTorch + YOLO + CUDA)
# 基础镜像: nvcr.io/nvidia/cuda:12.5.0-devel-ubuntu22.04
# ============================================

# 阶段1: 基础环境
FROM nvcr.io/nvidia/cuda:12.5.0-devel-ubuntu22.04 AS base

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3-venv \
    git \
    wget \
    curl \
    vim \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 升级 pip
RUN pip install --upgrade pip setuptools wheel

# 阶段2: Python 依赖
FROM base AS dependencies

# 安装 PyTorch (CUDA 12.5)
# 注意: 需要确认 PyTorch 版本支持 CUDA 12.5
RUN pip install torch==2.5.0 torchvision==0.20.0 torchaudio==2.5.0 --index-url https://download.pytorch.org/whl/cu125

# 复制 requirements.txt
COPY training/requirements.txt /tmp/

# 安装项目依赖
RUN pip install -r /tmp/requirements.txt

# 阶段3: 应用程序
FROM dependencies AS app

WORKDIR /app

# 复制训练框架代码
COPY training/ /app/

# 安装训练框架
RUN pip install -e .

# 创建目录
RUN mkdir -p /app/runs /app/models /app/datasets

# 暴露 MLflow 端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# 设置默认命令
CMD ["python", "-m", "edge_train.cli"]
