def get_bound_box(boxes):
    boxes = [box for box in boxes if box]
    if not boxes:
        return None

    left, top, right, bottom = list(zip(*boxes))
    return [min(left), min(top), max(right), max(bottom)]
