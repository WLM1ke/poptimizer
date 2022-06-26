PKG_MNG=brew
TOOLS=go golangci-lint

SRC=./cmd
BIN=./bin/poptimizer

new:
	$(PKG_MNG) install $(TOOLS)
update:
	$(PKG_MNG) upgrade $(TOOLS)
	go get -u -t -v ./...
	go mod tidy -v
lint:
	golangci-lint run
test: lint
	go test -v -covermode=atomic -race ./...
bench:
	go test -count=5 -run=None -bench . -benchmem ./...
build:
	go build -o $(BIN) -x $(SRC)
run: build
	(export $$(cat .env | grep -o '^[^#]\+' | xargs) && $(BIN))