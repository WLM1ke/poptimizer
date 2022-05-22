package lgr

import (
	"bytes"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestLogger(t *testing.T) {
	t.Parallel()

	writer := bytes.NewBuffer([]byte{})
	logger := WithOptions(Writer(writer), TimeWithSeconds(), Prefix("Some"))

	tbl := []struct {
		logFunc func(format string, args ...interface{})
		panic   bool
		out     string
	}{
		{logger.Infof, false, "\u001B[34mINFO \u001B[0mSome: some\n"},
		{logger.Warnf, false, "\u001B[33mWARN \u001B[0mSome: some\n"},
		{logger.Panicf, true, "\u001B[31mPANIC \u001B[0mSome: some\n"},
	}

	for _, testCase := range tbl {
		writer.Reset()

		if testCase.panic {
			assert.Panics(t, func() {
				testCase.logFunc("%s", "some")
			}, "Не возникла паника")
		} else {
			assert.NotPanics(t, func() {
				testCase.logFunc("%s", "some")
			}, "Не должно быть паники")
		}

		assert.Equal(t, testCase.out, writer.String()[20:], "Некорректный вывод в логи")
	}
}

func TestDefaultLoggers(t *testing.T) {
	t.Parallel()

	logs := []*Logger{
		New("Some"),
		Discard(),
	}

	for _, log := range logs {
		assert.NotPanics(t, func() {
			log.Infof("%s", "some")
		}, "Не должно быть паники")

		assert.NotPanics(t, func() {
			log.Warnf("%s", "some")
		}, "Не должно быть паники")

		assert.Panics(t, func() {
			log.Panicf("%s", "some")
		}, "Не возникла паника")

		newLogger := log.WithPrefix("prefix")

		assert.Equal(t, "prefix: ", newLogger.prefix, "Не верный префикс")
		assert.Equal(t, newLogger.timeFormat, log.timeFormat, "Не верный формат даты")
		assert.Equal(t, newLogger.pool, log.pool, "Не верный пул буферов")
		assert.Equal(t, newLogger.lock, log.lock, "Не верный мьютекс")
		assert.Equal(t, newLogger.writer, log.writer, "Не верный io.Writer")
	}
}
