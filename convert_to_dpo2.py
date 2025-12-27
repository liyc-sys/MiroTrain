#!/usr/bin/env python3
"""
将matched_data_1.jsonl和matched_data_2.jsonl转换为DPO格式
在question前面加上system prompt
优先按question匹配，如果失败则按sample_id匹配
使用完整的interleaved_text包含工具调用过程，保留所有原始标签
"""

import json
import sys
import re  # 移到顶部导入
from pathlib import Path

# 导入system prompt
# 假设 docs 文件夹在当前脚本同级目录下
sys.path.insert(0, str(Path(__file__).parent / "docs"))
try:
    from system_prompt import SYSTEM_PROMPT
except ImportError:
    # 如果找不到文件，提供一个默认的 prompt 以防报错
    SYSTEM_PROMPT = "You are a helpful assistant."
    print("Warning: system_prompt.py not found, using default prompt.")


def load_jsonl(file_path):
    """加载JSONL文件"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def split_interleaved_to_messages(text):
    """
    辅助函数：输入 interleaved_text，将其拆分为 assistant 和 user 消息。
    - <tool_output>...</tool_output> 标签内的内容（含标签本身）识别为 user 角色。
    - 其他内容识别为 assistant 角色。
    - 严格保留原始标签和换行符。
    """
    if not text:
        return []

    # 改进正则：
    # 1. <tool_output(?:\s+[^>]*)?> : 兼容 <tool_output> 或 <tool_output name="...">
    # 2. flags=re.DOTALL : 关键！确保 . 能匹配换行符 \n
    pattern = r'<tool_output(?:\s+[^>]*)?>.*?</tool_output>'
    
    messages = []
    last_index = 0
    
    # 使用 DOTALL (匹配换行) 和 IGNORECASE (忽略大小写)
    for match in re.finditer(pattern, text, flags=re.DOTALL | re.IGNORECASE):
        # --- 1. 标签左侧的内容 (Assistant) ---
        outside_content = text[last_index:match.start()]
        
        # strip() 去除首尾空白，避免产生只有换行符的空消息
        if outside_content and outside_content.strip():
            messages.append({
                "role": "assistant",
                "content": outside_content.strip()
            })
            
        # --- 2. 标签本身及其内容 (User) ---
        # 直接使用 group(0) 获取完整的 <tool_output>...</tool_output>
        # 这里不做 strip，保留标签的原始格式
        full_tag_content = match.group(0)
        messages.append({
            "role": "user",
            "content": full_tag_content 
        })
        
        last_index = match.end()

    # --- 3. 最后一个标签之后的内容 (Assistant) ---
    remaining_content = text[last_index:]
    if remaining_content and remaining_content.strip():
        messages.append({
            "role": "assistant",
            "content": remaining_content.strip()
        })
        
    return messages


def convert_to_dpo_format(data1, data2, output_file, match_by_id=True):
    """
    将两个数据文件转换为DPO格式，使用完整的工具调用流程
    """
    dpo_data = []
    
    # 提取公共逻辑：构建单条 DPO 数据
    def build_dpo_item(question, text_chosen, text_rejected):
        # 基础结构
        chosen_msgs = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ]
        rejected_msgs = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ]
        
        # 使用辅助函数拆分 interleaved_text
        chosen_msgs.extend(split_interleaved_to_messages(text_chosen))
        rejected_msgs.extend(split_interleaved_to_messages(text_rejected))
        
        return {
            "chosen": chosen_msgs,
            "rejected": rejected_msgs
        }

    if match_by_id:
        # 按sample_id匹配
        data1_dict = {item['sample_id']: item for item in data1}
        data2_dict = {item['sample_id']: item for item in data2}
        
        common_ids = set(data1_dict.keys()) & set(data2_dict.keys())
        
        print(f"按sample_id匹配: 找到 {len(common_ids)} 个匹配的样本")
        
        for sample_id in sorted(common_ids):
            item1 = data1_dict[sample_id]
            item2 = data2_dict[sample_id]
            
            question = item1.get('question', '')
            # 获取 interleaved_text，如果没有则为空字符串
            answer1 = item1.get('trajectory', {}).get('interleaved_text', '')
            answer2 = item2.get('trajectory', {}).get('interleaved_text', '')

            dpo_data.append(build_dpo_item(question, answer1, answer2))

    else:
        # 按question匹配
        data1_dict = {item.get('question', ''): item for item in data1}
        data2_dict = {item.get('question', ''): item for item in data2}
        
        common_questions = set(data1_dict.keys()) & set(data2_dict.keys())
        common_questions.discard('') # 移除空question
        
        print(f"按question匹配: 找到 {len(common_questions)} 个匹配的样本")
        
        for question in sorted(common_questions):
            item1 = data1_dict[question]
            item2 = data2_dict[question]
            
            answer1 = item1.get('trajectory', {}).get('interleaved_text', '')
            answer2 = item2.get('trajectory', {}).get('interleaved_text', '')
            
            # 这里的逻辑原本缺失分割，现在补上了
            dpo_data.append(build_dpo_item(question, answer1, answer2))
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in dpo_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"成功转换 {len(dpo_data)} 条数据到 {output_file}")


def main():
    # 文件路径 - 请根据实际情况修改
    data1_path = Path("/Users/liyc/Desktop/MiroTrain/matched_data_1.jsonl")
    data2_path = Path("/Users/liyc/Desktop/MiroTrain/matched_data_2.jsonl")
    output_path = Path("/Users/liyc/Desktop/MiroTrain/dpo_dataset.jsonl")
    
    if not data1_path.exists() or not data2_path.exists():
        print(f"错误: 输入文件不存在。\n{data1_path}\n{data2_path}")
        return

    print("开始加载数据...")
    data1 = load_jsonl(data1_path)
    data2 = load_jsonl(data2_path)
    
    print(f"加载完成: data1={len(data1)}条, data2={len(data2)}条")
    
    print("开始转换...")
    # 策略：优先按 question 匹配
    convert_to_dpo_format(data1, data2, output_path, match_by_id=False)
    
    # 检查输出文件是否为空，如果为空则尝试按 sample_id 匹配
    is_empty = True
    if output_path.exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            if f.readline():
                is_empty = False
    
    if is_empty:
        print("\n按question匹配结果为空，尝试按sample_id匹配...")
        convert_to_dpo_format(data1, data2, output_path, match_by_id=True)
    
    print("转换完成！")


if __name__ == "__main__":
    main()