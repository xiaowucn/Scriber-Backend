from unittest import TestCase

from remarkable.plugins.cgs.common.enum_utils import ConvertContentEnum
from remarkable.plugins.cgs.common.para_similarity import ParagraphSimilarity
from remarkable.plugins.cgs.common.patterns_util import P_PRIVATE_SIMILARITY_PATTERNS


class TestDiff(TestCase):
    def test_text_match_seq(self):
        texts_a = ["AAAAA5BBB3"]
        texts_b = ["AAAAA", "BBBBB", "AAAAABBB"]
        self.assertSequenceEqual(" A A A A A-5 B B B-3", ParagraphSimilarity(texts_a, texts_b, ratio=0.8).result_text)

    def test_seq_all_match_seq(self):
        texts_a = ["BBBBBXCCCCX", "AAAAA5BBB3"]
        texts_b = ["AAAAA5", "BBBBB5CCCC4", "AAAAABBB"]
        self.assertSequenceEqual(
            " B B B B B-X+5 C C C C-X+4\n A A A A A-5 B B B-3",
            ParagraphSimilarity(texts_a, texts_b, ratio=0.8).result_text,
        )

    def test_last_seq_match_seq(self):
        texts_a = ["bbbbbXccccX", "AAAAA5BBB3"]
        texts_b = ["AAAAA5", "BBBBB5CCCC4", "AAAAABBB"]
        similarity = ParagraphSimilarity(texts_a, texts_b, ratio=0.8, fill_paragraph=True)
        self.assertSequenceEqual("-b-b-b-b-b-X-c-c-c-c-X\n A A A A A-5 B B B-3", similarity.result_text)
        self.assertFalse(similarity.is_full_matched)
        self.assertTrue(similarity.is_matched)

        similarity = ParagraphSimilarity(texts_a, texts_b, ratio=0.8, fill_paragraph=False)
        self.assertSequenceEqual("-b-b-b-b-b-X-c-c-c-c-X\n A A A A A-5 B B B-3", similarity.result_text)
        self.assertFalse(similarity.is_full_matched)
        self.assertTrue(similarity.is_matched)

    def test_addition_item(self):
        texts_a = ["AAAAA4", "AAAAA5BBB3"]
        texts_b = ["AAAAA5", "BBBBB5CCCC4", "AAAAABBB"]
        self.assertSequenceEqual(
            " A A A A A-4+5\n+B+B+B+B+B+5+C+C+C+C+4\n A A A A A-5 B B B-3",
            ParagraphSimilarity(texts_a, texts_b, ratio=0.8).result_text,
        )

    def test_miss_item(self):
        texts_a = ["AAAAA4", "BBBBB5CCCC4", "AAAAA5BBB3"]
        texts_b = ["AAAAA5", "AAAAABBB"]
        self.assertSequenceEqual(
            " A A A A A-4+5\n-B-B-B-B-B-5-C-C-C-C-4\n A A A A A-5 B B B-3",
            ParagraphSimilarity(texts_a, texts_b, ratio=0.8).result_text,
        )

    def test_empty_seq(self):
        texts_a = ["DDDDDDDD"]
        texts_b = ["AAAAA5", "AAAAABBB"]
        similarity = ParagraphSimilarity(texts_a, texts_b, ratio=0.8, fill_paragraph=True)
        self.assertSequenceEqual("-D-D-D-D-D-D-D-D", similarity.result_text)
        self.assertFalse(similarity.is_full_matched)
        self.assertFalse(similarity.is_matched)

        similarity = ParagraphSimilarity(texts_a, texts_b, ratio=0.8, fill_paragraph=False)
        self.assertSequenceEqual("-D-D-D-D-D-D-D-D", similarity.result_text)
        self.assertFalse(similarity.is_full_matched)
        self.assertFalse(similarity.is_matched)

    def test_miss_last_item(self):
        texts_a = ["AAAAA4", "CCCCCCC"]
        texts_b = ["AAAAA5", "BBBBB5CCCC4", "AAAAABBB"]
        self.assertSequenceEqual(
            " A A A A A-4+5\n-C-C-C-C-C-C-C", ParagraphSimilarity(texts_a, texts_b, ratio=0.8).result_text
        )

    def test_repeat_item(self):
        texts_a = ["AAAAA4", "AAAAA5BBB3"]
        texts_b = ["AAAAA5", "BBBBB5CCCC4", "AAAAABBB", "AAAAA5", "BBBBB5CCCC4", "AAAAABBB"]
        self.assertSequenceEqual(
            " A A A A A-4+5\n+B+B+B+B+B+5+C+C+C+C+4\n A A A A A-5 B B B-3",
            ParagraphSimilarity(texts_a, texts_b, ratio=0.8).result_text,
        )

    def test_best_match(self):
        texts_a = ["AAAAA4", "AAAAA5BBB3"]
        texts_b = ["AAAAA5", "AAAAABBB", "AAAAABBB", "AAAAA6", "BBBBB5CCCC4", "AAAAA5BBB3"]
        self.assertSequenceEqual(
            " A A A A A-4+5\n A A A A A-5 B B B-3",
            ParagraphSimilarity(texts_a, texts_b, ratio=0.8).result_text,
        )

    def test_filter_junk(self):
        texts_a = ["AAAAA5.", "XXXXX", "AAAAA5。"]
        texts_b = ["AAA?AA5。。。", "AAAAABBB", "AAAAABBB", "AAAAA6", "BBBBB5CCCC4", "AAAAA5BBB3"]
        similarity = ParagraphSimilarity(texts_a, texts_b, ratio=0.8, fill_paragraph=True)
        self.assertSequenceEqual(
            " A A A ? A A 5 。 。 。\n-X-X-X-X-X\n+A+A+A+A+A+B+B+B\n+A+A+A+A+A+B+B+B\n A A A A A-5+6",
            similarity.result_text,
        )
        self.assertFalse(similarity.is_full_matched)
        self.assertTrue(similarity.is_matched)

        similarity = ParagraphSimilarity(texts_a, texts_b, ratio=0.8, fill_paragraph=False)
        self.assertSequenceEqual(
            " A A A ? A A 5 。 。 。\n-X-X-X-X-X\n+A+A+A+A+A+B+B+B\n+A+A+A+A+A+B+B+B\n A A A A A-5+6",
            similarity.result_text,
        )
        self.assertFalse(similarity.is_full_matched)
        self.assertTrue(similarity.is_matched)

    def test_diff_junk(self):
        texts_a = ["二十一、违约责任"]
        texts_b = ["二十一、违约责任83"]
        self.assertSequenceEqual(
            " 二 十 一 、 违 约 责 任+8+3",
            ParagraphSimilarity(texts_a, texts_b, ratio=0.8).result_text,
        )

    def test_ignore_diff_numbering(self):
        texts_a = ["21.违约责任!!!!"]
        texts_b = ["二十一、违约责任?"]
        similarity = ParagraphSimilarity(texts_a, texts_b, ratio=0.8)
        self.assertSequenceEqual(
            " 二 十 一 、 违 约 责 任 ?",
            similarity.result_text,
        )
        self.assertTrue(similarity.is_full_matched)

    def test_diff_sentences(self):
        texts_a = ["21.违约责任。二十一二十一二十一二十一", "ces"]
        texts_b = ["二十一、违[!]约责任?。一一一一一一一一一。一一", "ces"]
        self.assertSequenceEqual(
            " 二 十 一 、 违 [ ! ] 约 责 任 ? 。-二-十-一-二-十-一-二-十-一-二-十-一+一+一+一+一+一+一+一+一+一+。+一+一\n c e s",
            ParagraphSimilarity(texts_a, texts_b, ratio=0.8).result_text,
        )

    def test_sentences_contains_template(self):
        texts_a = ["违约责任。二十一二十一二十一二十一", "ces"]
        texts_b = ["xx。违[!]约责任?。一一一一一一一一一。一一", "ces。xxx"]
        self.assertSequenceEqual(
            "+x+x+。 违 [ ! ] 约 责 任 ? 。-二-十-一-二-十-一-二-十-一-二-十-一+一+一+一+一+一+一+一+一+一+。+一+一\n c e s+x+x+x",
            ParagraphSimilarity(texts_a, texts_b, ratio=0.8, fill_paragraph=True).result_text,
        )

        self.assertSequenceEqual(
            " 违 [ ! ] 约 责 任 ? 。-二-十-一-二-十-一-二-十-一-二-十-一+一+一+一+一+一+一+一+一+一+。+一+一\n c e s",
            ParagraphSimilarity(texts_a, texts_b, ratio=0.8, fill_paragraph=False).result_text,
        )

    def test_keep_miss_junk(self):
        texts_a = [",,,AAAB,B,BCCC"]
        texts_b = ["AAACCC"]
        self.assertSequenceEqual(
            " A A A-B-,-B-,-B C C C",
            ParagraphSimilarity(texts_a, texts_b, ratio=0.8).result_text,
        )

    def test_keep_miss_header_footer_junk(self):
        texts_a = [",,,B,B,BCCCCCCCCCCCCCCCCCCCCCC,F,"]
        texts_b = ["AACCCCCCCCCCCCCCCCCCCCCC"]
        self.assertSequenceEqual(
            "+A+A-,-,-,-B-,-B-,-B C C C C C C C C C C C C C C C C C C C C C C-,-F",
            ParagraphSimilarity(texts_a, texts_b, ratio=0.8).result_text,
        )

    def test_param_max_width(self):
        texts_a = ["AAAAA", "BBBBB"]
        texts_b = ["XXXXX", "AAAAA", "BBBBB", "XXXX", "XXXX", "XXXX", "XXXX", "XXXX", "XXXX", "BBBBB"]
        self.assertSequenceEqual(
            " A A A A A\n B B B B B",
            ParagraphSimilarity(texts_a, texts_b, ratio=0.8, max_width=3).result_text,
        )

    def test_seq_match(self):
        texts_a = [
            "募集结算资金专用账户监督机构：指根据《募集办法》对本基金的募集结算资金专用账户进行监督的机构。募集结算资金专用账户监督机构依据法律法规及与募集机构签署的账户监督协议对募集结算资金专用账户实施有效监督。"
        ]
        texts_b = [
            "10、募集结算资金专用账户监督机构：指根据《募集办法》对本基金的募集结算资金专用账户进行监督的机构。募集结算资金专用账户监督机构依据法律法规及与募集机构签署的账户监督协议对募集结算资金专用账户实施有效监督。每一个募集结算资金专用账户监督机构仅对与自己签署账户监督协议的募集机构开立的募集结算资金专用账户实施有效监督。"
        ]

        self.assertTrue(ParagraphSimilarity(texts_a, texts_b, ratio=0.8, max_width=3).is_full_matched_or_contain)

    def test_suffix_match(self):
        texts_a = ["AAAABBBB", "CCCC", "BBBBB"]
        texts_b = ["募集结算资金专用账户监督机构,AAAABBBB", "CCCC", "BBBBB"]
        self.assertSequenceEqual(
            " A A A A B B B B\n C C C C\n B B B B B",
            ParagraphSimilarity(texts_a, texts_b, max_width=3).result_text,
        )

    def test_prefix_match(self):
        texts_a = ["AAAABBBB", "CCCC", "募集结算"]
        texts_b = ["AAAABBBB", "CCCC", "募集结算,募集结算资金专用账户监督机构"]
        self.assertSequenceEqual(
            " A A A A B B B B\n C C C C\n 募 集 结 算",
            ParagraphSimilarity(texts_a, texts_b, max_width=3).result_text,
        )

    def test_compare_two_text(self):
        self.assertSequenceEqual(
            "募集结算资金《专用账户》监督机构。AAX;X",
            ParagraphSimilarity.compare_two_text(
                "募集结算资金(专用账户)监督机构;AA。XX", "募集结算资金《专用账户》监督机构。AAX;X"
            ).html_diff_content,
        )

    def test_replace_symbol_with_right_text(self):
        # 近义词前标点符号还原
        texts_a = ["6、私募1，私募基金管理人提请聘用、更换投资顾问"]
        texts_b = ["6、私募,、托管人提请聘用、更换投资顾问"]
        self.assertSequenceEqual(
            " 6 、 私 募 , 、+托-1-私-募-基-金 管-理 人 提 请 聘 用 、 更 换 投 资 顾 问",
            ParagraphSimilarity(texts_a, texts_b, ratio=0.5).result_text,
        )

    def test_head_similar_word_text(self):
        # 近义词前标点符号还原
        texts_a = ["7、测试管理人托管人因私募基金财产的管理"]
        texts_b = ["私募基金管理人、私募基金托管人因私募基金财产的管理"]
        self.assertSequenceEqual(
            "-测-试 私 募 基 金 管 理 人 、 私 募 基 金 托 管 人 因 私 募 基 金 财 产 的 管 理",
            ParagraphSimilarity(
                texts_a, texts_b, ratio=0.7, similarity_patterns=P_PRIVATE_SIMILARITY_PATTERNS
            ).result_text,
        )

    def test_ignore_head_symbol_text(self):
        # 近义词前标点符号还原
        texts_a = ["私募基金管理人保证在募集资金前已在中国基金业协会登记为私募基金管理人"]
        texts_b = ["✓基金管理人保证在募集资金前已在中国基金业协会登记为管理人"]
        self.assertSequenceEqual(
            " ✓ 基 金 管 理 人 保 证 在 募 集 资 金 前 已 在 中 国 基 金 业 协 会 登 记 为 管 理 人",
            ParagraphSimilarity(texts_a, texts_b, similarity_patterns=P_PRIVATE_SIMILARITY_PATTERNS).result_text,
        )

    def test_tail_symbol_exist_text(self):
        # 近义词前标点符号还原
        texts_a = ["QDII基金受到投资市场坐在的国家或地区宏观经济运作影响"]
        texts_b = ["（18）投资QDⅡ的风险（如有）QD11基金受到投资市场坐在的国家或地区宏观经济运作影响"]
        self.assertSequenceEqual(
            " （ 1 8 ）+投+资 Q D Ⅱ+的+风+险+（+如+有+）+Q+D+1+1 基 金 受 到 投 资 市 场 坐 在 的 国 家 或 地 区 宏 观 经 济 运 作 影 响",
            ParagraphSimilarity(texts_a, texts_b, similarity_patterns=P_PRIVATE_SIMILARITY_PATTERNS).result_text,
        )

    def test_similar_number_text(self):
        # 近义词前标点符号还原
        texts_a = [
            "2012年基金管理人的董事在最近12个月内变更超过百分之五十，基金管理人认购本基金的金额不少于1000万元人民币"
        ]
        texts_b = [
            "二零一二年基金管理人的董事在最近十二个月内变更超过1/2，基金管理人认购本基金的金额不少于0.1亿元人民币"
        ]
        self.assertSequenceEqual(
            " 二 零 一 二 年 基 金 管 理 人 的 董 事 在 最 近 十 二 个 月 内 变 更 超 过 1 / 2 ， 基 金 管 理 人 认 购 本 基 金 的 金 额 不 少 于 0 . 1 亿 元 人 民 币",
            ParagraphSimilarity(texts_a, texts_b, convert_types=ConvertContentEnum.member_values()).result_text,
        )

    def test_similar_percentage_text(self):
        # 近义词前标点符号还原
        texts_a = ["基金管理人认购本基金的比例不少于10.0%"]
        texts_b = ["基金管理人认购本基金的比例不少于百分之十"]
        self.assertSequenceEqual(
            " 基 金 管 理 人 认 购 本 基 金 的 比 例 不 少 于 百 分 之 十",
            ParagraphSimilarity(texts_a, texts_b, convert_types=ConvertContentEnum.member_values()).result_text,
        )

    def test_symbol_text(self):
        # 对比书名号后的标点符号
        texts_a = ["（3）发现基金管理人,有违反《基金合同》、托管协议及国家法律法规行为"]
        texts_b = ["（3）发现，基金管理人有违反《基金合同》及国家法律法规行为"]
        self.assertSequenceEqual(
            " （ 3 ） 发 现 ， 基 金 管 理 人 有 违 反 《 基 金 合 同 》-、-托-管-协-议 及 国 家 法 律 法 规 行 为",
            ParagraphSimilarity(texts_a, texts_b, convert_types=ConvertContentEnum.member_values()).result_text,
        )

    def test_tail_symbol_text(self):
        # 还原左侧文本尾部剩余字符（忽略比较的符号）
        texts_a = ["2、银行同期存款利息（税后）。"]
        texts_b = ["2、银行同期存款利息。"]
        self.assertSequenceEqual(
            " 2 、 银 行 同 期 存 款 利 息-（-税-后-） 。",
            ParagraphSimilarity(texts_a, texts_b, convert_types=ConvertContentEnum.member_values()).result_text,
        )

    def test_head_punctuation_word_text(self):
        # 近义词前标点符号还原
        texts_a = ["（4）交纳基金认购；"]
        texts_b = ["（4）缴纳基金认购；"]
        self.assertSequenceEqual(
            " （ 4 ）-交+缴 纳 基 金 认 购 ；",
            ParagraphSimilarity(texts_a, texts_b, ratio=0.7).result_text,
        )

    def test_brackets_word_text(self):
        texts_a = [
            "遵照《深圳证券交易所交易规则》、《深圳证券交易所证券投资基金上市规则》、《深圳证券交易所证券投资基金交易和申购赎回实施细则》等有关规定。"
        ]
        texts_b = ["遵照《深圳证券交易所交易规则》、《深圳证券交易所证券投资基金上市规则》等有关规定。"]
        self.assertSequenceEqual(
            " 遵 照 《 深 圳 证 券 交 易 所 交 易 规 则 》 、 《 深 圳 证 券 交 易 所 证 券 投 资 基 金 上 市 规 则 》-、-《-深-圳-证-券-交-易-所-证-券-投-资-基-金-交-易-和-申-购-赎-回-实-施-细-则-》 等 有 关 规 定 。",
            ParagraphSimilarity(texts_a, texts_b, ratio=0.7).result_text,
        )

        texts_a = ["除第2、9、14项外"]
        texts_b = ["除上述（2）、（9）、（14）、（18）、（20）情形之外"]
        self.assertSequenceEqual(
            " 除-第+上+述 （ 2 ） 、 （ 9 ） 、 （ 1 4 ）-项 、+（+1+8+） 、+（+2+0+）+情+形+之 外",
            ParagraphSimilarity(texts_a, texts_b, ratio=0.3).result_text,
        )

    def test_tail_punctuation_word_text(self):
        texts_a = ["（4）交纳基金认购、收购；"]
        texts_b = ["（4）缴纳基金认购；"]
        self.assertSequenceEqual(
            " （ 4 ）-交+缴 纳 基 金 认 购-、-收-购 ；",
            ParagraphSimilarity(texts_a, texts_b, ratio=0.7).result_text,
        )

    def test_merge_equal_diff_result(self):
        texts_a = ["基金募集期间募集的资金存入专门账户。在募集结束前，任何人不得动用。"]
        texts_b = ["基金募集期间募集的资金存入专门账户，在募集结束前。任何人不得动用。"]
        self.assertSequenceEqual(
            " 基 金 募 集 期 间 募 集 的 资 金 存 入 专 门 账 户 ， 在 募 集 结 束 前 。 任 何 人 不 得 动 用 。",
            ParagraphSimilarity(texts_a, texts_b, ratio=0.7).result_text,
        )
