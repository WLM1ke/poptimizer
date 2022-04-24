package app

import (
	"bufio"
	"errors"
	"io"
	"os"
	"strings"

	"github.com/caarlos0/env/v6"
)

const (
	_envPath      = `.env`
	_commentStart = `#`
)

func (a *App) loadConfig() {
	if err := env.Parse(a.config); err != nil {
		a.code = 1
		a.logger.Panicf("can't load config -> %s", err)
	}

	a.logger.Infof("App: config loaded")
}

func (a *App) readEnvFile() map[string]string {
	file, err := os.Open(_envPath)

	switch {
	case errors.Is(err, os.ErrNotExist):
		a.logger.Panicf("no %s file - using defaults", _envPath)

		return nil
	case err != nil:
		a.code = 1
		a.logger.Panicf("can't load %s file -> %s", _envPath, err)
	}

	defer func() {
		err := file.Close()
		if err != nil {
			a.code = 1
			a.logger.Panicf("can't close %s file -> %s", _envPath, err)
		}
	}()

	return a.parse(file)
}

func (a *App) parse(file io.Reader) map[string]string {
	envs := make(map[string]string)

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		if err := scanner.Err(); err != nil {
			a.code = 1
			a.logger.Panicf("can't parse %s file -> %s", _envPath, err)
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
			a.code = 1
			a.logger.Panicf("can't parse line: %s", line)
		}

		envs[line[:index]] = line[index+1:]
	}

	return envs
}
