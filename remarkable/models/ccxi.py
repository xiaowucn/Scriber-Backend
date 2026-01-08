class CCXIFileProject:
    columns_in_meta = ["name", "prj_type", "participants", "uid"]

    def __init__(self, project):
        self.project = project

    def to_dict(self):
        ret = {"prj_num": self.project.name, "uid": self.project.uid}
        for key in self.columns_in_meta:
            ret[key] = self.project.meta.get(key)

        return ret


class CCXIFileTree:
    columns_in_meta = ["name", "prj_num", "uid"]

    def __init__(self, tree):
        self.tree = tree

    def to_dict(self):
        ret = {"version": self.tree.name}
        for key in self.columns_in_meta:
            ret[key] = self.tree.meta.get(key)

        return ret
