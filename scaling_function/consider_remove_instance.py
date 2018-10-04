"""These functions try to distribute the tasks
from one instance to other instances,
difference is the attribute they are trying."""


def consider_remove_instance_by_memory(tasks, instances):
    """Function to consider remove instances by distributing the tasks by memory.

    Functions tests for each task combination of instances in recursive
    approach. Recursion happens only if instance.memory - task.memory > 0.

    Args:
        *tasks (task_capacity): Task memory and cpu object.
        *instances (instance_capacity): Instance memory and cpu object.

    Returns:
        *instance_capacity: Returns one of the combination of instances
        which could be used for the tasks, if none exists None is returned.

    """
    if len(tasks) == 0:
        return instances if len(
            [
                instance for instance in instances if instance.memory > 0
            ]
        ) else None
    for task in tasks:
        for instance in instances:
            if instance.memory - task.memory > 0:
                tmp_instance = instance
                tmp_instance.memory -= task.memory
                new_instances = []
                for new_instance in instances:
                    if new_instance != tmp_instance:
                        new_instances.append(
                            new_instance
                        )
                    else:
                        new_instances.append(
                            tmp_instance
                        )
                new_tasks = [
                    new_task for new_task
                    in tasks if new_task != task
                ]
                check_next = (
                    consider_remove_instance_by_memory(
                        new_tasks,
                        new_instances
                    )
                )
                if check_next is not None:
                    return check_next


def consider_remove_instance_by_cpu(tasks, instances):
    """This functions does exactly the same as the ony above but for cpu."""
    if len(tasks) == 0:
        return instances if len(
            [
                instance for instance in instances if instance.cpu > 0
            ]
        ) else None
    for task in tasks:
        for instance in instances:
            if instance.cpu - task.cpu > 0:
                tmp_instance = instance
                tmp_instance.cpu -= task.cpu
                new_instances = []
                for new_instance in instances:
                    if new_instance != tmp_instance:
                        new_instances.append(
                            new_instance
                        )
                    else:
                        new_instances.append(
                            tmp_instance
                        )
                new_tasks = [
                    new_task for new_task
                    in tasks if new_task != task
                ]
                check_next = (
                    consider_remove_instance_by_cpu(
                        new_tasks,
                        new_instances
                    )
                )
                if check_next is not None:
                    return check_next
