package com.edge.cloud.repository;

import com.edge.cloud.entity.OtaTask;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * OTA 升级任务数据访问接口
 */
@Repository
public interface OtaTaskRepository extends JpaRepository<OtaTask, String> {

    /**
     * 根据状态查询任务
     */
    List<OtaTask> findByStatus(OtaTask.OtaStatus status);

    /**
     * 根据状态查询任务（分页）
     */
    Page<OtaTask> findByStatus(OtaTask.OtaStatus status, Pageable pageable);

    /**
     * 根据升级类型查询
     */
    List<OtaTask> findByUpgradeType(OtaTask.UpgradeType upgradeType);

    /**
     * 查询正在运行的任务
     */
    @Query("SELECT o FROM OtaTask o WHERE o.status = 'RUNNING' ORDER BY o.createdAt")
    List<OtaTask> findRunningTasks();

    /**
     * 查询待运行的任务
     */
    @Query("SELECT o FROM OtaTask o WHERE o.status IN ('PENDING', 'SCHEDULED') ORDER BY o.scheduledTime ASC")
    List<OtaTask> findPendingTasks();
}
