package domain

import "context"

// ReadRepo осуществляет загрузку агрегата.
type ReadRepo[E Entity] interface {
	Get(ctx context.Context, qid QID) (Aggregate[E], error)
}

// ListRepo выводит перечень id агрегатов в заданной группе.
type ListRepo interface {
	List(ctx context.Context, sub, group string) ([]string, error)
}

// ReadGroupRepo осуществляет загрузку всех агрегатов группы.
type ReadGroupRepo[E Entity] interface {
	GetGroup(ctx context.Context, sub, group string) ([]Aggregate[E], error)
}

// WriteRepo осуществляет сохранение агрегата.
type WriteRepo[E Entity] interface {
	Save(ctx context.Context, agg Aggregate[E]) error
}

// DeleteRepo осуществляет сохранение агрегата.
type DeleteRepo interface {
	Delete(ctx context.Context, qid QID) error
}

// ReadWriteRepo позволяет читать и сохранять агрегаты.
type ReadWriteRepo[E Entity] interface {
	ReadRepo[E]
	WriteRepo[E]
}

// BackupRestore осуществляет резервное копирование заданной группы агрегатов.
type BackupRestore interface {
	Backup(ctx context.Context, subdomain, group string) error
	// Restore возвращает количество агрегатов и восстанавливает данные, если нет.
	Restore(ctx context.Context, subdomain, group string) (int, error)
}
