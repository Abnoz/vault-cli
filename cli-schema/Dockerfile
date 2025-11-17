# Build stage
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copy go mod files
COPY go.mod ./
COPY main.go ./

# Download dependencies
RUN go mod download && go mod tidy

# Build the CLI
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o schema-cli .

# Final stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /app

# Copy the binary from builder
COPY --from=builder /app/schema-cli .

# Copy the schema file (will be mounted as volume, but this ensures it exists)
WORKDIR /workspace

# Default command (can be overridden in docker-compose)
CMD ["./schema-cli"]

