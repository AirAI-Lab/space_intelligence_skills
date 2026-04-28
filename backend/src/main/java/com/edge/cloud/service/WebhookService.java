package com.edge.cloud.service;

import com.edge.cloud.entity.WebhookConfig;
import com.edge.cloud.dto.InferenceResultDTO;
import com.edge.cloud.repository.WebhookConfigRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.*;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.*;
import com.fasterxml.jackson.core.type.TypeReference;

@Slf4j
@Service
@RequiredArgsConstructor
public class WebhookService {

    private final WebhookConfigRepository webhookConfigRepository;
    private final RestTemplate restTemplate = new RestTemplate();

    @Async
    public void fireAlertEvent(InferenceResultDTO result) {
        String eventType = "alert." + result.getAlertLevel();
        List<WebhookConfig> configs = webhookConfigRepository.findByEnabledTrue();

        for (WebhookConfig config : configs) {
            if (!matchesEvent(config.getEvents(), eventType)) continue;
            sendWebhook(config, eventType, result);
        }
    }

    @Async
    public void fireResultEvent(InferenceResultDTO result) {
        String eventType = "result." + result.getSource();
        List<WebhookConfig> configs = webhookConfigRepository.findByEnabledTrue();

        for (WebhookConfig config : configs) {
            if (!matchesEvent(config.getEvents(), eventType)) continue;
            sendWebhook(config, eventType, result);
        }
    }

    private boolean matchesEvent(String configuredEvents, String event) {
        if (configuredEvents == null || configuredEvents.isEmpty()) return true;
        for (String e : configuredEvents.split(",")) {
            String trimmed = e.trim();
            if (trimmed.equals(event) || trimmed.equals("*")) return true;
            // Support wildcards like "alert.*"
            if (trimmed.endsWith(".*") && event.startsWith(trimmed.substring(0, trimmed.length() - 1))) return true;
        }
        return false;
    }

    private void sendWebhook(WebhookConfig config, String eventType, InferenceResultDTO payload) {
        try {
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("event", eventType);
            body.put("timestamp", LocalDateTime.now().toString());
            body.put("data", payload);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            if (config.getSecret() != null && !config.getSecret().isEmpty()) {
                headers.set("X-Webhook-Secret", config.getSecret());
            }
            if (config.getHeaders() != null && !config.getHeaders().isEmpty()) {
                try {
                    Map<String, String> customHeaders = new com.fasterxml.jackson.databind.ObjectMapper()
                            .readValue(config.getHeaders(), new TypeReference<Map<String, String>>() {});
                    customHeaders.forEach(headers::set);
                } catch (Exception ignored) {}
            }

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);
            ResponseEntity<String> response = restTemplate.exchange(
                    config.getUrl(), HttpMethod.POST, entity, String.class);

            config.setLastTriggerTime(LocalDateTime.now());
            config.setTriggerCount(config.getTriggerCount() != null ? config.getTriggerCount() + 1 : 1);
            config.setLastError(null);
            webhookConfigRepository.save(config);

            log.debug("Webhook fired: config={}, event={}, status={}",
                    config.getName(), eventType, response.getStatusCode());
        } catch (Exception e) {
            log.warn("Webhook failed: config={}, event={}, error={}",
                    config.getName(), eventType, e.getMessage());
            config.setLastError(e.getMessage().substring(0, Math.min(e.getMessage().length(), 500)));
            webhookConfigRepository.save(config);
        }
    }

    @Transactional
    public WebhookConfig createConfig(com.edge.cloud.dto.WebhookConfigRequest request) {
        WebhookConfig config = new WebhookConfig();
        config.setName(request.getName());
        config.setUrl(request.getUrl());
        config.setSecret(request.getSecret());
        config.setEvents(request.getEvents());
        config.setHeaders(request.getHeaders());
        config.setEnabled(request.getEnabled() != null ? request.getEnabled() : true);
        config.setTriggerCount(0);
        return webhookConfigRepository.save(config);
    }

    @Transactional
    public WebhookConfig updateConfig(Long id, com.edge.cloud.dto.WebhookConfigRequest request) {
        WebhookConfig config = webhookConfigRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Webhook config not found: " + id));
        if (request.getName() != null) config.setName(request.getName());
        if (request.getUrl() != null) config.setUrl(request.getUrl());
        if (request.getSecret() != null) config.setSecret(request.getSecret());
        if (request.getEvents() != null) config.setEvents(request.getEvents());
        if (request.getHeaders() != null) config.setHeaders(request.getHeaders());
        if (request.getEnabled() != null) config.setEnabled(request.getEnabled());
        return webhookConfigRepository.save(config);
    }

    public void deleteConfig(Long id) {
        webhookConfigRepository.deleteById(id);
    }

    public List<WebhookConfig> listConfigs() {
        return webhookConfigRepository.findAll();
    }
}
