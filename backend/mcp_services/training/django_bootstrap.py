from __future__ import annotations

import os


def bootstrap_django(settings_module: str) -> None:
    """初始化 Django 環境，供獨立 MCP 服務重用既有 ORM 與服務層。"""

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

    import django
    from django.apps import apps

    if not apps.ready:
        django.setup()
