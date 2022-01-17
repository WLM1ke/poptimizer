package repo

import (
	"context"
	"errors"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

var (
	ErrTableNotFound = errors.New("table not found")
	ErrInternal      = errors.New("repo internal error")
	ErrTableUpdate   = errors.New("table update error")
)

// Read осуществляет загрузку таблиц.
type Read[R any] interface {
	// Get загружает таблицу.
	Get(ctx context.Context, id domain.ID) (domain.Table[R], error)
}

// JSONViewer осуществляет загрузку таблицы в виде ExtendedJSON.
type JSONViewer interface {
	// GetJSON загружает ExtendedJSON представление таблицы.
	GetJSON(ctx context.Context, id domain.ID) ([]byte, error)
}

// ReadWrite осуществляет загрузку и сохранение таблиц.
type ReadWrite[R any] interface {
	Read[R]
	// Replace перезаписывает таблицу.
	Replace(ctx context.Context, table domain.Table[R]) error
	// Append добавляет строки в конец таблицы.
	Append(ctx context.Context, table domain.Table[R]) error
}
