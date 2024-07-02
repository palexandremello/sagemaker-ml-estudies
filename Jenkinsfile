pipeline {
    agent any

    environment {
        AWS_DEFAULT_REGION = 'us-east-1'
        AWS_CREDENTIALS_ID = 'aws-credentials'
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/palexandremello/sagemaker-ml-estudies.git'
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
                        \$(aws ecr get-login --no-include-email --region ${env.AWS_DEFAULT_REGION})
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
                    // Verificação do tipo do modelo (substitua pela sua lógica real)
                    def modelType = 'train' // ou 'pre-trained'
                    if (modelType == 'pre-trained') {
                        currentBuild.description = 'Pre-trained model detected'
                        currentBuild.result = 'SUCCESS'
                        return
                    } else {
                        echo 'Model requires training...'
                    }
                }
            }
        }

        stage('Create or Train Model') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: "${env.AWS_CREDENTIALS_ID}"]]) {
                    script {
                        def modelType = 'train'
                        if (modelType == 'pre-trained') {
                            sh """
                            aws sagemaker create-model \
                                --model-name meu-modelo-${env.IMAGE_TAG} \
                                --primary-container Image=${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_DEFAULT_REGION}.amazonaws.com/${env.ECR_REPO}:${env.IMAGE_TAG} \
                                --execution-role-arn ${env.SAGEMAKER_ROLE}
                            """
                        } else {
                            sh """
                            aws sagemaker create-training-job \
                                --training-job-name meu-training-job-${env.IMAGE_TAG} \
                                --algorithm-specification TrainingImage=${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_DEFAULT_REGION}.amazonaws.com/${env.ECR_REPO}:${env.IMAGE_TAG},TrainingInputMode=File \
                                --role-arn ${env.SAGEMAKER_ROLE} \
                                --input-data-config ChannelName=training,DataSource={S3DataSource={S3Uri=s3://meu-bucket/dados, S3DataType=S3Prefix, S3DataDistributionType=FullyReplicated}},ContentType=csv \
                                --output-data-config S3OutputPath=s3://meu-bucket/output \
                                --resource-config InstanceType=ml.m5.large,InstanceCount=1,VolumeSizeInGB=50 \
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
                            --endpoint-config-name meu-endpoint-staging-config-${env.IMAGE_TAG} \
                            --production-variants VariantName=AllTraffic,ModelName=meu-modelo-${env.IMAGE_TAG},InitialInstanceCount=1,InstanceType=ml.m5.large

                        aws sagemaker create-endpoint \
                            --endpoint-name meu-endpoint-staging-${env.IMAGE_TAG} \
                            --endpoint-config-name meu-endpoint-staging-config-${env.IMAGE_TAG}
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
                            --endpoint-config-name meu-endpoint-prod-config-${env.IMAGE_TAG} \
                            --production-variants VariantName=AllTraffic,ModelName=meu-modelo-${env.IMAGE_TAG},InitialInstanceCount=1,InstanceType=ml.m5.large

                        aws sagemaker create-endpoint \
                            --endpoint-name meu-endpoint-prod-${env.IMAGE_TAG} \
                            --endpoint-config-name meu-endpoint-prod-config-${env.IMAGE_TAG}
                        """
                    }
                }
            }
        }
    }
}
