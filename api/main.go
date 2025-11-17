package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/hashicorp/vault/api"
	swaggerFiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"
	"gopkg.in/yaml.v3"
	
	_ "vault-secrets-api/docs" // This is important for swagger docs
)

// @title           Vault Secrets API
// @version         1.0.0
// @description     API to read secrets from HashiCorp Vault
// @termsOfService  http://swagger.io/terms/

// @contact.name   API Support
// @contact.url    http://www.example.com/support
// @contact.email  support@example.com

// @license.name  Apache 2.0
// @license.url   http://www.apache.org/licenses/LICENSE-2.0.html

// @securityDefinitions.apikey ApiKeyAuth
// @in header
// @name X-API-Key
// @description Enter your API key in the format: Bearer {token}

// @host      localhost:8001
// @BasePath  /

var (
	apiKey      string
	vaultAddr   string
	vaultToken  string
	vaultClient *api.Client
)

type SecretResponse struct {
	Path  string `json:"path"`
	Key   string `json:"key"`
	Value string `json:"value"`
}

type HealthResponse struct {
	Status            string `json:"status"`
	VaultAuthenticated bool  `json:"vault_authenticated"`
	VaultAddress      string `json:"vault_address"`
	Error             string `json:"error,omitempty"`
}

type RootResponse struct {
	Message  string            `json:"message"`
	Version  string            `json:"version"`
	Endpoints map[string]string `json:"endpoints"`
}

// SecretSchema represents a secret definition in the YAML schema
type SecretSchema struct {
	Name        string `yaml:"name"`
	Type        string `yaml:"type"`
	Required    bool   `yaml:"required"`
	Description string `yaml:"description"`
}

// SecretsSchema represents the YAML schema structure
type SecretsSchema struct {
	Secrets []SecretSchema `yaml:"secrets"`
}

// ValidationResult represents the result of validating a single secret
type ValidationResult struct {
	Name      string `json:"name"`
	Valid     bool   `json:"valid"`
	Present   bool   `json:"present"`
	TypeValid bool   `json:"type_valid"`
	Error     string `json:"error,omitempty"`
}

// SecretsValidationResponse represents the overall validation response
type SecretsValidationResponse struct {
	SecretsValidation bool              `json:"secrets_validation"`
	TotalSecrets      int               `json:"total_secrets"`
	ValidSecrets      int               `json:"valid_secrets"`
	MissingSecrets    int               `json:"missing_secrets"`
	InvalidSecrets    int               `json:"invalid_secrets"`
	Results           []ValidationResult `json:"results"`
}

func init() {
	apiKey = os.Getenv("API_KEY")
	vaultAddr = os.Getenv("VAULT_ADDR")
	if vaultAddr == "" {
		vaultAddr = "http://vault:8200"
	}
	vaultToken = os.Getenv("VAULT_TOKEN")

	// Initialize Vault client
	config := api.DefaultConfig()
	config.Address = vaultAddr
	var err error
	vaultClient, err = api.NewClient(config)
	if err != nil {
		log.Fatalf("Failed to create Vault client: %v", err)
	}
	if vaultToken != "" {
		vaultClient.SetToken(vaultToken)
	}
}

func verifyAPIKey() gin.HandlerFunc {
	return func(c *gin.Context) {
		apiKeyHeader := c.GetHeader("X-API-Key")
		
		if apiKeyHeader == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"detail": "API key required. Please provide X-API-Key header in your request.",
			})
			c.Abort()
			return
		}

		if apiKey == "" {
			c.JSON(http.StatusInternalServerError, gin.H{
				"detail": "API key not configured on server. Please contact administrator.",
			})
			c.Abort()
			return
		}

		if apiKeyHeader != apiKey {
			c.JSON(http.StatusForbidden, gin.H{
				"detail": "Invalid API key",
			})
			c.Abort()
			return
		}

		c.Next()
	}
}

// rootHandler godoc
// @Summary      Get API information
// @Description  Returns API information and available endpoints
// @Tags         info
// @Accept       json
// @Produce      json
// @Success      200  {object}  RootResponse
// @Router       / [get]
func rootHandler(c *gin.Context) {
	response := RootResponse{
		Message:  "Vault Secrets API",
		Version:  "1.0.0",
		Endpoints: map[string]string{
			"get_dev_key":    "/api/v1/secrets/dev/{key}",
			"validate":       "/api/v1/secrets/validate",
			"health":         "/health",
			"swagger":        "/swagger/index.html",
		},
	}
	c.JSON(http.StatusOK, response)
}

