docker build --platform linux/amd64 -t sijuntan/flock:aws -f Dockerfile.aws .
docker tag sijuntan/flock:aws 270448519663.dkr.ecr.us-west-1.amazonaws.com/flock:latest
docker push 270448519663.dkr.ecr.us-west-1.amazonaws.com/flock:latest
python3 deploy_aws.py

docker build --platform linux/amd64 -t sijuntan/flock:ubuntu -f Dockerfile.ubuntu .
docker push sijuntan/flock:ubuntu
gcloud run deploy flock --image sijuntan/flock:ubuntu --port 5000 --command "python3" --args "handler.py,-p,5000,-s,gcp" --region us-west2