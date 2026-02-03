package com.edge.cloud.controller;

import com.edge.cloud.dto.DeviceHeartbeatRequest;
import com.edge.cloud.dto.DeviceHeartbeatResponse;
import com.edge.cloud.dto.InferenceResultRequest;
import com.edge.cloud.dto.OtaStatusReportRequest;
import com.edge.cloud.service.DeviceCommunicationService;
import com.edge.cloud.service.WebSocketMessageService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * 边缘设备通信控制器 (RESTful API)
 * 边缘设备通过HTTP POST向云端发送数据
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/edge")
@RequiredArgsConstructor
public class EdgeDeviceController {

    private final DeviceCommunicationService deviceCommunicationService;
    private final WebSocketMessageService webSocketMessageService;

    /**
     * 设备心跳接口
     * 边缘设备定期调用此接口上报状态
     *
     * POST /api/v1/edge/heartbeat
     */
    @PostMapping("/heartbeat")
    public ResponseEntity<DeviceHeartbeatResponse> heartbeat(@RequestBody DeviceHeartbeatRequest request) {
        log.info("收到设备心跳: deviceId={}, cpuUsage={}%, gpuUsage={}%, status={}",
                request.getDeviceId(),
                request.getCpuUsage(),
                request.getGpuUsage(),
                request.getDeviceType());

        try {
            // 处理心跳，更新设备状态
            DeviceHeartbeatResponse response = deviceCommunicationService.processHeartbeat(request);

            // 通过WebSocket推送设备状态更新到前端
            Map<String, Object> statusData = new java.util.HashMap<>();
            statusData.put("device_id", request.getDeviceId());
            statusData.put("cpu_usage", request.getCpuUsage());
            statusData.put("gpu_usage", request.getGpuUsage());
            statusData.put("memory_usage", request.getMemoryUsage());
            statusData.put("temperature", request.getTemperature());
            statusData.put("inference_fps", request.getInferenceFps());
            statusData.put("timestamp", System.currentTimeMillis());
            webSocketMessageService.broadcast("/topic/device/" + request.getDeviceId() + "/status", statusData);

            return ResponseEntity.ok(response);

        } catch (Exception e) {
            log.error("处理心跳失败: deviceId={}, error={}", request.getDeviceId(), e.getMessage(), e);
            return ResponseEntity.ok(DeviceHeartbeatResponse.builder()
                    .status("ERROR")
                    .message(e.getMessage())
                    .serverTime(System.currentTimeMillis())
                    .build());
        }
    }

    /**
     * 设备注册接口
     * 新设备首次上线时调用
     *
     * POST /api/v1/edge/register
     */
    @PostMapping("/register")
    public ResponseEntity<Map<String, Object>> register(@RequestBody DeviceHeartbeatRequest request) {
        log.info("设备注册请求: deviceId={}, deviceName={}, deviceType={}",
                request.getDeviceId(), request.getDeviceName(), request.getDeviceType());

        try {
            Map<String, Object> result = deviceCommunicationService.registerDevice(request);

            // 通知前端有新设备注册
            webSocketMessageService.broadcast("/topic/devices/registered", result);

            return ResponseEntity.ok(result);

        } catch (Exception e) {
            log.error("设备注册失败: deviceId={}, error={}", request.getDeviceId(), e.getMessage(), e);
            return ResponseEntity.badRequest().body(Map.of(
                    "status", "ERROR",
                    "message", e.getMessage()
            ));
        }
    }

