# encoding=utf-8
import logging


class ScriberAnswerComparer:
    def __init__(self, question_data, doc_data):
        pass

    def compare(self, answer_1, answer_2):
        ua1, ua2 = answer_1.get("userAnswer"), answer_2.get("userAnswer")
        if ua1.keys() != ua2.keys():
            logging.error("keys diff: %s, %s", ua1.keys(), ua2.keys())
            return False

        for key, column in ua1.items():
            if not self.compare_column(column, ua2.get(key)):
                logging.error("item of key %s diff", key)
                return False

        return True

    def compare_column(self, col1, col2):
        items1, items2 = (
            sorted(items, key=lambda item: item.get("schemaMD5")) for items in (col1.get("items"), col2.get("items"))
        )
        if len(items1) != len(items2):
            logging.error("item len diff: %s, %s", len(items1), len(items2))
            return False

        for item1, item2 in zip(items1, items2):
            if not self.compare_item(item1, item2):
                return False

        return True

    @classmethod
    def overlap_percent(cls, box1, box2):
        def area(box):
            return (box[2] - box[0]) * (box[3] - box[1])

        def norm_box(box):
            box = [float(x) for x in box]
            box[2] += box[0]
            box[3] += box[1]
            return box

        def overlap(box1, box2):
            def get_width_abstract(box1, box2, idx1, idx2):
                if box1[idx2] < box2[idx1]:  # non-overlap
                    return None
                elif box1[idx2] < box2[idx2]:  # partial-overlap
                    return box1[idx2] - box2[idx1]
                else:  # box2 inside box1
                    return box2[idx2] - box2[idx1]

            def get_width(box1, box2):
                return get_width_abstract(box1, box2, idx1=0, idx2=2)

            def get_height(box1, box2):
                return get_width_abstract(box1, box2, idx1=1, idx2=3)

            if box1[0] < box2[0]:
                width = get_width(box1, box2)
            else:
                width = get_width(box2, box1)
            if box1[1] < box2[1]:
                height = get_height(box1, box2)
            else:
                height = get_height(box2, box1)
            if not width or not height:
                return None
            return width * height

        box1 = norm_box(box1)
        box2 = norm_box(box2)
        area1 = area(box1)
        area2 = area(box2)
        overlap_area = overlap(box1, box2)
        if not overlap_area:
            return 0
        percent = overlap_area / min(area1, area2)
        return percent

    def compare_item(self, item1, item2):
        enum_label_1 = item1.get("enumLabel", "")
        enum_label_2 = item2.get("enumLabel", "")
        if enum_label_1 != enum_label_2:
            logging.error("item enumLabel diff: %s, %s", enum_label_1, enum_label_2)
            return False
        fields1, fields2 = (
            sorted(fields, key=lambda field: field.get("name")) for fields in (item1.get("fields"), item2.get("fields"))
        )
        if len(fields1) != len(fields2):
            logging.error("field len diff: %s, %s", len(fields1), len(fields2))
            return False

        if not self.compare_answer_content(fields1, fields2):
            return False

        return True

    def compare_answer_content(self, fields1, fields2):
        for field1, field2 in zip(fields1, fields2):
            if field1.get("label") != field2.get("label"):
                logging.error("label diff: %s, %s", field1.get("label"), field2.get("label"))
                return False
            else:
                enum_label_1 = field1.get("enumLabel", "")
                enum_label_2 = field2.get("enumLabel", "")
                if enum_label_1 != enum_label_2:
                    logging.error("field enumLabel diff: %s, %s", enum_label_1, enum_label_2)
                    return False

                comp1 = field1.get("components", [])
                comp2 = field2.get("components", [])
                if len(comp1) != len(comp2):
                    logging.error("component len diff: %s, %s on %s", len(comp1), len(comp2), field1["label"])
                    return False

                if not self.compare_box(comp1, comp2, field1):
                    return False
        return True

    def compare_box(self, comp1, comp2, field1):
        for comp_item1, comp_item2 in zip(comp1, comp2):
            frame1 = comp_item1.get("frameData", None)
            frame2 = comp_item2.get("frameData", None)
            if frame1 is None and frame2 is None:
                continue
            if frame1 is None or frame2 is None:
                logging.error("one of the box is None: %s", field1.get("label"))
                return False
            percent = self.overlap_percent(
                (frame1["left"], frame1["top"], frame1["width"], frame1["height"]),
                (frame2["left"], frame2["top"], frame2["width"], frame2["height"]),
            )
            if percent < 0.5:
                logging.error("box diff: %s %s", percent, field1.get("label"))
                return False
        return True
