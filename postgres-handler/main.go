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

// EtfDailyData ETF每日数据结构（独立于 stock_data，不混用）
type EtfDailyData struct {
	Code          string    `json:"code" db:"code"`
	TradingDate   time.Time `json:"trading_date" db:"trading_date"`
	Name          string    `json:"name" db:"name"`
	LatestPrice   float64   `json:"latest_price" db:"latest_price"`
	ChangeAmount  float64   `json:"change_amount" db:"change_amount"`
	ChangePercent float64   `json:"change_percent" db:"change_percent"`
	Buy           float64   `json:"buy" db:"buy"`
	Sell          float64   `json:"sell" db:"sell"`
	PrevClose     float64   `json:"prev_close" db:"prev_close"`
	Open          float64   `json:"open" db:"open"`
	High          float64   `json:"high" db:"high"`
	Low           float64   `json:"low" db:"low"`
	Volume        int64     `json:"volume" db:"volume"`
	Turnover      int64     `json:"turnover" db:"turnover"`
}

// IndexInfo 指数基本信息
type IndexInfo struct {
	Code        string    `json:"code" db:"code"`
	DisplayName string    `json:"display_name" db:"display_name"`
	PublishDate time.Time `json:"publish_date" db:"publish_date"`
	CreatedAt   time.Time `json:"created_at" db:"created_at"`
}

// IndexDailyData 指数每日行情数据
type IndexDailyData struct {
	Code          string    `json:"code" db:"code"`
	TradingDate   time.Time `json:"trading_date" db:"trading_date"`
	Open          float64   `json:"open" db:"open"`
	Close         float64   `json:"close" db:"close"`
	High          float64   `json:"high" db:"high"`
	Low           float64   `json:"low" db:"low"`
	Volume        int64     `json:"volume" db:"volume"`
	Amount        float64   `json:"amount" db:"amount"`
	ChangePercent float64   `json:"change_percent" db:"change_percent"`
}

