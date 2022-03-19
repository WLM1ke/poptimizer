new:
	brew install go
	brew install golangci-lint
update:
	brew upgrade go
	brew upgrade golangci-lint
lint:
	golangci-lint run
test:
	make lint
	go test -v -covermode=atomic -race ./...
bench:
	go get -u -t -v ./...
	go mod tidy -v
	go test -count=5 -run=None -bench . -benchmem ./...
build:
	go build -o .bin/podata -x cmd/main.go
run:
	go run ./cmd