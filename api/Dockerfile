# Build stage
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copy go mod files
COPY go.mod ./
COPY main.go ./
COPY secrets-schema.yaml ./

# Download dependencies and generate go.sum
RUN go mod download && go mod tidy

# Install swag for generating Swagger docs
RUN go install github.com/swaggo/swag/cmd/swag@latest

# Generate Swagger documentation
RUN swag init

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o vault-api .

# Final stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /root/

# Copy the binary from builder
COPY --from=builder /app/vault-api .

# Copy Swagger docs
COPY --from=builder /app/docs ./docs

# Copy secrets schema file
COPY --from=builder /app/secrets-schema.yaml ./secrets-schema.yaml

EXPOSE 8000

CMD ["./vault-api"]
