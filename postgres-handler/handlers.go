package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

func (h *DatabaseHandler) batchInsertTimesfmForecastHandler(c *gin.Context) {
	var req []struct {
		Symbol          string  `json:"symbol"`
		Ds              string  `json:"ds"`
		Tsf             float64 `json:"tsf"`
		Tsf01           float64 `json:"tsf_01"`
		Tsf02           float64 `json:"tsf_02"`
		Tsf03           float64 `json:"tsf_03"`
		Tsf04           float64 `json:"tsf_04"`
		Tsf05           float64 `json:"tsf_05"`
		Tsf06           float64 `json:"tsf_06"`
		Tsf07           float64 `json:"tsf_07"`
		Tsf08           float64 `json:"tsf_08"`
		Tsf09           float64 `json:"tsf_09"`
		ChunkIndex      int     `json:"chunk_index"`
		BestQuantile    string  `json:"best_quantile"`
		BestQuantilePct string  `json:"best_quantile_pct"`
		BestPredPct     float64 `json:"best_pred_pct"`
		ActualPct       float64 `json:"actual_pct"`
		DiffPct         float64 `json:"diff_pct"`
		MSE             float64 `json:"mse"`
		MAE             float64 `json:"mae"`
		CombinedScore   float64 `json:"combined_score"`
		UserID          int     `json:"user_id"`
		Version         float64 `json:"version"`
		HorizonLen      int     `json:"horizon_len"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
		return
	}
	if len(req) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "empty list"})
		return
	}
	list := make([]TimesfmForecast, 0, len(req))
	for i, v := range req {
		if v.Symbol == "" || v.Ds == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("item %d missing symbol or ds", i)})
			return
		}
		var t time.Time
		var err error
		layouts := []string{"2006-01-02 15:04:05", time.RFC3339, "2006-01-02"}
		for _, layout := range layouts {
			t, err = time.Parse(layout, v.Ds)
			if err == nil {
				break
			}
		}
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("invalid ds format: %s", v.Ds)})
			return
		}
		list = append(list, TimesfmForecast{
			Symbol: v.Symbol, Ds: t, Tsf: v.Tsf, Tsf01: v.Tsf01, Tsf02: v.Tsf02, Tsf03: v.Tsf03, Tsf04: v.Tsf04, Tsf05: v.Tsf05, Tsf06: v.Tsf06, Tsf07: v.Tsf07, Tsf08: v.Tsf08, Tsf09: v.Tsf09,
			ChunkIndex: v.ChunkIndex, BestQuantile: v.BestQuantile, BestQuantilePct: v.BestQuantilePct, BestPredPct: v.BestPredPct, ActualPct: v.ActualPct, DiffPct: v.DiffPct, MSE: v.MSE, MAE: v.MAE, CombinedScore: v.CombinedScore,
			UserID: v.UserID, Version: v.Version, HorizonLen: v.HorizonLen,
		})
	}
	if err := h.BatchInsertTimesfmForecast(list); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success"})
}

func (h *DatabaseHandler) getTimesfmForecastBySymbolVersionHorizon(c *gin.Context) {
	var req struct {
		Symbol     string  `json:"symbol"`
		Version    float64 `json:"version"`
		HorizonLen int     `json:"horizon_len"`
		Limit      *int    `json:"limit"`
		Offset     *int    `json:"offset"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
		return
	}
	if strings.TrimSpace(req.Symbol) == "" || req.HorizonLen <= 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "symbol and horizon_len are required"})
		return
	}
	limit := 200
	offset := 0
	if req.Limit != nil && *req.Limit > 0 {
		limit = *req.Limit
	}
	if req.Offset != nil && *req.Offset >= 0 {
		offset = *req.Offset
	}
	rows, err := h.db.Raw(`
        SELECT symbol, ds, tsf, tsf_01, tsf_02, tsf_03, tsf_04, tsf_05, tsf_06, tsf_07, tsf_08, tsf_09,
               chunk_index, best_quantile, best_quantile_pct, best_pred_pct, actual_pct, diff_pct, mse, mae, combined_score,
               version, horizon_len
        FROM timesfm_forecast
        WHERE symbol = $1 AND version = $2 AND horizon_len = $3
        ORDER BY ds ASC
        LIMIT $4 OFFSET $5`, req.Symbol, req.Version, req.HorizonLen, limit, offset).Rows()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	defer rows.Close()
	list := []TimesfmForecast{}
	for rows.Next() {
		var v TimesfmForecast
		if err := rows.Scan(
			&v.Symbol, &v.Ds, &v.Tsf, &v.Tsf01, &v.Tsf02, &v.Tsf03, &v.Tsf04, &v.Tsf05, &v.Tsf06, &v.Tsf07, &v.Tsf08, &v.Tsf09,
			&v.ChunkIndex, &v.BestQuantile, &v.BestQuantilePct, &v.BestPredPct, &v.ActualPct, &v.DiffPct, &v.MSE, &v.MAE, &v.CombinedScore,
			&v.Version, &v.HorizonLen,
		); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		list = append(list, v)
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: list})
}

