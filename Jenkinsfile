pipeline {
    agent any

    environment {
        AWS_DEFAULT_REGION = 'us-east-1'
        AWS_CREDENTIALS_ID = 'aws-credentials'
        DOMAIN_ID = 'd-g6d3q693r6ep'
        SLACK_CHANNEL = '#jenkins-deploys-models' // Substitua pelo seu canal do Slack
        SLACK_CREDENTIALS_ID = 'jenkins-slack' // Substitua pelo ID das suas credenciais do Slack configuradas no Jenkins
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/palexandremello/sagemaker-ml-estudies'
                script {
                    env.COMMIT_HASH = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
                }
            }
        }

        stage('Set Environment Variables from Parameter Store') {
            steps {
                withCredentials([[
                    $class: 'AmazonWebServicesCredentialsBinding',
                    credentialsId: "${env.AWS_CREDENTIALS_ID}"
                ]]) {
                    script {
                        def params = [
                            'aws-account-id',
                            'ecr-repo',
                            'sagemaker-role',
                        ]
                        params.each { param ->
                            def command = "aws ssm get-parameter --name /sagemaker-byoc-builder/dev/${param} --with-decryption --query Parameter.Value --output text"
                            def value = sh(returnStdout: true, script: command).trim()
                            env."${param.replace('-', '_').toUpperCase()}" = value
                        }
                    }
                }
            }
        }

        stage('Load Configuration') {
            steps {
                script {
                    def config = readYaml file: 'config_model.yaml'
                    env.PROJECT_NAME = config.project_name
                    env.S3_BUCKET_NAME = config.s3.bucket_name
                    env.DATA_PREFIX = config.s3.data_prefix
                    env.MODEL_PREFIX = config.s3.model_prefix
                    env.INFERENCE_PREFIX = config.s3.inference_prefix
                    env.TRAINING_DATA_PATH = config.data.training
                    env.VALIDATION_DATA_PATH = config.data.validation
                    env.MODEL_NAME = config.models.model_name
                    env.TRAINING_JOB_NAME_PREFIX = config.training.training_job_name_prefix
                    env.INSTANCE_TYPE = config.sagemaker.instance_type
                    env.INITIAL_INSTANCE_COUNT = config.sagemaker.initial_instance_count.toString()
                    env.MAX_RUNTIME = config.sagemaker.max_runtime_in_seconds.toString()
                    env.MODEL_PACKAGE_GROUP_NAME = config.sagemaker.model_package_group_name
                    env.APPROVAL_STATUS = config.sagemaker.approval_status
                    env.INFERENCE_INSTANCE_TYPE = config.sagemaker.inference_instance_type
                    env.INFERENCE_INITIAL_INSTANCE_COUNT = config.sagemaker.inference_initial_instance_count.toString()
                    env.HYPER_PARAMETERS = config.training.hyper_parameters
                    env.SAGEMAKER_ENV = config.sagemaker.environment
                }
            }
        }

        stage('Create ECR Repository if not exists') {
            steps {
                withCredentials([[
                    $class: 'AmazonWebServicesCredentialsBinding',
                    credentialsId: "${env.AWS_CREDENTIALS_ID}"
                ]]) {
                    script {
                        def repoExists = sh(
                            script: "aws ecr describe-repositories --repository-names ${env.ECR_REPO} --region ${env.AWS_DEFAULT_REGION}",
                            returnStatus: true
                        ) == 0

                        if (!repoExists) {
                            sh "aws ecr create-repository --repository-name ${env.ECR_REPO} --region ${env.AWS_DEFAULT_REGION}"
                        }
                    }
                }
            }
        }

        stage('Build and Push Image to ECR') {
            steps {
                withCredentials([[
                    $class: 'AmazonWebServicesCredentialsBinding',
                    credentialsId: "${env.AWS_CREDENTIALS_ID}"
                ]]) {
                    script {
                    
                        def buildDate = sh(script: "date +%Y%m%d%H%M%S", returnStdout: true).trim()
                        def imageTag = "${env.BUILD_NUMBER}-${buildDate}"
                        echo "Dockerfile modified. Building new image."
                        sh """
                        aws ecr get-login-password --region ${env.AWS_DEFAULT_REGION} | docker login --username AWS --password-stdin ${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_DEFAULT_REGION}.amazonaws.com
                        docker build -t ${env.ECR_REPO}:${imageTag} .
                        docker tag ${env.ECR_REPO}:${imageTag} ${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_DEFAULT_REGION}.amazonaws.com/${env.ECR_REPO}:${imageTag}
                        docker push ${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_DEFAULT_REGION}.amazonaws.com/${env.ECR_REPO}:${imageTag}
                        """
                        env.IMAGE_TAG = imageTag
                    }
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
                                --primary-container Image=${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_DEFAULT_REGION}.amazonaws.com/${env.ECR_REPO}:${env.IMAGE_TAG},ModelDataUrl=s3://${env.MODEL_PATH} \
                                --execution-role-arn ${env.SAGEMAKER_ROLE}
                            """
                        } else {
                            def trainingDataUri = "s3://${env.S3_BUCKET_NAME}/${env.PROJECT_NAME}/${env.DATA_PREFIX}/${env.TRAINING_DATA_PATH}"
                            def validationDataUri = "s3://${env.S3_BUCKET_NAME}/${env.PROJECT_NAME}/${env.DATA_PREFIX}/${env.VALIDATION_DATA_PATH}"
                            def outputUri = "s3://${env.S3_BUCKET_NAME}/${env.PROJECT_NAME}/${env.MODEL_PREFIX}"

                            sh """
                            aws sagemaker create-training-job \
                                --training-job-name ${env.TRAINING_JOB_NAME_PREFIX}-${env.IMAGE_TAG} \
                                --algorithm-specification TrainingImage=${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_DEFAULT_REGION}.amazonaws.com/${env.ECR_REPO}:${env.IMAGE_TAG},TrainingInputMode=File \
                                --role-arn ${env.SAGEMAKER_ROLE} \
                                --input-data-config ChannelName=training,DataSource={S3DataSource={S3Uri=${trainingDataUri},S3DataType=S3Prefix,S3DataDistributionType=FullyReplicated}},ContentType=csv \
                                --output-data-config S3OutputPath=${outputUri} \
                                --resource-config InstanceType=${env.INSTANCE_TYPE},InstanceCount=${env.INITIAL_INSTANCE_COUNT},VolumeSizeInGB=50 \
                                --stopping-condition MaxRuntimeInSeconds=${env.MAX_RUNTIME}
                            """

                            timeout(time: 1, unit: 'HOURS') { // Ajuste conforme necessário
                                waitUntil {
                                    script {
                                        def trainingJobStatus = sh(
                                            script: "aws sagemaker describe-training-job --training-job-name ${env.TRAINING_JOB_NAME_PREFIX}-${env.IMAGE_TAG} --query 'TrainingJobStatus' --output text",
                                            returnStdout: true
                                        ).trim()

                                        echo "Training Job Status: ${trainingJobStatus}"
                                        return trainingJobStatus == 'Completed'
                                    }
                                }
                                sleep time: 30, unit: 'SECONDS' // Ajuste conforme necessário
                            }

                            sh """
                            aws sagemaker create-model \
                                --model-name ${env.MODEL_NAME}-${env.IMAGE_TAG} \
                                --primary-container Image=${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_DEFAULT_REGION}.amazonaws.com/${env.ECR_REPO}:${env.IMAGE_TAG},ModelDataUrl=${outputUri}/${env.TRAINING_JOB_NAME_PREFIX}-${env.IMAGE_TAG}/output/model.tar.gz \
                                --execution-role-arn ${env.SAGEMAKER_ROLE}
                            """

                            def modelPackageGroupName = "${env.MODEL_PACKAGE_GROUP_NAME}"
                            def modelPackageGroupExists = sh(
                                script: """
                                    aws sagemaker list-model-package-groups --name-contains ${modelPackageGroupName} \
                                    --query 'ModelPackageGroupSummaryList[?ModelPackageGroupName==`'${modelPackageGroupName}'`].ModelPackageGroupName' \
                                    --output text
                                """,
                                returnStdout: true
                            ).trim()

                            if (!modelPackageGroupExists) {
                                echo "Creating model package group: ${modelPackageGroupName}"
                                sh """
                                aws sagemaker create-model-package-group \
                                    --model-package-group-name ${modelPackageGroupName} \
                                    --model-package-group-description "Group for all models of ${env.PROJECT_NAME}"
                                """
                            } else {
                                echo "Model package group ${modelPackageGroupName} already exists."
                            }

                            sh """
                            aws sagemaker create-model-package \
                                --model-package-group-name ${env.MODEL_PACKAGE_GROUP_NAME} \
                                --model-package-description "Model package for ${env.MODEL_NAME}-${env.IMAGE_TAG}" \
                                --model-approval-status ${env.APPROVAL_STATUS} \
                                --inference-specification '{
                                    "Containers": [{
                                        "Image": "${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_DEFAULT_REGION}.amazonaws.com/${env.ECR_REPO}:${env.IMAGE_TAG}",
                                        "ModelDataUrl": "${outputUri}/${env.TRAINING_JOB_NAME_PREFIX}-${env.IMAGE_TAG}/output/model.tar.gz",
                                        "Environment": {}
                                    }],
                                    "SupportedContentTypes": ["text/csv"],
                                    "SupportedResponseMIMETypes": ["text/csv"]
                                }'
                            """
                        }
                    }
                }
            }
        }

stage('Verify and Deploy Model') {
    steps {
        withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: "${env.AWS_CREDENTIALS_ID}"]]) {
            script {
                def modelPackageName = "${env.MODEL_PACKAGE_GROUP_NAME}-${env.IMAGE_TAG}"

                def json = sh(script: """
                    aws sagemaker list-model-packages --model-package-group-name ${MODEL_PACKAGE_GROUP_NAME} --output json --region ${AWS_DEFAULT_REGION}
                """, returnStdout: true).trim()
    
                def filtered_model = sh(script: """
                    echo '${json}' | jq -c --arg desc "${modelPackageName}" '.ModelPackageSummaryList[] | select(.ModelPackageDescription == \$desc)'
                """, returnStdout: true).trim()
                
                def model_package_version = sh(script: """
                    echo '${filtered_model}' | jq -r '.ModelPackageVersion'
                """, returnStdout: true).trim()
                echo "Filtered Model Package: ${filtered_model}"
                echo "Model Package Version: ${model_package_version}"
                
                def endpointName = "${env.PROJECT_NAME}-${env.MODEL_NAME}-v${model_package_version}-${env.SAGEMAKER_ENV}"

                echo "Model Approval Status: ${env.APPROVAL_STATUS}"

                if (env.APPROVAL_STATUS == 'Approved') {
                    echo "Model is approved. Deploying model."

                    sh """
                    aws sagemaker create-endpoint-config \
                        --endpoint-config-name ${env.ENDPOINT_CONFIG_NAME}-${env.IMAGE_TAG} \
                        --production-variants '[{
                            "VariantName": "AllTraffic",
                            "ModelName": "${env.MODEL_NAME}-${env.IMAGE_TAG}",
                            "InitialInstanceCount": ${env.INITIAL_INSTANCE_COUNT},
                            "InstanceType": "${env.INFERENCE_INSTANCE_TYPE}",
                            "InitialVariantWeight": 1.0
                        }]'
                    """

                    sh """
                    aws sagemaker create-endpoint \
                        --endpoint-name ${endpointName} \
                        --endpoint-config-name ${env.ENDPOINT_CONFIG_NAME}-${env.IMAGE_TAG}
                    """
                } else {
                    echo "Model in PendingApproval. Skipping deployment."
                }
            }
        }
    }
}


    }
}
