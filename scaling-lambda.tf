data "aws_iam_policy_document" "lambda" {
  statement {
    effect = "Allow"

    actions = [
      "ecs:*",
      "cloudwatch:*",
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = [
      "*",
    ]
  }
}

data "archive_file" "dotfiles" {
  type        = "zip"
  output_path = "${path.module}/main.zip"

  source {
    content  = "${file("${path.module}/scaling_function/main.py")}"
    filename = "main.py"
  }

  source {
    content  = "${file("${path.module}/scaling_function/metrics.py")}"
    filename = "metrics.py"
  }

  source {
    content  = "${file("${path.module}/scaling_function/consider_remove_instance.py")}"
    filename = "consider_remove_instance.py"
  }

  source {
    content  = "${file("${path.module}/scaling_function/capacity_classes.py")}"
    filename = "capacity_classes.py"
  }
}

data "null_data_source" "path-to-some-file" {
  inputs {
    filename = "${substr("${path.module}/main.zip", length(path.cwd) + 1, -1)}"
  }
}

module "lambda" {
  source  = "telia-oss/lambda/aws"
  version = "0.2.0"

  name_prefix = "${ecs_cluster_name}-scaling-lambda"

  filename = "${data.null_data_source.path-to-some-file.outputs.filename}"

  environment = {
    CPU_UPSCALE_LIMIT   = "${var.upper_cpu_percentage_threashold}"
    CPU_DOWNSCALE_LIMIT = "${var.lower_cpu_percentage_threashold}"
    MEM_UPSCALE_LIMIT   = "${var.upper_ram_percentage_threashold}"
    MEM_DOWNSCALE_LIMIT = "${var.lower_ram_percentage_threashold}"
    ECS_CLUSTER         = "${var.ecs_cluster_name}"
    ALLOW_SCALE_DOWN    = "${var.allow_scale_down ? "True" : "False"}"
    ALLOW_SCALE_UP      = "${var.allow_scale_up ? "True" : "False"}"
  }

  handler = "main.lambda_handler"

  runtime = "python2.7"

  policy = "${data.aws_iam_policy_document.lambda.json}"
}

resource "aws_lambda_permission" "cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = "${module.lambda.arn}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.lambda.arn}"
}

resource "aws_cloudwatch_event_rule" "lambda" {
  name                = "${module.lambda.name}"
  schedule_expression = "rate(5 minutes)"
}

resource "aws_cloudwatch_event_target" "lambda" {
  target_id = "${module.lambda.name}"
  rule      = "${aws_cloudwatch_event_rule.lambda.name}"
  arn       = "${module.lambda.arn}"
}
