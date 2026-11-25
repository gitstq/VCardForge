"""电话号码规范化引擎。

自研规则（零依赖，不查询任何在线号段库）:

    - 统一去除空格 / 括号 / 连字符 / 全角字符；
    - ``+`` 开头 -> 直接保留为国际格式；
    - ``00`` 开头 -> 转为 ``+`` 国际格式；
    - 11 位且以 1 开头 -> 判定为中国大陆手机号，补 ``+86``；
    - 3-4 位本地短号、区号座机（如 ``010-1234567``）保持原样但去格式；
    - 输出统一的小写数字键用于去重比较。
"""

from __future__ import annotations

import re

from .model import PhoneNumber

__all__ = ["normalize_phone", "phone_key", "normalize_contact_phones"]

_STRIP_RE = re.compile(r"[\s\-\(\)（）\.．/\\]")
_FULLWIDTH = str.maketrans("０１２３４５６７８９＋", "0123456789+")


def normalize_phone(raw: str, default_country: str = "+86") -> str:
    """把任意格式的电话号码规范化为 E.164 风格字符串。

    无法识别国别时保持数字原样（不强行加国别码，避免误判）。
    """
    if raw is None:
        return ""
    text = raw.translate(_FULLWIDTH)
    text = _STRIP_RE.sub("", text).strip()
    if not text:
        return ""
    # 国际格式
    if text.startswith("+"):
        digits = text[1:]
        if digits.isdigit():
            return "+" + digits
        return text
    if text.startswith("00"):
        digits = text[2:]
        if digits.isdigit():
            return "+" + digits
    digits = re.sub(r"\D", "", text)
    if not digits:
        return text
    # 中国大陆手机号：11 位、1 开头（13/14/15/16/17/18/19）
    if len(digits) == 11 and digits.startswith("1"):
        return default_country + digits
    # 带长途前缀 0 的座机：010 / 021 / 0755 等
    if len(digits) in (10, 11, 12) and digits.startswith("0"):
        return default_country + digits
    # 短号 / 服务号 / 本地号：原样返回纯数字
    return digits


def phone_key(raw: str) -> str:
    """去重比较键：取规范化结果；若规范化为空则用原始数字。"""
    norm = normalize_phone(raw)
    if norm:
        return norm
    return re.sub(r"\D", "", raw or "")


def normalize_contact_phones(contacts) -> None:
    """就地规范化一组联系人的所有 TEL 字段的 ``normalized`` 值。"""
    for contact in contacts:
        for phone in contact.phones:
            phone.normalized = normalize_phone(phone.raw)
