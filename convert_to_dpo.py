#!/usr/bin/env python3
"""
将matched_data_1.jsonl和matched_data_2.jsonl转换为DPO格式
在question前面加上system prompt
优先按question匹配，如果失败则按sample_id匹配
使用完整的interleaved_text包含工具调用过程，保留所有原始标签
"""

import json
import sys
from pathlib import Path

# 导入system prompt
sys.path.insert(0, str(Path(__file__).parent / "docs"))
from system_prompt import SYSTEM_PROMPT


def load_jsonl(file_path):
    """加载JSONL文件"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def convert_to_dpo_format(data1, data2, output_file, match_by_id=True):
    """
    将两个数据文件转换为DPO格式，使用完整的工具调用流程
    
    Args:
        data1: 第一个文件的数据（作为chosen）
        data2: 第二个文件的数据（作为rejected）
        output_file: 输出文件路径
        match_by_id: 如果True，按sample_id匹配；如果False，按question匹配
    
    注意：
        - 使用interleaved_text字段而非final_answer，保留完整的工具调用过程
        - 保留所有原始标签：<think>, <call_tool>, </call_tool>, <tool_output>, </tool_output>, <answer>, </answer>
        - 生成的数据包含完整的推理-工具调用-结果理解-答案链条
    """
    dpo_data = []
    
    if match_by_id:
        # 按sample_id匹配
        data1_dict = {item['sample_id']: item for item in data1}
        data2_dict = {item['sample_id']: item for item in data2}
        
        # 找到共同的sample_id
        common_ids = set(data1_dict.keys()) & set(data2_dict.keys())
        
        print(f"按sample_id匹配: 找到 {len(common_ids)} 个匹配的样本")
        print(f"data1 总样本数: {len(data1_dict)}")
        print(f"data2 总样本数: {len(data2_dict)}")
        
        for sample_id in sorted(common_ids):
            item1 = data1_dict[sample_id]
            item2 = data2_dict[sample_id]
            
            question = item1.get('question', '')
            answer1 = item1.get('trajectory', {}).get('interleaved_text', '')
            answer2 = item2.get('trajectory', {}).get('interleaved_text', '')

            import re

            def split_interleaved_to_messages(text):
                """
                输入 interleaved_text，
                严格匹配 <tool_output> 到 </tool_output> 之间的内容（包含换行符）。
                标签部分（含标签本身）作为 user，
                标签以外的部分作为 assistant。
                """
                if not text:
                    return []

                # 1. 核心正则：严格匹配这两个特定的标签
                # 2. flags=re.DOTALL：这是“能匹配上”的关键，让 . 能匹配换行符 \n
                pattern = r'<tool_output>.*?</tool_output>'
                
                messages = []
                last_index = 0
                
                for match in re.finditer(pattern, text, flags=re.DOTALL):
                    # --- 1. 标签左侧的内容 (Assistant) ---
                    outside_content = text[last_index:match.start()]
                    # strip() 去除首尾空白，避免由换行产生的空消息
                    if outside_content and outside_content.strip():
                        messages.append({
                            "role": "assistant",
                            "content": outside_content.strip()
                        })
                        
                    # --- 2. 标签本身及其内容 (User) ---
                    # 直接使用 group(0) 获取完整的 <tool_output>...</tool_output>
                    full_tag_content = match.group(0)
                    messages.append({
                        "role": "user",
                        "content": full_tag_content  # 这里保留了原始格式，未做strip以免破坏标签结构
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
            
            # 对 chosen 答案和 rejected 答案分别做 interleaved_to_messages 拆分
            # 最前面都插 system prompt 和 user 的问题
            chosen_messages = []
            rejected_messages = []
            # system prompt
            chosen_messages.append({"role": "system", "content": SYSTEM_PROMPT})
            rejected_messages.append({"role": "system", "content": SYSTEM_PROMPT})
            # user 问题
            chosen_messages.append({"role": "user", "content": question})
            rejected_messages.append({"role": "user", "content": question})
            # assistant/user 交错的消息体
            chosen_messages.extend(split_interleaved_to_messages(answer1))
            rejected_messages.extend(split_interleaved_to_messages(answer2))
            
            
            # # 构建chosen和rejected消息
            # chosen_messages = [
            #     {"role": "system", "content": SYSTEM_PROMPT},
            #     {"role": "user", "content": question},
            #     {"role": "assistant", "content": answer1}
            # ]
            
            # rejected_messages = [
            #     {"role": "system", "content": SYSTEM_PROMPT},
            #     {"role": "user", "content": question},
            #     {"role": "assistant", "content": answer2}
            # ]
            
            dpo_item = {
                "chosen": chosen_messages,
                "rejected": rejected_messages
            }
            
            dpo_data.append(dpo_item)
    else:
        # 按question匹配
        data1_dict = {item.get('question', ''): item for item in data1}
        data2_dict = {item.get('question', ''): item for item in data2}
        
        # 找到共同的question
        common_questions = set(data1_dict.keys()) & set(data2_dict.keys())
        # 移除空question
        common_questions.discard('')
        
        print(f"按question匹配: 找到 {len(common_questions)} 个匹配的样本")
        print(f"data1 总样本数: {len(data1_dict)}")
        print(f"data2 总样本数: {len(data2_dict)}")
        
        for question in sorted(common_questions):
            item1 = data1_dict[question]
            item2 = data2_dict[question]
            
            answer1 = item1.get('trajectory', {}).get('interleaved_text', '')
            answer2 = item2.get('trajectory', {}).get('interleaved_text', '')
            
            # 构建chosen和rejected消息
            chosen_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer1}
            ]
            
            rejected_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer2}
            ]
            
            dpo_item = {
                "chosen": chosen_messages,
                "rejected": rejected_messages
            }
            
            dpo_data.append(dpo_item)
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in dpo_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"成功转换 {len(dpo_data)} 条数据到 {output_file}")


def main():
    # 文件路径
    data1_path = Path("/Users/liyc/Desktop/MiroTrain/matched_data_1.jsonl")
    data2_path = Path("/Users/liyc/Desktop/MiroTrain/matched_data_2.jsonl")
    output_path = Path("/Users/liyc/Desktop/MiroTrain/dpo_dataset.jsonl")
    
    print("开始加载数据...")
    data1 = load_jsonl(data1_path)
    data2 = load_jsonl(data2_path)
    
    print(f"加载完成: data1={len(data1)}条, data2={len(data2)}条")
    
    print("开始转换...")
    # 按question匹配
    convert_to_dpo_format(data1, data2, output_path, match_by_id=False)
    
    # 如果按question匹配失败，尝试按sample_id匹配
    if len(load_jsonl(output_path)) == 0:
        print("\n按question匹配失败，尝试按sample_id匹配...")
        convert_to_dpo_format(data1, data2, output_path, match_by_id=True)
    
    print("转换完成！")


if __name__ == "__main__":
    main()

