package com.edge.cloud.repository;

import com.edge.cloud.entity.AlertRule;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AlertRuleRepository extends JpaRepository<AlertRule, Long> {
    List<AlertRule> findByEnabledTrue();

    List<AlertRule> findByEnabledTrueAndDeviceId(String deviceId);

    List<AlertRule> findByEnabledTrueAndTriggerCloudInferTrue();
}
