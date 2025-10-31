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

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables (if not using Cloud Foundry services):
```bash
export RABBITMQ_HOST=localhost
export RABBITMQ_PORT=5672
# ... etc
```

3. Run the application:
```bash
python app.py
```

4. Open browser: http://localhost:8080

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

4. Deploy the application:
```bash
cf push
```

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

