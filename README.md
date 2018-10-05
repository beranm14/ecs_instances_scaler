# Autoscaling of EC2 instances in ECS cluster setup

Once upon a time, I stumbled upon a task to scale up and down EC2 instances under the ECS. Scaling should consider physical load and desired capacity of tasks. This is done in few steps.

In the `main.py` you can see whole Lambda function which can be upload to AWS by terraform. Source code maybe misleading in some parts.

## Upscale and downscale according of current load

There is only one catch. I considered only CPU/Memory load for upscale as well as for downscale. This have to be done with extra care. Upscale can be done by one of the value reaching the threshold. The problem is downscale which can be done only if all of the values are bellow given threshold.

So for each of the metric -- CPU/Memory -- the average is count and compared to thresholds. If both CPU/Memory is lower than threshold, downscale could be on the was. For upscale, only one of those values can reach the threshold.

## Upscale and downscale according of reservations

Each instance in ECS have its predefined CPU and memory units to use. Those are called reservations. Each ECS task have some needs as well. If there are none, ECS task have zero for the value.

That means developers can deploy a task with memory and CPU reservation. Each task can be scaled up in case ECS scaling need to.

### Upscale

To upscale the EC2 instances, there have to be a task, which have bigger reservations than the cluster can offer. To be safe, some fictitious task which have the reservation in CPU and memory as the task which have the biggest reservation in CPU and memory is added. That means there is always a space for the new task. If developer creates new task with bigger reservation than the fictitious biggest task, he have to wait.

### Downscale

This is little bit tricky. To downscale, there have to be enough free units on the EC2 instances to accommodate all the tasks and the possible fictitious task and leave enough units on some instance which could be removed. This is considered in function called `consider_remove_instance_by_*`. 

## Scaling in ASG

If the Lambda function considers to upscale, it sends 1 to metric `AggregateScaleMetric`. In case of downscale, the -1 is sends. The alarms scaling is created by terraform, so it should add or remove the ec2 instance.

## FlowChart

![FlowChart](https://raw.githubusercontent.com/beranm14/ecs_instances_scaler/master/ecs_scale.png)

## Not solved problems

Developer can create a task, which is bigger than instance's units. That means no matter what scaling happens, it would fail to start the task. In this case, give up, inform the developer this is not good, remove his task and the cluster will scale down as well.

Also, this will not scale the tasks, that's the job of ECS scaling.
