#!/usr/bin/env python3
"""測試 MCP 工具名稱解析優化"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.mcp_client import MCPClientManager
from src.core.config import MCPConfig

def test_mcp_optimization():
    """測試 MCP 工具名稱解析優化"""
    print("🧪 測試 MCP 工具名稱解析優化...")
    
    manager = MCPClientManager()
    
    # 添加一些模擬的 MCP 服務器配置
    configs = [
        MCPConfig(name="server1", command="echo", args=["test1"]),
        MCPConfig(name="server2", command="echo", args=["test2"]),
        MCPConfig(name="long_server_name", command="echo", args=["test3"]),
    ]
    
    # 手動添加到管理器（不需要實際連接）
    for config in configs:
        manager._connections[config.name] = None  # Mock connection
        manager._server_configs[config.name] = config
        prefix = f"{config.name}_"
        manager._tool_prefix_map[prefix] = config.name
    
    print(f"✅ 添加了 {len(configs)} 個 MCP 服務器")
    print(f"✅ 前綴映射: {manager._tool_prefix_map}")
    
    # 測試工具名稱解析
    test_cases = [
        ("server1_test_tool", "server1", "test_tool"),
        ("server2_another_tool", "server2", "another_tool"),
        ("long_server_name_special_tool", "long_server_name", "special_tool"),
        ("nonexistent_tool", None, "nonexistent_tool"),
        ("", None, None),
        (None, None, None),
    ]
    
    print("\n🔍 測試工具名稱解析:")
    all_passed = True
    
    for tool_name, expected_server, expected_tool in test_cases:
        server, tool = manager.resolve_tool_name(tool_name)
        
        if server == expected_server and tool == expected_tool:
            print(f"✅ '{tool_name}' -> ({server}, '{tool}')")
        else:
            print(f"❌ '{tool_name}' -> 期望 ({expected_server}, '{expected_tool}'), 實際 ({server}, '{tool}')")
            all_passed = False
    
    # 性能測試
    print("\n⚡ 性能測試:")
    test_tool = "server1_performance_test"
    iterations = 10000
    
    start_time = time.time()
    for _ in range(iterations):
        manager.resolve_tool_name(test_tool)
    end_time = time.time()
    
    avg_time = (end_time - start_time) / iterations * 1000000  # microseconds
    print(f"✅ {iterations} 次解析平均耗時: {avg_time:.2f} μs")
    
    if avg_time < 100:  # Should be very fast now
        print("✅ 性能優化成功！")
    else:
        print("⚠️  性能可能需要進一步優化")
    
    # 測試移除服務器
    print("\n🗑️  測試服務器移除:")
    manager._connections.pop("server1", None)
    manager._server_configs.pop("server1", None)
    prefix = "server1_"
    manager._tool_prefix_map.pop(prefix, None)
    
    server, tool = manager.resolve_tool_name("server1_test_tool")
    if server is None and tool == "server1_test_tool":
        print("✅ 服務器移除後正確處理工具名稱")
    else:
        print(f"❌ 服務器移除後處理錯誤: ({server}, '{tool}')")
        all_passed = False
    
    if all_passed:
        print("\n✅ MCP 工具名稱解析優化測試通過！")
        return True
    else:
        print("\n❌ MCP 工具名稱解析優化測試失敗！")
        return False

if __name__ == "__main__":
    test_mcp_optimization()
