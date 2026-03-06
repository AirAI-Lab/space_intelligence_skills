# 空中空间智能体 - 长期记忆

> **项目**: SkyEdge AI System
> **版本**: V2.0
> **最后更新**: 2026-03-06 09:15

---

## 1. 项目概述

### 1.1 核心定位

**"空中空间智能体 - 不是另一个无人机平台"**

我们构建的是 **AI智能体操作系统**，为无人机等空中设备提供：

| 能力 | 描述 |
|------|------|
| **空间智能** | 理解三维空间环境，构建空间记忆 |
| **自主决策** | 基于空间记忆和世界模型进行决策 |
| **持续进化** | 从空间交互中持续学习和进化 |
| **开放生态** | 基于多智能体架构的开放生态 |

### 1.2 团队规模

- **当前**: <10人
- **目标**: 按需扩展

---

## 2. 代码仓库

### 2.1 仓库概览

| 仓库 | 路径 | 说明 |
|------|------|------|
| **云边协同平台** | `D:\github\edge_infer_cloud` | 后端、前端、训练服务 |
| **边缘推理框架** | `D:\github\edge_infer` | C++推理引擎、16个AI插件 |

### 2.2 云边协同平台结构

```
edge_infer_cloud/
├── backend/          # Java/Spring Boot 后端
│   └── src/main/     # 源码 (API、Service、Repository)
├── frontend/         # Vue3 + Element Plus 前端
│   └── src/          # 组件、视图、API
├── models/           # 算法模型开发
│   ├── rcmt/         # RCMT变化检测
│   └── rcmt_v3/      # RCMT V3版本
├── training/         # 训练服务
├── edge-agent/       # 边缘代理
├── data/             # 数据集
└── docs/             # 文档
    └── v2_reorganized/  # V2重组版文档 ← 新结构
```

### 2.3 边缘推理框架结构

```
edge_infer/
├── src/
│   ├── core/         # 核心框架 (插件接口、推理引擎)
│   ├── plugins/      # 16个AI推理插件
│   │   ├── object_detection/   # 目标检测 (YOLOv8)
│   │   ├── change_detection/   # 变化检测 (RCMT)
│   │   ├── semantic_seg/       # 语义分割
│   │   ├── mot_tracking/       # 目标跟踪
│   │   └── ...                 # 其他插件
│   └── plugin_manager/         # 插件生命周期管理
├── models/           # 推理模型 (ONNX/Engine)
│   └── rcmt/         # RCMT模型
├── rcmt_v3/          # RCMT V3 训练代码
│   ├── models/       # 模型定义
│   ├── datasets/     # 数据集
│   ├── logs_swin_final_v2/  # 当前训练日志
│   └── checkpoints_*/       # 检查点
└── datasets/         # 训练数据 (LEVIR-MCD, SYSU-CD)
```

---

## 3. 核心技术

### 3.1 RCMT变化检测 (核心算法)

**算法概述**: RCMT (Recurrent Cross-Memory Transformer for Spatio-Temporal Change Detection)

**核心创新**:
- 时序记忆机制 (Temporal Memory)
- 空间记忆机制 (Spatial Memory)
- 交叉记忆机制 (Cross-Memory)
- 循环注意力机制 (Recurrent Attention)

**训练状态 (2026-03-06)**:

| 版本 | 进度 | 最佳F1 | 状态 |
|------|------|--------|------|
| **Swin V2** | Epoch 130/300 | 0.8924 | 🔄 训练中 |
| **Swin V1** | 完成 300/300 | 0.9048 | ✅ 已完成 |

**日志路径**: `D:\github\edge_infer\rcmt_v3\logs_swin_final_v2\train.log`

**检查命令**:
```powershell
Get-Content "D:\github\edge_infer\rcmt_v3\logs_swin_final_v2\train.log" -Tail 50
```

### 3.2 AI推理插件 (16个)

| 类别 | 插件 | 模型 |
|------|------|------|
| **目标检测** | object_detection, person_detection, vehicle_detection, helmet_detect | YOLOv8系列 |
| **变化检测** | change_detection | **RCMT** (核心) |
| **分割** | semantic_seg, instance_seg | SegFormer, YOLOv8-seg |
| **跟踪** | mot_tracking, counting | DeepSORT |
| **姿态** | pose_estimation | YOLOv8-pose |
| **OCR** | text_ocr, lp_recognition | PaddleOCR |
| **异常** | anomaly_detection, thermal_detection | AutoEncoder |

### 3.3 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | Java 17, Spring Boot 3.x |
| **前端** | Vue 3, Element Plus, Vite |
| **边缘推理** | C++17, TensorRT, CUDA |
| **深度学习** | PyTorch 2.x, Transformers |
| **通讯** | MQTT, HTTP/REST |
| **数据库** | PostgreSQL, TimescaleDB, Redis |