// healthHandler godoc
// @Summary      Health check
// @Description  Check the health status of the API and Vault connection
// @Tags         health
// @Accept       json
// @Produce      json
// @Success      200  {object}  HealthResponse
// @Router       /health [get]
func healthHandler(c *gin.Context) {
	response := HealthResponse{
		VaultAddress: vaultAddr,
	}

	// Check if Vault is accessible
	if vaultToken == "" {
		response.Status = "unhealthy"
		response.Error = "Vault token not configured"
		c.JSON(http.StatusOK, response)
		return
	}

	// Try to check Vault health endpoint (doesn't require authentication)
	healthClient, err := api.NewClient(&api.Config{
		Address: vaultAddr,
	})
	if err != nil {
		response.Status = "unhealthy"
		response.Error = err.Error()
		c.JSON(http.StatusOK, response)
		return
	}

	// Check health endpoint
	healthResp, err := healthClient.Sys().Health()
	if err != nil {
		response.Status = "unhealthy"
		response.Error = err.Error()
		c.JSON(http.StatusOK, response)
		return
	}

	if healthResp != nil {
		response.Status = "healthy"
		// Check if we can authenticate with the token
		if vaultToken != "" {
			vaultClient.SetToken(vaultToken)
			_, err := vaultClient.Auth().Token().LookupSelf()
			response.VaultAuthenticated = (err == nil)
		}
	} else {
		response.Status = "unhealthy"
		response.Error = "Vault returned empty response"
	}

	c.JSON(http.StatusOK, response)
}

// getDevSecretKeyHandler godoc
// @Summary      Get secret value by key
// @Description  Get a specific key value from the 'dev' path in Vault
// @Tags         secrets
// @Accept       json
// @Produce      json
// @Param        key   path      string  true  "Secret key name (e.g., POSTGRES_PASSWORD, AZURE_CLIENT_ID)"
// @Success      200   {object}  SecretResponse
// @Failure      401   {object}  map[string]string  "Unauthorized - API key required"
// @Failure      403   {object}  map[string]string  "Forbidden - Invalid API key"
// @Failure      404   {object}  map[string]string  "Not Found - Key or path not found"
// @Failure      500   {object}  map[string]string  "Internal Server Error"
// @Security     ApiKeyAuth
// @Router       /api/v1/secrets/dev/{key} [get]
func getDevSecretKeyHandler(c *gin.Context) {
	key := c.Param("key")

	// Check for custom Vault token in header
	customToken := c.GetHeader("X-Vault-Token")
	if customToken != "" {
		vaultClient.SetToken(customToken)
		defer vaultClient.SetToken(vaultToken) // Restore original token
	}

	// Read secret from Vault
	secretPath := "secret/data/dev"
	secret, err := vaultClient.Logical().Read(secretPath)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"detail": fmt.Sprintf("Error reading secret: %v", err),
		})
		return
	}

	if secret == nil || secret.Data == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"detail": "Secret path 'dev' not found",
		})
		return
	}

	// Extract data from KV v2 response
	var data map[string]interface{}
	if dataRaw, ok := secret.Data["data"]; ok {
		if dataMap, ok := dataRaw.(map[string]interface{}); ok {
			data = dataMap
		}
	}

	if data == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"detail": "Secret path 'dev' not found",
		})
		return
	}

	// Get the specific key
	value, exists := data[key]
	if !exists {
		c.JSON(http.StatusNotFound, gin.H{
			"detail": fmt.Sprintf("Key '%s' not found in path 'dev'", key),
		})
		return
	}

	// Convert value to string
	valueStr := fmt.Sprintf("%v", value)

	response := SecretResponse{
		Path:  "secret/dev",
		Key:   key,
		Value: valueStr,
	}

	c.JSON(http.StatusOK, response)
}

// validateSecretType validates if a value matches the expected type
func validateSecretType(value interface{}, expectedType string) bool {
	if value == nil {
		return false
	}

	valueStr := fmt.Sprintf("%v", value)
	
	switch expectedType {
	case "string":
		return true // All values can be strings
	case "integer":
		_, err := strconv.Atoi(valueStr)
		return err == nil
	case "boolean":
		lower := strings.ToLower(valueStr)
		return lower == "true" || lower == "false" || lower == "1" || lower == "0"
	case "float":
		_, err := strconv.ParseFloat(valueStr, 64)
		return err == nil
	default:
		return true // Unknown types are considered valid
	}
}

