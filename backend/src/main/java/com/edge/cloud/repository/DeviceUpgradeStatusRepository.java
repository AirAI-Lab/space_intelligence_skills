package com.edge.cloud.repository;

import com.edge.cloud.entity.DeviceUpgradeStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * 设备升级状态数据访问接口
 */
@Repository
public interface DeviceUpgradeStatusRepository extends JpaRepository<DeviceUpgradeStatus, String> {

    /**
     * 根据任务ID查询所有设备升级状态
     */
    List<DeviceUpgradeStatus> findByTaskId(String taskId);

    /**
     * 根据任务ID和状态查询
     */
    List<DeviceUpgradeStatus> findByTaskIdAndStatus(String taskId, DeviceUpgradeStatus.UpgradeStatus status);

    /**
     * 根据设备ID查询最近的升级状态
     */
    @Query("SELECT d FROM DeviceUpgradeStatus d WHERE d.deviceId = :deviceId ORDER BY d.createdAt DESC")
    List<DeviceUpgradeStatus> findRecentByDeviceId(String deviceId);

    /**
     * 查询任务中失败的设备
     */
    @Query("SELECT d FROM DeviceUpgradeStatus d WHERE d.taskId = :taskId AND d.status IN ('FAILED', 'DOWNLOAD_FAILED', 'INSTALL_FAILED')")
    List<DeviceUpgradeStatus> findFailedDevices(String taskId);

    /**
     * 查询任务中完成的设备
     */
    @Query("SELECT d FROM DeviceUpgradeStatus d WHERE d.taskId = :taskId AND d.status = 'COMPLETED'")
    List<DeviceUpgradeStatus> findCompletedDevices(String taskId);

    /**
     * 根据任务ID和设备ID查询（唯一约束）
     */
    Optional<DeviceUpgradeStatus> findByTaskIdAndDeviceId(String taskId, String deviceId);
}
