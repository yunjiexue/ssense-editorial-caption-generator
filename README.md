# SSENSE Editorial Caption Generator

A powerful tool for generating editorial captions for SSENSE products in multiple languages.

## Features
- Multilingual caption generation
- MongoDB integration for data persistence
- Multiple caption templates
- User-friendly web interface
- Real-time product data fetching

## Setup

### Prerequisites
- Python 3.13.3 or higher
- MongoDB installed and running
- Required Python packages (install via pip):
  ```
  pip3 install -r requirements.txt
  ```

### Environment Variables
Create a `.env` file in the project root with:
```
MONGODB_URI=your_mongodb_connection_string
PORT=8080
```

## Usage
1. Start the application:
   ```
   python3 app.py
   ```
2. Open your browser and navigate to `http://localhost:8080`
3. Enter the SSENSE product URL
4. Click "Generate Captions in All Languages"
5. View and copy the generated captions

## Database Structure
The application uses MongoDB to store:
- Product information
- Generated captions
- Template configurations

## Contributing
Feel free to submit issues and enhancement requests.
