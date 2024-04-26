import os
import argparse
from google.cloud import storage
from google.oauth2 import service_account
from google.cloud import run_v1, run_v2
from google.protobuf import field_mask_pb2 as field_mask
# import googleapiclient.discovery

def create_service_account(project_id, name, display_name):
    """Creates a service account."""
    credentials = service_account.Credentials.from_service_account_file(
        filename=os.environ['GOOGLE_APPLICATION_CREDENTIALS'],
        scopes=['https://www.googleapis.com/auth/cloud-platform'])

    service = googleapiclient.discovery.build(
        'iam', 'v1', credentials=credentials)

    my_service_account = service.projects().serviceAccounts().create(
        name='projects/' + project_id,
        body={
            'accountId': name,
            'serviceAccount': {
                'displayName': display_name
            }
        }).execute()

    print('Created service account: ' + my_service_account['email'])
    return my_service_account

def download_blob(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)

    blob.download_to_filename(destination_file_name)

    print(f'Blob {source_blob_name} downloaded to {destination_file_name}.')


def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

    print(f'File {source_file_name} uploaded to {bucket_name}/{destination_blob_name}.')


def upload_string(bucket_name, content, destination_blob_name):
    """Upload a string to the specified GCP bucket."""
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_string(content)

    print(f"String content uploaded to {destination_blob_name} in bucket {bucket_name}.")


def download_string(bucket_name, source_blob_name):
    """Download a string from the specified GCP bucket."""
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(source_blob_name)

    content = blob.download_as_text()

    print(f"String content downloaded from {source_blob_name} in bucket {bucket_name}:")
    print(content)
    return content


def create_bucket(bucket_name, region="us-west2"):
    storage_client = storage.Client()
    try:
        bucket = storage_client.bucket(bucket_name)
        if not bucket.exists():
            bucket.create(location=region)
            print(f"Bucket {bucket_name} created in region {region}")
    except Exception as e:
        print(f"Error creating bucket {bucket_name}. Exception: {e}")
        raise e

def deploy_container(project_id, image_name, service_name, region='us-west1'):
    """
    Deploy a Docker container to Google Cloud Run.
    
    :param project_id: The ID of your Google Cloud project.
    :param image_name: The name of the Docker image to deploy.
    :param service_name: The name of the Cloud Run service.
    :param region: The region where the Cloud Run service will be deployed.
    """
    client = run_v1.ServicesClient()
    parent = f"namespaces/{project_id}"
    
    service = run_v1.Service(
        api_version='serving.knative.dev/v1',
        kind='Service',
        metadata=run_v1.ObjectMeta(name=f"{service_name}", namespace=project_id),
        spec=run_v1.ServiceSpec(
            template=run_v1.RevisionTemplate(
                spec=run_v1.RevisionSpec(
                    containers=[run_v1.Container(image=image_name)],
                )
            )
        )
    )
    
    update_mask = field_mask.FieldMask(paths=['spec.template.spec.containers'])
    
    try:
        response = client.replace_service(service=service, name=f"{parent}/services/{service_name}", update_mask=update_mask)
        print(f"Service {service_name} has been deployed.")
    except Exception as e:
        print(f"Error deploying service {service_name}: {e}")


# from google.cloud import run_v2

# def sample_create_service():
#     # Create a client
#     client = run_v2.ServicesClient()

#     # Initialize request argument(s)
#     request = run_v2.CreateServiceRequest(
#         parent="parent_value",
#         service_id="service_id_value",
#     )

#     # Make the request
#     operation = client.create_service(request=request)

#     print("Waiting for operation to complete...")

#     response = operation.result()

#     # Handle the response
#     print(response)



if __name__ == '__main__':
    # func_name = "flock"
    # for i in range(30):
    #     bucket_name = f"flock-gcp-serverless-storage-user{i}"
    #     create_bucket(bucket_name)


    # Replace with your project ID, Docker image name, and service name
    project_id = 'your-project-id'
    image_name = 'gcr.io/your-project-id/your-image-name'
    service_name = 'your-service-name'

    deploy_container(project_id, image_name, service_name)