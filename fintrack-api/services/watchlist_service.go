package services

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"math"
	"net/http"
	"strings"
	"time"

	"fintrack-api/config"
	"fintrack-api/database"
	"fintrack-api/models"
)

type WatchlistService struct {
	db     *database.DB
	config *config.Config
}

func NewWatchlistService(db *database.DB, cfg *config.Config) *WatchlistService {
	return &WatchlistService{db: db, config: cfg}
}

var ErrSymbolNotFound = errors.New("symbol not found")
var ErrDuplicateSymbol = errors.New("duplicate symbol")

func (s *WatchlistService) AddToWatchlist(userID int, req *models.AddToWatchlistRequest) error {
	stockType := 1
	if req.StockType != nil {
		stockType = *req.StockType
	}

	var name sql.NullString
	symLower := strings.ToLower(req.Symbol)

	var exists bool
	if err := s.db.Conn.QueryRow(`SELECT EXISTS(SELECT 1 FROM user_watchlist WHERE user_id = $1 AND symbol = $2)`, userID, symLower).Scan(&exists); err != nil {
		return fmt.Errorf("failed to check duplicate: %v", err)
	}
	if exists {
		return ErrDuplicateSymbol
	}
	code := strings.TrimPrefix(strings.TrimPrefix(symLower, "sh"), "sz")
	var table string
	if stockType == 2 {
		table = "etf_daily"
	} else {
		table = "a_stock_comment_daily"
	}
	query := fmt.Sprintf("SELECT COALESCE(name, '') FROM %s WHERE code = $1 OR code = $2 ORDER BY trading_date DESC LIMIT 1", table)
	err := s.db.Conn.QueryRow(query, code, symLower).Scan(&name)
	if err == sql.ErrNoRows {
		return ErrSymbolNotFound
	}
	if err != nil {
		return fmt.Errorf("failed to query %s: %v", table, err)
	}

	nameStr := strings.TrimSpace(name.String)
	if nameStr != "" {
		_, err = s.db.Conn.Exec(
			`INSERT INTO stocks (symbol, company_name) VALUES ($1, $2)
             ON CONFLICT (symbol) DO UPDATE SET company_name = EXCLUDED.company_name`,
			symLower, nameStr,
		)
		if err != nil {
			log.Printf("upsert stocks failed, continue without company_name: %v", err)
		}
	}

	_, err = s.db.Conn.Exec(`
		INSERT INTO user_watchlist (user_id, symbol, notes, stock_type) 
		VALUES ($1, $2, $3, $4)
	`, userID, symLower, req.Notes, stockType)

	if err != nil {
		return fmt.Errorf("failed to add to watchlist: %v", err)
	}

	return nil
}

func (s *WatchlistService) GetLatestQuotesBySymbols(symbols []string) ([]models.LatestQuote, error) {
	if len(symbols) == 0 {
		return []models.LatestQuote{}, nil
	}

	codes := make([]string, 0, len(symbols))
	symbolsLower := make([]string, 0, len(symbols))
	codeToSymbol := make(map[string]string, len(symbols)*2)
	for _, sym := range symbols {
		lower := strings.ToLower(sym)
		c := strings.TrimPrefix(strings.TrimPrefix(lower, "sh"), "sz")
		codes = append(codes, c)
		symbolsLower = append(symbolsLower, lower)
		codeToSymbol[c] = sym
		codeToSymbol[lower] = sym
	}

	placeholders := make([]string, len(codes))
	args := make([]interface{}, len(codes))
	for i, c := range codes {
		placeholders[i] = fmt.Sprintf("$%d", i+1)
		args[i] = c
	}

	qStock := fmt.Sprintf(`
        SELECT DISTINCT ON (code) code, trading_date, latest_price, change_percent, turnover_rate
        FROM a_stock_comment_daily
        WHERE code IN (%s)
        ORDER BY code, trading_date DESC
    `, strings.Join(placeholders, ","))

	rows, err := s.db.Conn.Query(qStock, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to query a_stock_comment_daily: %v", err)
	}
	defer rows.Close()

	quotes := make(map[string]models.LatestQuote)
	for rows.Next() {
		var code string
		var dt time.Time
		var price sql.NullFloat64
		var change sql.NullFloat64
		var turnover sql.NullFloat64
		if err := rows.Scan(&code, &dt, &price, &change, &turnover); err != nil {
			return nil, fmt.Errorf("failed to scan a_stock_comment_daily: %v", err)
		}
		sym := codeToSymbol[code]
		p := models.LatestQuote{Symbol: sym}
		ds := dt.Format("2006-01-02")
		p.TradingDate = &ds
		if price.Valid {
			p.LatestPrice = &price.Float64
		}
		if change.Valid {
			p.ChangePercent = &change.Float64
		}
		if turnover.Valid {
			p.TurnoverRate = &turnover.Float64
		}
		quotes[code] = p
	}

	etfPlaceholders := make([]string, len(symbolsLower))
	etfArgs := make([]interface{}, 0, len(codes)+len(symbolsLower))
	// numeric code placeholders first
	etfArgs = append(etfArgs, args...)
	for i := range symbolsLower {
		etfPlaceholders[i] = fmt.Sprintf("$%d", len(etfArgs)+i+1)
	}
	for _, sl := range symbolsLower {
		etfArgs = append(etfArgs, sl)
	}

	qEtf := fmt.Sprintf(`
        SELECT DISTINCT ON (code) code, trading_date, latest_price, change_percent
        FROM etf_daily
        WHERE code IN (%s) OR LOWER(code) IN (%s)
        ORDER BY code, trading_date DESC
    `, strings.Join(placeholders, ","), strings.Join(etfPlaceholders, ","))

	rows2, err := s.db.Conn.Query(qEtf, etfArgs...)
	if err != nil {
		return nil, fmt.Errorf("failed to query etf_daily: %v", err)
	}
	defer rows2.Close()
	for rows2.Next() {
		var code string
		var dt time.Time
		var price sql.NullFloat64
		var change sql.NullFloat64
		if err := rows2.Scan(&code, &dt, &price, &change); err != nil {
			return nil, fmt.Errorf("failed to scan etf_daily: %v", err)
		}
		sym := codeToSymbol[code]
		if sym == "" {
			norm := strings.TrimPrefix(strings.TrimPrefix(strings.ToLower(code), "sh"), "sz")
			sym = codeToSymbol[norm]
		}
		p := models.LatestQuote{Symbol: sym}
		ds := dt.Format("2006-01-02")
		p.TradingDate = &ds
		if price.Valid {
			p.LatestPrice = &price.Float64
		}
		if change.Valid {
			p.ChangePercent = &change.Float64
		}
		if _, exists := quotes[code]; !exists {
			// Always store by normalized numeric code to align with stock side mapping
			norm := strings.TrimPrefix(strings.TrimPrefix(strings.ToLower(code), "sh"), "sz")
			quotes[norm] = p
		}
	}

	result := make([]models.LatestQuote, 0, len(symbols))
	for _, c := range codes {
		if q, ok := quotes[c]; ok {
			result = append(result, q)
		} else {
			result = append(result, models.LatestQuote{Symbol: codeToSymbol[c]})
		}
	}
	return result, nil
}

