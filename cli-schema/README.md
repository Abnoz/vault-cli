# Schema CLI Tool

A command-line interface tool to manage the secrets schema YAML file (`secrets-schema.yaml`).

## Installation

The CLI is available as a Docker image. The helper script will build it automatically on first use.

## Usage

### List all secret definitions

```bash
./cli-schema/schema-cli.sh list
```

### Get a specific secret definition

```bash
./cli-schema/schema-cli.sh get POSTGRES_SERVER
```

### Add a new secret definition

```bash
./cli-schema/schema-cli.sh add VARIABLE_NAME type required "description"
```

**Parameters:**
- `VARIABLE_NAME`: Name of the variable
- `type`: Data type (`string`, `integer`, `boolean`, or `float`)
- `required`: Whether the variable is required (`true` or `false`)
- `description`: Description of the variable

**Example:**
```bash
./cli-schema/schema-cli.sh add NEW_API_KEY string true "API key for external service"
```

### Edit a secret definition property

```bash
./cli-schema/schema-cli.sh edit VARIABLE_NAME property value
```

**Properties you can edit:**
- `type`: Change the data type
- `required`: Change if it's required (`true` or `false`)
- `description`: Change the description

**Examples:**
```bash
# Change type
./cli-schema/schema-cli.sh edit POSTGRES_PORT type integer

# Change required status
./cli-schema/schema-cli.sh edit DEBUG required false

# Change description
./cli-schema/schema-cli.sh edit SECRET_KEY description "Secret key for JWT tokens"
```

### Delete a secret definition

```bash
./cli-schema/schema-cli.sh delete VARIABLE_NAME
```

This will prompt for confirmation before deleting.

**Example:**
```bash
./cli-schema/schema-cli.sh delete OLD_VARIABLE
```

## Options

- `--file`: Specify a different schema file path (default: `api/secrets-schema.yaml`)

**Example:**
```bash
./cli-schema/schema-cli.sh --file custom-schema.yaml list
```

## Examples

```bash
# List all definitions
./cli-schema/schema-cli.sh list

# Get a specific definition
./cli-schema/schema-cli.sh get AZURE_CLIENT_ID

# Add a new variable
./cli-schema/schema-cli.sh add NEW_FEATURE_FLAG boolean false "Feature flag for new feature"

# Edit a variable's type
./cli-schema/schema-cli.sh edit MAX_RETRIES type integer

# Edit a variable's required status
./cli-schema/schema-cli.sh edit OPTIONAL_CONFIG required false

# Edit a variable's description
./cli-schema/schema-cli.sh edit API_URL description "Base URL for the API endpoint"

# Delete a variable
./cli-schema/schema-cli.sh delete DEPRECATED_VAR
```

## Valid Types

- `string`: Text values
- `integer`: Whole numbers
- `boolean`: true/false values
- `float`: Decimal numbers

