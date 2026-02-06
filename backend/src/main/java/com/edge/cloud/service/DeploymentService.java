package com.edge.cloud.service;

import com.edge.cloud.dto.ModelDeploymentDTO;
import com.edge.cloud.entity.Device;
import com.edge.cloud.entity.Model;
import com.edge.cloud.entity.ModelDeployment;
import com.edge.cloud.repository.DeviceRepository;
import com.edge.cloud.repository.ModelDeploymentRepository;
import com.edge.cloud.repository.ModelRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 部署记录服务
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DeploymentService {

    private final ModelDeploymentRepository deploymentRepository;
    private final ModelRepository modelRepository;
    private final DeviceRepository deviceRepository;

    /**
     * 创建部署记录
     */
    @Transactional
    public ModelDeploymentDTO createDeployment(String modelId, String deviceId, String deploymentType,
                                               String deployedBy, String otaTaskId) {
        Model model = modelRepository.findById(modelId)
                .orElseThrow(() -> new RuntimeException("模型不存在: " + modelId));
        Device device = deviceRepository.findById(deviceId)
                .orElseThrow(() -> new RuntimeException("设备不存在: " + deviceId));

        ModelDeployment deployment = new ModelDeployment();
        deployment.setDeploymentId(generateDeploymentId());
        deployment.setModelId(modelId);
        deployment.setModelName(model.getModelName());
        deployment.setDeviceId(deviceId);
        deployment.setDeviceName(device.getDeviceName());
        deployment.setDeploymentType(deploymentType);
        deployment.setStatus(ModelDeployment.DeploymentStatus.DEPLOYING.name());
        deployment.setPreviousModelId(device.getCurrentModelId());
        deployment.setPreviousModelName(getPreviousModelName(device.getCurrentModelId()));
        deployment.setOtaTaskId(otaTaskId);
        deployment.setDeployedBy(deployedBy);
        deployment.setDeployedAt(LocalDateTime.now());

        deployment = deploymentRepository.save(deployment);
        log.info("创建部署记录: deploymentId={}, model={}, device={}",
                deployment.getDeploymentId(), modelId, deviceId);

        return ModelDeploymentDTO.fromEntity(deployment);
    }

    /**
     * 更新部署状态为成功
     */
    @Transactional
    public void markDeploymentSuccess(String deploymentId, Float inferenceFps, Integer memoryUsage,
                                       Float gpuUtilization) {
        ModelDeployment deployment = deploymentRepository.findById(deploymentId)
                .orElseThrow(() -> new RuntimeException("部署记录不存在: " + deploymentId));

        deployment.setStatus(ModelDeployment.DeploymentStatus.SUCCESS.name());
        deployment.setCompletedAt(LocalDateTime.now());
        deployment.setInferenceFps(inferenceFps);
        deployment.setMemoryUsageMb(memoryUsage);
        deployment.setGpuUtilization(gpuUtilization);

        deploymentRepository.save(deployment);
        log.info("部署成功: deploymentId={}", deploymentId);
    }

    /**
     * 更新部署状态为失败
     */
    @Transactional
    public void markDeploymentFailed(String deploymentId, String errorMessage) {
        ModelDeployment deployment = deploymentRepository.findById(deploymentId)
                .orElseThrow(() -> new RuntimeException("部署记录不存在: " + deploymentId));

        deployment.setStatus(ModelDeployment.DeploymentStatus.FAILED.name());
        deployment.setCompletedAt(LocalDateTime.now());
        deployment.setErrorMessage(errorMessage);

        deploymentRepository.save(deployment);
        log.error("部署失败: deploymentId={}, error={}", deploymentId, errorMessage);
    }

    /**
     * 标记部署已回滚
     */
    @Transactional
    public void markDeploymentRolledBack(String deploymentId) {
        ModelDeployment deployment = deploymentRepository.findById(deploymentId)
                .orElseThrow(() -> new RuntimeException("部署记录不存在: " + deploymentId));

        deployment.setStatus(ModelDeployment.DeploymentStatus.ROLLED_BACK.name());
        deployment.setRollbackAt(LocalDateTime.now());

        deploymentRepository.save(deployment);
        log.info("部署已回滚: deploymentId={}", deploymentId);
    }

    /**
     * 获取部署记录详情
     */
    public ModelDeploymentDTO getDeployment(String deploymentId) {
        ModelDeployment deployment = deploymentRepository.findById(deploymentId)
                .orElseThrow(() -> new RuntimeException("部署记录不存在: " + deploymentId));
        return ModelDeploymentDTO.fromEntity(deployment);
    }

    /**
     * 分页查询部署记录（支持多条件过滤）
     */
    public Map<String, Object> listDeployments(String modelId, String deviceId, String status,
                                                String deploymentType, LocalDateTime startTime,
                                                LocalDateTime endTime, int page, int pageSize) {
        Pageable pageable = PageRequest.of(page - 1, pageSize, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<ModelDeployment> result = deploymentRepository.findByConditions(
                modelId, deviceId, status, deploymentType, startTime, endTime, pageable);

        Map<String, Object> response = new HashMap<>();
        response.put("items", result.getContent().stream()
                .map(ModelDeploymentDTO::fromEntity)
                .collect(Collectors.toList()));
        response.put("total", result.getTotalElements());
        response.put("page", page);
        response.put("pageSize", pageSize);

        return response;
    }

    /**
     * 获取模型的部署历史
     */
    public List<ModelDeploymentDTO> getModelDeploymentHistory(String modelId) {
        List<ModelDeployment> deployments = deploymentRepository.findByModelIdOrderByCreatedAtDesc(modelId);
        return deployments.stream()
                .map(ModelDeploymentDTO::fromEntity)
                .collect(Collectors.toList());
    }

    /**
     * 获取设备的部署历史
     */
    public Map<String, Object> getDeviceDeploymentHistory(String deviceId, int page, int pageSize) {
        Pageable pageable = PageRequest.of(page - 1, pageSize, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<ModelDeployment> result = deploymentRepository.findByDeviceIdOrderByCreatedAtDesc(deviceId, pageable);

        Map<String, Object> response = new HashMap<>();
        response.put("items", result.getContent().stream()
                .map(ModelDeploymentDTO::fromEntity)
                .collect(Collectors.toList()));
        response.put("total", result.getTotalElements());
        response.put("page", page);
        response.put("pageSize", pageSize);

        return response;
    }

    /**
     * 获取设备的当前部署信息
     */
    public ModelDeploymentDTO getDeviceCurrentDeployment(String deviceId) {
        ModelDeployment deployment = deploymentRepository.findFirstByDeviceIdOrderByCreatedAtDesc(deviceId);
        return deployment != null ? ModelDeploymentDTO.fromEntity(deployment) : null;
    }

    /**
     * 获取最近部署记录
     */
    public Map<String, Object> getRecentDeployments(int page, int pageSize) {
        Pageable pageable = PageRequest.of(page - 1, pageSize, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<ModelDeployment> result = deploymentRepository.findRecentDeployments(pageable);

        Map<String, Object> response = new HashMap<>();
        response.put("items", result.getContent().stream()
                .map(ModelDeploymentDTO::fromEntity)
                .collect(Collectors.toList()));
        response.put("total", result.getTotalElements());
        response.put("page", page);
        response.put("pageSize", pageSize);

        return response;
    }

    /**
     * 获取部署统计信息
     */
    public Map<String, Object> getDeploymentStats(String modelId) {
        long totalCount = deploymentRepository.countByModelId(modelId);
        long successCount = deploymentRepository.countSuccessfulByModelId(modelId);

        Map<String, Object> stats = new HashMap<>();
        stats.put("modelId", modelId);
        stats.put("totalDeployments", totalCount);
        stats.put("successfulDeployments", successCount);
        stats.put("failedDeployments", totalCount - successCount);
        stats.put("successRate", totalCount > 0 ? (double) successCount / totalCount : 0);

        return stats;
    }

    /**
     * 获取模型在哪些设备上正在运行
     */
    public List<Map<String, Object>> getModelActiveDevices(String modelId) {
        List<ModelDeployment> deployments = deploymentRepository.findByModelIdAndStatus(
                modelId, ModelDeployment.DeploymentStatus.SUCCESS.name());

        return deployments.stream()
                .filter(d -> d.getRollbackAt() == null) // 未被回滚
                .map(d -> {
                    Map<String, Object> info = new HashMap<>();
                    info.put("deviceId", d.getDeviceId());
                    info.put("deviceName", d.getDeviceName());
                    info.put("deployedAt", d.getDeployedAt());
                    info.put("inferenceFps", d.getInferenceFps());
                    return info;
                })
                .collect(Collectors.toList());
    }

    /**
     * 生成部署ID
     */
    private String generateDeploymentId() {
        return "D" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"))
                + String.format("%04d", new Random().nextInt(10000));
    }

    /**
     * 删除部署记录
     */
    @Transactional
    public void deleteDeployment(String deploymentId) {
        ModelDeployment deployment = deploymentRepository.findById(deploymentId)
                .orElseThrow(() -> new RuntimeException("部署记录不存在: " + deploymentId));

        // 允许删除任何状态的部署记录
        deploymentRepository.deleteById(deploymentId);
        log.info("删除部署记录: deploymentId={}, status={}", deploymentId, deployment.getStatus());
    }

    /**
     * 批量删除部署记录
     */
    @Transactional
    public void deleteDeployments(List<String> deploymentIds) {
        for (String deploymentId : deploymentIds) {
            try {
                deleteDeployment(deploymentId);
            } catch (Exception e) {
                log.warn("删除部署记录失败: deploymentId={}, error={}", deploymentId, e.getMessage());
            }
        }
    }

    /**
     * 清空所有已完成/失败/已回滚的部署记录
     */
    @Transactional
    public Map<String, Object> clearCompletedDeployments() {
        // 查询所有非DEPLOYING状态的记录
        List<ModelDeployment> allDeployments = deploymentRepository.findAll();
        int total = allDeployments.size();
        int deleted = 0;
        int skipped = 0;

        for (ModelDeployment deployment : allDeployments) {
            String status = deployment.getStatus();
            if (!ModelDeployment.DeploymentStatus.DEPLOYING.name().equals(status)) {
                try {
                    deploymentRepository.deleteById(deployment.getDeploymentId());
                    deleted++;
                } catch (Exception e) {
                    log.warn("删除部署记录失败: deploymentId={}, error={}",
                            deployment.getDeploymentId(), e.getMessage());
                }
            } else {
                skipped++;
            }
        }

        log.info("清空部署记录完成: 总数={}, 删除={}, 跳过={}", total, deleted, skipped);

        Map<String, Object> result = new HashMap<>();
        result.put("total", total);
        result.put("deleted", deleted);
        result.put("skipped", skipped);
        return result;
    }

    /**
     * 获取上一个模型的名称
     */
    private String getPreviousModelName(String modelId) {
        if (modelId == null) return null;
        return modelRepository.findById(modelId)
                .map(Model::getModelName)
                .orElse(null);
    }
}
