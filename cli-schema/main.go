package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/spf13/cobra"
	"gopkg.in/yaml.v3"
)

var schemaFile string = "api/secrets-schema.yaml"

type SecretSchema struct {
	Name        string `yaml:"name"`
	Type        string `yaml:"type"`
	Required    bool   `yaml:"required"`
	Description string `yaml:"description"`
}

type SecretsSchema struct {
	Secrets []SecretSchema `yaml:"secrets"`
}

var rootCmd = &cobra.Command{
	Use:   "schema-cli",
	Short: "CLI tool to manage secrets schema YAML file",
	Long:  "A CLI tool to list, add, edit, and delete secret definitions in the secrets-schema.yaml file",
}

var listCmd = &cobra.Command{
	Use:   "list",
	Short: "List all secret definitions in schema",
	Long:  "List all secret definitions from the secrets-schema.yaml file",
	Run:   listSecrets,
}

var getCmd = &cobra.Command{
	Use:   "get [name]",
	Short: "Get a specific secret definition",
	Long:  "Get the definition of a specific secret by name",
	Args:  cobra.ExactArgs(1),
	Run:   getSecret,
}

var addCmd = &cobra.Command{
	Use:   "add [name] [type] [required] [description]",
	Short: "Add a new secret definition",
	Long:  "Add a new secret definition to the schema. Required: name, type (string/integer/boolean), required (true/false), description",
	Args:  cobra.ExactArgs(4),
	Run:   addSecret,
}

var editCmd = &cobra.Command{
	Use:   "edit [name] [property] [value]",
	Short: "Edit a property of a secret definition",
	Long:  "Edit a property (type, required, description) of an existing secret definition",
	Args:  cobra.ExactArgs(3),
	Run:   editSecret,
}

var deleteCmd = &cobra.Command{
	Use:   "delete [name]",
	Short: "Delete a secret definition",
	Long:  "Delete a secret definition from the schema",
	Args:  cobra.ExactArgs(1),
	Run:   deleteSecret,
}

func init() {
	rootCmd.PersistentFlags().StringVar(&schemaFile, "file", "api/secrets-schema.yaml", "Path to secrets-schema.yaml file")

	rootCmd.AddCommand(listCmd)
	rootCmd.AddCommand(getCmd)
	rootCmd.AddCommand(addCmd)
	rootCmd.AddCommand(editCmd)
	rootCmd.AddCommand(deleteCmd)
}

func readSchema() (*SecretsSchema, error) {
	data, err := os.ReadFile(schemaFile)
	if err != nil {
		return nil, fmt.Errorf("error reading schema file: %w", err)
	}

	var schema SecretsSchema
	if err := yaml.Unmarshal(data, &schema); err != nil {
		return nil, fmt.Errorf("error parsing schema file: %w", err)
	}

	return &schema, nil
}

func writeSchema(schema *SecretsSchema) error {
	data, err := yaml.Marshal(schema)
	if err != nil {
		return fmt.Errorf("error marshaling schema: %w", err)
	}

	if err := os.WriteFile(schemaFile, data, 0644); err != nil {
		return fmt.Errorf("error writing schema file: %w", err)
	}

	return nil
}

func findSecret(schema *SecretsSchema, name string) (int, *SecretSchema) {
	for i, secret := range schema.Secrets {
		if secret.Name == name {
			return i, &secret
		}
	}
	return -1, nil
}

func listSecrets(cmd *cobra.Command, args []string) {
	schema, err := readSchema()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	if len(schema.Secrets) == 0 {
		fmt.Println("No secrets defined in schema.")
		return
	}

	fmt.Printf("\nFound %d secret definition(s) in schema:\n\n", len(schema.Secrets))
	fmt.Printf("%-40s %-15s %-10s %s\n", "Name", "Type", "Required", "Description")
	fmt.Println(strings.Repeat("-", 100))

	for _, secret := range schema.Secrets {
		required := "No"
		if secret.Required {
			required = "Yes"
		}
		desc := secret.Description
		if len(desc) > 40 {
			desc = desc[:37] + "..."
		}
		fmt.Printf("%-40s %-15s %-10s %s\n", secret.Name, secret.Type, required, desc)
	}
	fmt.Println()
}

