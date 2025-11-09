package services

import (
	"database/sql"
	"fmt"

	"fintrack-api/database"
	"fintrack-api/models"
)

type WatchlistService struct {
	db *database.DB
}

func NewWatchlistService(db *database.DB) *WatchlistService {
	return &WatchlistService{db: db}
}

func (s *WatchlistService) AddToWatchlist(userID int, req *models.AddToWatchlistRequest) error {
	// First, check if stock exists or create it
	var stockID int
	err := s.db.Conn.QueryRow(`
		SELECT id FROM stocks WHERE symbol = $1
	`, req.Symbol).Scan(&stockID)
	
	if err != nil {
		if err == sql.ErrNoRows {
			// Stock doesn't exist, create it
			err = s.db.Conn.QueryRow(`
				INSERT INTO stocks (symbol, company_name, exchange, sector) 
				VALUES ($1, $2, $3, $4) 
				RETURNING id
			`, req.Symbol, req.Symbol, nil, nil).Scan(&stockID)
			if err != nil {
				return fmt.Errorf("failed to create stock: %v", err)
			}
		} else {
			return fmt.Errorf("failed to check stock existence: %v", err)
		}
	}

	// Add to watchlist
	_, err = s.db.Conn.Exec(`
		INSERT INTO user_watchlist (user_id, stock_id, notes) 
		VALUES ($1, $2, $3)
	`, userID, stockID, req.Notes)
	
	if err != nil {
		return fmt.Errorf("failed to add to watchlist: %v", err)
	}

	return nil
}

func (s *WatchlistService) GetWatchlist(userID int) ([]models.WatchlistItem, error) {
	rows, err := s.db.Conn.Query(`
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
		var price sql.NullFloat64
		var changePercent sql.NullFloat64
		var volume sql.NullInt64

		err := rows.Scan(
			&item.ID, &item.AddedAt, &item.Notes,
			&item.Stock.ID, &item.Stock.Symbol, &item.Stock.CompanyName, 
			&item.Stock.Exchange, &item.Stock.Sector, &item.Stock.Industry, 
			&item.Stock.MarketCap, &item.Stock.CreatedAt, &item.Stock.UpdatedAt,
			&price, &changePercent, &volume,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan watchlist item: %v", err)
		}

		// Set current price if available
		if price.Valid {
			item.CurrentPrice = &models.StockPrice{
				Price:         price.Float64,
				ChangePercent: &changePercent.Float64,
				Volume:        &volume.Int64,
			}
		}

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