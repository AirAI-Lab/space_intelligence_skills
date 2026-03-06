# 妙算3快速验证指南

> **目标**: 在大疆妙算3上验证edge_infer核心功能，为后续一体机开发打基础  
> **时间**: 3-4周  
> **难度**: 中等  
> **文档状态**: V1.0

---

## 📋 目录

1. [准备工作](#1-准备工作)
2. [妙算3环境配置](#2-妙算3环境配置)
3. [edge_infer编译部署](#3-edge_infer编译部署)
4. [云边协同配置](#4-云边协同配置)
5. [模型部署与推理测试](#5-模型部署与推理测试)
6. [性能测试与优化](#6-性能测试与优化)
7. [演示材料准备](#7-演示材料准备)

---

## 1. 准备工作

### 1.1 硬件清单

| 设备 | 数量 | 说明 |
|------|------|------|
| 大疆妙算3 Manifold 3 | 1 | 核心计算平台 |
| 妙算3配套相机 | 1 | 可选，用于视频流测试 |
| 无人机（如M300 RTK） | 1 | 可选，用于实际飞行测试 |
| 网线（Cat5e或以上） | 1 | 连接妙算3与PC |
| 电源适配器 | 1 | 妙算3电源 |
| 显示器+HDMI线 | 1 | 调试用 |
| 键鼠 | 1 | 调试用 |

### 1.2 软件清单

| 软件 | 版本 | 用途 |
|------|------|------|
| Ubuntu 20.04 LTS | 妙算3预装 | 操作系统 |
| JetPack 4.6.x | 妙算3预装 | CUDA/TensorRT等 |
| Python 3.8+ | 预装 | 运行环境 |
| Git | 最新版 | 代码管理 |
| CMake | 3.18+ | 编译工具 |
| OpenCV | 4.5+ | 图像处理 |

### 1.3 网络环境

```
┌─────────────┐         网络           ┌──────────────┐
│   开发PC    │ ◄──────────────► │    妙算3      │
│ (Windows)   │  192.168.1.100    │ (192.168.1.101) │
│             │                   │              │
│ - edge_cloud│                   │ - edge_infer │
│ - 训练服务  │                   │ - 推理服务  │
│ - MQTT Broker│                  │ - OTA Client │
└─────────────┘                   └──────────────┘
```

---

## 2. 妙算3环境配置

### 2.1 系统信息查看

```bash
# 连接到妙算3（SSH或直接登录）
ssh nvidia@192.168.1.101

# 查看系统信息
cat /etc/os-release
# 应该显示 Ubuntu 20.04

# 查看JetPack版本
dpkg -l | grep jetpack
# 或
cat /etc/nv_tegra_release

# 查看CUDA版本
nvcc --version
# JetPack 4.6.x 对应 CUDA 11.4

# 查看TensorRT版本
dpkg -l | grep tensorrt

# 查看Jetson型号
cat /sys/firmware/devicetree/base/model
# 应该显示 NVIDIA Jetson AGX Orin (妙算3）
```

### 2.2 安装依赖

```bash
# 更新系统
sudo apt-get update && sudo apt-get upgrade -y

# 安装基础工具
sudo apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    vim \
    htop

# 安装Python依赖
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    python3-opencv

# 安装MQTT库（用于云边协同）
sudo apt-get install -y \
    libmosquitto-dev \
    mosquitto-clients

# 安装JSON库
sudo apt-get install -y \
    libjsoncpp-dev

# 安装OpenCV完整版（如果需要）
sudo apt-get install -y \
    libopencv-dev \
    python3-opencv-apps

# 验证安装
python3 --version
cmake --version
git --version
```

### 2.3 准备工作目录

```bash
# 创建工作目录
mkdir -p ~/workspace
cd ~/workspace

# 克隆edge_infer仓库
git clone https://github.com/yourusername/edge_infer.git
cd edge_infer

# 查看目录结构
ls -la
```

---

## 3. edge_infer编译部署

### 3.1 生成TensorRT引擎文件

**重要**: 在妙算3上生成.engine文件，确保与硬件和TensorRT版本匹配

```bash
# 进入edge_infer目录
cd ~/workspace/edge_infer

# 下载YOLOv8模型（如果没有）
python3 tools/download_models.py

# 或使用ultralytics导出ONNX
pip3 install ultralytics
yolo export model=yolov8n.pt format=onnx

# 使用TensorRT的trtexec工具生成.engine
trtexec \
    --onnx=models/object_detection/yolov8n.onnx \
    --saveEngine=models/object_detection/yolov8n.engine \
    --fp16 \
    --batchSize=1 \
    --workspace=2048

# 验证引擎文件
trtexec \
    --loadEngine=models/object_detection/yolov8n.engine \
    --duration=30

# 查看引擎信息
ls -lh models/object_detection/yolov8n.engine
```

**说明**：
- `--fp16`: 使用FP16精度，速度更快
- `--batchSize=1`: 边缘推理通常用batch=1
- `--workspace=2048`: 2GB工作空间

### 3.2 编译edge_infer

```bash
# 创建编译目录
cd ~/workspace/edge_infer
rm -rf build
mkdir build
cd build

# 配置CMake（启用MQTT和TensorRT）
cmake .. \
    -DUSE_TENSORRT=ON \
    -DUSE_MQTT=ON \
    -DCMAKE_BUILD_TYPE=Release

# 编译
make -j$(nproc)

# 查看生成的可执行文件
ls -lh edge_framework
```

### 3.3 配置运行环境

#### 3.3.1 复制模型文件

```bash
# 确保模型文件在正确位置
cd ~/workspace/edge_infer

# 检查模型目录
ls -lh models/object_detection/

# 如果没有.engine文件，重新生成
trtexec \
    --onnx=models/object_detection/yolov8n.onnx \
    --saveEngine=models/object_detection/yolov8n.engine \
    --fp16
```

#### 3.3.2 配置文件

```bash
# 编辑config/main_config.json
vim config/main_config.json
```

```json
{
  "model": {
    "type": "yolov8",
    "engine_path": "models/object_detection/yolov8n.engine",
    "input_width": 640,
    "input_height": 640,
    "num_classes": 80,
    "conf_threshold": 0.5,
    "nms_threshold": 0.45
  },
  "video": {
    "input_type": "camera",
    "camera_id": 0,
    "rtsp_url": ""
  },
  "output": {
    "show_result": true,
    "save_video": false,
    "rtmp_url": ""
  },
  "inference": {
    "batch_size": 1,
    "gpu_device_id": 0
  }
}
```

#### 3.3.3 配置云边协同

```bash
# 编辑config/cloud_config.json
vim config/cloud_config.json
```

```json
{
  "cloud": {
    "enabled": true,
    "api_base_url": "http://192.168.1.100:8081/api/v1",
    "device_id": "manifold3_001",
    "device_name": "Manifold 3 Test Device",
    "device_type": "MANIFOLD_3",
    "ip_address": "192.168.1.101",
    "port": 1883
  },
  "mqtt": {
    "enabled": true,
    "broker_host": "192.168.1.100",
    "broker_port": 1883,
    "username": "admin",
    "password": "admin123456",
    "client_id": "manifold3_001"
  },
  "ota": {
    "enabled": true,
    "model_dir": "/home/nvidia/workspace/edge_infer/models",
    "auto_reload": true
  }
}
```

---

## 4. 云边协同配置

### 4.1 配置云端平台

#### 4.1.1 启动edge_infer_cloud

```bash
# 在开发PC上（Windows）
cd d:\github\edge_infer_cloud\deployment\docker

# 编辑docker-compose.yml，设置BACKEND_EXTERNAL_URL
# 找到backend服务的environment部分，设置：
# BACKEND_EXTERNAL_URL=http://192.168.1.100:8081

# 启动服务
docker-compose up -d

# 验证服务启动
docker-compose ps

# 查看日志（如有问题）
docker-compose logs backend
docker-compose logs emqx
```

#### 4.1.2 访问管理平台

打开浏览器访问：
- 中文导航: http://localhost:8889
- 前端管理: http://localhost:3000
- API文档: http://localhost:8081/swagger-ui.html
- EMQX Dashboard: http://localhost:18083

#### 4.1.3 注册设备

方式1: 通过Web界面
1. 访问 http://localhost:3000
2. 进入"设备管理"
3. 点击"新增设备"
4. 填写设备信息：
   - 设备ID: manifold3_001
   - 设备名称: Manifold 3 Test Device
   - 设备类型: MANIFOLD_3
   - IP地址: 192.168.1.101

方式2: 通过API
```bash
curl -X POST http://localhost:8081/api/v1/devices \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "manifold3_001",
    "device_name": "Manifold 3 Test Device",
    "device_type": "MANIFOLD_3",
    "ip_address": "192.168.1.101",
    "port": 1883
  }'
```

### 4.2 验证MQTT连接

#### 4.2.1 在妙算3上测试MQTT

```bash
# 安装MQTT客户端
sudo apt-get install -y mosquitto-clients

# 测试订阅
mosquitto_sub -h 192.168.1.100 -p 1883 -t "device/manifold3_001/#" -v

# 另开一个终端，测试发布
mosquitto_pub -h 192.168.1.100 -p 1883 -t "device/manifold3_001/test" -m "Hello from Manifold 3"
```

#### 4.2.2 在EMQX Dashboard查看

1. 访问 http://localhost:18083
2. 登录（admin/admin123456）
3. 查看"连接"页面，应该看到manifold3_001在线

---

## 5. 模型部署与推理测试

### 5.1 准备模型

#### 5.1.1 在云端平台导入模型

方式1: 通过Web界面
1. 访问 http://localhost:3000
2. 进入"模型管理"
3. 点击"导入模型"
4. 上传ONNX模型文件

方式2: 通过API
```bash
# 假设已有ONNX模型
curl -X POST http://localhost:8081/api/v1/models/import \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "yolov8n_manifold3",
    "model_type": "detection",
    "model_format": "onnx",
    "file_path": "/path/to/yolov8n.onnx"
  }'
```

#### 5.1.2 转换模型为Engine

在云端平台转换（推荐在PC上转换，然后上传）：

```bash
# 使用PyTorch导出ONNX
pip install ultralytics
yolo export model=yolov8n.pt format=onnx

# 或使用TensorRT转换（如果PC上有TensorRT）
trtexec \
    --onnx=yolov8n.onnx \
    --saveEngine=yolov8n.engine \
    --fp16
```

通过Web界面上传engine文件到模型管理。

### 5.2 创建部署任务

#### 5.2.1 通过Web界面

1. 进入"模型管理"
2. 选择模型，点击"部署"
3. 选择目标设备：manifold3_001
4. 确认部署

#### 5.2.2 通过API

```bash
curl -X POST http://localhost:8081/api/v1/ota/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "taskName": "妙算3模型部署",
    "upgradeType": "MODEL",
    "modelId": "M_xxx",
    "deviceIds": ["manifold3_001"]
  }'
```

### 5.3 监控部署进度

#### 5.3.1 通过Web界面

进入"部署记录"查看实时进度

#### 5.3.2 通过API

```bash
# 查询任务状态
curl http://localhost:8081/api/v1/ota/tasks/{task_id}

# 查询设备状态
curl http://localhost:8081/api/v1/ota/tasks/{task_id}/devices
```

部署进度阶段：
- 0-25%: 下载模型
- 25-30%: 验证文件
- 30-90%: TensorRT转换
- 90-100%: 应用更新

### 5.4 运行推理服务

#### 5.4.1 启动edge_infer

```bash
# 在妙算3上
cd ~/workspace/edge_infer/build

# 运行推理服务
./edge_framework

# 查看日志
tail -f ../logs/edge_framework.log
```

#### 5.4.2 验证推理结果

使用摄像头输入：
```bash
# 确保config/main_config.json中配置了摄像头
# "video": {"input_type": "camera", "camera_id": 0}

# 运行时应该看到实时检测画面
```

使用视频文件输入：
```bash
# 修改配置
"video": {
    "input_type": "video_file",
    "video_path": "/path/to/test.mp4"
}

# 运行
./edge_framework
```

使用RTSP流：
```bash
# 修改配置
"video": {
    "input_type": "rtsp",
    "rtsp_url": "rtsp://192.168.1.xxx:8554/stream"
}

# 运行
./edge_framework
```

---

## 6. 性能测试与优化

### 6.1 基准测试

#### 6.1.1 推理延迟测试

```bash
# 使用trtexec测试引擎性能
trtexec \
    --loadEngine=models/object_detection/yolov8n.engine \
    --duration=60 \
    --warmUp=10

# 记录关键指标：
# - Latency (ms): 端到端延迟
# - Throughput (FPS): 帧率
# - GPU Utilization (%): GPU利用率
```

**预期性能（YOLOv8n, FP16, 640x640）**：
| 指标 | 目标值 | 测试值 | 备注 |
|------|--------|--------|------|
| 推理延迟 | < 50ms | - | 端到端 |
| 帧率 | > 20 FPS | - | 实时要求 |
| GPU利用率 | > 70% | - | 充分利用 |

#### 6.1.2 云边协同延迟测试

```bash
# 在妙算3上运行推理服务
./edge_framework &

# 在云端触发模型更新
curl -X POST http://localhost:8081/api/v1/ota/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "taskName": "延迟测试",
    "upgradeType": "MODEL",
    "modelId": "M_xxx",
    "deviceIds": ["manifold3_001"]
  }'

# 记录时间戳
# - T0: 触发时间
# - T1: 开始下载
# - T2: 下载完成
# - T3: TensorRT转换完成
# - T4: 应用完成

# 计算各阶段耗时
下载耗时 = T2 - T1
转换耗时 = T3 - T2
应用耗时 = T4 - T3
总耗时 = T4 - T0
```

**预期性能**：
| 阶段 | 目标值 | 测试值 | 备注 |
|------|--------|--------|------|
| 下载 | < 30s | - | 100MB模型 |
| 转换 | < 60s | - | TensorRT |
| 应用 | < 5s | - | 热加载 |
| 总计 | < 100s | - | - |

### 6.2 性能优化

#### 6.2.1 TensorRT优化

```bash
# 重新生成引擎，使用更多优化选项
trtexec \
    --onnx=models/object_detection/yolov8n.onnx \
    --saveEngine=models/object_detection/yolov8n.engine \
    --fp16 \
    --sparsity=enable \
    --precisionConstraints=prefer \
    --calib=calibration.cache

# 使用INT8量化（需要校准数据）
trtexec \
    --onnx=models/object_detection/yolov8n.onnx \
    --saveEngine=models/object_detection/yolov8n_int8.engine \
    --int8 \
    --calib=calibration.cache
```

#### 6.2.2 模型优化

```bash
# 使用更小的模型（YOLOv8n → YOLOv8n-ultralytics）
yolo export model=yolov8n-ultralytics.pt format=onnx

# 调整输入尺寸（640x640 → 512x512）
yolo export model=yolov8n.pt format=onnx imgsz=512

# 使用动态batch（batch=1 → batch=2）
yolo export model=yolov8n.pt format=onnx batch=2
```

#### 6.2.3 系统优化

```bash
# 调整GPU频率
sudo jetson_clocks --show
sudo jetson_clocks --mode MAX_PERFORMANCE

# 查看GPU状态
tegrastats

# 优化内存分配
echo 1 | sudo tee /proc/sys/vm/overcommit_memory
```

---

## 7. 演示材料准备

### 7.1 视频录制

#### 7.1.1 录制推理演示

```bash
# 使用OBS录制推理过程
# 或使用FFmpeg录制屏幕

# 安装FFmpeg
sudo apt-get install -y ffmpeg

# 录制推理过程（60秒）
ffmpeg -f x11grab -s 1920x1080 -r 30 -t 60 \
    -i :0.0 \
    -c:v libx264 -preset fast -crf 22 \
    demo_inference.mp4
```

#### 7.1.2 录制云边协同演示

1. 打开两个窗口：
   - 窗口1: 云端管理平台（左侧）
   - 窗口2: 妙算3 SSH终端（右侧）

2. 录制完整流程：
   - 创建部署任务
   - 监控部署进度
   - 妙算3接收OTA
   - 模型热加载
   - 推理结果展示

### 7.2 性能对比

#### 7.2.1 对比表格

| 指标 | 本地推理 | 云边协同 | 说明 |
|------|----------|----------|------|
| 推理延迟 | 30ms | 32ms | 云边无影响 |
| 更新速度 | 手动（10min） | 自动（2min） | OTA优势 |
| 模型管理 | 手动 | 自动 | 云端统一 |
| 设备监控 | 本地 | 云端 | 远程管理 |

#### 7.2.2 性能曲线

```python
# 生成性能对比图
import matplotlib.pyplot as plt

# 数据
models = ['YOLOv8n', 'YOLOv8s', 'YOLOv8m']
local_latency = [30, 45, 60]
cloud_latency = [32, 47, 62]

# 绘制曲线
plt.figure(figsize=(10, 6))
plt.plot(models, local_latency, 'b-o', label='本地推理')
plt.plot(models, cloud_latency, 'r-s', label='云边协同')
plt.xlabel('模型')
plt.ylabel('延迟 (ms)')
plt.title('推理延迟对比')
plt.legend()
plt.grid(True)
plt.savefig('performance_comparison.png')
```

### 7.3 文档准备

#### 7.3.1 技术文档

1. **架构文档**：
   - 整体架构图
   - 模块说明
   - 数据流向

2. **API文档**：
   - REST API列表
   - MQTT主题设计
   - 请求/响应示例

3. **部署文档**：
   - 环境要求
   - 安装步骤
   - 配置说明

4. **用户手册**：
   - 快速开始
   - 功能说明
   - 常见问题

#### 7.3.2 演示PPT

**核心内容**：
1. 项目背景与痛点
2. 解决方案与架构
3. 核心技术（RCMT、多智能体）
4. 产品演示视频
5. 性能对比数据
6. 市场前景与商业模式

### 7.4 数据收集

#### 7.4.1 性能数据

```json
{
  "performance": {
    "inference": {
      "model": "YOLOv8n",
      "resolution": "640x640",
      "precision": "FP16",
      "latency_ms": 32.5,
      "fps": 30.8,
      "gpu_utilization": 78
    },
    "ota": {
      "model_size_mb": 95.2,
      "download_time_s": 28.3,
      "convert_time_s": 54.7,
      "apply_time_s": 3.2,
      "total_time_s": 86.2
    },
    "collaboration": {
      "heartbeat_interval_s": 10,
      "latency_ms": 15,
      "reliability": "99.9%"
    }
  }
}
```

#### 7.4.2 场景数据

记录实际测试场景：
- 场景名称
- 环境条件（光照、温度、湿度）
- 测试结果
- 问题和解决方案

---

## 8. 验收标准

### 8.1 功能验收

- [ ] 妙算3成功运行edge_infer
- [ ] 云端成功注册设备
- [ ] MQTT连接正常
- [ ] OTA升级成功
- [ ] 模型热加载成功
- [ ] 实时推理正常

### 8.2 性能验收

- [ ] 推理延迟 < 100ms
- [ ] 帧率 > 20 FPS
- [ ] OTA总耗时 < 100s
- [ ] 心跳正常上报
- [ ] 设备在线率 > 99%

### 8.3 交付物

- [ ] 完整的演示视频
- [ ] 性能测试报告
- [ ] 部署文档
- [ ] API文档
- [ ] 技术架构PPT

---

## 9. 常见问题

### 9.1 编译问题

**问题**: CMake找不到TensorRT

**解决**:
```bash
# 设置TensorRT路径
export TensorRT_DIR=/usr/src/tensorrt

# 或在CMakeLists.txt中指定
set(TensorRT_DIR /usr/src/tensorrt)
```

**问题**: 缺少OpenCV库

**解决**:
```bash
# 安装OpenCV
sudo apt-get install -y libopencv-dev python3-opencv

# 设置OpenCV路径
export OpenCV_DIR=/usr
```

### 9.2 运行问题

**问题**: 无法加载.engine文件

**解决**:
```bash
# 检查TensorRT版本
dpkg -l | grep tensorrt

# 重新生成engine（必须匹配版本）
trtexec \
    --onnx=yolov8n.onnx \
    --saveEngine=yolov8n.engine \
    --fp16
```

**问题**: MQTT连接失败

**解决**:
```bash
# 检查网络连通性
ping 192.168.1.100

# 检查MQTT端口
telnet 192.168.1.100 1883

# 查看EMQX日志
docker logs edge_cloud_emqx
```

### 9.3 性能问题

**问题**: 推理速度慢

**解决**:
```bash
# 检查GPU频率
sudo jetson_clocks --show

# 设置为性能模式
sudo jetson_clocks --mode MAX_PERFORMANCE

# 查看GPU状态
tegrastats
```

---

**文档状态**: V1.0  
**最后更新**: 2026-02-15  
**维护者**: Development Team