func (s *WatchlistService) LookupStockName(symbol string, stockType int) (string, error) {
	var name sql.NullString
	code := strings.TrimPrefix(strings.TrimPrefix(strings.ToLower(symbol), "sh"), "sz")
	var table string
	if stockType == 2 {
		table = "etf_daily"
		query := fmt.Sprintf("SELECT COALESCE(name, '') FROM %s WHERE code = $1 OR code = $2 ORDER BY trading_date DESC LIMIT 1", table)
		err := s.db.Conn.QueryRow(query, code, symbol).Scan(&name)
		if err == sql.ErrNoRows {
			return "", ErrSymbolNotFound
		}
		if err != nil {
			return "", fmt.Errorf("failed to query %s: %v", table, err)
		}
		return strings.TrimSpace(name.String), nil
	} else {
		table = "a_stock_comment_daily"
		// 股票仅使用6位数字code进行匹配
		query := fmt.Sprintf("SELECT COALESCE(name, '') FROM %s WHERE code = $1 ORDER BY trading_date DESC LIMIT 1", table)
		err := s.db.Conn.QueryRow(query, code).Scan(&name)
		if err == sql.ErrNoRows {
			return "", ErrSymbolNotFound
		}
		if err != nil {
			return "", fmt.Errorf("failed to query %s: %v", table, err)
		}
		return strings.TrimSpace(name.String), nil
	}
}

func (s *WatchlistService) GetWatchlist(userID int) ([]models.WatchlistItem, error) {
	rows, err := s.db.Conn.Query(`
		SELECT 
			uw.id, uw.symbol, uw.added_at, uw.notes, COALESCE(uw.stock_type, 1),
			COALESCE(s.company_name, ''),
			COALESCE(tbp.unique_key, ''),
			COALESCE(tbp.timesfm_version, ''),
			COALESCE(uw.strategy_unique_key, ''),
			COALESCE(tsp.name, '')
		FROM user_watchlist uw
		LEFT JOIN stocks s ON uw.symbol = s.symbol
		LEFT JOIN LATERAL (
			SELECT unique_key, timesfm_version
			FROM timesfm_best_predictions
			WHERE symbol = uw.symbol
			ORDER BY created_at DESC
			LIMIT 1
		) tbp ON true
		LEFT JOIN timesfm_strategy_params tsp ON uw.strategy_unique_key = tsp.unique_key
		WHERE uw.user_id = $1
		ORDER BY uw.added_at DESC
	`, userID)

	if err != nil {
		return nil, fmt.Errorf("failed to get watchlist: %v", err)
	}
	defer rows.Close()

	items := []models.WatchlistItem{}
	for rows.Next() {
		var item models.WatchlistItem
		var uniqueKey, version, strategyKey, strategyName string
		var stockType int

		err := rows.Scan(
			&item.ID, &item.Stock.Symbol, &item.AddedAt, &item.Notes, &stockType,
			&item.Stock.CompanyName,
			&uniqueKey, &version,
			&strategyKey, &strategyName,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan watchlist item: %v", err)
		}

		item.UniqueKey = uniqueKey
		item.StockType = &stockType
		item.StrategyUniqueKey = strategyKey
		item.StrategyName = strategyName
		items = append(items, item)
	}

	return items, nil
}

func (s *WatchlistService) BindStrategy(userID int, req *models.BindStrategyRequest) error {
	// Check if strategy exists
	var exists bool
	err := s.db.Conn.QueryRow(`
		SELECT EXISTS(SELECT 1 FROM timesfm_strategy_params WHERE unique_key = $1 AND (user_id = $2 OR user_id IS NULL))
	`, req.StrategyUniqueKey, userID).Scan(&exists)
	if err != nil {
		return fmt.Errorf("failed to check strategy existence: %v", err)
	}
	if !exists {
		return fmt.Errorf("strategy not found")
	}

	// Update user_watchlist
	// Note: symbol in request might need normalization or we assume it matches what's in DB
	// Assuming symbol matches.
	res, err := s.db.Conn.Exec(`
		UPDATE user_watchlist 
		SET strategy_unique_key = $1
		WHERE user_id = $2 AND symbol = $3
	`, req.StrategyUniqueKey, userID, req.Symbol)

	if err != nil {
		return fmt.Errorf("failed to bind strategy: %v", err)
	}

	rowsAffected, _ := res.RowsAffected()
	if rowsAffected == 0 {
		return fmt.Errorf("watchlist item not found for symbol %s", req.Symbol)
	}

	return nil
}

func (s *WatchlistService) RemoveFromWatchlist(userID, watchlistID int) error {
	// Check if the watchlist item belongs to the user
	var exists bool
	err := s.db.Conn.QueryRow(`
		SELECT EXISTS(SELECT 1 FROM user_watchlist WHERE id = $1 AND user_id = $2)
	`, watchlistID, userID).Scan(&exists)
	if err != nil {
		return fmt.Errorf("failed to check watchlist ownership: %v", err)
	}
	if !exists {
		return fmt.Errorf("watchlist item not found")
	}

	// Remove from watchlist
	_, err = s.db.Conn.Exec(`
		DELETE FROM user_watchlist WHERE id = $1 AND user_id = $2
	`, watchlistID, userID)
	if err != nil {
		return fmt.Errorf("failed to remove from watchlist: %v", err)
	}

	return nil
}

func (s *WatchlistService) UpdateWatchlistItem(userID, watchlistID int, req *models.UpdateWatchlistRequest) (*models.WatchlistItem, error) {
	// Update the watchlist item
	_, err := s.db.Conn.Exec(`
		UPDATE user_watchlist 
		SET notes = $1
		WHERE id = $2 AND user_id = $3
	`, req.Notes, watchlistID, userID)
	if err != nil {
		return nil, fmt.Errorf("failed to update watchlist item: %v", err)
	}

	// Return the updated item
	return s.getWatchlistItemByID(watchlistID)
}

