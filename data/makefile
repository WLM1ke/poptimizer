new:
	brew install go
	brew install golangci-lint
update:
	brew upgrade go
	brew upgrade golangci-lint
lint:
	go get -u -t -v ./...
	go mod tidy -v
	golangci-lint run
test:
	make lint
	go test -v -covermode=atomic -race ./...
bench:
	make lint
	go test -count=5 -run=None -bench . -benchmem ./...
build:
	make test
	go build -o .bin/podata -x cmd/main.go
run:
	go run ./cmd