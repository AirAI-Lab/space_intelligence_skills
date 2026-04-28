package com.edge.cloud.service;

import com.edge.cloud.dto.AlertRuleRequest;
import com.edge.cloud.dto.InferenceResultDTO;
import com.edge.cloud.entity.AlertRule;
import com.edge.cloud.repository.AlertRuleRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class AlertRuleService {

    private final AlertRuleRepository alertRuleRepository;

    public List<AlertRule> listRules() {
        return alertRuleRepository.findAll();
    }

    public List<AlertRule> getEnabledRules() {
        return alertRuleRepository.findByEnabledTrue();
    }

    public List<AlertRule> getCloudTriggerRules() {
        return alertRuleRepository.findByEnabledTrueAndTriggerCloudInferTrue();
    }

    @Transactional
    public AlertRule createRule(AlertRuleRequest request) {
        AlertRule rule = new AlertRule();
        applyRequest(rule, request);
        return alertRuleRepository.save(rule);
    }

    @Transactional
    public AlertRule updateRule(Long id, AlertRuleRequest request) {
        AlertRule rule = alertRuleRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Alert rule not found: " + id));
        applyRequest(rule, request);
        return alertRuleRepository.save(rule);
    }

    public void deleteRule(Long id) {
        alertRuleRepository.deleteById(id);
    }

    /**
     * Evaluate rules against an inference result and return the highest matching alert level.
     * Returns null if no rule matches (meaning the result should not generate an alert).
     */
    public String evaluateRules(InferenceResultDTO result) {
        List<AlertRule> rules = getEnabledRules();
        String highestLevel = null;
        int highestPriority = 0;

        for (AlertRule rule : rules) {
            if (!matchesRule(rule, result)) continue;

            // Check threshold condition
            if (!matchesCondition(rule, result)) continue;

            int priority = alertPriority(rule.getAlertLevel());
            if (priority > highestPriority) {
                highestPriority = priority;
                highestLevel = rule.getAlertLevel();
            }
        }
        return highestLevel;
    }

    /**
     * Check if any enabled rule requests cloud inference trigger for this result.
     */
    public boolean shouldTriggerCloudInfer(InferenceResultDTO result) {
        List<AlertRule> rules = getCloudTriggerRules();
        for (AlertRule rule : rules) {
            if (matchesRule(rule, result)) {
                return true;
            }
        }
        return false;
    }

    private boolean matchesRule(AlertRule rule, InferenceResultDTO result) {
        if (rule.getDeviceId() != null && !rule.getDeviceId().equals(result.getDeviceId())) return false;
        if (rule.getSource() != null && !rule.getSource().equals(result.getSource())) return false;
        if (rule.getModelName() != null && !rule.getModelName().equals(result.getModelName())) return false;
        if (rule.getClassName() != null) {
            if (result.getResultJson() == null) return false;
            Object detections = result.getResultJson().get("detections");
            if (detections instanceof List<?> detList) {
                boolean found = detList.stream().anyMatch(d ->
                        d instanceof java.util.Map<?, ?> m && rule.getClassName().equals(m.get("class_name")));
                if (!found) return false;
            }
            Object segments = result.getResultJson().get("segments");
            if (segments instanceof java.util.Map<?, ?> segMap) {
                if (!segMap.containsKey(rule.getClassName())) return false;
            }
        }
        return true;
    }

    private boolean matchesCondition(AlertRule rule, InferenceResultDTO result) {
        Float threshold = rule.getThresholdValue();
        if (threshold == null) return true;

        String condType = rule.getConditionType();
        if ("area_threshold".equals(condType) && result.getResultJson() != null) {
            Object segments = result.getResultJson().get("segments");
            if (segments instanceof java.util.Map<?, ?> segMap && rule.getClassName() != null) {
                Object segInfo = segMap.get(rule.getClassName());
                if (segInfo instanceof java.util.Map<?, ?> m && m.get("area") instanceof Number area) {
                    return area.floatValue() >= threshold;
                }
            }
        } else if ("count_threshold".equals(condType)) {
            return result.getDetectionCount() != null && result.getDetectionCount() >= threshold.intValue();
        } else if ("confidence_threshold".equals(condType) && result.getResultJson() != null) {
            Object detections = result.getResultJson().get("detections");
            if (detections instanceof List<?> detList) {
                return detList.stream().anyMatch(d ->
                        d instanceof java.util.Map<?, ?> m &&
                                m.get("confidence") instanceof Number conf &&
                                conf.floatValue() >= threshold);
            }
        }
        return true;
    }

    private void applyRequest(AlertRule rule, AlertRuleRequest req) {
        if (req.getName() != null) rule.setName(req.getName());
        rule.setDeviceId(req.getDeviceId());
        rule.setModelName(req.getModelName());
        rule.setSource(req.getSource());
        rule.setClassName(req.getClassName());
        if (req.getConditionType() != null) rule.setConditionType(req.getConditionType());
        rule.setThresholdValue(req.getThresholdValue());
        if (req.getAlertLevel() != null) rule.setAlertLevel(req.getAlertLevel());
        rule.setAlertMessage(req.getAlertMessage());
        rule.setTriggerCloudInfer(req.getTriggerCloudInfer() != null ? req.getTriggerCloudInfer() : false);
        rule.setEnabled(req.getEnabled() != null ? req.getEnabled() : true);
    }

    private int alertPriority(String level) {
        return switch (level) {
            case "critical" -> 3;
            case "warning" -> 2;
            case "info" -> 1;
            default -> 0;
        };
    }
}