// validateSecretsHandler validates all secrets in Vault against the schema
// validateSecretsHandler godoc
// @Summary      Validate secrets against schema
// @Description  Validates all secrets in Vault against the secrets-schema.yaml file. Returns true if all required secrets are present and valid.
// @Tags         validation
// @Accept       json
// @Produce      json
// @Success      200   {object}  SecretsValidationResponse
// @Failure      401   {object}  map[string]string  "Unauthorized - API key required"
// @Failure      403   {object}  map[string]string  "Forbidden - Invalid API key"
// @Failure      500   {object}  map[string]string  "Internal Server Error"
// @Security     ApiKeyAuth
// @Router       /api/v1/secrets/validate [get]
func validateSecretsHandler(c *gin.Context) {
	// Check for custom Vault token in header
	customToken := c.GetHeader("X-Vault-Token")
	if customToken != "" {
		vaultClient.SetToken(customToken)
		defer vaultClient.SetToken(vaultToken) // Restore original token
	}

	// Read secrets from Vault
	secretPath := "secret/data/dev"
	secret, err := vaultClient.Logical().Read(secretPath)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"detail": fmt.Sprintf("Error reading secrets from Vault: %v", err),
		})
		return
	}

	if secret == nil || secret.Data == nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"detail": "Secret path 'dev' not found in Vault",
		})
		return
	}

	// Extract data from KV v2 response
	var vaultData map[string]interface{}
	if dataRaw, ok := secret.Data["data"]; ok {
		if dataMap, ok := dataRaw.(map[string]interface{}); ok {
			vaultData = dataMap
		}
	}

	if vaultData == nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"detail": "No data found in secret path 'dev'",
		})
		return
	}

	// Read and parse the YAML schema
	schemaFile := "secrets-schema.yaml"
	if _, err := os.Stat(schemaFile); os.IsNotExist(err) {
		// Try in current directory or common locations
		possiblePaths := []string{
			"./secrets-schema.yaml",
			"/app/secrets-schema.yaml",
			"/root/secrets-schema.yaml",
		}
		found := false
		for _, path := range possiblePaths {
			if _, err := os.Stat(path); err == nil {
				schemaFile = path
				found = true
				break
			}
		}
		if !found {
			c.JSON(http.StatusInternalServerError, gin.H{
				"detail": "secrets-schema.yaml file not found",
			})
			return
		}
	}

	schemaData, err := os.ReadFile(schemaFile)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"detail": fmt.Sprintf("Error reading schema file: %v", err),
		})
		return
	}

	var schema SecretsSchema
	if err := yaml.Unmarshal(schemaData, &schema); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"detail": fmt.Sprintf("Error parsing schema file: %v", err),
		})
		return
	}

	// Validate each secret
	results := []ValidationResult{}
	validCount := 0
	missingCount := 0
	invalidCount := 0

	for _, secretDef := range schema.Secrets {
		result := ValidationResult{
			Name: secretDef.Name,
		}

		// Check if secret exists in Vault
		value, exists := vaultData[secretDef.Name]
		result.Present = exists

		if !exists {
			if secretDef.Required {
				result.Valid = false
				result.Error = "Required secret is missing"
				missingCount++
			} else {
				result.Valid = true // Optional secrets are valid if missing
				validCount++
			}
		} else {
			// Validate type
			result.TypeValid = validateSecretType(value, secretDef.Type)
			if !result.TypeValid {
				result.Valid = false
				result.Error = fmt.Sprintf("Type mismatch: expected %s, got %T", secretDef.Type, value)
				invalidCount++
			} else {
				result.Valid = true
				validCount++
			}
		}

		results = append(results, result)
	}

	// Determine overall validation status
	secretsValidation := missingCount == 0 && invalidCount == 0

	response := SecretsValidationResponse{
		SecretsValidation: secretsValidation,
		TotalSecrets:      len(schema.Secrets),
		ValidSecrets:      validCount,
		MissingSecrets:    missingCount,
		InvalidSecrets:    invalidCount,
		Results:           results,
	}

	c.JSON(http.StatusOK, response)
}

func setupRouter() *gin.Engine {
	// Set Gin to release mode for production
	if os.Getenv("GIN_MODE") == "" {
		gin.SetMode(gin.ReleaseMode)
	}

	router := gin.Default()

	// CORS middleware
	router.Use(func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, X-API-Key, X-Vault-Token, accept, origin, Cache-Control, X-Requested-With")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT, DELETE, PATCH")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	})

	// Public endpoints
	router.GET("/", rootHandler)
	router.GET("/health", healthHandler)
	
	// Swagger documentation
	router.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))

	// Protected endpoints (require API key)
	api := router.Group("/api/v1")
	api.Use(verifyAPIKey())
	{
		api.GET("/secrets/dev/:key", getDevSecretKeyHandler)
		api.GET("/secrets/validate", validateSecretsHandler)
	}

	return router
}

func main() {
	router := setupRouter()
	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}

	log.Printf("Starting Vault Secrets API on port %s", port)
	if err := router.Run(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}

