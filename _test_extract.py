import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.nlp_processor.extractor import MultiTechniqueExtractor, _clean_triplet, _is_generic_entity, _is_valid_relation_pair

test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests")
test_files = ["test.txt", "test1.txt", "test2.txt"]

all_text = ""
for fname in test_files:
    fpath = os.path.join(test_dir, fname)
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            all_text += f.read() + "\n\n"

print(f"测试文本总长度: {len(all_text)} 字符\n")

print("=== 1. 泛实体过滤测试 ===")
test_entities = ["公司", "总部", "信息", "技术", "科技", "工业", "平台", "系统",
                 "华为", "阿里巴巴", "北京", "5G芯片", "拼多多", "字节跳动"]
for e in test_entities:
    result = _is_generic_entity(e)
    status = "❌ 过滤" if result else "✅ 保留"
    print(f"  {e}: {status}")

print("\n=== 2. 自反过滤测试 ===")
test_triplets = [
    ("激素", "包含", "激素"),
    ("细胞", "包含", "细胞"),
    ("华为", "研发", "5G芯片"),
]
for e1, rel, e2 in test_triplets:
    result = _clean_triplet(e1, rel, e2)
    status = "❌ 过滤" if result is None else "✅ 保留"
    print(f"  ({e1}, {rel}, {e2}): {status}")

print("\n=== 3. 关系合理性测试 ===")
test_pairs = [
    ("玻璃", "生产", "食品"),
    ("华为", "研发", "5G芯片"),
    ("工业", "生产", "莫扎特"),
    ("中国", "位于", "尼泊尔"),
]
for e1, rel, e2 in test_pairs:
    result = _clean_triplet(e1, rel, e2)
    status = "❌ 过滤" if result is None else "✅ 保留"
    print(f"  ({e1}, {rel}, {e2}): {status}")

print("\n=== 4. 完整抽取测试（仅快速方法） ===")
extractor = MultiTechniqueExtractor(use_llm_cache=False)
fast_techniques = ["rule", "template", "spacy_rule", "spacy_template", "spacy_dep"]
triplets = extractor.extract(all_text, techniques=fast_techniques, smart_mode=False)

print(f"\n抽取结果: 共 {len(triplets)} 个三元组\n")
for i, (e1, rel, e2) in enumerate(triplets):
    print(f"  {i+1}. {e1} → {rel} → {e2}")

print(f"\n=== 统计: {extractor.get_stats()} ===")
