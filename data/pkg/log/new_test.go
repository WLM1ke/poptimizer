package log

import (
	"bytes"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestLogger(t *testing.T) {
	writer := bytes.NewBuffer([]byte{})
	logger := WithOptions(Writer(writer), TimeWithSeconds(), Name("Some"))

	tbl := []struct {
		logFunc func(format string, args ...interface{})
		panic   bool
		out     string
	}{
		{logger.Infof, false, "\u001B[34mINFO \u001B[0mSome Ошибка: причина\n"},
		{logger.Warnf, false, "\u001B[33mWARN \u001B[0mSome Ошибка: причина\n"},
		{logger.Panicf, true, "\u001B[31mPANIC \u001B[0mSome Ошибка: причина\n"},
	}

	for _, testCase := range tbl {
		writer.Reset()

		if testCase.panic {
			assert.Panics(t, func() {
				testCase.logFunc("Ошибка: %s", "причина")
			}, "Не возникла паника")
		} else {
			assert.NotPanics(t, func() {
				testCase.logFunc("Ошибка: %s", "причина")
			}, "Не должно быть паники")
		}

		assert.Equal(t, testCase.out, writer.String()[20:], "Некорректный вывод в логи")
	}
}

func TestDefaultLoggers(t *testing.T) {
	logs := []*Logger{
		New("Some"),
		NoOp(),
	}

	for _, log := range logs {
		assert.NotPanics(t, func() {
			log.Infof("Ошибка: %s", "причина")
		}, "Не должно быть паники")

		assert.NotPanics(t, func() {
			log.Warnf("Ошибка: %s", "причина")
		}, "Не должно быть паники")

		assert.Panics(t, func() {
			log.Panicf("Ошибка: %s", "причина")
		}, "Не возникла паника")
	}
}
