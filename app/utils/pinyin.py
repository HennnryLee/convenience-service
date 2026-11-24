"""拼音排序键（纯函数）。

问题背景：SQLite 默认 BINARY 排序规则按 UTF-8 字节序比较中文，得到的是
Unicode 码点序（住 U+4F4F → 儿 U+513F → 家 U+5BB6 …），既不是拼音也不是笔画。
普通用户看到"按名称"却排成这个样子，会认为功能坏了 —— 排序规则不该成为
只有数据库开发者才看得懂的实现细节。

解决思路：写入时把名称折算成"无声调小写拼音串"存为冗余列 name_pinyin，
排序直接比较该列。数据库只做普通字符串比较，既不需要理解中文，也不依赖
具体数据库的 collation 实现（SQLite 的 BINARY、MySQL 的 utf8mb4_0900_ai_ci
各不相同），因此换库后顺序依然稳定。

教材对应：用冗余字段"以空间换时间"，避免在查询期对列做函数计算（那样无法
走索引）；同时把"排序规则"从数据库实现细节提升为显式的业务数据。
"""
import re

from pypinyin import lazy_pinyin

# 与 ServiceItem.name 的 100 字符上限对应：中文平均 3~4 个字母/字，
# 255 足以覆盖，极端超长名截断尾部即可（不影响可用性）。
PINYIN_KEY_MAX_LENGTH = 255

_SEPARATOR = re.compile(r"[^a-z0-9]+")


def to_pinyin_key(text):
    """名称 -> 拼音排序键。

    前置条件：text 为 None 或字符串。
    后置条件：返回小写、"音节间单空格分隔"的字符串（可能为空串），长度 <= 255。

    处理步骤：
      1. lazy_pinyin 按词组上下文取常用读音（重庆 -> chongqing，银行 -> yinhang）
      2. 非中文字符原样保留（iPhone 15 维修 -> iphone 15 wei xiu）
      3. 用单空格分隔音节，让音节边界参与比较

    为什么必须保留分隔符：若直接拼成无分隔串，"社保卡"(shebao)、"社区"(shequ)、
    "身份证"(shenfen) 会按字符比成 shebao < shenfen < shequ，把"身份证"插到两个
    "社"中间；按音节比较才是 she-bao < she-qu < shen-fen，与汉语拼音字典序一致。
    """
    if not text:
        return ""
    syllables = []
    for syllable in lazy_pinyin(str(text)):
        cleaned = _SEPARATOR.sub(" ", syllable.lower()).strip()
        if cleaned:
            syllables.append(cleaned)
    return " ".join(syllables)[:PINYIN_KEY_MAX_LENGTH].strip()
