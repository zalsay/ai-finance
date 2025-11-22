package services

import (
	"crypto/sha256"
	"database/sql"
	"fmt"
	"time"

	"fintrack-api/database"
	"fintrack-api/models"
	"fintrack-api/utils"

	"golang.org/x/crypto/bcrypt"
)

type AuthService struct {
	db *database.DB
}

func NewAuthService(db *database.DB) *AuthService {
	return &AuthService{db: db}
}

func (s *AuthService) Register(req *models.RegisterRequest) (*models.AuthResponse, error) {
	// Check if user already exists
	var exists bool
	err := s.db.Conn.QueryRow("SELECT EXISTS(SELECT 1 FROM users WHERE email = $1)", req.Email).Scan(&exists)
	if err != nil {
		return nil, fmt.Errorf("failed to check user existence: %w", err)
	}
	if exists {
		return nil, fmt.Errorf("user with email %s already exists", req.Email)
	}

	// Hash password
	hashedPassword, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
	if err != nil {
		return nil, fmt.Errorf("failed to hash password: %w", err)
	}

	// Create user
	var user models.User
	query := `
		INSERT INTO users (email, password_hash, username)
		VALUES ($1, $2, $3)
		RETURNING id, email, username, is_premium, created_at, updated_at
	`
	err = s.db.Conn.QueryRow(query, req.Email, string(hashedPassword), req.Username).Scan(
		&user.ID, &user.Email, &user.Username, &user.IsPremium, &user.CreatedAt, &user.UpdatedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create user: %w", err)
	}

	// Generate JWT token
	token, err := utils.GenerateJWT(user.ID, user.Email)
	if err != nil {
		return nil, fmt.Errorf("failed to generate token: %w", err)
	}

	// Store session
	if err := s.storeSession(user.ID, token); err != nil {
		return nil, fmt.Errorf("failed to store session: %w", err)
	}

	return &models.AuthResponse{
		Token: token,
		User:  user,
	}, nil
}

func (s *AuthService) Login(req *models.LoginRequest) (*models.AuthResponse, error) {
	var user models.User
	var passwordHash string

	query := `
		SELECT id, email, password_hash, username, is_premium, created_at, updated_at
		FROM users 
		WHERE email = $1
	`
	err := s.db.Conn.QueryRow(query, req.Email).Scan(
		&user.ID, &user.Email, &passwordHash, &user.Username, &user.IsPremium, &user.CreatedAt, &user.UpdatedAt,
	)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("invalid email or password")
		}
		return nil, fmt.Errorf("failed to find user: %w", err)
	}

	// Verify password
	if err := bcrypt.CompareHashAndPassword([]byte(passwordHash), []byte(req.Password)); err != nil {
		return nil, fmt.Errorf("invalid email or password")
	}

	// Generate JWT token
	token, err := utils.GenerateJWT(user.ID, user.Email)
	if err != nil {
		return nil, fmt.Errorf("failed to generate token: %w", err)
	}

	// Store session
	if err := s.storeSession(user.ID, token); err != nil {
		return nil, fmt.Errorf("failed to store session: %w", err)
	}

	return &models.AuthResponse{
		Token: token,
		User:  user,
	}, nil
}

func (s *AuthService) GetUserProfile(userID int) (*models.UserProfile, error) {
	var profile models.UserProfile
	query := `
		SELECT id, email, username, is_premium, created_at
		FROM users 
		WHERE id = $1
	`
	err := s.db.Conn.QueryRow(query, userID).Scan(
		&profile.ID, &profile.Email, &profile.Username, &profile.IsPremium, &profile.CreatedAt,
	)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("user not found")
		}
		return nil, fmt.Errorf("failed to get user profile: %w", err)
	}

	return &profile, nil
}

func (s *AuthService) ValidateSession(token string) (*models.User, error) {
	// First validate JWT token
	claims, err := utils.ValidateJWT(token)
	if err != nil {
		return nil, fmt.Errorf("invalid token: %w", err)
	}

	// Check if session exists in database
	tokenHash := s.hashToken(token)
	var sessionExists bool
	err = s.db.Conn.QueryRow(`
		SELECT EXISTS(
			SELECT 1 FROM user_sessions 
			WHERE user_id = $1 AND token_hash = $2 AND expires_at > NOW()
		)
	`, claims.UserID, tokenHash).Scan(&sessionExists)
	if err != nil {
		return nil, fmt.Errorf("failed to validate session: %w", err)
	}
	if !sessionExists {
		return nil, fmt.Errorf("session not found or expired")
	}

	// Get user details
	var user models.User
	query := `
		SELECT id, email, username, is_premium, created_at, updated_at
		FROM users 
		WHERE id = $1
	`
	err = s.db.Conn.QueryRow(query, claims.UserID).Scan(
		&user.ID, &user.Email, &user.Username, &user.IsPremium, &user.CreatedAt, &user.UpdatedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to get user: %w", err)
	}

	return &user, nil
}

func (s *AuthService) Logout(userID int, token string) error {
	tokenHash := s.hashToken(token)
	_, err := s.db.Conn.Exec(`
		DELETE FROM user_sessions 
		WHERE user_id = $1 AND token_hash = $2
	`, userID, tokenHash)
	return err
}

func (s *AuthService) storeSession(userID int, token string) error {
	tokenHash := s.hashToken(token)
	expiresAt := time.Now().Add(24 * time.Hour) // 24 hours from now

	// Use UPSERT to update existing session or insert new one
	// This ensures each user has only one active session
	_, err := s.db.Conn.Exec(`
		INSERT INTO user_sessions (user_id, token_hash, expires_at)
		VALUES ($1, $2, $3)
		ON CONFLICT (user_id) 
		DO UPDATE SET 
			token_hash = EXCLUDED.token_hash,
			expires_at = EXCLUDED.expires_at,
			created_at = CURRENT_TIMESTAMP
	`, userID, tokenHash, expiresAt)

	return err
}

func (s *AuthService) hashToken(token string) string {
	hash := sha256.Sum256([]byte(token))
	return fmt.Sprintf("%x", hash)
}

func (s *AuthService) CleanupExpiredSessions() error {
	_, err := s.db.Conn.Exec("DELETE FROM user_sessions WHERE expires_at < NOW()")
	return err
}

func nullString(s string) *string {
	if s == "" {
		return nil
	}
	return &s
}
