package repository

import (
	"context"
	"fmt"

	"github.com/WLM1ke/poptimizer/opt/pkg/clients"
	"go.mongodb.org/mongo-driver/mongo"
)

const _backupDir = `dump`

// BackupRestoreService резервного копирования пользовательских данных.
type BackupRestoreService struct {
	uri    string
	client *mongo.Client
}

// NewBackupRestoreService сервис резервного копирования пользовательских данных.
func NewBackupRestoreService(uri string, client *mongo.Client) *BackupRestoreService {
	return &BackupRestoreService{
		uri:    uri,
		client: client,
	}
}

// Restore осуществляет восстановление определенной группы данных, если она не содержит документов.
func (s BackupRestoreService) Restore(ctx context.Context, subdomain, group string) (int, error) {
	count, err := s.client.Database(subdomain).Collection(group).EstimatedDocumentCount(ctx)
	if err != nil {
		return 0, fmt.Errorf("can't check collection %s.%s -> %w", subdomain, group, err)
	}

	if count != 0 {
		return int(count), nil
	}

	if err := clients.MongoDBRestore(ctx, _backupDir, s.uri, subdomain, group); err != nil {
		return 0, err
	}

	return 0, nil
}

// Backup осуществляет бекап определенной группы данных.
func (s BackupRestoreService) Backup(ctx context.Context, subdomain, group string) error {
	if err := clients.MongoDBBackup(ctx, _backupDir, s.uri, subdomain, group); err != nil {
		return err
	}

	return nil
}
