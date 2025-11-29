package routes

import (
	"bytes"
	"compress/gzip"
	"io"
	"strings"
	"time"

	"fintrack-api/config"
	"fintrack-api/database"
	"fintrack-api/handlers"
	"fintrack-api/services"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

func SetupRouter(cfg *config.Config, db *database.DB) *gin.Engine {
	// 设置Gin模式
	if cfg.Server.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	router := gin.Default()

	// 支持请求体gzip解压
	router.Use(func(c *gin.Context) {
		if strings.EqualFold(c.GetHeader("Content-Encoding"), "gzip") {
			if gzReader, err := gzip.NewReader(c.Request.Body); err == nil {
				defer gzReader.Close()
				if body, err := io.ReadAll(gzReader); err == nil {
					c.Request.Body = io.NopCloser(bytes.NewReader(body))
					c.Request.Header.Del("Content-Encoding")
				}
			}
		}
		c.Next()
	})

	// 响应内容gzip压缩（不依赖外部包）
	router.Use(GzipResponseMiddleware())

	// CORS配置：全量放通（与 postgres-handler 保持一致）
	router.Use(cors.New(cors.Config{
		AllowOriginFunc:  func(origin string) bool { return true },
		AllowMethods:     []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept", "Authorization", "X-Requested-With", "Content-Length"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: cfg.CORS.AllowCredentials,
		MaxAge:           12 * time.Hour,
	}))

	// 初始化服务
	authService := services.NewAuthService(db)
	watchlistService := services.NewWatchlistService(db, cfg)

	// 初始化处理器
	authHandler := handlers.NewAuthHandler(authService)
	watchlistHandler := handlers.NewWatchlistHandler(watchlistService)

	// 健康检查
	router.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status":  "ok",
			"message": "FinTrack API is running",
		})
	})

	// API版本组
	v1 := router.Group("/api/v1")
	{
		// 认证路由
		auth := v1.Group("/auth")
		{
			auth.POST("/register", authHandler.Register)
			auth.POST("/login", authHandler.Login)
			auth.GET("/profile", authHandler.AuthMiddleware(), authHandler.GetProfile)
			auth.POST("/logout", authHandler.AuthMiddleware(), authHandler.Logout)
		}

		// Watchlist路由
		watchlist := v1.Group("/watchlist")
		watchlist.Use(authHandler.AuthMiddleware())
		{
			watchlist.POST("", watchlistHandler.AddToWatchlist)
			watchlist.GET("", watchlistHandler.GetWatchlist)
			watchlist.DELETE("/:id", watchlistHandler.RemoveFromWatchlist)
			watchlist.PUT("/:id", watchlistHandler.UpdateWatchlistItem)
		}

		// 预测保存路由：保存TimesFM最佳分位结果（无需鉴权，或按需添加鉴权）
		savePredictions := v1.Group("/save-predictions")
		{
			savePredictions.POST("/mtf-best", watchlistHandler.SaveTimesfmBest)
			savePredictions.POST("/mtf-best/val-chunk", watchlistHandler.SaveTimesfmValChunk)

			// 公开接口：按 unique_key 查询单条 best 记录
			savePredictions.GET("/mtf-best/by-unique", watchlistHandler.GetTimesfmBestByUniqueKey)
			// 公开接口：按 unique_key 查询单条 best 记录的验证集分块
			savePredictions.POST("/backtest", watchlistHandler.SaveTimesfmBacktest)
		}

		getPredictions := v1.Group("/get-predictions")
		{
			// 需要鉴权，按当前登录用户查询其关联的best列表
			getPredictions.GET("/mtf-best", authHandler.AuthMiddleware(), watchlistHandler.ListTimesfmBestByUser)
			// 公开查询：根据 is_public = 1 返回公开的 timesfm-best，并同步返回对应的验证集分块
			getPredictions.GET("/mtf-best/public", watchlistHandler.ListPublicTimesfmBestWithValidation)
		}



		// TimesFM 推理与回测代理路由
		timesfm := v1.Group("/mtf")
		{
			timesfm.POST("/predict", watchlistHandler.TriggerTimesfmPredict)
			timesfm.POST("/backtest", authHandler.AuthMiddleware(), watchlistHandler.RunTimesfmBacktestProxy)
		}

		// 股票相关路由（预留）
		stocks := v1.Group("/stocks")
		{
			stocks.GET("", func(c *gin.Context) {
				c.JSON(200, gin.H{"message": "Stocks endpoint - coming soon"})
			})
			stocks.GET("/:symbol", func(c *gin.Context) {
				c.JSON(200, gin.H{"message": "Stock detail endpoint - coming soon"})
			})
		}
	}

	return router
}

// gzip Writer包装，拦截写出并压缩
type gzipWriter struct {
	gin.ResponseWriter
	writer io.Writer
}

func (g *gzipWriter) Write(data []byte) (int, error) {
	return g.writer.Write(data)
}

// 中间件：按客户端Accept-Encoding支持gzip时压缩响应
func GzipResponseMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		if !strings.Contains(c.GetHeader("Accept-Encoding"), "gzip") {
			c.Next()
			return
		}
		c.Header("Content-Encoding", "gzip")
		gz := gzip.NewWriter(c.Writer)
		defer gz.Close()
		c.Writer = &gzipWriter{ResponseWriter: c.Writer, writer: gz}
		c.Next()
	}
}
