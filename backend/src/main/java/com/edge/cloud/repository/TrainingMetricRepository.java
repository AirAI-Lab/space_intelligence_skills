package com.edge.cloud.repository;

import com.edge.cloud.entity.TrainingMetric;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 训练指标时序数据访问接口 (TimescaleDB)
 */
@Repository
public interface TrainingMetricRepository extends JpaRepository<TrainingMetric, Long> {

    /**
     * 根据任务ID查询所有指标
     */
    @Query("SELECT m FROM TrainingMetric m WHERE m.jobId = :jobId ORDER BY m.epoch ASC")
    List<TrainingMetric> findByJobIdOrderByEpoch(@Param("jobId") String jobId);

    /**
     * 根据任务ID和轮次查询指标
     */
    TrainingMetric findByJobIdAndEpoch(String jobId, Integer epoch);

    /**
     * 查询指定时间范围内的指标
     */
    @Query("SELECT m FROM TrainingMetric m WHERE m.jobId = :jobId AND m.time BETWEEN :startTime AND :endTime ORDER BY m.time ASC")
    List<TrainingMetric> findByJobIdAndTimeBetween(
            @Param("jobId") String jobId,
            @Param("startTime") LocalDateTime startTime,
            @Param("endTime") LocalDateTime endTime
    );

    /**
     * 查询最新的指标
     */
    @Query("SELECT m FROM TrainingMetric m WHERE m.jobId = :jobId ORDER BY m.time DESC")
    List<TrainingMetric> findLatestByJobId(@Param("jobId") String jobId);

    /**
     * 删除指定任务的所有指标
     */
    void deleteByJobId(String jobId);

    /**
     * 统计任务的指标数量
     */
    long countByJobId(String jobId);
}