// StockCommentDaily A股每日评论/指标数据（来源：akshare stock_comment_em）
type StockCommentDaily struct {
    Code                 string    `json:"code" db:"code"`
    TradingDate          time.Time `json:"trading_date" db:"trading_date"`
    Name                 string    `json:"name" db:"name"`
    LatestPrice          float64   `json:"latest_price" db:"latest_price"`
    ChangePercent        float64   `json:"change_percent" db:"change_percent"`
    TurnoverRate         float64   `json:"turnover_rate" db:"turnover_rate"`
    PeRatio              float64   `json:"pe_ratio" db:"pe_ratio"`
    MainCost             float64   `json:"main_cost" db:"main_cost"`
    InstitutionParticipation float64 `json:"institution_participation" db:"institution_participation"`
    CompositeScore       float64   `json:"composite_score" db:"composite_score"`
    Rise                 int64     `json:"rise" db:"rise"`
    CurrentRank          int64     `json:"current_rank" db:"current_rank"`
    AttentionIndex       float64   `json:"attention_index" db:"attention_index"`
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

	// 创建独立的 ETF 每日数据表（不与 stock_data 混用）
	createEtfDailySQL := `
    CREATE TABLE IF NOT EXISTS etf_daily (
        code TEXT NOT NULL,
        trading_date DATE NOT NULL,
        name TEXT,
        latest_price NUMERIC(12,4),
        change_amount NUMERIC(12,4),
        change_percent NUMERIC(12,4),
        buy NUMERIC(12,4),
        sell NUMERIC(12,4),
        prev_close NUMERIC(12,4),
        open NUMERIC(12,4),
        high NUMERIC(12,4),
        low NUMERIC(12,4),
        volume BIGINT,
        turnover BIGINT,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
        PRIMARY KEY (code, trading_date)
    );
    CREATE INDEX IF NOT EXISTS idx_etf_daily_trading_date ON etf_daily (trading_date);
    CREATE INDEX IF NOT EXISTS idx_etf_daily_code ON etf_daily (code);
    `
	if _, err := h.db.Exec(createEtfDailySQL); err != nil {
		return fmt.Errorf("failed to create etf_daily table: %v", err)
	}
	log.Println("Table etf_daily ensured successfully")

	// 指数基本信息表
	createIndexInfoSQL := `
    CREATE TABLE IF NOT EXISTS index_info (
        code TEXT PRIMARY KEY,
        display_name TEXT,
        publish_date DATE,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_index_info_display_name ON index_info (display_name);
    `
	if _, err := h.db.Exec(createIndexInfoSQL); err != nil {
		return fmt.Errorf("failed to create index_info table: %v", err)
	}
	log.Println("Table index_info ensured successfully")

	// 指数每日数据表
	createIndexDailySQL := `
    CREATE TABLE IF NOT EXISTS index_daily (
        code TEXT NOT NULL,
        trading_date DATE NOT NULL,
        open NUMERIC(12,4),
        close NUMERIC(12,4),
        high NUMERIC(12,4),
        low NUMERIC(12,4),
        volume BIGINT,
        amount NUMERIC(20,4),
        change_percent NUMERIC(12,4),
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
        PRIMARY KEY (code, trading_date)
    );
    CREATE INDEX IF NOT EXISTS idx_index_daily_code ON index_daily (code);
    CREATE INDEX IF NOT EXISTS idx_index_daily_trading_date ON index_daily (trading_date);
    `
	if _, err := h.db.Exec(createIndexDailySQL); err != nil {
		return fmt.Errorf("failed to create index_daily table: %v", err)
	}
    log.Println("Table index_daily ensured successfully")

    // A股每日评论/指标数据表（stock_comment_em）
    createAStockCommentDailySQL := `
    CREATE TABLE IF NOT EXISTS a_stock_comment_daily (
        code TEXT NOT NULL,
        trading_date DATE NOT NULL,
        name TEXT,
        latest_price NUMERIC(12,4),
        change_percent NUMERIC(12,4),
        turnover_rate NUMERIC(12,4),
        pe_ratio NUMERIC(12,4),
        main_cost NUMERIC(12,4),
        institution_participation NUMERIC(12,4),
        composite_score NUMERIC(12,4),
        rise BIGINT,
        current_rank BIGINT,
        attention_index NUMERIC(12,4),
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
        PRIMARY KEY (code, trading_date)
    );
    CREATE INDEX IF NOT EXISTS idx_a_stock_comment_daily_code ON a_stock_comment_daily (code);
    CREATE INDEX IF NOT EXISTS idx_a_stock_comment_daily_trading_date ON a_stock_comment_daily (trading_date);
    CREATE INDEX IF NOT EXISTS idx_a_stock_comment_daily_name ON a_stock_comment_daily (name);
    `
    if _, err := h.db.Exec(createAStockCommentDailySQL); err != nil {
        return fmt.Errorf("failed to create a_stock_comment_daily table: %v", err)
    }
    log.Println("Table a_stock_comment_daily ensured successfully")

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

// UpsertEtfDaily 单条ETF每日数据 upsert（独立表）
func (h *DatabaseHandler) UpsertEtfDaily(data *EtfDailyData) error {
	query := `
    INSERT INTO etf_daily (
        code, trading_date, name, latest_price, change_amount, change_percent,
        buy, sell, prev_close, open, high, low, volume, turnover
    ) VALUES ($1, $2, $3, $4, $5, $6,
              $7, $8, $9, $10, $11, $12, $13, $14)
    ON CONFLICT (code, trading_date) DO UPDATE SET
        name = EXCLUDED.name,
        latest_price = EXCLUDED.latest_price,
        change_amount = EXCLUDED.change_amount,
        change_percent = EXCLUDED.change_percent,
        buy = EXCLUDED.buy,
        sell = EXCLUDED.sell,
        prev_close = EXCLUDED.prev_close,
        open = EXCLUDED.open,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        volume = EXCLUDED.volume,
        turnover = EXCLUDED.turnover`

	_, err := h.db.Exec(query,
		data.Code, data.TradingDate, data.Name, data.LatestPrice, data.ChangeAmount, data.ChangePercent,
		data.Buy, data.Sell, data.PrevClose, data.Open, data.High, data.Low, data.Volume, data.Turnover,
	)
	if err != nil {
		return fmt.Errorf("failed to upsert etf daily: %v", err)
	}
	return nil
}

// BatchUpsertEtfDaily 批量 upsert ETF每日数据（独立表）
func (h *DatabaseHandler) BatchUpsertEtfDaily(dataList []EtfDailyData) error {
	tx, err := h.db.Begin()
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %v", err)
	}
	defer tx.Rollback()

	stmt, err := tx.Prepare(`
    INSERT INTO etf_daily (
        code, trading_date, name, latest_price, change_amount, change_percent,
        buy, sell, prev_close, open, high, low, volume, turnover
    ) VALUES ($1, $2, $3, $4, $5, $6,
              $7, $8, $9, $10, $11, $12, $13, $14)
    ON CONFLICT (code, trading_date) DO UPDATE SET
        name = EXCLUDED.name,
        latest_price = EXCLUDED.latest_price,
        change_amount = EXCLUDED.change_amount,
        change_percent = EXCLUDED.change_percent,
        buy = EXCLUDED.buy,
        sell = EXCLUDED.sell,
        prev_close = EXCLUDED.prev_close,
        open = EXCLUDED.open,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        volume = EXCLUDED.volume,
        turnover = EXCLUDED.turnover`)
	if err != nil {
		return fmt.Errorf("failed to prepare etf upsert statement: %v", err)
	}
	defer stmt.Close()

	for _, d := range dataList {
		if _, err := stmt.Exec(
			d.Code, d.TradingDate, d.Name, d.LatestPrice, d.ChangeAmount, d.ChangePercent,
			d.Buy, d.Sell, d.PrevClose, d.Open, d.High, d.Low, d.Volume, d.Turnover,
		); err != nil {
			return fmt.Errorf("failed to execute etf upsert batch: %v", err)
		}
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("failed to commit etf upsert batch: %v", err)
	}
	return nil
}

