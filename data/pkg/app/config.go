package app

import (
	"bufio"
	"errors"
	"fmt"
	"github.com/caarlos0/env/v6"
	"io"
	"os"
	"strings"
)

const (
	_envPath      = `.env`
	_commentStart = `#`
)

func LoadConfig(cfg interface{}) {
	opts := env.Options{
		Environment:     readFile(),
		RequiredIfNoDef: true,
	}

	if err := env.Parse(cfg, opts); err != nil {
		panic(fmt.Sprintf("can't load config -> %s", err))
	}
}

func readFile() map[string]string {
	file, err := os.Open(_envPath)
	switch {
	case errors.Is(err, os.ErrNotExist):
		return nil
	case err != nil:
		panic(fmt.Sprintf("can't load %s file -> %s", _envPath, err))
	}

	defer func() {
		err := file.Close()
		if err != nil {
			panic(fmt.Sprintf("can't close %s file -> %s", _envPath, err))
		}
	}()

	return parse(file)
}

func parse(file io.Reader) map[string]string {
	envs := make(map[string]string)

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		if err := scanner.Err(); err != nil {
			panic(fmt.Sprintf("can't parse %s file -> %s", _envPath, err))
		}

		line := scanner.Text()
		switch {
		case len(line) == 0:
			continue
		case strings.HasPrefix(line, _commentStart):
			continue
		}

		index := strings.Index(line, "=")
		if index == -1 {
			panic(fmt.Errorf("can't parse line: %s", line))
		}

		envs[line[:index]] = line[index+1:]

	}

	return envs
}
