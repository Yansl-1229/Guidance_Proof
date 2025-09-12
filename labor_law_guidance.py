import os
import json
from openai import OpenAI
from typing import List, Dict, Any


class LaborLawGuidance:
    """劳动法维权举证指导系统"""
    
    def __init__(self):
        """初始化系统"""
        self.client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.conversation_history = []
        self.user_evidence = {}
        self.required_evidence = []
        
    def load_conversation_history(self, file_path: str) -> bool:
        """加载对话历史文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    self.conversation_history = data[0].get('conversations', [])
                    return True
                return False
        except Exception as e:
            print(f"加载对话历史失败: {e}")
            return False
    
    def analyze_case_with_ai(self, conversation_data: List[Dict]) -> str:
        """使用AI分析劳动争议案例"""
        try:
            # 构建对话内容
            conversation_text = ""
            for msg in conversation_data:
                role = "用户" if msg['from'] == 'human' else "律师"
                conversation_text += f"{role}: {msg['value']}\n\n"
            
            system_prompt = """
            你是一位专业的劳动法律师，请基于以下劳动争议对话历史，分析案例并提供以下信息：
            
            1. 案例类型和争议焦点
            2. 劳动者申请仲裁或诉讼时需要准备的具体证据材料清单
            3. 每类证据的法律要件和证明标准
            4. 证据的重要性等级（关键证据/重要证据/辅助证据）
            
            请以结构化的方式回答，便于后续的交互式指导。
            """
            
            completion = self.client.chat.completions.create(
                model="qwen-max-latest",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请分析以下劳动争议对话：\n\n{conversation_text}"}
                ],
                temperature=0.3
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            return f"AI分析失败: {e}"
    
    def extract_required_evidence(self, ai_analysis: str) -> List[Dict]:
        """从AI分析结果中提取所需证据清单"""
        try:
            # 使用AI提取结构化的证据清单
            system_prompt = """
            请从以下分析结果中提取证据清单，并以JSON格式返回，格式如下：
            [
                {
                    "evidence_type": "证据类型",
                    "description": "证据描述",
                    "legal_requirements": "法律要件",
                    "importance": "关键证据/重要证据/辅助证据",
                    "collection_method": "取证方法建议"
                }
            ]
            """
            
            completion = self.client.chat.completions.create(
                model="qwen-max-latest",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": ai_analysis}
                ],
                temperature=0.1
            )
            
            result = completion.choices[0].message.content
            # 尝试解析JSON
            try:
                return json.loads(result)
            except:
                # 如果JSON解析失败，返回基本格式
                return [{
                    "evidence_type": "劳动合同",
                    "description": "证明劳动关系存在的基础文件",
                    "legal_requirements": "需要双方签字盖章，内容完整",
                    "importance": "关键证据",
                    "collection_method": "保留原件和复印件"
                }]
                
        except Exception as e:
            print(f"提取证据清单失败: {e}")
            return []
    
    def interactive_evidence_check(self, evidence_list: List[Dict]) -> Dict:
        """交互式证据核查 - 专业化两轮律师对话流程"""
        
        # 第一轮对话：律师列出证据清单并询问用户持有情况
        print("\n=== 律师证据指导 ===")
        print("\n律师：根据案情分析，您需要准备以下关键证据：\n")
        
        # 详细列出所需证据清单
        for i, evidence in enumerate(evidence_list, 1):
            importance_icon = "🔴" if evidence['importance'] == '关键证据' else "🟡" if evidence['importance'] == '重要证据' else "🟢"
            print(f"{i}. {importance_icon} {evidence['evidence_type']} ({evidence['importance']})")
            print(f"   作用：{evidence['description']}")
            print(f"   法律要件：{evidence['legal_requirements']}")
            print()
        
        print("律师：请问您目前手上有哪些证据材料？")
        print("（请直接输入您持有的证据材料，例如：我目前持有书面劳动合同、解除劳动合同通知书）")
        
        # 用户自由输入持有的证据
        user_input = input("\n您的回答：").strip()
        
        # 解析用户输入，匹配证据类型
        user_evidence = self._parse_user_evidence_input(user_input, evidence_list)
        
        # 第二轮对话：律师确认并分析现有证据，提供缺失证据的取证建议
        print("\n" + "=" * 60)
        print("\n律师：已确认您现有的证据材料。让我为您进行专业分析：\n")
        
        # 确认用户现有证据
        owned_evidence = [k for k, v in user_evidence.items() if v['status'] in ['是', '部分']]
        if owned_evidence:
            print("✅ 您目前持有的证据：")
            for evidence_type in owned_evidence:
                status_text = "完整" if user_evidence[evidence_type]['status'] == '是' else "部分"
                print(f"   • {evidence_type} ({status_text})")
            print()
        
        # 针对现有证据进行关键条款分析
        if owned_evidence:
            print("📋 针对这些材料，需要重点关注：")
            for evidence_type in owned_evidence:
                evidence_info = user_evidence[evidence_type]['evidence_info']
                analysis = self._analyze_evidence_key_points(evidence_type, evidence_info)
                print(f"\n• {evidence_type}中的关键要点：")
                print(f"  {analysis}")
        
        # 对于缺失的证据，提供具体取证方法
        missing_evidence = [evidence for evidence in evidence_list 
                          if evidence['evidence_type'] not in user_evidence 
                          or user_evidence[evidence['evidence_type']]['status'] == '否']
        
        if missing_evidence:
            print("\n⚠️  对于缺失的证据，建议通过以下方式收集：")
            for evidence in missing_evidence:
                if evidence['importance'] == '关键证据':
                    print(f"\n🔴 {evidence['evidence_type']} (关键证据 - 优先收集)")
                    print(f"   取证方法：{evidence['collection_method']}")
                    print(f"   重要性：{evidence['description']}")
            
            for evidence in missing_evidence:
                if evidence['importance'] in ['重要证据', '辅助证据']:
                    icon = "🟡" if evidence['importance'] == '重要证据' else "🟢"
                    print(f"\n{icon} {evidence['evidence_type']} ({evidence['importance']})")
                    print(f"   取证方法：{evidence['collection_method']}")
        
        print("\n律师：以上是基于您案件情况的专业建议，建议优先收集关键证据以提高维权成功率。")
        
        return user_evidence
    
    def _parse_user_evidence_input(self, user_input: str, evidence_list: List[Dict]) -> Dict:
        """解析用户输入的证据材料"""
        user_evidence = {}
        
        for evidence in evidence_list:
            evidence_type = evidence['evidence_type']
            # 检查用户输入中是否包含该证据类型的关键词
            keywords = [evidence_type, evidence_type.replace('书', ''), evidence_type.replace('材料', ''), 
                       evidence_type.replace('证明', ''), evidence_type.replace('记录', '')]
            
            found = False
            for keyword in keywords:
                if keyword in user_input and len(keyword) > 1:
                    found = True
                    break
            
            if found:
                # 判断是完整持有还是部分持有
                if any(word in user_input for word in ['部分', '不完整', '缺少', '没有完整']):
                    status = '部分'
                else:
                    status = '是'
                
                user_evidence[evidence_type] = {
                    'status': status,
                    'evidence_info': evidence,
                    'details': f"用户提及持有{evidence_type}"
                }
            else:
                user_evidence[evidence_type] = {
                    'status': '否',
                    'evidence_info': evidence
                }
        
        return user_evidence
    
    def _analyze_evidence_key_points(self, evidence_type: str, evidence_info: Dict) -> str:
        """分析证据的关键要点"""
        try:
            system_prompt = f"""
            你是专业的劳动法律师，请针对{evidence_type}这类证据，分析其关键法律要点。
            
            证据信息：{evidence_info}
            
            请简要说明在审查这类证据时需要重点关注的条款或要点，
            以及这些要点对案件的重要意义。回答要专业但通俗易懂，不超过100字。
            """
            
            completion = self.client.chat.completions.create(
                model="qwen-max-latest",
                messages=[
                    {"role": "system", "content": system_prompt}
                ],
                temperature=0.2
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            # 提供默认的关键要点分析
            default_analysis = {
                '劳动合同': '重点关注工作岗位、工资标准、工作时间、合同期限等条款是否明确，以及双方签字盖章是否完整',
                '解除劳动合同通知书': '重点关注解除理由是否合法、程序是否规范、是否提及经济补偿等关键信息',
                '工资条': '重点关注工资构成、发放时间、扣款项目是否合理，以及是否能证明实际工资水平',
                '考勤记录': '重点关注工作时间、加班情况、请假记录是否真实完整，能否证明实际工作状况'
            }
            return default_analysis.get(evidence_type, f'重点关注{evidence_type}的真实性、完整性和法律效力')
    
    def provide_collection_guidance(self, user_evidence: Dict, evidence_list: List[Dict]):
        """提供取证指导"""
        print("\n=== 取证指导建议 ===")
        
        missing_evidence = []
        incomplete_evidence = []
        
        for evidence in evidence_list:
            evidence_type = evidence['evidence_type']
            if evidence_type not in user_evidence:
                missing_evidence.append(evidence)
            elif user_evidence[evidence_type]['status'] in ['否', '部分']:
                incomplete_evidence.append(evidence)
        
        if missing_evidence:
            print("\n【缺失的关键证据】")
            for evidence in missing_evidence:
                if evidence['importance'] == '关键证据':
                    print(f"\n⚠️  {evidence['evidence_type']} (关键证据)")
                    print(f"   作用: {evidence['description']}")
                    print(f"   取证方法: {evidence['collection_method']}")
                    print(f"   法律要件: {evidence['legal_requirements']}")
        
        if incomplete_evidence:
            print("\n【需要完善的证据】")
            for evidence in incomplete_evidence:
                print(f"\n📋 {evidence['evidence_type']}")
                print(f"   完善建议: {evidence['collection_method']}")
        
        # 提供个性化建议
        self.provide_personalized_advice(user_evidence, evidence_list)
    
    def provide_personalized_advice(self, user_evidence: Dict, evidence_list: List[Dict]):
        """提供个性化建议"""
        try:
            # 构建用户证据情况描述
            evidence_summary = ""
            for evidence_type, info in user_evidence.items():
                evidence_summary += f"{evidence_type}: {info['status']}"
                if 'details' in info:
                    evidence_summary += f" ({info['details']})"
                evidence_summary += "\n"
            
            system_prompt = """
            基于用户当前的证据持有情况，请提供个性化的维权建议：
            1. 优先级最高的取证任务
            2. 注意事项和风险提示
            
            请用通俗易懂的语言，给出实用的建议。（不超过200个字）
            """
            
            completion = self.client.chat.completions.create(
                model="qwen-max-latest",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"用户证据情况：\n{evidence_summary}"}
                ],
                temperature=0.3
            )
            
            print("\n=== 个性化维权建议 ===")
            print(completion.choices[0].message.content)
            
        except Exception as e:
            print(f"\n生成个性化建议失败: {e}")
    
    def run_guidance_session(self, conversation_file: str = "conversation.json"):
        """运行完整的指导会话"""
        print("=" * 60)
        print("         劳动法维权举证指导系统")
        print("=" * 60)
        
        # 1. 加载对话历史
        print("\n正在加载案例数据...")
        if not self.load_conversation_history(conversation_file):
            print("❌ 无法加载对话历史文件，请检查文件路径")
            return
        
        print("✅ 案例数据加载成功")
        
        # 2. AI分析案例
        print("\n正在分析案例...")
        ai_analysis = self.analyze_case_with_ai(self.conversation_history)
        print("\n=== 案例分析结果 ===")
        print(ai_analysis)
        
        # 3. 提取证据清单
        print("\n正在生成证据清单...")
        evidence_list = self.extract_required_evidence(ai_analysis)
        
        if not evidence_list:
            print("❌ 无法生成证据清单")
            return
        
        # 4. 交互式证据核查
        user_evidence = self.interactive_evidence_check(evidence_list)
        
        # 5. 提供取证指导
        self.provide_collection_guidance(user_evidence, evidence_list)
        
        print("\n=== 指导会话结束 ===")
        print("如需进一步咨询，建议联系专业律师。")


def labor_law_guidance_main(conversation_file: str = "conversation.json"):
    """劳动法维权举证指导主函数
    
    Args:
        conversation_file: 对话历史文件路径，默认为当前目录下的conversation.json
    
    Returns:
        None
    
    功能说明:
        1. 基于对话历史分析劳动争议案例
        2. 生成所需证据材料清单
        3. 交互式询问用户已有证据
        4. 评估证据质量和法律要件
        5. 提供个性化取证建议
    
    使用示例:
        # 使用默认对话文件
        labor_law_guidance_main()
        
        # 指定对话文件路径
        labor_law_guidance_main("path/to/your/conversation.json")
    """
    try:
        # 检查环境变量
        if not os.getenv("DASHSCOPE_API_KEY"):
            print("❌ 请设置DASHSCOPE_API_KEY环境变量")
            print("   export DASHSCOPE_API_KEY=your_api_key")
            return
        
        # 创建指导系统实例
        guidance_system = LaborLawGuidance()
        
        # 运行指导会话
        guidance_system.run_guidance_session(conversation_file)
        
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
    except Exception as e:
        print(f"\n❌ 系统错误: {e}")
        print("请检查网络连接和API配置")


if __name__ == "__main__":
    # 直接运行时使用默认配置
    labor_law_guidance_main()