import json
import logging
import os
import boto3
import datetime
import pprint
import dateutil


def empty_copy(obj):
    class Empty(obj.__class__):
        def __init__(self):
            pass
    newcopy = Empty()
    newcopy.__class__ = obj.__class__
    return newcopy


class instance_capacity:
    def __init__(self, memory=0, cpu=0, container_instance_id=""):
        self.cpu = int(cpu)
        self.memory = int(memory)
        self.instance_id = ""
        self.container_instance_id = container_instance_id

    def __str__(self):
        return "id:" + self.container_instance_id + " cpu:" + str(self.cpu) + " mem:" + str(self.memory)

    def __repr__(self):
        return "id:" + self.container_instance_id + " cpu:" + str(self.cpu) + " mem:" + str(self.memory)

    def __eq__(self, other):
        return self.container_instance_id == other.container_instance_id

    def __copy__(self, memodict={}):
        copy_object = empty_copy(self)
        copy_object.cpu = self.cpu
        copy_object.memory = self.memory
        copy_object.instance_id = self.instance_id
        copy_object.container_instance_id = self.container_instance_id
        return copy_object


class task_capacity:
    def __init__(self, memory=0, cpu=0, container_instance_id="", task_arn=""):
        self.cpu = int(cpu)
        self.memory = int(memory)
        self.container_instance_id = container_instance_id
        self.task_arn = task_arn

    def __str__(self):
        return "cpu:" + str(self.cpu) + " mem:" + str(self.memory)

    def __repr__(self):
        return "container_instance_id: " + self.container_instance_id + " cpu:" + str(self.cpu) + " mem:" + str(self.memory)

    def __eq__(self, other):
        return self.task_arn == other.task_arn

    def __copy__(self, memodict={}):
        copy_object = empty_copy(self)
        copy_object.cpu = self.cpu
        copy_object.memory = self.memory
        copy_object.task_arn = self.task_arn
        copy_object.container_instance_id = self.container_instance_id
        return copy_object


def consider_remove_instance_by_memory(tasks, instances):
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


def get_cpu_metric(clw, instance_id):
    response = clw.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName='CPUUtilization',
        Dimensions=[
            {
                'Name': 'InstanceId',
                'Value': instance_id
            },
        ],
        StartTime=(
            datetime.datetime.now(
                dateutil.tz.tzlocal()
            ) -
            datetime.timedelta(seconds=600)).strftime("%s"),
        EndTime=datetime.datetime.now(
            dateutil.tz.tzlocal()
        ).strftime("%s"),
        Period=86400,
        Statistics=[
            'Average',
        ],
        Unit='Percent'
    )
    for cpu in response['Datapoints']:
        if 'Average' in cpu:
            return (cpu['Average'])


def put_agr_metric(clw, cluster, value):
    clw.put_metric_data(
        Namespace='AWS/ECS',
        MetricData=[{
            'MetricName': 'AggregateScaleMetric',
            'Dimensions': [{
                'Name': 'ClusterName',
                'Value': cluster
            }],
            'Timestamp': datetime.datetime.now(
                dateutil.tz.tzlocal()),
            'Value': value
        }])


def get_memory_metric(clw, instance_id):
    response = clw.get_metric_statistics(
        Namespace='CWAgent',
        MetricName='mem_used_percent',
        Dimensions=[
            {
                'Name': 'InstanceId',
                'Value': instance_id
            },
        ],
        StartTime=(
            datetime.datetime.now(
                dateutil.tz.tzlocal()
            ) -
            datetime.timedelta(seconds=600)).strftime("%s"),
        EndTime=datetime.datetime.now(
            dateutil.tz.tzlocal()
        ).strftime("%s"),
        Period=86400,
        Statistics=[
            'Average',
        ],
        Unit='Percent'
    )
    for cpu in response['Datapoints']:
        if 'Average' in cpu:
            return (cpu['Average'])


