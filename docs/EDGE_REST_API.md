# Edge Device REST API Documentation

## Overview

This document describes the RESTful API for edge-cloud communication in the edge_infer_cloud platform. Edge devices use these HTTP endpoints to communicate with the cloud platform, replacing the MQTT approach.

**Base URL**: `http://your-cloud-server:8081/api/v1/edge`

---

## API Endpoints

### 1. Device Registration

Register a new edge device with the cloud platform.

**Endpoint**: `POST /api/v1/edge/register`

**Request Body**:
```json
{
  "device_id": "EDGE_DEVICE_001",
  "device_name": "Edge Device 1",
  "device_type": "EDGE_BOX",
  "ip": "192.168.1.100",
  "mac": "00:11:22:33:44:55",
  "os_version": "Ubuntu 22.04",
  "agent_version": "1.0.0",
  "gpu_model": "NVIDIA RTX 3060",
  "gpu_memory": 12288,
  "gpu_memory_usage": 4500,
  "cpu_usage": 45.5,
  "gpu_usage": 60.0,
  "memory_usage": 55.0,
  "disk_usage": 40.0,
  "temperature": 65.0,
  "current_model_id": "M001",
  "current_model_version": "v1.0.0",
  "inference_fps": 25.0,
  "uptime_seconds": 3600,
  "timestamp": "2026-01-27T10:00:00"
}
```

**Response**:
```json
{
  "status": "SUCCESS",
  "message": "Device registered successfully",
  "device_id": "EDGE_DEVICE_001",
  "registered_at": "2026-01-27T10:00:00"
}
```

---

### 2. Device Heartbeat

Send periodic heartbeat to update device status and receive commands from cloud.

**Endpoint**: `POST /api/v1/edge/heartbeat`

**Request Body**: Same as registration

**Response**:
```json
{
  "status": "SUCCESS",
  "message": "Heartbeat received",
  "serverTime": 1706342400000,
  "commands": [
    {
      "commandType": "OTA_UPDATE",
      "commandId": "CMD_001",
      "taskId": "OTA_001",
      "params": "{\"model_id\": \"M002\", \"download_url\": \"http://...\"}",
      "priority": 5,
      "expireAt": 1706346000000
    }
  ]
}
```

**Recommended Frequency**: Every 5 seconds

---

### 3. Get Pending Commands

Poll for pending commands from the cloud (alternative to receiving in heartbeat response).

**Endpoint**: `GET /api/v1/edge/commands`

**Query Parameters**:
- `device_id` (required): Device ID
- `last_command_id` (optional): Last received command ID for pagination

**Example**:
```bash
GET /api/v1/edge/commands?device_id=EDGE_DEVICE_001&last_command_id=CMD_001
```

**Response**:
```json
{
  "status": "SUCCESS",
  "commands": [...],
  "has_more": false
}
```

**Recommended Frequency**: Every 2 seconds

---

### 4. Acknowledge Command

Confirm that a command has been received and will be executed.

**Endpoint**: `POST /api/v1/edge/commands/{command_id}/ack`

**Request Body**:
```json
{
  "device_id": "EDGE_DEVICE_001"
}
```

**Response**:
```json
{
  "status": "SUCCESS",
  "message": "Command acknowledged"
}
```

---

### 5. Report OTA Status

Report OTA upgrade progress to the cloud.

**Endpoint**: `POST /api/v1/edge/ota/status`

**Request Body**:
```json
{
  "task_id": "OTA_001",
  "device_id": "EDGE_DEVICE_001",
  "status": "DOWNLOADING",
  "progress": 45,
  "error": null,
  "timestamp": "2026-01-27T10:05:00"
}
```

**Status Values**:
- `PENDING`: Waiting to start
- `DOWNLOADING`: Downloading model
- `VERIFYING`: Verifying checksum
- `APPLYING`: Applying update
- `COMPLETED`: Successfully completed
- `FAILED`: Failed with error

**Response**:
```json
{
  "status": "SUCCESS",
  "message": "OTA status received"
}
```

---

### 6. Report Inference Result

Report inference detection results to the cloud.

**Endpoint**: `POST /api/v1/edge/inference/result`

**Request Body**:
```json
{
  "device_id": "EDGE_DEVICE_001",
  "model_id": "M001",
  "model_version": "v1.0.0",
  "inference_time_ms": 35,
  "frame_count": 1,
  "frame_width": 1920,
  "frame_height": 1080,
  "detections": [
    {
      "class_id": 0,
      "class_name": "person",
      "confidence": 0.95,
      "bbox": [100, 200, 50, 100]
    }
  ],
  "timestamp": "2026-01-27T10:00:05"
}
```