func (s *WatchlistService) getWatchlistItemByID(watchlistID int) (*models.WatchlistItem, error) {
	row := s.db.Conn.QueryRow(`
		SELECT 
			uw.id, uw.added_at, uw.notes,
			s.id, s.symbol, s.company_name, s.exchange, s.sector, s.industry, s.market_cap, s.created_at, s.updated_at,
			sp.price, sp.change_percent, sp.volume
		FROM user_watchlist uw
		JOIN stocks s ON uw.stock_id = s.id
		LEFT JOIN LATERAL (
			SELECT price, change_percent, volume
			FROM stock_prices 
			WHERE stock_id = s.id 
			ORDER BY recorded_at DESC 
			LIMIT 1
		) sp ON true
		WHERE uw.id = $1
	`, watchlistID)

	var item models.WatchlistItem
	var price sql.NullFloat64
	var changePercent sql.NullFloat64
	var volume sql.NullInt64

	err := row.Scan(
		&item.ID, &item.AddedAt, &item.Notes,
		&item.Stock.ID, &item.Stock.Symbol, &item.Stock.CompanyName,
		&item.Stock.Exchange, &item.Stock.Sector, &item.Stock.Industry,
		&item.Stock.MarketCap, &item.Stock.CreatedAt, &item.Stock.UpdatedAt,
		&price, &changePercent, &volume,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to get watchlist item: %v", err)
	}

	// Set current price if available
	if price.Valid {
		item.CurrentPrice = &models.StockPrice{
			Price:         price.Float64,
			ChangePercent: &changePercent.Float64,
			Volume:        &volume.Int64,
		}
	}

	return &item, nil
}

// SyncStockData calls the Python service to sync stock data
func (s *WatchlistService) SyncStockData(symbol string) {
	// Parse exchange prefix to determine stock type
	stockType := 1 // default to Shanghai (sh)
	if strings.HasPrefix(symbol, "sz") {
		stockType = 2 // Shenzhen
	}

	// Remove prefix for the actual stock code
	cleanSymbol := strings.TrimPrefix(strings.TrimPrefix(symbol, "sh"), "sz")

	// Prepare request payload
	payload := map[string]interface{}{
		"symbol":     cleanSymbol,
		"stock_type": stockType,
		"batch_size": 1000,
	}

	jsonData, err := json.Marshal(payload)
	if err != nil {
		log.Printf("Failed to marshal sync request: %v", err)
		return
	}

	// Call Python service
	url := fmt.Sprintf("%s/api/sync-stock", s.config.PythonService.BaseURL)
	client := &http.Client{
		Timeout: time.Duration(s.config.PythonService.Timeout) * time.Second,
	}

	resp, err := client.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		log.Printf("Failed to call Python sync service: %v", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("Python sync service returned non-200 status: %d", resp.StatusCode)
		return
	}

	log.Printf("Successfully triggered stock data sync for %s (type: %d)", cleanSymbol, stockType)
}

func (s *WatchlistService) TriggerTimesfmPredict(req *models.TimesfmPredictRequest) (int, map[string]interface{}, error) {
	cleanSymbol := strings.TrimPrefix(strings.TrimPrefix(req.Symbol, "sh"), "sz")
	payload := map[string]interface{}{
		"stock_code": cleanSymbol,
		"stock_type": "stock",
	}
	if req.Years != nil {
		payload["years"] = *req.Years
	}
	if req.HorizonLen != nil {
		payload["horizon_len"] = *req.HorizonLen
	}
	if req.ContextLen != nil {
		payload["context_len"] = *req.ContextLen
	}
	if req.TimeStep != nil {
		payload["time_step"] = *req.TimeStep
	}
	if req.IncludeTechnicalIndicators != nil {
		payload["include_technical_indicators"] = *req.IncludeTechnicalIndicators
	}
	if req.FixedEndDate != nil {
		payload["fixed_end_date"] = *req.FixedEndDate
	}
	if req.PredictionMode != nil {
		payload["prediction_mode"] = *req.PredictionMode
	}

	jsonData, err := json.Marshal(payload)
	if err != nil {
		return 0, nil, fmt.Errorf("marshal predict payload: %v", err)
	}
	url := fmt.Sprintf("%s/predict_for_best", s.config.PythonService.BaseURL)
	client := &http.Client{Timeout: time.Duration(s.config.PythonService.Timeout) * time.Second}
	resp, err := client.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return 0, nil, fmt.Errorf("call python predict: %v", err)
	}
	defer resp.Body.Close()
	var body map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		return resp.StatusCode, nil, fmt.Errorf("decode python predict response: %v", err)
	}
	return resp.StatusCode, body, nil
}

func (s *WatchlistService) RunTimesfmBacktest(req *models.TimesfmBacktestRequest) (int, map[string]interface{}, error) {
	cleanSymbol := strings.TrimPrefix(strings.TrimPrefix(req.Symbol, "sh"), "sz")
	payload := map[string]interface{}{
		"stock_code": cleanSymbol,
		"stock_type": "stock",
	}
	if req.StockType != nil {
		payload["stock_type"] = *req.StockType
	}
	if req.Years != nil {
		payload["years"] = *req.Years
	}
	if req.HorizonLen != nil {
		payload["horizon_len"] = *req.HorizonLen
	}
	if req.ContextLen != nil {
		payload["context_len"] = *req.ContextLen
	}
	if req.TimeStep != nil {
		payload["time_step"] = *req.TimeStep
	}
	if req.StartDate != nil {
		payload["start_date"] = *req.StartDate
	}
	if req.EndDate != nil {
		payload["end_date"] = *req.EndDate
	}
	if req.TimesfmVersion != nil {
		payload["timesfm_version"] = *req.TimesfmVersion
	} else {
		payload["timesfm_version"] = "2.0"
	}
	if req.UserID != nil {
		payload["user_id"] = *req.UserID
	}
	if req.BuyThresholdPct != nil {
		payload["buy_threshold_pct"] = *req.BuyThresholdPct
	}
	if req.SellThresholdPct != nil {
		payload["sell_threshold_pct"] = *req.SellThresholdPct
	}
	if req.InitialCash != nil {
		payload["initial_cash"] = *req.InitialCash
	}
	if req.EnableRebalance != nil {
		payload["enable_rebalance"] = *req.EnableRebalance
	}
	if req.MaxPositionPct != nil {
		payload["max_position_pct"] = *req.MaxPositionPct
	}
	if req.MinPositionPct != nil {
		payload["min_position_pct"] = *req.MinPositionPct
	}
	if req.SlopePositionPerPct != nil {
		payload["slope_position_per_pct"] = *req.SlopePositionPerPct
	}
	if req.RebalanceTolerancePct != nil {
		payload["rebalance_tolerance_pct"] = *req.RebalanceTolerancePct
	}
	if req.TradeFeeRate != nil {
		payload["trade_fee_rate"] = *req.TradeFeeRate
	}
	if req.TakeProfitThresholdPct != nil {
		payload["take_profit_threshold_pct"] = *req.TakeProfitThresholdPct
	}
	if req.TakeProfitSellFrac != nil {
		payload["take_profit_sell_frac"] = *req.TakeProfitSellFrac
	}

	jsonData, err := json.Marshal(payload)
	if err != nil {
		return 0, nil, fmt.Errorf("marshal backtest payload: %v", err)
	}
	url := fmt.Sprintf("%s/backtest/run", s.config.PythonService.BaseURL)
	client := &http.Client{Timeout: time.Duration(s.config.PythonService.Timeout) * time.Second}
	resp, err := client.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return 0, nil, fmt.Errorf("call python backtest: %v", err)
	}
	defer resp.Body.Close()
	var body map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		return resp.StatusCode, nil, fmt.Errorf("decode python backtest response: %v", err)
	}
	return resp.StatusCode, body, nil
}

