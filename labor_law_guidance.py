import os
import json
import re
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
        """从AI分析结果中提取所需证据清单
        目标：确保尽可能解析出“全部”证据项，而不是退回单一默认项。
        策略：
        1) 先请求模型“只返回JSON数组”，并尽量用response_format强制JSON；
        2) 解析返回文本中的JSON代码块或方括号片段；
        3) 如果仍失败，则从ai_analysis原始分析文本中回溯解析要点条目，构造结构化清单。
        """
        import re

        def _extract_json_from_text(text: str) -> str | None:
            # 优先提取```json ... ```代码块
            code_block = re.search(r"```json\s*(\[.*?\])\s*```",
                                   text, re.DOTALL | re.IGNORECASE)
            if code_block:
                return code_block.group(1).strip()
            # 其次提取``` ... ```中的数组
            code_block_generic = re.search(r"```\s*(\[.*?\])\s*```",
                                           text, re.DOTALL | re.IGNORECASE)
            if code_block_generic:
                return code_block_generic.group(1).strip()
            # 最后尝试截取第一个'['到最后一个']'之间内容
            start = text.find('[')
            end = text.rfind(']')
            if start != -1 and end != -1 and end > start:
                candidate = text[start:end+1].strip()
                return candidate
            return None

        try:
            # 使用AI提取结构化的证据清单（强约束仅返回JSON）
            system_prompt = (
                "你是资深劳动法证据清单解析器。请从输入的分析文本中提取证据清单，"
                "并且‘只返回’一个JSON数组，不要任何其他文字、解释或Markdown。"
                "数组元素字段：evidence_type, description, legal_requirements, importance, collection_method。"
                "importance 取值限定：'关键证据' | '重要证据' | '辅助证据'。"
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": ai_analysis}
            ]

            # 尝试使用response_format强制JSON（若不支持将抛错，进入fallback）
            try:
                completion = self.client.chat.completions.create(
                    model="qwen-max-latest",
                    messages=messages,
                    temperature=0.1,
                    response_format={"type": "json_object"}  # 期望返回一个对象或数组
                )
                result_text = completion.choices[0].message.content
            except Exception:
                completion = self.client.chat.completions.create(
                    model="qwen-max-latest",
                    messages=messages,
                    temperature=0.1
                )
                result_text = completion.choices[0].message.content

            # 先直接尝试解析
            try:
                parsed = json.loads(result_text)
                # 有的模型在json_object下会返回对象包裹数组，比如{"items": [...]}，做一次展开
                if isinstance(parsed, dict):
                    for k, v in parsed.items():
                        if isinstance(v, list):
                            parsed = v
                            break
                if isinstance(parsed, list):
                    return self._normalize_evidence_items(parsed)
            except Exception:
                pass

            # 从文本中提取JSON片段再解析
            json_snippet = _extract_json_from_text(result_text)
            if json_snippet:
                try:
                    parsed = json.loads(json_snippet)
                    if isinstance(parsed, list):
                        return self._normalize_evidence_items(parsed)
                except Exception:
                    pass

            # 兜底：直接从原始分析文本中解析（通常为Markdown要点列表）
            fallback_items = self._fallback_parse_evidence_from_text(ai_analysis)
            if fallback_items:
                return self._normalize_evidence_items(fallback_items)

            # 仍失败，保底返回多项常见证据而非单项
            return self._normalize_evidence_items([
                {
                    "evidence_type": "劳动合同",
                    "description": "证明劳动关系存在的基础文件",
                    "legal_requirements": "需双方签字盖章、LOADED/签署，真实性、合法性、关联性",
                    "importance": "关键证据",
                    "collection_method": "保留原件与清晰复印/扫描件；重点页拍照备份"
                },
                {
                    "evidence_type": "解除劳动合同通知书",
                    "description": "证明解除事实与理由的核心文件",
                    "legal_requirements": "应LOADED解除依据、理由、日期并加盖公司公章；保留送达凭证",
                    "importance": "关键证据",
                    "collection_method": "保留原件/邮寄凭证；如为邮件/系统通知，保留完整截图与元数据"
                },
                {
                    "evidence_type": "工资发放记录",
                    "description": "证明工资标准与已发放情况",
                    "legal_requirements": "银行流水/工资条与期间一致，能够对应至个人账户及发薪主体",
                    "importance": "重要证据",
                    "collection_method": "下载银行流水、保存工资条/邮件，必要时向财务索取盖章证明"
                },
                {
                    "evidence_type": "社保缴纳记录",
                    "description": "辅助证明劳动关系与用工主体",
                    "legal_requirements": "社保缴费明细与任职期间对应，显示单位名称与缴费基数",
                    "importance": "重要证据",
                    "collection_method": "人社App/线下大厅打印缴费明细，保留电子与纸质版"
                },
                {
                    "evidence_type": "绩效考核记录",
                    "description": "反驳“不能胜任”或证明绩效水平",
                    "legal_requirements": "来源客观、形成于争议前，能对应期间与岗位",
                    "importance": "重要证据",
                    "collection_method": "导出系统记录、保存邮件与截图，标注日期与来源"
                }
            ])

        except Exception as e:
            print(f"提取证据清单失败: {e}")
            return []

    # 辅助：从自然语言/Markdown分析文本中回溯解析证据项
    def _fallback_parse_evidence_from_text(self, text: str) -> List[Dict]:
        import re
        items: List[Dict] = []

        # 通过常见模式提取形如 “- **证据名**：描述” 的条目
        pattern = re.compile(r"^\s*[-\u2022]\s*\*\*(.+?)\*\*\s*[:：]\s*(.+?)\s*$",
                             re.MULTILINE)
        matches = pattern.findall(text)
        for name, desc in matches:
            items.append({
                "evidence_type": name.strip(),
                "description": desc.strip(),
            })

        # 如未匹配，退而求其次，匹配 “- 证据名：描述”
        if not items:
            pattern2 = re.compile(r"^\s*[-\u2022]\s*(.+?)\s*[:：]\s*(.+?)\s*$",
                                  re.MULTILINE)
            for name, desc in pattern2.findall(text):
                # 排除小节标题等非证据行
                if len(name) > 20:  # 粗略过滤：证据名一般不太长
                    continue
                items.append({
                    "evidence_type": name.strip().strip('《》'),
                    "description": desc.strip(),
                })

        # 为每项补齐默认字段（importance等后续统一归一）
        return items

    # 辅助：规范化、补全证据项的字段
    def _normalize_evidence_items(self, items: List[Dict]) -> List[Dict]:
        def default_by_type(name: str) -> Dict[str, str]:
            name = name.strip().strip('《》')
            mapping = {
                "劳动合同": {
                    "importance": "关键证据",
                    "legal_requirements": "需双方签字盖章、条款完整，真实性、合法性、关联性",
                    "collection_method": "保留原件与复印件，关键页拍照留存"
                },
                "解除劳动合同通知书": {
                    "importance": "关键证据",
                    "legal_requirements": "写明理由/依据/日期并加盖公章，保留送达凭证",
                    "collection_method": "保留原件/截图与邮件头信息，保存邮寄凭证"
                },
                "社保缴纳记录": {
                    "importance": "重要证据",
                    "legal_requirements": "明示单位名称、基数与缴费期间，能对应任职时段",
                    "collection_method": "人社App/大厅打印缴费明细"
                },
                "工资发放记录": {
                    "importance": "重要证据",
                    "legal_requirements": "银行流水与发薪记录一致，能对应个人账户与发薪主体",
                    "collection_method": "下载流水/保存工资条，必要时开具收入证明"
                },
                "绩效考核记录": {
                    "importance": "重要证据",
                    "legal_requirements": "来源客观、形成于争议前，能对应期间与岗位",
                    "collection_method": "导出系统记录、保存邮件与截图"
                },
                "培训或调岗记录": {
                    "importance": "重要证据",
                    "legal_requirements": "LOADED培训/调岗时间、原因、岗位及确认方式",
                    "collection_method": "保留OA/邮件/通知截图，向HR索取相关记录"
                },
                "入职证明": {
                    "importance": "辅助证据",
                    "legal_requirements": "能反映入职日期与岗位信息",
                    "collection_method": "用人单位开具，或以合同首页/登记表替代"
                },
                "月工资证明": {
                    "importance": "重要证据",
                    "legal_requirements": "能反映最近12个月平均工资及构成",
                    "collection_method": "银行流水+工资条/HR盖章证明"
                },
                "年假政策文件": {
                    "importance": "辅助证据",
                    "legal_requirements": "公司正式制度/员工手册生效并公示",
                    "collection_method": "下载制度/手册PDF或盖章纸质版"
                },
                "未休年假记录": {
                    "importance": "重要证据",
                    "legal_requirements": "能反映未休天数、期间与审批状态",
                    "collection_method": "系统截图/考勤导出，邮件确认"
                },
                "聊天记录": {
                    "importance": "辅助证据",
                    "legal_requirements": "来源真实、未篡改，能反映沟通事实",
                    "collection_method": "导出微信/企微聊天，保留原文件与时间戳"
                },
                "公司内部文件": {
                    "importance": "辅助证据",
                    "legal_requirements": "与岗位/考核/制度直接相关，来源可追溯",
                    "collection_method": "保存岗位说明书、考核标准等，并注明来源"
                },
            }
            base = mapping.get(name, {
                "importance": "重要证据",
                "legal_requirements": "满足真实性、合法性、关联性三性，注意形成时间与来源",
                "collection_method": "保留原件/截图与电子版备份，必要时向单位申请证明"
            })
            return base

        normalized: List[Dict] = []
        for raw in items:
            name = (raw.get("evidence_type") or raw.get("name") or "").strip()
            if not name:
                # 没有名称则跳过
                continue
            defaults = default_by_type(name)
            normalized.append({
                "evidence_type": name.strip().strip('《》'),
                "description": raw.get("description") or raw.get("desc") or "",
                "legal_requirements": raw.get("legal_requirements") or defaults["legal_requirements"],
                "importance": raw.get("importance") or defaults["importance"],
                "collection_method": raw.get("collection_method") or defaults["collection_method"],
            })

        # 去重（按 evidence_type）并保持顺序
        seen = set()
        deduped: List[Dict] = []
        for it in normalized:
            key = it["evidence_type"]
            if key in seen:
                continue
            seen.add(key)
            deduped.append(it)
        return deduped


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
        """解析用户输入的证据材料，仅从用户输入中提取其“已持有/部分持有”的证据。
        - 仅返回用户声称持有（完整或部分）的证据项；不为未提及或明确否定的证据填充“否”，
          以便后续通过“未在字典中”判定为缺失并提供取证建议。
        - 具备更稳健的否定、部分与肯定识别，避免“没有劳动合同”被误判为持有。
        """
        result: Dict[str, Dict] = {}
        text = (user_input or "").strip()
        if not text:
            return result

        # 将输入拆分为若干语句，便于就近判断否定/部分/肯定语义
        seps = "，,。.;；!！?？\n"
        sentences: List[str] = []
        buf = ""
        for ch in text:
            buf += ch
            if ch in seps:
                sentences.append(buf.strip())
                buf = ""
        if buf.strip():
            sentences.append(buf.strip())

        negative_markers = ["没有", "没", "未", "无", "缺", "不在手上", "没带", "未拿到", "没拿到", "未收到", "没收到", "找不到", "丢了", "未签", "没签"]
        partial_markers = ["部分", "不完整", "缺少", "只有", "复印件", "电子版", "截图", "影印件", "缺页", "仅有", "照片", "部分月份", "部分记录"]
        positive_markers = ["有", "持有", "在手上", "拿到", "收到", "保存", "留存", "具备", "已经", "已", "现有", "手里有", "手上有", "可以提供"]

        # 常见证据别名映射（在不改变 evidence_list 的前提下增强匹配能力）
        alias_map: Dict[str, List[str]] = {
            "劳动合同": ["书面劳动合同", "劳动合同书", "合同", "劳动协议", "聘用合同", "入职合同"],
            "解除劳动合同通知书": ["解雇通知", "解除通知", "辞退通知", "解除劳动合同通知", "解聘通知", "开除通知"],
            "工资条": ["工资发放记录", "薪资条", "工资单", "薪资单", "发薪记录", "薪酬记录", "工资条截图"],
            "社保缴纳记录": ["社保记录", "社保缴费记录", "社保明细", "社保清单", "五险缴费记录", "参保记录"],
            "考勤记录": ["打卡记录", "门禁记录", "排班记录", "出勤记录", "工时记录", "加班记录"],
            "培训或调岗记录": ["培训记录", "培训证明", "调岗通知", "岗位调整记录", "岗位变更记录", "调岗函"],
            "未休年假记录": ["年假记录", "年休假记录", "带薪年假记录", "年假余额", "假期记录"],
        }

        def gen_aliases(name: str) -> List[str]:
            # 基于原名称生成一些简化别名
            base = [name]
            simplified = name
            for suf in ["书", "通知书", "证明", "记录", "材料", "清单", "合同书", "协议书", "说明"]:
                simplified = simplified.replace(suf, "")
            simplified = simplified.strip()
            if simplified and simplified != name:
                base.append(simplified)
            # 合并预置别名
            if name in alias_map:
                base.extend(alias_map[name])
            # 去重并按长度降序，优先匹配更长更具体的别名
            dedup = []
            seen = set()
            for a in base:
                a = a.strip()
                if a and a not in seen:
                    seen.add(a)
                    dedup.append(a)
            dedup.sort(key=len, reverse=True)
            return dedup

        def sentence_has_marker(sent: str, markers: List[str]) -> bool:
            return any(m in sent for m in markers)

        for evidence in evidence_list:
            etype = evidence.get("evidence_type", "").strip()
            if not etype:
                continue
            aliases = gen_aliases(etype)
            status_for_item = None  # None/"是"/"部分"
            matched_sentence = None

            for sent in sentences:
                # 如果该句未涉及任何别名则跳过
                alias_hit = None
                for al in aliases:
                    if al and al in sent:
                        alias_hit = al
                        break
                if not alias_hit:
                    continue

                # 若出现明确否定，且无明显肯定，视为未持有（不记录到结果中）
                neg = sentence_has_marker(sent, negative_markers)
                pos = sentence_has_marker(sent, positive_markers)
                part = sentence_has_marker(sent, partial_markers)

                # 更细的就近否定判断：别名前 6 个字符内若出现否定词，也视为否定
                try:
                    idx = sent.index(alias_hit)
                    window = sent[max(0, idx-6):idx]
                    if any(m in window for m in negative_markers):
                        neg = True
                except ValueError:
                    pass

                if neg and not pos:
                    # 明确表示没有该证据 -> 不纳入已持有清单
                    continue

                # 有肯定或未否定且被提及，结合是否部分的描述
                if part:
                    status_for_item = "部分"
                else:
                    status_for_item = "是"
                matched_sentence = sent
                break  # 该证据已归类，无需再看其他句子

            if status_for_item:
                result[etype] = {
                    "status": status_for_item,
                    "evidence_info": evidence,
                    "details": f"从用户输入中识别：{matched_sentence or ''}".strip()
                }

        return result
    
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
        print(evidence_list)
        
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