func (h *DatabaseHandler) saveTimesfmBestHandler(c *gin.Context) {
	var req struct {
		UniqueKey          string                 `json:"unique_key"`
		Symbol             string                 `json:"symbol"`
		TimesfmVersion     string                 `json:"timesfm_version"`
		BestPredictionItem string                 `json:"best_prediction_item"`
		BestMetrics        map[string]interface{} `json:"best_metrics"`
		IsPublic           *int                   `json:"is_public"`
		TrainStartDate     string                 `json:"train_start_date"`
		TrainEndDate       string                 `json:"train_end_date"`
		TestStartDate      string                 `json:"test_start_date"`
		TestEndDate        string                 `json:"test_end_date"`
		ValStartDate       string                 `json:"val_start_date"`
		ValEndDate         string                 `json:"val_end_date"`
		ContextLen         int                    `json:"context_len"`
		HorizonLen         int                    `json:"horizon_len"`
		ShortName          string                 `json:"short_name"`
		StockType          int                    `json:"stock_type"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		slog.Error("Error binding JSON: %v", err)
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
		return
	}
	if strings.TrimSpace(req.UniqueKey) == "" || strings.TrimSpace(req.Symbol) == "" || strings.TrimSpace(req.TimesfmVersion) == "" || strings.TrimSpace(req.BestPredictionItem) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "unique_key, symbol, timesfm_version, best_prediction_item are required"})
		return
	}
	metricsJSON, err := json.Marshal(req.BestMetrics)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "best_metrics must be JSON object"})
		return
	}
	isPublic := 0
	if req.IsPublic != nil {
		isPublic = *req.IsPublic
	}
	if strings.TrimSpace(req.ShortName) == "" {
		if req.StockType == 2 {
			// Try getting ETF data to fill ShortName. Use offset 0 to get the latest record.
			etfData, errEtf := h.GetEtfDaily(req.Symbol, 1, 0)
			slog.Info("GetEtfDaily", "symbol", req.Symbol, "data", etfData, "err", errEtf)
			if errEtf == nil {
				if len(etfData) > 0 {
					req.ShortName = etfData[0].Name
				}
			}
		}
		if req.StockType == 1 {
			code := strings.TrimLeft(req.Symbol, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
			stockData, errStock := h.GetAStockCommentDailyByCode(code, 1, 0)
			slog.Info("GetAStockCommentDailyByCode", "symbol", req.Symbol, "data", stockData, "err", errStock)
			if errStock == nil {
				if len(stockData) > 0 {
					req.ShortName = stockData[0].Name
				}
			}
		}
	}
	err = h.db.Exec(`
        INSERT INTO timesfm_best_predictions (
            unique_key, symbol, timesfm_version, best_prediction_item, best_metrics,
            is_public,
            train_start_date, train_end_date,
            test_start_date, test_end_date,
            val_start_date, val_end_date,
            context_len, horizon_len, short_name, stock_type
        ) VALUES (
            $1, $2, $3, $4, $5::jsonb,
            $6,
            $7::date, $8::date,
            $9::date, $10::date,
            $11::date, $12::date,
            $13, $14, $15, $16
        )
        ON CONFLICT (unique_key) DO UPDATE SET
            symbol = EXCLUDED.symbol,
            timesfm_version = EXCLUDED.timesfm_version,
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
            short_name = EXCLUDED.short_name,
			stock_type = EXCLUDED.stock_type,
            updated_at = CURRENT_TIMESTAMP`,
		req.UniqueKey, req.Symbol, req.TimesfmVersion, req.BestPredictionItem, string(metricsJSON),
		isPublic,
		req.TrainStartDate, req.TrainEndDate,
		req.TestStartDate, req.TestEndDate,
		req.ValStartDate, req.ValEndDate,
		req.ContextLen, req.HorizonLen, req.ShortName, req.StockType,
	).Error
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("failed to upsert timesfm_best_predictions: %v", err)})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: gin.H{"unique_key": req.UniqueKey}})
}

func (h *DatabaseHandler) saveTimesfmValChunkHandler(c *gin.Context) {
	var req struct {
		UniqueKey   string                 `json:"unique_key"`
		ChunkIndex  int                    `json:"chunk_index"`
		StartDate   string                 `json:"start_date"`
		EndDate     string                 `json:"end_date"`
		Symbol      string                 `json:"symbol"`
		UserID      *int                   `json:"user_id"`
		Predictions map[string]interface{} `json:"predictions"`
		Actual      []float64              `json:"actual_values"`
		Dates       []string               `json:"dates"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
		return
	}
	if strings.TrimSpace(req.UniqueKey) == "" || req.ChunkIndex < 0 || strings.TrimSpace(req.StartDate) == "" || strings.TrimSpace(req.EndDate) == "" || req.Predictions == nil || req.Actual == nil || req.Dates == nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "missing required fields"})
		return
	}
	predsJSON, err := json.Marshal(req.Predictions)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "predictions must be JSON object"})
		return
	}
	actualJSON, _ := json.Marshal(req.Actual)
	datesJSON, _ := json.Marshal(req.Dates)
	var uidArg interface{}
	if req.UserID != nil {
		uidArg = *req.UserID
	} else {
		uidArg = nil
	}
	err = h.db.Exec(`
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
            updated_at = CURRENT_TIMESTAMP`,
		req.UniqueKey, req.ChunkIndex, uidArg, req.Symbol, req.StartDate, req.EndDate, string(predsJSON), string(actualJSON), string(datesJSON),
	).Error
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("failed to upsert timesfm_best_validation_chunks: %v", err)})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success"})
}

