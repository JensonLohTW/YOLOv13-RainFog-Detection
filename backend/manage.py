#!/usr/bin/env python3
import os
import sys


def main() -> None:
    # 從 backend/.env 載入環境變數（已有的 shell 環境變數優先，不覆蓋）
    try:
        from dotenv import load_dotenv
        load_dotenv(override=False)
    except ImportError:
        pass  # 生產環境通常直接設定真實 env vars，不需要 dotenv

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
