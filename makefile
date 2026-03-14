# =============================================================================
# Mwalika Canonical Service Makefile, v1
#
# Purpose:
#   Standard CI and deployment targets for Mwalika services.
#   Service-specific config lives in `service.mk`.
#
# Main targets:
#   build-push              Build and push image to ECR (docker)
#   build-push-buildx       Build and push image to ECR (buildx)
#   reg-credentials-secret  Create/update ECR regcred secret in Kubernetes
#   staging-env-secret      Create/update staging env secret in Kubernetes
#   production-env-secret   Create/update production env secret in Kubernetes
#   deploy-staging          Apply staging manifests with IMAGE_REF substituted
#   deploy-production       Apply production manifests with IMAGE_REF substituted
#   rollout-staging         Restart staging deployment
#   rollout-production      Restart production deployment
#   terminate-staging       Delete staging manifests
#   terminate-production    Delete production manifests
# =============================================================================

# --- Shell (CI-safe) ---

SHELL := /usr/bin/env bash
.SHELLFLAGS := -euo pipefail -c

# --- Service Configuration ---

SERVICE_MK ?= service.mk
ifeq ($(wildcard $(SERVICE_MK)),)
$(error Missing $(SERVICE_MK), create it and set SERVICE_NAME)
endif
include $(SERVICE_MK)

ifeq ($(strip $(SERVICE_NAME)),)
$(error SERVICE_NAME is required in $(SERVICE_MK))
endif

# --- Global Config ---

# - AWS Config -

# NOTE: For local development use export AWS_PROFILE=<profile-name>
# in your shell to set the profile.
AWS_PROFILE    ?=
AWS_REGION     ?= af-south-1

REPO_NAME      ?= $(SERVICE_NAME)

PROFILE_ARG = $(if $(AWS_PROFILE),--profile $(AWS_PROFILE),)
ACCOUNT_ID  ?= $(shell aws sts get-caller-identity $(PROFILE_ARG) \
	--query Account --output text)