func (h *DatabaseHandler) getTimesfmBestByUniqueKeyHandler(c *gin.Context) {
	uniqueKey := c.Query("unique_key")
	if strings.TrimSpace(uniqueKey) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "unique_key is required"})
		return
	}
	row := h.db.Raw(`
        SELECT id, unique_key, symbol, timesfm_version, best_prediction_item, best_metrics,
               is_public,
               train_start_date, train_end_date,
               test_start_date, test_end_date,
               val_start_date, val_end_date,
               context_len, horizon_len,
               created_at, updated_at
        FROM timesfm_best_predictions
        WHERE unique_key = $1
        LIMIT 1`, uniqueKey).Row()
	var item struct {
		ID                 int
		UniqueKey          string
		Symbol             string
		TimesfmVersion     string
		BestPredictionItem string
		BestMetrics        string
		IsPublic           int
		TrainStartDate     time.Time
		TrainEndDate       time.Time
		TestStartDate      time.Time
		TestEndDate        time.Time
		ValStartDate       time.Time
		ValEndDate         time.Time
		ContextLen         int
		HorizonLen         int
		CreatedAt          time.Time
		UpdatedAt          time.Time
	}
	if err := row.Scan(
		&item.ID, &item.UniqueKey, &item.Symbol, &item.TimesfmVersion, &item.BestPredictionItem, &item.BestMetrics,
		&item.IsPublic,
		&item.TrainStartDate, &item.TrainEndDate,
		&item.TestStartDate, &item.TestEndDate,
		&item.ValStartDate, &item.ValEndDate,
		&item.ContextLen, &item.HorizonLen,
		&item.CreatedAt, &item.UpdatedAt,
	); err != nil {
		if err == sql.ErrNoRows {
			c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: item})
}

