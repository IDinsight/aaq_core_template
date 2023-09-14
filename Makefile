#!make

# Load project config
include ./project_config.cfg
export

$(eval NAME=$(PROJECT_NAME))
$(eval PORT=9902)
$(eval VERSION=dev)
$(eval AWS_PROFILE_NAME=default)

# Need to specify bash in order for conda activate to work.
SHELL=/bin/bash

# Note that the extra activate is needed to ensure that the activate floats env to the front of PATH
CONDA_ACTIVATE=source $$(conda info --base)/etc/profile.d/conda.sh ; conda activate ; conda activate

# env vars
APP_SECRETS = INBOUND_CHECK_TOKEN ENABLE_FAQ_REFRESH_CRON PROMETHEUS_MULTIPROC_DIR FAQ_REFRESH_FREQ LANGUAGE_CONTEXT_REFRESH_FREQ

DB_SECRETS = PG_ENDPOINT PG_PORT PG_USERNAME PG_PASSWORD PG_DATABASE
SENTRY_CONFIG = SENTRY_DSN SENTRY_ENVIRONMENT SENTRY_TRACES_SAMPLE_RATE

PGPASSFILE = .pgpass


# Load db details
ifneq (,./secrets/database_secrets.env)
    -include ./secrets/database_secrets.env
    export
endif

cmd-exists-%:
	@hash $(*) > /dev/null 2>&1 || \
		(echo "ERROR: '$(*)' must be installed and available on your PATH."; exit 1)
guard-%:
	@if [ -z '${${*}}' ]; then echo 'ERROR: environment variable $* not set' && exit 1; fi

setup: setup-dev setup-db-all setup-ecr

setup-db-all: setup-db init-db-tables

setup-dev: setup-env setup-secrets
	
setup-db: cmd-exists-psql cmd-exists-createdb guard-PG_ENDPOINT guard-PG_PORT guard-PG_USERNAME guard-PG_PASSWORD guard-PG_DATABASE
	@echo "Creating Role: $(PG_USERNAME)"
	@psql -U postgres -h $(PG_ENDPOINT) -c "CREATE ROLE $(PG_USERNAME) WITH CREATEDB LOGIN PASSWORD '$(PG_PASSWORD)';"
	@echo "Creating Role: $(PG_USERNAME)_test"
	@psql -U postgres -h $(PG_ENDPOINT) -c "CREATE ROLE $(PG_USERNAME)_test WITH CREATEDB LOGIN PASSWORD '$(PG_PASSWORD)';"
	@echo $(PG_ENDPOINT):$(PG_PORT):*:$(PG_USERNAME):$(PG_PASSWORD) > .pgpass
	@echo $(PG_ENDPOINT):$(PG_PORT):*:$(PG_USERNAME)_test:$(PG_PASSWORD) >> .pgpass
	@chmod 0600 .pgpass
	@echo "Creating Db: $(PG_DATABASE)"
	@createdb -h $(PG_ENDPOINT) -p $(PG_PORT) -U $(PG_USERNAME) -O $(PG_USERNAME) $(PG_DATABASE)
	@psql -h $(PG_ENDPOINT) -p $(PG_PORT) -U $(PG_USERNAME) -d $(PG_DATABASE) \
		-c "CREATE SCHEMA $(PROJECT_SHORT_NAME) AUTHORIZATION $(PG_USERNAME); ALTER ROLE $(PG_USERNAME) SET search_path TO $(PROJECT_SHORT_NAME);"
	@echo "Creating Db: $(PG_DATABASE)-test"
	@createdb -h $(PG_ENDPOINT) -p $(PG_PORT) -U $(PG_USERNAME)_test -O $(PG_USERNAME)_test $(PG_DATABASE)-test
	@psql -h $(PG_ENDPOINT) -p $(PG_PORT) -U $(PG_USERNAME)_test -d $(PG_DATABASE)-test \
		-c "CREATE SCHEMA $(PROJECT_SHORT_NAME) AUTHORIZATION $(PG_USERNAME)_test; ALTER ROLE $(PG_USERNAME)_test SET search_path TO $(PROJECT_SHORT_NAME);"
	@rm .pgpass

