#!/bin/bash
echo ${account_id}

# Install required utilities, can add more
yum install git -y
yum install jq -y
yum install postgresql -y
yum install unzip -y
yum install wget -y
sudo yum install golang -y

curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install


