"""VCardForge — 零依赖 · 离线优先的 vCard (.vcf) 通讯录工具箱。

纯 Python 标准库实现，无任何第三方依赖。

公开 API 一览::

    from vcardforge import Contact, parse_file, parse_text, write_file

    contacts = parse_file("users.vcf")
    write_file(contacts, "out.vcf", version="4.0")

子模块说明:
    - ``parser``   : vCard 2.1/3.0/4.0 文本解析（行折叠、QP/BASE64、参数）
    - ``model``    : ``Contact`` 数据模型与字段访问
    - ``writer``   : vCard 3.0/4.0 生成与行折叠输出
    - ``phone``    : 电话号码规范化与去重键
    - ``merge``    : 多文件合并与智能去重
    - ``export``   : JSON / CSV 导出
    - ``validate`` : 合规校验与质量报告
    - ``cli``      : 命令行入口 ``python -m vcardforge``
"""

__version__ = "1.0.0"
__author__ = "VCardForge Contributors"
__license__ = "MIT"

from .model import Contact, PhoneNumber, EmailAddress, Birthday
from .parser import parse_text, parse_file, ParseError
from .writer import write_text, write_file
from .phone import normalize_phone, phone_key
from .merge import merge_contacts, dedup_contacts, MergeReport
from .export import to_json, to_csv
from .validate import validate_contacts, ValidationReport

__all__ = [
    "Contact",
    "PhoneNumber",
    "EmailAddress",
    "Birthday",
    "parse_text",
    "parse_file",
    "ParseError",
    "write_text",
    "write_file",
    "normalize_phone",
    "phone_key",
    "merge_contacts",
    "dedup_contacts",
    "MergeReport",
    "to_json",
    "to_csv",
    "validate_contacts",
    "ValidationReport",
    "__version__",
]
