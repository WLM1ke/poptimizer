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
