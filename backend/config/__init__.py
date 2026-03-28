"""Django project configuration package."""

import pymysql

# 使用純 Python 的 PyMySQL 代替 mysqlclient，降低本地安裝門檻。
pymysql.install_as_MySQLdb()