// UpsertIndexInfo 插入或更新指数基本信息
func (h *DatabaseHandler) UpsertIndexInfo(info *IndexInfo) error {
	query := `
    INSERT INTO index_info (code, display_name, publish_date)
    VALUES ($1, $2, $3)
    ON CONFLICT (code) DO UPDATE SET
        display_name = EXCLUDED.display_name,
        publish_date = EXCLUDED.publish_date`
	_, err := h.db.Exec(query, info.Code, info.DisplayName, info.PublishDate)
	if err != nil {
		return fmt.Errorf("failed to upsert index_info: %v", err)
	}
	return nil
}

// BatchUpsertIndexInfo 批量插入或更新指数基本信息
func (h *DatabaseHandler) BatchUpsertIndexInfo(list []IndexInfo) error {
	tx, err := h.db.Begin()
	if err != nil {
		return err
	}
	defer func() {
		if err != nil {
			tx.Rollback()
		}
	}()

	stmt, err := tx.Prepare(`
        INSERT INTO index_info (code, display_name, publish_date)
        VALUES ($1, $2, $3)
        ON CONFLICT (code) DO UPDATE SET
            display_name = EXCLUDED.display_name,
            publish_date = EXCLUDED.publish_date`)
	if err != nil {
		return err
	}
	defer stmt.Close()

	for _, v := range list {
		if _, err = stmt.Exec(v.Code, v.DisplayName, v.PublishDate); err != nil {
			return fmt.Errorf("batch upsert index_info failed: %v", err)
		}
	}

	if err = tx.Commit(); err != nil {
		return err
	}
	return nil
}

// UpsertIndexDaily 插入或更新指数每日数据
func (h *DatabaseHandler) UpsertIndexDaily(d *IndexDailyData) error {
	query := `
    INSERT INTO index_daily (
        code, trading_date, open, close, high, low, volume, amount, change_percent
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    ON CONFLICT (code, trading_date) DO UPDATE SET
        open = EXCLUDED.open,
        close = EXCLUDED.close,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        volume = EXCLUDED.volume,
        amount = EXCLUDED.amount,
        change_percent = EXCLUDED.change_percent`
	_, err := h.db.Exec(query,
		d.Code, d.TradingDate, d.Open, d.Close, d.High, d.Low, d.Volume, d.Amount, d.ChangePercent)
	if err != nil {
		return fmt.Errorf("failed to upsert index_daily: %v", err)
	}
	return nil
}

// BatchUpsertIndexDaily 批量插入或更新指数每日数据
func (h *DatabaseHandler) BatchUpsertIndexDaily(list []IndexDailyData) error {
	tx, err := h.db.Begin()
	if err != nil {
		return err
	}
	defer func() {
		if err != nil {
			tx.Rollback()
		}
	}()

	stmt, err := tx.Prepare(`
        INSERT INTO index_daily (
            code, trading_date, open, close, high, low, volume, amount, change_percent
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (code, trading_date) DO UPDATE SET
            open = EXCLUDED.open,
            close = EXCLUDED.close,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            volume = EXCLUDED.volume,
            amount = EXCLUDED.amount,
            change_percent = EXCLUDED.change_percent`)
	if err != nil {
		return err
	}
	defer stmt.Close()

	for _, v := range list {
		if _, err = stmt.Exec(v.Code, v.TradingDate, v.Open, v.Close, v.High, v.Low, v.Volume, v.Amount, v.ChangePercent); err != nil {
			return fmt.Errorf("batch upsert index_daily failed: %v", err)
		}
	}

	if err = tx.Commit(); err != nil {
		return err
	}
	return nil
}

