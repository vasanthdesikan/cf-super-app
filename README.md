# Cloud Foundry Service Tester

A Cloud Foundry application for testing transactions to backend services including RabbitMQ, Valkey (Redis), MySQL, and PostgreSQL.

## Features

- **Dynamic UI Tabs**: Only shows tabs for services enabled in configuration
- **Service Configuration**: Single YAML manifest file controls which services are active
- **Transaction Testing**: Test read/write operations for each configured service
- **Cloud Foundry Ready**: Deployable with `cf push` command
- **Tanzu Data Services Support**: Automatically binds to Tanzu Data Services (p.rabbitmq, p.mysql, etc.)
- **User Provisioned Services Support**: Supports UPS services for external or custom services
- **Automatic Service Discovery**: Intelligently discovers and connects to both Tanzu and UPS services

## Services Supported

- **RabbitMQ**: Publish and consume messages
- **Valkey/Redis**: Set and get key-value pairs
- **MySQL**: Insert and select operations
- **PostgreSQL**: Insert and select operations

## Configuration

Edit `services-config.yml` to enable/disable services:

```yaml
services:
  rabbitmq:
    enabled: true
    display_name: "RabbitMQ"
    
  valkey:
    enabled: true
    display_name: "Valkey"
    
  mysql:
    enabled: true
    display_name: "MySQL"
    
  postgres:
    enabled: true
    display_name: "PostgreSQL"
```

## CLI Interface

The application includes a command-line interface for all operations available in the UI.

### Usage

```bash
python cli.py <service> <action> [options]
```

### Examples

**MySQL Operations:**
```bash
# List all tables
python cli.py mysql list-tables

# Show table data
python cli.py mysql show-table --table test_table
python cli.py mysql show-table --table test_table --limit 20 --offset 0

# Test transaction
python cli.py mysql test --table-name test_table --value "My test data"
```

**PostgreSQL Operations:**
```bash
# List all tables
python cli.py postgres list-tables

# Show table data
python cli.py postgres show-table --table test_table

# Test transaction
python cli.py postgres test --table-name test_table --value "My test data"
```

**RabbitMQ Operations:**
```bash
# List all queues
python cli.py rabbitmq list-queues

# Test transaction
python cli.py rabbitmq test --queue-name my_queue --message "Hello World"

# CRUD Operations
# Publish message (CREATE)
python cli.py rabbitmq publish --queue my_queue --message "Hello World"
python cli.py rabbitmq publish --queue my_queue --message "Persistent" --durable

# Consume message (READ)
python cli.py rabbitmq consume --queue my_queue
python cli.py rabbitmq consume --queue my_queue --no-ack

# Purge queue (DELETE messages)
python cli.py rabbitmq purge --queue my_queue

# Delete queue completely
python cli.py rabbitmq delete-queue --queue my_queue
python cli.py rabbitmq delete-queue --queue my_queue --if-empty
```

**Valkey Operations:**
```bash
# List cache keys
python cli.py valkey list-keys
python cli.py valkey list-keys --pattern "test_*" --limit 50

# Test transaction
python cli.py valkey test --key my_key --value "My value"

# CRUD Operations
# Set key (CREATE/UPDATE)
python cli.py valkey set --key my_key --value "My value"
python cli.py valkey set --key my_key --value "My value" --ttl 3600

# Get key (READ)
python cli.py valkey get --key my_key

# Check if key exists
python cli.py valkey exists --key my_key

# Delete key (DELETE)
python cli.py valkey delete --key my_key
```

### CRUD Operations

**Create (Insert) Rows:**
```bash
# MySQL
python cli.py mysql create --table users --data '{"name":"John","email":"john@example.com","age":30}'

# PostgreSQL
python cli.py postgres create --table users --data '{"name":"John","email":"john@example.com","age":30}'
```

**Update Rows:**
```bash
# MySQL - Update where id = 1
python cli.py mysql update --table users --where "id = %s" --where-values '[1]' --data '{"name":"Jane","age":25}'

# PostgreSQL - Update where id = 1
python cli.py postgres update --table users --where "id = %s" --where-values '[1]' --data '{"name":"Jane","age":25}'
```

**Delete Rows:**
```bash
# MySQL - Delete where id = 1
python cli.py mysql delete --table users --where "id = %s" --where-values '[1]'

# PostgreSQL - Delete where id = 1
python cli.py postgres delete --table users --where "id = %s" --where-values '[1]'

# Delete multiple rows (where age > 50)
python cli.py mysql delete --table users --where "age > %s" --where-values '[50]'
```

### Help

Get help for any service:
```bash
python cli.py <service> --help
python cli.py mysql --help
```

## Local Development

### Quick Setup

Run the setup script to create a virtual environment and install dependencies:

**On macOS/Linux:**
```bash
./setup.sh
```

**On Windows:**
```cmd
setup.bat
```

**Cross-platform (Python script):**
```bash
python3 setup.py
```

The setup script will:
- Check Python version (requires 3.8+)
- Create a virtual environment in `venv/`
- Install all dependencies from `requirements.txt`
- Provide instructions for activation

### Manual Setup

Alternatively, set up manually:

1. Create virtual environment:
```bash
python3 -m venv venv
```

2. Activate virtual environment:
```bash
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate.bat
```

3. Install dependencies:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. Set environment variables (if not using Cloud Foundry services):
```bash
export RABBITMQ_HOST=localhost
export RABBITMQ_PORT=5672
# ... etc
```

5. Run the application:
```bash
python app.py
```

6. Open browser: http://localhost:8080

