package com.edge.cloud.repository;

import com.edge.cloud.entity.ModelDeployment;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 模型部署记录 Repository
 */
@Repository
public interface ModelDeploymentRepository extends JpaRepository<ModelDeployment, String> {

    /**
     * 根据模型ID查询部署记录
     */
    List<ModelDeployment> findByModelIdOrderByCreatedAtDesc(String modelId);

    /**
     * 根据设备ID查询部署记录
     */
    Page<ModelDeployment> findByDeviceIdOrderByCreatedAtDesc(String deviceId, Pageable pageable);

    /**
     * 根据状态查询部署记录
     */
    Page<ModelDeployment> findByStatusOrderByCreatedAtDesc(String status, Pageable pageable);

    /**
     * 根据部署类型查询
     */
    Page<ModelDeployment> findByDeploymentTypeOrderByCreatedAtDesc(String deploymentType, Pageable pageable);

    /**
     * 查询模型的活跃部署（状态为SUCCESS且未被回滚）
     */
    List<ModelDeployment> findByModelIdAndStatus(String modelId, String status);

    /**
     * 查询设备的当前部署
     */
    ModelDeployment findFirstByDeviceIdOrderByCreatedAtDesc(String deviceId);

    /**
     * 分页查询部署记录（支持多条件过滤）
     */
    @Query("SELECT d FROM ModelDeployment d WHERE " +
           "(CAST(:modelId AS text) IS NULL OR d.modelId = :modelId) AND " +
           "(CAST(:deviceId AS text) IS NULL OR d.deviceId = :deviceId) AND " +
           "(CAST(:status AS text) IS NULL OR d.status = :status) AND " +
           "(CAST(:deploymentType AS text) IS NULL OR d.deploymentType = :deploymentType) AND " +
           "(CAST(:startTime AS timestamp) IS NULL OR d.createdAt >= :startTime) AND " +
           "(CAST(:endTime AS timestamp) IS NULL OR d.createdAt <= :endTime)")
    Page<ModelDeployment> findByConditions(
        @Param("modelId") String modelId,
        @Param("deviceId") String deviceId,
        @Param("status") String status,
        @Param("deploymentType") String deploymentType,
        @Param("startTime") LocalDateTime startTime,
        @Param("endTime") LocalDateTime endTime,
        Pageable pageable
    );

    /**
     * 统计模型部署次数
     */
    @Query("SELECT COUNT(d) FROM ModelDeployment d WHERE d.modelId = :modelId")
    long countByModelId(@Param("modelId") String modelId);

    /**
     * 统计设备部署次数
     */
    @Query("SELECT COUNT(d) FROM ModelDeployment d WHERE d.deviceId = :deviceId")
    long countByDeviceId(@Param("deviceId") String deviceId);

    /**
     * 统计部署成功率
     */
    @Query("SELECT COUNT(d) FROM ModelDeployment d WHERE d.modelId = :modelId AND d.status = 'SUCCESS'")
    long countSuccessfulByModelId(@Param("modelId") String modelId);

    /**
     * 查询最近部署记录
     */
    @Query("SELECT d FROM ModelDeployment d ORDER BY d.createdAt DESC")
    Page<ModelDeployment> findRecentDeployments(Pageable pageable);

    /**
     * 根据OTA任务ID和设备ID查找部署记录
     */
    java.util.Optional<ModelDeployment> findByOtaTaskIdAndDeviceId(String otaTaskId, String deviceId);
}
