# Temporal PEFT v2.0 训练脚本

## 创建时间
2026-03-16 21:26 UTC+8

## 脚本信息

- **文件**: `train_v2.py`
- **位置**: `/workspace/rcmt_v3/temporal_peft/train_v2.py`
- **状态**: ✅ 已创建并同步

## v2.0架构

```yaml
Temporal PEFT v2.0:
  基础组件:
    - SAM2 Backbone (frozen)
    - Temporal Adapter
    - Change-Aware LoRA
  
  v2.0新增:
    ✅ MultiScaleTemporalDecoder (1.75M)
      - TemporalDiffModule (时序差异检测)
      - AdaptiveScaleFusion (自适应尺度融合)
      - BoundaryRefinementModule (边界细化) ← 关键！
      - ChangeAwareAttention (变化感知注意力)
    
    ✅ AdvancedCombinedLoss
      - BoundaryWeightedLoss (边界权重x2)
      - OnlineHardExampleMining (30%困难样本)
      - Dice Loss
      - Focal Loss
```

## 参数统计

| 组件 | 参数量 |
|------|--------|
| 基础PEFT | ~1.67M |
| MultiScaleTemporalDecoder | +1.75M |
| **总计** | **~3.42M** |

## 预期性能

| 指标 | v1.0 | v2.0 | PeftCD |
|------|------|------|--------|
| **F1** | 87-89% | **90-92%** 🎯 | 92.3% |
| **参数** | 1.67M | 3.42M | 10.0M |
| **F1/Param** | 53.3 | **26.9** | 9.23 |
| **速度** | ~35 FPS | ~30 FPS | ~25 FPS |

## 核心创新

### 1. 边界细化模块（关键！）
- 专门检测变化边界
- 边界注意力机制
- 提升边界区域精度
- **预期F1提升**: +2-3%

### 2. 边界加权损失
- 边界区域权重 x2
- 在线困难样本挖掘
- 平衡边界和内部区域
- **预期F1提升**: +1-1.5%

### 3. 完整数据集
- 7,134训练样本（vs 错误的89）
- 2,038验证样本
- **预期F1提升**: +20-25%

## 启动训练

```bash
# 复制脚本到容器
docker cp train_v2.py rcmt-training:/workspace/rcmt_v3/temporal_peft/

# 启动训练
docker exec rcmt-training bash -c "cd /workspace/rcmt_v3/temporal_peft && \
  nohup python3 train_v2.py > /tmp/peft_v2_train.log 2>&1 &"

# 监控训练
docker exec rcmt-training tail -f /tmp/peft_v2_train.log
```

## 监控指标

### 训练过程
- 每10 epochs打印详细指标
- 自动保存最佳模型（F1提升时）
- Early Stopping (patience=20)

### 关键指标
- **F1**: 目标 ≥ 90%
- **Boundary Loss**: 边界区域损失
- **F1/Param**: 目标 ≥ 25

### 里程碑
- ✅ F1 ≥ 87%: 基线达标
- ✅ F1 ≥ 90%: 达到目标
- 🏆 F1 ≥ 92.3%: 超越PeftCD！

## 对比实验

完成后进行完整对比：
1. vs PeftCD (SOTA)
2. vs ChangeFormer
3. vs BIT
4. vs v1.0 (基线)

## 输出文件

- `best_model.pth`: 最佳模型
- `latest_checkpoint.pth`: 最新检查点
- `logs/`: TensorBoard日志

## 时间预估

- 训练时间: 10-15小时
- 预计完成: 明天上午

---

**创建者**: OpenClaw Innovation Team  
**创建时间**: 2026-03-16 21:26  
**状态**: ✅ 脚本就绪，待启动训练
