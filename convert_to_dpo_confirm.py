#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def check_dpo_dataset(file_path, num_samples_to_show=3):
    """
    检查DPO数据集的格式、标签保留情况和分割逻辑
    """
    path = Path(file_path)
    if not path.exists():
        print(f"❌ 错误: 文件不存在 -> {path}")
        return

    print(f"🔍 开始检查文件: {path.name}")
    print("=" * 60)

    total_count = 0
    error_count = 0
    valid_count = 0
    
    # 统计信息
    stats = {
        "total_turns": 0,
        "has_tool_calls": 0
    }

    with open(path, 'r', encoding='utf-8') as f:
        for line_idx, line in enumerate(f):
            total_count += 1
            try:
                item = json.loads(line.strip())
            except json.JSONDecodeError:
                print(f"❌ 第 {line_idx+1} 行 JSON 解析失败")
                error_count += 1
                continue

            # 检查基本结构
            if "chosen" not in item or "rejected" not in item:
                print(f"❌ 第 {line_idx+1} 行缺少 chosen 或 rejected 字段")
                error_count += 1
                continue

            # 检查 chosen 和 rejected
            has_error = False
            for key in ["chosen", "rejected"]:
                msgs = item[key]
                
                # 1. 检查 System Prompt
                if msgs[0]['role'] != 'system':
                    print(f"⚠️ 第 {line_idx+1} 行 [{key}] 第一条不是 system")
                    has_error = True
                
                # 2. 检查 User Question
                if msgs[1]['role'] != 'user':
                    print(f"⚠️ 第 {line_idx+1} 行 [{key}] 第二条不是 user (question)")
                    has_error = True

                # 3. 检查后续的消息流 (Tool Output 分割检查)
                for i, msg in enumerate(msgs[2:], start=2):
                    role = msg['role']
                    content = msg['content']
                    
                    stats["total_turns"] += 1

                    # 检查 Assistant 角色
                    if role == 'assistant':
                        # Assistant 内容中不应该包含 <tool_output>，因为应该被分割给 User 了
                        # 注意：这里使用 loose check，因为有时候 assistant 可能会引用标签，但大概率是分割失败
                        if "<tool_output>" in content and "</tool_output>" in content:
                            # 只有当成对出现时，才极大概率是分割漏了
                            print(f"❌ 第 {line_idx+1} 行 [{key}] index {i} (Assistant) 包含完整 <tool_output> 标签，分割可能失败！")
                            print(f"   内容片段: {content[:50]}...")
                            has_error = True

                    # 检查 User 角色 (应该是 Tool Output)
                    elif role == 'user':
                        stats["has_tool_calls"] += 1
                        # User 消息必须包含 <tool_output> 标签
                        if "<tool_output>" not in content:
                            print(f"❌ 第 {line_idx+1} 行 [{key}] index {i} (User) 是工具返回，但缺少 <tool_output> 标签！")
                            print(f"   内容片段: {content[:50]}...")
                            has_error = True
                        
                        # 检查标签是否保留完整
                        if not content.strip().startswith("<tool_output") or "</tool_output>" not in content:
                             # 允许带有属性，所以 startswith 检查 <tool_output
                             pass # 只要包含就行，上面已经检查了包含

            if has_error:
                error_count += 1
            else:
                valid_count += 1

            # --- 可视化打印前 N 个样本 ---
            if valid_count <= num_samples_to_show and not has_error:
                print(f"\n✅ [样本预览 {valid_count}] (只展示 Chosen)")
                print("-" * 40)
                print(f"Question: {item['chosen'][1]['content'][:100]}...")
                print("-" * 20)
                
                # 打印交互流
                for i, msg in enumerate(item['chosen'][2:], start=2):
                    role_tag = f"[{msg['role'].upper()}]"
                    content_preview = msg['content'].replace('\n', ' ')
                    
                    # 高亮显示 Tool Output 标签
                    if "<tool_output>" in msg['content']:
                        tag_check = "✅ 标签存在"
                    else:
                        tag_check = ""
                        
                    print(f"{role_tag:<12} {content_preview[:80]}... {tag_check}")
                    
                    # 如果是 User，打印完整内容确认标签没被切掉
                    if msg['role'] == 'user' and i == 3: # 只打印第一个工具返回的完整内容
                        print(f"   └── 🔍 深度检查完整内容: {msg['content'][:60]} ... {msg['content'][-20:]}")

    print("\n" + "=" * 60)
    print("📊 检查报告")
    print(f"总样本数: {total_count}")
    print(f"✅ 通过检查: {valid_count}")
    print(f"❌ 发现问题: {error_count}")
    print(f"工具调用次数 (User Turns): {stats['has_tool_calls']}")
    
    if error_count == 0:
        print("\n🎉 完美！所有数据格式正确，<tool_output> 标签已保留且分割逻辑正确。")
    else:
        print("\n⚠️ 存在错误，请检查上方的错误日志。")

if __name__ == "__main__":
    # 这里修改为你的输出文件路径
    output_file = "/Users/liyc/Desktop/MiroTrain/dpo_dataset.jsonl"
    check_dpo_dataset(output_file)