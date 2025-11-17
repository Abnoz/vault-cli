package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/hashicorp/vault/api"
	"github.com/spf13/cobra"
)

var (
	vaultAddr  string
	vaultToken string
	secretPath string = "secret/data/dev"
)

var rootCmd = &cobra.Command{
	Use:   "vault-cli",
	Short: "CLI tool to manage Vault secrets",
	Long:  "A CLI tool to list, add, edit, and delete secrets in HashiCorp Vault",
}

var listCmd = &cobra.Command{
	Use:   "list",
	Short: "List all secrets",
	Long:  "List all secrets stored in the Vault dev path",
	Run:   listSecrets,
}

var getCmd = &cobra.Command{
	Use:   "get [key]",
	Short: "Get a specific secret value",
	Long:  "Get the value of a specific secret by key name",
	Args:  cobra.ExactArgs(1),
	Run:   getSecret,
}

var addCmd = &cobra.Command{
	Use:   "add [key] [value]",
	Short: "Add a new secret",
	Long:  "Add a new secret key-value pair to Vault",
	Args:  cobra.ExactArgs(2),
	Run:   addSecret,
}

var editCmd = &cobra.Command{
	Use:   "edit [key] [value]",
	Short: "Edit an existing secret",
	Long:  "Edit the value of an existing secret. If value is provided, it will be set directly. Otherwise, you'll be prompted to enter it.",
	Args:  cobra.RangeArgs(1, 2),
	Run:   editSecret,
}

var deleteForce bool

var deleteCmd = &cobra.Command{
	Use:   "delete [key]",
	Short: "Delete a secret",
	Long:  "Delete a secret from Vault",
	Args:  cobra.ExactArgs(1),
	Run:   deleteSecret,
}

var setCmd = &cobra.Command{
	Use:   "set [key] [value]",
	Short: "Set a secret value (add or update)",
	Long:  "Set a secret value. Creates the secret if it doesn't exist, updates it if it does.",
	Args:  cobra.ExactArgs(2),
	Run:   setSecret,
}

func init() {
	// Default to vault service name for Docker, but can be overridden
	defaultAddr := "http://vault:8200"
	if os.Getenv("VAULT_ADDR") != "" {
		defaultAddr = os.Getenv("VAULT_ADDR")
	} else if os.Getenv("DOCKER") == "" {
		// If not in Docker, use localhost
		defaultAddr = "http://localhost:8200"
	}
	
	rootCmd.PersistentFlags().StringVar(&vaultAddr, "addr", defaultAddr, "Vault server address")
	rootCmd.PersistentFlags().StringVar(&vaultToken, "token", "", "Vault token (or set VAULT_TOKEN env var)")
	rootCmd.PersistentFlags().StringVar(&secretPath, "path", "secret/data/dev", "Secret path in Vault")

	rootCmd.AddCommand(listCmd)
	rootCmd.AddCommand(getCmd)
	rootCmd.AddCommand(addCmd)
	rootCmd.AddCommand(editCmd)
	deleteCmd.Flags().BoolVarP(&deleteForce, "force", "f", false, "Skip confirmation prompt")
	rootCmd.AddCommand(deleteCmd)
	rootCmd.AddCommand(setCmd)
}

func getVaultClient() (*api.Client, error) {
	// Use environment variable if token flag is not set
	if vaultToken == "" {
		vaultToken = os.Getenv("VAULT_TOKEN")
	}

	// Use environment variable if addr flag is not set
	if vaultAddr == "" {
		vaultAddr = os.Getenv("VAULT_ADDR")
		if vaultAddr == "" {
			// Default to vault service name for Docker, fallback to localhost
			vaultAddr = "http://vault:8200"
		}
	}

	config := api.DefaultConfig()
	config.Address = vaultAddr

	client, err := api.NewClient(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create Vault client: %w", err)
	}

	if vaultToken == "" {
		return nil, fmt.Errorf("Vault token is required. Set VAULT_TOKEN env var or use --token flag")
	}

	client.SetToken(vaultToken)
	return client, nil
}

func readSecrets(client *api.Client) (map[string]interface{}, error) {
	secret, err := client.Logical().Read(secretPath)
	if err != nil {
		return nil, fmt.Errorf("error reading secrets: %w", err)
	}

	if secret == nil || secret.Data == nil {
		return make(map[string]interface{}), nil
	}

	// Extract data from KV v2 response
	var data map[string]interface{}
	if dataRaw, ok := secret.Data["data"]; ok {
		if dataMap, ok := dataRaw.(map[string]interface{}); ok {
			data = dataMap
		}
	}

	if data == nil {
		return make(map[string]interface{}), nil
	}

	return data, nil
}

func writeSecrets(client *api.Client, data map[string]interface{}) error {
	_, err := client.Logical().Write(secretPath, map[string]interface{}{
		"data": data,
	})
	if err != nil {
		return fmt.Errorf("error writing secrets: %w", err)
	}
	return nil
}

func listSecrets(cmd *cobra.Command, args []string) {
	client, err := getVaultClient()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	data, err := readSecrets(client)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	if len(data) == 0 {
		fmt.Println("No secrets found.")
		return
	}

	fmt.Printf("\nFound %d secret(s):\n\n", len(data))
	fmt.Println("Key\t\t\tValue")
	fmt.Println(strings.Repeat("-", 80))

	for key, value := range data {
		valueStr := fmt.Sprintf("%v", value)
		// Truncate long values for display
		if len(valueStr) > 50 {
			valueStr = valueStr[:47] + "..."
		}
		fmt.Printf("%-30s\t%s\n", key, valueStr)
	}
	fmt.Println()
}

