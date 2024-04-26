docker build -t flock-aws -f Dockerfile.aws .
docker tag flock-aws 270448519663.dkr.ecr.us-west-1.amazonaws.com/flock-aws
docker push 270448519663.dkr.ecr.us-west-1.amazonaws.com/flock-aws
python3 ./deploy/deploy_aws.py

# aws ecr get-login-password --region us-west-1 | docker login --username AWS --password-stdin 270448519663.dkr.ecr.us-west-1.amazonaws.com/flock-aws