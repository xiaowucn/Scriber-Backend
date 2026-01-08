from functools import lru_cache

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.plugins.cgs.common.patterns_util import R_SERIAL_CN_NUMBER


@lru_cache()
def clear_syl_title(title):
    title = clean_txt(title)
    return syl_clean.sub("", title).strip()


syl_clean = PatternCollection(
    [
        rf"^[第\(（\[]*[一二三四五六七八九十\d\s\-a-zA-Z{R_SERIAL_CN_NUMBER}]+[.．、]?(章|节|章节|部分|条)?、?[\)）\]]*",
        r"[:：]*$",
    ]
)
