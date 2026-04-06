from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from data.dataset_levir_repro import LEVIRCDReproDataset
from models.loss_peftcd import PeftCDLoss
from models.metrics_peftcd import compute_confusion, metrics_from_confusion
from models.model_peftcd_with_acta import PeftCDWithACTAModel


def load_config(path: Path):
    import yaml
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def evaluate(model, loader, criterion, device, threshold: float):
    model.eval()
    conf = {'tp': 0.0, 'fp': 0.0, 'fn': 0.0, 'tn': 0.0}
    total_loss = 0.0

    with torch.no_grad():
        for img_a, img_b, label in loader:
            img_a = img_a.to(device)
            img_b = img_b.to(device)
            label = label.to(device)

            out = model(img_a, img_b)
            logits = out['change_map']
            total_loss += float(criterion(logits, label)['total'].item())

            cur = compute_confusion(logits, label, threshold)
            for k in conf:
                conf[k] += cur[k]

    metrics = metrics_from_confusion(conf)
    metrics['loss'] = total_loss / max(len(loader), 1)
    metrics['threshold'] = threshold
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description='PeftCD with ACTA evaluation')
    parser.add_argument('--config', type=str, default='configs/config_peft_with_acta.yaml')
    parser.add_argument('--checkpoint', type=str, required=True)
    parser.add_argument('--split', type=str, default='test', choices=['val', 'test'])
    args = parser.parse_args()

    config = load_config(Path(args.config))
    exp_id = config['experiment']['id']

    dataset = LEVIRCDReproDataset(
        root_dir=config['dataset']['root_dir'],
        split=args.split,
        list_dir=config['dataset'].get('split_dir'),
        augment=False,
        image_size=config['dataset'].get('image_size', 256),
        use_split_subdirs=bool(config['dataset'].get('use_split_subdirs', False)),
        split_map=config['dataset'].get('split_map'),
    )
    loader = torch.utils.data.DataLoader(
        dataset,
        batch_size=config['dataset'].get('batch_size', 16),
        shuffle=False,
        num_workers=config['dataset'].get('num_workers', 4),
        pin_memory=True,
    )

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'Using device: {device}')
    print(f'Loading checkpoint: {args.checkpoint}')

    model = PeftCDWithACTAModel(config['model'], config['dataset']).to(device)
    ckpt = torch.load(args.checkpoint, map_location=device)
    # Checkpoint may be a raw state_dict or wrapped in a dict
    if 'model_state_dict' in ckpt:
        model.load_state_dict(ckpt['model_state_dict'], strict=True)
    else:
        model.load_state_dict(ckpt, strict=True)

    criterion = PeftCDLoss(
        bce_weight=float(config['loss'].get('bce_weight', 1.0)),
        dice_weight=float(config['loss'].get('dice_weight', 1.0)),
        loss_type=str(config['loss'].get('type', 'bce_dice')),
        pos_weight=config['loss'].get('pos_weight'),
    ).to(device)

    threshold = float(config['eval'].get('fixed_threshold', 0.5))

    print(f'Evaluating on {args.split} set ({len(dataset)} samples)...')
    metrics = evaluate(model, loader, criterion, device, threshold)

    report_dir = ROOT / config['paths'].get('report_dir', 'artifacts/reports')
    report_dir.mkdir(parents=True, exist_ok=True)
    output = report_dir / f'{exp_id}_{args.split}_eval.json'

    payload = {
        'experiment_id': exp_id,
        'split': args.split,
        'checkpoint': str(Path(args.checkpoint).resolve()),
        'metrics': metrics,
        'timestamp': datetime.now().isoformat(),
    }

    with open(output, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)

    print('=' * 60)
    print('EVALUATION RESULTS')
    print('=' * 60)
    print(f'Experiment: {exp_id}')
    print(f'Split: {args.split}')
    print(f'Checkpoint: {Path(args.checkpoint).name}')
    print('-' * 60)
    iou_pct = metrics['iou'] * 100
    f1_pct = metrics['f1'] * 100
    prec_pct = metrics['precision'] * 100
    rec_pct = metrics['recall'] * 100
    print(f'  IoU:       {metrics["iou"]:.4f} ({iou_pct:.2f}%)')
    print(f'  F1 Score:  {metrics["f1"]:.4f} ({f1_pct:.2f}%)')
    print(f'  Precision: {metrics["precision"]:.4f} ({prec_pct:.2f}%)')
    print(f'  Recall:    {metrics["recall"]:.4f} ({rec_pct:.2f}%)')
    print(f'  Loss:      {metrics["loss"]:.4f}')
    print('=' * 60)
    print(f'Saved to: {output}')


if __name__ == '__main__':
    main()