// 获取指定 unique_key 的最新验证分块（按 chunk_index DESC 取一条）
func (h *DatabaseHandler) getLatestTimesfmValChunkHandler(c *gin.Context) {
    uniqueKey := c.Query("unique_key")
    if strings.TrimSpace(uniqueKey) == "" {
        c.JSON(http.StatusBadRequest, gin.H{"error": "unique_key is required"})
        return
    }

    row := h.db.Raw(`
        SELECT 
            unique_key, chunk_index, start_date::text, end_date::text, symbol,
            predictions, actual_values, dates
        FROM timesfm_best_validation_chunks
        WHERE unique_key = $1
        ORDER BY chunk_index DESC
        LIMIT 1`, uniqueKey).Row()

    var (
        uk         string
        chunkIndex int
        startDate  string
        endDate    string
        symbol     string
        predsJSON  []byte
        actualJSON []byte
        datesJSON  []byte
    )

    if err := row.Scan(&uk, &chunkIndex, &startDate, &endDate, &symbol, &predsJSON, &actualJSON, &datesJSON); err != nil {
        if err == sql.ErrNoRows {
            c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
            return
        }
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }

    var preds map[string]interface{}
    var actual []float64
    var dates []string
    if err := json.Unmarshal(predsJSON, &preds); err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to unmarshal predictions"})
        return
    }
    if err := json.Unmarshal(actualJSON, &actual); err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to unmarshal actual_values"})
        return
    }
    if err := json.Unmarshal(datesJSON, &dates); err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to unmarshal dates"})
        return
    }

    c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: gin.H{
        "unique_key":  uk,
        "chunk_index": chunkIndex,
        "start_date":  startDate,
        "end_date":    endDate,
        "symbol":      symbol,
        "predictions": preds,
        "actual_values": actual,
        "dates":         dates,
    }})
}