session = boto3.session.Session()
logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    ecs = session.client(service_name='ecs', region_name='eu-west-1')
    clw = session.client(service_name='cloudwatch', region_name='eu-west-1')
    cluster_name = os.environ.get('ECS_CLUSTER')
    cpu_upscale_limit = os.environ.get('CPU_UPSCALE_LIMIT') if \
        os.environ.get('CPU_UPSCALE_LIMIT') else 80
    mem_upscale_limit = os.environ.get('MEM_UPSCALE_LIMIT') if \
        os.environ.get('MEM_UPSCALE_LIMIT') else 70
    cpu_downscale_limit = os.environ.get('CPU_DOWNSCALE_LIMIT') if \
        os.environ.get('CPU_DOWNSCALE_LIMIT') else 10
    mem_downscale_limit = os.environ.get('MEM_DOWNSCALE_LIMIT') if \
        os.environ.get('MEM_DOWNSCALE_LIMIT') else 30

    # Creating combination of metrics to make cluster scale up
    #  the cluster nodes, not the services but instances!

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
    # logger.info("avg_memory_usage: " + str(avg_memory_usage))
    # logger.info("avg_cpu_usage: " + str(avg_cpu_usage))

    # in this case we need to find count of desired cpu/memory
    #  if the biggest task desires more cpu/memory than
    #  we have left in cluster, we have to scale up

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

    # find ficticious the biggest task by desired capacity of container
    # there is no task with both memory/cpu that big
    # this is just a combination of the values
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

    #  if all the reserved capacity of a tasks in service on one server
    #  plus the capacity of the biggest task can be placed somewhere else
    #  there should be scale down

    tasks_arns_from_cluster = ecs.list_tasks(
        cluster=cluster_name
    )['taskArns']

    # pprint.pprint(tasks_arns_from_cluster)

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

    # consider scaling down for memory
    for i in instances_remaining_capacities:
        # get capacities of the tasks on the instance
        tasks_on_the_instance = [
            task for task in task_capacities_to_consider
            if task.container_instance_id == i.container_instance_id
        ]
        instance_combination_which_can_take_tasks_by_memory = consider_remove_instance_by_memory(
            tasks_on_the_instance +
            [  # adding the task which is imaginary the biggest in the cluster
                virtual_max_size_desired_capacity
            ],
            [
                remaining_instances for remaining_instances
                in instances_remaining_capacities
                if remaining_instances != i
            ]
        )
        instance_combination_which_can_take_tasks_by_cpu = consider_remove_instance_by_cpu(
            tasks_on_the_instance +
            [  # adding the task which is imaginary the biggest in the cluster
                virtual_max_size_desired_capacity
            ],
            [
                remaining_instances for remaining_instances
                in instances_remaining_capacities
                if remaining_instances != i
            ]
        )
        
        if instance_combination_which_can_take_tasks_by_memory is not None:
            can_scale_down_by_reserved_memory = True
        if instance_combination_which_can_take_tasks_by_cpu is not None:
            can_scale_down_by_reserved_cpu = True
        if can_scale_down_by_reserved_cpu and can_scale_down_by_reserved_memory:
            break

    logger.info("Could scale up cause of cpu usage: avg cpu usage: " + str(avg_cpu_usage) + " > cpu upscale limit: " + str(cpu_upscale_limit)) \
        if avg_cpu_usage > cpu_upscale_limit else \
        logger.info("Could NOT scale up cause of cpu usage: avg cpu usage: " + str(avg_cpu_usage) + " <= cpu upscale limit: " + str(cpu_upscale_limit))
    logger.info("Could scale up cause of memory usage: avg memory usage: " + str(avg_memory_usage) + " > memory upscale limit: " + str(mem_upscale_limit)) \
        if avg_memory_usage > mem_upscale_limit else \
        logger.info("Could NOT scale up cause of cpu usage: avg memory usage: " + str(avg_memory_usage) + " <= memory upscale limit: " + str(mem_upscale_limit))
    logger.info("Have to scale up cause of the new biggest task CPU (" + str(virtual_max_size_desired_capacity.cpu) + ") won't fit in current cluster reservation") if scale_up_by_desired_cpu else \
        logger.info("Won't scale up cause of the new biggest task CPU (" + str(virtual_max_size_desired_capacity.cpu) + ") would fit in current cluster reservation")
    logger.info("Have to scale up cause of the new biggest task MEMORY (" + str(virtual_max_size_desired_capacity.memory) + ") won't fit in current cluster reservation") if scale_up_by_desired_memory else \
        logger.info("Won't scale up cause of the new biggest task MEMORY (" + str(virtual_max_size_desired_capacity.memory) + ") would fit in current cluster reservation")


    logger.info("Could scale down cause of cpu usage: avg cpu usage: " + str(avg_cpu_usage) + " < cpu downscale limit: " + str(cpu_downscale_limit)) \
        if avg_cpu_usage < cpu_downscale_limit else \
        logger.info("Could NOT scale down cause of cpu usage: avg cpu usage: " + str(avg_cpu_usage) + " >= cpu downscale limit: " + str(cpu_downscale_limit))
    logger.info("Could scale down cause of memory usage: avg memory usage: " + str(avg_memory_usage) + " < memory downscale limit: " + str(mem_downscale_limit)) \
        if avg_memory_usage < mem_downscale_limit else \
        logger.info("Could NOT scale down cause of memory usage: avg memory usage: " + str(avg_memory_usage) + " >= memory downscale limit: " + str(mem_downscale_limit))

    logger.info("Can scale down by reserved MEMORY because there is at least one instance which have tasks which can be distributed to other instances") if can_scale_down_by_reserved_memory else \
        logger.info("Could not scale down by reserved MEMORY because there is no instance which have tasks which can be distributed to other instances")

    logger.info("Can scale down by reserved CPU because there is at least one instance which have tasks which can be distributed to other instances") if can_scale_down_by_reserved_cpu else \
        logger.info("Could not scale down by reserved CPU because there is no instance which have tasks which can be distributed to other instances")


    # this is very important, consider cpu rising above
    #  the threashold but memory still low,
    #  that's why `or` is used

    if avg_cpu_usage > cpu_upscale_limit or \
            avg_memory_usage > mem_upscale_limit or \
            scale_up_by_desired_cpu or \
            scale_up_by_desired_memory:
        put_agr_metric(clw, cluster_name, 1)

    # if the cpu goes bellow but memory still stays
    #  the same, do not scale

    elif avg_cpu_usage < cpu_downscale_limit and \
            avg_memory_usage < mem_downscale_limit and \
            can_scale_down_by_reserved_memory and \
            can_scale_down_by_reserved_cpu:
        put_agr_metric(clw, cluster_name, -1)

    else:
        put_agr_metric(clw, cluster_name, 0)

    return {
        "statusCode": 200,
        "body": json.dumps('Ended correctly')
    }

#
# THIS IS A TEST CASE for downscale combinations
#

# pprint.pprint(
#     consider_remove_instance_by_cpu(
#         [
#             task_capacity(80, 80, "task_a", "task_a"),
#             task_capacity(50, 50, "task_b", "task_b")
#         ],
#         [
#             instance_capacity(100, 100, "instance_1"),
#             instance_capacity(100, 100, "instance_2")
#         ]
#     )
# )
# pprint.pprint(
#     consider_remove_instance_by_memory(
#         [
#             task_capacity(80, 80, "task_a", "task_a"),
#             task_capacity(50, 50, "task_b", "task_b")
#         ],
#         [
#             instance_capacity(100, 100, "instance_1"),
#             instance_capacity(100, 100, "instance_2")
#         ]
#     )
# )

lambda_handler("", "")
