package com.edge.cloud.repository;

import com.edge.cloud.entity.ConversionTask;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * 模型转换任务数据访问接口
 */
@Repository
public interface ConversionTaskRepository extends JpaRepository<ConversionTask, String> {

    /**
     * 根据模型ID查询转换任务
     */
    List<ConversionTask> findByModelId(String modelId);

    /**
     * 根据状态查询任务
     */
    List<ConversionTask> findByStatus(ConversionTask.ConversionStatus status);

    /**
     * 根据状态查询任务（分页）
     */
    Page<ConversionTask> findByStatus(ConversionTask.ConversionStatus status, Pageable pageable);

    /**
     * 根据转换类型查询
     */
    List<ConversionTask> findByConversionType(ConversionTask.ConversionType conversionType);

    /**
     * 查询正在运行的任务
     */
    @Query("SELECT c FROM ConversionTask c WHERE c.status = 'RUNNING' ORDER BY c.createdAt")
    List<ConversionTask> findRunningTasks();

    /**
     * 查询待运行的任务
     */
    @Query("SELECT c FROM ConversionTask c WHERE c.status = 'PENDING' ORDER BY c.createdAt ASC")
    List<ConversionTask> findPendingTasks();
}
