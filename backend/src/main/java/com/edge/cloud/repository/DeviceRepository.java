package com.edge.cloud.repository;

import com.edge.cloud.entity.Device;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * 设备数据访问接口
 */
@Repository
public interface DeviceRepository extends JpaRepository<Device, String> {

    /**
     * 根据设备状态查询设备列表
     */
    List<Device> findByStatus(Device.DeviceStatus status);

    /**
     * 根据设备组ID查询设备列表
     */
    List<Device> findByGroupId(String groupId);

    /**
     * 根据设备类型查询设备列表
     */
    List<Device> findByDeviceType(String deviceType);

    /**
     * 根据当前模型ID查询设备列表
     */
    List<Device> findByCurrentModelId(String modelId);

    /**
     * 查询需要心跳检查的离线设备
     * Note: 使用原生SQL查询，因为HQL不支持INTERVAL语法
     */
    @Query(value = "SELECT * FROM devices WHERE status = 'ONLINE' AND last_heartbeat < CURRENT_TIMESTAMP - INTERVAL '5 minutes'", nativeQuery = true)
    List<Device> findOfflineDevices();

    /**
     * 统计各状态的设备数量
     */
    @Query("SELECT d.status, COUNT(d) FROM Device d GROUP BY d.status")
    List<Object[]> countByStatus();
}
