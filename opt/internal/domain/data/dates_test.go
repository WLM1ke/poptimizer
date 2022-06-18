package data

import (
	"github.com/stretchr/testify/assert"
	"testing"
	time "time"
)

func TestTradingDateService_getNewDay(t *testing.T) {
	t.Parallel()

	tests := []struct {
		checked  time.Time
		nowDelta time.Duration
		expected time.Time
		ok       bool
	}{
		{
			checked:  time.Date(2022, time.June, 15, 0, 0, 0, 0, time.UTC),
			nowDelta: -24*time.Hour + time.Minute,
			expected: time.Date(2022, time.June, 16, 0, 0, 0, 0, time.UTC),
			ok:       true,
		},
		{
			checked:  time.Date(2022, time.June, 16, 0, 0, 0, 0, time.UTC),
			nowDelta: -time.Minute,
			expected: time.Date(2022, time.June, 16, 0, 0, 0, 0, time.UTC),
			ok:       false,
		},
		{
			checked:  time.Date(2022, time.June, 16, 0, 0, 0, 0, time.UTC),
			nowDelta: time.Minute,
			expected: time.Date(2022, time.June, 17, 0, 0, 0, 0, time.UTC),
			ok:       true,
		},

		{
			checked:  time.Date(2022, time.June, 17, 0, 0, 0, 0, time.UTC),
			nowDelta: 24*time.Hour - time.Minute,
			expected: time.Date(2022, time.June, 17, 0, 0, 0, 0, time.UTC),
			ok:       false,
		},
	}

	service := NewTradingDateService(nil, nil, nil, nil)
	baseNow := time.Date(2022, time.June, 18, 0, 45, 0, 0, service.loc)

	for _, test := range tests {
		service.checkedDate = test.checked

		now := baseNow.Add(test.nowDelta).UTC()

		day, ok := service.getNewDay(now)

		assert.Equal(
			t,
			test.expected,
			day,
			"wrong new day %s vs %s", test.expected, day)

		assert.Equal(
			t,
			test.ok,
			ok,
			"wrong new day ok %v vs %v", test.ok, ok)
	}

}
