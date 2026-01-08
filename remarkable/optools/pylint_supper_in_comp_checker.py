from astroid import nodes
from pylint import checkers
from pylint.checkers import utils


class SupperInCompChecker(checkers.BaseChecker):
    name = "super-in-comprehension"

    msgs = {
        "R9527": (
            "You need to abstract super() to a variable",
            "do-not-use-super-in-comprehension",
            "Use super() in comprehension may cause compatibility issues with cython.",
        ),
    }
    options = ()

    priority = -1

    @utils.only_required_for_messages(
        "do-not-use-super-in-comprehension",
    )
    def visit_comprehension(self, node: nodes.Comprehension) -> None:
        self._check_super_in_comprehension(node)

    def _check_super_in_comprehension(self, node: nodes.Comprehension) -> None:
        if " super(" not in node.as_string():
            return

        self.add_message("do-not-use-super-in-comprehension", node=node)


def register(linter):
    linter.register_checker(SupperInCompChecker(linter))