// 保存TimesFM最佳分位预测结果到PG（UPSERT by unique_key）
func (s *WatchlistService) SaveTimesfmBest(req *models.SaveTimesfmBestRequest) error {
	// 解析日期字符串为DATE由SQL处理
	metricsJSON, err := json.Marshal(req.BestMetrics)
	if err != nil {
		return fmt.Errorf("failed to marshal best_metrics: %v", err)
	}

	// 确定是否公开：从请求取值；若未提供，默认公开(1)
	isPublic := 1
	if req.IsPublic != nil {
		isPublic = *req.IsPublic
	}

	_, err = s.db.Conn.Exec(`
        INSERT INTO timesfm_best_predictions (
            unique_key, symbol, timesfm_version, best_prediction_item, best_metrics,
            is_public,
            train_start_date, train_end_date,
            test_start_date, test_end_date,
            val_start_date, val_end_date,
            context_len, horizon_len
        ) VALUES (
            $1, $2, $3, $4, $5::jsonb,
            $6,
            $7::date, $8::date,
            $9::date, $10::date,
            $11::date, $12::date,
            $13, $14
        )
        ON CONFLICT (unique_key) DO UPDATE SET
            best_prediction_item = EXCLUDED.best_prediction_item,
            best_metrics = EXCLUDED.best_metrics,
            is_public = EXCLUDED.is_public,
            train_start_date = EXCLUDED.train_start_date,
            train_end_date = EXCLUDED.train_end_date,
            test_start_date = EXCLUDED.test_start_date,
            test_end_date = EXCLUDED.test_end_date,
            val_start_date = EXCLUDED.val_start_date,
            val_end_date = EXCLUDED.val_end_date,
            context_len = EXCLUDED.context_len,
            horizon_len = EXCLUDED.horizon_len,
            updated_at = CURRENT_TIMESTAMP
    `,
		req.UniqueKey, req.Symbol, req.TimesfmVersion, req.BestPredictionItem, string(metricsJSON),
		isPublic,
		req.TrainStartDate, req.TrainEndDate,
		req.TestStartDate, req.TestEndDate,
		req.ValStartDate, req.ValEndDate,
		req.ContextLen, req.HorizonLen,
	)

	if err != nil {
		return fmt.Errorf("failed to upsert timesfm_best_predictions: %v", err)
	}
	return nil
}

// 按 unique_key 查询单条 TimesFM 最佳分位预测记录
func (s *WatchlistService) GetTimesfmBestByUniqueKey(uniqueKey string) (*models.TimesfmBestPrediction, error) {
	row := s.db.Conn.QueryRow(`
        SELECT 
            id, unique_key, symbol, timesfm_version, best_prediction_item, best_metrics,
            is_public,
            train_start_date, train_end_date,
            test_start_date, test_end_date,
            val_start_date, val_end_date,
            context_len, horizon_len,
            created_at, updated_at
        FROM timesfm_best_predictions
        WHERE unique_key = $1
        LIMIT 1
    `, uniqueKey)

	var item models.TimesfmBestPrediction
	err := row.Scan(
		&item.ID, &item.UniqueKey, &item.Symbol, &item.TimesfmVersion, &item.BestPredictionItem, &item.BestMetrics,
		&item.IsPublic,
		&item.TrainStartDate, &item.TrainEndDate,
		&item.TestStartDate, &item.TestEndDate,
		&item.ValStartDate, &item.ValEndDate,
		&item.ContextLen, &item.HorizonLen,
		&item.CreatedAt, &item.UpdatedAt,
	)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, sql.ErrNoRows
		}
		return nil, fmt.Errorf("failed to get timesfm_best_predictions by unique_key: %v", err)
	}

	return &item, nil
}

