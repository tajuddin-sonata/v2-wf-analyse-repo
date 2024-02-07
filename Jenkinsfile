pipeline {
    agent {
        label 'jenkins-slave'
    }

    parameters{
        choice(name: 'ENVIRONMENT', choices:[
            'dev',
            'staging',
            'prod'],
            description: 'Choose which environment to deploy to.')
        string(name: 'AZURE_FUNCTION_NAME', description: '''The name of FunctionApp to deploy
            jenkins-wf-configure 
            jenkins-wf-transcode
            jenkins-wf-transcribe
            jenkins-wf-analyse
            jenkins-wf-redact''' )

        string(name: 'AZURE_FUNCTION_ASP_NAME', description: '''The name of App service Plan for FunctionApp to deploy
            v2-functions-ASP
            jenkins-wf-configure-ASP 
            jenkins-wf-transcode-ASP
            jenkins-wf-transcribe-ASP
            jenkins-wf-analyse-ASP
            jenkins-wf-redact-ASP''' )
        
        string(name: 'APP_INSIGHTS_INSTRUMENTATION_KEY', description: '''select the existing Application insight Instrumentation Key .
            9b3a9c7a-fec6-4f67-b669-a149294fbeee 
            ''' )

        string(name: 'FUNC_STORAGE_ACCOUNT_NAME', description: '''select the existing Storage account name for Func App or create new .
            v2funcappstg569650
            ccadevfunctionappstgacc 
            ''' )

        string(name: 'AZURE_APP_INSIGHTS_NAME', description: '''The name of Application insight for FunctionApp to deploy
            v2-func-app-insight
            ''' )

        string(name: 'REGION', defaultValue: 'CentralIndia', description: 'Region to Deploy to.')

        // choice(name: 'SUBSCRIPTION', choices:[
        //     '48986b2e-5349-4fab-a6e8-d5f02072a4b8',
        //     '34b1c36e-d8e8-4bd5-a6f3-2f92a1c0626e',
        //     '70c3af66-8434-419b-b808-0b3c0c4b1a04'
        //     ],
        //     description: 'Subscription to deploy to .')

        string(name: 'SUBSCRIPTION', description: ''' select subscription as:
            48986b2e-5349-4fab-a6e8-d5f02072a4b8
            34b1c36e-d8e8-4bd5-a6f3-2f92a1c0626e
            70c3af66-8434-419b-b808-0b3c0c4b1a04''')

        choice(name: 'RESOURCE_GROUP_NAME', choices:[
            'jenkins-247-rg',
            'CCA-DEV'
            ],
            description: 'Azure Resource Group in which the FunctionApp need to deploy .')

        choice(name: 'SKU', choices:[
            'S3','S1', 'S2',
            'B1', 'B2', 'B3', 
            'P1V3','P2V3', 'P3V3'], 
            description: 'ASP SKU.')

        choice(name: 'PYTHON_RUNTIME_VERSION', choices:[
            '3.9',
            '3.10',
            '3.11'],
            description: 'Python runtime version.')
    }

    environment {
        AZURE_CLIENT_ID = credentials('azurerm_client_id')
        AZURE_CLIENT_SECRET = credentials('azurerm_client_secret')
        AZURE_TENANT_ID = credentials('azurerm_tenant_id')
        ZIP_FILE_NAME = "${params.AZURE_FUNCTION_NAME}.zip"
    }

    stages {

        stage('Checkout') {
            steps {
                // checkout scm
                git branch: 'dev', url: 'https://github.com/tajuddin-sonata/v2-wf-analyse-repo.git'
                
                // Install Pip
                // sh 'sudo yum install -y python3-pip'

                // Install project dependencies
                // sh 'pip3 install -r requirements.txt -t .'
            }
        }

        // stage('Package Code') {
        //     steps {
        //         sh "zip -r ${ZIP_FILE_NAME} ."
        //     }
        // }
        

        stage('Create FunctionApp') {
            steps {
                // Create ASP for functionApp
                sh 'az login --service-principal -u $AZURE_CLIENT_ID -p $AZURE_CLIENT_SECRET --tenant $AZURE_TENANT_ID'
                sh "az account set --subscription ${params.SUBSCRIPTION}"
                // sh "az appservice plan create --name ${params.AZURE_FUNCTION_ASP_NAME} --resource-group ${params.RESOURCE_GROUP_NAME} --sku ${params.SKU} --is-linux --location ${params.REGION}"
                
                // Create FunctionApp
                sh "az functionapp create --name ${params.AZURE_FUNCTION_NAME} --resource-group ${params.RESOURCE_GROUP_NAME} --plan ${params.AZURE_FUNCTION_ASP_NAME} --runtime python --runtime-version ${params.PYTHON_RUNTIME_VERSION} --functions-version 4 --storage-account ${params.FUNC_STORAGE_ACCOUNT_NAME}"
                sh "az functionapp config appsettings set --name ${params.AZURE_FUNCTION_NAME} --resource-group ${params.RESOURCE_GROUP_NAME} --settings APPINSIGHTS_INSTRUMENTATIONKEY=${params.APP_INSIGHTS_INSTRUMENTATION_KEY}"
            }
        }

        stage('Deploy to Azure Function App') {
            steps {
                script {
                    sh """
                    wget https://github.com/Azure/azure-functions-core-tools/releases/download/4.0.5455/Azure.Functions.Cli.linux-x64.4.0.5455.zip
                    unzip -o -d azure-functions-cli Azure.Functions.Cli.linux-x64.*.zip

                    cd azure-functions-cli
                    chmod +x func
                    chmod +x gozip
                    export PATH=`pwd`:$PATH
                    cd ..

                    cd src/
                    ls -ltr
                    func azure functionapp publish ${params.AZURE_FUNCTION_NAME} --python
                    """
                }
            }
        }

        // stage('Deploy to Azure Function App') {
        //     steps {
        //         script {
        //             // Azure CLI commands to deploy the function code
        //             sh 'az login --service-principal -u $AZURE_CLIENT_ID -p $AZURE_CLIENT_SECRET --tenant $AZURE_TENANT_ID'
        //             sh "az account set --subscription ${params.SUBSCRIPTION}"
        //             sh "az functionapp deployment source config-zip --src ${ZIP_FILE_NAME} --name ${params.AZURE_FUNCTION_NAME} --resource-group ${params.RESOURCE_GROUP_NAME}"
        //         }
        //     }
        // }
    }
}