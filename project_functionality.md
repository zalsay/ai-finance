# Project Functionality Documentation

## Overview
This project is a comprehensive financial analysis and prediction platform that leverages advanced AI models to forecast stock market trends. It consists of a modern web frontend, a robust backend API, and specialized AI services for time-series forecasting.

## Architecture
The project follows a microservices-like architecture with the following main components:

1.  **Frontend (`fintrack-ai-front`)**: A React-based web application.
2.  **Backend API (`fintrack-api`)**: A Go (Gin) server handling business logic, authentication, and data persistence.
3.  **AI Services (`ai-fucntions`)**:
    *   **Kronos**: A foundation model for financial K-line data.
    *   **TimesFM Service**: A FastAPI service providing stock prediction capabilities using the TimesFM model.
    *   **Akshare Server**: A data provider service (implied).

## Component Details

### 1. Frontend (`fintrack-ai-front`)
*   **Tech Stack**: React 19, TypeScript, Vite, TailwindCSS (implied by class names).
*   **Key Features**:
    *   **Dashboard**: Displays stock data and predictions.
    *   **Watchlist**: Allows users to track specific stocks.
    *   **Authentication**: User login and profile management using JWT.
    *   **Internationalization**: Support for multiple languages.
    *   **Responsive Design**: Mobile-friendly navigation and layout.
*   **Integration**: Communicates with the backend API and potentially directly with AI services (via proxy or backend).

### 2. Backend API (`fintrack-api`)
*   **Tech Stack**: Go 1.21, Gin Web Framework, PostgreSQL (`lib/pq`).
*   **Key Features**:
    *   **RESTful API**: Provides endpoints for the frontend.
    *   **Authentication**: JWT-based auth middleware.
    *   **Database Management**: Handles connections and schema initialization for PostgreSQL.
    *   **Configuration**: Loads settings from config files/env variables.
*   **Structure**:
    *   `handlers`: Request handlers.
    *   `models`: Database models.
    *   `routes`: API route definitions.
    *   `services`: Business logic.

### 3. AI Services (`ai-fucntions`)

#### A. Kronos
*   **Description**: A decoder-only foundation model designed specifically for financial market data (K-lines).
*   **Core Logic**:
    *   **Tokenizer**: Quantizes continuous OHLCV data into discrete tokens.
    *   **Model**: Autoregressive Transformer pre-trained on data from 45+ global exchanges.
    *   **Capabilities**: Forecasting, fine-tuning on custom datasets (e.g., A-share market).
*   **Usage**: capable of generating probabilistic forecasts for future market movements.

#### B. TimesFM Service (`timesfm`)
*   **Tech Stack**: Python, FastAPI, PyTorch/JAX (implied by env vars).
*   **Description**: A dedicated service for stock price prediction using the TimesFM model.
*   **API Endpoints**:
    *   `POST /predict`: Predicts for a single stock.
    *   `POST /predict/batch`: Batch prediction for multiple stocks.
    *   `POST /predict/chunked`: Segmented prediction for long sequences or backtesting (Mode 1: Fixed training set).
    *   `GET /health`: Service health check.
*   **Features**:
    *   **Data Preprocessing**: Fetches data via `akshare-tools`, handles normalization.
    *   **Metrics**: Calculates MSE, MAE, and combined scores to evaluate predictions.
    *   **GPU Acceleration**: Supports GPU inference.

#### C. Akshare Tools (`akshare-tools`)
*   **Purpose**: Utilities to fetch financial data, likely using the Akshare library.
*   **Integration**: Used by the TimesFM service to retrieve historical stock data for training and inference.

## Data Flow
1.  **User Interaction**: User requests stock analysis via the Frontend.
2.  **API Request**: Frontend calls Backend API.
3.  **Data Retrieval**: Backend (or AI service directly) fetches historical data using Akshare tools.
4.  **AI Inference**: Data is passed to Kronos or TimesFM models for prediction.
5.  **Response**: Predictions are returned to the Frontend for visualization.

## Deployment
*   **Docker**: The `timesfm` directory contains a `Dockerfile` and `docker-compose.yml`, suggesting containerized deployment for the AI services.
*   **Environment**: Relies on environment variables for configuration (e.g., DB credentials, GPU IDs).
