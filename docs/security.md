# Security Practices

- Keep tokens/DSNs in environment variables.
- Do not commit `.env` files.
- Use least-privilege DB accounts.
- Use `socrata doctor --check-db` to verify configuration without exposing credentials.
