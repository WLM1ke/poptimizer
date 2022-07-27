package web

import (
	"embed"
	"fmt"
	"io/fs"
)

//go:embed spa
var spa embed.FS

// GetSPAFiles возвращает index.html и остальные файлы для запуска SPA на базе Alpine.js.
func GetSPAFiles() (fs.FS, error) {
	sub, err := fs.Sub(spa, "spa")
	if err != nil {
		return nil, fmt.Errorf("can't load SPA files -> %w", err)
	}

	return sub, nil
}
