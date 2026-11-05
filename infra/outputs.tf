output "instance_id" {
  value = aws_instance.app.id
}

output "public_ip" {
  value = aws_eip.app.public_ip
}

output "url" {
  value = "https://${aws_route53_record.app.fqdn}"
}

output "session_command" {
  value = "aws ssm start-session --region ${var.region} --target ${aws_instance.app.id}"
}
