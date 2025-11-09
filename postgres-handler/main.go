package main

import (
    "database/sql"
    "fmt"
    "log"
    "net/http"
    "os"
    "strings"
    "time"

    "github.com/gin-contrib/gzip"
    "github.com/gin-gonic/gin"
    _ "github.com/lib/pq"
)

// StockData 股票数据结构
type StockData struct {
	ID               int       `json:"id" db:"id"`
	Datetime         time.Time `json:"datetime" db:"datetime"`
	Open             float64   `json:"open" db:"open"`
	Close            float64   `json:"close" db:"close"`
	High             float64   `json:"high" db:"high"`
	Low              float64   `json:"low" db:"low"`
	Volume           int64     `json:"volume" db:"volume"`
	Amount           float64   `json:"amount" db:"amount"`
	Amplitude        float64   `json:"amplitude" db:"amplitude"`
	PercentageChange float64   `json:"percentage_change" db:"percentage_change"`
	AmountChange     float64   `json:"amount_change" db:"amount_change"`
	TurnoverRate     float64   `json:"turnover_rate" db:"turnover_rate"`
	Type             int       `json:"type" db:"type"` // 分区字段：1=股票，2=基金（包含ETF），3=指数，4+=其他
	Symbol           string    `json:"symbol" db:"symbol"`
	CreatedAt        time.Time `json:"created_at" db:"created_at"`
	UpdatedAt        time.Time `json:"updated_at" db:"updated_at"`
}

// DatabaseHandler 数据库处理器
type DatabaseHandler struct {
	db *sql.DB
}

// ApiResponse 通用API响应结构
type ApiResponse struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

// NewDatabaseHandler 创建新的数据库处理器
func NewDatabaseHandler() (*DatabaseHandler, error) {
	// 从环境变量获取数据库连接信息
	dbHost := getEnv("DB_HOST", "8.163.5.7")
	dbPort := getEnv("DB_PORT", "5432")
	dbUser := getEnv("DB_USER", "user_THtJYy")
	dbPassword := getEnv("DB_PASSWORD", "password_CnKYP8")
	dbName := getEnv("DB_NAME", "fintrack")

	connStr := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		dbHost, dbPort, dbUser, dbPassword, dbName)

	db, err := sql.Open("postgres", connStr)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to database: %v", err)
	}

	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %v", err)
	}

	handler := &DatabaseHandler{db: db}
	
	// 初始化数据库表和分区
	if err := handler.initializeDatabase(); err != nil {
		return nil, fmt.Errorf("failed to initialize database: %v", err)
	}

	return handler, nil
}

// initializeDatabase 初始化数据库表和分区
func (h *DatabaseHandler) initializeDatabase() error {
	// 创建主表（分区表）
	createMainTableSQL := `
	CREATE TABLE IF NOT EXISTS stock_data (
		id SERIAL,
		datetime TIMESTAMP NOT NULL,
		open DECIMAL(10,4) NOT NULL,
		close DECIMAL(10,4) NOT NULL,
		high DECIMAL(10,4) NOT NULL,
		low DECIMAL(10,4) NOT NULL,
		volume BIGINT NOT NULL,
		amount DECIMAL(15,2) NOT NULL,
		amplitude DECIMAL(8,4) NOT NULL,
		percentage_change DECIMAL(8,4) NOT NULL,
		amount_change DECIMAL(10,4) NOT NULL,
		turnover_rate DECIMAL(8,4) NOT NULL,
		type INTEGER NOT NULL,
		symbol VARCHAR(20) NOT NULL,
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		PRIMARY KEY (id, type)
	) PARTITION BY RANGE (type);`

	if _, err := h.db.Exec(createMainTableSQL); err != nil {
		return fmt.Errorf("failed to create main table: %v", err)
	}

	// 创建分区表
	partitions := []struct {
		name     string
		minValue int
		maxValue int
		comment  string
	}{
		{"stock_data_stocks", 1, 2, "股票数据分区"},
		{"stock_data_funds", 2, 3, "基金数据分区（包含ETF）"},
		{"stock_data_indices", 3, 4, "指数数据分区"},
		{"stock_data_others", 4, 100, "其他类型数据分区"},
	}

	for _, partition := range partitions {
		createPartitionSQL := fmt.Sprintf(`
		CREATE TABLE IF NOT EXISTS %s PARTITION OF stock_data
		FOR VALUES FROM (%d) TO (%d);`,
			partition.name, partition.minValue, partition.maxValue)

		if _, err := h.db.Exec(createPartitionSQL); err != nil {
			return fmt.Errorf("failed to create partition %s: %v", partition.name, err)
		}

		// 添加索引
		createIndexSQL := fmt.Sprintf(`
		CREATE INDEX IF NOT EXISTS idx_%s_datetime ON %s (datetime);
		CREATE INDEX IF NOT EXISTS idx_%s_symbol ON %s (symbol);
		CREATE INDEX IF NOT EXISTS idx_%s_symbol_datetime ON %s (symbol, datetime);`,
			partition.name, partition.name,
			partition.name, partition.name,
			partition.name, partition.name)

		if _, err := h.db.Exec(createIndexSQL); err != nil {
			log.Printf("Warning: failed to create index for %s: %v", partition.name, err)
		}
	}

	log.Println("Database initialized successfully with partitioned tables")
	return nil
}

