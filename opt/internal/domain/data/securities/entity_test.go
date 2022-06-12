package securities

import (
	"testing"

	"github.com/WLM1ke/gomoex"
	"github.com/stretchr/testify/assert"
)

func prepare() Table {
	return Table{
		{Ticker: "AKRN", Selected: true},
		{Ticker: "GAZP", Selected: true},
		{Ticker: "NVTK", Selected: false},
		{Ticker: "RTKM", Selected: false},
		{Ticker: "RTKMD", Selected: false},
		{Ticker: "RTKMP", Selected: false},
		{Ticker: "UPRO", Selected: true},
	}
}

func TestTable_update(t *testing.T) {
	t.Parallel()

	sec := prepare().update([]gomoex.Security{
		{Ticker: "GMKN"},
		{Ticker: "RTKMP"},
		{Ticker: "NVTK"},
		{Ticker: "AKRN"},
	})

	expected := Table{
		{Ticker: "AKRN", Selected: true},
		{Ticker: "GMKN", Selected: false},
		{Ticker: "NVTK", Selected: false},
		{Ticker: "RTKMP", Selected: false},
	}

	assert.Equal(t, expected, sec, "incorrect update of selected sec")
}

func TestTable_Selected(t *testing.T) {
	t.Parallel()

	tickers := prepare().Selected()
	out := []string{"AKRN", "GAZP", "UPRO"}

	assert.Equal(t, out, tickers, "wrong selected tickers")
}

func TestTable_NotSelected(t *testing.T) {
	t.Parallel()

	table := []struct {
		prefix string
		out    []string
	}{
		{"", nil},
		{"n", []string{"NVTK"}},
		{"RT", []string{"RTKM", "RTKMD", "RTKMP"}},
		{"G", []string{}},
	}

	for _, c := range table {
		assert.Equal(
			t,
			c.out,
			prepare().NotSelected(c.prefix),
			"wrong not selected tickers",
		)
	}
}

func TestTable_Select(t *testing.T) {
	t.Parallel()

	table := []struct {
		ticker   string
		ok       bool
		selected []string
	}{
		{"R", false, []string{"AKRN", "GAZP", "UPRO"}},
		{"AKRN", false, []string{"AKRN", "GAZP", "UPRO"}},
		{"NVTK", true, []string{"AKRN", "GAZP", "NVTK", "UPRO"}},
		{"Z", false, []string{"AKRN", "GAZP", "UPRO"}},
	}

	for _, test := range table {
		sec := prepare()
		ok := sec.Select(test.ticker)

		assert.Equal(t, 7, len(sec), "size of sec must not change")
		assert.Equal(t, test.ok, ok, "wrong addition to selected sec")
		assert.Equal(t, test.selected, sec.Selected(), "wrong addition to selected sec")
	}
}

func TestTable_Unselect(t *testing.T) {
	t.Parallel()

	table := []struct {
		ticker   string
		ok       bool
		selected []string
	}{
		{"R", false, []string{"AKRN", "GAZP", "UPRO"}},
		{"AKRN", true, []string{"GAZP", "UPRO"}},
		{"NVTK", false, []string{"AKRN", "GAZP", "UPRO"}},
	}

	for _, test := range table {
		sec := prepare()
		ok := sec.Unselect(test.ticker)

		assert.Equal(t, 7, len(sec), "size of sec must not change")
		assert.Equal(t, test.ok, ok, "wrong removal to selected sec")
		assert.Equal(t, test.selected, sec.Selected(), "wrong removal to selected sec")
	}
}
