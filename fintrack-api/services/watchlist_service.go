package services

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
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

func (s *WatchlistService) AddToWatchlist(userID int, req *models.AddToWatchlistRequest) error {
	// Directly add symbol to watchlist - no need for stocks table
	_, err := s.db.Conn.Exec(`
		INSERT INTO user_watchlist (user_id, symbol, notes) 
		VALUES ($1, $2, $3)
	`, userID, req.Symbol, req.Notes)

	if err != nil {
		return fmt.Errorf("failed to add to watchlist: %v", err)
	}

	return nil
}

func (s *WatchlistService) GetWatchlist(userID int) ([]models.WatchlistItem, error) {
	rows, err := s.db.Conn.Query(`
		SELECT 
			uw.id, uw.symbol, uw.added_at, uw.notes,
			COALESCE(tbp.unique_key, ''),
			COALESCE(tbp.timesfm_version, '')
		FROM user_watchlist uw
		LEFT JOIN LATERAL (
			SELECT unique_key, timesfm_version
			FROM timesfm_best_predictions
			WHERE symbol = uw.symbol
			ORDER BY created_at DESC
			LIMIT 1
		) tbp ON true
		WHERE uw.user_id = $1
		ORDER BY uw.added_at DESC
	`, userID)

	if err != nil {
		return nil, fmt.Errorf("failed to get watchlist: %v", err)
	}
	defer rows.Close()

	var items []models.WatchlistItem
	for rows.Next() {
		var item models.WatchlistItem
		var uniqueKey, version string

		err := rows.Scan(
			&item.ID, &item.Stock.Symbol, &item.AddedAt, &item.Notes,
			&uniqueKey, &version,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan watchlist item: %v", err)
		}
		
		// Assuming WatchlistItem has a field for uniqueKey or we put it in notes/stock struct
		// But stock struct is shared. Let's add UniqueKey to WatchlistItem in models first.
		// For now, I'll add it to the WatchlistItem struct in next step.
		// Wait, I cannot modify models in this tool call if I don't have the file open.
		// I will use a temporary field or check if I can extend the model.
		// Let's modify models/stock.go first to add UniqueKey to WatchlistItem.
		
		// Wait, I can't modify two files in one tool call unless I use shell or multiple calls.
		// I will revert this mental step and modify models/stock.go first.
		// But I'm already in edit_file_fast_apply for watchlist_service.go.
		// I will just retrieve it but I need a place to store it.
		// I'll just assume I will add it to models.WatchlistItem.
		
		item.UniqueKey = uniqueKey
		items = append(items, item)
	}

	return items, nil
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

// 列出公开的 timesfm-best（is_public = 1）
func (s *WatchlistService) ListPublicTimesfmBest() ([]models.TimesfmBestPrediction, error) {
	rows, err := s.db.Conn.Query(`
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
        ORDER BY updated_at DESC
    `)
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

	_, err = s.db.Conn.Exec(`
        INSERT INTO timesfm_backtests (
            unique_key, user_id, symbol, timesfm_version, context_len, horizon_len,
            used_quantile, buy_threshold_pct, sell_threshold_pct, trade_fee_rate, total_fees_paid, actual_total_return_pct,
            benchmark_return_pct, benchmark_annualized_return_pct, period_days,
            validation_start_date, validation_end_date, validation_benchmark_return_pct, validation_benchmark_annualized_return_pct, validation_period_days,
            position_control, predicted_change_stats, per_chunk_signals,
            equity_curve_values, equity_curve_pct, equity_curve_pct_gross, curve_dates, actual_end_prices, trades
        ) VALUES (
            $1, $2, $3, $4, $5, $6,
            $7, $8, $9, $10, $11, $12,
            $13, $14, $15,
            $16::date, $17::date, $18, $19, $20,
            $21::jsonb, $22::jsonb, $23::jsonb,
            $24::jsonb, $25::jsonb, $26::jsonb, $27::jsonb, $28::jsonb, $29::jsonb
        )
        ON CONFLICT (unique_key) DO UPDATE SET
            user_id = EXCLUDED.user_id,
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
		req.UniqueKey, uidArg, req.Symbol, req.TimesfmVersion, req.ContextLen, req.HorizonLen,
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
            unique_key, user_id,
            buy_threshold_pct, sell_threshold_pct, initial_cash,
            enable_rebalance, max_position_pct, min_position_pct,
            slope_position_per_pct, rebalance_tolerance_pct,
            trade_fee_rate, take_profit_threshold_pct, take_profit_sell_frac
        ) VALUES (
            $1, $2,
            $3, $4, $5,
            $6, $7, $8,
            $9, $10,
            $11, $12, $13
        )
        ON CONFLICT (unique_key) DO UPDATE SET
            user_id = EXCLUDED.user_id,
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
        req.UniqueKey, uidArg,
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
        SELECT unique_key, user_id,
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
        &item.UniqueKey, &uid,
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
