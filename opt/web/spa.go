package web

import (
	"embed"
	"io/fs"
)

//go:embed spa
var spa embed.FS

// GetSPAFiles возвращает index.html и остальные файлы для запуска SPA на базе Alpine.js.
func GetSPAFiles() (fs.FS, error) {
	return fs.Sub(spa, "spa")
}
