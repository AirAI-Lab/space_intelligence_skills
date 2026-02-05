#!/usr/bin/env python3
"""
测试模型转换上传功能

用法:
    python scripts/test_conversion.py --task-id CONV2026010112000012345 --file models/helmet_detect/best.onnx
"""

import argparse
import os
import sys
import json
import time
import requests
from pathlib import Path

# Windows 兼容：设置 UTF-8 编码
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 配置
CLOUD_BASE_URL = os.environ.get("CLOUD_BASE_URL", "http://localhost:8081")

# 颜色输出
class Colors:
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

def log_info(msg):
    print(f"{Colors.GREEN}[INFO]{Colors.NC} {msg}")

def log_warn(msg):
    print(f"{Colors.YELLOW}[WARN]{Colors.NC} {msg}")

def log_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}")

def log_header(msg):
    print(f"\n{Colors.BLUE}==========================================")
    print(f"{msg}")
    print(f"=========================================={Colors.NC}\n")

def check_backend_health():
    """检查后端服务健康状态"""
    log_header("1. 检查后端服务")

    try:
        # 尝试健康检查端点
        response = requests.get(f"{CLOUD_BASE_URL}/actuator/health", timeout=5)
        if response.status_code == 200:
            log_info("✓ 后端服务运行正常")
            return True
    except:
        pass

    # 尝试访问首页
    try:
        response = requests.get(f"{CLOUD_BASE_URL}/", timeout=5)
        if response.status_code < 500:
            log_info("✓ 后端服务可访问")
            return True
    except Exception as e:
        log_error(f"✗ 无法连接到后端服务: {CLOUD_BASE_URL}")
        return False

def check_conversion_task(task_id):
    """检查转换任务状态"""
    log_header("2. 检查转换任务")

    url = f"{CLOUD_BASE_URL}/api/v1/conversion/tasks/{task_id}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        task_status = data.get("data", {}).get("status")
        model_id = data.get("data", {}).get("modelId")
        log_info(f"任务状态: {task_status}")
        log_info(f"模型 ID: {model_id}")
        return model_id
    else:
        log_warn(f"无法获取任务状态 (HTTP {response.status_code})")
        return None

def upload_conversion_file(task_id, onnx_file):
    """上传转换完成的文件"""
    log_header("3. 上传转换文件")

    if not os.path.exists(onnx_file):
        log_error(f"文件不存在: {onnx_file}")
        return False

    file_size = os.path.getsize(onnx_file)
    log_info(f"文件: {onnx_file}")
    log_info(f"大小: {file_size} bytes")

    url = f"{CLOUD_BASE_URL}/api/v1/conversion/internal/{task_id}/complete-with-file"

    start_time = time.time()

    with open(onnx_file, 'rb') as f:
        files = {'file': (os.path.basename(onnx_file), f, 'application/octet-stream')}
        data = {'optimization_time_seconds': '60'}

        response = requests.post(url, files=files, data=data)

    elapsed = time.time() - start_time

    log_info(f"上传耗时: {elapsed:.2f}s")
    log_info(f"HTTP 状态码: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        log_info("✓ 文件上传成功")
        log_info(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return True
    else:
        log_error(f"✗ 文件上传失败 (HTTP {response.status_code})")
        try:
            error_data = response.json()
            log_error(f"错误信息: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
        except:
            log_error(f"错误内容: {response.text[:200]}")
        return False

def verify_model_update(model_id):
    """验证模型记录已更新"""
    log_header("4. 验证模型记录")

    if not model_id:
        log_warn("跳过验证（无模型 ID）")
        return

    # 等待数据库更新
    time.sleep(2)

    url = f"{CLOUD_BASE_URL}/api/v1/models/{model_id}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        model = data.get("data", {})

        model_status = model.get("status")
        onnx_path = model.get("onnxFilePath")
        onnx_size = model.get("onnxFileSizeBytes")

        log_info(f"模型状态: {model_status}")
        log_info(f"ONNX 路径: {onnx_path}")
        log_info(f"ONNX 大小: {onnx_size} bytes")

        if onnx_path:
            # 检查是否是 S3 key 格式
            if onnx_path.startswith("models/") or "-" in onnx_path:
                log_info("✓ 文件路径是存储 key 格式")
            else:
                log_warn(f"文件路径格式: {onnx_path}")
        else:
            log_error("✗ ONNX 路径为空")
    else:
        log_error(f"无法获取模型信息 (HTTP {response.status_code})")

def test_model_download(model_id):
    """测试模型文件下载"""
    log_header("5. 测试文件下载")

    if not model_id:
        log_warn("跳过下载测试（无模型 ID）")
        return

    url = f"{CLOUD_BASE_URL}/api/v1/models/{model_id}/download?format=onnx"

    try:
        # 只下载前 1000 字节进行验证
        headers = {"Range": "bytes=0-999"}
        response = requests.get(url, headers=headers, timeout=30)

        log_info(f"HTTP 状态码: {response.status_code}")
        log_info(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")

        if response.status_code in [200, 206]:
            downloaded_bytes = len(response.content)
            log_info(f"✓ 文件下载成功")
            log_info(f"下载字节数: {downloaded_bytes}")

            # 检查是否是二进制文件
            if response.headers.get('Content-Type', '').startswith('application/octet-stream'):
                log_info("✓ Content-Type 正确")
            elif response.headers.get('Content-Type', '').startswith('application/json'):
                log_warn("返回的是 JSON 而非二进制文件")
                log_info(f"响应内容: {response.text[:200]}")
        elif response.status_code == 404:
            log_warn("✗ 文件未找到")
        else:
            log_error(f"✗ 下载失败 (HTTP {response.status_code})")
    except Exception as e:
        log_error(f"下载异常: {e}")

def main():
    parser = argparse.ArgumentParser(description="测试模型转换上传功能")
    parser.add_argument("--task-id", required=True, help="转换任务 ID")
    parser.add_argument("--file", required=True, help="要上传的 ONNX 文件路径")
    parser.add_argument("--verify-only", action="store_true", help="仅验证不上传")

    args = parser.parse_args()

    log_header("模型转换上传功能测试")
    log_info(f"后端地址: {CLOUD_BASE_URL}")
    log_info(f"任务 ID: {args.task_id}")
    log_info(f"文件路径: {args.file}")

    # 1. 检查后端服务
    if not check_backend_health():
        sys.exit(1)

    # 2. 检查转换任务
    model_id = check_conversion_task(args.task_id)

    # 3. 上传文件（如果指定）
    if not args.verify_only:
        if upload_conversion_file(args.task_id, args.file):
            # 4. 验证模型记录
            verify_model_update(model_id)
    else:
        log_info("验证模式：跳过文件上传")

    # 5. 测试下载
    test_model_download(model_id)

    log_header("测试完成")
    log_info("所有测试已完成！")

if __name__ == "__main__":
    main()
