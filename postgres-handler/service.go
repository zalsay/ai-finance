package main

import (
    "database/sql"
    "fmt"
    "time"
)

type DatabaseHandler struct {
    db *sql.DB
}

func (h *DatabaseHandler) Close() error { return h.db.Close() }

func (h *DatabaseHandler) InsertStockData(data *StockData) error {
    query := `
    INSERT INTO stock_data (
        datetime, open, close, high, low, volume, amount, amplitude,
        percentage_change, amount_change, turnover_rate, type, symbol
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
    RETURNING id, created_at, updated_at`
    return h.db.QueryRow(query,
        data.Datetime, data.Open, data.Close, data.High, data.Low,
        data.Volume, data.Amount, data.Amplitude, data.PercentageChange,
        data.AmountChange, data.TurnoverRate, data.Type, data.Symbol,
    ).Scan(&data.ID, &data.CreatedAt, &data.UpdatedAt)
}

func (h *DatabaseHandler) BatchInsertStockData(dataList []StockData) error {
    tx, err := h.db.Begin()
    if err != nil { return fmt.Errorf("failed to begin transaction: %v", err) }
    defer tx.Rollback()
    stmt, err := tx.Prepare(`
    INSERT INTO stock_data (
        datetime, open, close, high, low, volume, amount, amplitude,
        percentage_change, amount_change, turnover_rate, type, symbol
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)`)
    if err != nil { return fmt.Errorf("failed to prepare statement: %v", err) }
    defer stmt.Close()
    for _, data := range dataList {
        if _, err := stmt.Exec(
            data.Datetime, data.Open, data.Close, data.High, data.Low,
            data.Volume, data.Amount, data.Amplitude, data.PercentageChange,
            data.AmountChange, data.TurnoverRate, data.Type, data.Symbol,
        ); err != nil { return fmt.Errorf("failed to execute batch insert: %v", err) }
    }
    if err := tx.Commit(); err != nil { return fmt.Errorf("failed to commit transaction: %v", err) }
    return nil
}

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
    return err
}

func (h *DatabaseHandler) BatchInsertTimesfmForecast(list []TimesfmForecast) error {
    if len(list) == 0 { return fmt.Errorf("empty list") }
    tx, err := h.db.Begin(); if err != nil { return err }
    stmt, err := tx.Prepare(`
        INSERT INTO timesfm_forecast (
            symbol, ds, tsf, tsf_01, tsf_02, tsf_03, tsf_04, tsf_05, tsf_06, tsf_07, tsf_08, tsf_09,
            chunk_index, best_quantile, best_quantile_pct, best_pred_pct, actual_pct, diff_pct, mse, mae, combined_score,
            version, horizon_len
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
            $13, $14, $15, $16, $17, $18, $19, $20, $21,
            $22, $23
        )`)
    if err != nil { tx.Rollback(); return err }
    defer stmt.Close()
    for _, v := range list {
        if _, err := stmt.Exec(
            v.Symbol, v.Ds, v.Tsf, v.Tsf01, v.Tsf02, v.Tsf03, v.Tsf04, v.Tsf05, v.Tsf06, v.Tsf07, v.Tsf08, v.Tsf09,
            v.ChunkIndex, v.BestQuantile, v.BestQuantilePct, v.BestPredPct, v.ActualPct, v.DiffPct, v.MSE, v.MAE, v.CombinedScore,
            v.Version, v.HorizonLen,
        ); err != nil { tx.Rollback(); return err }
    }
    return tx.Commit()
}

