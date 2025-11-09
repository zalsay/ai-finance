package models

import (
	"time"
)

type Stock struct {
	ID          int       `json:"id" db:"id"`
	Symbol      string    `json:"symbol" db:"symbol"`
	CompanyName string    `json:"company_name" db:"company_name"`
	Exchange    *string   `json:"exchange" db:"exchange"`
	Sector      *string   `json:"sector" db:"sector"`
	Industry    *string   `json:"industry" db:"industry"`
	MarketCap   *int64    `json:"market_cap" db:"market_cap"`
	CreatedAt   time.Time `json:"created_at" db:"created_at"`
	UpdatedAt   time.Time `json:"updated_at" db:"updated_at"`
}

type StockPrice struct {
	ID           int       `json:"id" db:"id"`
	StockID      int       `json:"stock_id" db:"stock_id"`
	Price        float64   `json:"price" db:"price"`
	ChangePercent *float64 `json:"change_percent" db:"change_percent"`
	Volume       *int64    `json:"volume" db:"volume"`
	MarketCap    *int64    `json:"market_cap" db:"market_cap"`
	RecordedAt   time.Time `json:"recorded_at" db:"recorded_at"`
}

type StockPrediction struct {
	ID             int       `json:"id" db:"id"`
	StockID        int       `json:"stock_id" db:"stock_id"`
	PredictedHigh  *float64  `json:"predicted_high" db:"predicted_high"`
	PredictedLow   *float64  `json:"predicted_low" db:"predicted_low"`
	Confidence     *float64  `json:"confidence" db:"confidence"`
	Sentiment      *string   `json:"sentiment" db:"sentiment"`
	Analysis       *string   `json:"analysis" db:"analysis"`
	PredictionDate time.Time `json:"prediction_date" db:"prediction_date"`
	CreatedAt      time.Time `json:"created_at" db:"created_at"`
}

type UserWatchlist struct {
	ID      int       `json:"id" db:"id"`
	UserID  int       `json:"user_id" db:"user_id"`
	StockID int       `json:"stock_id" db:"stock_id"`
	AddedAt time.Time `json:"added_at" db:"added_at"`
	Notes   *string   `json:"notes" db:"notes"`
}

type UserPortfolio struct {
	ID           int       `json:"id" db:"id"`
	UserID       int       `json:"user_id" db:"user_id"`
	StockID      int       `json:"stock_id" db:"stock_id"`
	Shares       float64   `json:"shares" db:"shares"`
	AverageCost  float64   `json:"average_cost" db:"average_cost"`
	PurchaseDate time.Time `json:"purchase_date" db:"purchase_date"`
	CreatedAt    time.Time `json:"created_at" db:"created_at"`
	UpdatedAt    time.Time `json:"updated_at" db:"updated_at"`
}

// DTOs for API responses
type StockData struct {
	Symbol        string           `json:"symbol"`
	CompanyName   string           `json:"company_name"`
	CurrentPrice  float64          `json:"current_price"`
	ChangePercent float64          `json:"change_percent"`
	Prediction    *StockPrediction `json:"prediction,omitempty"`
}

type WatchlistItem struct {
	ID          int                `json:"id"`
	Stock       Stock              `json:"stock"`
	CurrentPrice *StockPrice       `json:"current_price,omitempty"`
	Prediction  *StockPrediction   `json:"prediction,omitempty"`
	AddedAt     time.Time          `json:"added_at"`
	Notes       *string            `json:"notes"`
}

type AddToWatchlistRequest struct {
	Symbol string  `json:"symbol" binding:"required"`
	Notes  *string `json:"notes"`
}

type UpdateWatchlistRequest struct {
	Notes *string `json:"notes"`
}

type PortfolioItem struct {
	ID           int              `json:"id"`
	Stock        Stock            `json:"stock"`
	Shares       float64          `json:"shares"`
	AverageCost  float64          `json:"average_cost"`
	CurrentPrice *StockPrice      `json:"current_price,omitempty"`
	TotalValue   float64          `json:"total_value"`
	GainLoss     float64          `json:"gain_loss"`
	GainLossPercent float64       `json:"gain_loss_percent"`
	PurchaseDate time.Time        `json:"purchase_date"`
}