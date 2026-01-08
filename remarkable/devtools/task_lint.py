import os

from invoke import run, task


@task
def code_check(ctx):
    os.environ["RUFF_NO_CACHE"] = "true"
    os.environ["PYTHONPATH"] = f"{ctx['project_root']}:{os.environ.get('PYTHONPATH', '')}"
    # 只检查最近十次的修改内容
    run("git diff --name-only HEAD~10 HEAD | xargs pre-commit run --files")
