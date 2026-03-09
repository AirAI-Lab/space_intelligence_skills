# 空中空间智能体 - 文档中心

> **项目**: SkyEdge AI System (空中空间智能体)
> **版本**: V2.0 (重组版)
> **日期**: 2026-03-06

---

## 项目概述

**SkyEdge AI** 是一个 AI 智能体驱动的空中空间智能系统，不是另一个无人机平台，而是：
- **空间认知** 而非仅仅是视觉
- **自主决策** 而非远程控制
- **持续学习** 而非静态算法
- **开放生态** 而非封闭系统

## 文档结构

```
docs/v2_reorganized/
├── README.md                    # 本文档
├── 01_architecture/             # 系统架构
│   ├── OVERVIEW.md             # 系统总览
│   ├── MULTI_AGENT_DESIGN.md   # 多智能体设计
│   └── TECHNICAL_MOAT.md       # 技术护城河
├── 02_software/                 # 软件开发
│   ├── EDGE_INFER_FRAMEWORK.md # 边缘推理框架
│   ├── CLOUD_PLATFORM.md       # 云边协同平台
│   └── PLUGIN_DEVELOPMENT.md   # 插件开发指南
├── 03_algorithm/                # 算法开发
│   ├── RCMT_FRAMEWORK.md       # RCMT变化检测
│   ├── MODEL_DEVELOPMENT.md    # 模型开发流程
│   └── TRAINING_GUIDE.md       # 训练指南
├── 04_product/                  # 产品规划
│   ├── PRODUCT_ROADMAP.md      # 产品路线图
│   └── REQUIREMENTS.md         # 需求文档
└── 05_business/                 # 商业文档
    ├── BUSINESS_PLAN.md        # 商业计划
    ├── INVESTOR_GUIDE.md       # 投资人指南
    └── IMPLEMENTATION_MASTER_PLAN.md # 落地实施总纲（完整版）
```

## 代码仓库

| 仓库 | 路径 | 说明 |
|------|------|------|
| **云边协同平台** | `D:\github\edge_infer_cloud` | 后端、前端、训练、数据库 |
| **边缘AI推理框架** | `D:\github\edge_infer` | C++推理引擎、插件系统 |
| **算法模型** | `D:\github\edge_infer_cloud\models` | RCMT等算法开发 |
| **边缘模型** | `D:\github\edge_infer\models` | 推理模型（云端转换后） |
| **推理插件** | `D:\github\edge_infer\src\plugins` | 21个AI推理插件 |

## 团队协作

### 智能体负责人体系

通过 `@delegate` 命令调用不同的子代理：

| 代理 | 职责 | 代码范围 |
|------|------|----------|
| **软件开发代理** | 边缘推理框架、云边协同平台 | `edge_infer/src/*`, `edge_infer_cloud/backend/*`, `frontend/*` |
| **算法开发代理** | RCMT、模型训练、算法优化 | `edge_infer/models/rcmt/*`, `edge_infer_cloud/models/*`, `rcmt_v3/*` |
| **产品开发代理** | 产品规划、需求管理、用户体验 | 文档、原型、路线图 |

### 使用方式

```
@delegate 软件开发代理: 请帮我检查edge_infer框架的插件加载逻辑
@delegate 算法开发代理: 优化RCMT模型的训练参数
@delegate 产品开发代理: 更新Q2产品路线图
```

## 快速开始

1. **新人入职**: 阅读 [01_architecture/OVERVIEW.md](./01_architecture/OVERVIEW.md)
2. **业务实施**: 阅读 [05_business/IMPLEMENTATION_MASTER_PLAN.md](./05_business/IMPLEMENTATION_MASTER_PLAN.md) ⭐ **重要**
3. **软件开发**: 阅读 [02_software/EDGE_INFER_FRAMEWORK.md](./02_software/EDGE_INFER_FRAMEWORK.md)
4. **算法开发**: 阅读 [03_algorithm/RCMT_FRAMEWORK.md](./03_algorithm/RCMT_FRAMEWORK.md)
5. **产品规划**: 阅读 [04_product/PRODUCT_ROADMAP.md](./04_product/PRODUCT_ROADMAP.md)

---

**维护者**: SkyEdge AI Team
**最后更新**: 2026-03-06
