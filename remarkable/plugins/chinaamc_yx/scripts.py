import json
from pathlib import Path

from remarkable.common.storage import localstorage
from remarkable.config import get_config, project_root
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.pw_models.model import NewFileProject, NewMold
from remarkable.pw_models.question import NewQuestion


async def dump_samples():
    """导出范文相关数据"""
    project_name = get_config("chinaamc_yx.sample_project")
    samples_path = Path(f"{project_root}/data/chinaamc_yx/samples")
    project = await NewFileProject.find_by_kwargs(name=project_name)
    query = (
        NewQuestion.select(NewQuestion, NewMold.name.alias("mold_name"))
        .join(NewFile, on=(NewFile.id == NewQuestion.fid))
        .join(NewMold, on=(NewQuestion.mold == NewMold.id))
    )

    questions = await pw_db.execute(query.where(NewFile.pid == project.id).dicts())
    for question in questions:
        schema = question["mold_name"]
        with open(samples_path / f"{schema}.json", "w") as file_obj:
            json.dump(question, file_obj)

        file = await NewFile.find_by_id(question["fid"])
        file_path = samples_path / f"{schema}.pdf"
        pdf_data = localstorage.read_file(file.pdf_path())
        localstorage.write_file(file_path.as_posix(), pdf_data)

        print(f"dump for {schema}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(dump_samples())