// 按 unique_key 查询单条 TimesFM 回测结果
func (s *WatchlistService) GetTimesfmBacktestByUniqueKey(uniqueKey string) (map[string]interface{}, error) {
	row := s.db.Conn.QueryRow(`
        SELECT 
            unique_key, symbol, timesfm_version, context_len, horizon_len,
            used_quantile, buy_threshold_pct, sell_threshold_pct, trade_fee_rate, total_fees_paid, actual_total_return_pct,
            benchmark_return_pct, benchmark_annualized_return_pct, period_days,
            validation_start_date, validation_end_date, validation_benchmark_return_pct, validation_benchmark_annualized_return_pct, validation_period_days,
            position_control, predicted_change_stats, per_chunk_signals,
            equity_curve_values, equity_curve_pct, equity_curve_pct_gross, curve_dates, actual_end_prices, trades
        FROM timesfm_backtests
        WHERE unique_key = $1
        LIMIT 1
    `, uniqueKey)

	var (
		uniqueKeyOut, symbol, timesfmVersion                                                 string
		contextLen, horizonLen, periodDays, validationPeriodDays                             int
		usedQuantile                                                                         string
		buyThresholdPct, sellThresholdPct, tradeFeeRate, totalFeesPaid, actualTotalReturnPct float64
		benchmarkReturnPct, benchmarkAnnualizedReturnPct                                     float64
		validationStartDate, validationEndDate                                               sql.NullTime
		validationBenchmarkReturnPct, validationBenchmarkAnnualizedReturnPct                 float64
		positionControl, predictedChangeStats, perChunkSignals                               []byte
		equityCurveValues, equityCurvePct, equityCurvePctGross                               []byte
		curveDates, actualEndPrices, trades                                                  []byte
	)

	err := row.Scan(
		&uniqueKeyOut, &symbol, &timesfmVersion, &contextLen, &horizonLen,
		&usedQuantile, &buyThresholdPct, &sellThresholdPct, &tradeFeeRate, &totalFeesPaid, &actualTotalReturnPct,
		&benchmarkReturnPct, &benchmarkAnnualizedReturnPct, &periodDays,
		&validationStartDate, &validationEndDate, &validationBenchmarkReturnPct, &validationBenchmarkAnnualizedReturnPct, &validationPeriodDays,
		&positionControl, &predictedChangeStats, &perChunkSignals,
		&equityCurveValues, &equityCurvePct, &equityCurvePctGross, &curveDates, &actualEndPrices, &trades,
	)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, sql.ErrNoRows
		}
		return nil, fmt.Errorf("failed to get timesfm_backtests by unique_key: %v", err)
	}

	out := map[string]interface{}{
		"unique_key":                      uniqueKeyOut,
		"symbol":                          symbol,
		"timesfm_version":                 timesfmVersion,
		"context_len":                     contextLen,
		"horizon_len":                     horizonLen,
		"used_quantile":                   usedQuantile,
		"buy_threshold_pct":               buyThresholdPct,
		"sell_threshold_pct":              sellThresholdPct,
		"trade_fee_rate":                  tradeFeeRate,
		"total_fees_paid":                 totalFeesPaid,
		"actual_total_return_pct":         actualTotalReturnPct,
		"benchmark_return_pct":            benchmarkReturnPct,
		"benchmark_annualized_return_pct": benchmarkAnnualizedReturnPct,
		"period_days":                     periodDays,
		"validation_start_date": func() interface{} {
			if validationStartDate.Valid {
				return validationStartDate.Time.Format("2006-01-02")
			}
			return nil
		}(),
		"validation_end_date": func() interface{} {
			if validationEndDate.Valid {
				return validationEndDate.Time.Format("2006-01-02")
			}
			return nil
		}(),
		"validation_benchmark_return_pct":            validationBenchmarkReturnPct,
		"validation_benchmark_annualized_return_pct": validationBenchmarkAnnualizedReturnPct,
		"validation_period_days":                     validationPeriodDays,
		"position_control":                           positionControl,
		"predicted_change_stats":                     predictedChangeStats,
		"per_chunk_signals":                          perChunkSignals,
		"equity_curve_values":                        equityCurveValues,
		"equity_curve_pct":                           equityCurvePct,
		"equity_curve_pct_gross":                     equityCurvePctGross,
		"curve_dates":                                curveDates,
		"actual_end_prices":                          actualEndPrices,
		"trades":                                     trades,
	}
	return out, nil
}

// 按用户ID查询其所有TimesFM最佳分位预测列表
func (s *WatchlistService) ListTimesfmBestByUserID(userID int) ([]models.TimesfmBestPrediction, error) {
	rows, err := s.db.Conn.Query(`
        SELECT 
            id, unique_key, symbol, timesfm_version, best_prediction_item, best_metrics,
            is_public,
            train_start_date, train_end_date,
            test_start_date, test_end_date,
            val_start_date, val_end_date,
            context_len, horizon_len,
            created_at, updated_at
        FROM timesfm_best_predictions
        WHERE EXISTS (
            SELECT 1 FROM timesfm_best_validation_chunks vc
            WHERE vc.unique_key = timesfm_best_predictions.unique_key
              AND vc.user_id = $1
        )
        ORDER BY updated_at DESC
    `, userID)
	if err != nil {
		return nil, fmt.Errorf("failed to query timesfm_best_predictions by user_id: %v", err)
	}
	defer rows.Close()

	var results []models.TimesfmBestPrediction
	for rows.Next() {
		var item models.TimesfmBestPrediction
		if err := rows.Scan(
			&item.ID, &item.UniqueKey, &item.Symbol, &item.TimesfmVersion, &item.BestPredictionItem, &item.BestMetrics,
			&item.IsPublic,
			&item.TrainStartDate, &item.TrainEndDate,
			&item.TestStartDate, &item.TestEndDate,
			&item.ValStartDate, &item.ValEndDate,
			&item.ContextLen, &item.HorizonLen,
			&item.CreatedAt, &item.UpdatedAt,
		); err != nil {
			return nil, fmt.Errorf("failed to scan timesfm_best_predictions: %v", err)
		}
		results = append(results, item)
	}
	return results, nil
}

// 列出公开的 timesfm-best（is_public = 1），支持按 horizon_len 筛选
func (s *WatchlistService) ListPublicTimesfmBest(horizonLen int) ([]models.TimesfmBestPrediction, error) {
	query := `
        SELECT 
            id, unique_key, symbol, timesfm_version, best_prediction_item, best_metrics,
            is_public,
            train_start_date, train_end_date,
            test_start_date, test_end_date,
            val_start_date, val_end_date,
            context_len, horizon_len,
            created_at, updated_at, COALESCE(short_name, '') AS short_name
        FROM timesfm_best_predictions
        WHERE is_public = 1
    `
	var args []interface{}
	if horizonLen > 0 {
		query += ` AND horizon_len = $1`
		args = append(args, horizonLen)
	}
	query += ` ORDER BY updated_at DESC`

	rows, err := s.db.Conn.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to query public timesfm_best_predictions: %v", err)
	}
	defer rows.Close()

	var results []models.TimesfmBestPrediction
	for rows.Next() {
		var item models.TimesfmBestPrediction
		if err := rows.Scan(
			&item.ID, &item.UniqueKey, &item.Symbol, &item.TimesfmVersion, &item.BestPredictionItem, &item.BestMetrics,
			&item.IsPublic,
			&item.TrainStartDate, &item.TrainEndDate,
			&item.TestStartDate, &item.TestEndDate,
			&item.ValStartDate, &item.ValEndDate,
			&item.ContextLen, &item.HorizonLen,
			&item.CreatedAt, &item.UpdatedAt, &item.ShortName,
		); err != nil {
			return nil, fmt.Errorf("failed to scan public timesfm_best_predictions: %v", err)
		}
		results = append(results, item)
	}

	return results, nil
}