    /**
     * OTA升级状态上报
     * 边缘设备在OTA过程中上报进度
     *
     * POST /api/v1/edge/ota/status
     */
    @PostMapping("/ota/status")
    public ResponseEntity<Map<String, Object>> reportOtaStatus(@RequestBody OtaStatusReportRequest request) {
        log.info("收到OTA状态上报: taskId={}, deviceId={}, status={}, progress={}%",
                request.getTaskId(), request.getDeviceId(), request.getStatus(), request.getProgress());

        try {
            Map<String, Object> result = deviceCommunicationService.processOtaStatus(request);

            // 通过WebSocket推送OTA进度到前端
            webSocketMessageService.sendOtaTaskProgress(request.getTaskId(), Map.of(
                    "device_id", request.getDeviceId(),
                    "status", request.getStatus(),
                    "progress", request.getProgress(),
                    "error", request.getError(),
                    "timestamp", System.currentTimeMillis()
            ));

            return ResponseEntity.ok(result);

        } catch (Exception e) {
            log.error("处理OTA状态失败: taskId={}, error={}", request.getTaskId(), e.getMessage(), e);
            return ResponseEntity.badRequest().body(Map.of(
                    "status", "ERROR",
                    "message", e.getMessage()
            ));
        }
    }

    /**
     * 推理结果上报
     * 边缘设备上报推理检测结果
     *
     * POST /api/v1/edge/inference/result
     */
    @PostMapping("/inference/result")
    public ResponseEntity<Map<String, Object>> reportInferenceResult(@RequestBody InferenceResultRequest request) {
        log.debug("收到推理结果: deviceId={}, modelId={}, detections={}",
                request.getDeviceId(), request.getModelId(), request.getDetections().size());

        try {
            Map<String, Object> result = deviceCommunicationService.processInferenceResult(request);
            return ResponseEntity.ok(result);

        } catch (Exception e) {
            log.error("处理推理结果失败: deviceId={}, error={}", request.getDeviceId(), e.getMessage(), e);
            return ResponseEntity.badRequest().body(Map.of(
                    "status", "ERROR",
                    "message", e.getMessage()
            ));
        }
    }

    /**
     * 获取待执行命令
     * 边缘设备轮询此接口获取云端下发的命令
     *
     * GET /api/v1/edge/commands?device_id=xxx
     */
    @GetMapping("/commands")
    public ResponseEntity<Map<String, Object>> getCommands(
            @RequestParam("device_id") String deviceId,
            @RequestParam(value = "last_command_id", required = false) String lastCommandId) {

        try {
            Map<String, Object> result = deviceCommunicationService.getPendingCommands(deviceId, lastCommandId);
            return ResponseEntity.ok(result);

        } catch (Exception e) {
            log.error("获取命令失败: deviceId={}, error={}", deviceId, e.getMessage(), e);
            return ResponseEntity.ok(Map.of(
                    "status", "ERROR",
                    "message", e.getMessage(),
                    "commands", new Object[]{}
            ));
        }
    }

    /**
     * 下载模型文件
     * 边缘设备从此接口下载更新的模型
     *
     * GET /api/v1/edge/models/{model_id}/download
     */
    @GetMapping("/models/{model_id}/download")
    public ResponseEntity<Map<String, Object>> getModelDownloadInfo(@PathVariable("model_id") String modelId) {
        try {
            Map<String, Object> result = deviceCommunicationService.getModelDownloadInfo(modelId);
            return ResponseEntity.ok(result);

        } catch (Exception e) {
            log.error("获取模型下载信息失败: modelId={}, error={}", modelId, e.getMessage(), e);
            return ResponseEntity.notFound().build();
        }
    }

    /**
     * 命令执行确认
     * 边缘设备收到命令后确认，云端标记为已接收
     *
     * POST /api/v1/edge/commands/{command_id}/ack
     */
    @PostMapping("/commands/{command_id}/ack")
    public ResponseEntity<Map<String, Object>> acknowledgeCommand(
            @PathVariable("command_id") String commandId,
            @RequestBody Map<String, Object> payload) {

        try {
            String deviceId = (String) payload.get("device_id");
            deviceCommunicationService.acknowledgeCommand(deviceId, commandId);

            return ResponseEntity.ok(Map.of(
                    "status", "SUCCESS",
                    "message", "Command acknowledged"
            ));

        } catch (Exception e) {
            log.error("确认命令失败: commandId={}, error={}", commandId, e.getMessage(), e);
            return ResponseEntity.badRequest().body(Map.of(
                    "status", "ERROR",
                    "message", e.getMessage()
            ));
        }
    }
}