## Cloud Foundry Deployment

1. Ensure you're logged into Cloud Foundry:
```bash
cf login
```

### Option 1: Tanzu Data Services (Managed Services)

2. Create Tanzu Data Service instances:
```bash
# Tanzu RabbitMQ
cf create-service p.rabbitmq standard my-rabbitmq-service

# Tanzu Redis/Valkey
cf create-service p.redis standard my-valkey-service

# Tanzu MySQL
cf create-service p.mysql standard my-mysql-service

# Tanzu PostgreSQL
cf create-service p.postgresql standard my-postgres-service
```

### Option 2: User Provisioned Services (UPS)

2. Create User Provisioned Service instances:
```bash
# UPS for RabbitMQ
cf create-user-provided-service my-rabbitmq-service \
  -p '{"hostname":"rabbitmq.example.com","port":"5672","username":"user","password":"pass","vhost":"/"}'

# UPS for Valkey/Redis
cf create-user-provided-service my-valkey-service \
  -p '{"host":"redis.example.com","port":"6379","password":"pass"}' \
  -t redis,valkey

# UPS for MySQL
cf create-user-provided-service my-mysql-service \
  -p '{"hostname":"mysql.example.com","port":"3306","name":"mydb","username":"user","password":"pass"}' \
  -t mysql,database

# UPS for PostgreSQL
cf create-user-provided-service my-postgres-service \
  -p '{"hostname":"postgres.example.com","port":"5432","name":"mydb","username":"user","password":"pass"}' \
  -t postgresql,database
```

### Option 3: Mixed (Tanzu + UPS)

You can mix Tanzu Data Services and User Provisioned Services as needed.

3. Update `manifest.yml` to bind your service instances:
```yaml
services:
  - my-rabbitmq-service
  - my-valkey-service
  - my-mysql-service
  - my-postgres-service
```

4. Deploy the application with variables:
```bash
# Get your space name and domain
SPACE_NAME=$(cf target | grep space | awk '{print $2}')
DOMAIN=$(cf domains | grep -v '^name' | head -n 1 | awk '{print $1}')

# Deploy with variables
cf push --var SPACE_NAME=$SPACE_NAME --var DOMAIN=$DOMAIN
```

Alternatively, create a `vars.yml` file:
```yaml
SPACE_NAME: your-space-name
DOMAIN: your-domain.com
```

Then deploy:
```bash
cf push --vars-file vars.yml
```

The routes will be automatically created in the format `{app-name}-{space-name}.{domain}` as specified in the manifest.

The application will automatically:
- Read service credentials from `VCAP_SERVICES`
- Support both Tanzu Data Services and User Provisioned Services
- Initialize only enabled services from `services-config.yml`
- Display tabs only for enabled services

### Service Discovery

The app automatically discovers services in this order:
1. **Tanzu Data Services** - Services with types like `p.rabbitmq`, `p.mysql`, etc.
2. **User Provisioned Services** - Services with type `user-provided` (matched by name or tags)
3. **Standard Cloud Foundry Services** - Services with types like `p-rabbitmq`, `p-mysql`, etc.
4. **Environment Variables** - Fallback if no services found in VCAP_SERVICES

## Project Structure

```
.
├── app.py                      # Main Flask application
├── manifest.yml                # Cloud Foundry deployment manifest
├── Procfile                    # Process definition for Cloud Foundry
├── requirements.txt            # Python dependencies
├── runtime.txt                 # Python version
├── services-config.yml         # Service configuration (enable/disable services)
├── .cfignore                  # Files to ignore during CF push
├── setup.sh                    # Setup script for macOS/Linux
├── setup.bat                   # Setup script for Windows
├── setup.py                    # Cross-platform setup script
├── cli.py                      # Command-line interface
├── services/                   # Service handler modules
│   ├── __init__.py
│   ├── credential_helper.py   # Helper for Tanzu and UPS discovery
│   ├── rabbitmq_handler.py
│   ├── valkey_handler.py
│   ├── mysql_handler.py
│   └── postgres_handler.py
└── templates/
    └── index.html             # Web UI with tabs
```

## How It Works

1. **Configuration Loading**: App reads `services-config.yml` on startup
2. **Service Initialization**: Only enabled services are initialized
3. **Dynamic UI**: Frontend receives enabled services and creates tabs dynamically
4. **Transaction Testing**: Each tab allows testing transactions to its service
5. **Cloud Foundry Integration**: Services are bound via `VCAP_SERVICES` environment variable

## Notes

- **Tanzu Data Services**: Supports services with types like `p.rabbitmq`, `p.mysql`, `p.postgresql`, `p.redis`
- **User Provisioned Services**: Supports UPS services matched by name or tags in VCAP_SERVICES
- **Automatic Discovery**: App automatically detects and connects to both Tanzu and UPS services
- **Credential Parsing**: Handles various credential formats including URIs, connection strings, and structured credentials
- **Environment Variables**: Falls back to environment variables if services not found in VCAP_SERVICES
- **Graceful Handling**: App gracefully handles missing or unavailable services
- **Configuration-Driven**: Only enabled services in `services-config.yml` will show tabs in the UI

## User Provisioned Services (UPS) Tag Convention

For UPS services, the app matches services by:
1. Service name (exact match)
2. Tags containing service type (e.g., `rabbitmq`, `mysql`, `postgresql`, `redis`)

Example UPS with tags:
```bash
cf create-user-provided-service my-db \
  -p '{"hostname":"db.example.com","port":"5432","name":"mydb","username":"user","password":"pass"}' \
  -t postgresql,database
```

