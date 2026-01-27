package com.edge.cloud.repository;

import com.edge.cloud.entity.TrainingJob;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * 训练任务数据访问接口
 */
@Repository
public interface TrainingJobRepository extends JpaRepository<TrainingJob, String> {

    /**
     * 根据状态查询任务
     */
    List<TrainingJob> findByStatus(TrainingJob.TrainingStatus status);

    /**
     * 根据状态查询任务（分页）
     */
    Page<TrainingJob> findByStatus(TrainingJob.TrainingStatus status, Pageable pageable);

    /**
     * 根据数据集ID查询相关训练任务
     */
    List<TrainingJob> findByDatasetId(String datasetId);

    /**
     * 根据基础模型ID查询相关训练任务
     */
    List<TrainingJob> findByBaseModelId(String baseModelId);

    /**
     * 根据输出模型ID查询训练任务
     */
    Optional<TrainingJob> findByOutputModelId(String outputModelId);

    /**
     * 查询正在运行的任务
     */
    @Query("SELECT t FROM TrainingJob t WHERE t.status = 'RUNNING' ORDER BY t.createdAt")
    List<TrainingJob> findRunningJobs();

    /**
     * 查询待运行的任务
     */
    @Query("SELECT t FROM TrainingJob t WHERE t.status = 'PENDING' ORDER BY t.createdAt ASC")
    List<TrainingJob> findPendingJobs();

    /**
     * 统计各状态的任务数量
     */
    @Query("SELECT t.status, COUNT(t) FROM TrainingJob t GROUP BY t.status")
    List<Object[]> countByStatus();

    /**
     * 根据 MLflow Run ID 查询
     */
    Optional<TrainingJob> findByMlflowRunId(String mlflowRunId);
}
