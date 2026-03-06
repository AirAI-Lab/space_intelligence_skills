# Session使用指南

## 概述
本文档记录了RCMT-V3项目的智能体session管理，方便后续任务调用和上下文延续。

---

## 📝 写作智能体Session

### Session信息
- **标签**: `论文tex重新生成`
- **Session Key**: `agent:main:subagent:f3745c89-803b-43d0-9bcb-4441cc0efe94`
- **状态**: ✅ 已完成
- **创建时间**: 2026-03-05 19:50

### 核心能力
- 基于实验数据生成高质量学术论文
- 中英文双语写作
- IEEE期刊格式规范
- 数学公式、表格、图表处理

### Session上下文包含
✅ RCMT-V3论文完整结构
✅ Hybrid版本实验数据（11.8M, 90.16% F1, 45 FPS）
✅ Swin版本实验数据（58.7M, 91.45% F1, 32 FPS）
✅ Dual Architecture、BTF、Systematic Optimization创新点
✅ 所有对比实验和消融研究数据

### 如何调用此session

#### 方法1: 直接发送消息
```
sessions_send(
    sessionKey="agent:main:subagent:f3745c89-803b-43d0-9bcb-4441cc0efe94",
    message="修改Abstract部分，强调Dual Architecture的创新性"
)
```

#### 方法2: 使用@delegate标签
```
@delegate 修改论文的Introduction部分，添加更多相关工作引用
```

#### 适用场景
- 📄 论文内容修改和优化
- 📊 补充实验结果和分析
- 🔄 生成其他格式的文档（markdown、Word等）
- 🌐 翻译和本地化
- ✏️ 响应reviewer意见

---

## 🤖 变化检测大模型开发Session

### Session信息
- **标签**: `CD模型开发`
- **Session Key**: `agent:main:subagent:98a36e19-b468-4bbd-8760-f37159c9026d`
- **状态**: 🟢 初始化中
- **创建时间**: 2026-03-05 20:19

### 核心能力
- 模型架构设计（Transformer, Hybrid, CNN等）
- 训练策略优化（Loss, Scheduler, Augmentation）
- 实验设计和消融研究
- 性能评估和结果分析
- 模型压缩和部署优化

### 技术环境
- **框架**: PyTorch 2.0.1 + CUDA 11.8
- **数据集**: LEVIR-CD, SYSU-CD, WHU-CD
- **硬件**: RTX 5060 Ti (16GB VRAM)
- **工作目录**: D:\github\edge_infer_cloud\projects\rcmt_v3

### 如何调用此session

#### 方法1: 直接发送消息
```
sessions_send(
    sessionKey="agent:main:subagent:98a36e19-b468-4bbd-8760-f37159c9026d",
    message="设计一个新的Transformer-based变化检测模型架构"
)
```

#### 方法2: 使用@delegate标签
```
@delegate 优化当前模型的训练策略，尝试新的数据增强方法
```

#### 适用场景
- 🏗️ 模型架构设计和实现
- 🔧 超参数调优和训练策略
- 📈 实验管理和结果分析
- 🚀 模型部署和推理优化
- 📊 消融研究和对比实验

---

## 💡 使用建议

### Session选择
- **论文写作相关** → 使用 `论文tex重新生成` session
- **模型开发相关** → 使用 `变化检测大模型开发` session

### 上下文延续
这些session都保留了完整的上下文，包括：
- 项目结构和文件位置
- 实验数据和结果
- 之前的讨论和决策
- 技术细节和配置

### 任务委托
使用 `@delegate` 标签可以自动将任务分配给合适的session。

---

## 📋 Session管理

### 查看所有session
```
sessions_list()
```

### 查看活跃session
```
subagents(action="list")
```

### 结束session
```
subagents(action="kill", target="session_key")
```

---

**最后更新**: 2026-03-05 20:17
**维护者**: RCMT-V3项目组