// BatchUpsertAStockCommentDaily 批量插入或更新 A股每日评论/指标数据
func (h *DatabaseHandler) BatchUpsertAStockCommentDaily(list []StockCommentDaily) error {
    tx, err := h.db.Begin()
    if err != nil {
        return err
    }
    defer func() {
        if err != nil {
            tx.Rollback()
        }
    }()

    stmt, err := tx.Prepare(`
        INSERT INTO a_stock_comment_daily (
            code, trading_date, name, latest_price, change_percent, turnover_rate,
            pe_ratio, main_cost, institution_participation, composite_score,
            rise, current_rank, attention_index
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        ON CONFLICT (code, trading_date) DO UPDATE SET
            name = EXCLUDED.name,
            latest_price = EXCLUDED.latest_price,
            change_percent = EXCLUDED.change_percent,
            turnover_rate = EXCLUDED.turnover_rate,
            pe_ratio = EXCLUDED.pe_ratio,
            main_cost = EXCLUDED.main_cost,
            institution_participation = EXCLUDED.institution_participation,
            composite_score = EXCLUDED.composite_score,
            rise = EXCLUDED.rise,
            current_rank = EXCLUDED.current_rank,
            attention_index = EXCLUDED.attention_index`)
    if err != nil {
        return err
    }
    defer stmt.Close()

    for _, v := range list {
        if _, err = stmt.Exec(
            v.Code, v.TradingDate, v.Name, v.LatestPrice, v.ChangePercent, v.TurnoverRate,
            v.PeRatio, v.MainCost, v.InstitutionParticipation, v.CompositeScore,
            v.Rise, v.CurrentRank, v.AttentionIndex,
        ); err != nil {
            return fmt.Errorf("batch upsert a_stock_comment_daily failed: %v", err)
        }
    }

    if err = tx.Commit(); err != nil {
        return err
    }
    return nil
}

func (h *DatabaseHandler) GetAStockCommentDailyByName(name string, limit int, offset int) ([]StockCommentDaily, error) {
    query := `
    SELECT 
        code,
        trading_date,
        COALESCE(name, ''),
        COALESCE(latest_price, 0),
        COALESCE(change_percent, 0),
        COALESCE(turnover_rate, 0),
        COALESCE(pe_ratio, 0),
        COALESCE(main_cost, 0),
        COALESCE(institution_participation, 0),
        COALESCE(composite_score, 0),
        COALESCE(rise, 0),
        COALESCE(current_rank, 0),
        COALESCE(attention_index, 0)
    FROM a_stock_comment_daily
    WHERE name ILIKE $1
    ORDER BY trading_date DESC
    LIMIT $2 OFFSET $3`

    rows, err := h.db.Query(query, "%"+name+"%", limit, offset)
    if err != nil {
        return nil, fmt.Errorf("failed to query a_stock_comment_daily by name: %v", err)
    }
    defer rows.Close()

    var result []StockCommentDaily
    for rows.Next() {
        var item StockCommentDaily
        if err := rows.Scan(
            &item.Code, &item.TradingDate, &item.Name, &item.LatestPrice,
            &item.ChangePercent, &item.TurnoverRate, &item.PeRatio, &item.MainCost,
            &item.InstitutionParticipation, &item.CompositeScore, &item.Rise,
            &item.CurrentRank, &item.AttentionIndex,
        ); err != nil {
            return nil, fmt.Errorf("failed to scan a_stock_comment_daily row: %v", err)
        }
        result = append(result, item)
    }
    if len(result) == 0 {
        return nil, nil
    }
    return result, nil
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

// GetEtfDaily 根据 code 查询 ETF 每日数据（按日期倒序，支持分页）
func (h *DatabaseHandler) GetEtfDaily(code string, limit int, offset int) ([]EtfDailyData, error) {
	query := `
    SELECT code, trading_date, name, latest_price, change_amount, change_percent,
           buy, sell, prev_close, open, high, low, volume, turnover
    FROM etf_daily
    WHERE code = $1
    ORDER BY trading_date DESC
    LIMIT $2 OFFSET $3`

	rows, err := h.db.Query(query, code, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to query etf_daily: %v", err)
	}
	defer rows.Close()

	var results []EtfDailyData
	for rows.Next() {
		var d EtfDailyData
		if err := rows.Scan(
			&d.Code, &d.TradingDate, &d.Name, &d.LatestPrice, &d.ChangeAmount, &d.ChangePercent,
			&d.Buy, &d.Sell, &d.PrevClose, &d.Open, &d.High, &d.Low, &d.Volume, &d.Turnover,
		); err != nil {
			return nil, fmt.Errorf("failed to scan etf_daily row: %v", err)
		}
		results = append(results, d)
	}
	return results, nil
}

// GetEtfDailyByDateRange 根据日期区间查询 ETF 每日数据（按日期升序）
func (h *DatabaseHandler) GetEtfDailyByDateRange(code string, startDate, endDate time.Time) ([]EtfDailyData, error) {
	query := `
    SELECT code, trading_date, name, latest_price, change_amount, change_percent,
           buy, sell, prev_close, open, high, low, volume, turnover
    FROM etf_daily
    WHERE code = $1 AND trading_date >= $2 AND trading_date <= $3
    ORDER BY trading_date ASC`

	rows, err := h.db.Query(query, code, startDate, endDate)
	if err != nil {
		return nil, fmt.Errorf("failed to query etf_daily by date range: %v", err)
	}
	defer rows.Close()

	var results []EtfDailyData
	for rows.Next() {
		var d EtfDailyData
		if err := rows.Scan(
			&d.Code, &d.TradingDate, &d.Name, &d.LatestPrice, &d.ChangeAmount, &d.ChangePercent,
			&d.Buy, &d.Sell, &d.PrevClose, &d.Open, &d.High, &d.Low, &d.Volume, &d.Turnover,
		); err != nil {
			return nil, fmt.Errorf("failed to scan etf_daily row: %v", err)
		}
		results = append(results, d)
	}
	return results, nil
}

// GetIndexDaily 按 code 查询指数每日数据（分页，日期倒序）
func (h *DatabaseHandler) GetIndexDaily(code string, limit int, offset int) ([]IndexDailyData, error) {
	query := `
    SELECT code, trading_date, open, close, high, low, volume, amount, change_percent
    FROM index_daily
    WHERE code = $1
    ORDER BY trading_date DESC
    LIMIT $2 OFFSET $3`

	rows, err := h.db.Query(query, code, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to query index_daily: %v", err)
	}
	defer rows.Close()

	var result []IndexDailyData
	for rows.Next() {
		var item IndexDailyData
		if err := rows.Scan(&item.Code, &item.TradingDate, &item.Open, &item.Close, &item.High, &item.Low, &item.Volume, &item.Amount, &item.ChangePercent); err != nil {
			return nil, fmt.Errorf("failed to scan index_daily row: %v", err)
		}
		result = append(result, item)
	}
	if len(result) == 0 {
		return nil, nil
	}
	return result, nil
}

// GetIndexDailyByDateRange 按 code 与日期区间查询指数每日数据（日期正序）
func (h *DatabaseHandler) GetIndexDailyByDateRange(code string, startDate, endDate time.Time) ([]IndexDailyData, error) {
	query := `
    SELECT code, trading_date, open, close, high, low, volume, amount, change_percent
    FROM index_daily
    WHERE code = $1 AND trading_date BETWEEN $2 AND $3
    ORDER BY trading_date ASC`

	rows, err := h.db.Query(query, code, startDate, endDate)
	if err != nil {
		return nil, fmt.Errorf("failed to query index_daily by date range: %v", err)
	}
	defer rows.Close()

	var result []IndexDailyData
	for rows.Next() {
		var item IndexDailyData
		if err := rows.Scan(&item.Code, &item.TradingDate, &item.Open, &item.Close, &item.High, &item.Low, &item.Volume, &item.Amount, &item.ChangePercent); err != nil {
			return nil, fmt.Errorf("failed to scan index_daily row: %v", err)
		}
		result = append(result, item)
	}
	if len(result) == 0 {
		return nil, nil
	}
	return result, nil
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
		Code:    200,
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
		Code:    200,
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
		Code:    200,
		Message: "Success",
		Data:    data,
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
		Code:    200,
		Message: "Success",
		Data:    data,
	})
}

