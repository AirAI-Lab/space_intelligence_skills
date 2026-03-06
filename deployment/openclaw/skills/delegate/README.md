# 智能委托系统 - 自动子代理判断

## 功能说明

**零学习成本，全自动智能判断**

系统会自动分析每个任务的复杂度，决定是在主对话执行还是委托给子代理。用户无需学习任何特殊语法，**像平时一样自然输入即可**。

---

## 安装方法

### 一键安装

```batch
cd D:\github\edge_infer_cloud\deployment\openclaw
install-delegate-skill.bat
```

### 手动安装

```batch
# 创建技能目录
mkdir C:\Users\wennu\.openclaw\skills\delegate

# 复制文件
copy D:\github\edge_infer_cloud\deployment\openclaw\skills\delegate\SKILL.md C:\Users\wennu\.openclaw\skills\delegate\
copy D:\github\edge_infer_cloud\deployment\openclaw\skills\delegate\delegate.js C:\Users\wennu\.openclaw\skills\delegate\
```

### 重启网关

```batch
cd D:\github\edge_infer_cloud\deployment\openclaw
stop-gateway.bat
start-gateway.bat
```

---

## 使用方法

### 自然输入（无需任何语法）

直接输入你的任务，系统自动判断：

```
✅ 简单任务 -> 主对话执行
帮我读取 config.json

✅ 复杂任务 -> 自动子代理
请全面分析 rcmt_v3 项目的代码架构并给出优化建议
```

---

## 智能判断示例

### 示例1：简单任务（主对话）

```
用户：读取 train.log 的最后20行

系统判断：
- 复杂度：2分
- 判断：简单任务
- 执行：主对话直接执行

结果：立即显示日志内容
```

### 示例2：中等任务（主对话）

```
用户：分析 train_rcmt_v3_optimized.py 使用的模型架构

系统判断：
- 复杂度：3分
- 判断：中等任务
- 执行：主对话执行

结果：显示架构分析
```

### 示例3：复杂任务（自动子代理）

```
用户：请全面分析 rcmt_v3 项目，包括两个训练脚本的区别，
      并给出统一的命名建议，最后修订论文

系统判断：
- 复杂度：12分
  - "全面" +3分
  - "分析" +3分
  - 多个文件操作 +4分
  - 论文修订 +3分
- 判断：复杂任务
- 执行：自动生成子代理

结果：
[Spawned subagent main (session: xxx, run yyy)]

... [后台执行] ...

[子代理完成]
✅ 项目分析完成
- 代码分析：完成
- 命名建议：完成
- 论文修订：完成
详细报告已保存
```

---

## 判断标准

### 自动触发子代理的条件

| 条件 | 权重 | 说明 |
|------|------|------|
| 高权重关键词 | +3分/个 | 全面、完整、深度、修订、优化、重构、分析、研究、批量 |
| 中权重关键词 | +2分/个 | 配置、集成、生成、输出、报告 |
| 文件操作 | +2分/个 | 涉及多个文件的操作 |
| 工具调用 | +1分/个 | 预估需要的工具调用次数 |
| 复杂任务类型 | +3分 | 论文修订、代码审查、批量处理 |
| 长任务描述 | +2分 | 超过200字符 |

**阈值：>= 5分 → 自动子代理**

---

## 对比说明

### 之前（手动）

```
用户需要手动输入：
/subagents spawn main "任务：..." --model xxx --runTimeoutSeconds xxx
```

### 现在（自动）

```
用户只需输入：
请全面分析项目代码并给出优化建议

系统自动：
1. 检测复杂度
2. 判断执行方式
3. 生成子代理命令
4. 监控执行
5. 汇总结果
```

---

## 配置选项

在 `openclaw.json` 中配置：

```json
{
  "agents": {
    "defaults": {
      "subagents": {
        "model": "zai/glm-4.7-flash",
        "maxConcurrent": 4,
        "runTimeoutSeconds": 900,
        "autoDelegateThreshold": 5
      }
    }
  }
}
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| autoDelegateThreshold | 自动委托阈值（分） | 5 |
| model | 子代理使用的模型 | zai/glm-4.7-flash |
| runTimeoutSeconds | 默认超时（秒） | 900 |

---

## 监控子代理

如果任务被委托给子代理，可以使用以下命令监控：

```
/subagents list              # 查看所有子代理
/subagents info <id>         # 查看子代理详情
/subagents log <id>          # 查看子代理输出
/subagents kill <id>         # 停止子代理
```

---

## 实际使用案例

### 案例1：代码分析

```
输入：分析项目中所有训练脚本的模型配置差异

系统：
[检测到：多个脚本 + 分析 = 7分]
[决策：使用子代理]

[Spawned subagent main (session: xxx)]

完成后：
✅ 分析完成
- train_rcmt_v3_optimized.py：CNN+Transformer，11.8M参数
- train_rcmt_v3_swin_temporal.py：Swin+Transformer，58.7M参数
- 差异总结：架构复杂度、参数量、性能对比
```

### 案例2：论文修订

```
输入：请根据IEEE顶刊风格修订论文，修正所有格式问题

系统：
[检测到：修订 + IEEE + 所有格式 = 10分]
[决策：使用子代理，使用主模型]

[Spawned subagent main (model: zai/glm-4.7)]

完成后：
✅ 论文修订完成
- 摘要格式：已修正
- Markdown格式：已移除
- 段落表述：已优化
- 中英文版本：已输出
```

### 案例3：批量处理

```
输入：批量处理所有训练日志，生成性能报告

系统：
[检测到：批量 + 所有日志 + 生成报告 = 9分]
[决策：使用子代理]

[Spawned subagent main (session: xxx)]

完成后：
✅ 批量处理完成
- 处理日志：5个文件
- 生成报告：performance_report.md
- 性能趋势图：已保存
```

---

## 技能文件位置

```
C:\Users\wennu\.openclaw\skills\delegate\
├── SKILL.md          # 技能说明
├── delegate.js       # 实现代码
├── package.json      # 配置
└── README.md         # 本文件
```

---

## 故障排除

### 技能未生效

1. 确认文件已复制：
   ```
   dir C:\Users\wennu\.openclaw\skills\delegate\
   ```

2. 确认 Gateway 已重启：
   ```
   netstat -ano | findstr ":18789"
   ```

### 子代理未自动触发

1. 检查任务复杂度是否达到阈值（5分）
2. 可以手动触发：
   ```
   [delegate] 你的任务
   ```

### 查看系统判断

```
用户：为什么这个任务用子代理？
系统：该任务复杂度评分为 8 分
      - 检测到高权重关键词: "全面"
      - 检测到高权重关键词: "分析"
      - 预估需要10+次工具调用
      预计执行时间约15分钟
      -> 使用子代理以保持主对话清洁
```

---

## 核心优势

| 特性 | 说明 |
|------|------|
| **零学习成本** | 无需记忆任何语法或命令 |
| **自动判断** | 系统自动分析任务复杂度 |
| **透明决策** | 判断逻辑清晰可见 |
| **保持清洁** | 复杂任务自动隔离 |
| **智能优化** | 自动选择最佳执行方式 |
| **节省时间** | 无需手动编写子代理命令 |

---

## 下一步

1. ✅ 运行 `install-delegate-skill.bat`
2. ✅ 重启 Gateway
3. ✅ 像平时一样输入任务
4. ✅ 系统自动优化执行方式

**就这么简单！**
