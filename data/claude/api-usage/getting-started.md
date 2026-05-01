# Claude API: Getting Started

The Claude API lets developers integrate Claude into their applications.

## Access

API access requires an Anthropic account at console.anthropic.com. API usage is billed separately from claude.ai subscriptions.

## Authentication

All API requests require an API key passed in the `x-api-key` header:

```
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: YOUR_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-6","max_tokens":1024,"messages":[{"role":"user","content":"Hello"}]}'
```

## API Keys

Create and manage API keys in console.anthropic.com → API Keys. 

Best practices:
- Never commit API keys to source control.
- Use environment variables: `ANTHROPIC_API_KEY`.
- Rotate keys regularly.
- Delete unused keys immediately.

## Rate Limits

Rate limits depend on your usage tier. New accounts start at:
- Requests per minute (RPM): 50
- Tokens per minute (TPM): 40,000
- Tokens per day (TPD): 1,000,000

Limits increase automatically as you use the API and maintain good standing.

## Pricing

Pricing is per million tokens (input + output). See anthropic.com/pricing for current rates. Pricing varies by model.

## SDKs

Official SDKs are available for:
- Python: `pip install anthropic`
- TypeScript/JavaScript: `npm install @anthropic-ai/sdk`