// 根据 unique_key 查询对应的验证集分块列表
func (s *WatchlistService) ListValidationChunksByUniqueKey(uniqueKey string) ([]models.SaveTimesfmValChunkRequest, error) {
	rows, err := s.db.Conn.Query(`
        SELECT 
            unique_key, chunk_index, start_date::text, end_date::text, symbol,
            predictions, actual_values, dates
        FROM timesfm_best_validation_chunks
        WHERE unique_key = $1
        ORDER BY chunk_index ASC
    `, uniqueKey)
	if err != nil {
		return nil, fmt.Errorf("failed to query validation chunks by unique_key: %v", err)
	}
	defer rows.Close()

	var chunks []models.SaveTimesfmValChunkRequest
	for rows.Next() {
		var req models.SaveTimesfmValChunkRequest
		var predsJSON, actualJSON, datesJSON []byte
		if err := rows.Scan(
			&req.UniqueKey, &req.ChunkIndex, &req.StartDate, &req.EndDate, &req.Symbol,
			&predsJSON, &actualJSON, &datesJSON,
		); err != nil {
			return nil, fmt.Errorf("failed to scan validation chunk: %v", err)
		}
		// 反序列化 JSONB 字段
		if err := json.Unmarshal(predsJSON, &req.Predictions); err != nil {
			return nil, fmt.Errorf("failed to unmarshal predictions: %v", err)
		}
		if err := json.Unmarshal(actualJSON, &req.Actual); err != nil {
			return nil, fmt.Errorf("failed to unmarshal actual_values: %v", err)
		}
		if err := json.Unmarshal(datesJSON, &req.Dates); err != nil {
			return nil, fmt.Errorf("failed to unmarshal dates: %v", err)
		}
		chunks = append(chunks, req)
	}
	return chunks, nil
}

func (s *WatchlistService) ListFuturePredictionsByUniqueKey(uniqueKey string) ([]string, []float64, float64, float64, float64, error) {
	row := s.db.Conn.QueryRow(`SELECT best_prediction_item FROM timesfm_best_predictions WHERE unique_key = $1 LIMIT 1`, uniqueKey)
	var bestItem string
	if err := row.Scan(&bestItem); err != nil {
		return nil, nil, 0, 0, 0, fmt.Errorf("failed to get best_prediction_item: %v", err)
	}

	rows, err := s.db.Conn.Query(`
        SELECT dates, predictions
        FROM timesfm_best_validation_chunks
        WHERE unique_key = $1 AND start_date >= CURRENT_DATE + INTERVAL '1 day'
        ORDER BY chunk_index ASC
    `, uniqueKey)
	if err != nil {
		return nil, nil, 0, 0, 0, fmt.Errorf("failed to query future validation chunks: %v", err)
	}
	defer rows.Close()

	var outDates []string
	var outPreds []float64
	var predictedLatest float64 = 0

	for rows.Next() {
		var datesJSON, predsJSON []byte
		if err := rows.Scan(&datesJSON, &predsJSON); err != nil {
			return nil, nil, 0, 0, 0, fmt.Errorf("failed to scan future chunk: %v", err)
		}
		var dates []string
		var preds map[string]interface{}
		if err := json.Unmarshal(datesJSON, &dates); err != nil {
			return nil, nil, 0, 0, 0, fmt.Errorf("failed to unmarshal dates: %v", err)
		}
		if err := json.Unmarshal(predsJSON, &preds); err != nil {
			return nil, nil, 0, 0, 0, fmt.Errorf("failed to unmarshal predictions: %v", err)
		}
		val, ok := preds[bestItem]
		if !ok {
			continue
		}
		arr, ok := val.([]interface{})
		if !ok {
			continue
		}
		maxLen := len(dates)
		if len(arr) < maxLen {
			maxLen = len(arr)
		}
		for i := 0; i < maxLen; i++ {
			var p float64
			switch v := arr[i].(type) {
			case float64:
				p = v
			case float32:
				p = float64(v)
			case int:
				p = float64(v)
			case int64:
				p = float64(v)
			case json.Number:
				if f, e := v.Float64(); e == nil {
					p = f
				} else {
					continue
				}
			default:
				continue
			}
			if p == 0 || math.IsNaN(p) || math.IsInf(p, 0) {
				continue
			}
			outDates = append(outDates, dates[i])
			outPreds = append(outPreds, p)
		}
	}

	// compute predicted latest price
	for i := len(outPreds) - 1; i >= 0; i-- {
		if outPreds[i] != 0 && !math.IsNaN(outPreds[i]) && !math.IsInf(outPreds[i], 0) {
			predictedLatest = outPreds[i]
			break
		}
	}

	// fetch latest actual price from chunks with start_date <= CURRENT_DATE
	var actualLatest float64 = 0
	pastRows, err := s.db.Conn.Query(`
        SELECT actual_values
        FROM timesfm_best_validation_chunks
        WHERE unique_key = $1 AND start_date <= CURRENT_DATE
        ORDER BY chunk_index ASC
    `, uniqueKey)
	if err == nil {
		defer pastRows.Close()
		for pastRows.Next() {
			var actualJSON []byte
			if err := pastRows.Scan(&actualJSON); err != nil {
				continue
			}
			var actuals []float64
			// actual_values stored as JSON array of numbers
			if err := json.Unmarshal(actualJSON, &actuals); err != nil {
				continue
			}
			for i := len(actuals) - 1; i >= 0; i-- {
				a := actuals[i]
				if a != 0 && !math.IsNaN(a) && !math.IsInf(a, 0) {
					actualLatest = a
					break
				}
			}
		}
	}

	// compute change percent between predicted latest vs latest actual
	var changePercent float64 = 0
	if actualLatest > 0 && predictedLatest > 0 {
		changePercent = (predictedLatest - actualLatest) / actualLatest * 100
	}

	return outDates, outPreds, predictedLatest, actualLatest, changePercent, nil
}