---

## 4. 文档体系

### 4.1 新文档结构 (`docs/v2_reorganized/`)

```
v2_reorganized/
├── README.md              # 文档索引
├── MEMORY.md              # 长期记忆 ← 本文档
├── AGENTS_CONFIG.md       # 智能体配置
├── DOCUMENT_MIGRATION.md  # 迁移映射表
├── 01_architecture/       # 系统架构
│   ├── OVERVIEW.md        # 系统总览
│   ├── MULTI_AGENT_DESIGN.md  # 多智能体设计 (迁移中)
│   └── TECHNICAL_MOAT.md  # 技术护城河 (迁移中)
├── 02_software/           # 软件开发
│   ├── EDGE_INFER_FRAMEWORK.md  # 边缘框架
│   ├── CODE_ANALYSIS_EDGE.md    # 代码分析 (生成中)
│   └── CODE_ANALYSIS_CLOUD.md   # 代码分析 (生成中)
├── 03_algorithm/          # 算法开发
│   └── RCMT_FRAMEWORK.md  # RCMT框架
├── 04_product/            # 产品规划 (迁移中)
└── 05_business/           # 商业文档 (迁移中)
```

### 4.2 文档迁移进度

| Phase | 状态 | 内容 |
|-------|------|------|
| Phase 1 | ✅ 完成 | 创建新结构、核心文档 |
| Phase 2 | 🔄 进行中 | 架构、产品、商业文档迁移 |
| Phase 3 | ⏳ 待执行 | 清理冗余、归档旧文档 |

---

## 5. 智能体体系

### 5.1 代理分工

| 代理 | 职责 | 代码范围 |
|------|------|----------|
| **软件开发代理** | 边缘框架、云边平台 | `edge_infer/src/*`, `backend/*`, `frontend/*` |
| **算法开发代理** | RCMT、模型训练 | `models/rcmt/*`, `rcmt_v3/*` |
| **产品开发代理** | 需求、路线图 | 文档、规划 |

### 5.2 调用方式

```
@delegate 软件开发代理: 检查插件加载逻辑
@delegate 算法开发代理: 检查训练状态
@delegate 产品开发代理: 更新产品路线图
```

---

## 6. 开发任务

### 6.1 高优先级

- [ ] **RCMT训练完成** - 目标 F1 > 0.92
- [ ] **模型量化部署** - FP16/INT8 + TensorRT
- [ ] **文档迁移Phase 2** - 进行中

### 6.2 中优先级

- [ ] 论文撰写 (CVPR/ICCV)
- [ ] 前端UI优化
- [ ] 自动化测试覆盖

### 6.3 低优先级

- [ ] 插件市场
- [ ] 可视化调试工具
- [ ] 多语言支持

---

## 7. 更新日志

### 2026-03-06 (下午更新)
- 配置24小时自动化工作方案
  - 创建 `06_automation/24H_AUTOMATION.md`
  - 创建 `06_automation/WEEKEND_GUIDE.md`
  - 配置 HEARTBEAT.md 定期检查任务
  - 创建监控脚本:
    - `scripts/monitor_training.ps1` - 训练监控
    - `scripts/health_check.ps1` - 系统健康检查
    - `scripts/auto_commit.ps1` - 自动代码提交
- 修复设备管理页面在线状态问题
- 分析训练页面与代码关系

### 2026-03-06 (上午)
- 创建新文档体系 (`docs/v2_reorganized/`)
- 设置智能体管理配置
- 整理代码仓库结构映射
- 记录RCMT训练状态 (Swin V2 Epoch 130/300, F1 0.8924)
- 启动3个子代理并行任务：
  - 文档迁移-Phase2
  - 代码分析-edge_infer
  - 代码分析-edge_infer_cloud
- 配置24小时自动化工作方案
- 创建监控脚本 (monitor_training.ps1, health_check.ps1, auto_commit.ps1)
- 配置HEARTBEAT.md定期检查任务

---

## 8. 快速参考

### 训练状态检查
```powershell
Get-Content "D:\github\edge_infer\rcmt_v3\logs_swin_final_v2\train.log" -Tail 100
```

### 项目目录
- 云边协同: `D:\github\edge_infer_cloud`
- 边缘推理: `D:\github\edge_infer`

### 关键文件
- 本记忆: `docs/v2_reorganized/MEMORY.md`
- 文档索引: `docs/v2_reorganized/README.md`
- 代理配置: `docs/v2_reorganized/AGENTS_CONFIG.md`

---

**维护者**: SkyEdge AI Team
**创建时间**: 2026-03-06
**最后更新**: 2026-03-06 09:15