// insertEtfDailyHandler 单条ETF每日数据 upsert（HTTP）
func (h *DatabaseHandler) insertEtfDailyHandler(c *gin.Context) {
	var req struct {
		Code          string  `json:"code"`
		TradingDate   string  `json:"trading_date"` // YYYY-MM-DD
		Name          string  `json:"name"`
		LatestPrice   float64 `json:"latest_price"`
		ChangeAmount  float64 `json:"change_amount"`
		ChangePercent float64 `json:"change_percent"`
		Buy           float64 `json:"buy"`
		Sell          float64 `json:"sell"`
		PrevClose     float64 `json:"prev_close"`
		Open          float64 `json:"open"`
		High          float64 `json:"high"`
		Low           float64 `json:"low"`
		Volume        int64   `json:"volume"`
		Turnover      int64   `json:"turnover"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
		return
	}
	if req.Code == "" || req.TradingDate == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "code and trading_date are required"})
		return
	}
	tDate, err := time.Parse("2006-01-02", req.TradingDate)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid trading_date format (YYYY-MM-DD)"})
		return
	}

	data := EtfDailyData{
		Code:          req.Code,
		TradingDate:   tDate,
		Name:          req.Name,
		LatestPrice:   req.LatestPrice,
		ChangeAmount:  req.ChangeAmount,
		ChangePercent: req.ChangePercent,
		Buy:           req.Buy,
		Sell:          req.Sell,
		PrevClose:     req.PrevClose,
		Open:          req.Open,
		High:          req.High,
		Low:           req.Low,
		Volume:        req.Volume,
		Turnover:      req.Turnover,
	}

	if err := h.UpsertEtfDaily(&data); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "ETF daily upsert success"})
}

// batchInsertEtfDailyHandler 批量ETF每日数据 upsert（HTTP）
func (h *DatabaseHandler) batchInsertEtfDailyHandler(c *gin.Context) {
	var reqList []struct {
		Code          string  `json:"code"`
		TradingDate   string  `json:"trading_date"`
		Name          string  `json:"name"`
		LatestPrice   float64 `json:"latest_price"`
		ChangeAmount  float64 `json:"change_amount"`
		ChangePercent float64 `json:"change_percent"`
		Buy           float64 `json:"buy"`
		Sell          float64 `json:"sell"`
		PrevClose     float64 `json:"prev_close"`
		Open          float64 `json:"open"`
		High          float64 `json:"high"`
		Low           float64 `json:"low"`
		Volume        int64   `json:"volume"`
		Turnover      int64   `json:"turnover"`
	}
	if err := c.ShouldBindJSON(&reqList); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
		return
	}
	if len(reqList) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "empty list"})
		return
	}

	dataList := make([]EtfDailyData, 0, len(reqList))
	for i, r := range reqList {
		if r.Code == "" || r.TradingDate == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("code and trading_date required at index %d", i)})
			return
		}
		tDate, err := time.Parse("2006-01-02", r.TradingDate)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("invalid trading_date at index %d", i)})
			return
		}
		dataList = append(dataList, EtfDailyData{
			Code:          r.Code,
			TradingDate:   tDate,
			Name:          r.Name,
			LatestPrice:   r.LatestPrice,
			ChangeAmount:  r.ChangeAmount,
			ChangePercent: r.ChangePercent,
			Buy:           r.Buy,
			Sell:          r.Sell,
			PrevClose:     r.PrevClose,
			Open:          r.Open,
			High:          r.High,
			Low:           r.Low,
			Volume:        r.Volume,
			Turnover:      r.Turnover,
		})
	}

	if err := h.BatchUpsertEtfDaily(dataList); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "ETF daily batch upsert success", Data: gin.H{"count": len(dataList)}})
}

// getEtfDailyHandler 按 code 查询 ETF 每日数据（分页）
func (h *DatabaseHandler) getEtfDailyHandler(c *gin.Context) {
	code := c.Param("code")
	var req struct {
		Limit  *int `json:"limit"`
		Offset *int `json:"offset"`
	}
	if err := c.ShouldBindJSON(&req); err != nil && err.Error() != "EOF" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
		return
	}
	limit := 100
	if req.Limit != nil {
		limit = *req.Limit
	}
	offset := 0
	if req.Offset != nil {
		offset = *req.Offset
	}

	data, err := h.GetEtfDaily(code, limit, offset)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: data})
}

// getEtfDailyByDateRangeHandler 按日期区间查询 ETF 每日数据
func (h *DatabaseHandler) getEtfDailyByDateRangeHandler(c *gin.Context) {
	code := c.Param("code")
	var req struct {
		StartDate string `json:"start_date"`
		EndDate   string `json:"end_date"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
		return
	}
	if req.StartDate == "" || req.EndDate == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "start_date and end_date are required"})
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

	data, err := h.GetEtfDailyByDateRange(code, startDate, endDate)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: data})
}

