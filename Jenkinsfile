pipeline {
    agent any

    environment {
        AWS_DEFAULT_REGION = 'us-east-1'
        AWS_CREDENTIALS_ID = 'aws-credentials'
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'master', url: 'https://github.com/usuario/repositorio.git'
                script {
                    env.COMMIT_HASH = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
                }
            }
        }

        stage('Verify Commit') {
            steps {
                echo 'Verifying commit...'
                // Adicione aqui qualquer verificação ou teste que você precise
            }
        }

        stage('Build and Push Image to ECR') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: "${env.AWS_CREDENTIALS_ID}"]]) {
                    script {
                        def imageTag = "${env.BUILD_NUMBER}-${env.COMMIT_HASH}"
                        sh """
                        $(aws ecr get-login --no-include-email --region ${env.AWS_DEFAULT_REGION})
                        docker build -t ${env.ECR_REPO}:${imageTag} .
                        docker tag ${env.ECR_REPO}:${imageTag} ${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_DEFAULT_REGION}.amazonaws.com/${env.ECR_REPO}:${imageTag}
                        docker push ${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_DEFAULT_REGION}.amazonaws.com/${env.ECR_REPO}:${imageTag}
                        """
                        env.IMAGE_TAG = imageTag
                    }
                }
            }
        }

        stage('Model Type Check') {
            steps {
                script {
                    def config = readYaml file: 'config_model.yaml'
                    env.MODEL_TYPE = config.model_type
                    env.MODEL_NAME_PREFIX = config.model_name_prefix
                    env.ENDPOINT_CONFIG_NAME_PREFIX = config.endpoint_config_name_prefix
                    env.ENDPOINT_NAME_PREFIX = config.endpoint_name_prefix
                    env.INSTANCE_TYPE = config.inference.InstanceType
                    env.INITIAL_INSTANCE_COUNT = config.inference.InitialInstanceCount
                    env.S3_INPUT_BUCKET = config.s3.input_bucket
                    env.S3_OUTPUT_BUCKET = config.s3.output_bucket
                    env.S3_DATA_PREFIX = config.s3.data_prefix
                }
            }
        }

        stage('Create or Train Model') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: "${env.AWS_CREDENTIALS_ID}"]]) {
                    script {
                        if (env.MODEL_TYPE == 'pre-trained') {
                            sh """
                            aws sagemaker create-model \
                                --model-name ${env.MODEL_NAME_PREFIX}-${env.IMAGE_TAG} \
                                --primary-container Image=${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_DEFAULT_REGION}.amazonaws.com/${env.ECR_REPO}:${env.IMAGE_TAG} \
                                --execution-role-arn ${env.SAGEMAKER_ROLE}
                            """
                        } else {
                            sh """
                            aws sagemaker create-training-job \
                                --training-job-name ${env.MODEL_NAME_PREFIX}-training-${env.IMAGE_TAG} \
                                --algorithm-specification TrainingImage=${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_DEFAULT_REGION}.amazonaws.com/${env.ECR_REPO}:${env.IMAGE_TAG},TrainingInputMode=File \
                                --role-arn ${env.SAGEMAKER_ROLE} \
                                --input-data-config ChannelName=training,DataSource={S3DataSource={S3Uri=s3://${env.S3_INPUT_BUCKET}/${env.S3_DATA_PREFIX}, S3DataType=S3Prefix, S3DataDistributionType=FullyReplicated}},ContentType=csv \
                                --output-data-config S3OutputPath=s3://${env.S3_OUTPUT_BUCKET}/output \
                                --resource-config InstanceType=${env.INSTANCE_TYPE},InstanceCount=${env.INITIAL_INSTANCE_COUNT},VolumeSizeInGB=50 \
                                --stopping-condition MaxRuntimeInSeconds=3600
                            """
                        }
                    }
                }
            }
        }

        stage('Deploy to Staging') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: "${env.AWS_CREDENTIALS_ID}"]]) {
                    script {
                        sh """
                        aws sagemaker create-endpoint-config \
                            --endpoint-config-name ${env.ENDPOINT_CONFIG_NAME_PREFIX}-staging-config-${env.IMAGE_TAG} \
                            --production-variants VariantName=AllTraffic,ModelName=${env.MODEL_NAME_PREFIX}-${env.IMAGE_TAG},InitialInstanceCount=${env.INITIAL_INSTANCE_COUNT},InstanceType=${env.INSTANCE_TYPE}

                        aws sagemaker create-endpoint \
                            --endpoint-name ${env.ENDPOINT_NAME_PREFIX}-staging-${env.IMAGE_TAG} \
                            --endpoint-config-name ${env.ENDPOINT_CONFIG_NAME_PREFIX}-staging-config-${env.IMAGE_TAG}
                        """
                    }
                }
            }
        }

        stage('Model Evaluation') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: "${env.AWS_CREDENTIALS_ID}"]]) {
                    script {
                        echo 'Evaluating model...'
                        sh """
                        kubectl run evaluate-model-${env.IMAGE_TAG} --image=${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_DEFAULT_REGION}.amazonaws.com/${env.ECR_REPO}:${env.IMAGE_TAG} --restart=Never --namespace=default -- /bin/sh -c 'python evaluate.py'
                        """
                    }
                }
            }
        }

        stage('Deploy to Production') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: "${env.AWS_CREDENTIALS_ID}"]]) {
                    script {
                        sh """
                        aws sagemaker create-endpoint-config \
                            --endpoint-config-name ${env.ENDPOINT_CONFIG_NAME_PREFIX}-prod-config-${env.IMAGE_TAG} \
                            --production-variants VariantName=AllTraffic,ModelName=${env.MODEL_NAME_PREFIX}-${env.IMAGE_TAG},InitialInstanceCount=${env.INITIAL_INSTANCE_COUNT},InstanceType=${env.INSTANCE_TYPE}

                        aws sagemaker create-endpoint \
                            --endpoint-name ${env.ENDPOINT_NAME_PREFIX}-prod-${env.IMAGE_TAG} \
                            --endpoint-config-name ${env.ENDPOINT_CONFIG_NAME_PREFIX}-prod-config-${env.IMAGE_TAG}
                        """
                    }
                }
            }
        }
    }
}