func (h *DatabaseHandler) BatchUpsertEtfDaily(dataList []EtfDailyData) error {
    tx, err := h.db.Begin(); if err != nil { return fmt.Errorf("failed to begin transaction: %v", err) }
    defer tx.Rollback()
    stmt, err := tx.Prepare(`
    INSERT INTO etf_daily (
        code, trading_date, name, latest_price, change_amount, change_percent,
        buy, sell, prev_close, open, high, low, volume, turnover
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
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
    if err != nil { return fmt.Errorf("failed to prepare etf upsert statement: %v", err) }
    defer stmt.Close()
    for _, d := range dataList {
        if _, err := stmt.Exec(
            d.Code, d.TradingDate, d.Name, d.LatestPrice, d.ChangeAmount, d.ChangePercent,
            d.Buy, d.Sell, d.PrevClose, d.Open, d.High, d.Low, d.Volume, d.Turnover,
        ); err != nil { return fmt.Errorf("failed to execute etf upsert batch: %v", err) }
    }
    if err := tx.Commit(); err != nil { return fmt.Errorf("failed to commit etf upsert batch: %v", err) }
    return nil
}

func (h *DatabaseHandler) UpsertIndexInfo(info *IndexInfo) error {
    _, err := h.db.Exec(`
    INSERT INTO index_info (code, display_name, publish_date)
    VALUES ($1, $2, $3)
    ON CONFLICT (code) DO UPDATE SET
        display_name = EXCLUDED.display_name,
        publish_date = EXCLUDED.publish_date`, info.Code, info.DisplayName, info.PublishDate)
    return err
}

func (h *DatabaseHandler) BatchUpsertIndexInfo(list []IndexInfo) error {
    tx, err := h.db.Begin(); if err != nil { return err }
    defer func() { if err != nil { tx.Rollback() } }()
    stmt, err := tx.Prepare(`
        INSERT INTO index_info (code, display_name, publish_date)
        VALUES ($1, $2, $3)
        ON CONFLICT (code) DO UPDATE SET
            display_name = EXCLUDED.display_name,
            publish_date = EXCLUDED.publish_date`)
    if err != nil { return err }
    defer stmt.Close()
    for _, v := range list {
        if _, err = stmt.Exec(v.Code, v.DisplayName, v.PublishDate); err != nil {
            return fmt.Errorf("batch upsert index_info failed: %v", err)
        }
    }
    if err = tx.Commit(); err != nil { return err }
    return nil
}

func (h *DatabaseHandler) UpsertIndexDaily(d *IndexDailyData) error {
    _, err := h.db.Exec(`
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
        change_percent = EXCLUDED.change_percent`,
        d.Code, d.TradingDate, d.Open, d.Close, d.High, d.Low, d.Volume, d.Amount, d.ChangePercent)
    return err
}

func (h *DatabaseHandler) BatchUpsertIndexDaily(list []IndexDailyData) error {
    tx, err := h.db.Begin(); if err != nil { return err }
    defer func() { if err != nil { tx.Rollback() } }()
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
    if err != nil { return err }
    defer stmt.Close()
    for _, v := range list {
        if _, err = stmt.Exec(v.Code, v.TradingDate, v.Open, v.Close, v.High, v.Low, v.Volume, v.Amount, v.ChangePercent); err != nil {
            return fmt.Errorf("batch upsert index_daily failed: %v", err)
        }
    }
    if err = tx.Commit(); err != nil { return err }
    return nil
}

func (h *DatabaseHandler) BatchUpsertAStockCommentDaily(list []StockCommentDaily) error {
    tx, err := h.db.Begin(); if err != nil { return err }
    defer func() { if err != nil { tx.Rollback() } }()
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
    if err != nil { return err }
    defer stmt.Close()
    for _, v := range list {
        if _, err = stmt.Exec(
            v.Code, v.TradingDate, v.Name, v.LatestPrice, v.ChangePercent, v.TurnoverRate,
            v.PeRatio, v.MainCost, v.InstitutionParticipation, v.CompositeScore,
            v.Rise, v.CurrentRank, v.AttentionIndex,
        ); err != nil { return fmt.Errorf("batch upsert a_stock_comment_daily failed: %v", err) }
    }
    if err = tx.Commit(); err != nil { return err }
    return nil
}

func (h *DatabaseHandler) GetAStockCommentDailyByName(name string, limit int, offset int) ([]StockCommentDaily, error) {
    rows, err := h.db.Query(`
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
    LIMIT $2 OFFSET $3`, "%"+name+"%", limit, offset)
    if err != nil { return nil, fmt.Errorf("failed to query a_stock_comment_daily by name: %v", err) }
    defer rows.Close()
    var result []StockCommentDaily
    for rows.Next() {
        var item StockCommentDaily
        if err := rows.Scan(
            &item.Code, &item.TradingDate, &item.Name, &item.LatestPrice,
            &item.ChangePercent, &item.TurnoverRate, &item.PeRatio, &item.MainCost,
            &item.InstitutionParticipation, &item.CompositeScore, &item.Rise,
            &item.CurrentRank, &item.AttentionIndex,
        ); err != nil { return nil, fmt.Errorf("failed to scan a_stock_comment_daily row: %v", err) }
        result = append(result, item)
    }
    if len(result) == 0 { return nil, nil }
    return result, nil
}

func (h *DatabaseHandler) GetStockData(symbol string, stockType int, limit int, offset int) ([]StockData, error) {
    rows, err := h.db.Query(`
    SELECT id, datetime, open, close, high, low, volume, amount, amplitude,
           percentage_change, amount_change, turnover_rate, type, symbol,
           created_at, updated_at
    FROM stock_data
    WHERE symbol = $1 AND type = $2
    ORDER BY datetime DESC
    LIMIT $3 OFFSET $4`, symbol, stockType, limit, offset)
    if err != nil { return nil, fmt.Errorf("failed to query stock data: %v", err) }
    defer rows.Close()
    var results []StockData
    for rows.Next() {
        var data StockData
        if err := rows.Scan(
            &data.ID, &data.Datetime, &data.Open, &data.Close, &data.High, &data.Low,
            &data.Volume, &data.Amount, &data.Amplitude, &data.PercentageChange,
            &data.AmountChange, &data.TurnoverRate, &data.Type, &data.Symbol,
            &data.CreatedAt, &data.UpdatedAt,
        ); err != nil { return nil, fmt.Errorf("failed to scan row: %v", err) }
        results = append(results, data)
    }
    return results, nil
}

func (h *DatabaseHandler) GetStockDataByDateRange(symbol string, stockType int, startDate, endDate time.Time) ([]StockData, error) {
    rows, err := h.db.Query(`
    SELECT id, datetime, open, close, high, low, volume, amount, amplitude,
           percentage_change, amount_change, turnover_rate, type, symbol,
           created_at, updated_at
    FROM stock_data
    WHERE symbol = $1 AND type = $2 AND datetime >= $3 AND datetime <= $4
    ORDER BY datetime ASC`, symbol, stockType, startDate, endDate)
    if err != nil { return nil, fmt.Errorf("failed to query stock data by date range: %v", err) }
    defer rows.Close()
    var results []StockData
    for rows.Next() {
        var data StockData
        if err := rows.Scan(
            &data.ID, &data.Datetime, &data.Open, &data.Close, &data.High, &data.Low,
            &data.Volume, &data.Amount, &data.Amplitude, &data.PercentageChange,
            &data.AmountChange, &data.TurnoverRate, &data.Type, &data.Symbol,
            &data.CreatedAt, &data.UpdatedAt,
        ); err != nil { return nil, fmt.Errorf("failed to scan row: %v", err) }
        results = append(results, data)
    }
    return results, nil
}

func (h *DatabaseHandler) GetEtfDaily(code string, limit int, offset int) ([]EtfDailyData, error) {
    rows, err := h.db.Query(`
    SELECT code, trading_date, name, latest_price, change_amount, change_percent,
           buy, sell, prev_close, open, high, low, volume, turnover
    FROM etf_daily
    WHERE code = $1
    ORDER BY trading_date DESC
    LIMIT $2 OFFSET $3`, code, limit, offset)
    if err != nil { return nil, fmt.Errorf("failed to query etf_daily: %v", err) }
    defer rows.Close()
    var results []EtfDailyData
    for rows.Next() {
        var d EtfDailyData
        if err := rows.Scan(
            &d.Code, &d.TradingDate, &d.Name, &d.LatestPrice, &d.ChangeAmount, &d.ChangePercent,
            &d.Buy, &d.Sell, &d.PrevClose, &d.Open, &d.High, &d.Low, &d.Volume, &d.Turnover,
        ); err != nil { return nil, fmt.Errorf("failed to scan etf_daily row: %v", err) }
        results = append(results, d)
    }
    return results, nil
}

func (h *DatabaseHandler) GetEtfDailyByDateRange(code string, startDate, endDate time.Time) ([]EtfDailyData, error) {
    rows, err := h.db.Query(`
    SELECT code, trading_date, name, latest_price, change_amount, change_percent,
           buy, sell, prev_close, open, high, low, volume, turnover
    FROM etf_daily
    WHERE code = $1 AND trading_date >= $2 AND trading_date <= $3
    ORDER BY trading_date ASC`, code, startDate, endDate)
    if err != nil { return nil, fmt.Errorf("failed to query etf_daily by date range: %v", err) }
    defer rows.Close()
    var results []EtfDailyData
    for rows.Next() {
        var d EtfDailyData
        if err := rows.Scan(
            &d.Code, &d.TradingDate, &d.Name, &d.LatestPrice, &d.ChangeAmount, &d.ChangePercent,
            &d.Buy, &d.Sell, &d.PrevClose, &d.Open, &d.High, &d.Low, &d.Volume, &d.Turnover,
        ); err != nil { return nil, fmt.Errorf("failed to scan etf_daily row: %v", err) }
        results = append(results, d)
    }
    return results, nil
}

func (h *DatabaseHandler) GetIndexDaily(code string, limit int, offset int) ([]IndexDailyData, error) {
    rows, err := h.db.Query(`
    SELECT code, trading_date, open, close, high, low, volume, amount, change_percent
    FROM index_daily
    WHERE code = $1
    ORDER BY trading_date DESC
    LIMIT $2 OFFSET $3`, code, limit, offset)
    if err != nil { return nil, fmt.Errorf("failed to query index_daily: %v", err) }
    defer rows.Close()
    var result []IndexDailyData
    for rows.Next() {
        var item IndexDailyData
        if err := rows.Scan(&item.Code, &item.TradingDate, &item.Open, &item.Close, &item.High, &item.Low, &item.Volume, &item.Amount, &item.ChangePercent); err != nil {
            return nil, fmt.Errorf("failed to scan index_daily row: %v", err)
        }
        result = append(result, item)
    }
    if len(result) == 0 { return nil, nil }
    return result, nil
}

func (h *DatabaseHandler) GetIndexDailyByDateRange(code string, startDate, endDate time.Time) ([]IndexDailyData, error) {
    rows, err := h.db.Query(`
    SELECT code, trading_date, open, close, high, low, volume, amount, change_percent
    FROM index_daily
    WHERE code = $1 AND trading_date BETWEEN $2 AND $3
    ORDER BY trading_date ASC`, code, startDate, endDate)
    if err != nil { return nil, fmt.Errorf("failed to query index_daily by date range: %v", err) }
    defer rows.Close()
    var result []IndexDailyData
    for rows.Next() {
        var item IndexDailyData
        if err := rows.Scan(&item.Code, &item.TradingDate, &item.Open, &item.Close, &item.High, &item.Low, &item.Volume, &item.Amount, &item.ChangePercent); err != nil {
            return nil, fmt.Errorf("failed to scan index_daily row: %v", err)
        }
        result = append(result, item)
    }
    if len(result) == 0 { return nil, nil }
    return result, nil
}

