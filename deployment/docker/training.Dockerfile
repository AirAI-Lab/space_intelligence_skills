# ============================================
# 训练服务 Dockerfile (PyTorch + YOLO + CUDA)
# 基础镜像: nvidia/cuda:12.8.0-devel-ubuntu22.04
# 支持 RTX 5060 Ti (Blackwell sm_120)
# 统一版本: PyTorch 2.10.0 + CUDA 12.8
# ============================================

# 阶段1: 基础环境
FROM nvidia/cuda:12.8.0-devel-ubuntu22.04 AS base

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=600 \
    PIP_RETRIES=10 \
    TORCH_CUDA_ARCH_LIST="12.0" \
    CUDA_VISIBLE_DEVICES=0 \
    CUDA_HOME=/usr/local/cuda \
    FORCE_CUDA="1" \
    CUDA_VERSION="12.8" \
    TZ=Asia/Shanghai \
    DEBIAN_FRONTEND=noninteractive

# 安装系统依赖（包括字体和时区支持）
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3-venv \
    git \
    wget \
    curl \
    vim \
    libgl1-mesa-glx \
    libglib2.0-0 \
    fonts-liberation \
    fonts-dejavu-core \
    fonts-noto-cjk \
    fontconfig \
    && ln -snf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo 'Asia/Shanghai' > /etc/timezone \
    && apt-get install -y tzdata \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 升级 pip
RUN pip install --upgrade pip setuptools wheel

# 阶段2: Python 依赖
FROM base AS dependencies

# 创建本地缓存目录
RUN mkdir -p /tmp/pip_cache

# 复制本地缓存（如果存在）- 复制整个目录，可以为空
COPY pip_cache /tmp/pip_cache

# 安装 PyTorch 2.10 with CUDA 12.8 支持 RTX 50 系列 (sm_120)
# 版本对应关系: torch 2.10.0 + torchvision 0.25.0 + torchaudio 2.10.0
# 注意: cu128 版本的 PyTorch 可以在 CUDA 12.x 运行时上运行（向后兼容）
RUN pip install torch==2.10.0+cu128 torchvision==0.25.0+cu128 torchaudio==2.10.0+cu128 \
    --index-url https://download.pytorch.org/whl/cu128 \
    --find-links /tmp/pip_cache \
    --retries 10 \
    --timeout 600

# 复制 requirements.txt（相对于 build context）
COPY requirements.txt /tmp/

# 安装项目依赖
RUN pip install -r /tmp/requirements.txt

# 阶段3: 应用程序
FROM dependencies AS app

WORKDIR /app

# 复制训练框架代码（build context 是 training 目录）
COPY . /app/

# 创建目录（包括 Ultralytics 字体缓存目录）
RUN mkdir -p /app/runs /app/models /app/datasets /root/.config/Ultralytics/

# 使用本地系统字体替代 Arial.ttf（避免网络下载）
RUN ln -sf /usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf /root/.config/Ultralytics/Arial.ttf || \
    ln -sf /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf /root/.config/Ultralytics/Arial.ttf || \
    true

# 暴露训练服务端口
EXPOSE 5002

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5002/health || exit 1

# 设置默认命令
CMD ["python", "app.py"]