func getSecret(cmd *cobra.Command, args []string) {
	name := args[0]

	schema, err := readSchema()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	_, secret := findSecret(schema, name)
	if secret == nil {
		fmt.Fprintf(os.Stderr, "Error: Secret '%s' not found in schema\n", name)
		os.Exit(1)
	}

	fmt.Printf("\nSecret Definition: %s\n", name)
	fmt.Println(strings.Repeat("-", 50))
	fmt.Printf("Name:        %s\n", secret.Name)
	fmt.Printf("Type:        %s\n", secret.Type)
	fmt.Printf("Required:    %v\n", secret.Required)
	fmt.Printf("Description: %s\n", secret.Description)
	fmt.Println()
}

func addSecret(cmd *cobra.Command, args []string) {
	name := args[0]
	secretType := args[1]
	requiredStr := args[2]
	description := args[3]

	// Validate type
	validTypes := []string{"string", "integer", "boolean", "float"}
	typeValid := false
	for _, t := range validTypes {
		if secretType == t {
			typeValid = true
			break
		}
	}
	if !typeValid {
		fmt.Fprintf(os.Stderr, "Error: Invalid type '%s'. Valid types are: %s\n", secretType, strings.Join(validTypes, ", "))
		os.Exit(1)
	}

	// Parse required
	required, err := strconv.ParseBool(requiredStr)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: Invalid required value '%s'. Must be 'true' or 'false'\n", requiredStr)
		os.Exit(1)
	}

	schema, err := readSchema()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	// Check if already exists
	if _, existing := findSecret(schema, name); existing != nil {
		fmt.Fprintf(os.Stderr, "Error: Secret '%s' already exists in schema. Use 'edit' to modify it.\n", name)
		os.Exit(1)
	}

	// Add new secret
	newSecret := SecretSchema{
		Name:        name,
		Type:        secretType,
		Required:    required,
		Description: description,
	}

	schema.Secrets = append(schema.Secrets, newSecret)

	if err := writeSchema(schema); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("✓ Successfully added secret definition '%s' to schema\n", name)
}

func editSecret(cmd *cobra.Command, args []string) {
	name := args[0]
	property := strings.ToLower(args[1])
	value := args[2]

	schema, err := readSchema()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	idx, secret := findSecret(schema, name)
	if secret == nil {
		fmt.Fprintf(os.Stderr, "Error: Secret '%s' not found in schema. Use 'add' to create it.\n", name)
		os.Exit(1)
	}

	switch property {
	case "type":
		// Validate type
		validTypes := []string{"string", "integer", "boolean", "float"}
		typeValid := false
		for _, t := range validTypes {
			if value == t {
				typeValid = true
				break
			}
		}
		if !typeValid {
			fmt.Fprintf(os.Stderr, "Error: Invalid type '%s'. Valid types are: %s\n", value, strings.Join(validTypes, ", "))
			os.Exit(1)
		}
		schema.Secrets[idx].Type = value

	case "required":
		required, err := strconv.ParseBool(value)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: Invalid required value '%s'. Must be 'true' or 'false'\n", value)
			os.Exit(1)
		}
		schema.Secrets[idx].Required = required

	case "description":
		schema.Secrets[idx].Description = value

	default:
		fmt.Fprintf(os.Stderr, "Error: Invalid property '%s'. Valid properties are: type, required, description\n", property)
		os.Exit(1)
	}

	if err := writeSchema(schema); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("✓ Successfully updated property '%s' of secret '%s'\n", property, name)
}

func deleteSecret(cmd *cobra.Command, args []string) {
	name := args[0]

	schema, err := readSchema()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	idx, secret := findSecret(schema, name)
	if secret == nil {
		fmt.Fprintf(os.Stderr, "Error: Secret '%s' not found in schema\n", name)
		os.Exit(1)
	}

	// Confirm deletion
	fmt.Printf("Are you sure you want to delete '%s' from schema? (yes/no): ", name)
	
	// Try to read from stdin
	reader := bufio.NewReader(os.Stdin)
	confirmation, err := reader.ReadString('\n')
	if err != nil {
		// If we can't read interactively, require a flag or skip confirmation
		fmt.Fprintf(os.Stderr, "\nError: Cannot read confirmation. Use --force flag to skip confirmation.\n")
		os.Exit(1)
	}
	confirmation = strings.TrimSpace(strings.ToLower(confirmation))

	if confirmation != "yes" && confirmation != "y" {
		fmt.Println("Deletion cancelled.")
		return
	}

	// Remove from slice
	schema.Secrets = append(schema.Secrets[:idx], schema.Secrets[idx+1:]...)

	if err := writeSchema(schema); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("✓ Successfully deleted secret definition '%s' from schema\n", name)
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

