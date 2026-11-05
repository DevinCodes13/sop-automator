variable "region" {
  type    = string
  default = "us-east-1"
}

variable "instance_type" {
  type    = string
  default = "t4g.small"
}

variable "zone_name" {
  type    = string
  default = "aws.vulntrack.app"
}

variable "subdomain" {
  type    = string
  default = "sop"
}

variable "repo_url" {
  type    = string
  default = "https://github.com/DevinCodes13/sop-automator.git"
}

variable "ssm_prefix" {
  type    = string
  default = "/sop-automator"
}
