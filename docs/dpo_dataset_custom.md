# DPO数据集格式说明和自定义指南

## DPO数据集存储格式

DPO数据集需要包含**chosen**（被选中的回答）和**rejected**（被拒绝的回答）两列数据。

### 格式1: 对话格式（推荐，支持多轮对话）

每行数据包含两个对话列表，格式如下：

```json
{
  "chosen": [
    {"role": "user", "content": "问题1"},
    {"role": "assistant", "content": "好的回答"}
  ],
  "rejected": [
    {"role": "user", "content": "问题1"},
    {"role": "assistant", "content": "不好的回答"}
  ]
}
```

**多轮对话示例：**
```json
{
  "chosen": [
    {"role": "user", "content": "什么是机器学习？"},
    {"role": "assistant", "content": "机器学习是人工智能的一个分支..."},
    {"role": "user", "content": "能举个例子吗？"},
    {"role": "assistant", "content": "比如图像识别、语音识别等..."}
  ],
  "rejected": [
    {"role": "user", "content": "什么是机器学习？"},
    {"role": "assistant", "content": "我不太清楚..."},
    {"role": "user", "content": "能举个例子吗？"},
    {"role": "assistant", "content": "抱歉，我无法回答"}
  ]
}
```

### 格式2: Prompt-Chosen-Rejected格式（仅支持单轮对话）

```json
{
  "prompt": "问题",
  "chosen": "好的回答",
  "rejected": "不好的回答"
}
```

## 数据文件格式

支持以下格式：
- **JSON文件** (`.json`)
- **JSONL文件** (`.jsonl`，每行一个JSON对象)
- **CSV文件** (`.csv`)
- **HuggingFace Hub数据集**

### JSON文件示例 (`my_dpo_data.json`)

```json
[
  {
    "chosen": [
      {"role": "user", "content": "如何学习Python？"},
      {"role": "assistant", "content": "学习Python可以从基础语法开始，推荐阅读官方文档..."}
    ],
    "rejected": [
      {"role": "user", "content": "如何学习Python？"},
      {"role": "assistant", "content": "不知道"}
    ]
  },
  {
    "chosen": [
      {"role": "user", "content": "什么是深度学习？"},
      {"role": "assistant", "content": "深度学习是机器学习的一个子领域，使用多层神经网络..."}
    ],
    "rejected": [
      {"role": "user", "content": "什么是深度学习？"},
      {"role": "assistant", "content": "就是AI"}
    ]
  }
]
```

### JSONL文件示例 (`my_dpo_data.jsonl`)

```jsonl
{"chosen": [{"role": "user", "content": "问题1"}, {"role": "assistant", "content": "回答1"}], "rejected": [{"role": "user", "content": "问题1"}, {"role": "assistant", "content": "回答2"}]}
{"chosen": [{"role": "user", "content": "问题2"}, {"role": "assistant", "content": "回答3"}], "rejected": [{"role": "user", "content": "问题2"}, {"role": "assistant", "content": "回答4"}]}
```

## 自定义DPO数据集的方法

### 方法1: 使用标准格式 + column_map（最简单）

如果你的数据列名不是`chosen`和`rejected`，可以使用`column_map`映射：

**数据文件** (`custom_data.json`):
```json
[
  {
    "good_response": [
      {"role": "user", "content": "问题"},
      {"role": "assistant", "content": "好回答"}
    ],
    "bad_response": [
      {"role": "user", "content": "问题"},
      {"role": "assistant", "content": "坏回答"}
    ]
  }
]
```

**配置文件** (`config.yaml`):
```yaml
dataset:
  _component_: torchtune.datasets.preference_dataset
  source: json
  data_files: ./custom_data.json
  column_map:
    chosen: good_response
    rejected: bad_response
  train_on_input: False  # 是否在prompt上计算loss
  split: train
```

### 方法2: 创建自定义Message Transform

如果你的数据格式完全不同，可以创建自定义的transform：

**步骤1**: 创建自定义transform文件 `my_transform.py`:

```python
from typing import Any, Mapping
from torchtune.data import Message, Transform

class MyCustomDPOTransform(Transform):
    """自定义DPO数据转换"""
    
    def __init__(self, train_on_input: bool = False):
        self.train_on_input = train_on_input
    
    def __call__(self, sample: Mapping[str, Any]) -> Mapping[str, Any]:
        # 从你的数据格式中提取chosen和rejected
        # 假设你的格式是：
        # {
        #   "question": "...",
        #   "answer_good": "...",
        #   "answer_bad": "..."
        # }
        
        question = sample["question"]
        good_answer = sample["answer_good"]
        bad_answer = sample["answer_bad"]
        
        # 转换为Message格式
        chosen_messages = [
            Message(role="user", content=question, masked=not self.train_on_input),
            Message(role="assistant", content=good_answer, masked=False)
        ]
        
        rejected_messages = [
            Message(role="user", content=question, masked=not self.train_on_input),
            Message(role="assistant", content=bad_answer, masked=False)
        ]
        
        return {"chosen": chosen_messages, "rejected": rejected_messages}
```

**步骤2**: 创建自定义数据集函数 `my_dataset.py`:

```python
from torchtune.datasets import PreferenceDataset
from my_transform import MyCustomDPOTransform

def my_custom_dpo_dataset(
    tokenizer,
    *,
    source: str,
    train_on_input: bool = False,
    **load_dataset_kwargs
):
    message_transform = MyCustomDPOTransform(train_on_input=train_on_input)
    
    return PreferenceDataset(
        source=source,
        message_transform=message_transform,
        tokenizer=tokenizer,
        **load_dataset_kwargs
    )
```

**步骤3**: 在配置文件中使用：

```yaml
dataset:
  _component_: my_dataset.my_custom_dpo_dataset
  source: json
  data_files: ./my_custom_data.json
  train_on_input: False
  split: train
```

### 方法3: 直接使用PreferenceDataset类

```python
from torchtune.datasets import PreferenceDataset
from torchtune.data import ChosenRejectedToMessages
from my_transform import MyCustomDPOTransform

# 使用标准transform
dataset = PreferenceDataset(
    source="json",
    data_files="./my_data.json",
    message_transform=ChosenRejectedToMessages(
        train_on_input=False,
        column_map={"chosen": "my_chosen_col", "rejected": "my_rejected_col"}
    ),
    tokenizer=tokenizer,
    split="train"
)

# 或使用自定义transform
dataset = PreferenceDataset(
    source="json",
    data_files="./my_data.json",
    message_transform=MyCustomDPOTransform(train_on_input=False),
    tokenizer=tokenizer,
    split="train"
)
```

## 完整配置示例

### 示例1: 本地JSON文件

```yaml
dataset:
  _component_: torchtune.datasets.preference_dataset
  source: json
  data_files: ./data/my_dpo_dataset.json
  train_on_input: False
  split: train
```

### 示例2: 本地JSONL文件

```yaml
dataset:
  _component_: torchtune.datasets.preference_dataset
  source: json
  data_files: ./data/my_dpo_dataset.jsonl
  train_on_input: False
  split: train
```

### 示例3: HuggingFace Hub数据集

```yaml
dataset:
  _component_: torchtune.datasets.preference_dataset
  source: "miromind-ai/MiroVerse-v0.1"
  name: "MiroVerse-DPO"
  split: "MuSiQue_8B_DPO"
```

### 示例4: 自定义列名

```yaml
dataset:
  _component_: torchtune.datasets.preference_dataset
  source: json
  data_files: ./data/custom_format.json
  column_map:
    chosen: good_answer
    rejected: bad_answer
  train_on_input: False
  split: train
```

### 示例5: 添加系统提示词

```yaml
dataset:
  _component_: torchtune.datasets.preference_dataset
  source: json
  data_files: ./data/my_dpo_dataset.json
  new_system_prompt: "You are a helpful assistant."
  train_on_input: False
  split: train
```

### 示例6: 数据过滤

```yaml
dataset:
  _component_: torchtune.datasets.preference_dataset
  source: json
  data_files: ./data/my_dpo_dataset.json
  train_on_input: False
  split: train
  # 可以通过filter_fn过滤数据（需要在代码中定义）
```

## 数据预处理流程

1. **加载数据**: 使用`datasets.load_dataset()`加载
2. **转换消息**: `message_transform`将原始数据转换为`Message`列表
3. **Tokenization**: 将`Message`列表tokenize为token IDs
4. **生成Labels**: 根据masking策略生成labels（-100表示不计算loss）
5. **Collate**: `padded_collate_dpo`将batch中的chosen和rejected拼接并padding

## 注意事项

1. **列名要求**: 数据必须包含`chosen`和`rejected`列（或通过`column_map`映射）
2. **对话格式**: 每列必须是消息列表，每个消息包含`role`和`content`
3. **角色支持**: 支持`system`、`user`、`assistant`等角色
4. **Masking策略**: 
   - `train_on_input=False` (默认): 只在assistant回复上计算loss
   - `train_on_input=True`: 在prompt和回复上都计算loss
5. **多轮对话**: 支持多轮对话，但chosen和rejected的prompt部分必须相同

## 验证数据集

创建测试脚本验证数据集格式：

```python
from datasets import load_dataset
from torchtune.datasets import preference_dataset
from torchtune.modules.transforms.tokenizers import get_tokenizer

# 加载tokenizer
tokenizer = get_tokenizer("your_model_path")

# 加载数据集
dataset = preference_dataset(
    tokenizer=tokenizer,
    source="json",
    data_files="./my_data.json",
    train_on_input=False
)

# 检查第一个样本
sample = dataset[0]
print("Chosen input IDs:", sample["chosen_input_ids"][:20])
print("Rejected input IDs:", sample["rejected_input_ids"][:20])
print("Chosen labels:", sample["chosen_labels"][:20])
print("Rejected labels:", sample["rejected_labels"][:20])
```

## 常见问题

**Q: 我的数据是单轮对话，格式是prompt-chosen-rejected，怎么办？**
A: 可以使用`StackExchangePairedToMessages` transform，或参考`torchtune/torchtune/datasets/_stack_exchange_paired.py`创建类似的transform。

**Q: 如何添加数据过滤？**
A: 在配置中添加`filter_fn`参数，或在代码中定义过滤函数。

**Q: 支持哪些数据源？**
A: 支持HuggingFace datasets支持的所有格式：JSON、JSONL、CSV、Parquet等，以及HuggingFace Hub上的数据集。