func (h *DatabaseHandler) saveTimesfmBacktestHandler(c *gin.Context) {
	var req struct {
		UniqueKey                              string                   `json:"unique_key"`
		Symbol                                 string                   `json:"symbol"`
		TimesfmVersion                         string                   `json:"timesfm_version"`
		ContextLen                             int                      `json:"context_len"`
		HorizonLen                             int                      `json:"horizon_len"`
		UserID                                 *int                     `json:"user_id"`
		UsedQuantile                           string                   `json:"used_quantile"`
		BuyThresholdPct                        float64                  `json:"buy_threshold_pct"`
		SellThresholdPct                       float64                  `json:"sell_threshold_pct"`
		TradeFeeRate                           float64                  `json:"trade_fee_rate"`
		TotalFeesPaid                          float64                  `json:"total_fees_paid"`
		ActualTotalReturnPct                   float64                  `json:"actual_total_return_pct"`
		BenchmarkReturnPct                     float64                  `json:"benchmark_return_pct"`
		BenchmarkAnnualizedReturnPct           float64                  `json:"benchmark_annualized_return_pct"`
		PeriodDays                             int                      `json:"period_days"`
		ValidationStartDate                    string                   `json:"validation_start_date"`
		ValidationEndDate                      string                   `json:"validation_end_date"`
		ValidationBenchmarkReturnPct           float64                  `json:"validation_benchmark_return_pct"`
		ValidationBenchmarkAnnualizedReturnPct float64                  `json:"validation_benchmark_annualized_return_pct"`
		ValidationPeriodDays                   int                      `json:"validation_period_days"`
		PositionControl                        map[string]interface{}   `json:"position_control"`
		PredictedChangeStats                   map[string]interface{}   `json:"predicted_change_stats"`
		PerChunkSignals                        map[string]interface{}   `json:"per_chunk_signals"`
		EquityCurveValues                      []float64                `json:"equity_curve_values"`
		EquityCurvePct                         []float64                `json:"equity_curve_pct"`
		EquityCurvePctGross                    []float64                `json:"equity_curve_pct_gross"`
		CurveDates                             []string                 `json:"curve_dates"`
		ActualEndPrices                        []float64                `json:"actual_end_prices"`
		Trades                                 []map[string]interface{} `json:"trades"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
		return
	}
	if strings.TrimSpace(req.UniqueKey) == "" || strings.TrimSpace(req.Symbol) == "" || strings.TrimSpace(req.TimesfmVersion) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "unique_key, symbol, timesfm_version are required"})
		return
	}
	posJSON, _ := json.Marshal(req.PositionControl)
	statsJSON, _ := json.Marshal(req.PredictedChangeStats)
	signalsJSON, _ := json.Marshal(req.PerChunkSignals)
	eqValsJSON, _ := json.Marshal(req.EquityCurveValues)
	eqPctJSON, _ := json.Marshal(req.EquityCurvePct)
	eqPctGrossJSON, _ := json.Marshal(req.EquityCurvePctGross)
	curveDatesJSON, _ := json.Marshal(req.CurveDates)
	actualEndJSON, _ := json.Marshal(req.ActualEndPrices)
	tradesJSON, _ := json.Marshal(req.Trades)
	var uidArg interface{}
	if req.UserID != nil {
		uidArg = *req.UserID
	} else {
		uidArg = nil
	}
	err := h.db.Exec(`
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
            updated_at = CURRENT_TIMESTAMP`,
		req.UniqueKey, uidArg, req.Symbol, req.TimesfmVersion, req.ContextLen, req.HorizonLen,
		req.UsedQuantile, req.BuyThresholdPct, req.SellThresholdPct, req.TradeFeeRate, req.TotalFeesPaid, req.ActualTotalReturnPct,
		req.BenchmarkReturnPct, req.BenchmarkAnnualizedReturnPct, req.PeriodDays,
		req.ValidationStartDate, req.ValidationEndDate, req.ValidationBenchmarkReturnPct, req.ValidationBenchmarkAnnualizedReturnPct, req.ValidationPeriodDays,
		string(posJSON), string(statsJSON), string(signalsJSON),
		string(eqValsJSON), string(eqPctJSON), string(eqPctGrossJSON), string(curveDatesJSON), string(actualEndJSON), string(tradesJSON),
	).Error
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("failed to upsert timesfm_backtests: %v", err)})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: gin.H{"unique_key": req.UniqueKey}})
}

func (h *DatabaseHandler) saveStrategyParamsHandler(c *gin.Context) {
	var req struct {
		UniqueKey              string  `json:"unique_key"`
		UserID                 *int    `json:"user_id"`
		BuyThresholdPct        float64 `json:"buy_threshold_pct"`
		SellThresholdPct       float64 `json:"sell_threshold_pct"`
		InitialCash            float64 `json:"initial_cash"`
		EnableRebalance        bool    `json:"enable_rebalance"`
		MaxPositionPct         float64 `json:"max_position_pct"`
		MinPositionPct         float64 `json:"min_position_pct"`
		SlopePositionPerPct    float64 `json:"slope_position_per_pct"`
		RebalanceTolerancePct  float64 `json:"rebalance_tolerance_pct"`
		TradeFeeRate           float64 `json:"trade_fee_rate"`
		TakeProfitThresholdPct float64 `json:"take_profit_threshold_pct"`
		TakeProfitSellFrac     float64 `json:"take_profit_sell_frac"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
		return
	}
	if strings.TrimSpace(req.UniqueKey) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "unique_key is required"})
		return
	}
	var uidArg interface{}
	if req.UserID != nil {
		uidArg = *req.UserID
	} else {
		uidArg = nil
	}
	err := h.db.Exec(`
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
            updated_at = CURRENT_TIMESTAMP`,
		req.UniqueKey, uidArg,
		req.BuyThresholdPct, req.SellThresholdPct, req.InitialCash,
		req.EnableRebalance, req.MaxPositionPct, req.MinPositionPct,
		req.SlopePositionPerPct, req.RebalanceTolerancePct,
		req.TradeFeeRate, req.TakeProfitThresholdPct, req.TakeProfitSellFrac,
	).Error
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("failed to upsert timesfm_strategy_params: %v", err)})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: gin.H{"unique_key": req.UniqueKey}})
}