setup-ecr: cmd-exists-aws
	aws ecr create-repository \
		--repository-name aaq_solution/$(NAME) \
		--region $(AWS_REGION)

# Setup postgres tables
init-db-tables: cmd-exists-psql guard-PG_ENDPOINT guard-PG_PORT guard-PG_USERNAME guard-PG_PASSWORD guard-PG_DATABASE
	@echo $(PG_ENDPOINT):$(PG_PORT):$(PG_DATABASE):$(PG_USERNAME):$(PG_PASSWORD) > .pgpass
	@echo $(PG_ENDPOINT):$(PG_PORT):$(PG_DATABASE)-test:$(PG_USERNAME)_test:$(PG_PASSWORD) >> .pgpass
	@chmod 0600 .pgpass
	@psql -h $(PG_ENDPOINT) -U $(PG_USERNAME) -d $(PG_DATABASE) -a -f ./scripts/core_tables.sql 
	@psql -h $(PG_ENDPOINT) -U $(PG_USERNAME)_test -d $(PG_DATABASE)-test -a -f ./scripts/core_tables.sql 
	@rm .pgpass

# Setup postgres tables in stg
init-db-tables-stg: cmd-exists-psql guard-PG_ENDPOINT guard-PG_PORT guard-PG_USERNAME guard-PG_PASSWORD guard-PG_DATABASE
	@echo $(PG_ENDPOINT):$(PG_PORT):$(PG_DATABASE):$(PG_USERNAME):$(PG_PASSWORD) > .pgpass
	@chmod 0600 .pgpass
	@psql -h $(PG_ENDPOINT) -U $(PG_USERNAME) -d $(PG_DATABASE) -a -f ./scripts/drop_tables.sql 
	@psql -h $(PG_ENDPOINT) -U $(PG_USERNAME) -d $(PG_DATABASE) -a -f ./scripts/core_tables.sql 
	@rm .pgpass
	@python ./scripts/load_db.py

setup-env: guard-PROJECT_CONDA_ENV cmd-exists-conda
	conda create --name $(PROJECT_CONDA_ENV) python==3.9 -y
	$(CONDA_ACTIVATE) $(PROJECT_CONDA_ENV); pip install --upgrade pip
	$(CONDA_ACTIVATE) $(PROJECT_CONDA_ENV); pip install -r requirements.txt --ignore-installed 
	$(CONDA_ACTIVATE) $(PROJECT_CONDA_ENV); pip install -r requirements_dev.txt --ignore-installed 
	$(CONDA_ACTIVATE) $(PROJECT_CONDA_ENV); pre-commit install

setup-secrets:
	@mkdir -p ./secrets/
	@if [ `ls -1 ./secrets | wc -l` -gt 0 ]; then \
		echo "One or more env file already exist"; exit 1; \
	fi
	@for env_var in $(APP_SECRETS) ; do \
		echo "$$env_var=" >> ./secrets/app_secrets.env ; \
	done

	@for env_var in $(DB_SECRETS) ; do \
		echo "$$env_var=" >> ./secrets/database_secrets.env ; \
	done

	@for env_var in $(SENTRY_CONFIG) ; do \
		echo "$$env_var=" >> ./secrets/sentry_config.env ; \
	done
	
ci:
	isort --profile black --check core_model
	black --check core_model tests
	flake8 core_model tests --count --ignore=E501,E203,E731,W503,E722 --show-source --statistics

test:
	pytest -k "not slow" tests

test-all:
	pytest tests

profile-dev-google:
	mkdir -p profiling/outputs
	pyinstrument --outfile=profiling/outputs/profile_google.html -m pytest -m "google" profiling/test_profiling.py::TestMainEndpoints

profile-dev-fasttext:
	mkdir -p profiling/outputs
	pyinstrument --outfile=profiling/outputs/profile_fasttext.html -m pytest -m "fasttext" profiling/test_profiling.py::TestMainEndpoints