**Response**:
```json
{
  "status": "SUCCESS",
  "message": "Inference result received"
}
```

**Recommended Frequency**: Every 1-2 seconds (only when detections exist)

---

### 7. Get Model Download Info

Get download URL for a model file.

**Endpoint**: `GET /api/v1/edge/models/{model_id}/download`

**Response**:
```json
{
  "model_id": "M001",
  "download_url": "/api/v1/models/M001/file",
  "expires_at": 1706346000000
}
```

---

## Command Types

### OTA_UPDATE

Trigger OTA firmware/model update.

**Command Structure**:
```json
{
  "commandType": "OTA_UPDATE",
  "commandId": "CMD_001",
  "taskId": "OTA_001",
  "params": {
    "model_id": "M002",
    "download_url": "http://cloud/api/v1/models/M002/file",
    "model_version": "v2.0.0"
  }
}
```

### CONFIG_UPDATE

Update device configuration.

**Command Structure**:
```json
{
  "commandType": "CONFIG_UPDATE",
  "commandId": "CMD_002",
  "params": {
    "inference_fps": 30,
    "max_detections": 100
  }
}
```

### RESTART

Restart the edge device agent.

**Command Structure**:
```json
{
  "commandType": "RESTART",
  "commandId": "CMD_003",
  "params": {}
}
```

### STOP

Stop the edge device (emergency).

**Command Structure**:
```json
{
  "commandType": "STOP",
  "commandId": "CMD_004",
  "params": {}
}
```

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK`: Success
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

**Error Response Format**:
```json
{
  "status": "ERROR",
  "message": "Error description"
}
```

---

## WebSocket Integration

For real-time updates from cloud to edge device, use WebSocket:

**Connect to**: `ws://your-cloud-server:8081/ws`

**Subscribe to**:
- `/topic/device/{device_id}/commands` - Receive commands
- `/topic/device/{device_id}/config` - Receive config updates

**STOMP Example**:
```javascript
const client = Stomp.over(ws);
client.connect({}, () => {
  client.subscribe('/topic/device/EDGE_DEVICE_001/commands', (msg) => {
    const command = JSON.parse(msg.body);
    // Handle command
  });
});
```

---

## Python Client Example

See [`scripts/test/rest_edge_client.py`](../scripts/test/rest_edge_client.py) for a complete Python implementation.

Basic usage:
```python
from rest_edge_client import RestEdgeClient

client = RestEdgeClient(
    device_id="EDGE_DEVICE_001",
    api_base="http://localhost:8081/api/v1/edge"
)

# Register and start
client.start()  # Runs heartbeat, command poll, and inference loops
```

---

## Authentication

For production use, add API key authentication:

```python
headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
}
response = requests.post(url, json=payload, headers=headers)
```

---

## Comparison with MQTT

| Feature | RESTful + WebSocket | MQTT |
|---------|---------------------|------|
| Firewall/NAT friendly | Yes (HTTP 80/443) | No (1883) |
| Bidirectional | Yes (WebSocket) | Yes |
| Debugging | Easy (curl/browser) | Hard (need MQTT client) |
| Scalability | Good | Excellent |
| Network overhead | Medium | Low |
| Complexity | Low | Medium |

**Recommendation**: Use RESTful + WebSocket for most edge-cloud scenarios, especially when:
- Devices may be behind NAT/firewalls
- Cross-network (WAN) deployment
- Debugging simplicity is important
- Existing HTTP infrastructure

---

## Testing

### Test Device Registration
```bash
curl -X POST http://localhost:8081/api/v1/edge/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "TEST_DEVICE_001",
    "device_name": "Test Device",
    "device_type": "EDGE_BOX",
    "ip": "192.168.1.100",
    "mac": "00:11:22:33:44:55",
    "os_version": "Ubuntu 22.04",
    "agent_version": "1.0.0",
    "cpu_usage": 30.0,
    "gpu_usage": 50.0,
    "memory_usage": 45.0,
    "timestamp": "2026-01-27T10:00:00"
  }'
```

### Run Python Test Client
```bash
cd scripts/test
pip install requests
python rest_edge_client.py
```

---

## Next Steps

1. **Add Authentication**: Implement API key or JWT authentication
2. **Add HTTPS**: Use TLS for secure communication
3. **Add Retry Logic**: Handle network failures gracefully
4. **Add Compression**: Compress large payloads (e.g., inference results)
5. **Add Rate Limiting**: Prevent API abuse