IMAGE_TAG   ?= $(shell git rev-parse --short HEAD)
ECR_URI     = $(ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(REPO_NAME)
IMAGE_REF   = $(ECR_URI):$(IMAGE_TAG)

STAGING_ENV_SECRET_ID    ?= $(SERVICE_NAME)/env/staging
PROD_ENV_SECRET_ID       ?= $(SERVICE_NAME)/env/production

# - K8S Config -

K8S_NAMESPACE  ?= default
K8S_DIR        ?= kubernetes

K8S_STAGING_DIR    ?= $(K8S_DIR)/staging
K8S_PRODUCTION_DIR ?= $(K8S_DIR)/production

K8S_STAGING_DEPLOYMENT ?= $(SERVICE_NAME)-staging
K8S_PROD_DEPLOYMENT    ?= $(SERVICE_NAME)-production

REG_SECRET_NAME          ?= regcred-mwalika
STAGING_ENV_SECRET_NAME  ?= $(SERVICE_NAME)-env-staging
PROD_ENV_SECRET_NAME     ?= $(SERVICE_NAME)-env-production

# --- Targets ---

# - Building -

.PHONY: \
	build-push \
	build-push-buildx

# Build and push images to ECR with local Docker architecture
# default is arm64 in codebuild configuration
build-push:
	@echo "🏗️ Building and pushing $(IMAGE_REF)"; \
	aws ecr get-login-password --region $(AWS_REGION) $(PROFILE_ARG) \
	| docker login --username AWS --password-stdin \
	  $(ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com; \
	docker build -t "$(ECR_URI):$(IMAGE_TAG)" .; \
	docker tag "$(ECR_URI):$(IMAGE_TAG)" "$(ECR_URI):latest"; \
	docker push "$(ECR_URI):$(IMAGE_TAG)"; \
	docker push "$(ECR_URI):latest"; \
	echo "✅ $(SERVICE_NAME) image pushed: $(IMAGE_REF)"

# Build and push images to ECR with commit hash, uses buildx
build-push-buildx:
	@echo "🏗️ Building and pushing $(IMAGE_REF)"; \
	aws ecr get-login-password --region $(AWS_REGION) $(PROFILE_ARG) \
	| docker login --username AWS --password-stdin \
	  $(ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com; \
	docker buildx build --platform linux/arm64 \
	  -t "$(ECR_URI):$(IMAGE_TAG)" \
	  -t "$(ECR_URI):latest" \
	  --push .; \
	echo "✅ $(SERVICE_NAME) image pushed: $(IMAGE_REF)"

# - Secrets -

.PHONY: \
	reg-credentials-secret \
	staging-env-secret \
	production-env-secret

# Create/update registry credentials secret for ECR
reg-credentials-secret:
	@echo "🔑 Creating $(REG_SECRET_NAME) secret in Kubernetes"; \
	kubectl create secret docker-registry "$(REG_SECRET_NAME)" \
	  --docker-server="$(ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com" \
	  --docker-username=AWS \
	  --docker-password="$$(aws ecr get-login-password --region $(AWS_REGION) $(PROFILE_ARG))" \
	  --namespace="$(K8S_NAMESPACE)" \
	  --dry-run=client -o yaml | kubectl apply -f -; \
	echo "✅ $(REG_SECRET_NAME) secret ready"

# Create/update staging environment secret
staging-env-secret: reg-credentials-secret
	@echo "🔑 Fetching staging environment secrets from AWS Secrets Manager"; \
	tmp_dir="$$(mktemp -d -t "$(SERVICE_NAME).XXXXXX")"; \
	trap "rm -rf '$$tmp_dir'" EXIT; \
	env_file="$$tmp_dir/.env.staging.$(SERVICE_NAME)"; \
	aws secretsmanager get-secret-value \
	  --secret-id "$(STAGING_ENV_SECRET_ID)" \
	  --region "$(AWS_REGION)" \
	  $(PROFILE_ARG) \
	  --query SecretString \
	  --output text > "$$env_file"; \
	echo "🔑 Creating $(STAGING_ENV_SECRET_NAME) secret in Kubernetes"; \
	kubectl create secret generic "$(STAGING_ENV_SECRET_NAME)" \
	  --from-env-file="$$env_file" \
	  --namespace="$(K8S_NAMESPACE)" \
	  --dry-run=client -o yaml | kubectl apply -f -; \
	echo "✅ $(SERVICE_NAME) staging secret ready"; \
	echo "🧹 Cleaning up temp files with trap"; \

# Create/update production environment secret
production-env-secret: reg-credentials-secret
	@echo "🔑 Fetching production environment secrets from AWS Secrets Manager"; \
	tmp_dir="$$(mktemp -d -t "$(SERVICE_NAME).XXXXXX")"; \
	trap "rm -rf '$$tmp_dir'" EXIT; \
	env_file="$$tmp_dir/.env.production.$(SERVICE_NAME)"; \
	aws secretsmanager get-secret-value \
	  --secret-id "$(PROD_ENV_SECRET_ID)" \
	  --region "$(AWS_REGION)" \
	  $(PROFILE_ARG) \
	  --query SecretString \
	  --output text > "$$env_file"; \
	echo "🔑 Creating $(PROD_ENV_SECRET_NAME) secret in Kubernetes"; \
	kubectl create secret generic "$(PROD_ENV_SECRET_NAME)" \
	  --from-env-file="$$env_file" \
	  --namespace="$(K8S_NAMESPACE)" \
	  --dry-run=client -o yaml | kubectl apply -f -; \
	echo "✅ $(SERVICE_NAME) production secret ready"; \
	echo "🧹 Cleaning up temp files with trap"; \

# - Inspecting Service Resources -

.PHONY: \
	image-ref-available

image-ref-available:
	@echo "🔎 Checking if image exists in ECR: $(IMAGE_REF)"
	@aws ecr describe-images \
	  --repository-name "$(REPO_NAME)" \
	  --image-ids imageTag="$(IMAGE_TAG)" \
	  --region "$(AWS_REGION)" \
	  $(PROFILE_ARG) \
	  > /dev/null 2>&1 || { \
	    echo "❌ Image not found in ECR"; \
	    echo "Repository: $(REPO_NAME)"; \
	    echo "Tag: $(IMAGE_TAG)"; \
	    echo "Expected image: $(IMAGE_REF)"; \
	    echo ""; \
	    echo "Build and push the image first:"; \
	    echo "make build push"; \
	    exit 1; \
	  }
	@echo "✅ Image exists in ECR"

# - Creating Deployments -

.PHONY: \
	deploy-staging \
	deploy-production

# Deploy service in staging environment
deploy-staging: image-ref-available staging-env-secret
	@echo "🚀 Deploying $(SERVICE_NAME) in staging environment"; \
	test -d "$(K8S_STAGING_DIR)" || { echo "Missing $(K8S_STAGING_DIR)"; exit 1; }; \
	compgen -G "$(K8S_STAGING_DIR)/*.yaml" > /dev/null || { \
	  echo "No manifests found in $(K8S_STAGING_DIR)"; exit 1; \
	}; \
	IMAGE_REF="$(IMAGE_REF)"; \
	K8S_NAMESPACE="$(K8S_NAMESPACE)"; \
	export IMAGE_REF K8S_NAMESPACE; \
	tmp_dir="$$(mktemp -d)"; \
	trap "rm -rf '$$tmp_dir'" EXIT; \
	for manifest in $(K8S_STAGING_DIR)/*.yaml; do \
	  out="$$tmp_dir/$$(basename "$$manifest")"; \
	  echo "Processing $$manifest -> $$out"; \
	  envsubst < "$$manifest" > "$$out"; \
	done; \
	kubectl apply -f "$$tmp_dir" --namespace="$(K8S_NAMESPACE)"; \
	echo "✅ $(SERVICE_NAME) deployed to staging"

# Deploy service in production environment
deploy-production: image-ref-available production-env-secret
	@echo "🚀 Deploying $(SERVICE_NAME) in production environment"; \
	test -d "$(K8S_PRODUCTION_DIR)" || { echo "Missing $(K8S_PRODUCTION_DIR)"; exit 1; }; \
	compgen -G "$(K8S_PRODUCTION_DIR)/*.yaml" > /dev/null || { \
	  echo "No manifests found in $(K8S_PRODUCTION_DIR)"; exit 1; \
	}; \
	IMAGE_REF="$(IMAGE_REF)"; \
	K8S_NAMESPACE="$(K8S_NAMESPACE)"; \
	export IMAGE_REF K8S_NAMESPACE; \
	tmp_dir="$$(mktemp -d)"; \
	trap "rm -rf '$$tmp_dir'" EXIT; \
	for manifest in $(K8S_PRODUCTION_DIR)/*.yaml; do \
	  out="$$tmp_dir/$$(basename "$$manifest")"; \
	  echo "Processing $$manifest -> $$out"; \
	  envsubst < "$$manifest" > "$$out"; \
	done; \
	kubectl apply -f "$$tmp_dir" --namespace="$(K8S_NAMESPACE)"; \
	echo "✅ $(SERVICE_NAME) deployed to production"

# - Updates/Rollouts -

.PHONY: \
	rollout-staging \
	rollout-production

# Force rollout to staging
rollout-staging: staging-env-secret
	@echo "🔄 Forcing rollout of $(SERVICE_NAME) in staging"; \
	kubectl rollout restart "deployment/$(K8S_STAGING_DEPLOYMENT)" \
	  --namespace="$(K8S_NAMESPACE)"; \
	echo "✅ $(SERVICE_NAME) rollout to staging complete"

# Force rollout to production
rollout-production: production-env-secret
	@echo "🔄 Forcing rollout of $(SERVICE_NAME) in production"; \
	kubectl rollout restart "deployment/$(K8S_PROD_DEPLOYMENT)" \
	  --namespace="$(K8S_NAMESPACE)"; \
	echo "✅ $(SERVICE_NAME) rollout to production complete"

# - Terminating Deployments -

.PHONY: \
	terminate-staging \
	terminate-production

# Terminate staging environment resources
terminate-staging:
	@echo "🛑 Terminating $(SERVICE_NAME) in staging environment"; \
	test -d "$(K8S_STAGING_DIR)" || { echo "Missing $(K8S_STAGING_DIR)"; exit 1; }; \
	compgen -G "$(K8S_STAGING_DIR)/*.yaml" > /dev/null || { \
	  echo "No manifests found in $(K8S_STAGING_DIR)"; exit 1; \
	}; \
	for manifest in $(K8S_STAGING_DIR)/*.yaml; do \
	  echo "Deleting $$manifest"; \
	  kubectl delete -f "$$manifest" \
	    --namespace="$(K8S_NAMESPACE)" \
		--ignore-not-found=true; \
	done; \
	echo "✅ $(SERVICE_NAME) terminated in staging"

# Terminate production environment resources
terminate-production:
	@echo "🛑 Terminating $(SERVICE_NAME) in production environment"; \
	test -d "$(K8S_PRODUCTION_DIR)" || { echo "Missing $(K8S_PRODUCTION_DIR)"; exit 1; }; \
	compgen -G "$(K8S_PRODUCTION_DIR)/*.yaml" > /dev/null || { \
	  echo "No manifests found in $(K8S_PRODUCTION_DIR)"; exit 1; \
	}; \
	for manifest in $(K8S_PRODUCTION_DIR)/*.yaml; do \
	  echo "Deleting $$manifest"; \
	  kubectl delete -f "$$manifest" \
	    --namespace="$(K8S_NAMESPACE)" \
		--ignore-not-found=true; \
	done; \
	echo "✅ $(SERVICE_NAME) terminated in production"
