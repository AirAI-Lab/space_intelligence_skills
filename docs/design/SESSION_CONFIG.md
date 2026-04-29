# 空中智能体 - 长期Session配置

> **Session名称**: 空中智能体
> **创建时间**: 2026-03-06
> **目的**: 持续管理和维护SkyEdge AI项目

---

## 1. Session信息

```yaml
name: 空中智能体
description: SkyEdge AI 项目管理Session
workspaces:
  - D:\github\edge_infer_cloud
  - D:\github\edge_infer
memory_files:
  - docs/v2_reorganized/MEMORY.md
  - memory/YYYY-MM-DD.md
config_files:
  - docs/v2_reorganized/AGENTS_CONFIG.md
```

## 2. 启动命令

### 方式1: 在当前Session中使用 @delegate

```
@delegate 请阅读项目记忆并汇报当前状态
@delegate 软件开发代理: 检查插件系统
@delegate 算法开发代理: 检查训练进度
```

### 方式2: 创建独立持久Session (需要支持thread的通道)

在Discord/Telegram等支持thread的通道：

```
@delegate 请成为空中智能体的长期助理，阅读以下文件建立项目理解：
1. D:\github\edge_infer_cloud\docs\v2_reorganized\MEMORY.md
2. D:\github\edge_infer_cloud\docs\v2_reorganized\README.md
3. D:\github\edge_infer_cloud\docs\v2_reorganized\AGENTS_CONFIG.md
```

## 3. 职责范围

### 3.1 项目记忆管理
- 维护 MEMORY.md 长期记忆
- 记录重要决策和变更
- 更新训练状态和进度

### 3.2 代码仓库理解
- 理解代码结构和模块
- 跟踪技术栈和依赖
- 分析代码变更影响

### 3.3 开发协调
- 分配任务给正确的子代理
- 协调不同模块的开发
- 跟踪任务进度

### 3.4 文档维护
- 保持文档最新
- 整理和归档旧文档
- 生成技术报告

## 4. 子代理体系

| 子代理 | 职责 | 代码范围 |
|--------|------|----------|
| software-dev | 边缘框架、云边平台 | edge_infer/src/*, backend/*, frontend/* |
| algorithm-dev | RCMT、模型训练 | models/rcmt/*, rcmt_v3/* |
| product-dev | 需求、路线图 | 文档、规划 |

## 5. 日常工作流程

### 每日启动检查
```
1. 检查训练状态: Get-Content "D:\github\edge_infer\rcmt_v3\logs_swin_final_v2\train.log" -Tail 50
2. 查看memory/目录下的日记
3. 确认待办任务优先级
```

### 任务分配
```
用户请求 → 分析任务类型 → 选择子代理 → 执行 → 更新记忆
```

### 记忆更新
```
重要事件 → 更新MEMORY.md
日常工作 → 更新memory/YYYY-MM-DD.md
```

## 6. 快速命令参考

### 训练状态
```powershell
Get-Content "D:\github\edge_infer\rcmt_v3\logs_swin_final_v2\train.log" -Tail 100
```

### 代码仓库
```powershell
# 边缘框架
cd D:\github\edge_infer
Get-ChildItem src/plugins -Directory

# 云边协同
cd D:\github\edge_infer_cloud
Get-ChildItem backend/src/main/java -Recurse -Filter "*.java"
```

### 文档更新
```powershell
cd D:\github\edge_infer_cloud
code docs/v2_reorganized/MEMORY.md
```

---

**配置状态**: 活跃
**最后更新**: 2026-03-06