// InsertStockData 插入股票数据
func (h *DatabaseHandler) InsertStockData(data *StockData) error {
	query := `
	INSERT INTO stock_data (
		datetime, open, close, high, low, volume, amount, amplitude,
		percentage_change, amount_change, turnover_rate, type, symbol
	) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
	RETURNING id, created_at, updated_at`

	err := h.db.QueryRow(query,
		data.Datetime, data.Open, data.Close, data.High, data.Low,
		data.Volume, data.Amount, data.Amplitude, data.PercentageChange,
		data.AmountChange, data.TurnoverRate, data.Type, data.Symbol,
	).Scan(&data.ID, &data.CreatedAt, &data.UpdatedAt)

	if err != nil {
		return fmt.Errorf("failed to insert stock data: %v", err)
	}

	return nil
}

// BatchInsertStockData 批量插入股票数据
func (h *DatabaseHandler) BatchInsertStockData(dataList []StockData) error {
	tx, err := h.db.Begin()
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %v", err)
	}
	defer tx.Rollback()

	stmt, err := tx.Prepare(`
	INSERT INTO stock_data (
		datetime, open, close, high, low, volume, amount, amplitude,
		percentage_change, amount_change, turnover_rate, type, symbol
	) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)`)
	
	if err != nil {
		return fmt.Errorf("failed to prepare statement: %v", err)
	}
	defer stmt.Close()

	for _, data := range dataList {
		_, err := stmt.Exec(
			data.Datetime, data.Open, data.Close, data.High, data.Low,
			data.Volume, data.Amount, data.Amplitude, data.PercentageChange,
			data.AmountChange, data.TurnoverRate, data.Type, data.Symbol,
		)
		if err != nil {
			return fmt.Errorf("failed to execute batch insert: %v", err)
		}
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("failed to commit transaction: %v", err)
	}

	return nil
}

// GetStockData 获取股票数据
func (h *DatabaseHandler) GetStockData(symbol string, stockType int, limit int, offset int) ([]StockData, error) {
	query := `
	SELECT id, datetime, open, close, high, low, volume, amount, amplitude,
		   percentage_change, amount_change, turnover_rate, type, symbol,
		   created_at, updated_at
	FROM stock_data
	WHERE symbol = $1 AND type = $2
	ORDER BY datetime DESC
	LIMIT $3 OFFSET $4`

	rows, err := h.db.Query(query, symbol, stockType, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to query stock data: %v", err)
	}
	defer rows.Close()

	var results []StockData
	for rows.Next() {
		var data StockData
		err := rows.Scan(
			&data.ID, &data.Datetime, &data.Open, &data.Close, &data.High, &data.Low,
			&data.Volume, &data.Amount, &data.Amplitude, &data.PercentageChange,
			&data.AmountChange, &data.TurnoverRate, &data.Type, &data.Symbol,
			&data.CreatedAt, &data.UpdatedAt,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan row: %v", err)
		}
		results = append(results, data)
	}

	return results, nil
}

// GetStockDataByDateRange 根据日期范围获取股票数据
func (h *DatabaseHandler) GetStockDataByDateRange(symbol string, stockType int, startDate, endDate time.Time) ([]StockData, error) {
	query := `
	SELECT id, datetime, open, close, high, low, volume, amount, amplitude,
		   percentage_change, amount_change, turnover_rate, type, symbol,
		   created_at, updated_at
	FROM stock_data
	WHERE symbol = $1 AND type = $2 AND datetime >= $3 AND datetime <= $4
	ORDER BY datetime ASC`

	rows, err := h.db.Query(query, symbol, stockType, startDate, endDate)
	if err != nil {
		return nil, fmt.Errorf("failed to query stock data by date range: %v", err)
	}
	defer rows.Close()

	var results []StockData
	for rows.Next() {
		var data StockData
		err := rows.Scan(
			&data.ID, &data.Datetime, &data.Open, &data.Close, &data.High, &data.Low,
			&data.Volume, &data.Amount, &data.Amplitude, &data.PercentageChange,
			&data.AmountChange, &data.TurnoverRate, &data.Type, &data.Symbol,
			&data.CreatedAt, &data.UpdatedAt,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan row: %v", err)
		}
		results = append(results, data)
	}

	return results, nil
}

// HTTP处理器
func (h *DatabaseHandler) insertStockDataHandler(c *gin.Context) {
    var data StockData
    if err := c.ShouldBindJSON(&data); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
        return
    }
    if err := h.InsertStockData(&data); err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    c.JSON(http.StatusOK, ApiResponse{
		Code: 200,
		Message: "Success",
	})
}