func (h *DatabaseHandler) getStrategyParamsByUniqueKeyHandler(c *gin.Context) {
	uniqueKey := c.Query("unique_key")
	userId, err := strconv.Atoi(c.Query("user_id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "user_id must be an integer"})
		return
	}
	if strings.TrimSpace(uniqueKey) == "" || userId == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "unique_key and user_id are required"})
		return
	}
	row := h.db.Raw(`
        SELECT unique_key, user_id,
               buy_threshold_pct, sell_threshold_pct, initial_cash,
               enable_rebalance, max_position_pct, min_position_pct,
               slope_position_per_pct, rebalance_tolerance_pct,
               trade_fee_rate, take_profit_threshold_pct, take_profit_sell_frac,
               created_at, updated_at
        FROM timesfm_strategy_params
        WHERE unique_key = $1 AND user_id = $2
        LIMIT 1`, uniqueKey, userId).Row()
	var item StrategyParams
	var uid sql.NullInt64
	if err := row.Scan(
		&item.UniqueKey, &uid,
		&item.BuyThresholdPct, &item.SellThresholdPct, &item.InitialCash,
		&item.EnableRebalance, &item.MaxPositionPct, &item.MinPositionPct,
		&item.SlopePositionPerPct, &item.RebalanceTolerancePct,
		&item.TradeFeeRate, &item.TakeProfitThresholdPct, &item.TakeProfitSellFrac,
		&item.CreatedAt, &item.UpdatedAt,
	); err != nil {
		if err == sql.ErrNoRows {
			c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if uid.Valid {
		v := int(uid.Int64)
		item.UserID = &v
	} else {
		item.UserID = nil
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: item})
}

func (h *DatabaseHandler) getStrategyParamsByUserHandler(c *gin.Context) {
	uidStr := c.Query("user_id")
	if strings.TrimSpace(uidStr) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "user_id is required"})
		return
	}
	uid, err := strconv.Atoi(uidStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid user_id"})
		return
	}
	rows, err := h.db.Raw(`
        SELECT unique_key, user_id,
               buy_threshold_pct, sell_threshold_pct, initial_cash,
               enable_rebalance, max_position_pct, min_position_pct,
               slope_position_per_pct, rebalance_tolerance_pct,
               trade_fee_rate, take_profit_threshold_pct, take_profit_sell_frac,
               created_at, updated_at
        FROM timesfm_strategy_params
        WHERE user_id = $1
        ORDER BY updated_at DESC`, uid).Rows()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	defer rows.Close()
	list := []StrategyParams{}
	for rows.Next() {
		var item StrategyParams
		var uidN sql.NullInt64
		if err := rows.Scan(
			&item.UniqueKey, &uidN,
			&item.BuyThresholdPct, &item.SellThresholdPct, &item.InitialCash,
			&item.EnableRebalance, &item.MaxPositionPct, &item.MinPositionPct,
			&item.SlopePositionPerPct, &item.RebalanceTolerancePct,
			&item.TradeFeeRate, &item.TakeProfitThresholdPct, &item.TakeProfitSellFrac,
			&item.CreatedAt, &item.UpdatedAt,
		); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		if uidN.Valid {
			v := int(uidN.Int64)
			item.UserID = &v
		} else {
			item.UserID = nil
		}
		list = append(list, item)
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: list})
}

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
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success"})
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
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Batch insert successful"})
}

func (h *DatabaseHandler) getStockDataHandler(c *gin.Context) {
	symbol := c.Param("symbol")
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
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: data})
}

func (h *DatabaseHandler) getStockDataByDateRangeHandler(c *gin.Context) {
	symbol := c.Param("symbol")
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
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: data})
}

