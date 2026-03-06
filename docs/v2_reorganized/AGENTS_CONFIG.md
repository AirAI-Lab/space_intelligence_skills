# 空中智能体 - 子代理配置

> **更新日期**: 2026-03-06
> **配置文件**: `~/.openclaw/openclaw.json`

---

## 1. 子代理列表

| 代理ID | 标签 | 角色 | 调用方式 |
|--------|------|------|----------|
| **main** | 主代理 | 总控、协调 | 默认 |
| **software-dev** | 软件开发代理 | 软件工程师 | `@delegate [软件工程师]` |
| **algorithm-dev** | 算法开发代理 | 算法工程师 | `@delegate [算法工程师]` |
| **product-dev** | 产品开发代理 | 产品工程师 | `@delegate [产品工程师]` |
| **hardware-dev** | 硬件开发代理 | 硬件工程师 | `@delegate [硬件工程师]` |
| **marketing-ops** | 市场运营代理 | 市场运营 | `@delegate [市场运营]` |
| **leadership** | 负责人代理 | CTO/CEO | `@delegate [负责人]` |

---

## 2. 角色职责

### 2.1 技术团队

#### 软件开发代理 (software-dev)
- **职责**: 边缘推理框架、云边协同平台开发
- **代码范围**:
  ```
  edge_infer/src/core/           # 核心框架
  edge_infer/src/plugins/        # 推理插件
  edge_infer_cloud/backend/      # 后端服务
  edge_infer_cloud/frontend/     # 前端界面
  ```
- **适用任务**: C++/Python开发、Java后端、Vue3前端、MQTT通讯

#### 算法开发代理 (algorithm-dev)
- **职责**: RCMT变化检测模型训练、优化、部署
- **代码范围**:
  ```
  edge_infer/models/rcmt/        # RCMT模型
  edge_infer/rcmt_v3/            # RCMT V3
  edge_infer_cloud/models/       # 云端模型
  edge_infer_cloud/training/     # 训练服务
  ```
- **适用任务**: PyTorch、Transformer、模型优化、TensorRT导出

#### 硬件开发代理 (hardware-dev)
- **职责**: 硬件设计、PCB开发、嵌入式系统、模块集成
- **代码范围**:
  ```
  hardware/                      # 硬件设计
  edge_infer/src/external/       # 外部平台对接
  ```
- **适用任务**: PCB设计、Jetson适配、5G/RTK/Mesh集成、飞控对接

---

### 2.2 产品团队

#### 产品开发代理 (product-dev)
- **职责**: 产品规划、需求分析、文档维护、用户体验
- **代码范围**:
  ```
  edge_infer_cloud/docs/         # 文档
  ```
- **适用任务**: 产品路线图、需求文档、用户手册、竞品分析

#### 市场运营代理 (marketing-ops)
- **职责**: 市场推广、品牌建设、客户关系、商务合作
- **代码范围**:
  ```
  edge_infer_cloud/docs/v2_reorganized/05_business/  # 商业文档
  ```
- **适用任务**: 商业计划、营销策略、客户沟通、社区运营

---

### 2.3 管理团队

#### 负责人代理 (leadership)
- **职责**: 战略决策、资源分配、团队管理、投资对接
- **代码范围**:
  ```
  edge_infer_cloud/docs/v2_reorganized/04_product/   # 产品规划
  edge_infer_cloud/docs/v2_reorganized/05_business/  # 商业文档
  edge_infer_cloud/MEMORY.md                         # 项目记忆
  ```
- **适用任务**: 战略规划、里程碑审批、资源协调、投融资准备

---

## 3. 使用方式

### 3.1 指定角色调用

```
@delegate [软件工程师] 检查插件加载逻辑
@delegate [算法工程师] 检查RCMT训练进度
@delegate [产品工程师] 更新产品路线图
@delegate [硬件工程师] 评估Jetson Orin NX适配方案
@delegate [市场运营] 准备产品演示材料
@delegate [负责人] 审批Phase 2里程碑
```

### 3.2 自动选择

不带角色时，主代理会根据任务内容自动选择：

```
@delegate 优化YOLOv8推理性能  → software-dev
@delegate 检查模型F1分数     → algorithm-dev
@delegate 更新用户手册       → product-dev
@delegate PCB设计评审        → hardware-dev
@delegate 准备商业计划书     → marketing-ops
@delegate 里程碑审批         → leadership
```

---

## 4. 组织架构

```
                    ┌─────────────┐
                    │   负责人     │
                    │ (leadership) │
                    │  CTO/CEO    │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐      ┌─────▼─────┐     ┌─────▼─────┐
    │ 技术团队 │      │ 产品团队  │     │ 市场团队  │
    └────┬────┘      └─────┬─────┘     └─────┬─────┘
         │                 │                 │
    ┌────┼────┐       ┌────┴────┐            │
    │    │    │       │         │            │
 ┌──▼┐ ┌──▼┐ ┌──▼┐  ┌──▼┐    ┌──▼┐        ┌──▼┐
 │软 │ │算 │ │硬 │  │产 │    │市 │        │   │
 │件 │ │法 │ │件 │  │品 │    │场 │        │   │
 └───┘ └───┘ └───┘  └───┘    └───┘        └───┘
```

---

## 5. 典型工作流

### 5.1 产品开发流程

```
[负责人] 制定战略目标
    ↓
[产品工程师] 需求分析 → 产品规划
    ↓
[软件/算法/硬件工程师] 技术实现
    ↓
[市场运营] 产品推广 → 客户反馈
    ↓
[负责人] 里程碑审批 → 下一阶段
```

### 5.2 问题解决流程

```
发现问题 → [主代理] 分析 → 委托对应子代理
                              ↓
                    ┌─────────┼─────────┐
                    ↓         ↓         ↓
              [软件]      [算法]     [硬件]
                    ↓         ↓         ↓
                    └─────────┼─────────┘
                              ↓
                        解决方案 → [主代理] 汇报
```

---

## 6. 配置详情

### 6.1 子代理配置

```yaml
subagents:
  model: zai/glm-4.7
  maxConcurrent: 6        # 最多同时6个子代理
  maxSpawnDepth: 2        # 最大嵌套深度2层
  maxChildrenPerAgent: 8  # 每个代理最多8个子代理
  runTimeoutSeconds: 3600 # 任务超时1小时
  archiveAfterMinutes: 60 # 60分钟后归档
```

### 6.2 模型配置

| 代理类型 | 推荐模型 | 说明 |
|----------|----------|------|
| 主代理 | zai/glm-5 | 高质量决策 |
| 技术子代理 | zai/glm-4.7 | 代码能力强 |
| 管理/产品子代理 | zai/glm-4.7 | 理解能力强 |

---

## 7. 注意事项

1. **Token隔离**: 子代理有独立上下文，不消耗主代理token
2. **并发限制**: 最多同时运行6个子代理
3. **超时设置**: 任务超时时间1小时
4. **结果合并**: 子代理完成后返回结果摘要

---

**配置状态**: ✅ 已配置
**最后更新**: 2026-03-06
