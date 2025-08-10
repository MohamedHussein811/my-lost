# My Lost App - API Server 📱

A FastAPI server for reporting and finding lost items without user registration. Users can post lost items on a map with details and search for items by location, category, and text.

## ✨ Features

- 📍 **Location-based reporting**: Add lost items with GPS coordinates
- 🔍 **Advanced search**: Filter by category, location, and text search
- 🚀 **Fast performance**: Memory caching for quick responses
- 🛡️ **Rate limiting**: 2 posts per day per device to prevent spam
- 📱 **No registration**: Anonymous reporting using device identifiers
- 🌍 **Geospatial queries**: Find items near specific locations

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- MongoDB (local or cloud)

### 1. Clone and Install
```bash
git clone <repository-url>
cd my-lost-app
pip install -r requirements.txt
```

### 2. Set Environment Variables
Create a `.env` file in the root directory:
```env
# Database Configuration
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=mylost_db

# Optional Settings (with defaults)
COLLECTION_NAME=lost_items
RATE_LIMIT_COLLECTION=user_rate_limits
CACHE_TTL=300
MAX_POSTS_PER_DAY=2
```

### 3. Run the Server
```bash
# Development mode
python main.py

# Or with uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Verify Installation
Open your browser and go to:
- **API Health**: http://localhost:8000/api/v1/health
- **API Docs**: http://localhost:8000/docs
- **Root**: http://localhost:8000

## 🔧 Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MONGODB_URL` | MongoDB connection string | `mongodb://localhost:27017` | ✅ |
| `DATABASE_NAME` | Database name | `mylost_db` | ✅ |
| `COLLECTION_NAME` | Lost items collection | `lost_items` | ❌ |
| `RATE_LIMIT_COLLECTION` | Rate limiting collection | `user_rate_limits` | ❌ |
| `CACHE_TTL` | Cache time-to-live (seconds) | `300` | ❌ |
| `MAX_POSTS_PER_DAY` | Posts per device per day | `2` | ❌ |

### MongoDB Setup Options

#### MongoDB URL
```env
MONGODB_URL=your_mongodb_url

## 📖 Simple Usage

### 1. Create a Lost Item
```bash
curl -X POST "http://localhost:8000/api/v1/lost-items/" \
  -H "Content-Type: application/json" \
  -H "X-Device-ID: my-device-123" \
  -d '{
    "longitude": -74.006,
    "latitude": 40.7128,
    "image_url": "https://example.com/image.jpg",
    "description": "Lost black iPhone with blue case",
    "category": "electronics",
    "found_at_address": "Central Park, NY",
    "finder_info": {
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "+1234567890"
    }
  }'
```

### 2. Search for Items
```bash
# Get all items
curl "http://localhost:8000/api/v1/lost-items/"

# Search by category
curl "http://localhost:8000/api/v1/lost-items/?category=electronics"

# Search nearby (5km radius)
curl "http://localhost:8000/api/v1/lost-items/nearby/?latitude=40.7128&longitude=-74.006&radius=5"

# Text search
curl "http://localhost:8000/api/v1/lost-items/?search=iPhone"
```

### 3. Rate Limiting
Each device can post maximum **2 items per day**. Use different device identifiers:
```bash
# Headers for different devices
-H "X-Device-ID: device-123"
-H "X-Mac-Address: 00:1B:44:11:3A:B7"
-H "X-User-Agent: MyApp/1.0"
```

## 🏗️ Project Structure

```
my-lost-app/
├── main.py                 # FastAPI app and startup
├── requirements.txt        # Python dependencies
├── config/
│   └── settings.py        # Environment configuration
├── models/
│   └── lost_item.py       # Pydantic models
├── database/
│   └── mongodb.py         # Database connection
├── services/
│   ├── cache_service.py   # Memory caching
│   ├── rate_limit_service.py  # Rate limiting
│   └── lost_item_service.py   # Business logic
├── api/
│   └── routes/
│       ├── health.py      # Health check
│       └── lost_items.py  # Main API routes
└── docs/                  # Documentation
    ├── API_REQUESTS.md
    └── POSTMAN.md
```

## 🐳 Docker Setup (Optional)

### Using Docker Compose
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Docker Build
```bash
# Build image
docker build -t my-lost-app .

# Run container
docker run -p 8000:8000 \
  -e MONGODB_URL=mongodb://host.docker.internal:27017 \
  my-lost-app
```

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/lost-items/` | Create lost item |
| `GET` | `/api/v1/lost-items/` | Get items (with filters) |
| `GET` | `/api/v1/lost-items/{id}` | Get specific item |
| `GET` | `/api/v1/lost-items/nearby/` | Get nearby items |

### Available Filters
- **category**: Any string (case insensitive)
- **region**: `min_lat`, `max_lat`, `min_lng`, `max_lng`
- **search**: Text search in description/notes/address
- **pagination**: `limit` (max 100), `skip`

## 🧪 Testing

### Manual Testing
1. **Health Check**: http://localhost:8000/api/v1/health
2. **Create Item**: Use Postman or curl examples above
3. **View Docs**: http://localhost:8000/docs (Interactive API docs)

### Using Postman
Import the collection from `docs/POSTMAN.md` for comprehensive testing.

### Rate Limit Testing
```bash
# First post (success)
curl -X POST ... -H "X-Device-ID: test-device"

# Second post (success)  
curl -X POST ... -H "X-Device-ID: test-device"

# Third post (rate limited - 429 error)
curl -X POST ... -H "X-Device-ID: test-device"
```

## 🔍 Troubleshooting

### Common Issues

**1. MongoDB Connection Error**
```
Failed to connect to MongoDB
```
- Check if MongoDB is running
- Verify `MONGODB_URL` in `.env`
- For MongoDB Atlas, check network access and credentials

**2. Rate Limit Issues**
```
Daily post limit exceeded
```
- Use different device identifier
- Wait 24 hours for reset
- Check `MAX_POSTS_PER_DAY` setting

**3. Validation Errors**
```
422 Unprocessable Entity
```
- Check required fields in request body
- Verify latitude (-90 to 90) and longitude (-180 to 180)
- Ensure email format is valid

**4. Import Errors**
```
ModuleNotFoundError
```
- Run `pip install -r requirements.txt`
- Check Python version (3.8+ required)

### Debug Mode
Run with debug logging:
```bash
# Set log level
export LOG_LEVEL=DEBUG
python main.py
```

## 📈 Performance

- **Caching**: Responses cached for 5 minutes (configurable)
- **Database Indexing**: Optimized for geospatial and text queries  
- **Rate Limiting**: Prevents spam with daily limits
- **Pagination**: Efficient data loading with skip/limit

## 🔒 Security Features

- Input validation with Pydantic models
- Rate limiting per device
- MongoDB injection protection
- CORS configuration for web apps
- No sensitive data exposure in errors

## 📝 Example Categories

Categories are flexible strings (case insensitive):
- `electronics`, `mobile phone`, `laptop`
- `clothing`, `jacket`, `shoes`
- `accessories`, `glasses`, `watch`
- `documents`, `keys`, `wallet`
- `bags`, `jewelry`, `toys`
- Or any custom category you need!

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Documentation**: Check `/docs` endpoint when server is running
- **Issues**: Create GitHub issue with error details and logs
- **API Testing**: Use provided Postman collection

---

**Ready to help people find their lost items! 🎯**