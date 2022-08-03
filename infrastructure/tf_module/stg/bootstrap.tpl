#!/bin/bash
echo ECS_CLUSTER=${cluster_name} >> /etc/ecs/ecs.config

# Install required utilities, can add more
yum install git -y
yum install jq -y
yum install postgresql -y