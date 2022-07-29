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
		out     string
	}{
		{logger.Infof, "\u001B[34mINFO \u001B[0mSome: some\n"},
		{logger.Warnf, "\u001B[33mWARN \u001B[0mSome: some\n"},
	}

	for _, testCase := range tbl {
		writer.Reset()

		assert.NotPanics(t, func() {
			testCase.logFunc("%s", "some")
		}, "Не должно быть паники")

		assert.Equal(t, testCase.out, writer.String()[20:], "Некорректный вывод в логи")
	}
}

func TestDefaultLoggers(t *testing.T) {
	t.Parallel()

	logs := []Logger{
		New("Some"),
		Discard(),
	}

	for _, log := range logs {
		newLogger := log.WithPrefix("prefix").(*logger)

		assert.Equal(t, "prefix: ", newLogger.prefix, "Не верный префикс")
		assert.Equal(t, newLogger.timeFormat, newLogger.timeFormat, "Не верный формат даты")
		assert.Equal(t, newLogger.pool, newLogger.pool, "Не верный пул буферов")
		assert.Equal(t, newLogger.lock, newLogger.lock, "Не верный мьютекс")
		assert.Equal(t, newLogger.writer, newLogger.writer, "Не верный io.Writer")
	}
}
