# SSL/TLS Certificates Configuration

**Status:** ✅ CERTIFICATES GENERATED
**Date:** 2026-01-18
**Priority:** P1 Critical

## Generated Certificates

Self-signed SSL certificates have been generated for staging deployment:

- **Certificate:** `certificate.crt` (RSA 4096-bit, valid 365 days)
- **Private Key:** `key.pem` (RSA 4096-bit)
- **Subject:** `/C=US/ST=California/L=San Francisco/O=Story Portal/OU=Platform/CN=story-portal.local`
- **Valid From:** 2026-01-18
- **Valid Until:** 2027-01-18

## Certificate Details

```bash
# View certificate details
openssl x509 -in certificate.crt -text -noout

# Verify certificate and key match
openssl x509 -noout -modulus -in certificate.crt | openssl md5
openssl rsa -noout -modulus -in key.pem | openssl md5
```

## Usage

### Option 1: Uvicorn SSL Configuration (Recommended for Development)

Update the service startup command to include SSL parameters:

```bash
uvicorn L09_api_gateway.main:app \
  --host 0.0.0.0 \
  --port 8009 \
  --ssl-keyfile=/app/ssl/key.pem \
  --ssl-certfile=/app/ssl/certificate.crt
```

### Option 2: Nginx SSL Termination (Recommended for Production)

Deploy nginx as a reverse proxy with SSL termination:

```nginx
server {
    listen 443 ssl http2;
    server_name story-portal.local;

    ssl_certificate /etc/ssl/certs/certificate.crt;
    ssl_certificate_key /etc/ssl/private/key.pem;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://l09-api-gateway:8009;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name story-portal.local;
    return 301 https://$server_name$request_uri;
}
```

### Option 3: Docker Compose Integration

Update `docker-compose.app.yml` to mount SSL certificates:

```yaml
l09-api-gateway:
  image: l09-api-gateway:latest
  container_name: l09-api-gateway
  ports:
    - "8009:8009"
    - "8443:8443"  # HTTPS port
  volumes:
    - ./ssl:/app/ssl:ro  # Mount SSL certificates as read-only
  environment:
    - SSL_ENABLED=true
    - SSL_KEYFILE=/app/ssl/key.pem
    - SSL_CERTFILE=/app/ssl/certificate.crt
  command: >
    uvicorn L09_api_gateway.main:app
    --host 0.0.0.0
    --port 8443
    --ssl-keyfile /app/ssl/key.pem
    --ssl-certfile /app/ssl/certificate.crt
```

## Production Deployment

For production, replace self-signed certificates with certificates from a trusted CA.

### Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Generate certificates
sudo certbot --nginx -d story-portal.com

# Auto-renewal is configured by default
sudo certbot renew --dry-run
```

### Manual Certificate Installation

If using certificates from a CA (e.g., DigiCert, Sectigo):

1. Place the certificate files in `platform/ssl/`:
   - `certificate.crt` - Server certificate
   - `key.pem` - Private key
   - `ca-bundle.crt` - CA intermediate certificates (if applicable)

2. Update permissions:
   ```bash
   chmod 600 platform/ssl/key.pem
   chmod 644 platform/ssl/certificate.crt
   ```

3. Verify certificate chain:
   ```bash
   openssl verify -CAfile ca-bundle.crt certificate.crt
   ```

## Security Best Practices

1. **Key Protection:**
   - Never commit private keys to version control
   - Set restrictive permissions (600) on key files
   - Use secrets management for production keys

2. **Certificate Validation:**
   - Regularly check certificate expiration
   - Set up monitoring alerts 30 days before expiration
   - Test certificate renewal process

3. **TLS Configuration:**
   - Use TLS 1.2 or higher only
   - Disable weak ciphers and protocols
   - Enable HSTS for production deployments

4. **Monitoring:**
   - Monitor SSL certificate expiration
   - Track SSL/TLS handshake errors
   - Monitor cipher suite usage

## Testing HTTPS

### Local Testing

```bash
# Test HTTPS connection (self-signed, ignore verification)
curl -k https://localhost:8443/health

# Test with certificate verification (add to hosts file first)
echo "127.0.0.1 story-portal.local" | sudo tee -a /etc/hosts
curl --cacert platform/ssl/certificate.crt https://story-portal.local:8443/health
```

### Certificate Verification

```bash
# Check certificate validity
openssl s_client -connect localhost:8443 -servername story-portal.local < /dev/null

# Test TLS versions
openssl s_client -tls1_2 -connect localhost:8443 < /dev/null
openssl s_client -tls1_3 -connect localhost:8443 < /dev/null
```

## Files in This Directory

- `certificate.crt` - SSL certificate (public)
- `key.pem` - Private key (KEEP SECURE)
- `private.key` - Backup/alternative key format
- `README.md` - This documentation

## .gitignore Configuration

Ensure private keys are not committed:

```gitignore
# SSL/TLS private keys
platform/ssl/*.pem
platform/ssl/*.key
platform/ssl/private.*

# Keep certificate and documentation
!platform/ssl/certificate.crt
!platform/ssl/README.md
```

## Troubleshooting

### Certificate Verification Failed

If clients reject the self-signed certificate:

1. **Option A:** Add certificate to client trust store
2. **Option B:** Use `-k` flag with curl (testing only)
3. **Option C:** Replace with CA-signed certificate

### Permission Denied

```bash
# Fix permissions
sudo chown $(whoami):$(whoami) platform/ssl/*
chmod 600 platform/ssl/key.pem
chmod 644 platform/ssl/certificate.crt
```

### Certificate Expired

```bash
# Regenerate certificate
cd platform/ssl
openssl req -x509 -newkey rsa:4096 \
  -keyout key.pem \
  -out certificate.crt \
  -days 365 -nodes \
  -subj "/C=US/ST=California/L=San Francisco/O=Story Portal/OU=Platform/CN=story-portal.local"
```

## Next Steps

1. ✅ Certificates generated
2. ⏳ Update L09 API Gateway to use SSL
3. ⏳ Configure nginx for SSL termination (optional)
4. ⏳ Update all service URLs to use HTTPS
5. ⏳ Test HTTPS connectivity
6. ⏳ For production: Replace with Let's Encrypt or CA-signed certificates

## References

- [Uvicorn SSL Documentation](https://www.uvicorn.org/#command-line-options)
- [Nginx SSL Configuration](https://nginx.org/en/docs/http/configuring_https_servers.html)
- [Let's Encrypt](https://letsencrypt.org/)
- [SSL Labs Server Test](https://www.ssllabs.com/ssltest/)
