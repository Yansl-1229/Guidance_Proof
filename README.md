# 劳动法维权举证指导功能

## 功能概述

本项目提供了一个基于AI的命令行交互式劳动法维权举证指导功能，能够：

1. **智能案例分析**：基于劳动争议对话历史，使用Qwen-max-latest模型分析案例
2. **证据清单生成**：自动生成劳动者申请仲裁或诉讼时需要的具体材料清单
3. **交互式证据核查**：通过对话询问用户当前持有的证据材料
4. **法律要件指导**：明确告知证据需要满足的法律要件
5. **个性化取证建议**：针对缺失证据提供具体的取证方法和建议

## 文件结构

```
Guidance_Proof/
├── labor_law_guidance.py    # 主功能模块
├── example_usage.py         # 使用示例
├── Qwen_API.py             # Qwen模型调用示例
├── conversation.json        # 劳动争议对话历史样本
└── README.md               # 说明文档
```

## 环境要求

### Python环境
- Python 3.7+
- 推荐使用conda环境：AILaborLawyer

### 依赖库
```bash
pip install openai
```

### API配置
需要配置阿里云百炼API密钥：
```bash
# Windows
set DASHSCOPE_API_KEY=your_api_key_here

# Linux/Mac
export DASHSCOPE_API_KEY=your_api_key_here
```

## 核心功能函数

### `labor_law_guidance_main(conversation_file="conversation.json")`

**主要功能函数**，提供完整的劳动法维权举证指导流程。

**参数：**
- `conversation_file` (str): 对话历史文件路径，默认为"conversation.json"

**功能流程：**
1. 加载劳动争议对话历史
2. AI分析案例并生成证据清单
3. 交互式询问用户已有证据
4. 评估证据质量和法律要件
5. 提供个性化取证建议

## 使用方法

### 方法一：直接调用主函数

```python
from labor_law_guidance import labor_law_guidance_main

# 使用默认对话文件
labor_law_guidance_main()

# 使用自定义对话文件
labor_law_guidance_main("my_conversation.json")
```

### 方法二：使用类实例（高级用法）

```python
from labor_law_guidance import LaborLawGuidance

# 创建指导系统实例
guidance = LaborLawGuidance()

# 运行完整会话
guidance.run_guidance_session("conversation.json")

# 或者分步骤使用
if guidance.load_conversation_history("conversation.json"):
    analysis = guidance.analyze_case_with_ai(guidance.conversation_history)
    evidence_list = guidance.extract_required_evidence(analysis)
    # ... 继续其他操作
```

### 方法三：运行示例程序

```bash
# 运行交互式示例菜单
python example_usage.py

# 直接运行主程序
python labor_law_guidance.py
```

## 对话历史文件格式

系统支持以下JSON格式的对话历史文件：

```json
[
  {
    "conversations": [
      {
        "from": "human",
        "value": "用户输入内容"
      },
      {
        "from": "gpt",
        "value": "AI回复内容"
      }
    ]
  }
]
```

## 功能特点

### 1. 智能案例分析
- 基于真实劳动争议对话历史
- 使用Qwen-max-latest模型进行专业分析
- 识别争议焦点和案例类型

### 2. 结构化证据管理
- 自动生成证据材料清单
- 按重要性分级（关键证据/重要证据/辅助证据）
- 明确法律要件和证明标准

### 3. 交互式用户体验
- 命令行友好界面
- 逐项核查用户已有证据
- 实时评估证据质量

### 4. 个性化指导建议
- 基于用户实际情况
- 提供具体取证方法
- 评估维权成功可能性

## 使用示例

### 完整使用流程

```python
# 1. 导入功能
from labor_law_guidance import labor_law_guidance_main

# 2. 确保环境变量已设置
import os
if not os.getenv("DASHSCOPE_API_KEY"):
    print("请设置DASHSCOPE_API_KEY环境变量")
    exit()

# 3. 运行指导会话
labor_law_guidance_main("conversation.json")
```

### 交互过程示例

```
============================================================
         劳动法维权举证指导系统
============================================================

正在加载案例数据...
✅ 案例数据加载成功

正在分析案例...

=== 案例分析结果 ===
根据对话分析，这是一起违法解除劳动合同纠纷...

=== 证据材料核查 ===
请告诉我您目前已经持有哪些证据材料：

1. 劳动合同 - 证明劳动关系存在的基础文件
   重要性: 关键证据
   法律要件: 需要双方签字盖章，内容完整

您是否持有此类证据？(是/否/部分): 是
请简要描述您持有的具体材料: 有完整的劳动合同原件

证据质量评估: 符合法律要件，建议保留原件...
```

## 注意事项

1. **API配置**：确保正确设置DASHSCOPE_API_KEY环境变量
2. **网络连接**：需要稳定的网络连接访问AI服务
3. **文件路径**：确保对话历史文件路径正确
4. **专业建议**：本系统提供初步指导，重要案件建议咨询专业律师

## 错误处理

系统包含完善的错误处理机制：
- API调用失败时的重试机制
- 文件加载异常处理
- 用户输入验证
- 网络连接异常提示

## 扩展功能

### 自定义证据类型
可以通过修改`LaborLawGuidance`类来添加特定类型的证据分析：

```python
class CustomLaborLawGuidance(LaborLawGuidance):
    def analyze_specific_case_type(self, case_type):
        # 添加特定案例类型的分析逻辑
        pass
```

### 批量处理
可以扩展为批量处理多个案例：

```python
def batch_guidance(file_list):
    for file_path in file_list:
        labor_law_guidance_main(file_path)
```

## 技术架构

- **AI模型**：阿里云百炼 Qwen-max-latest
- **API接口**：OpenAI兼容接口
- **数据格式**：JSON格式对话历史
- **交互方式**：命令行界面
- **编程语言**：Python 3.7+

## 版本信息

- 版本：1.0.0
- 更新日期：2024年
- 作者：AI Assistant
- 许可证：MIT License

## 联系支持

如有问题或建议，请通过以下方式联系：
- 提交Issue到项目仓库
- 发送邮件至技术支持
- 查看项目文档和FAQ

---

**免责声明**：本系统仅提供法律信息参考，不构成正式法律建议。重要法律事务请咨询专业律师。