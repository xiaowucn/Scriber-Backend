# -*- coding: utf-8 -*-
import re

from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import CharResult


class Sentence:
    def __init__(self, start, end, chars):
        self.start = start
        self.end = end
        self.chars = chars

    @property
    def content(self):
        return "".join(i["text"] for i in self.chars)

    def __str__(self):
        return self.content


class Paragraph:
    def __init__(self, element, sentence_separator=r"[；。]"):
        self.element = element
        self.sentence_separator = sentence_separator
        self.sentences = self.build_sentences()

    @property
    def content(self):
        return self.element["text"]

    def build_sentences(self):
        sentences = []
        last_match = None
        has_no_separator = re.search(self.sentence_separator, self.content) is None
        if has_no_separator and self.content:
            start = 0
            end = len(self.content) + 1
            sentences.append(Sentence(start, end, self.element["chars"]))
            return sentences
        for match in re.finditer(self.sentence_separator, self.content):
            if last_match is None:
                start_index = 0
                end_index = match.end()
            else:
                start_index = last_match.end()
                end_index = match.start() + 1
            chars = self.element["chars"][start_index:end_index]
            sentences.append(Sentence(start_index, end_index, chars))
            last_match = match
        return sentences

    def __str__(self):
        return self.element["text"]


class RelationEntity(BaseModel):
    target_element = "paragraph"
    base_all_elements = True
    filter_elements_by_target = True

    def __init__(self, options, schema, predictor):
        super(RelationEntity, self).__init__(options, schema, predictor)
        self._relation_pattern = self._options["relation_pattern"]
        self.stop_patterns = self._options.get("stop_patterns", [])
        self.entity_options = self._options["entity_options"]
        self.syllabus_pattern = self._options.get("syllabus_pattern")
        self.filter_sentences_use_pattern = self._options.get("filter_sentences_use_pattern", False)

    @property
    def relation_patterns(self):
        return self._relation_pattern if isinstance(self._relation_pattern, list) else [self._relation_pattern]

    def train(self, dataset, **kwargs):
        pass

    def print_model(self):
        pass

    def normalize_content(self, content):
        normalized = content
        for i in self.stop_patterns:
            normalized = re.sub(i, "", normalized)

        return normalized

    def extract_entities(self, sentence):
        normalized_sentence = self.normalize_content(sentence.content)
        entities = []
        for i in self.entity_options:
            matched = next(
                (re.search(p, normalized_sentence) for p in i["patterns"] if re.search(p, normalized_sentence)), None
            )
            name = i["schema_name"]
            if matched:
                match_start, match_end = matched.span("entity")
                start = sentence.content.index(matched["entity"], match_start)
                end = start + len(matched["entity"])
                chars = sentence.chars[start:end]
                entity = {"schema_name": name, "content": "".join(i["text"] for i in chars), "chars": chars}
                entities.append(entity)

        return entities

    def match_relation(self, content):
        return any(re.search(i, content) for i in self.relation_patterns)

    def predict_schema_answer(self, elements):
        answers = []
        elements = [i for i in elements if self.match_relation(i["text"])]
        for element in elements:
            # syllabus_titles = [i['title'] for i in self.pdfinsight.get_parent_syllabuses(element['syllabus'])]
            # if syllabus_titles and self.syllabus_pattern:
            #     if all(re.search(self.syllabus_pattern, i) is None for i in syllabus_titles):
            #         continue
            paragraph = Paragraph(element)
            sentences = paragraph.sentences
            if self.filter_sentences_use_pattern:
                sentences = [s for s in paragraph.sentences if self.match_relation(s.content)]
            for sentence in sentences:
                answer = {}
                entities = self.extract_entities(sentence)
                for entity in entities:
                    element_results = [CharResult(element, chars=entity["chars"])]
                    answer_result = self.create_result(
                        element_results, column=entity["schema_name"], text=entity["content"]
                    )
                    answer[entity["schema_name"]] = [answer_result]

                if answer:
                    answers.append(answer)
                    if not self.multi:
                        break
            if answers and not self.multi_elements:
                break

        return answers