// 保存验证集分块的预测与实际值（UPSERT by unique_key+chunk_index）
func (s *WatchlistService) SaveTimesfmValChunk(req *models.SaveTimesfmValChunkRequest) error {
	predsJSON, err := json.Marshal(req.Predictions)
	if err != nil {
		return fmt.Errorf("failed to marshal predictions: %v", err)
	}
	actualJSON, err := json.Marshal(req.Actual)
	if err != nil {
		return fmt.Errorf("failed to marshal actual_values: %v", err)
	}
	datesJSON, err := json.Marshal(req.Dates)
	if err != nil {
		return fmt.Errorf("failed to marshal dates: %v", err)
	}

	// 处理可选的 user_id 指针
	var uidArg interface{}
	if req.UserID != nil {
		uidArg = *req.UserID
	} else {
		uidArg = nil
	}

	_, err = s.db.Conn.Exec(`
        INSERT INTO timesfm_best_validation_chunks (
            unique_key, chunk_index, user_id, symbol, start_date, end_date, predictions, actual_values, dates
        ) VALUES (
            $1, $2, $3, $4, $5::date, $6::date, $7::jsonb, $8::jsonb, $9::jsonb
        )
        ON CONFLICT (unique_key, chunk_index) DO UPDATE SET
            start_date = EXCLUDED.start_date,
            end_date = EXCLUDED.end_date,
            predictions = EXCLUDED.predictions,
            actual_values = EXCLUDED.actual_values,
            dates = EXCLUDED.dates,
            updated_at = CURRENT_TIMESTAMP
    `,
		req.UniqueKey, req.ChunkIndex, uidArg, req.Symbol, req.StartDate, req.EndDate,
		string(predsJSON), string(actualJSON), string(datesJSON),
	)
	if err != nil {
		return fmt.Errorf("failed to upsert timesfm_best_validation_chunks: %v", err)
	}
	return nil
}

// 保存 TimesFM 回测结果到 PG（UPSERT by unique_key）
func (s *WatchlistService) SaveTimesfmBacktest(req *models.SaveTimesfmBacktestRequest) error {
	posJSON, err := json.Marshal(req.PositionControl)
	if err != nil {
		return fmt.Errorf("failed to marshal position_control: %v", err)
	}
	statsJSON, err := json.Marshal(req.PredictedChangeStats)
	if err != nil {
		return fmt.Errorf("failed to marshal predicted_change_stats: %v", err)
	}
	signalsJSON, err := json.Marshal(req.PerChunkSignals)
	if err != nil {
		return fmt.Errorf("failed to marshal per_chunk_signals: %v", err)
	}
	eqValsJSON, err := json.Marshal(req.EquityCurveValues)
	if err != nil {
		return fmt.Errorf("failed to marshal equity_curve_values: %v", err)
	}
	eqPctJSON, err := json.Marshal(req.EquityCurvePct)
	if err != nil {
		return fmt.Errorf("failed to marshal equity_curve_pct: %v", err)
	}
	eqPctGrossJSON, err := json.Marshal(req.EquityCurvePctGross)
	if err != nil {
		return fmt.Errorf("failed to marshal equity_curve_pct_gross: %v", err)
	}
	curveDatesJSON, err := json.Marshal(req.CurveDates)
	if err != nil {
		return fmt.Errorf("failed to marshal curve_dates: %v", err)
	}
	actualEndJSON, err := json.Marshal(req.ActualEndPrices)
	if err != nil {
		return fmt.Errorf("failed to marshal actual_end_prices: %v", err)
	}
	tradesJSON, err := json.Marshal(req.Trades)
	if err != nil {
		return fmt.Errorf("failed to marshal trades: %v", err)
	}

	var uidArg interface{}
	if req.UserID != nil {
		uidArg = *req.UserID
	} else {
		uidArg = nil
	}
	var spIDArg interface{}
	if req.StrategyParamsID != nil {
		spIDArg = *req.StrategyParamsID
	} else {
		var spID int
		if req.UserID != nil {
			row := s.db.Conn.QueryRow(`SELECT id FROM timesfm_strategy_params WHERE unique_key = $1 AND user_id = $2 LIMIT 1`, req.UniqueKey, *req.UserID)
			if err := row.Scan(&spID); err == nil {
				spIDArg = spID
			} else {
				spIDArg = nil
			}
		} else {
			row := s.db.Conn.QueryRow(`SELECT id FROM timesfm_strategy_params WHERE unique_key = $1 LIMIT 1`, req.UniqueKey)
			if err := row.Scan(&spID); err == nil {
				spIDArg = spID
			} else {
				spIDArg = nil
			}
		}
	}

	_, err = s.db.Conn.Exec(`
        INSERT INTO timesfm_backtests (
            unique_key, user_id, strategy_params_id, symbol, timesfm_version, context_len, horizon_len,
            used_quantile, buy_threshold_pct, sell_threshold_pct, trade_fee_rate, total_fees_paid, actual_total_return_pct,
            benchmark_return_pct, benchmark_annualized_return_pct, period_days,
            validation_start_date, validation_end_date, validation_benchmark_return_pct, validation_benchmark_annualized_return_pct, validation_period_days,
            position_control, predicted_change_stats, per_chunk_signals,
            equity_curve_values, equity_curve_pct, equity_curve_pct_gross, curve_dates, actual_end_prices, trades
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7,
            $8, $9, $10, $11, $12, $13,
            $14, $15, $16,
            $17::date, $18::date, $19, $20, $21,
            $22::jsonb, $23::jsonb, $24::jsonb,
            $25::jsonb, $26::jsonb, $27::jsonb, $28::jsonb, $29::jsonb, $30::jsonb
        )
        ON CONFLICT (unique_key) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            strategy_params_id = EXCLUDED.strategy_params_id,
            symbol = EXCLUDED.symbol,
            timesfm_version = EXCLUDED.timesfm_version,
            context_len = EXCLUDED.context_len,
            horizon_len = EXCLUDED.horizon_len,
            used_quantile = EXCLUDED.used_quantile,
            buy_threshold_pct = EXCLUDED.buy_threshold_pct,
            sell_threshold_pct = EXCLUDED.sell_threshold_pct,
            trade_fee_rate = EXCLUDED.trade_fee_rate,
            total_fees_paid = EXCLUDED.total_fees_paid,
            actual_total_return_pct = EXCLUDED.actual_total_return_pct,
            benchmark_return_pct = EXCLUDED.benchmark_return_pct,
            benchmark_annualized_return_pct = EXCLUDED.benchmark_annualized_return_pct,
            period_days = EXCLUDED.period_days,
            validation_start_date = EXCLUDED.validation_start_date,
            validation_end_date = EXCLUDED.validation_end_date,
            validation_benchmark_return_pct = EXCLUDED.validation_benchmark_return_pct,
            validation_benchmark_annualized_return_pct = EXCLUDED.validation_benchmark_annualized_return_pct,
            validation_period_days = EXCLUDED.validation_period_days,
            position_control = EXCLUDED.position_control,
            predicted_change_stats = EXCLUDED.predicted_change_stats,
            per_chunk_signals = EXCLUDED.per_chunk_signals,
            equity_curve_values = EXCLUDED.equity_curve_values,
            equity_curve_pct = EXCLUDED.equity_curve_pct,
            equity_curve_pct_gross = EXCLUDED.equity_curve_pct_gross,
            curve_dates = EXCLUDED.curve_dates,
            actual_end_prices = EXCLUDED.actual_end_prices,
            trades = EXCLUDED.trades,
            updated_at = CURRENT_TIMESTAMP
        `,
		req.UniqueKey, uidArg, spIDArg, req.Symbol, req.TimesfmVersion, req.ContextLen, req.HorizonLen,
		req.UsedQuantile, req.BuyThresholdPct, req.SellThresholdPct, req.TradeFeeRate, req.TotalFeesPaid, req.ActualTotalReturnPct,
		req.BenchmarkReturnPct, req.BenchmarkAnnualizedReturnPct, req.PeriodDays,
		req.ValidationStartDate, req.ValidationEndDate, req.ValidationBenchmarkReturnPct, req.ValidationBenchmarkAnnualizedReturnPct, req.ValidationPeriodDays,
		string(posJSON), string(statsJSON), string(signalsJSON),
		string(eqValsJSON), string(eqPctJSON), string(eqPctGrossJSON), string(curveDatesJSON), string(actualEndJSON), string(tradesJSON),
	)
	if err != nil {
		return fmt.Errorf("failed to upsert timesfm_backtests: %v", err)
	}
	return nil
}

