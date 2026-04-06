import json
from pathlib import Path
from collections import Counter

meta_dir = Path('/app/water_inspection/data/datasets/meta')
class_count = Counter()

for meta_file in meta_dir.glob('*.json'):
    with open(meta_file) as f:
        meta = json.load(f)
    active_class = meta.get('active_class')
    if active_class:
        class_count[active_class] += 1

print("Dataset GT Class Distribution:")
print("="*50)
for cls, count in class_count.most_common():
    print(f"{cls}: {count}")
