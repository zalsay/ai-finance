# TimesFM FastAPI 推理服务 Dockerfile
FROM ubuntu:22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0
ENV GPU_ID=0
ENV SERVICE_PORT=8000

# 安装系统依赖和Python 3.11
RUN apt-get update && \
    apt-get install -y \
        software-properties-common \
        git \
        wget \
        curl \
        build-essential \
        gnupg \
        ca-certificates \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
        python3.11 \
        python3.11-dev \
        python3.11-distutils \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3 \
    && ln -sf /usr/bin/python3.11 /usr/bin/python

# 安装pip for Python 3.11
RUN wget https://bootstrap.pypa.io/get-pip.py \
    && python3.11 get-pip.py \
    && rm get-pip.py \
    && ln -sf /usr/local/bin/pip3.11 /usr/bin/pip3 \
    && ln -sf /usr/local/bin/pip3.11 /usr/bin/pip

# 安装CUDA 13.0
RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb \
    && dpkg -i cuda-keyring_1.0-1_all.deb \
    && apt-get update \
    && apt-get -y install cuda-toolkit-13-0 \
    && rm cuda-keyring_1.0-1_all.deb \
    && rm -rf /var/lib/apt/lists/*

# 设置CUDA环境变量
ENV PATH=/usr/local/cuda-13.0/bin:/usr/local/bin:${PATH}
ENV LD_LIBRARY_PATH=/usr/local/cuda-13.0/lib64:/usr/local/lib
ENV CUDA_HOME=/usr/local/cuda-13.0

# 设置工作目录
WORKDIR /app

# 复制requirements文件
COPY requirements.txt .
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple
RUN pip config set install.trusted-host mirrors.aliyun.com
# 安装Python依赖
RUN pip install  --upgrade pip
RUN pip install  -r requirements.txt

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p /app/forecast-results
RUN mkdir -p /app/logs

# 设置权限
RUN chmod +x ./timesfm_inference/fastapi_service.py

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${SERVICE_PORT}/health || exit 1

# 启动命令
CMD ["python", "./timesfm_inference/fastapi_service.py"]