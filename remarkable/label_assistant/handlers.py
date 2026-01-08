from webargs import fields

from remarkable.base_handler import Auth, DbQueryHandler, route
from remarkable.common import field_validate
from remarkable.common.apispec_decorators import use_kwargs
from remarkable.common.storage import localstorage
from remarkable.models.new_file import NewFile
from remarkable.pdfinsight.reader import PdfinsightReader, PdfinsightSyllabus, PdfinsightTable
from remarkable.plugins.sse.sse_predictor_with_records.sse_predictor_with_records import SsePredictorWithRecord
from remarkable.predictor.predict import AnswerPredictorFactory
from remarkable.predictor.schema_answer import AnswerResult
from remarkable.pw_models.model import NewMold
from remarkable.pw_models.question import NewQuestion


@route(r"/question/(?P<qid>\d+)/association")
class TableAnswerAssociationHandler(DbQueryHandler):
    @Auth("browse")
    async def post(self, **kwargs):
        """
        json_body: {
            column1: {
                "box": {
                    "box": box,
                    "page": page,
                },
                "text": text,
            },
            column2: {},
        }
        """
        qid = kwargs["qid"]
        sample = self.get_json_body()
        key = self.get_query_argument("key")
        _file = await NewFile.find_by_qid(qid)
        question = await NewQuestion.find_by_id(qid)
        mold = await NewMold.find_by_id(question.mold)
        if not question:
            return self.error(f"can't find file: {qid}")
        answers = await self.run_in_executor(associate_table_answer, _file, mold, sample, key)
        return self.data(answers)


def find_table_by_sample(pdfinsight, sample):
    for item in sample.values():
        box = item.get("box")
        if not box:
            continue
        etype, ele = pdfinsight.find_element_by_outline(box["page"], box["box"])
        if ele and ele["class"] == "TABLE":
            return ele
    return None


def get_associated_answers(table_element, sample):
    table = PdfinsightTable(table_element)
    sample_columns = [
        (
            k,
            v,
            table.find_first_cellidx_list_by_outline(v["box"]["page"], v["box"]["box"]) if v and v.get("box") else None,
        )
        for k, v in sample.items()
        if not v.get("common")
    ]
    sample_input = [c[2] for c in sample_columns if c[2] is not None]
    sample_input_keys = [c[0] for c in sample_columns if c[2] is not None]
    sample_none_input_keys = [c[0] for c in sample_columns if c[2] is None]
    # import json
    # with open("debug.json", "w") as dump_fp:
    #     json.dump((table_element, sample_input), dump_fp)
    output = SsePredictorWithRecord.predict_with_one_record(table_element, sample_input)
    associated_answers = []
    for output_item in output:
        answer = {}
        for key, (row, col) in zip(sample_input_keys, output_item):
            cell = table.cell(row, col)
            answer[key] = {"box": {"box": cell["box"], "page": cell["page"]}, "text": cell["text"]}
        for key in sample_none_input_keys:
            answer[key] = None

        associated_answers.append(answer)
    return associated_answers


def associate_table_answer(_file, mold, sample, column):
    table_element = find_table_by_sample(PdfinsightReader(localstorage.mount(_file.pdfinsight_path())), sample)
    if not table_element:
        return []

    predictor = AnswerPredictorFactory.create(mold)
    if hasattr(predictor.formatter, "format_table"):
        table_element = predictor.formatter.format_table(table_element)
    if hasattr(predictor.formatter, "table_skip_rows"):
        table_element["skip_rows"] = predictor.formatter.table_skip_rows(column, table_element, sample)

    common_columns = {k: v for k, v in sample.items() if v.get("common")}
    postfix_columns = {k: v for k, v in sample.items() if v.get("postfix") and not v.get("common")}
    enum_columns = {k: v for k, v in sample.items() if v.get("value") and not v.get("common")}
    link_columns = {k: v for k, v in sample.items() if v.get("link") and not v.get("common")}

    for key, link in link_columns.items():
        sample.update({f"{key}_link": link["link"]})
    associated_answers = get_associated_answers(table_element, sample)
    for answer in associated_answers:
        answer.update(common_columns)
        for key, postfix in postfix_columns.items():
            answer[key]["text"] = answer[key]["text"] + postfix["postfix"]["text"]
        for key, enum in enum_columns.items():
            answer[key] = enum_field_assist(answer[key], enum)
        for key, link in link_columns.items():
            link_answer = answer.pop(f"{key}_link")
            answer[key]["text"] = answer[key]["text"] + link["link"]["symbol"] + link_answer["text"]

    return associated_answers


