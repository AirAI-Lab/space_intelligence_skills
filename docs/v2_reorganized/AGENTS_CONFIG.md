# 空中智能体 - 子代理配置

> **更新日期**: 2026-03-06
> **配置文件**: `~/.openclaw/openclaw.json`

---

## 1. 子代理列表

| 代理ID | 标签 | 职责 | 调用方式 |
|--------|------|------|----------|
| **main** | 主代理 | 总控、协调 | 默认 |
| **software-dev** | 软件开发代理 | 边缘框架、云边平台 | `@delegate [软件工程师]` |
| **algorithm-dev** | 算法开发代理 | RCMT训练、模型优化 | `@delegate [算法工程师]` |
| **product-dev** | 产品开发代理 | 产品规划、文档维护 | `@delegate [产品工程师]` |

---

## 2. 使用方式

### 2.1 主代理调用子代理

在主窗口中使用 `@delegate` 命令：

```
@delegate [软件工程师] 检查插件加载逻辑
@delegate [算法工程师] 检查RCMT训练进度
@delegate [产品工程师] 更新产品路线图
```

### 2.2 自动选择

不带角色时，主代理会根据任务内容自动选择：

```
@delegate 优化YOLOv8推理性能  → 自动选择 software-dev
@delegate 检查模型F1分数     → 自动选择 algorithm-dev
@delegate 更新用户手册       → 自动选择 product-dev
```

---

## 3. 子代理职责范围

### 3.1 软件开发代理 (software-dev)

**代码范围**:
```
edge_infer/src/core/           # 核心框架
edge_infer/src/plugins/        # 推理插件
edge_infer/src/plugin_manager/ # 插件管理
edge_infer_cloud/backend/      # 后端服务
edge_infer_cloud/frontend/     # 前端界面
edge_infer_cloud/edge-agent/   # 边缘代理
```

**适用任务**:
- C++/Python 开发
- Java/Spring Boot 后端
- Vue3 前端
- MQTT 通讯
- TensorRT 推理优化

### 3.2 算法开发代理 (algorithm-dev)

**代码范围**:
```
edge_infer/models/rcmt/        # RCMT模型
edge_infer/rcmt_v3/            # RCMT V3
edge_infer_cloud/models/       # 云端模型
edge_infer_cloud/training/     # 训练服务
```

**适用任务**:
- PyTorch 深度学习
- 变化检测算法
- Transformer 架构
- 模型优化 (量化/蒸馏)
- TensorRT 导出

### 3.3 产品开发代理 (product-dev)

**代码范围**:
```
edge_infer_cloud/docs/         # 文档
```

**适用任务**:
- 产品规划
- 需求分析
- 文档维护
- 用户体验
- 路线图制定

---

## 4. 工作流程

```
用户请求 → 主代理(main) → 分析任务类型 → 委托子代理
                                    ↓
              ┌─────────────────────┼─────────────────────┐
              ↓                     ↓                     ↓
       software-dev           algorithm-dev          product-dev
              ↓                     ↓                     ↓
         执行任务              执行任务              执行任务
              ↓                     ↓                     ↓
              └─────────────────────┼─────────────────────┘
                                    ↓
                            返回结果给主代理
```

---

## 5. 注意事项

1. **Token隔离**: 子代理有独立上下文，不会消耗主代理token
2. **并发限制**: 最多同时运行4个子代理
3. **超时设置**: 子代理任务超时时间1小时
4. **结果合并**: 子代理完成后，主代理会收到结果摘要

---

**配置状态**: ✅ 已配置
**最后更新**: 2026-03-06