func (h *DatabaseHandler) batchInsertStockDataHandler(c *gin.Context) {
    var dataList []StockData
    if err := c.ShouldBindJSON(&dataList); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
        return
    }
    if err := h.BatchInsertStockData(dataList); err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    c.JSON(http.StatusOK, ApiResponse{
		Code: 200,
		Message: "Batch insert successful",
	})
}

func (h *DatabaseHandler) getStockDataHandler(c *gin.Context) {
    symbol := c.Param("symbol")
    // 读取JSON Body参数
    var req struct {
        Type   *int `json:"type"`
        Limit  *int `json:"limit"`
        Offset *int `json:"offset"`
    }
    if err := c.ShouldBindJSON(&req); err != nil && err.Error() != "EOF" {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
        return
    }

    stockType := 1
    if req.Type != nil {
        stockType = *req.Type
    }
    limit := 100
    if req.Limit != nil {
        limit = *req.Limit
    }
    offset := 0
    if req.Offset != nil {
        offset = *req.Offset
    }

    data, err := h.GetStockData(symbol, stockType, limit, offset)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    c.JSON(http.StatusOK, ApiResponse{
		Code: 200,
		Message: "Success",
		Data: data,
	})
}

func (h *DatabaseHandler) getStockDataByDateRangeHandler(c *gin.Context) {
    symbol := c.Param("symbol")
    // 读取JSON Body参数
    var req struct {
        Type      *int   `json:"type"`
        StartDate string `json:"start_date"`
        EndDate   string `json:"end_date"`
    }
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
        return
    }

    stockType := 1
    if req.Type != nil {
        stockType = *req.Type
    }
    if req.StartDate == "" || req.EndDate == "" {
        c.JSON(http.StatusBadRequest, gin.H{"error": "start_date and end_date parameters are required"})
        return
    }
    startDate, err := time.Parse("2006-01-02", req.StartDate)
    if err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid start_date format (YYYY-MM-DD)"})
        return
    }
    endDate, err := time.Parse("2006-01-02", req.EndDate)
    if err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid end_date format (YYYY-MM-DD)"})
        return
    }

    data, err := h.GetStockDataByDateRange(symbol, stockType, startDate, endDate)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    c.JSON(http.StatusOK, ApiResponse{
		Code: 200,
		Message: "Success",
		Data: data,
	})
}

// Close 关闭数据库连接
func (h *DatabaseHandler) Close() error {
	return h.db.Close()
}

// 工具函数
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func main() {
    // 创建数据库处理器
    handler, err := NewDatabaseHandler()
    if err != nil {
        log.Fatal("Failed to create database handler:", err)
    }
    defer handler.Close()

    // 创建 Gin 引擎
    r := gin.Default()
    // 启用 gzip 中间件（根据客户端 Accept-Encoding 自动压缩响应）
    r.Use(gzip.Gzip(gzip.DefaultCompression))
    
    // 简单鉴权：固定token（从环境变量API_TOKEN读取，未设置则使用默认值）
    apiToken := getEnv("API_TOKEN", "fintrack-dev-token")
    r.Use(TokenAuthMiddleware(apiToken))

    // API 路由组
    api := r.Group("/api/v1")
    {
        api.POST("/stock-data", handler.insertStockDataHandler)
        api.POST("/stock-data/batch", handler.batchInsertStockDataHandler)
        api.POST("/stock-data/:symbol", handler.getStockDataHandler)
        api.POST("/stock-data/:symbol/range", handler.getStockDataByDateRangeHandler)
    }

    // 健康检查
    r.GET("/health", func(c *gin.Context) {
        c.JSON(http.StatusOK, gin.H{"status": "ok"})
    })

    port := getEnv("PORT", "8080")
    log.Printf("Server starting on port %s", port)
    log.Printf("API endpoints:")
    log.Printf("  POST /api/v1/stock-data - Insert single stock data")
    log.Printf("  POST /api/v1/stock-data/batch - Batch insert stock data")
    log.Printf("  POST /api/v1/stock-data/:symbol - Get stock data (JSON body: {type, limit, offset})")
    log.Printf("  POST /api/v1/stock-data/:symbol/range - Get stock data by date range (JSON body: {type, start_date, end_date})")
    log.Printf("  GET  /health - Health check")

    if err := r.Run(":" + port); err != nil {
        log.Fatal("Server failed to start:", err)
    }
}

// TokenAuthMiddleware 使用固定token进行简单鉴权
// 客户端需要在请求头中携带：
//  - X-Token: <token>
//  或 Authorization: Bearer <token>
// /health 路径不鉴权
func TokenAuthMiddleware(expectedToken string) gin.HandlerFunc {
    return func(c *gin.Context) {
        // 跳过健康检查
        if c.Request.URL.Path == "/health" {
            c.Next()
            return
        }

        // 尝试从 X-Token 或 Authorization(Bearer) 中读取token
        token := c.GetHeader("X-Token")
        if token == "" {
            auth := c.GetHeader("Authorization")
            if strings.HasPrefix(auth, "Bearer ") {
                token = strings.TrimPrefix(auth, "Bearer ")
            }
        }

        if token == "" || token != expectedToken {
            c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
            return
        }

        c.Next()
    }
}