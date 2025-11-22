package routes

import (
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

	// CORS配置
	corsConfig := cors.DefaultConfig()
	corsConfig.AllowOrigins = cfg.CORS.AllowedOrigins
	corsConfig.AllowMethods = cfg.CORS.AllowedMethods
	corsConfig.AllowHeaders = cfg.CORS.AllowedHeaders
	corsConfig.AllowCredentials = cfg.CORS.AllowCredentials
	router.Use(cors.New(corsConfig))

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
