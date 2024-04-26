SW_VERSION ?= latest
IMAGE_ORG ?= mcnet

IMAGE_TAG_BASE ?= quay.io/$(IMAGE_ORG)/flock_client_func
IMG ?= $(IMAGE_TAG_BASE):$(SW_VERSION)
build:
	@echo "Start go build phase"
	go build -o ./bin/relay ./cmd/relay/relay.go
	go build -o ./bin/fr-adm ./cmd/admin/admin.go
	go build -o ./bin/client_func ./client/
	gcc -Wall -o ./bin/client hack/test.cpp -L/usr/lib -lssl -lcrypto
# gcc -Wall -o ./bin/ssl-server hack/ssl_server.c -L/usr/lib -lssl -lcrypto

lint:  ; $(info running linters...)
	@golangci-lint run --config=./.golangci.yaml ./...

docker-build:
	docker build --progress=plain --rm --tag client_func .

build-image:
	docker build --build-arg SW_VERSION="$(SW_VERSION)" -t ${IMG} .

push-image:
	docker push ${IMG}