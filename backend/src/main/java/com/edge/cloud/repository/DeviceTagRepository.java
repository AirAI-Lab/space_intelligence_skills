package com.edge.cloud.repository;

import com.edge.cloud.entity.DeviceTag;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface DeviceTagRepository extends JpaRepository<DeviceTag, Long> {
    List<DeviceTag> findByDeviceId(String deviceId);
    List<DeviceTag> findByTagKeyAndTagValue(String tagKey, String tagValue);
    void deleteByDeviceIdAndTagKey(String deviceId, String tagKey);
    List<DeviceTag> findByDeviceIdAndTagKey(String deviceId, String tagKey);
}
