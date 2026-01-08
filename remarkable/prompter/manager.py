from remarkable import config
from remarkable.prompter.builder import AnswerPrompterBuilder
from remarkable.prompter.impl.god import GodAnswerPrompter


class PrompterManager:
    def __init__(self):
        self.prompters = {}

    def get_schema_prompter(self, schema_id, godmode=False, vid=0):
        mode = config.get_config("prompter.mode", "v2")
        if godmode:
            prompter = GodAnswerPrompter(schema_id)
            return prompter

        if mode == "rpc":
            from remarkable.service.rpc import AnswerPrompterBuilderRPC

            builder = AnswerPrompterBuilderRPC(schema_id, vid=vid)
        else:
            builder = AnswerPrompterBuilder(schema_id, vid=vid)

        prompter = builder.load()
        if not prompter:
            return None

        self.prompters[schema_id] = prompter
        return prompter


prompter_manager = PrompterManager()
