package main

import "time"

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
    Type             int       `json:"type" db:"type"`
    Symbol           string    `json:"symbol" db:"symbol"`
    CreatedAt        time.Time `json:"created_at" db:"created_at"`
    UpdatedAt        time.Time `json:"updated_at" db:"updated_at"`
}

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

type IndexInfo struct {
    Code        string    `json:"code" db:"code"`
    DisplayName string    `json:"display_name" db:"display_name"`
    PublishDate time.Time `json:"publish_date" db:"publish_date"`
    CreatedAt   time.Time `json:"created_at" db:"created_at"`
}

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

type TimesfmForecast struct {
    Symbol          string    `json:"symbol" db:"symbol"`
    Ds              time.Time `json:"ds" db:"ds"`
    Tsf             float64   `json:"tsf" db:"tsf"`
    Tsf01           float64   `json:"tsf_01" db:"tsf_01"`
    Tsf02           float64   `json:"tsf_02" db:"tsf_02"`
    Tsf03           float64   `json:"tsf_03" db:"tsf_03"`
    Tsf04           float64   `json:"tsf_04" db:"tsf_04"`
    Tsf05           float64   `json:"tsf_05" db:"tsf_05"`
    Tsf06           float64   `json:"tsf_06" db:"tsf_06"`
    Tsf07           float64   `json:"tsf_07" db:"tsf_07"`
    Tsf08           float64   `json:"tsf_08" db:"tsf_08"`
    Tsf09           float64   `json:"tsf_09" db:"tsf_09"`
    ChunkIndex      int       `json:"chunk_index" db:"chunk_index"`
    BestQuantile    string    `json:"best_quantile" db:"best_quantile"`
    BestQuantilePct string    `json:"best_quantile_pct" db:"best_quantile_pct"`
    BestPredPct     float64   `json:"best_pred_pct" db:"best_pred_pct"`
    ActualPct       float64   `json:"actual_pct" db:"actual_pct"`
    DiffPct         float64   `json:"diff_pct" db:"diff_pct"`
    MSE             float64   `json:"mse" db:"mse"`
    MAE             float64   `json:"mae" db:"mae"`
    CombinedScore   float64   `json:"combined_score" db:"combined_score"`
    UserID          int       `json:"user_id" db:"user_id"`
    Version         float64   `json:"version" db:"version"`
    HorizonLen      int       `json:"horizon_len" db:"horizon_len"`
}

type StockCommentDaily struct {
    Code                     string    `json:"code" db:"code"`
    TradingDate              time.Time `json:"trading_date" db:"trading_date"`
    Name                     string    `json:"name" db:"name"`
    LatestPrice              float64   `json:"latest_price" db:"latest_price"`
    ChangePercent            float64   `json:"change_percent" db:"change_percent"`
    TurnoverRate             float64   `json:"turnover_rate" db:"turnover_rate"`
    PeRatio                  float64   `json:"pe_ratio" db:"pe_ratio"`
    MainCost                 float64   `json:"main_cost" db:"main_cost"`
    InstitutionParticipation float64   `json:"institution_participation" db:"institution_participation"`
    CompositeScore           float64   `json:"composite_score" db:"composite_score"`
    Rise                     int64     `json:"rise" db:"rise"`
    CurrentRank              int64     `json:"current_rank" db:"current_rank"`
    AttentionIndex           float64   `json:"attention_index" db:"attention_index"`
}

type ApiResponse struct {
    Code    int         `json:"code"`
    Message string      `json:"message"`
    Data    interface{} `json:"data,omitempty"`
}

