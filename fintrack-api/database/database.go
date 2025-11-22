package database

import (
	"database/sql"
	"fmt"
	"io/ioutil"
	"log"

	"fintrack-api/config"

	_ "github.com/lib/pq"
)

type DB struct {
	Conn *sql.DB
}

func NewConnection(cfg *config.Config) (*DB, error) {
	connStr := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=%s",
		cfg.Database.Host, cfg.Database.Port, cfg.Database.User,
		cfg.Database.Password, cfg.Database.DBName, cfg.Database.SSLMode)

	db, err := sql.Open("postgres", connStr)
	if err != nil {
		return nil, fmt.Errorf("failed to open database connection: %w", err)
	}

	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	// Set connection pool settings
	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)

	log.Println("Database connection established successfully")
	return &DB{Conn: db}, nil
}

func (db *DB) Close() error {
	return db.Conn.Close()
}

func (db *DB) InitializeSchema() error {
	// Read schema.sql file
	schemaSQL, err := ioutil.ReadFile("database/schema.sql")
	if err != nil {
		// Try reading from current directory if running from root
		schemaSQL, err = ioutil.ReadFile("fintrack-api/database/schema.sql")
		if err != nil {
			// Try absolute path as fallback (for development)
			schemaSQL, err = ioutil.ReadFile("/Users/sisu/Documents/code/ai-finance/fintrack-api/database/schema.sql")
			if err != nil {
				log.Printf("Warning: Could not read schema.sql file: %v", err)
				return nil
			}
		}
	}

	_, err = db.Conn.Exec(string(schemaSQL))
	if err != nil {
		return fmt.Errorf("failed to execute schema: %w", err)
	}

	log.Println("Database schema initialized successfully")
	return nil
}
