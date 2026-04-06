segmentor_path = '/app/water_inspection/models/open_vocab/core/segmentor.py'

with open(segmentor_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在 _load_inference_config 之前添加默认配置加载
old_code = """        # 加载推理参数
        self._load_inference_config()"""

new_code = """        # 加载默认配置（如果未提供）
        if not self.config or not self.config.get("cloud", {}).get("radio", {}).get("classes"):
            self._load_default_config()

        # 加载推理参数
        self._load_inference_config()"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(segmentor_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('✅ 添加默认配置加载调用')
else:
    print('⚠️ 未找到目标代码，可能已修复')
    # 查找实际代码
    import re
    matches = re.findall(r'self\._load_inference_config\(\)', content)
    print(f'  找到 {len(matches)} 处 _load_inference_config 调用')
