import json
import logging
import os
import boto3
from capacity_classes import task_capacity
from capacity_classes import instance_capacity
from consider_remove_instance import consider_remove_instance_by_memory
from consider_remove_instance import consider_remove_instance_by_cpu
from metrics import get_cpu_metric
from metrics import put_agr_metric
from metrics import get_memory_metric

session = boto3.session.Session()
logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    # initializing the clients
    ecs = session.client(service_name='ecs', region_name='eu-west-1')
    clw = session.client(service_name='cloudwatch', region_name='eu-west-1')
    # loading up the environment variables
    cluster_name = os.environ.get('ECS_CLUSTER')
    cpu_upscale_limit = os.environ.get('CPU_UPSCALE_LIMIT') if \
        os.environ.get('CPU_UPSCALE_LIMIT') else 80
    cpu_upscale_limit = int(cpu_upscale_limit)
    mem_upscale_limit = os.environ.get('MEM_UPSCALE_LIMIT') if \
        os.environ.get('MEM_UPSCALE_LIMIT') else 70
    mem_upscale_limit = int(mem_upscale_limit)
    cpu_downscale_limit = os.environ.get('CPU_DOWNSCALE_LIMIT') if \
        os.environ.get('CPU_DOWNSCALE_LIMIT') else 10
    cpu_downscale_limit = int(cpu_downscale_limit)
    mem_downscale_limit = os.environ.get('MEM_DOWNSCALE_LIMIT') if \
        os.environ.get('MEM_DOWNSCALE_LIMIT') else 30
    mem_downscale_limit = int(mem_downscale_limit)

    allow_scale_down = True if \
        os.environ.get('ALLOW_SCALE_DOWN') in ("True", "") else False
    allow_scale_up = True if \
        os.environ.get('ALLOW_SCALE_UP') in ("True", "") else False

    # upscale part

    """
      Counting average of cluster memory and cpu metrics data. Those are later
      used to compare with threshold.
    """

    instance_list = ecs.list_container_instances(
        cluster=cluster_name,
        status='ACTIVE')

    instances = ecs.describe_container_instances(
        cluster=cluster_name,
        containerInstances=instance_list['containerInstanceArns'])

    avg_memory_usage = 0
    avg_cpu_usage = 0

    for instance in instances['containerInstances']:
        avg_cpu_usage += get_cpu_metric(clw, instance['ec2InstanceId'])
        avg_memory_usage += get_memory_metric(clw, instance['ec2InstanceId'])

    avg_memory_usage = avg_memory_usage / len(instances)
    avg_cpu_usage = avg_cpu_usage / len(instances)

    """
       In this part we are going to find out it the biggest task would fit in
       our cluster. That means we always leave enough space in cluster for such
       a task. That seems as a waste but speeds up new deploy.
              
       In this case we need to find count of desired cpu/memory
       if the biggest task desires more cpu/memory than
       we have left in cluster, we have to scale up.
    """

    # collecting info about services in cluster
    services = ecs.list_services(
        cluster=cluster_name
    )

    # creating list of remaining capacities on each instance
    instances_remaining_capacities = []
    for instance in instances['containerInstances']:
        _instance_remaining_capacity = instance_capacity()
        _instance_remaining_capacity.instance_id = instance['ec2InstanceId']
        _instance_remaining_capacity.container_instance_id = instance['containerInstanceArn']
        for i in instance['remainingResources']:
            _instance_remaining_capacity.memory = i['integerValue'] \
                if i['name'] == 'MEMORY' else _instance_remaining_capacity.memory
            _instance_remaining_capacity.cpu = i['integerValue'] \
                if i['name'] == 'CPU' else _instance_remaining_capacity.cpu
        instances_remaining_capacities += [_instance_remaining_capacity]

    """
        Finding the fictitious biggest task by desired capacity of container,
        there is no task with both memory/cpu that big,
        this is just a combination of the values.
    """
    virtual_max_size_desired_capacity = task_capacity()

    # collecting info about tasks running in services in cluster
    tasks_arns_from_cluster_services = []
    for service in services['serviceArns']:
        running_service = ecs.describe_services(
            cluster=cluster_name, services=[service]
        )
        tasks_arns_from_cluster_services += [
            service['taskDefinition'] for service in running_service['services']
        ]

    for task_definition_arn in tasks_arns_from_cluster_services:
        container_memory_sum = 0
        container_cpu_sum = 0
        for container in ecs.describe_task_definition(
            taskDefinition=task_definition_arn
        )['taskDefinition']['containerDefinitions']:
            if "memory" in container.keys():
                container_memory_sum += container['memory']
            if "cpu" in container.keys():
                container_cpu_sum += container['cpu']

        virtual_max_size_desired_capacity.memory = container_memory_sum if \
            virtual_max_size_desired_capacity.memory < container_memory_sum else \
            virtual_max_size_desired_capacity.memory
        virtual_max_size_desired_capacity.cpu = container_cpu_sum if \
            virtual_max_size_desired_capacity.cpu < container_cpu_sum else \
            virtual_max_size_desired_capacity.cpu

    # scale up if there is no instance which can host the largest task
    scale_up_by_desired_memory = False
    if len(
        [
            i for i in instances_remaining_capacities if i.memory > virtual_max_size_desired_capacity.memory
        ]
    ) == 0:
        scale_up_by_desired_memory = True

    scale_up_by_desired_cpu = False
    if len(
        [
            i for i in instances_remaining_capacities if i.cpu > virtual_max_size_desired_capacity.cpu
        ]
    ) == 0:
        scale_up_by_desired_cpu = True

    # downscale part

    """
       If all the reserved capacity of a tasks in service on one server
       plus the capacity of the fictitious biggest task can be placed somewhere else
       there should be scale down.
    """

    tasks_arns_from_cluster = ecs.list_tasks(
        cluster=cluster_name
    )['taskArns']

    task_capacities = []
    for task in ecs.describe_tasks(
            cluster=cluster_name,
            tasks=tasks_arns_from_cluster
    )['tasks']:
        task_capacities += [
            task_capacity(
                task['memory'], task['cpu'],
                task['containerInstanceArn'],
                task['taskArn']
            )
        ]
    task_capacities_to_consider = task_capacities

    can_scale_down_by_reserved_memory = False
    can_scale_down_by_reserved_cpu = False

    # consider scaling down for memory and cpu
    for i in instances_remaining_capacities:
        # get capacities of the tasks on the instance
        tasks_on_the_instance = [
            task for task in task_capacities_to_consider
            if task.container_instance_id == i.container_instance_id
        ]
        # consider removing the instance by memory
        instance_combination_which_can_take_tasks_by_memory = consider_remove_instance_by_memory(
            tasks_on_the_instance +
            [  # adding the task which is imaginary the biggest in the cluster
                virtual_max_size_desired_capacity
            ],
            [  # create instance list by leaving out current isntance
                remaining_instances for remaining_instances
                in instances_remaining_capacities
                if remaining_instances != i
            ]
        )
        # consider removing the instance by cpu
        instance_combination_which_can_take_tasks_by_cpu = consider_remove_instance_by_cpu(
            tasks_on_the_instance +
            [  # adding the task which is imaginary the biggest in the cluster
                virtual_max_size_desired_capacity
            ],
            [  # create instance list by leaving out current isntance
                remaining_instances for remaining_instances
                in instances_remaining_capacities
                if remaining_instances != i
            ]
        )

        # if the combination is found, there is no need to continue
        if instance_combination_which_can_take_tasks_by_memory is not None:
            can_scale_down_by_reserved_memory = True
        if instance_combination_which_can_take_tasks_by_cpu is not None:
            can_scale_down_by_reserved_cpu = True
        if can_scale_down_by_reserved_cpu and can_scale_down_by_reserved_memory:
            break

    logger.info("Can scale UP cause of cpu usage: (avg_cpu_usage=" + str(avg_cpu_usage) + ") > (cpu_upscale_limit=" + str(cpu_upscale_limit) + ")") \
        if avg_cpu_usage > cpu_upscale_limit else \
        logger.info("Can NOT scale UP cause of cpu usage: (avg_cpu_usage=" + str(avg_cpu_usage) + ") <= (cpu_upscale_limit=" + str(cpu_upscale_limit) + ")")
    logger.info("Can scale UP cause of memory usage: (avg_memory_usage=" + str(avg_memory_usage) + ") > (memory_upscale_limit=" + str(mem_upscale_limit) + ")") \
        if avg_memory_usage > mem_upscale_limit else \
        logger.info("Can NOT scale UP cause of memory usage: (avg_memory_usage=" + str(avg_memory_usage) + ") <= (memory_upscale_limit=" + str(mem_upscale_limit) + ")")
    logger.info("Can scale UP cause of the new biggest task CPU (" + str(virtual_max_size_desired_capacity.cpu) + ") won't fit in current cluster reservations") \
        if scale_up_by_desired_cpu else \
        logger.info("Can NOT scale UP cause of the new biggest task CPU (" + str(virtual_max_size_desired_capacity.cpu) + ") would fit in current cluster reservations")
    logger.info("Can scale UP cause of the new biggest task MEMORY (" + str(virtual_max_size_desired_capacity.memory) + ") won't fit in current cluster reservations") \
        if scale_up_by_desired_memory else \
        logger.info("Can NOT scale UP cause of the new biggest task MEMORY (" + str(virtual_max_size_desired_capacity.memory) + ") would fit in current cluster reservations")


    logger.info("Can scale DOWN cause of cpu usage: (avg_cpu_usage=" + str(avg_cpu_usage) + ") < (cpu_downscale_limit=" + str(cpu_downscale_limit) + ")") \
        if avg_cpu_usage < cpu_downscale_limit else \
        logger.info("Can NOT scale DOWN cause of cpu usage: (avg_cpu_usage=" + str(avg_cpu_usage) + ") >= (cpu_downscale_limit: " + str(cpu_downscale_limit) + ")")
    logger.info("Can scale DOWN cause of memory usage: (avg_memory_usage=" + str(avg_memory_usage) + ") < (memory_downscale_limit=" + str(mem_downscale_limit) + ")") \
        if avg_memory_usage < mem_downscale_limit else \
        logger.info("Can NOT scale DOWN cause of memory usage: (avg_memory_usage=" + str(avg_memory_usage) + ") >= (memory_downscale_limit=" + str(mem_downscale_limit) + ")")

    logger.info("Can scale DOWN by reserved memory because there is at least one instance which have tasks which can be distributed to other instances") if can_scale_down_by_reserved_memory else \
        logger.info("Can NOT scale DOWN by reserved memory because there is no instance which have tasks which can be distributed to other instances")

    logger.info("Can scale DOWN by reserved CPU because there is at least one instance which have tasks which can be distributed to other instances") if can_scale_down_by_reserved_cpu else \
        logger.info("Can NOT scale DOWN by reserved CPU because there is no instance which have tasks which can be distributed to other instances")

    """
       This is very important: consider if cpu rises above
       the threshold but memory still lower than the threshold,
       that's why `or` is used.
    """

    if avg_cpu_usage > cpu_upscale_limit or \
            avg_memory_usage > mem_upscale_limit or \
            scale_up_by_desired_cpu or \
            scale_up_by_desired_memory and \
            allow_scale_up:
        logger.warning("Scaling up")
        put_agr_metric(clw, cluster_name, 1)

        """
           If the cpu goes bellow the threshold but memory still stays
           the same, do not scale down, all the conditions need to be met.
        """

    elif avg_cpu_usage < cpu_downscale_limit and \
            avg_memory_usage < mem_downscale_limit and \
            can_scale_down_by_reserved_memory and \
            can_scale_down_by_reserved_cpu and \
            allow_scale_down:
        logger.warning("Scaling down")
        put_agr_metric(clw, cluster_name, -1)
    else:
        put_agr_metric(clw, cluster_name, 0)
        logger.warning("Doing nothing")

    return {
        "statusCode": 200,
        "body": json.dumps('Ended correctly')
    }


if __name__ == "__main__":
    lambda_handler("", "")