func (h *DatabaseHandler) insertEtfDailyHandler(c *gin.Context) {
	var req struct {
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
	data := EtfDailyData{Code: req.Code, TradingDate: tDate, Name: req.Name, LatestPrice: req.LatestPrice, ChangeAmount: req.ChangeAmount, ChangePercent: req.ChangePercent, Buy: req.Buy, Sell: req.Sell, PrevClose: req.PrevClose, Open: req.Open, High: req.High, Low: req.Low, Volume: req.Volume, Turnover: req.Turnover}
	if err := h.UpsertEtfDaily(&data); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "ETF daily upsert success"})
}

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
		dataList = append(dataList, EtfDailyData{Code: r.Code, TradingDate: tDate, Name: r.Name, LatestPrice: r.LatestPrice, ChangeAmount: r.ChangeAmount, ChangePercent: r.ChangePercent, Buy: r.Buy, Sell: r.Sell, PrevClose: r.PrevClose, Open: r.Open, High: r.High, Low: r.Low, Volume: r.Volume, Turnover: r.Turnover})
	}
	if err := h.BatchUpsertEtfDaily(dataList); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "ETF daily batch upsert success", Data: gin.H{"count": len(dataList)}})
}

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

func (h *DatabaseHandler) insertIndexInfoHandler(c *gin.Context) {
	var req struct {
		Code        string `json:"code"`
		DisplayName string `json:"display_name"`
		PublishDate string `json:"publish_date"`
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
	payload := IndexDailyData{Code: req.Code, TradingDate: tDate, Open: req.Open, Close: req.Close, High: req.High, Low: req.Low, Volume: req.Volume, Amount: req.Amount, ChangePercent: req.ChangePercent}
	if err := h.UpsertIndexDaily(&payload); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: gin.H{"affected": 1}})
}

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
		list = append(list, IndexDailyData{Code: v.Code, TradingDate: tDate, Open: v.Open, Close: v.Close, High: v.High, Low: v.Low, Volume: v.Volume, Amount: v.Amount, ChangePercent: v.ChangePercent})
	}
	if err := h.BatchUpsertIndexDaily(list); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: gin.H{"affected": len(list)}})
}