// insertIndexInfoHandler 单条插入/更新指数基本信息
func (h *DatabaseHandler) insertIndexInfoHandler(c *gin.Context) {
	var req struct {
		Code        string `json:"code"`
		DisplayName string `json:"display_name"`
		PublishDate string `json:"publish_date"` // YYYY-MM-DD
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
		return
	}
	if req.Code == "" || req.PublishDate == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "code and publish_date are required"})
		return
	}
	pDate, err := time.Parse("2006-01-02", req.PublishDate)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid publish_date format (YYYY-MM-DD)"})
		return
	}
	payload := IndexInfo{Code: req.Code, DisplayName: req.DisplayName, PublishDate: pDate}
	if err := h.UpsertIndexInfo(&payload); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: gin.H{"affected": 1}})
}

// batchInsertIndexInfoHandler 批量插入/更新指数基本信息
func (h *DatabaseHandler) batchInsertIndexInfoHandler(c *gin.Context) {
	var req []struct {
		Code        string `json:"code"`
		DisplayName string `json:"display_name"`
		PublishDate string `json:"publish_date"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
		return
	}
	if len(req) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "empty list"})
		return
	}
	list := make([]IndexInfo, 0, len(req))
	for i, v := range req {
		if v.Code == "" || v.PublishDate == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("item %d missing code or publish_date", i)})
			return
		}
		pDate, err := time.Parse("2006-01-02", v.PublishDate)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("item %d invalid publish_date format", i)})
			return
		}
		list = append(list, IndexInfo{Code: v.Code, DisplayName: v.DisplayName, PublishDate: pDate})
	}
	if err := h.BatchUpsertIndexInfo(list); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: gin.H{"affected": len(list)}})
}

// insertIndexDailyHandler 单条插入/更新指数每日数据
func (h *DatabaseHandler) insertIndexDailyHandler(c *gin.Context) {
	var req struct {
		Code          string  `json:"code"`
		TradingDate   string  `json:"trading_date"`
		Open          float64 `json:"open"`
		Close         float64 `json:"close"`
		High          float64 `json:"high"`
		Low           float64 `json:"low"`
		Volume        int64   `json:"volume"`
		Amount        float64 `json:"amount"`
		ChangePercent float64 `json:"change_percent"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
		return
	}
	if req.Code == "" || req.TradingDate == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "code and trading_date are required"})
		return
	}
	tDate, err := time.Parse("2006-01-02", req.TradingDate)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid trading_date format (YYYY-MM-DD)"})
		return
	}
	payload := IndexDailyData{
		Code:          req.Code,
		TradingDate:   tDate,
		Open:          req.Open,
		Close:         req.Close,
		High:          req.High,
		Low:           req.Low,
		Volume:        req.Volume,
		Amount:        req.Amount,
		ChangePercent: req.ChangePercent,
	}
	if err := h.UpsertIndexDaily(&payload); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: gin.H{"affected": 1}})
}

