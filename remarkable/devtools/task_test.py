from invoke import run, task


@task()
def unittest(_):
    _SCRIPT = """
    bin/db_util.sh test
    pytest
    exit_code=$?
    bin/db_util.sh test down
    exit $exit_code
    """
    run(f"bash -c '{_SCRIPT}'")