func (h *DatabaseHandler) batchInsertAStockCommentDailyHandler(c *gin.Context) {
	var req []struct {
		Code                     string  `json:"code"`
		TradingDate              string  `json:"trading_date"`
		Name                     string  `json:"name"`
		LatestPrice              float64 `json:"latest_price"`
		ChangePercent            float64 `json:"change_percent"`
		TurnoverRate             float64 `json:"turnover_rate"`
		PeRatio                  float64 `json:"pe_ratio"`
		MainCost                 float64 `json:"main_cost"`
		InstitutionParticipation float64 `json:"institution_participation"`
		CompositeScore           float64 `json:"composite_score"`
		Rise                     int64   `json:"rise"`
		CurrentRank              int64   `json:"current_rank"`
		AttentionIndex           float64 `json:"attention_index"`
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
		list = append(list, StockCommentDaily{Code: v.Code, TradingDate: tDate, Name: v.Name, LatestPrice: v.LatestPrice, ChangePercent: v.ChangePercent, TurnoverRate: v.TurnoverRate, PeRatio: v.PeRatio, MainCost: v.MainCost, InstitutionParticipation: v.InstitutionParticipation, CompositeScore: v.CompositeScore, Rise: v.Rise, CurrentRank: v.CurrentRank, AttentionIndex: v.AttentionIndex})
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
		StockType int `json:"stock_type"`
		Symbol    string `json:"symbol"`
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

func (h *DatabaseHandler) getAStockCommentDailyByCodeHandler (c *gin.Context) {
	code := c.Param("code")
	limit := 1
	offset := 0
	data, err := h.GetAStockCommentDailyByCode(code, limit, offset)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, ApiResponse{Code: 200, Message: "Success", Data: data})
}



func (h *DatabaseHandler) getIndexDailyHandler(c *gin.Context) {
	code := c.Param("code")
	var req struct {
		Limit  int `json:"limit"`
		Offset int `json:"offset"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
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

// saveLlmTokenUsageHandler saves a new LLM token usage record
func (h *DatabaseHandler) saveLlmTokenUsageHandler(c *gin.Context) {
	var usage LlmTokenUsage
	if err := c.ShouldBindJSON(&usage); err != nil {
		c.JSON(http.StatusBadRequest, ApiResponse{Code: 400, Message: fmt.Sprintf("Invalid request body: %v", err)})
		return
	}

	// Validate required fields
	if usage.UserID == 0 {
		c.JSON(http.StatusBadRequest, ApiResponse{Code: 400, Message: "user_id is required"})
		return
	}
	if usage.Provider == "" {
		c.JSON(http.StatusBadRequest, ApiResponse{Code: 400, Message: "provider is required"})
		return
	}
	if usage.Model == "" {
		c.JSON(http.StatusBadRequest, ApiResponse{Code: 400, Message: "model is required"})
		return
	}

	if err := h.SaveLlmTokenUsage(&usage); err != nil {
		slog.Error("Failed to save LLM token usage", "error", err)
		c.JSON(http.StatusInternalServerError, ApiResponse{Code: 500, Message: fmt.Sprintf("Failed to save token usage: %v", err)})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{Code: 0, Message: "success", Data: usage})
}

// getLlmTokenUsageByUserHandler retrieves LLM token usage records for a user
func (h *DatabaseHandler) getLlmTokenUsageByUserHandler(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := strconv.Atoi(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, ApiResponse{Code: 400, Message: "Invalid user_id"})
		return
	}

	// Parse query parameters
	limitStr := c.DefaultQuery("limit", "100")
	offsetStr := c.DefaultQuery("offset", "0")
	limit, _ := strconv.Atoi(limitStr)
	offset, _ := strconv.Atoi(offsetStr)

	var startDate, endDate *time.Time
	if startDateStr := c.Query("start_date"); startDateStr != "" {
		parsed, err := time.Parse(time.RFC3339, startDateStr)
		if err == nil {
			startDate = &parsed
		}
	}
	if endDateStr := c.Query("end_date"); endDateStr != "" {
		parsed, err := time.Parse(time.RFC3339, endDateStr)
		if err == nil {
			endDate = &parsed
		}
	}

	var provider, model *string
	if p := c.Query("provider"); p != "" {
		provider = &p
	}
	if m := c.Query("model"); m != "" {
		model = &m
	}

	records, err := h.GetLlmTokenUsageByUser(userID, limit, offset, startDate, endDate, provider, model)
	if err != nil {
		slog.Error("Failed to get LLM token usage", "error", err, "user_id", userID)
		c.JSON(http.StatusInternalServerError, ApiResponse{Code: 500, Message: fmt.Sprintf("Failed to retrieve token usage: %v", err)})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{Code: 0, Message: "success", Data: records})
}

// getLlmTokenUsageStatsHandler retrieves aggregated token usage statistics for a user
func (h *DatabaseHandler) getLlmTokenUsageStatsHandler(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := strconv.Atoi(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, ApiResponse{Code: 400, Message: "Invalid user_id"})
		return
	}

	var startDate, endDate *time.Time
	if startDateStr := c.Query("start_date"); startDateStr != "" {
		parsed, err := time.Parse(time.RFC3339, startDateStr)
		if err == nil {
			startDate = &parsed
		}
	}
	if endDateStr := c.Query("end_date"); endDateStr != "" {
		parsed, err := time.Parse(time.RFC3339, endDateStr)
		if err == nil {
			endDate = &parsed
		}
	}

	stats, err := h.GetLlmTokenUsageStats(userID, startDate, endDate)
	if err != nil {
		slog.Error("Failed to get LLM token usage stats", "error", err, "user_id", userID)
		c.JSON(http.StatusInternalServerError, ApiResponse{Code: 500, Message: fmt.Sprintf("Failed to retrieve token usage stats: %v", err)})
		return
	}

	c.JSON(http.StatusOK, ApiResponse{Code: 0, Message: "success", Data: stats})
}
