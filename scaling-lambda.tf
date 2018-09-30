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

data "archive_file" "main" {
  type        = "zip"
  source_file = "main.py"
  output_path = "main.zip"
}

module "lambda" {
  source  = "telia-oss/lambda/aws"
  version = "0.2.0"

  name_prefix = "${ecs_cluster_name}-scaling-lambda"

  filename = "main.zip"

  environment = {
    CPU_UPSCALE_LIMIT   = "${var.upper_cpu_percentage_threashold}"
    CPU_DOWNSCALE_LIMIT = "${var.lower_cpu_percentage_threashold}"
    MEM_UPSCALE_LIMIT   = "${var.upper_ram_percentage_threashold}"
    MEM_DOWNSCALE_LIMIT = "${var.lower_ram_percentage_threashold}"
    ECS_CLUSTER         = "${var.ecs_cluster_name}"
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
