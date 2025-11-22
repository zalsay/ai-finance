package handlers

import (
	"net/http"
	"strconv"

	"fintrack-api/models"
	"fintrack-api/services"

	"github.com/gin-gonic/gin"
)

type WatchlistHandler struct {
	watchlistService *services.WatchlistService
}

func NewWatchlistHandler(watchlistService *services.WatchlistService) *WatchlistHandler {
	return &WatchlistHandler{watchlistService: watchlistService}
}

func (h *WatchlistHandler) AddToWatchlist(c *gin.Context) {
	userID, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
		return
	}

	var req models.AddToWatchlistRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	err := h.watchlistService.AddToWatchlist(userID.(int), &req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// Trigger stock data sync asynchronously (non-blocking)
	go h.watchlistService.SyncStockData(req.Symbol)

	c.JSON(http.StatusCreated, gin.H{"message": "Stock added to watchlist successfully"})
}

func (h *WatchlistHandler) GetWatchlist(c *gin.Context) {
	userID, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
		return
	}

	items, err := h.watchlistService.GetWatchlist(userID.(int))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get watchlist"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"watchlist": items,
		"count":     len(items),
	})
}

func (h *WatchlistHandler) RemoveFromWatchlist(c *gin.Context) {
	userID, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
		return
	}

	watchlistIDStr := c.Param("id")
	watchlistID, err := strconv.Atoi(watchlistIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid watchlist ID"})
		return
	}

	err = h.watchlistService.RemoveFromWatchlist(userID.(int), watchlistID)
	if err != nil {
		if err.Error() == "watchlist item not found" {
			c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to remove from watchlist"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Stock removed from watchlist successfully"})
}

func (h *WatchlistHandler) UpdateWatchlistItem(c *gin.Context) {
	userID, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
		return
	}

	watchlistIDStr := c.Param("id")
	watchlistID, err := strconv.Atoi(watchlistIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid watchlist ID"})
		return
	}

	var req models.UpdateWatchlistRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	item, err := h.watchlistService.UpdateWatchlistItem(userID.(int), watchlistID, &req)
	if err != nil {
		if err.Error() == "watchlist item not found" {
			c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update watchlist item"})
		return
	}

	c.JSON(http.StatusOK, item)
}
