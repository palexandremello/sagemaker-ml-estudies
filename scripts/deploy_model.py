import boto3
import sagemaker
from sagemaker.model import Model
from sagemaker.s3 import S3Uploader, s3_path_join
import os
import yaml
import sys

def deploy_model(config_path):
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)

    model_name = config['model_name']
    entry_point = config['entry_point']
    instance_type = config['instance_type']
    
    s3_bucket = os.getenv('S3_BUCKET')
    model_tar_path = f"s3://{s3_bucket}/{model_name}/model.tar.gz"
    
    role = os.getenv('SAGEMAKER_EXECUTION_ROLE')
    image_uri = os.getenv('IMAGE_URI')

    if not all([s3_bucket, role, image_uri]):
        raise ValueError("S3_BUCKET, SAGEMAKER_EXECUTION_ROLE, and IMAGE_URI environment variables must be set")

    huggingface_model = Model(
        model_data=model_tar_path,
        role=role,
        image_uri=image_uri,
        entry_point=f'models/{model_name}/{entry_point}'
    )

    predictor = huggingface_model.deploy(
        initial_instance_count=1,
        instance_type=instance_type,
        endpoint_name=f'{model_name}-endpoint'
    )

    print(f"Model {model_name} deployed to endpoint: {model_name}-endpoint")

def main():
    if len(sys.argv) != 2:
        raise ValueError("Usage: upload_and_deploy_model.py <model_name>")
    model_name = sys.argv[1]
    config_path = os.path.join('models', model_name, 'config.yml')
    if os.path.exists(config_path):
        deploy_model(config_path)
    else:
        print(f"No config file found for model {model_name}")

if __name__ == "__main__":
    main()
