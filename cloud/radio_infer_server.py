#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
C-RADIOv4 云端推理服务

通过 MQTT 接收边缘设备上传的关键帧，执行 C-RADIOv4 开放词汇分割，
并将分割结果回传给边缘设备。

MQTT Topic 设计:
  订阅: device/+/cloud/frame     (边缘设备上传的关键帧)
  发布: device/{device_id}/cloud/result  (分割结果)

消息格式:
  请求 (frame):
    {
      "device_id": "jetson-001",
      "frame_id": 12345,
      "timestamp": "2026-04-01T10:00:00",
      "image": "<base64 JPEG>",
      "classes": ["black_water", "green_water"]  // 可选，默认全部分割
    }

  响应 (result):
    {
      "device_id": "jetson-001",
      "frame_id": 12345,
      "timestamp": "2026-04-01T10:00:00.123",
      "segments": {
        "black_water": {"area": 0.05, "score": 0.8, "bbox": [x1,y1,x2,y2]},
        "green_water": {"area": 0.12, "score": 0.75, "bbox": [x1,y1,x2,y2]}
      },
      "alerts": [
        {"class_name": "black_water", "level": "critical", "message": "黑水面积5%"}
      ],
      "inference_time_ms": 150.5
    }

环境变量:
  MQTT_BROKER_URL   - MQTT broker 地址 (默认 tcp://emqx:1883)
  MQTT_USERNAME     - MQTT 用户名 (可选)
  MQTT_PASSWORD     - MQTT 密码 (可选)
  MODEL_PATH        - C-RADIOv4 权重路径 (默认 checkpoints/model.safetensors)
  CONFIG_PATH       - 水利巡检配置文件路径
  DEVICE            - 推理设备 (默认 cuda)
  INPUT_SIZE        - 输入尺寸 (默认 896)
  PREFER_ONLINE     - 是否优先在线加载 (默认 true，即官方库优先)

作者: 空中智能体团队
日期: 2026-04-01
"""

import os
import sys
import json
import base64
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "models" / "water_inspection"))

import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("radio_infer_server")


class RadioInferServer:
    """C-RADIOv4 云端推理服务"""

    def __init__(self):
        # 从环境变量读取配置
        self.mqtt_broker = os.getenv("MQTT_BROKER_URL", "tcp://emqx:1883")
        self.mqtt_username = os.getenv("MQTT_USERNAME", "")
        self.mqtt_password = os.getenv("MQTT_PASSWORD", "")

        # 模型路径 (本地官方代码 + checkpoint + SigLIP2)
        self.checkpoint_path = os.getenv(
            "RADIO_CHECKPOINT_PATH",
            "/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar",
        )
        self.radio_code_dir = os.getenv(
            "RADIO_CODE_DIR",
            "/app/models/NVlabs_RADIO",
        )
        self.siglip2_dir = os.getenv(
            "SIGLIP2_DIR",
            "/app/models/siglip2-giant-opt-patch16-384",
        )
        self.config_path = os.getenv(
            "CONFIG_PATH",
            str(PROJECT_ROOT / "models" / "water_inspection" / "configs" / "water_inspection.yaml"),
        )
        self.device = os.getenv("DEVICE", "cuda")
        self.input_size = int(os.getenv("INPUT_SIZE", "896"))

        # 报警阈值
        self.alert_min_area = float(os.getenv("ALERT_MIN_AREA", "0.01"))
        self.sim_floor = float(os.getenv("SIM_FLOOR", "0.0"))
        self.class_gate = float(os.getenv("CLASS_GATE", "0.0"))

        # 分割器 (延迟加载)
        self._segmentor = None
        self._classes_config = None

        # MQTT 客户端
        self._client: Optional[mqtt.Client] = None

        # 统计
        self._stats = {
            "total_frames": 0,
            "total_inference_ms": 0.0,
            "errors": 0,
        }

    # ── 模型加载 ──

    def _load_model(self):
        """加载 C-RADIOv4 分割器和配置"""
        import yaml

        logger.info("加载配置文件: %s", self.config_path)
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # 获取分割类别配置
        radio_config = config.get("cloud", {}).get("radio", {})
        self._classes_config = radio_config.get("classes", {})

        if not self._classes_config:
            # fallback
            self._classes_config = config.get("dinov3_sam3", {}).get("classes", {})

        logger.info("分割类别: %s", list(self._classes_config.keys()))

        # 推理参数
        infer_config = radio_config.get("inference", {})
        threshold = float(infer_config.get("threshold", 0.3))
        min_area = float(infer_config.get("min_area", 0.01))

        # 加载分割器
        from models.open_vocab.radio_segmentor import CRadioV4Segmentor

        logger.info("加载 C-RADIOv4 分割器...")
        self._segmentor = CRadioV4Segmentor(
            checkpoint_path=self.checkpoint_path,
            radio_code_dir=self.radio_code_dir,
            siglip2_dir=self.siglip2_dir,
            device=self.device,
            input_size=self.input_size,
        )
        self._threshold = threshold
        self._min_area = min_area

        logger.info("模型加载完成")

    # ── MQTT ──

    def _setup_mqtt(self):
        """配置 MQTT 客户端"""
        client_id = f"radio_infer_{os.getenv('HOSTNAME', 'cloud')}"
        self._client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

        if self.mqtt_username:
            self._client.username_pw_set(self.mqtt_username, self.mqtt_password)

        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

        # 解析 broker 地址
        broker_str = self.mqtt_broker.replace("tcp://", "").replace("mqtt://", "")
        host, port = broker_str.split(":") if ":" in broker_str else (broker_str, 1883)

        logger.info("连接 MQTT broker: %s:%s", host, port)
        self._client.connect(host, int(port), keepalive=60)
        self._client.loop_start()

    def _on_connect(self, client, userdata, flags, rc):
        """MQTT 连接回调"""
        if rc == 0:
            topic = "device/+/cloud/frame"
            client.subscribe(topic, qos=1)
            logger.info("已订阅: %s", topic)
        else:
            logger.error("MQTT 连接失败: rc=%d", rc)

    def _on_message(self, client, userdata, msg):
        """MQTT 消息回调 — 处理关键帧"""
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            self._handle_frame(payload)
        except Exception as e:
            logger.error("处理消息失败: %s", e, exc_info=True)
            self._stats["errors"] += 1

    # ── 推理 ──

    def _handle_frame(self, payload: dict):
        """处理一帧图像"""
        device_id = payload.get("device_id", "unknown")
        frame_id = payload.get("frame_id", 0)
        image_b64 = payload.get("image", "")
        requested_classes = payload.get("classes")

        logger.info("收到帧: device=%s, frame_id=%s", device_id, frame_id)

        # 解码图像
        image_data = base64.b64decode(image_b64)
        image_array = np.frombuffer(image_data, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if image is None:
            logger.warning("图像解码失败: device=%s", device_id)
            return

        # 分割
        t0 = time.time()

        classes_config = self._classes_config
        if requested_classes:
            classes_config = {
                k: v for k, v in classes_config.items()
                if k in requested_classes
            }

        results = self._segmentor.segment(
            image, classes_config,
            threshold=self._threshold,
            min_area=self._min_area,
            sim_floor=self.sim_floor,
            class_gate=self.class_gate,
        )

        inference_ms = (time.time() - t0) * 1000

        # 更新统计
        self._stats["total_frames"] += 1
        self._stats["total_inference_ms"] += inference_ms

        # 构造结果
        segments = {}
        for name, seg in results.items():
            # 计算 bbox
            ys, xs = np.where(seg.mask)
            if len(ys) > 0:
                x1, y1 = int(xs.min()), int(ys.min())
                x2, y2 = int(xs.max()), int(ys.max())
                bbox = [x1, y1, x2, y2]
            else:
                bbox = [0, 0, 0, 0]

            segments[name] = {
                "area": round(seg.area_ratio, 4),
                "score": round(seg.score, 4),
                "bbox": bbox,
                "class_name_cn": seg.class_name_cn,
            }

        # 生成报警
        alerts = self._generate_alerts(segments)

        result_payload = {
            "device_id": device_id,
            "frame_id": frame_id,
            "timestamp": datetime.now().isoformat(),
            "segments": segments,
            "alerts": alerts,
            "inference_time_ms": round(inference_ms, 1),
        }

        # 发布结果
        result_topic = f"device/{device_id}/cloud/result"
        self._client.publish(
            result_topic,
            json.dumps(result_payload, ensure_ascii=False),
            qos=1,
        )

        logger.info(
            "完成: device=%s, segments=%d, alerts=%d, %.1fms",
            device_id, len(segments), len(alerts), inference_ms,
        )

    def _generate_alerts(self, segments: dict) -> list:
        """根据分割结果生成报警"""
        alerts = []

        alert_classes = {
            "black_water": "黑水污染",
            "brown_water": "褐色水体",
            "yellow_water": "黄色水体",
            "green_water": "藻类爆发",
            "red_water": "化学污染",
            "milky_water": "水体浑浊",
            "foam_water": "水面泡沫",
            "dam_seepage": "坝体渗水",
        }

        for class_name, info in segments.items():
            if info["area"] >= self.alert_min_area:
                desc = alert_classes.get(class_name, class_name)
                alerts.append({
                    "class_name": class_name,
                    "class_name_cn": info.get("class_name_cn", class_name),
                    "level": "critical",
                    "message": f"{desc}，面积占比 {info['area']:.1%}",
                    "area": info["area"],
                })

        return alerts

    # ── 启动 ──

    def run(self):
        """启动推理服务"""
        logger.info("=" * 60)
        logger.info("C-RADIOv4 云端推理服务启动")
        logger.info("=" * 60)

        # 加载模型
        self._load_model()

        # 启动 MQTT
        self._setup_mqtt()

        logger.info("服务已就绪，等待关键帧...")
        logger.info("按 Ctrl+C 停止")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("正在停止...")
            self._client.loop_stop()
            self._client.disconnect()

            # 打印统计
            n = self._stats["total_frames"]
            if n > 0:
                avg_ms = self._stats["total_inference_ms"] / n
                logger.info(
                    "统计: %d 帧, 平均 %.1f ms/帧, %d 错误",
                    n, avg_ms, self._stats["errors"],
                )

            logger.info("已停止")


def main():
    server = RadioInferServer()
    server.run()


if __name__ == "__main__":
    main()
