# 空中智能体 - 子代理管理配置

> **目的**: 定义不同模块的AI智能体负责人
> **使用**: 通过 `@delegate` 命令调用

---

## 1. 代理定义

### 1.1 软件开发代理

**代号**: `software-dev`
**职责**: 边缘AI推理框架、云边协同平台

**代码范围**:
```
edge_infer/src/core/           # 核心框架
edge_infer/src/plugins/        # 推理插件
edge_infer/src/plugin_manager/ # 插件管理
edge_infer_cloud/backend/      # 后端服务
edge_infer_cloud/frontend/     # 前端界面
edge_infer_cloud/edge-agent/   # 边缘代理
```

**技能**:
- C++/Python 开发
- Java/Spring Boot 后端
- Vue3 前端
- MQTT 通讯
- TensorRT 推理优化

---

### 1.2 算法开发代理

**代号**: `algorithm-dev`
**职责**: RCMT变化检测、模型训练、算法优化

**代码范围**:
```
edge_infer/models/rcmt/        # RCMT模型
edge_infer/rcmt_v3/            # RCMT V3
edge_infer_cloud/models/       # 云端模型
edge_infer_cloud/training/     # 训练服务
edge_infer_cloud/data/         # 数据集
```

**技能**:
- PyTorch 深度学习
- 变化检测算法
- Transformer 架构
- 模型优化 (量化/蒸馏)
- TensorRT 导出

---

### 1.3 产品开发代理

**代号**: `product-dev`
**职责**: 产品规划、需求管理、用户体验

**代码范围**:
```
edge_infer_cloud/docs/         # 文档
edge_infer/docs/               # 边缘文档
```

**技能**:
- 产品规划
- 需求分析
- 用户研究
- 竞品分析
- 路线图制定

---

## 2. 使用方式

### 2.1 直接调用

```
@delegate 检查训练状态
@delegate 优化RCMT参数
```

默认会根据任务内容自动选择合适的代理。

### 2.2 指定代理

```
@delegate 软件开发代理: 检查插件加载逻辑
@delegate 算法开发代理: 对比Swin V1和V2
@delegate 产品开发代理: 更新产品路线图
```

---

## 3. 工作流程

```
用户请求 → @delegate → 分析任务 → 选择代理 → 执行任务 → 返回结果
                           ↓
              ┌────────────┼────────────┐
              ↓            ↓            ↓
         software-dev  algorithm-dev  product-dev
```

---

## 4. 独立Session

空中智能体作为独立的长期Session运行，支持：

- ✅ 持续记忆项目状态
- ✅ 理解代码仓库结构
- ✅ 跟踪训练进度
- ✅ 管理开发任务

### 4.1 Session配置

```yaml
# 空中智能体 Session
session_id: skyedge-agent
label: 空中智能体
type: persistent
memory:
  - MEMORY.md          # 长期记忆
  - memory/daily/      # 日记
  - docs/              # 文档
workspaces:
  - D:\github\edge_infer_cloud
  - D:\github\edge_infer
```

### 4.2 启动Session

```
首次启动:
@delegate 请读取项目文档并建立项目记忆

日常使用:
@delegate 检查训练进度
@delegate 软件开发代理: 修复插件加载问题
```

---

## 5. 维护指南

### 5.1 记忆更新

定期更新以下文件：
- `MEMORY.md` - 长期记忆 (重要决策、架构变更)
- `memory/YYYY-MM-DD.md` - 日常工作记录

### 5.2 文档维护

- 新功能开发 → 更新相关技术文档
- 架构变更 → 更新架构文档
- API变更 → 更新API文档

---

**配置状态**: 活跃
**最后更新**: 2026-03-06
