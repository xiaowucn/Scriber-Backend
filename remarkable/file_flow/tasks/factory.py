from remarkable.file_flow.tasks.task import BaseTask, DefaultTask, TaskStatus, ZtsTask

tasks = {
    "default": DefaultTask,
    "zts": ZtsTask,
}


async def create_flow_task(client_name: str, start_value: TaskStatus = TaskStatus.created) -> BaseTask:
    cls = tasks.get(client_name, tasks["default"])
    task = cls(start_value=start_value)
    await task.activate_initial_state()

    return task
