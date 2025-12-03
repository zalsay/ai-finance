package config

import (
	"os"
	"strconv"
	"strings"

	"github.com/joho/godotenv"
)

type Config struct {
	Database        DatabaseConfig
	Server          ServerConfig
	JWT             JWTConfig
	CORS            CORSConfig
	External        ExternalAPIConfig
	Redis           RedisConfig
	PythonService   PythonServiceConfig
	LLM             LLMConfig
	PostgresHandler PostgresHandlerConfig
}

type DatabaseConfig struct {
	Host     string
	Port     string
	User     string
	Password string
	DBName   string
	SSLMode  string
}

type ServerConfig struct {
	Port        string
	Environment string
}

type JWTConfig struct {
	Secret     string
	Expiration int // hours
}

type CORSConfig struct {
	AllowedOrigins   []string
	AllowedMethods   []string
	AllowedHeaders   []string
	AllowCredentials bool
}

type ExternalAPIConfig struct {
	AlphaVantageKey string
	PolygonKey      string
}

type RedisConfig struct {
	Host     string
	Port     string
	Password string
	DB       int
}

type PythonServiceConfig struct {
	BaseURL string
	Timeout int // seconds
}

type LLMConfig struct {
	APIKey           string // OpenAI API Key
	BaseURL          string // OpenAI API Base URL (optional, for custom endpoints)
	DefaultModel     string // Default model (e.g., "gpt-3.5-turbo")
	MaxContextRounds int    // Maximum context rounds (default 3)
	Timeout          int    // API request timeout in seconds
}

type PostgresHandlerConfig struct {
	BaseURL  string // Postgres handler API base URL
	APIToken string // API token for authentication
	Timeout  int    // API request timeout in seconds
}

func LoadConfig() (*Config, error) {
	// 尝试加载.env文件
	godotenv.Load()

	config := &Config{
		Database: DatabaseConfig{
			Host:     getEnv("DB_HOST", "8.163.5.7"),
			Port:     getEnv("DB_PORT", "50432"),
			User:     getEnv("DB_USER", "user_THtJYy"),
			Password: getEnv("DB_PASSWORD", "password_CnKYP8"),
			DBName:   getEnv("DB_NAME", "fintrack"),
			SSLMode:  getEnv("DB_SSLMODE", "disable"),
		},
		Server: ServerConfig{
			Port:        getEnv("SERVER_PORT", "9000"),
			Environment: getEnv("ENVIRONMENT", "development"),
		},
		JWT: JWTConfig{
			Secret:     getEnv("JWT_SECRET", "your-secret-key"),
			Expiration: getEnvAsInt("JWT_EXPIRATION_HOURS", 24),
		},
		CORS: CORSConfig{
			AllowedOrigins:   strings.Split(getEnv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001,http://localhost:3002"), ","),
			AllowedMethods:   strings.Split(getEnv("CORS_ALLOWED_METHODS", "GET,POST,PUT,DELETE,OPTIONS"), ","),
			AllowedHeaders:   strings.Split(getEnv("CORS_ALLOWED_HEADERS", "Content-Type,Authorization"), ","),
			AllowCredentials: getEnvAsBool("CORS_ALLOW_CREDENTIALS", true),
		},
		External: ExternalAPIConfig{
			AlphaVantageKey: getEnv("ALPHA_VANTAGE_API_KEY", ""),
			PolygonKey:      getEnv("POLYGON_API_KEY", ""),
		},
		Redis: RedisConfig{
			Host:     getEnv("REDIS_HOST", "localhost"),
			Port:     getEnv("REDIS_PORT", "6379"),
			Password: getEnv("REDIS_PASSWORD", ""),
			DB:       getEnvAsInt("REDIS_DB", 0),
		},
		PythonService: PythonServiceConfig{
			BaseURL: getEnv("PYTHON_SERVICE_URL", "http://localhost:8001"),
			Timeout: getEnvAsInt("PYTHON_SERVICE_TIMEOUT", 30),
		},
		LLM: LLMConfig{
			APIKey:           getEnv("OPENAI_API_KEY", ""),
			BaseURL:          getEnv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
			DefaultModel:     getEnv("OPENAI_DEFAULT_MODEL", "gpt-3.5-turbo"),
			MaxContextRounds: getEnvAsInt("OPENAI_MAX_CONTEXT_ROUNDS", 3),
			Timeout:          getEnvAsInt("OPENAI_TIMEOUT", 60),
		},
		PostgresHandler: PostgresHandlerConfig{
			BaseURL:  getEnv("POSTGRES_HANDLER_URL", "http://localhost:8080"),
			APIToken: getEnv("POSTGRES_HANDLER_TOKEN", ""),
			Timeout:  getEnvAsInt("POSTGRES_HANDLER_TIMEOUT", 10),
		},
	}

	return config, nil
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvAsInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}

func getEnvAsBool(key string, defaultValue bool) bool {
	if value := os.Getenv(key); value != "" {
		if boolValue, err := strconv.ParseBool(value); err == nil {
			return boolValue
		}
	}
	return defaultValue
}
