#!/usr/bin/env python3
"""Test that all modules can be imported correctly."""


def test_config_import():
    """Test config module import."""
    from src.core.config import get_config
    print("✓ config module OK")


def test_storage_import():
    """Test storage module import."""
    from src.storage import SQLiteStorage
    print("✓ storage module OK")


def test_core_imports():
    """Test core module imports."""
    from src.core.skills import SkillDirectories
    from src.core.mcp_client import MCPClientManager
    print("✓ skills module OK")
    print("✓ mcp_client module OK")


def test_interface_import():
    """Test interface module import."""
    from src.interface.app import DerekAgentApp
    print("✓ interface module OK")


if __name__ == "__main__":
    print("Testing module imports...")
    test_config_import()
    test_storage_import()
    test_core_imports()
    test_interface_import()
    print("\nAll imports successful!")
