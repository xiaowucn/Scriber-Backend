import re
from typing import Callable, Iterator, Pattern

from remarkable.common.util import clean_txt

P_SERIAL = re.compile(
    "|".join(
        [
            r"^第[一二三四五六七八九十\d]+[条章]",
            r"^\d+([.]\d+)+",
            r"^[(（]?[一二三四五六七八九十]+[）)、.]?",
            r"^[(（][a-z\d]+[）)]",
            r"^\d+[）)、.．]",
            r"^\d+(?=[\u4e00-\u9fa5])",
            r"^[a-z]+[.．）)]",
            r"^[\u2460-\u249b]+",
        ]
    )
)

P_PUNCTUATION = re.compile(r"[,;:，。、；：]")

P_EXCLUDE_SERIAL = re.compile(
    "|".join(
        [
            r"^\d+年",
        ]
    )
)

P_QUOTE = re.compile(
    "|".join(
        [
            r"【[^】]*】",
        ]
    )
)

P_SENTENCE_SERIAL = re.compile(
    "|".join(
        [
            r"[(（][iv\d]+[）)]",
            r"\d+[）、]",
            r"[（(][一一二三四五六七八九十\d]+[）)]",
        ]
    )
)

P_DELIMITER = re.compile(r"[。；]")


class DiffMixin:
    paras: list[dict]
    _char2para: list[dict]
    _fixed_para_texts: list[str]

    @property
    def fixed_para_texts(self):
        if self._fixed_para_texts is not None:
            return self._fixed_para_texts
        self._set_before_diff()
        return self._fixed_para_texts

    @property
    def text(self):
        return "".join(self.fixed_para_texts)

    @property
    def char2para(self) -> list[dict | int]:
        """
        返回char到para_id的list映射,
        eg. ['a', 'bb', 'ccc'] -> [0, 1, 1, 2, 2, 2]
        如果需要保留字符, 比如diff的时候忽略字符a, 但是展示需要保留
        ['a', 'bb', 'ccc'] -> [{'text': 'a', 'para_id': 0, 'diff': 'same'}, 1, 1, 2, 2, 2]
        :return:
        """
        if self._char2para is not None:
            return self._char2para
        self._set_before_diff()
        return self._char2para or []

    @property
    def special_methods(self) -> list[Callable[[str, int], set[int]]]:
        raise NotImplementedError

    @property
    def common_regs(self) -> list[Pattern]:
        raise NotImplementedError

    def _set_before_diff(self):
        self._fixed_para_texts = []
        self._char2para = []
        offset = 0
        for para_id, para in enumerate(self.paras):
            cleaned_text = clean_txt(para.text)
            for char in cleaned_text:
                self._char2para.append({"para_id": para_id, "type": "normal", "char": char})

            positions = set()
            for method in self.special_methods:
                positions.update(method(cleaned_text, offset))

            self._fixed_para_texts.append(
                "".join(char for pos, char in enumerate(cleaned_text) if pos not in positions)
            )
            offset += len(cleaned_text)

    def _handle_common(self, clean_text: str, offset: int) -> set[int]:
        """
        记录从paras中去掉的chars的信息, 适用于只要满足正则的char都需要移除的情况
        :param clean_text:
        :return: 需要移除的char在clean text中的位置
        """
        positions = set()

        for reg in self.common_regs:
            extras = {}
            exclude_regs = []
            if reg == P_SERIAL:
                extras["type"] = "serial"
                exclude_regs.append(P_EXCLUDE_SERIAL)
            for matched in reg.finditer(clean_text):
                start, end = matched.start(), matched.end()
                if self.match_regs(exclude_regs, clean_text[start:]):
                    continue
                for pos in range(offset + start, offset + end):
                    self._char2para[pos].update({"text": clean_text[pos - offset], "diff": "same"})
                    self._char2para[pos].update(extras)
                positions.update(i for i in range(start, end))

        return positions

    def _handle_quote(self, clean_text: str, offset: int) -> set[int]:
        """
        记录从paras中去掉的chars的信息, 适用于满足正则的片段中只需要需要移除两边的char的情况
        """
        positions = set()

        for matched in P_QUOTE.finditer(clean_text):
            start, end = matched.start(), matched.end()
            for pos in [offset + start, offset + end - 1]:
                self._char2para[pos].update({"text": clean_text[pos - offset], "diff": "same"})
            positions.update([start, end - 1])

        return positions

    @staticmethod
    def _split_by_delimiter(clean_text: str) -> Iterator[str]:
        sentence = ""
        for char in clean_text:
            sentence += char
            if P_DELIMITER.search(char):
                yield sentence
                sentence = ""
        if sentence:
            yield sentence

    def _handle_sentence(self, clean_text: str, offset: int) -> set[int]:
        positions = set()
        count = 0
        for sentence in self._split_by_delimiter(clean_text):
            for matched in P_SENTENCE_SERIAL.finditer(sentence):
                start, end = matched.start(), matched.end()
                for pos in range(start, end):
                    self._char2para[offset + count + pos].update(
                        {"text": sentence[pos], "diff": "same", "type": "serial"}
                    )
                positions.update(count + i for i in range(start, end))
                break
            count += len(sentence)
        return positions

    def get_para_diff(self, *args, **kwargs):
        raise NotImplementedError

    @staticmethod
    def match_regs(regs, text):
        if hasattr(regs, "search"):
            regs = [regs]
        for reg in regs:
            matched = reg.search(text)
            if matched:
                return matched
        return None