// batchInsertIndexDailyHandler 批量插入/更新指数每日数据
func (h *DatabaseHandler) batchInsertIndexDailyHandler(c *gin.Context) {
	var req []struct {
		Code          string  `json:"code"`
		TradingDate   string  `json:"trading_date"`
		Open          float64 `json:"open"`
		Close         float64 `json:"close"`
		High          float64 `json:"high"`
		Low           float64 `json:"low"`
		Volume        int64   `json:"volume"`
		Amount        float64 `json:"amount"`
		ChangePercent float64 `json:"change_percent"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
		return
	}
	if len(req) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "empty list"})
		return
	}
	list := make([]IndexDailyData, 0, len(req))
	for i, v := range req {
		if v.Code == "" || v.TradingDate == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("item %d missing code or trading_date", i)})
			return
		}
		tDate, err := time.Parse("2006-01-02", v.TradingDate)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("item %d invalid trading_date format", i)})
			return
		}
		list = append(list, IndexDailyData{
			Code:          v.Code,
			TradingDate:   tDate,
			Open:          v.Open,
			Close:         v.Close,
			High:          v.High,
			Low:           v.Low,
			Volume:        v.Volume,
			Amount:        v.Amount,
			ChangePercent: v.ChangePercent,
		})
	}
	if err := h.BatchUpsertIndexDaily(list); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: gin.H{"affected": len(list)}})
}

// batchInsertAStockCommentDailyHandler 批量插入/更新 A股每日评论/指标数据
func (h *DatabaseHandler) batchInsertAStockCommentDailyHandler(c *gin.Context) {
    var req []struct {
        Code                   string  `json:"code"`
        TradingDate            string  `json:"trading_date"`
        Name                   string  `json:"name"`
        LatestPrice            float64 `json:"latest_price"`
        ChangePercent          float64 `json:"change_percent"`
        TurnoverRate           float64 `json:"turnover_rate"`
        PeRatio                float64 `json:"pe_ratio"`
        MainCost               float64 `json:"main_cost"`
        InstitutionParticipation float64 `json:"institution_participation"`
        CompositeScore         float64 `json:"composite_score"`
        Rise                   int64   `json:"rise"`
        CurrentRank            int64   `json:"current_rank"`
        AttentionIndex         float64 `json:"attention_index"`
    }
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
        return
    }
    if len(req) == 0 {
        c.JSON(http.StatusBadRequest, gin.H{"error": "empty list"})
        return
    }
    list := make([]StockCommentDaily, 0, len(req))
    for i, v := range req {
        if v.Code == "" || v.TradingDate == "" {
            c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("item %d missing code or trading_date", i)})
            return
        }
        tDate, err := time.Parse("2006-01-02", v.TradingDate)
        if err != nil {
            c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("item %d invalid trading_date format", i)})
            return
        }
        list = append(list, StockCommentDaily{
            Code:                   v.Code,
            TradingDate:            tDate,
            Name:                   v.Name,
            LatestPrice:            v.LatestPrice,
            ChangePercent:          v.ChangePercent,
            TurnoverRate:           v.TurnoverRate,
            PeRatio:                v.PeRatio,
            MainCost:               v.MainCost,
            InstitutionParticipation: v.InstitutionParticipation,
            CompositeScore:         v.CompositeScore,
            Rise:                   v.Rise,
            CurrentRank:            v.CurrentRank,
            AttentionIndex:         v.AttentionIndex,
        })
    }
    if err := h.BatchUpsertAStockCommentDaily(list); err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: gin.H{"affected": len(list)}})
}

func (h *DatabaseHandler) getAStockCommentDailyByNameHandler(c *gin.Context) {
    var req struct {
        Name   string `json:"name"`
        Limit  *int   `json:"limit"`
        Offset *int   `json:"offset"`
    }
    if err := c.ShouldBindJSON(&req); err != nil && err.Error() != "EOF" {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
        return
    }
    if strings.TrimSpace(req.Name) == "" {
        c.JSON(http.StatusBadRequest, gin.H{"error": "name is required"})
        return
    }
    limit := 20
    if req.Limit != nil && *req.Limit > 0 {
        limit = *req.Limit
    }
    offset := 0
    if req.Offset != nil && *req.Offset >= 0 {
        offset = *req.Offset
    }

    data, err := h.GetAStockCommentDailyByName(req.Name, limit, offset)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: data})
}

// getIndexDailyHandler 分页查询指数每日数据（日期倒序）
func (h *DatabaseHandler) getIndexDailyHandler(c *gin.Context) {
	code := c.Param("code")
	var req struct {
		Limit  int `json:"limit"`
		Offset int `json:"offset"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		// 允许空 JSON，使用默认值
		req.Limit = 20
		req.Offset = 0
	}
	if req.Limit <= 0 {
		req.Limit = 20
	}
	if req.Offset < 0 {
		req.Offset = 0
	}

	data, err := h.GetIndexDaily(code, req.Limit, req.Offset)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: data})
}