func getSecret(cmd *cobra.Command, args []string) {
	key := args[0]

	client, err := getVaultClient()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	data, err := readSecrets(client)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	value, exists := data[key]
	if !exists {
		fmt.Fprintf(os.Stderr, "Error: Secret '%s' not found\n", key)
		os.Exit(1)
	}

	fmt.Println(value)
}

func addSecret(cmd *cobra.Command, args []string) {
	key := args[0]
	value := args[1]

	client, err := getVaultClient()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	data, err := readSecrets(client)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	if _, exists := data[key]; exists {
		fmt.Fprintf(os.Stderr, "Error: Secret '%s' already exists. Use 'edit' or 'set' to update it.\n", key)
		os.Exit(1)
	}

	data[key] = value

	if err := writeSecrets(client, data); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("✓ Successfully added secret '%s'\n", key)
}

func editSecret(cmd *cobra.Command, args []string) {
	key := args[0]
	var newValue string

	client, err := getVaultClient()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	data, err := readSecrets(client)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	currentValue, exists := data[key]
	if !exists {
		fmt.Fprintf(os.Stderr, "Error: Secret '%s' not found. Use 'add' to create it.\n", key)
		os.Exit(1)
	}

	// If value is provided as argument, use it directly
	if len(args) == 2 {
		newValue = args[1]
	} else {
		// Otherwise, prompt for input
		fmt.Printf("Current value: %v\n", currentValue)
		fmt.Print("Enter new value: ")

		// Check if stdin is a terminal
		fileInfo, _ := os.Stdin.Stat()
		if (fileInfo.Mode() & os.ModeCharDevice) == 0 {
			// Not a terminal, try to read from stdin anyway
			reader := bufio.NewReader(os.Stdin)
			input, err := reader.ReadString('\n')
			if err != nil {
				fmt.Fprintf(os.Stderr, "\nError: Cannot read input interactively. Please provide the value as an argument:\n")
				fmt.Fprintf(os.Stderr, "  vault-cli edit %s \"new-value\"\n", key)
				os.Exit(1)
			}
			newValue = strings.TrimSpace(input)
		} else {
			// It's a terminal, read normally
			reader := bufio.NewReader(os.Stdin)
			input, err := reader.ReadString('\n')
			if err != nil {
				fmt.Fprintf(os.Stderr, "Error reading input: %v\n", err)
				os.Exit(1)
			}
			newValue = strings.TrimSpace(input)
		}
	}

	if newValue == "" {
		fmt.Println("No value entered. Aborting.")
		os.Exit(1)
	}

	// Try to preserve type if it's a number or boolean
	if intVal, err := strconv.Atoi(newValue); err == nil {
		data[key] = intVal
	} else if boolVal, err := strconv.ParseBool(newValue); err == nil {
		data[key] = boolVal
	} else {
		data[key] = newValue
	}

	if err := writeSecrets(client, data); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("✓ Successfully updated secret '%s'\n", key)
}

func deleteSecret(cmd *cobra.Command, args []string) {
	key := args[0]

	client, err := getVaultClient()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	data, err := readSecrets(client)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	if _, exists := data[key]; !exists {
		fmt.Fprintf(os.Stderr, "Error: Secret '%s' not found\n", key)
		os.Exit(1)
	}

	// Confirm deletion unless --force flag is used
	if !deleteForce {
		fmt.Printf("Are you sure you want to delete '%s'? (yes/no): ", key)
		
		// Check if stdin is a terminal
		fileInfo, _ := os.Stdin.Stat()
		if (fileInfo.Mode() & os.ModeCharDevice) != 0 {
			// It's a terminal, read normally
			reader := bufio.NewReader(os.Stdin)
			confirmation, err := reader.ReadString('\n')
			if err != nil {
				fmt.Fprintf(os.Stderr, "\nError reading input: %v\n", err)
				fmt.Fprintf(os.Stderr, "Use --force flag to skip confirmation: vault-cli delete %s --force\n", key)
				os.Exit(1)
			}
			confirmation = strings.TrimSpace(strings.ToLower(confirmation))
			if confirmation != "yes" && confirmation != "y" {
				fmt.Println("Deletion cancelled.")
				return
			}
		} else {
			// Not a terminal, require --force flag
			fmt.Fprintf(os.Stderr, "\nError: Cannot read confirmation interactively.\n")
			fmt.Fprintf(os.Stderr, "Use --force flag to skip confirmation: vault-cli delete %s --force\n", key)
			os.Exit(1)
		}
	}

	delete(data, key)

	if err := writeSecrets(client, data); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("✓ Successfully deleted secret '%s'\n", key)
}

func setSecret(cmd *cobra.Command, args []string) {
	key := args[0]
	value := args[1]

	client, err := getVaultClient()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	data, err := readSecrets(client)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	existed := false
	if _, exists := data[key]; exists {
		existed = true
	}

	// Try to preserve type if it's a number or boolean
	if intVal, err := strconv.Atoi(value); err == nil {
		data[key] = intVal
	} else if boolVal, err := strconv.ParseBool(value); err == nil {
		data[key] = boolVal
	} else {
		data[key] = value
	}

	if err := writeSecrets(client, data); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	if existed {
		fmt.Printf("✓ Successfully updated secret '%s'\n", key)
	} else {
		fmt.Printf("✓ Successfully added secret '%s'\n", key)
	}
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

