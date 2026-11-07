// Jenkins CI/CD pipeline for learner-analytics.
//   CI : every commit -> build test image -> lint -> unit tests -> build runtime image -> smoke test
//   CD : optional push to Docker Hub, automatic deployment of the new image to a staging server
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 30, unit: 'MINUTES')
    }

    // Jenkins runs locally, so GitHub cannot reach it with a webhook:
    // poll the repository every 2 minutes and build every new commit.
    triggers {
        pollSCM('H/2 * * * *')
    }

    parameters {
        booleanParam(name: 'PUSH_IMAGE', defaultValue: false,
                     description: 'Push the image to Docker Hub (needs the "dockerhub" credentials)')
        string(name: 'DOCKERHUB_REPO', defaultValue: 'borzki/learner-analytics',
               description: 'Docker Hub repository, <user>/<name>')
        booleanParam(name: 'DEPLOY_STAGING', defaultValue: true,
                     description: 'Deploy the new image to the staging container')
    }

    environment {
        IMAGE        = 'learner-analytics'
        TAG          = "${env.BUILD_NUMBER}"
        STAGING      = 'learner-analytics-staging'
        STAGING_PORT = '8501'
    }

    stages {
        stage('Checkout info') {
            steps {
                script {
                    env.GIT_SHORT = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                }
                sh 'git log -1 --pretty="Commit %h by %an: %s"'
                sh 'docker version --format "Docker client {{.Client.Version}}, server {{.Server.Version}}"'
            }
        }

        stage('Build test image') {
            steps {
                sh 'docker build --target test -t $IMAGE:test-$TAG .'
            }
        }

        stage('Lint') {
            steps {
                sh 'docker run --rm $IMAGE:test-$TAG ruff check .'
                sh 'docker run --rm $IMAGE:test-$TAG ruff format --check .'
            }
        }

        stage('Unit tests') {
            steps {
                sh 'docker run --name la-test-$TAG $IMAGE:test-$TAG'
            }
            post {
                always {
                    sh '''
                        rm -rf reports && mkdir -p reports
                        docker cp la-test-$TAG:/app/reports/. reports/ || true
                        docker rm -f la-test-$TAG || true
                    '''
                    junit allowEmptyResults: true, testResults: 'reports/junit.xml'
                    archiveArtifacts artifacts: 'reports/*.xml', allowEmptyArchive: true
                }
            }
        }

        stage('Build image') {
            steps {
                sh '''
                    docker build --target runtime \
                        --build-arg BUILD_NUMBER=$TAG \
                        --build-arg GIT_COMMIT=$GIT_SHORT \
                        -t $IMAGE:$TAG -t $IMAGE:latest .
                    docker image ls $IMAGE
                '''
            }
        }

        stage('Smoke test image') {
            steps {
                sh '''
                    docker run --rm $IMAGE:$TAG --version
                    docker run --rm --entrypoint sh $IMAGE:$TAG -c "
                        learner-analytics simulate --students 50 --seed 1 --out /tmp/d &&
                        learner-analytics analyze /tmp/d/logs.csv --truth /tmp/d/students.csv --out /tmp/r &&
                        ls /tmp/r"
                '''
            }
        }

        stage('Push to Docker Hub') {
            when { expression { params.PUSH_IMAGE == true } }
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub',
                                                  usernameVariable: 'DH_USER',
                                                  passwordVariable: 'DH_TOKEN')]) {
                    sh '''
                        echo "$DH_TOKEN" | docker login -u "$DH_USER" --password-stdin
                        docker tag $IMAGE:$TAG $DOCKERHUB_REPO:$TAG
                        docker tag $IMAGE:$TAG $DOCKERHUB_REPO:latest
                        docker push $DOCKERHUB_REPO:$TAG
                        docker push $DOCKERHUB_REPO:latest
                        docker logout
                    '''
                }
            }
        }

        stage('Deploy to staging') {
            when { expression { params.DEPLOY_STAGING != false } }
            steps {
                sh '''
                    docker rm -f $STAGING || true
                    docker run -d --name $STAGING --restart unless-stopped \
                        -p $STAGING_PORT:8000 --entrypoint serve-report $IMAGE:$TAG
                '''
            }
        }

        stage('Verify deployment') {
            when { expression { params.DEPLOY_STAGING != false } }
            steps {
                sh '''
                    for i in $(seq 1 30); do
                        if docker exec $STAGING python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/index.html')" 2>/dev/null; then
                            echo "Staging is up (attempt $i)"
                            docker exec $STAGING python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/summary.json').read().decode())"
                            exit 0
                        fi
                        sleep 2
                    done
                    echo "Staging did not start"; docker logs $STAGING; exit 1
                '''
            }
        }
    }

    post {
        always {
            sh 'docker rmi $IMAGE:test-$TAG || true'
        }
        success {
            echo "Build ${env.TAG} passed. Staging report: http://localhost:${env.STAGING_PORT}"
        }
        failure {
            echo 'Pipeline failed - see the stage logs above.'
        }
    }
}