profile-test-google:
	pytest -m "google" profiling/test_profiling.py::TestDummyFaqToDb
	mkdir -p profiling/outputs
	pyinstrument --outfile=profiling/outputs/profile_google.html -m pytest -m "google" profiling/test_profiling.py::TestMainEndpoints
	pytest -m "google" profiling/test_profiling.py::TestCleanDb

profile-test-fasttext:
	pytest -m "fasttext" profiling/test_profiling.py::TestDummyFaqToDb
	mkdir -p profiling/outputs
	pyinstrument --outfile=profiling/outputs/profile_fasttext.html -m pytest -m "fasttext" profiling/test_profiling.py::TestMainEndpoints
	pytest -m "fasttext" profiling/test_profiling.py::TestCleanDb

image:
	# Build docker image
	cp ./requirements.txt ./core_model/requirements.txt

	@docker build --rm \
		--build-arg NAME=$(NAME) \
		--build-arg PORT=$(PORT) \
		--build-arg TOKEN_MACHINE_USER=$(TOKEN_MACHINE_USER) \
		-t $(NAME):$(VERSION) \
		./core_model

	rm -rf ./core_model/requirements.txt

container:
	# Run container from image
	@docker container run \
		-p $(PORT):$(PORT) \
		--env-file ./secrets/app_secrets.env \
		--env-file ./secrets/database_secrets.env \
		--env-file ./secrets/sentry_config.env \
		--mount type=bind,source="$(PWD)/data",target="/usr/src/data" \
		$(NAME):$(VERSION)

