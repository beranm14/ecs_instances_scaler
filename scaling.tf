# Creating policies and metrics for scaling

# CPU scaling

# up

resource "aws_autoscaling_policy" "ecs_policy_up" {
  count = "${var.enable_scaling && var.upscale_count != 0 ? 1 : 0}"

  name                   = "${var.ecs_cluster_name}-scaling-metric-policy-up"
  scaling_adjustment     = "${var.upscale_count}"
  adjustment_type        = "ChangeInCapacity"
  cooldown               = "${var.cooldown}"
  autoscaling_group_name = "${module.cluster.asg_id}"
}

resource "aws_cloudwatch_metric_alarm" "ecs_metric_alarm_up" {
  count = "${var.enable_scaling && var.upscale_count != 0 ? 1 : 0}"

  alarm_name          = "${var.ecs_cluster_name}-scaling-metric-up"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "${var.count_evaluation_periods}"
  metric_name         = "AggregateScaleMetric"
  namespace           = "AWS/ECS"
  period              = "${var.evaluation_period}"
  statistic           = "Average"
  threshold           = "0"

  dimensions {
    ClusterName = "${var.ecs_cluster_name}"
  }

  alarm_description = "This metric monitors ec2 utilization to upscale"
  alarm_actions     = ["${aws_autoscaling_policy.ecs_policy_up.arn}"]
}

# down

resource "aws_autoscaling_policy" "ecs_policy_down" {
  count = "${var.enable_scaling && var.downscale_count != 0 ? 1 : 0}"

  name                   = "${var.ecs_cluster_name}-scaling-metric-policy-down"
  scaling_adjustment     = "${var.downscale_count}"
  adjustment_type        = "ChangeInCapacity"
  cooldown               = "${var.cooldown}"
  autoscaling_group_name = "${var.autoscaling_group_name}"
}

resource "aws_cloudwatch_metric_alarm" "ecs_metric_alarm_down" {
  count = "${var.enable_scaling && var.downscale_count != 0 ? 1 : 0}"

  alarm_name          = "${var.ecs_cluster_name}-scaling-metric-down"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "${var.count_evaluation_periods}"
  metric_name         = "AggregateScaleMetric"
  namespace           = "AWS/ECS"
  period              = "${var.evaluation_period}"
  statistic           = "Average"
  threshold           = "0"

  dimensions {
    ClusterName = "${var.ecs_cluster_name}"
  }

  alarm_description = "This metric monitors ec2 utilization to downscale"
  alarm_actions     = ["${aws_autoscaling_policy.ecs_policy_down.arn}"]
}
