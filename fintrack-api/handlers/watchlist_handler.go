package handlers

import (
	"database/sql"
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

// 保存TimesFM最佳分位预测结果
func (h *WatchlistHandler) SaveTimesfmBest(c *gin.Context) {
	// 可选鉴权：如果需要用户身份控制，可打开以下代码
	// userID, exists := c.Get("user_id")
	// if !exists {
	//     c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
	//     return
	// }

	var req models.SaveTimesfmBestRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.watchlistService.SaveTimesfmBest(&req); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Saved TimesFM best prediction", "unique_key": req.UniqueKey})
}

// 保存验证集分块的预测与实际
func (h *WatchlistHandler) SaveTimesfmValChunk(c *gin.Context) {
	var req models.SaveTimesfmValChunkRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.watchlistService.SaveTimesfmValChunk(&req); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Saved validation chunk", "unique_key": req.UniqueKey, "chunk_index": req.ChunkIndex})
}

// 查询某用户的TimesFM最佳分位预测列表
func (h *WatchlistHandler) ListTimesfmBestByUser(c *gin.Context) {
	userID, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
		return
	}

	results, err := h.watchlistService.ListTimesfmBestByUserID(userID.(int))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"predictions": results,
		"count":       len(results),
	})
}

// 按 unique_key 查询单条 TimesFM 最佳分位预测（公开）
func (h *WatchlistHandler) GetTimesfmBestByUniqueKey(c *gin.Context) {
	uniqueKey := c.Query("unique_key")
	if uniqueKey == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "unique_key is required"})
		return
	}

	item, err := h.watchlistService.GetTimesfmBestByUniqueKey(uniqueKey)
	if err != nil {
		if err == sql.ErrNoRows {
			c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"prediction": item})
}

func (h *WatchlistHandler) SaveStrategyParams(c *gin.Context) {
	var req models.SaveStrategyParamsRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err := h.watchlistService.SaveStrategyParams(&req); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "Saved strategy params", "unique_key": req.UniqueKey})
}

func (h *WatchlistHandler) GetStrategyParamsByUniqueKey(c *gin.Context) {
	uniqueKey := c.Query("unique_key")
	if uniqueKey == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "unique_key is required"})
		return
	}
	item, err := h.watchlistService.GetStrategyParamsByUniqueKey(uniqueKey)
	if err != nil {
		if err == sql.ErrNoRows {
			c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, item)
}

// 公开查询：返回 is_public = 1 的 timesfm-best，并联查对应的验证分块数据
func (h *WatchlistHandler) ListPublicTimesfmBestWithValidation(c *gin.Context) {
	items, err := h.watchlistService.ListPublicTimesfmBest()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// 为每条 best 取关联的验证分块列表
	result := make([]gin.H, 0, len(items))
	for _, it := range items {
		chunks, err := h.watchlistService.ListValidationChunksByUniqueKey(it.UniqueKey)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		result = append(result, gin.H{
			"best":   it,
			"chunks": chunks,
		})
	}

	c.JSON(http.StatusOK, gin.H{"items": result, "count": len(result)})
}

// 保存 TimesFM 回测结果
func (h *WatchlistHandler) SaveTimesfmBacktest(c *gin.Context) {
	var req models.SaveTimesfmBacktestRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.watchlistService.SaveTimesfmBacktest(&req); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "ok", "unique_key": req.UniqueKey})
}

func (h *WatchlistHandler) TriggerTimesfmPredict(c *gin.Context) {
	var req models.TimesfmPredictRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	status, body, err := h.watchlistService.TriggerTimesfmPredict(&req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(status, body)
}

func (h *WatchlistHandler) RunTimesfmBacktestProxy(c *gin.Context) {
	var req models.TimesfmBacktestRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if uid, ok := c.Get("user_id"); ok {
		if req.UserID == nil {
			u := uid.(int)
			req.UserID = &u
		}
	}
	status, body, err := h.watchlistService.RunTimesfmBacktest(&req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(status, body)
}
