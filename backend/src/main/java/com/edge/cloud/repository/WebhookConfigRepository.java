package com.edge.cloud.repository;

import com.edge.cloud.entity.WebhookConfig;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface WebhookConfigRepository extends JpaRepository<WebhookConfig, Long> {
    List<WebhookConfig> findByEnabledTrue();
}
