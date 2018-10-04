variable "upper_cpu_percentage_threashold" {
  description = "Percentage threashold which should be crossed to upscale the cluster"
  default     = 75
}

variable "lower_cpu_percentage_threashold" {
  description = "Percentage threashold which should be crossed to downscale the cluster"
  default     = 5
}

variable "count_evaluation_periods" {
  description = "How many periods should the AVG of cluster utilization be above given threashold"
  default     = 1
}

variable "evaluation_period" {
  description = "The length of one period given in seconds"
  default     = 60
}

variable "upper_ram_percentage_threashold" {
  description = "Percentage threashold which should be crossed to upscale the cluster"
  default     = 75
}

variable "lower_ram_percentage_threashold" {
  description = "Percentage threashold which should be crossed to downscale the cluster"
  default     = 20
}

variable "upscale_count" {
  description = "How many instances should be created for upscale"
  default     = 1
}

variable "downscale_count" {
  description = "How many instances should be removed for downscale"
  default     = -1
}

variable "cooldown" {
  description = "Cooldown period after scaling"
  default     = 300
}

variable "enable_scaling" {
  description = "Enable cpu/ram scaling"
  default     = false
}

variable "ecs_cluster_name" {
  description = "Name of cluster to be scaled"
}

variable "autoscaling_group_name" {
  description = "Autoscaling group name which should be scaled"
}

variable "allow_scale_up" {
  description = "Allow scale up of the instances"
  default     = true
}

variable "allow_scale_down" {
  description = "Allow scale down of the instances"
  default     = true
}
