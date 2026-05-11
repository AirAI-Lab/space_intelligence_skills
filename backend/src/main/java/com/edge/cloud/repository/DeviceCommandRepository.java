package com.edge.cloud.repository;

import com.edge.cloud.entity.DeviceCommand;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface DeviceCommandRepository extends JpaRepository<DeviceCommand, Long> {
    List<DeviceCommand> findByDeviceIdOrderByCreatedAtDesc(String deviceId);
    Optional<DeviceCommand> findByCommandId(String commandId);
    List<DeviceCommand> findByStatusAndExpireAtBefore(String status, LocalDateTime before);
    List<DeviceCommand> findByDeviceIdAndStatus(String deviceId, String status);
}