func (s *WatchlistService) SaveStrategyParams(req *models.SaveStrategyParamsRequest) error {
	var uidArg interface{}
	if req.UserID != nil {
		uidArg = *req.UserID
	} else {
		uidArg = nil
	}
	_, err := s.db.Conn.Exec(`
        INSERT INTO timesfm_strategy_params (
            unique_key, user_id, name,
            buy_threshold_pct, sell_threshold_pct, initial_cash,
            enable_rebalance, max_position_pct, min_position_pct,
            slope_position_per_pct, rebalance_tolerance_pct,
            trade_fee_rate, take_profit_threshold_pct, take_profit_sell_frac
        ) VALUES (
            $1, $2, $3,
            $4, $5, $6,
            $7, $8, $9,
            $10, $11,
            $12, $13, $14
        )
        ON CONFLICT (unique_key) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            name = EXCLUDED.name,
            buy_threshold_pct = EXCLUDED.buy_threshold_pct,
            sell_threshold_pct = EXCLUDED.sell_threshold_pct,
            initial_cash = EXCLUDED.initial_cash,
            enable_rebalance = EXCLUDED.enable_rebalance,
            max_position_pct = EXCLUDED.max_position_pct,
            min_position_pct = EXCLUDED.min_position_pct,
            slope_position_per_pct = EXCLUDED.slope_position_per_pct,
            rebalance_tolerance_pct = EXCLUDED.rebalance_tolerance_pct,
            trade_fee_rate = EXCLUDED.trade_fee_rate,
            take_profit_threshold_pct = EXCLUDED.take_profit_threshold_pct,
            take_profit_sell_frac = EXCLUDED.take_profit_sell_frac,
            updated_at = CURRENT_TIMESTAMP
    `,
		req.UniqueKey, uidArg, req.Name,
		req.BuyThresholdPct, req.SellThresholdPct, req.InitialCash,
		req.EnableRebalance, req.MaxPositionPct, req.MinPositionPct,
		req.SlopePositionPerPct, req.RebalanceTolerancePct,
		req.TradeFeeRate, req.TakeProfitThresholdPct, req.TakeProfitSellFrac,
	)
	if err != nil {
		return fmt.Errorf("failed to upsert timesfm_strategy_params: %v", err)
	}
	return nil
}

func (s *WatchlistService) GetStrategyParamsByUniqueKey(uniqueKey string) (*models.StrategyParams, error) {
	row := s.db.Conn.QueryRow(`
        SELECT unique_key, user_id, name, is_public,
               buy_threshold_pct, sell_threshold_pct, initial_cash,
               enable_rebalance, max_position_pct, min_position_pct,
               slope_position_per_pct, rebalance_tolerance_pct,
               trade_fee_rate, take_profit_threshold_pct, take_profit_sell_frac
        FROM timesfm_strategy_params
        WHERE unique_key = $1
        LIMIT 1
    `, uniqueKey)
	var item models.StrategyParams
	var uid sql.NullInt64
	err := row.Scan(
		&item.UniqueKey, &uid, &item.Name, &item.IsPublic,
		&item.BuyThresholdPct, &item.SellThresholdPct, &item.InitialCash,
		&item.EnableRebalance, &item.MaxPositionPct, &item.MinPositionPct,
		&item.SlopePositionPerPct, &item.RebalanceTolerancePct,
		&item.TradeFeeRate, &item.TakeProfitThresholdPct, &item.TakeProfitSellFrac,
	)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, sql.ErrNoRows
		}
		return nil, fmt.Errorf("failed to query strategy params by unique_key: %v", err)
	}
	if uid.Valid {
		v := int(uid.Int64)
		item.UserID = &v
	} else {
		item.UserID = nil
	}
	return &item, nil
}

// 获取用户的所有策略（包括系统预设策略）
func (s *WatchlistService) GetUserStrategies(userID int) ([]models.StrategyParams, error) {
	rows, err := s.db.Conn.Query(`
        SELECT unique_key, user_id, name, is_public,
               buy_threshold_pct, sell_threshold_pct, initial_cash,
               enable_rebalance, max_position_pct, min_position_pct,
               slope_position_per_pct, rebalance_tolerance_pct,
               trade_fee_rate, take_profit_threshold_pct, take_profit_sell_frac
        FROM timesfm_strategy_params
        WHERE user_id = $1 OR is_public = 1
        ORDER BY is_public DESC, updated_at DESC
    `, userID)
	if err != nil {
		return nil, fmt.Errorf("failed to query user strategies: %v", err)
	}
	defer rows.Close()

	var results []models.StrategyParams
	for rows.Next() {
		var item models.StrategyParams
		var uid sql.NullInt64
		err := rows.Scan(
			&item.UniqueKey, &uid, &item.Name, &item.IsPublic,
			&item.BuyThresholdPct, &item.SellThresholdPct, &item.InitialCash,
			&item.EnableRebalance, &item.MaxPositionPct, &item.MinPositionPct,
			&item.SlopePositionPerPct, &item.RebalanceTolerancePct,
			&item.TradeFeeRate, &item.TakeProfitThresholdPct, &item.TakeProfitSellFrac,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan strategy params: %v", err)
		}
		if uid.Valid {
			v := int(uid.Int64)
			item.UserID = &v
		} else {
			item.UserID = nil
		}
		results = append(results, item)
	}
	return results, nil
}
