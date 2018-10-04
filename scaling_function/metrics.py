"""This file contains only the metrics functions for AWS CloudWatch."""
import datetime
import dateutil

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
        Period=1,
        Statistics=[
            'Average',
        ],
        Unit='Percent'
    )
    cpu_avg = 0
    for cpu in response['Datapoints']:
        if 'Average' in cpu:
            cpu_avg += cpu['Average']
    return cpu_avg / len(response['Datapoints'])


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
        Period=1,
        Statistics=[
            'Average',
        ],
        Unit='Percent'
    )
    memory_avg = 0
    for memory in response['Datapoints']:
        if 'Average' in memory:
            memory_avg += memory['Average']
    return memory_avg / len(response['Datapoints'])
