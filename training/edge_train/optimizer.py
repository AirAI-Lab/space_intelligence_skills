"""
智能训练参数优化器

根据当前训练状态和指标趋势，自动优化续训参数，以获得最佳训练结果。
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TrainingState:
    """训练状态数据类"""
    current_epoch: int
    current_map50_95: float
    current_map50: float
    current_loss: float
    best_map50_95: float
    best_epoch: int

    # 趋势分析
    map_improvement_last_n: float  # 最近 N 轮的 mAP 提升幅度
    map_trend: str  # 'rising', 'stable', 'falling', 'plateau'
    loss_trend: str  # 'decreasing', 'stable', 'increasing'

    # 训练阶段
    training_phase: str  # 'early', 'middle', 'late', 'converged'


@dataclass
class ParameterRecommendation:
    """参数调整建议"""
    lr0: Optional[float] = None
    lrf: Optional[float] = None
    patience: Optional[int] = None
    weight_decay: Optional[float] = None
    warmup_epochs: Optional[int] = None
    mosaic: Optional[bool] = None
    mixup: Optional[float] = None
    close_mosaic: Optional[int] = None

    # 建议
    should_continue: bool = True
    reason: str = ""
    confidence: str = "medium"  # 'low', 'medium', 'high'

    def to_dict(self) -> Dict:
        """转换为字典，过滤 None 值"""
        return {
            'lr0': self.lr0,
            'lrf': self.lrf,
            'patience': self.patience,
            'weight_decay': self.weight_decay,
            'warmup_epochs': self.warmup_epochs,
            'mosaic': self.mosaic,
            'mixup': self.mixup,
            'close_mosaic': self.close_mosaic,
            'should_continue': self.should_continue,
            'reason': self.reason,
            'confidence': self.confidence
        }


class IntelligentParameterOptimizer:
    """智能训练参数优化器"""

    def __init__(self, analysis_window: int = 10):
        """
        初始化优化器

        Args:
            analysis_window: 分析最近多少轮的数据
        """
        self.analysis_window = analysis_window

    def analyze_training_state(
        self,
        results_csv: Path,
        checkpoint_epoch: int
    ) -> Optional[TrainingState]:
        """
        分析当前训练状态

        Args:
            results_csv: 训练结果文件
            checkpoint_epoch: 检查点对应的 epoch

        Returns:
            TrainingState: 训练状态，如果分析失败返回 None
        """
        if not results_csv.exists():
            logger.warning(f"results.csv 不存在: {results_csv}")
            return None

        try:
            df = pd.read_csv(results_csv)
            if df.empty:
                logger.warning("results.csv 为空")
                return None

            # 获取最新数据
            latest = df.iloc[-1]

            # 读取 mAP50-95（列名可能是 metrics/mAP50-95(B)）
            map_col = None
            for col in ['metrics/mAP50-95(B)', 'val/mAP50-95', 'mAP50-95']:
                if col in df.columns:
                    map_col = col
                    break

            if map_col is None:
                logger.warning("未找到 mAP50-95 列")
                return None

            current_map50_95 = float(latest[map_col])
            current_epoch = int(latest['epoch']) + 1  # CSV 中 epoch 从 0 开始

            # 读取 mAP50
            map50_col = None
            for col in ['metrics/mAP50(B)', 'val/mAP50', 'mAP50']:
                if col in df.columns:
                    map50_col = col
                    break
            current_map50 = float(latest[map50_col]) if map50_col else current_map50_95 * 1.2

            # 计算当前 loss
            current_loss = (
                latest.get('train/box_loss', 0) +
                latest.get('train/cls_loss', 0) +
                latest.get('train/dfl_loss', 0)
            )

            # 找到最佳 mAP 和对应 epoch
            best_idx = df[map_col].idxmax()
            best_map50_95 = float(df.loc[best_idx, map_col])
            best_epoch = int(df.loc[best_idx, 'epoch']) + 1

            # 分析最近 N 轮的 mAP 变化
            recent_data = df.tail(min(self.analysis_window, len(df)))
            if len(recent_data) >= 2:
                map_improvement = float(recent_data.iloc[-1][map_col] - recent_data.iloc[0][map_col])
            else:
                map_improvement = 0.0

            # 判断趋势
            map_trend = self._classify_trend(recent_data, map_col, 'higher_is_better')
            loss_trend = self._classify_loss_trend(df)

            # 判断训练阶段
            training_phase = self._determine_training_phase(
                current_epoch,
                current_map50_95,
                map_improvement,
                map_trend
            )

            return TrainingState(
                current_epoch=current_epoch,
                current_map50_95=current_map50_95,
                current_map50=current_map50,
                current_loss=float(current_loss),
                best_map50_95=best_map50_95,
                best_epoch=best_epoch,
                map_improvement_last_n=map_improvement,
                map_trend=map_trend,
                loss_trend=loss_trend,
                training_phase=training_phase
            )

        except Exception as e:
            logger.error(f"分析训练状态失败: {e}")
            return None

    def _classify_trend(
        self,
        df: pd.DataFrame,
        col: str,
        mode: str = 'higher_is_better'
    ) -> str:
        """
        分类趋势

        Args:
            df: 数据框
            col: 列名
            mode: 'higher_is_better' 或 'lower_is_better'

        Returns:
            'rising', 'falling', 'stable', 'plateau'
        """
        if len(df) < 3:
            return 'stable'

        values = df[col].values
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]

        first_mean = np.mean(first_half)
        second_mean = np.mean(second_half)
        overall_std = np.std(values)

        # 计算变化率
        if mode == 'higher_is_better':
            change_rate = (second_mean - first_mean) / (abs(first_mean) + 1e-8)
        else:
            change_rate = (first_mean - second_mean) / (abs(first_mean) + 1e-8)

        # 判断趋势
        if overall_std < 0.001:
            return 'stable'
        elif change_rate > 0.02:
            return 'rising' if mode == 'higher_is_better' else 'falling'
        elif change_rate < -0.02:
            return 'falling' if mode == 'higher_is_better' else 'rising'
        else:
            # 检查是否平台期（标准差很小但变化率也不大）
            if overall_std < 0.01:
                return 'plateau'
            return 'stable'

    def _classify_loss_trend(self, df: pd.DataFrame) -> str:
        """分类 loss 趋势"""
        loss_cols = ['train/box_loss', 'train/cls_loss', 'train/dfl_loss']
        total_loss = df[loss_cols].sum(axis=1) if all(c in df.columns for c in loss_cols) else df['train/loss'] if 'train/loss' in df.columns else None

        if total_loss is None:
            return 'stable'

        recent_loss = total_loss.tail(min(self.analysis_window, len(total_loss)))
        return self._classify_trend(
            pd.DataFrame({'loss': recent_loss}),
            'loss',
            mode='lower_is_better'
        )

    def _determine_training_phase(
        self,
        epoch: int,
        map50_95: float,
        map_improvement: float,
        map_trend: str
    ) -> str:
        """
        判断训练阶段

        Args:
            epoch: 当前轮次
            map50_95: 当前 mAP50-95
            map_improvement: 最近 N 轮的提升幅度
            map_trend: mAP 趋势

        Returns:
            'early', 'middle', 'late', 'converged'
        """
        # 已收敛：mAP 很高且几乎不提升
        if map50_95 > 0.7 and abs(map_improvement) < 0.005:
            return 'converged'

        # 后期：mAP 较高或轮次较多
        if map50_95 > 0.5 or epoch > 100:
            if map_trend == 'plateau' or abs(map_improvement) < 0.01:
                return 'late'
            return 'middle'

        # 中期：有一定训练基础
        if epoch > 30:
            return 'middle'

        # 初期
        return 'early'

    def optimize_parameters(
        self,
        state: TrainingState,
        user_params: Dict,
        original_params: Dict
    ) -> ParameterRecommendation:
        """
        根据训练状态优化参数

        Args:
            state: 训练状态
            user_params: 用户指定的参数
            original_params: 原始训练参数

        Returns:
            ParameterRecommendation: 参数调整建议
        """
        recommendation = ParameterRecommendation()

        # 获取原始和用户参数
        orig_lr0 = original_params.get('lr0', 0.01)
        user_lr0 = user_params.get('lr0', orig_lr0)
        orig_patience = original_params.get('patience', 30)
        user_patience = user_params.get('patience', orig_patience)

        # 根据训练阶段和趋势调整参数
        phase = state.training_phase
        map_trend = state.map_trend
        improvement = state.map_improvement_last_n

        logger.info(f"智能参数优化: 阶段={phase}, mAP趋势={map_trend}, "
                   f"当前mAP={state.current_map50_95:.4f}, 提升幅度={improvement:.4f}")

        # ============ 学习率调整策略 ============
        if phase == 'early':
            # 初期：保持或略微降低学习率
            recommendation.lr0 = user_lr0
            recommendation.reason += "初期训练: 保持学习率. "

        elif phase == 'middle':
            # 中期：根据趋势调整
            if map_trend == 'rising':
                # 上升中：保持学习率
                recommendation.lr0 = user_lr0
                recommendation.reason += "中期上升: 保持学习率. "
            elif map_trend == 'stable' or map_trend == 'plateau':
                # 稳定/平台期：降低学习率精细调优
                recommendation.lr0 = user_lr0 * 0.5
                recommendation.reason += f"中期平台: 降低学习率 {user_lr0:.4f}→{recommendation.lr0:.4f}. "
                recommendation.confidence = 'high'
            else:  # falling
                # 下降中：大幅降低学习率
                recommendation.lr0 = user_lr0 * 0.2
                recommendation.reason += f"中期下降: 大幅降低学习率 {user_lr0:.4f}→{recommendation.lr0:.4f}. "
                recommendation.confidence = 'high'

        elif phase == 'late':
            # 后期：使用低学习率微调
            if map_trend == 'plateau' or abs(improvement) < 0.01:
                # 平台期：大幅降低学习率
                recommendation.lr0 = user_lr0 * 0.1
                recommendation.reason += f"后期平台: 大幅降低学习率 {user_lr0:.4f}→{recommendation.lr0:.4f}. "
                recommendation.confidence = 'high'

                # 建议关闭 mosaic 增强泛化
                recommendation.close_mosaic = max(10, state.current_epoch)
                recommendation.reason += f"关闭 mosaic (epoch {recommendation.close_mosaic}+). "
            else:
                recommendation.lr0 = user_lr0 * 0.3
                recommendation.reason += f"后期微调: 降低学习率 {user_lr0:.4f}→{recommendation.lr0:.4f}. "

        elif phase == 'converged':
            # 已收敛：建议停止训练
            recommendation.should_continue = False
            recommendation.reason = f"模型已收敛 (mAP={state.current_map50_95:.4f})，建议停止训练. "
            recommendation.confidence = 'high'
            return recommendation

        # ============ Patience 调整策略 ============
        if phase == 'early':
            # 初期：使用正常 patience
            recommendation.patience = max(30, user_patience)
            recommendation.reason += f"初期: patience={recommendation.patience}. "

        elif phase == 'middle':
            # 中期：根据提升幅度调整
            if abs(improvement) < 0.01:
                # 提升缓慢：增加 patience
                recommendation.patience = 50
                recommendation.reason += f"提升缓慢: patience→{recommendation.patience}. "
            else:
                recommendation.patience = 30
                recommendation.reason += f"提升正常: patience={recommendation.patience}. "

        elif phase == 'late':
            # 后期：大幅增加 patience 或建议停止
            if abs(improvement) < 0.005:
                # 几乎不提升：建议评估是否继续
                if state.current_map50_95 < 0.3:
                    # mAP 还很低，可能需要更多训练
                    recommendation.patience = 100
                    recommendation.reason += "后期低mAP: patience=100. "
                else:
                    recommendation.patience = 50
                    recommendation.reason += "后期稳定: patience=50. "
            else:
                recommendation.patience = 30
                recommendation.reason += f"后期提升: patience={recommendation.patience}. "

        # ============ 其他参数调整 ============
        # 后期增加正则化防止过拟合
        if phase == 'late' and state.loss_trend == 'increasing':
            orig_wd = original_params.get('weight_decay', 0.0005)
            recommendation.weight_decay = orig_wd * 2
            recommendation.reason += f"loss上升: 增加正则化 {orig_wd:.5f}→{recommendation.weight_decay:.5f}. "

        # ============ 最终建议 ============
        # 如果 mAP 很低且几乎不提升，可能需要调整数据集或模型
        if state.current_map50_95 < 0.1 and abs(improvement) < 0.005 and state.current_epoch > 50:
            recommendation.should_continue = False
            recommendation.reason = "mAP 过低且提升停滞，建议检查数据集或调整模型架构. "
            recommendation.confidence = 'medium'

        logger.info(f"智能参数优化结果: {recommendation.reason}")
        logger.info(f"调整后参数: lr0={recommendation.lr0}, patience={recommendation.patience}")

        return recommendation

    def apply_recommendation(
        self,
        user_params: Dict,
        recommendation: ParameterRecommendation
    ) -> Dict:
        """
        将建议应用到用户参数

        Args:
            user_params: 用户原始参数
            recommendation: 参数建议

        Returns:
            应用后的参数
        """
        optimized_params = user_params.copy()

        if recommendation.lr0 is not None:
            optimized_params['lr0'] = recommendation.lr0
        if recommendation.lrf is not None:
            optimized_params['lrf'] = recommendation.lrf
        if recommendation.patience is not None:
            optimized_params['patience'] = recommendation.patience
        if recommendation.weight_decay is not None:
            optimized_params['weight_decay'] = recommendation.weight_decay
        if recommendation.warmup_epochs is not None:
            optimized_params['warmup_epochs'] = recommendation.warmup_epochs
        if recommendation.mosaic is not None:
            optimized_params['mosaic'] = recommendation.mosaic
        if recommendation.mixup is not None:
            optimized_params['mixup'] = recommendation.mixup
        if recommendation.close_mosaic is not None:
            optimized_params['close_mosaic'] = recommendation.close_mosaic

        return optimized_params


def get_training_summary(results_csv: Path) -> Optional[Dict]:
    """
    获取训练摘要信息（用于前端显示）

    Args:
        results_csv: 训练结果文件

    Returns:
        训练摘要字典
    """
    if not results_csv.exists():
        return None

    try:
        df = pd.read_csv(results_csv)
        if df.empty:
            return None

        # 找到 mAP 列
        map_col = None
        for col in ['metrics/mAP50-95(B)', 'val/mAP50-95', 'mAP50-95']:
            if col in df.columns:
                map_col = col
                break

        if map_col is None:
            return None

        latest = df.iloc[-1]
        best_idx = df[map_col].idxmax()

        return {
            'total_epochs': len(df),
            'current_epoch': int(latest['epoch']) + 1,
            'current_map50_95': float(latest[map_col]),
            'best_map50_95': float(df.loc[best_idx, map_col]),
            'best_epoch': int(df.loc[best_idx, 'epoch']) + 1,
            'latest_loss': float(
                latest.get('train/box_loss', 0) +
                latest.get('train/cls_loss', 0) +
                latest.get('train/dfl_loss', 0)
            )
        }
    except Exception as e:
        logger.error(f"获取训练摘要失败: {e}")
        return None