def enum_field_assist(field, sample):
    """
    目前枚举字段的推断就是直接复制
    :param field:
    :param sample:
    :return:
    """
    if not field:
        field = {}
    field["value"] = sample["value"]
    return field


@route(r"/question/(?P<qid>\d+)/answer_assist")
class AnswerAssistHandler(DbQueryHandler):
    @Auth("browse")
    async def post(self, **kwargs):
        """
        {
            'answer': {
                'schema':...
                'userAnswer':{
                    'items': [...],
                    'version':"2.2"
                }
            }
            'key':董监高核心人员基本情况,

        }
        :param args:
        :param kwargs:
        :return:
        """
        qid = kwargs["qid"]
        question = await NewQuestion.find_by_id(qid)
        if not question:
            return self.error(f"can't find question: {qid}")

        data = self.get_json_body()
        answer = await self.answer_assist(question, data["answer"], data["key"])
        return self.data(answer)

    async def answer_assist(self, question, answer, key):
        mold = await NewMold.find_by_id(question.mold)
        predictor = AnswerPredictorFactory.create(mold)
        if hasattr(predictor.formatter, "answer_assist"):
            answer = predictor.formatter.answer_assist(answer, key)
        return answer


@route(r"/question/(?P<qid>\d+)/chapter_assist")
class ChapterAssistHandler(DbQueryHandler):
    chapter_assist_kwargs = {
        "structure": fields.Nested(
            {"title": fields.Str(required=True), "content": fields.Str(required=True)}, required=True
        ),
        "labels": fields.List(
            fields.Dict(validate=lambda x: all("box" in v and "text" in v for v in x.values())),
            validate=field_validate.Length(min=1),
            required=True,
        ),
    }

    @Auth("browse")
    @use_kwargs(chapter_assist_kwargs, location="json")
    async def post(self, **kwargs):
        """
        json_body: {
            'structure':  {
                    'title': 'column1',
                    'content': 'column2',
            },
            'labels':  [
                    {
                        column1: {
                            "box": {
                                "box": box,
                                "page": page,
                            },
                            "text": text,
                        },
                    },
            ]
        }
        :param args:
        :param kwargs:
        :return:
        """
        qid = kwargs["qid"]
        title = kwargs["structure"]["title"]
        content = kwargs["structure"]["content"]
        labels = kwargs["labels"]
        file = await NewFile.find_by_qid(qid)
        labels = await self.run_in_executor(self.chapter_assist, file, title, content, labels)
        return self.data(labels)

    @staticmethod
    def chapter_assist(file: NewFile, title, content, labels):
        """
        根据指定的标题,找到其下面的文本
        """
        reader = PdfinsightReader(localstorage.mount(file.pdfinsight_path()))
        for item in labels:
            label_box = item[title]["box"]
            _, title_element = reader.find_element_by_outline(label_box["page"], label_box["box"])
            boxes = []
            for page_data in PdfinsightSyllabus.syl_outline(reader.syllabus_dict[title_element["syllabus"]], reader):
                boxes.append(AnswerResult.create_box(page_data["page"], page_data["outline"], page_data["text"]))
            item[content] = {"data": [{"boxes": boxes}]}
        return labels
