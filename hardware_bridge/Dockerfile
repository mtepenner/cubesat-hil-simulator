FROM golang:1.21-alpine AS builder

WORKDIR /app

COPY go.mod go.sum* ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /bridge ./cmd/daemon/

FROM alpine:3.19
RUN apk --no-cache add ca-certificates
COPY --from=builder /bridge /usr/local/bin/bridge

ENTRYPOINT ["bridge"]
CMD ["--mock"]
