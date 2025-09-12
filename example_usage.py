#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
劳动法维权举证指导功能使用示例

本文件展示如何使用labor_law_guidance.py中的功能函数
"""

from labor_law_guidance import labor_law_guidance_main, LaborLawGuidance
import os

def example_basic_usage():
    """基础使用示例"""
    print("=== 基础使用示例 ===")
    print("使用默认的conversation.json文件进行分析")
    
    # 直接调用主函数，使用默认配置
    labor_law_guidance_main()

def example_custom_file():
    """自定义文件路径示例"""
    print("=== 自定义文件路径示例 ===")
    
    # 指定自定义的对话历史文件
    custom_file = "custom_conversation.json"
    
    if os.path.exists(custom_file):
        labor_law_guidance_main(custom_file)
    else:
        print(f"文件 {custom_file} 不存在，使用默认文件")
        labor_law_guidance_main()

def example_class_usage():
    """使用类实例的高级示例"""
    print("=== 类实例使用示例 ===")
    
    # 创建指导系统实例
    guidance = LaborLawGuidance()
    
    # 加载对话历史
    if guidance.load_conversation_history("conversation.json"):
        print("✅ 对话历史加载成功")
        
        # 分析案例
        analysis = guidance.analyze_case_with_ai(guidance.conversation_history)
        print("\n=== AI分析结果 ===")
        print(analysis[:200] + "..." if len(analysis) > 200 else analysis)
        
        # 提取证据清单
        evidence_list = guidance.extract_required_evidence(analysis)
        print(f"\n✅ 提取到 {len(evidence_list)} 项证据要求")
        
        # 可以继续进行交互式会话
        # guidance.run_guidance_session()
    else:
        print("❌ 对话历史加载失败")

def check_environment():
    """检查环境配置"""
    print("=== 环境配置检查 ===")
    
    # 检查API密钥
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if api_key:
        print("✅ DASHSCOPE_API_KEY 已配置")
        print(f"   密钥前缀: {api_key[:10]}...")
    else:
        print("❌ DASHSCOPE_API_KEY 未配置")
        print("   请设置环境变量: export DASHSCOPE_API_KEY=your_api_key")
    
    # 检查对话文件
    if os.path.exists("conversation.json"):
        print("✅ conversation.json 文件存在")
    else:
        print("❌ conversation.json 文件不存在")
    
    # 检查Python环境
    try:
        from openai import OpenAI
        print("✅ openai 库已安装")
    except ImportError:
        print("❌ openai 库未安装")
        print("   请安装: pip install openai")

def interactive_menu():
    """交互式菜单"""
    while True:
        print("\n" + "="*50)
        print("    劳动法维权举证指导系统 - 使用示例")
        print("="*50)
        print("1. 环境配置检查")
        print("2. 基础功能演示")
        print("3. 自定义文件演示")
        print("4. 高级功能演示")
        print("5. 完整指导会话")
        print("0. 退出")
        
        choice = input("\n请选择功能 (0-5): ").strip()
        
        if choice == "0":
            print("再见！")
            break
        elif choice == "1":
            check_environment()
        elif choice == "2":
            try:
                example_basic_usage()
            except Exception as e:
                print(f"执行失败: {e}")
        elif choice == "3":
            try:
                example_custom_file()
            except Exception as e:
                print(f"执行失败: {e}")
        elif choice == "4":
            try:
                example_class_usage()
            except Exception as e:
                print(f"执行失败: {e}")
        elif choice == "5":
            try:
                labor_law_guidance_main()
            except Exception as e:
                print(f"执行失败: {e}")
        else:
            print("无效选择，请重新输入")
        
        input("\n按回车键继续...")

if __name__ == "__main__":
    # 运行交互式菜单
    interactive_menu()