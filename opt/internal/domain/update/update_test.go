package update

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

func TestTradingDateService_getNewDay(t *testing.T) {
	t.Parallel()

	tbl := []struct {
		checked  time.Time
		nowDelta time.Duration
		expected time.Time
	}{
		{
			checked:  time.Date(2022, time.June, 15, 0, 0, 0, 0, time.UTC),
			nowDelta: -24*time.Hour + time.Minute,
			expected: time.Date(2022, time.June, 16, 0, 0, 0, 0, time.UTC),
		},
		{
			checked:  time.Date(2022, time.June, 16, 0, 0, 0, 0, time.UTC),
			nowDelta: -time.Minute,
			expected: time.Date(2022, time.June, 16, 0, 0, 0, 0, time.UTC),
		},
		{
			checked:  time.Date(2022, time.June, 16, 0, 0, 0, 0, time.UTC),
			nowDelta: time.Minute,
			expected: time.Date(2022, time.June, 17, 0, 0, 0, 0, time.UTC),
		},

		{
			checked:  time.Date(2022, time.June, 17, 0, 0, 0, 0, time.UTC),
			nowDelta: 24*time.Hour - time.Minute,
			expected: time.Date(2022, time.June, 17, 0, 0, 0, 0, time.UTC),
		},
	}

	loc, err := time.LoadLocation(_issTZ)
	assert.Nil(t, err, "can't load time MOEX zone")

	service := Service{loc: loc}
	baseNow := time.Date(2022, time.June, 18, 0, 45, 0, 0, service.loc)

	for _, test := range tbl {
		service.checkedDay = test.checked

		now := baseNow.Add(test.nowDelta).UTC()

		day := service.lastDayEnded(now)
		assert.Equal(t, test.expected, day, "wrong new day")
	}
}
