#!/usr/bin/env python3
"""Entry point for Derek Agent Runner."""

import sys

USAGE = """\
Derek Agent Runner

用法:
  derek-agent                    啟動 TUI 聊天介面
  derek-agent models             設定模型 Provider（互動式精靈）
  derek-agent tools websearch    設定網路搜尋工具（互動式精靈）
  derek-agent --help             顯示此說明
"""


def main():
    """Main entry point."""
    args = sys.argv[1:]

    if args and args[0] in ("--help", "-h"):
        print(USAGE)
        sys.exit(0)

    if args and args[0] == "models":
        try:
            from src.cli.models_cmd import run_models_wizard
            run_models_wizard()
        except KeyboardInterrupt:
            print("\n已取消")
            sys.exit(0)
        except Exception as e:
            print(f"錯誤: {e}")
            sys.exit(1)
        return

    if args and args[0] == "tools":
        subcmd = args[1] if len(args) > 1 else ""
        if subcmd == "websearch":
            try:
                from src.cli.tools_cmd import run_websearch_wizard
                run_websearch_wizard()
            except KeyboardInterrupt:
                print("\n已取消")
                sys.exit(0)
            except Exception as e:
                print(f"錯誤: {e}")
                sys.exit(1)
        else:
            print(f"未知的 tools 子命令: {subcmd!r}")
            print("可用子命令: websearch")
            sys.exit(1)
        return

    # Default: launch TUI
    try:
        # Initialize logging from config
        from src.core.config import get_config, setup_logging
        setup_logging(get_config().settings.logging)

        from src.interface import run_app
        run_app()
    except KeyboardInterrupt:
        print("\n再見！")
        sys.exit(0)
    except Exception as e:
        print(f"錯誤: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
