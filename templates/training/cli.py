#!/usr/bin/env python3
"""
edge_train CLI - 参考 YOLOv8 设计
用法:
    edge-train train --data data.yaml --model yolov8n.pt --epochs 100
    edge-train val --model best.pt --data data.yaml
    edge-train predict --model best.pt --source images/
    edge-train export --model best.pt --format onnx
"""

import argparse
from ultralytics import YOLO

def train(opt):
    """训练模式"""
    model = YOLO(opt.model)
    results = model.train(
        data=opt.data,
        epochs=opt.epochs,
        batch=opt.batch,
        imgsz=opt.imgsz,
        device=opt.device,
        optimizer=opt.optimizer,
        lr0=opt.lr0,
        project=opt.project,
        name=opt.name,
        exist_ok=opt.exist_ok,
        pretrained=opt.pretrained,
        amp=opt.amp
    )
    return results

def val(opt):
    """验证模式"""
    model = YOLO(opt.model)
    results = model.val(
        data=opt.data,
        batch=opt.batch,
        imgsz=opt.imgsz,
        device=opt.device,
        plots=opt.plots,
        save_json=opt.save_json
    )
    return results

def predict(opt):
    """预测模式"""
    model = YOLO(opt.model)
    results = model.predict(
        source=opt.source,
        conf=opt.conf,
        iou=opt.iou,
        imgsz=opt.imgsz,
        save=opt.save,
        save_txt=opt.save_txt,
        save_conf=opt.save_conf
    )
    return results

def export(opt):
    """导出模式"""
    model = YOLO(opt.model)
    model.export(
        format=opt.format,
        imgsz=opt.imgsz,
        half=opt.half,
        dynamic=opt.dynamic,
        simplify=opt.simplify
    )

def parse_opt():
    """解析命令行参数（参考 YOLOv8）"""
    parser = argparse.ArgumentParser()

    # 通用参数
    parser.add_argument('--model', type=str, default='yolov8n.pt', help='模型文件')
    parser.add_argument('--data', type=str, default='data.yaml', help='数据集配置')
    parser.add_argument('--imgsz', '--img', '--img-size', type=int, default=640, help='图像大小')
    parser.add_argument('--batch', type=int, default=16, help='批量大小')
    parser.add_argument('--device', default='0', help='GPU 设备')

    # 训练参数
    parser.add_argument('--epochs', type=int, default=100, help='训练轮数')
    parser.add_argument('--optimizer', type=str, default='AdamW', help='优化器')
    parser.add_argument('--lr0', type=float, default=0.01, help='初始学习率')
    parser.add_argument('--project', default='runs/train', help='项目目录')
    parser.add_argument('--name', default='exp', help='实验名称')
    parser.add_argument('--exist-ok', action='store_true', help='允许覆盖')
    parser.add_argument('--pretrained', action='store_true', help='使用预训练')
    parser.add_argument('--amp', action='store_true', help='混合精度训练')

    # 验证/预测参数
    parser.add_argument('--plots', action='store_true', help='绘制图表')
    parser.add_argument('--save-json', action='store_true', help='保存 JSON 结果')
    parser.add_argument('--source', type=str, default='data/images', help='预测源')
    parser.add_argument('--conf', type=float, default=0.25, help='置信度阈值')
    parser.add_argument('--iou', type=float, default=0.7, help='NMS IOU 阈值')
    parser.add_argument('--save', action='store_true', help='保存结果')
    parser.add_argument('--save-txt', action='store_true', help='保存文本结果')
    parser.add_argument('--save-conf', action='store_true', help='保存置信度')

    # 导出参数
    parser.add_argument('--format', type=str, default='onnx', help='导出格式')
    parser.add_argument('--half', action='store_true', help='FP16 量化')
    parser.add_argument('--dynamic', action='store_true', help='动态轴')
    parser.add_argument('--simplify', action='store_true', help='简化 ONNX')

    # 任务类型
    subparsers = parser.add_subparsers(dest='task', help='任务类型')
    subparsers.add_parser('train', help='训练')
    subparsers.add_parser('val', help='验证')
    subparsers.add_parser('predict', help='预测')
    subparsers.add_parser('export', help='导出')

    return parser.parse_args()

def main(opt):
    """主函数"""
    if opt.task == 'train':
        train(opt)
    elif opt.task == 'val':
        val(opt)
    elif opt.task == 'predict':
        predict(opt)
    elif opt.task == 'export':
        export(opt)

if __name__ == '__main__':
    opt = parse_opt()
    main(opt)
