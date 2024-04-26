docker build -t flock-gcp -f Dockerfile.gcp .
docker tag flock-gcp gcr.io/on-demand-dots/flock
docker push gcr.io/on-demand-dots/flock
gcloud run deploy --image gcr.io/on-demand-dots/flock
