pipeline {
    agent any

    environment {
        AWS_DEFAULT_REGION = 'us-east-1'
        AWS_CREDENTIALS_ID = 'aws-credentials'
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

        stage('Verify Commit') {
            steps {
                echo 'Verifying commit...'
                // Adicione aqui qualquer verificação ou teste que você precise
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
                        def imageTag = "${env.BUILD_NUMBER}-${env.COMMIT_HASH}"
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
                    env.MODEL_PATH = config.inference.ModelDataUrl
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
                                --primary-container Image=${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_DEFAULT_REGION}.amazonaws.com/${env.ECR_REPO}:${env.IMAGE_TAG},ModelDataUrl=s3://${env.MODEL_PATH} \
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

        stage('Register Model') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: "${env.AWS_CREDENTIALS_ID}"]]) {
                    script {
                        sh """
                        aws sagemaker create-model-package \
                            --model-package-name ${env.MODEL_NAME_PREFIX}-package-${env.IMAGE_TAG} \
                            --model-package-description "Model package for ${env.MODEL_NAME_PREFIX} version ${env.IMAGE_TAG}" \
                            --model-approval-status Approved \
                            --model-metadata-properties '{\"CommitHash\":\"${env.COMMIT_HASH}\"}' \
                            --inference-specification '{\"Containers\":[{\"Image\":\"${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_DEFAULT_REGION}.amazonaws.com/${env.ECR_REPO}:${env.IMAGE_TAG}\",\"ModelDataUrl\":\"s3://${env.MODEL_PATH}\"}],\"SupportedContentTypes\":[\"text/csv\"],\"SupportedResponseMIMETypes\":[\"text/csv\"]}' \
                            --validation-specification '{\"ValidationRole\":\"${env.SAGEMAKER_ROLE}\",\"ValidationProfiles\":[{\"ProfileName\":\"DefaultProfile\",\"TransformJobDefinition\":{\"TransformInput\":{\"DataSource\":{\"S3DataSource\":{\"S3Uri\":\"s3://${env.S3_INPUT_BUCKET}/${env.S3_DATA_PREFIX}\",\"S3DataType\":\"S3Prefix\"}},\"ContentType\":\"text/csv\"},\"TransformOutput\":{\"S3OutputPath\":\"s3://${env.S3_OUTPUT_BUCKET}/validation-output\"},\"TransformResources\":{\"InstanceType\":\"${env.INSTANCE_TYPE}\",\"InstanceCount\":1}}}]}' \
                            --execution-role-arn ${env.SAGEMAKER_ROLE}
                        """
                    }
                }
            }
        }

        stage('Check Existing Endpoint') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: "${env.AWS_CREDENTIALS_ID}"]]) {
                    script {
                        def endpointExists = sh(
                            script: "aws sagemaker describe-endpoint --endpoint-name ${env.ENDPOINT_NAME_PREFIX}-staging --region ${env.AWS_DEFAULT_REGION}",
                            returnStatus: true
                        ) == 0

                        if (endpointExists) {
                            env.ENDPOINT_EXISTS = 'true'
                        } else {
                            env.ENDPOINT_EXISTS = 'false'
                        }
                    }
                }
            }
        }

        stage('Create Endpoint Config') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: "${env.AWS_CREDENTIALS_ID}"]]) {
                    script {
                        sh """
                        aws sagemaker create-endpoint-config \
                            --endpoint-config-name ${env.ENDPOINT_CONFIG_NAME_PREFIX}-staging-config-${env.IMAGE_TAG} \
                            --production-variants VariantName=AllTraffic,ModelName=${env.MODEL_NAME_PREFIX}-${env.IMAGE_TAG},InitialInstanceCount=${env.INITIAL_INSTANCE_COUNT},InstanceType=${env.INSTANCE_TYPE}
                        """
                    }
                }
            }
        }

        stage('Manual Approval for Endpoint Update') {
            when {
                expression {
                    return env.ENDPOINT_EXISTS == 'true'
                }
            }
            steps {
                script {
                    input message: 'Aprovar a substituição da configuração do endpoint de staging?', ok: 'Aprovar'
                }
            }
        }

        stage('Deploy to Staging') {
            when {
                expression {
                    return env.ENDPOINT_EXISTS == 'false'
                }
            }
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: "${env.AWS_CREDENTIALS_ID}"]]) {
                    script {
                        sh """
                        aws sagemaker create-endpoint \
                            --endpoint-name ${env.ENDPOINT_NAME_PREFIX}-staging \
                            --endpoint-config-name ${env.ENDPOINT_CONFIG_NAME_PREFIX}-staging-config-${env.IMAGE_TAG}
                        """
                    }
                }
            }
        }

        stage('Update Staging Endpoint') {
            when {
                expression {
                    return env.ENDPOINT_EXISTS == 'true'
                }
            }
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: "${env.AWS_CREDENTIALS_ID}"]]) {
                    script {
                        sh """
                        aws sagemaker update-endpoint \
                            --endpoint-name ${env.ENDPOINT_NAME_PREFIX}-staging \
                            --endpoint-config-name ${env.ENDPOINT_CONFIG_NAME_PREFIX}-staging-config-${env.IMAGE_TAG}
                        """
                    }
                }
            }
        }

        stage('Wait for Staging Endpoint') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: "${env.AWS_CREDENTIALS_ID}"]]) {
                    script {
                        sh """
                        while [ \$(aws sagemaker describe-endpoint --endpoint-name ${env.ENDPOINT_NAME_PREFIX}-staging --query 'EndpointStatus' --output text) != 'InService' ]; do
                            echo "Waiting for endpoint to be InService..."
                            sleep 30
                        done
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
                        echo "Aqui fazemos um teste do modelo"
                        """
                    }
                }
            }
        }
    }
}
