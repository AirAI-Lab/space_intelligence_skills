# HEARTBEAT.md

# 空中智能体 - 定期检查任务

## V6训练监控 (每30分钟)
- 检查V6论文版训练状态（容器：rcmt-training）
- 脚本: `train_rcmt_v6_paper.py` (400 epochs)
- 目录: `logs_swin_v6_paper/` + `checkpoints_swin_v6_paper/`

### 📢 新Best F1检测 (每次heartbeat执行)
1. 获取best_model修改时间：
   ```bash
   docker exec rcmt-training stat -c '%Y %y' /workspace/rcmt_v3/checkpoints_swin_v6_paper/best_model.pth
   ```
2. 比较状态文件：`memory/v6_best_f1_state.json`
3. 如果修改时间更新，从日志提取新Best F1：
   ```bash
   docker exec rcmt-training tail -300 /workspace/rcmt_v3/logs_swin_v6_paper/nohup.log | grep -B8 'New Best Model'
   ```
4. **立即发送通知**到飞书

### ⚠️ 卡死检测
- 单epoch >10分钟，如果超时>1小时则续训
- 日志追加，不替换（使用 `>>` 追加模式）

### 🔄 200 Epoch自动备份
- 脚本: `/tmp/check_v6_200ep_backup.sh`
- 触发条件: Epoch >= 200
- 备份: `best_model.pth` → `best_model_200ep.pth`
- 标记: `.backup_200ep_done`

### 📊 V6训练状态 (20:29 UTC+8 - 3月16日) - 🔄 **运行中**
- **状态**: 🔄 运行中
- **当前Epoch**: 351/400 (87.75%)
- **Best F1**: **0.8955** (Epoch 347) 🏆 **距V4仅差0.08%！**
- **最后更新**: 2026-03-16 20:29 UTC+8
- **参数量**: **58.7M** (Swin-Tiny)
- **数据集**: 7,120 train + 1,024 val ✅
- **200 epoch备份**: ✅ **已完成** (best_model_200ep.pth, 674MB)
- **最新突破**: ✅ **Epoch 347达到新Best F1 0.8955** (距V4仅差0.08%)

### 🚀 Temporal PEFT训练 - ✅ **已完成** (18:19 UTC+8 - 3月16日)
- **状态**: ✅ **训练完成**
- **最终进度**: 100/100 epochs (100%)
- **Best F1**: **0.6104** (Epoch 51) 🏆
- **最终性能** (Epoch 100): 训练F1=60.24%, 验证F1=60.01%
- **Loss**: 训练0.8444, 验证0.8570
- **训练时长**: ~1小时15分钟
- **数据集**: 89 train + 26 val (LEVIR-CD子集)
- **模型文件**: `best_model_100ep_fixed.pth` (Epoch 51, F1=61.04%)
- **关键成果**: ✅ 过拟合问题完全解决，训练稳定

## V4训练 ✅ 已完成
- **最终结果**: F1=**0.896282** (Epoch 317/400)
- **200 Epoch对比**: F1=**0.893730** (Epoch 195)
- 模型: `checkpoints_swin_v4_paper/best_model.pth`

## 代码同步检查 (每4小时)
- 检查edge_infer_cloud未提交的代码变更
- 检查edge_infer未提交的代码变更
- 自动提交有意义的变更（带描述）

## 日报生成 (每天18:00)
- 汇总今天的训练进度和指标
- 汇总代码变更
- 生成简要日报

---

## 当前重点 (Phase 1: 感知完善)

| 优先级 | 任务 | 状态 |
|--------|------|------|
| ✅ P0 | V4论文版训练 (400 epochs) | ✅ **完成** (F1=0.896282) |
| 🔄 P0 | V6论文版训练 (400 epochs) | 🚧 进行中 |
| P0 | 模型导出ONNX/TensorRT | ⏳ 待开始 |
| P0 | 论文更新（V4结果和策略） | 🚧 进行中 |
| P1 | 用户文档更新 | ⏳ 待开始 |
| P1 | API文档补充 | ⏳ 待开始 |

### 📊 训练状态 (2026-03-15 09:41 UTC+8)

**V4 (BTFormer)**: ✅ **完成**
- Best F1: **0.896282** (Epoch 317/400)
- 200 epoch内: F1=0.893730 (Epoch 195)
- 200 epoch后提升: **0.26%**
- 数据集: 7,120 train + 1,024 val ✅

**V6 (Swin-Temporal)**: ⏸️ **已暂停** (为Temporal PEFT让路)
- 最后记录: Epoch 347/400 (86.75%)
- Best F1: **0.8953** (Epoch 249) 🏆 距V4仅差0.10%
- 200 ep备份: ✅ **已完成**
- 数据集: 7,120 train + 1,024 val ✅

**Temporal PEFT (SAM2-Adapter)**: ✅ **已完成** ⚠️ **数据集错误**
- 最终: Epoch 100/100 (100%)
- Best F1: **0.6104** (Epoch 51)
- **问题**: 使用了错误的数据集（89样本子集）
- **修复**: 已准备完整数据集脚本（7,120样本）
- **预期F1**: 85-90% (使用完整数据集后)
- 完成时间: 2026-03-16 18:10 UTC+8

**📌 200 Epoch备份任务**: 当V6到达200 epoch时，备份best_model为`best_model_200ep.pth`

### 📈 V4 vs V6 公平对比
| 项目 | V4 (Hybrid) | V6 (Swin) |
|------|-------------|-----------|
| 参数量 | 11.8M | **58.7M** |
| Best F1 | 0.8963 | 训练中 |
| 数据集 | 7:2:1 ✅ | 7:2:1 ✅ |

---

## 执行说明

Heartbeat会定期读取此文件并执行里面的任务。
如果不需要任何检查，清空此文件内容即可（只保留注释）。
