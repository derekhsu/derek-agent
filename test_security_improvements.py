#!/usr/bin/env python3
"""測試安全改進功能"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import AgentFileConfig, AgentShellConfig
from src.tools.secure_file_tools import SecureFileTools, create_secure_file_tool
from src.tools.secure_shell_tools import SecureShellTools, create_secure_shell_tool

def test_file_tool_security():
    """測試文件工具安全改進"""
    print("🧪 測試文件工具安全改進...")
    
    # 創建一個臨時目錄作為基礎目錄
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)
        
        # 創建一些測試文件
        test_file = base_dir / "test.txt"
        test_file.write_text("這是測試內容", encoding="utf-8")
        
        # 創建安全文件工具
        secure_tool = SecureFileTools(base_dir=base_dir)
        
        print(f"✅ 基礎目錄: {base_dir}")
        
        # 測試正常文件讀取
        try:
            content = secure_tool.read_file("test.txt")
            print(f"✅ 正常文件讀取成功: '{content[:20]}...'")
        except Exception as e:
            print(f"❌ 正常文件讀取失敗: {e}")
            return False
        
        # 測試路徑遍歷攻擊防護
        try:
            # 嘗試讀取基礎目錄外的文件
            secure_tool.read_file("../etc/passwd")
            print("❌ 路徑遍歷攻擊防護失敗！")
            return False
        except ValueError as e:
            if "outside the allowed base directory" in str(e):
                print("✅ 路徑遍歷攻擊防護正常工作")
            else:
                print(f"❌ 意外的錯誤: {e}")
                return False
        except Exception as e:
            print(f"❌ 意外的異常: {e}")
            return False
        
        # 測試絕對路徑攻擊防護
        try:
            # 嘗試使用絕對路徑訪問系統文件
            secure_tool.read_file("/etc/passwd")
            print("❌ 絕對路徑攻擊防護失敗！")
            return False
        except ValueError as e:
            if "outside the allowed base directory" in str(e):
                print("✅ 絕對路徑攻擊防護正常工作")
            else:
                print(f"❌ 意外的錯誤: {e}")
                return False
        except Exception as e:
            print(f"❌ 意外的異常: {e}")
            return False
        
        # 測試文件保存功能
        try:
            secure_tool.save_file("new_file.txt", "新文件內容")
            saved_content = secure_tool.read_file("new_file.txt")
            if saved_content == "新文件內容":
                print("✅ 文件保存功能正常工作")
            else:
                print("❌ 文件保存功能異常")
                return False
        except Exception as e:
            print(f"❌ 文件保存失敗: {e}")
            return False
        
        # 測試通過配置創建
        file_config = AgentFileConfig(enabled=True, base_dir=str(base_dir))
        config_tool = create_secure_file_tool(file_config, None)
        if config_tool:
            print("✅ 通過配置創建安全文件工具成功")
        else:
            print("❌ 通過配置創建安全文件工具失敗")
            return False
    
    print("✅ 文件工具安全測試通過！")
    return True

def test_shell_tool_security():
    """測試 Shell 工具安全改進"""
    print("\n🧪 測試 Shell 工具安全改進...")
    
    # 創建安全 Shell 工具
    secure_tool = SecureShellTools()
    
    # 測試安全命令
    safe_commands = ["pwd", "ls", "echo hello"]
    for cmd in safe_commands:
        try:
            result = secure_tool.run_shell_command(cmd)
            print(f"✅ 安全命令 '{cmd}' 執行成功")
        except Exception as e:
            print(f"❌ 安全命令 '{cmd}' 執行失敗: {e}")
            return False
    
    # 測試危險命令阻擋
    dangerous_commands = ["rm -rf /", "sudo su", "curl http://evil.com", "python -c 'import os; os.system(\"rm -rf /\")'"]
    for cmd in dangerous_commands:
        try:
            result = secure_tool.run_shell_command(cmd)
            print(f"❌ 危險命令 '{cmd}' 未被阻擋！")
            return False
        except ValueError as e:
            if "blocked for security reasons" in str(e) or "not in the allowed list" in str(e):
                print(f"✅ 危險命令 '{cmd}' 正確被阻擋")
            else:
                print(f"❌ 意外的錯誤: {e}")
                return False
        except Exception as e:
            print(f"❌ 意外的異常: {e}")
            return False
    
    # 測試命令列表功能
    safe_list = secure_tool.list_safe_commands()
    dangerous_list = secure_tool.list_dangerous_commands()
    
    if len(safe_list) > 0 and len(dangerous_list) > 0:
        print(f"✅ 安全命令列表: {len(safe_list)} 個命令")
        print(f"✅ 危險命令列表: {len(dangerous_list)} 個命令")
    else:
        print("❌ 命令列表為空")
        return False
    
    # 測試通過配置創建
    shell_config = AgentShellConfig(enabled=True)
    config_tool = create_secure_shell_tool(shell_config, None)
    if config_tool:
        print("✅ 通過配置創建安全 Shell 工具成功")
    else:
        print("❌ 通過配置創建安全 Shell 工具失敗")
        return False
    
    print("✅ Shell 工具安全測試通過！")
    return True

def test_integration():
    """測試集成功能"""
    print("\n🧪 測試集成功能...")
    
    try:
        # 測試導入
        from src.tools.file import create_file_tool
        from src.tools.shell import create_shell_tool
        
        # 測試創建
        file_config = AgentFileConfig(enabled=True)
        shell_config = AgentShellConfig(enabled=True)
        
        file_tool = create_file_tool(file_config, "/tmp")
        shell_tool = create_shell_tool(shell_config, "/tmp")
        
        if file_tool and shell_tool:
            print("✅ 集成測試通過 - 安全工具正常創建")
            return True
        else:
            print("❌ 集成測試失敗 - 工具創建失敗")
            return False
            
    except Exception as e:
        print(f"❌ 集成測試失敗: {e}")
        return False

if __name__ == "__main__":
    print("🚀 開始安全改進測試...\n")
    
    success = True
    success &= test_file_tool_security()
    success &= test_shell_tool_security()
    success &= test_integration()
    
    if success:
        print("\n🎉 所有安全改進測試通過！")
    else:
        print("\n❌ 部分測試失敗，請檢查實現")