// getIndexDailyByDateRangeHandler 日期区间查询指数每日数据（日期正序）
func (h *DatabaseHandler) getIndexDailyByDateRangeHandler(c *gin.Context) {
	code := c.Param("code")
	var req struct {
		StartDate string `json:"start_date"`
		EndDate   string `json:"end_date"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
		return
	}
	if req.StartDate == "" || req.EndDate == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "start_date and end_date are required"})
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

	data, err := h.GetIndexDailyByDateRange(code, startDate, endDate)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: data})
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

		// ETF每日数据（独立表）写入
		api.POST("/etf/daily", handler.insertEtfDailyHandler)
		api.POST("/etf/daily/batch", handler.batchInsertEtfDailyHandler)

		// ETF每日数据（独立表）查询
		api.POST("/etf/daily/:code", handler.getEtfDailyHandler)
		api.POST("/etf/daily/:code/range", handler.getEtfDailyByDateRangeHandler)

		// 指数基本信息与每日数据
		api.POST("/index/info", handler.insertIndexInfoHandler)
		api.POST("/index/info/batch", handler.batchInsertIndexInfoHandler)
		api.POST("/index/daily", handler.insertIndexDailyHandler)
		api.POST("/index/daily/batch", handler.batchInsertIndexDailyHandler)
		api.POST("/index/daily/:code", handler.getIndexDailyHandler)
        api.POST("/index/daily/:code/range", handler.getIndexDailyByDateRangeHandler)
        // A股每日评论/指标数据（stock_comment_em）批量写入
        api.POST("/stock/comment/daily/batch", handler.batchInsertAStockCommentDailyHandler)
        api.POST("/stock/comment/daily/search", handler.getAStockCommentDailyByNameHandler)
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
	log.Printf("  POST /api/v1/etf/daily - Upsert single ETF daily data")
	log.Printf("  POST /api/v1/etf/daily/batch - Batch upsert ETF daily data")
	log.Printf("  POST /api/v1/etf/daily/:code - Query ETF daily data (JSON body: {limit, offset})")
	log.Printf("  POST /api/v1/etf/daily/:code/range - Query ETF daily data by date range (JSON body: {start_date, end_date})")
	log.Printf("  POST /api/v1/index/info - Upsert single index info")
	log.Printf("  POST /api/v1/index/info/batch - Batch upsert index info")
	log.Printf("  POST /api/v1/index/daily - Upsert single index daily data")
	log.Printf("  POST /api/v1/index/daily/batch - Batch upsert index daily data")
    log.Printf("  POST /api/v1/index/daily/:code - Query index daily data (JSON body: {limit, offset})")
    log.Printf("  POST /api/v1/index/daily/:code/range - Query index daily data by date range (JSON body: {start_date, end_date})")
    log.Printf("  POST /api/v1/stock/comment/daily/batch - Batch upsert A-stock comment daily metrics")
    log.Printf("  POST /api/v1/stock/comment/daily/search - Query A-stock comment daily by name (JSON body: {name, limit, offset})")
    log.Printf("  GET  /health - Health check")

	if err := r.Run(":" + port); err != nil {
		log.Fatal("Server failed to start:", err)
	}
}

// TokenAuthMiddleware 使用固定token进行简单鉴权
// 客户端需要在请求头中携带：
//   - X-Token: <token>
//     或 Authorization: Bearer <token>
//
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
