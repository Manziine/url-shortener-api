# URL Shortener API

<div align="center">

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white)

**A production-grade URL shortening service** — the classic backend interview project, built to real engineering standards with caching, analytics, rate limiting, and full observability.

</div>

---

## 🎯 Why This Project

URL shorteners appear in nearly every backend engineering interview. This implementation goes beyond the basics — it's what you'd actually build at a company like Bitly or TinyURL, demonstrating:

- **System design thinking**: Redis for hot-path caching, PostgreSQL for persistence
- **Performance**: Sub-millisecond redirects via Redis cache
- **Scalability**: Stateless app layer, horizontal scaling ready
- **Reliability**: Rate limiting, error handling, health checks
- **Observability**: Request analytics, click tracking

## 🏗️ Architecture

```
Client Request (GET /:code)
        │
        ▼
┌──────────────────┐
│   Nginx (SSL)    │  ← Rate limiting at edge
└────────┬─────────┘
         │
┌────────▼─────────┐
│   FastAPI App    │
│  (POST /shorten) │
│  (GET /:code)    │
└──┬──────────┬────┘
   │          │
┌──▼───┐  ┌───▼──────────┐
│Redis │  │  PostgreSQL  │
│Cache │  │  (persist)   │
│(TTL) │  │  analytics   │
└──────┘  └──────────────┘
```

**Cache strategy**: Redis stores short_code → long_url with 24h TTL. On cache miss, falls back to PostgreSQL and re-populates cache.

## ✅ Features

| Feature | Details |
|---|---|
| ⚡ Sub-ms redirects | Redis cache for hot URLs |
| 📊 Click analytics | Track clicks, referrers, timestamps per URL |
| 🔐 Optional auth | Authenticated users can manage their links |
| 🚦 Rate limiting | 10 req/min for anonymous, 100/min for auth users |
| 🔗 Custom slugs | Users can specify a custom short code |
| ⏰ URL expiration | Set TTL on shortened URLs |
| 🩺 Health checks | `/health` and `/metrics` endpoints |

## 🚀 Quick Start

```bash
git clone https://github.com/Manziine/url-shortener-api.git
cd url-shortener-api
cp .env.example .env
docker compose up --build

# Shorten a URL
curl -X POST http://localhost:8000/api/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/Manziine", "custom_slug": "portfolio"}'

# Response: {"short_url": "http://localhost:8000/portfolio", "code": "portfolio"}

# Redirect
curl -L http://localhost:8000/portfolio
# → redirects to https://github.com/Manziine
```

## 📁 Project Structure

```
url-shortener-api/
├── app/
│   ├── api/
│   │   ├── shorten.py      # POST /api/shorten — create short URL
│   │   ├── redirect.py     # GET /:code — redirect to original URL
│   │   └── analytics.py    # GET /api/analytics/:code — click stats
│   ├── core/
│   │   ├── config.py       # Settings (pydantic-settings)
│   │   ├── database.py     # Async PostgreSQL (SQLAlchemy)
│   │   ├── redis.py        # Redis connection & cache helpers
│   │   └── shortener.py    # URL encoding/collision logic
│   ├── models/
│   │   └── url.py          # SQLAlchemy URL + Click models
│   └── main.py             # FastAPI app factory
├── .github/workflows/ci.yml
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## 📡 API Reference

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/shorten` | Create short URL | Optional |
| GET | `/:code` | Redirect to original URL | ❌ |
| GET | `/api/analytics/:code` | Get click stats | ✅ |
| DELETE | `/api/urls/:code` | Delete a short URL | ✅ |
| GET | `/health` | Health check | ❌ |

### POST `/api/shorten` Request Body

```json
{
  "url": "https://github.com/Manziine",
  "custom_slug": "portfolio",    // optional
  "expires_in_days": 30          // optional, default: never
}
```

## 💡 Design Decisions & Trade-offs

**Why Redis + PostgreSQL (not just one)?**
- Redis alone loses data on restart and can't do complex queries
- PostgreSQL alone is too slow for high-frequency redirects (100k+ req/day)
- Together: Redis handles the hot path (microseconds), PostgreSQL handles analytics and durability

**Why Base62 encoding for codes?**
- Produces URL-safe, human-readable codes (`aB3xZ`)
- 6-character codes give 56 billion unique combinations
- No special characters that could break URLs

**Collision handling:**
- If generated code exists, append a counter suffix and retry (max 5 attempts)

## 🛠️ Built By

**Arnaud Ineza Manzi** — Backend Engineer
📧 ainezamanzi@gmail.com | 🔗 [LinkedIn](https://linkedin.com/in/arnaud-ineza-manzi-471221272) | 🐙 [GitHub](https://github.com/Manziine)