container-stg: guard-PROJECT_SHORT_NAME guard-AWS_REGION guard-AWS_ACCOUNT_ID
	# Configure ecs-cli options
	@ecs-cli configure --cluster ${PROJECT_SHORT_NAME}-cluster \
	--default-launch-type EC2 \
	--region $(AWS_REGION) \
	--config-name ${NAME}-config

	@PROJECT_NAME=$(NAME) \
	PORT=$(PORT) \
	IMAGE_NAME=$(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/aaq_solution/$(NAME):$(VERSION) \
	AWS_REGION=$(AWS_REGION) \
	ecs-cli compose -f docker-compose/docker-compose-stg.yml \
	--project-name ${NAME} \
	--cluster-config ${NAME}-config \
	--task-role-arn arn:aws:iam::$(AWS_ACCOUNT_ID):role/${PROJECT_SHORT_NAME}-task-role \
	service up \
	--create-log-groups \
	--deployment-min-healthy-percent 0

down-stg:
	@ecs-cli compose \
	-f docker-compose/docker-compose-stg.yml \
	--project-name ${NAME} \
	--cluster-config ${NAME}-config service down

push-image: image cmd-exists-aws guard-AWS_ACCOUNT_ID
	aws ecr --profile=$(AWS_PROFILE_NAME) get-login-password --region af-south-1 \
		| docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.af-south-1.amazonaws.com
	docker tag $(NAME):$(VERSION) $(AWS_ACCOUNT_ID).dkr.ecr.af-south-1.amazonaws.com/aaq_solution/$(NAME):$(VERSION)
	docker push $(AWS_ACCOUNT_ID).dkr.ecr.af-south-1.amazonaws.com/aaq_solution/$(NAME):$(VERSION)

prometheus:
	@docker container ls -a --filter name=prometheus --format "{{.ID}}" | xargs -r docker stop
	@docker container ls -a --filter name=prometheus --format "{{.ID}}" | xargs -r docker rm
	@docker container run -d \
		--name prometheus \
		-p 9090:9090 \
	    -v $(PWD)/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml \
		prom/prometheus

grafana:
	@docker container ls -a --filter name=grafana --format "{{.ID}}" | xargs -r docker stop
	@docker container ls -a --filter name=grafana --format "{{.ID}}" | xargs -r docker rm
	@docker container run -d \
		--name grafana \
		-p 3000:3000 \
	    -v $(PWD)/monitoring/grafana/datasource.yaml:/etc/grafana/provisioning/datasources/default.yaml \
		-v $(PWD)/monitoring/grafana/dashboard.yaml:/etc/grafana/provisioning/dashboards/default.yaml \
		-v $(PWD)/monitoring/grafana/dashboards:/var/lib/grafana/dashboards \
		grafana/grafana-oss

uptime-exporter: guard-UPTIMEROBOT_API_KEY
	@docker container ls -a --filter name=uptimerobot_exporter --format "{{.ID}}" | xargs -r docker stop
	@docker container ls -a --filter name=uptimerobot_exporter --format "{{.ID}}" | xargs -r docker rm
	@docker container run -d \
		--name uptimerobot_exporter \
		-e UPTIMEROBOT_API_KEY=$(UPTIMEROBOT_API_KEY) \
		-p 9705:9705 --read-only lekpamartin/uptimerobot_exporter

tf-backend-apply: cmd-exists-terraform guard-PROJECT_SHORT_NAME guard-AWS_REGION guard-AWS_BILLING_CODE guard-AWS_PROFILE_NAME
	@terraform -chdir="./infrastructure/tf_backend" init

	@terraform -chdir="./infrastructure/tf_backend" apply \
	-var 'project_short_name=${PROJECT_SHORT_NAME}' \
	-var 'billing_code=${AWS_BILLING_CODE}' \
	-var 'region=${AWS_REGION}' \
	-var 'aws_profile_name=${AWS_PROFILE_NAME}'

tf-backend-destroy: cmd-exists-terraform guard-PROJECT_SHORT_NAME guard-AWS_REGION guard-AWS_BILLING_CODE guard-AWS_PROFILE_NAME
	@terraform -chdir="./infrastructure/tf_backend" init

	@terraform -chdir="./infrastructure/tf_backend" destroy \
	-var 'project_short_name=${PROJECT_SHORT_NAME}' \
	-var 'billing_code=${AWS_BILLING_CODE}' \
	-var 'region=${AWS_REGION}' \
	-var 'aws_profile_name=${AWS_PROFILE_NAME}'

tf-apply: cmd-exists-terraform guard-PROJECT_SHORT_NAME guard-AWS_REGION guard-AWS_BILLING_CODE guard-AWS_PROFILE_NAME
	@terraform -chdir="./infrastructure/deployment" init \
	-backend-config="bucket=${PROJECT_SHORT_NAME}-terraform-state" \
	-backend-config="key=terraform.tfstate" \
	-backend-config="region=${AWS_REGION}" \
	-backend-config="dynamodb_table=${PROJECT_SHORT_NAME}-terraform-state-locks" \
	-backend-config="encrypt=true" \
	-backend-config="aws_profile_name=${AWS_PROFILE_NAME}"

	@terraform -chdir="./infrastructure/deployment" apply \
	-var 'project_short_name=${PROJECT_SHORT_NAME}' \
	-var 'billing_code=${AWS_BILLING_CODE}' \
	-var 'region=${AWS_REGION}' \
	-var 'keypair_name=${PROJECT_SHORT_NAME}-keypair' \
	-var 'aws_profile_name=${AWS_PROFILE_NAME}'

tf-destroy: cmd-exists-terraform guard-PROJECT_SHORT_NAME guard-AWS_REGION guard-AWS_BILLING_CODE guard-AWS_PROFILE_NAME
	@terraform -chdir="./infrastructure/deployment" init \
	-backend-config="bucket=${PROJECT_SHORT_NAME}-terraform-state" \
	-backend-config="key=terraform.tfstate" \
	-backend-config="region=${AWS_REGION}" \
	-backend-config="dynamodb_table=${PROJECT_SHORT_NAME}-terraform-state-locks" \
	-backend-config="encrypt=true" \

	@terraform -chdir="./infrastructure/deployment" destroy \
	-var 'project_short_name=${PROJECT_SHORT_NAME}' \
	-var 'billing_code=${AWS_BILLING_CODE}' \
	-var 'region=${AWS_REGION}' \
	-var 'keypair_name=${PROJECT_SHORT_NAME}-keypair' 

	@python ./infrastructure/delete_secrets.py ${PROJECT_SHORT_NAME} ${AWS_REGION}
