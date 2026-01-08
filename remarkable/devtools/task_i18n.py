from invoke import run, task


@task
def extract(ctx):
    run("pybabel extract remarkable/ -o i18n/locales/Scriber-Backend.pot --no-location")


@task
def update(ctx):
    run("pybabel update -D Scriber-Backend -i i18n/locales/Scriber-Backend.pot -d i18n/locales/")


@task
def compile2po(ctx):
    run("pybabel compile -D Scriber-Backend -d i18n/locales/")


@task
def po2mo(ctx):
    run("pybabel compile -D Scriber-Backend -d i18n/locales/")
