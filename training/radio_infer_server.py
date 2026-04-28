#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
C-RADIOv4 云端统一推理服务

自动检测运行模式：
  - 有边缘设备在线 → MQTT 模式（订阅 device/+/cloud/frame，等待边缘转发帧）
  - 仅有 RTMP 流   → RTMP 直连模式（从视频流按间隔采样）
  - 两者都有       → 双通道模式（MQTT 为主 + RTMP 补充采样）
  - 都没有         → 报错退出

命令行参数优先于环境变量。

用法:
  # 自动模式（推荐）— 检测 MQTT 和 RTMP 可用性后自动选择
  python cloud/radio_infer_server.py --config /app/models/construction_safety/configs/construction_safety.yaml

  # 仅 MQTT 模式（生产环境，边缘转发帧）
  python cloud/radio_infer_server.py --mode mqtt --config ...

  # 仅 RTMP 模式（开发/演示，无边缘设备）
  python cloud/radio_infer_server.py --mode stream --stream rtmp://192.168.0.103:1935/stream/safety_cam --config ...

  # 双通道模式（MQTT + RTMP 同时运行）
  python cloud/radio_infer_server.py --mode dual --stream rtmp://... --config ...

环境变量 (容器内通过 docker-compose 配置):
  MQTT_BROKER_URL       - MQTT broker 地址 (默认 tcp://emqx:1883)
  STREAM_URL            - RTMP/RTSP 视频流地址
  STREAM_INTERVAL       - 采样间隔秒数 (默认 3)
  CONFIG_PATH           - 场景配置文件路径
  RADIO_CHECKPOINT_PATH - C-RADIOv4 权重路径
  RADIO_CODE_DIR        - NVlabs_RADIO 代码路径
  SIGLIP2_DIR           - SigLIP2 模型路径
  BACKEND_API_URL       - 后端 API 地址
  DEVICE                - 推理设备 (cuda / cpu)
  INPUT_SIZE            - 输入尺寸 (默认 896)
"""

import os
import sys
import json
import base64
import time
import logging
import signal
import argparse
import urllib.request
import urllib.error
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 容器内脚本在 /app/ 下，parent.parent = /，需回退
if not (PROJECT_ROOT / "models").exists():
    PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "models" / "water_inspection"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("radio_server")

_shutdown = False


def _signal_handler(sig, frame):
    global _shutdown
    _shutdown = True
    logger.info("收到停止信号, 正在关闭...")


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


class RadioInferServer:
    """C-RADIOv4 云端统一推理服务"""

    _COLORS = [
        (0, 255, 0), (0, 0, 255), (0, 255, 255), (255, 0, 255),
        (255, 255, 0), (255, 128, 0), (128, 0, 255), (0, 128, 255),
    ]

    def __init__(self, args):
        # ── 运行模式 ──
        self.mode = args.mode  # auto / mqtt / stream / dual
        self.stream_url = args.stream or os.getenv("STREAM_URL", "")
        self.stream_interval = args.interval or int(os.getenv("STREAM_INTERVAL", "3"))
        self.stream_device_id = args.device_id or os.getenv("STREAM_DEVICE_ID", "cloud_gpu")

        # ── MQTT 配置 ──
        self.mqtt_broker = args.mqtt_broker or os.getenv("MQTT_BROKER_URL", "tcp://emqx:1883")
        self.mqtt_username = args.mqtt_username or os.getenv("MQTT_USERNAME", "")
        self.mqtt_password = args.mqtt_password or os.getenv("MQTT_PASSWORD", "")

        # ── 模型路径 ──
        self.checkpoint_path = args.checkpoint or os.getenv(
            "RADIO_CHECKPOINT_PATH", str(PROJECT_ROOT / "models" / "C-RADIOv4-H" / "c-radio_v4-h_half.pth.tar"))
        self.radio_code_dir = args.radio_code or os.getenv(
            "RADIO_CODE_DIR", str(PROJECT_ROOT / "models" / "NVlabs_RADIO"))
        self.siglip2_dir = args.siglip2 or os.getenv(
            "SIGLIP2_DIR", str(PROJECT_ROOT / "models" / "siglip2-giant-opt-patch16-384"))
        self.config_path = args.config or os.getenv(
            "CONFIG_PATH", str(PROJECT_ROOT / "models" / "construction_safety" / "configs" / "construction_safety.yaml"))
        self.device = args.device or os.getenv("DEVICE", "cuda")
        self.input_size = args.input_size or int(os.getenv("INPUT_SIZE", "896"))

        # ── 推理参数 ──
        self.alert_min_area = float(os.getenv("ALERT_MIN_AREA", "0.01"))

        # ── 后端 API ──
        self.backend_url = args.backend_url or os.getenv("BACKEND_API_URL", "http://backend:8080")

        # ── 内部状态 ──
        self._segmentor = None
        self._classes_config = None
        self._threshold = 0.3
        self._min_area = 0.01
        self._client: Optional[object] = None
        self._mqtt_connected = False
        self._frame_count = 0
        self._reported = 0
        self._resolved_mode = None  # auto 解析后的实际模式

    # ══════════════════════════════════════════
    #  模式自动检测
    # ══════════════════════════════════════════

    def _detect_mode(self) -> str:
        """根据环境自动检测运行模式"""
        if self.mode != "auto":
            return self.mode

        mqtt_ok = self._check_mqtt()
        stream_ok = bool(self.stream_url) and self._check_stream()

        if mqtt_ok and stream_ok:
            logger.info("自动检测: MQTT ✓ + RTMP ✓ → 双通道模式")
            return "dual"
        elif mqtt_ok:
            logger.info("自动检测: MQTT ✓ → MQTT 模式")
            return "mqtt"
        elif stream_ok:
            logger.info("自动检测: RTMP ✓ → RTMP 直连模式")
            return "stream"
        else:
            logger.error("自动检测: MQTT 和 RTMP 均不可用")
            logger.error("  → 请通过 --stream 指定视频流地址，或确保 MQTT broker 可达")
            sys.exit(1)

    def _check_mqtt(self) -> bool:
        """快速检测 MQTT broker 是否可达"""
        try:
            import paho.mqtt.client as mqtt
            broker_str = self.mqtt_broker.replace("tcp://", "").replace("mqtt://", "")
            parts = broker_str.split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 1883

            result = [False]

            def on_connect(client, userdata, flags, rc):
                result[0] = (rc == 0)
                client.disconnect()

            client = mqtt.Client(client_id="radio_probe", protocol=mqtt.MQTTv311)
            client.on_connect = on_connect
            if self.mqtt_username:
                client.username_pw_set(self.mqtt_username, self.mqtt_password)
            client.connect(host, port, keepalive=5)
            client.loop_start()
            time.sleep(2)
            client.loop_stop()
            return result[0]
        except Exception as e:
            logger.debug("MQTT 检测失败: %s", e)
            return False

    def _check_stream(self) -> bool:
        """快速检测 RTMP/RTSP 流是否可连接"""
        if not self.stream_url:
            return False
        try:
            cap = cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            ok = cap.isOpened()
            cap.release()
            return ok
        except Exception:
            return False

    # ══════════════════════════════════════════
    #  模型加载
    # ══════════════════════════════════════════

    def _load_model(self):
        import yaml

        logger.info("加载配置: %s", self.config_path)
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        radio_config = config.get("cloud", {}).get("radio", {})
        if not radio_config.get("classes"):
            radio_config = config.get("deployment", {}).get("cloud", {}).get("radio", {})
        self._classes_config = radio_config.get("classes", {})

        # 过滤掉 background 类
        self._classes_config = {
            k: v for k, v in self._classes_config.items()
            if not v.get("is_background", False)
        }

        logger.info("分割类别: %s", list(self._classes_config.keys()))

        infer_config = radio_config.get("inference", {}) or radio_config.get("model", {})
        self._threshold = float(infer_config.get("threshold", 0.3))
        self._min_area = float(infer_config.get("min_area", 0.01))

        from models.open_vocab import RADSegWaterSegmentor

        logger.info("加载 C-RADIOv4 模型...")
        self._segmentor = RADSegWaterSegmentor(
            checkpoint_path=self.checkpoint_path,
            radio_code_dir=self.radio_code_dir,
            siglip2_dir=self.siglip2_dir,
            device=self.device,
            input_size=self.input_size,
        )
        logger.info("模型加载完成")

    # ══════════════════════════════════════════
    #  推理核心 (所有模式共享)
    # ══════════════════════════════════════════

    _FONT = None

    def _get_font(self, size: int = 20):
        if self._FONT is not None and self._FONT.size == size:
            return self._FONT
        font_paths = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    # .ttc 文件需指定 index (Noto CJK SC = index 3)
                    self._FONT = ImageFont.truetype(fp, size, index=3 if fp.endswith(".ttc") else 0)
                    return self._FONT
                except Exception:
                    continue
        self._FONT = ImageFont.load_default()
        return self._FONT

    def _draw_annotations(self, image: np.ndarray, results: dict) -> bytes:
        annotated = image.copy()
        h, w = annotated.shape[:2]

        for i, (name, seg) in enumerate(results.items()):
            if not hasattr(seg, 'mask') or seg.mask is None:
                continue
            color = self._COLORS[i % len(self._COLORS)]
            mask = seg.mask.astype(bool)
            if mask.any():
                overlay = annotated.copy()
                overlay[mask] = color
                cv2.addWeighted(overlay, 0.4, annotated, 0.6, 0, annotated)
                ys, xs = np.where(mask)
                if len(ys) > 0:
                    cx, cy = int(xs.mean()), int(ys.mean())
                    label = f"{seg.class_name_cn or name} {seg.area_ratio:.1%}"

                    # PIL 渲染中文文字
                    font = self._get_font(20)
                    pil_img = Image.fromarray(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB))
                    draw = ImageDraw.Draw(pil_img)
                    bbox = draw.textbbox((0, 0), label, font=font)
                    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    tx, ty = cx - tw // 2, cy - th // 2

                    # 背景矩形
                    draw.rectangle([tx - 4, ty - 4, tx + tw + 4, ty + th + 4],
                                   fill=(color[2], color[1], color[0]))
                    draw.text((tx, ty), label, fill=(255, 255, 255), font=font)
                    annotated = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        if w > 960:
            scale = 960 / w
            annotated = cv2.resize(annotated, (960, int(h * scale)))
        _, buf = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buf.tobytes()

    def _infer_image(self, image: np.ndarray, device_id: str, frame_id: int, source: str = "cloud"):
        t0 = time.time()

        results = self._segmentor.segment(
            image, self._classes_config,
            threshold=self._threshold,
            min_area=self._min_area,
        )

        inference_ms = (time.time() - t0) * 1000

        segments = {}
        for name, seg in results.items():
            ys, xs = np.where(seg.mask)
            bbox = (
                [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
                if len(ys) > 0 else [0, 0, 0, 0]
            )
            segments[name] = {
                "area": round(seg.area_ratio, 4),
                "score": round(seg.score, 4),
                "bbox": bbox,
                "class_name_cn": seg.class_name_cn,
            }

        alerts = self._generate_alerts(segments)

        self._reported += 1
        seg_names = list(segments.keys()) or ["无检出"]
        logger.info(
            "[%d] %s frame=%d (%s): %s, %d alerts, %.0fms",
            self._reported, device_id, frame_id, source, seg_names, len(alerts), inference_ms,
        )

        if not alerts and not segments:
            return

        image_b64 = None
        if segments:
            try:
                img_bytes = self._draw_annotations(image, results)
                image_b64 = base64.b64encode(img_bytes).decode("ascii")
            except Exception as e:
                logger.warning("绘制标注失败: %s", e)

        payload = {
            "device_id": device_id,
            "frame_id": frame_id,
            "timestamp": datetime.now().isoformat(),
            "segments": segments,
            "alerts": alerts,
            "inference_time_ms": round(inference_ms, 1),
        }
        if image_b64:
            payload["image_base64"] = image_b64

        if self._client and self._mqtt_connected:
            topic = f"device/{device_id}/cloud/result"
            self._client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=1)

        self._report_to_backend(payload)

    # ══════════════════════════════════════════
    #  MQTT 模式
    # ══════════════════════════════════════════

    def _setup_mqtt(self):
        import paho.mqtt.client as mqtt

        client_id = f"radio_infer_{os.getenv('HOSTNAME', 'cloud')}"
        self._client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

        if self.mqtt_username:
            self._client.username_pw_set(self.mqtt_username, self.mqtt_password)

        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

        broker_str = self.mqtt_broker.replace("tcp://", "").replace("mqtt://", "")
        parts = broker_str.split(":")
        host, port = parts[0], int(parts[1]) if len(parts) > 1 else 1883

        logger.info("连接 MQTT: %s:%d", host, port)
        self._client.connect(host, port, keepalive=60)
        self._client.loop_start()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._mqtt_connected = True
            client.subscribe("device/+/cloud/frame", qos=1)
            logger.info("MQTT 已连接, 订阅: device/+/cloud/frame")
        else:
            self._mqtt_connected = False
            logger.error("MQTT 连接失败: rc=%d", rc)

    def _on_disconnect(self, client, userdata, rc):
        self._mqtt_connected = False
        if rc != 0:
            logger.warning("MQTT 意外断开 (rc=%d), 自动重连中...", rc)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            device_id = payload.get("device_id", "unknown")
            frame_id = payload.get("frame_id", 0)
            image_b64 = payload.get("image", "")

            image_data = base64.b64decode(image_b64)
            image_array = np.frombuffer(image_data, dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if image is None:
                logger.warning("图像解码失败: %s", device_id)
                return

            self._infer_image(image, device_id, frame_id, source="mqtt")
        except Exception as e:
            logger.error("处理 MQTT 帧失败: %s", e, exc_info=True)

    def _run_mqtt_loop(self):
        """MQTT 订阅主循环（阻塞）"""
        while not _shutdown:
            time.sleep(1)
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()

    # ══════════════════════════════════════════
    #  RTMP 直连模式
    # ══════════════════════════════════════════

    def _run_stream_loop(self):
        """RTMP 流式采样主循环（阻塞）"""
        logger.info("RTMP 直连: %s, 间隔 %ds", self.stream_url, self.stream_interval)

        last_infer_time = 0

        while not _shutdown:
            cap = None
            try:
                logger.info("连接视频流: %s", self.stream_url)
                cap = cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                if not cap.isOpened():
                    raise ConnectionError(f"无法打开: {self.stream_url}")

                logger.info("流已连接, 每 %ds 采样一帧", self.stream_interval)

                while not _shutdown:
                    ret, frame = cap.read()
                    if not ret:
                        logger.warning("流断开, 3s 后重连")
                        break

                    self._frame_count += 1
                    now = time.time()

                    if now - last_infer_time < self.stream_interval:
                        continue
                    last_infer_time = now

                    self._infer_image(frame, self.stream_device_id, self._frame_count, source="stream")

            except Exception as e:
                logger.warning("流异常: %s", e)
            finally:
                if cap:
                    cap.release()

            if not _shutdown:
                time.sleep(3)

    # ══════════════════════════════════════════
    #  双通道模式 (MQTT + RTMP 并行)
    # ══════════════════════════════════════════

    def _run_dual(self):
        """双通道: MQTT 在主线程，RTMP 在后台线程"""
        self._setup_mqtt()
        stream_thread = threading.Thread(target=self._run_stream_loop, daemon=True)
        stream_thread.start()
        logger.info("双通道模式: MQTT(主) + RTMP(后台) 已启动")
        self._run_mqtt_loop()

    # ══════════════════════════════════════════
    #  告警 + 上报
    # ══════════════════════════════════════════

    def _generate_alerts(self, segments: dict) -> list:
        alert_map = {
            # 水利巡检
            "black_water": ("critical", "黑水污染"),
            "brown_water": ("critical", "褐色水体"),
            "yellow_water": ("warning", "黄色水体"),
            "green_water": ("warning", "藻类爆发"),
            "red_water": ("critical", "化学污染"),
            "milky_water": ("warning", "水体浑浊"),
            "foam_water": ("warning", "水面泡沫"),
            "dam_seepage": ("critical", "坝体渗水"),
            # 施工安全
            "bare_soil_uncovered": ("warning", "裸土未覆盖"),
            "dust_pollution": ("critical", "扬尘污染"),
            "pit_water_accumulation": ("warning", "坑内积水"),
            "material_near_pit": ("warning", "基坑边材料堆放"),
        }

        alerts = []
        for class_name, info in segments.items():
            if info["area"] >= self.alert_min_area:
                level, desc = alert_map.get(class_name, ("warning", class_name))
                alerts.append({
                    "class_name": class_name,
                    "class_name_cn": info.get("class_name_cn", desc),
                    "level": level,
                    "message": f"{desc}，面积占比 {info['area']:.1%}",
                    "area": info["area"],
                })
        return alerts

    def _report_to_backend(self, payload: dict):
        try:
            url = f"{self.backend_url}/api/v1/cloud/inference/result"
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    logger.warning("后端返回: %d", resp.status)
        except urllib.error.URLError as e:
            logger.warning("后端上报失败: %s", e.reason)
        except Exception as e:
            logger.warning("后端异常: %s", e)

    # ══════════════════════════════════════════
    #  启动入口
    # ══════════════════════════════════════════

    def run(self):
        # 自动检测模式
        self._resolved_mode = self._detect_mode()

        mode_desc = {
            "mqtt": "MQTT 订阅 (边缘转发帧)",
            "stream": "RTMP 直连 (视频流采样)",
            "dual": "双通道 (MQTT 主 + RTMP 辅)",
        }

        logger.info("=" * 60)
        logger.info("C-RADIOv4 云端统一推理服务")
        logger.info("模式: %s", mode_desc.get(self._resolved_mode, self._resolved_mode))
        if self._resolved_mode in ("stream", "dual"):
            logger.info("流地址: %s, 间隔: %ds", self.stream_url, self.stream_interval)
        logger.info("后端: %s", self.backend_url)
        logger.info("配置: %s", self.config_path)
        logger.info("=" * 60)

        self._load_model()

        if self._resolved_mode == "mqtt":
            self._setup_mqtt()
            self._run_mqtt_loop()
        elif self._resolved_mode == "stream":
            self._run_stream_loop()
        elif self._resolved_mode == "dual":
            self._run_dual()

        logger.info("已停止, 共上报 %d 帧", self._reported)


def main():
    default_config = str(PROJECT_ROOT / "models" / "construction_safety" / "configs" / "construction_safety.yaml")

    parser = argparse.ArgumentParser(description="C-RADIOv4 云端统一推理服务")

    # 运行模式
    parser.add_argument("--mode", choices=["auto", "mqtt", "stream", "dual"],
                        default="auto",
                        help="运行模式 (默认 auto: 自动检测)")
    parser.add_argument("--stream", default="", help="RTMP/RTSP 视频流地址")
    parser.add_argument("--interval", type=int, default=0, help="采样间隔秒数 (默认 3)")
    parser.add_argument("--device-id", default="", help="设备ID (RTMP 模式下使用)")

    # MQTT
    parser.add_argument("--mqtt-broker", default="", help="MQTT broker 地址 (如 tcp://192.168.0.103:1883)")
    parser.add_argument("--mqtt-username", default="")
    parser.add_argument("--mqtt-password", default="")

    # 模型
    parser.add_argument("--config", default=default_config, help="场景配置文件路径")
    parser.add_argument("--checkpoint", default="", help="C-RADIOv4 权重路径")
    parser.add_argument("--radio-code", default="", help="NVlabs_RADIO 代码路径")
    parser.add_argument("--siglip2", default="", help="SigLIP2 模型路径")
    parser.add_argument("--device", default="", help="推理设备 (cuda / cpu)")
    parser.add_argument("--input-size", type=int, default=0, help="输入尺寸 (默认 896)")

    # 后端
    parser.add_argument("--backend-url", default="", help="后端 API 地址")

    args = parser.parse_args()
    server = RadioInferServer(args)
    server.run()


if __name__ == "__main__":
    main()
