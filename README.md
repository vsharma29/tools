# CryptoTrader Pro - Intraday Trading Assistant

A real-time cryptocurrency trading dashboard with technical analysis, live market data, and trading signals.

![CryptoTrader Pro](https://img.shields.io/badge/CryptoTrader-Pro-gold)
![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

### Real-Time Market Data
- Live price updates via Binance WebSocket API
- 24h statistics: high, low, volume, price change
- Support for 10+ major cryptocurrencies (BTC, ETH, BNB, SOL, XRP, ADA, DOGE, DOT, MATIC, LTC)

### Interactive Charts
- Professional candlestick charts using TradingView Lightweight Charts
- Multiple timeframes: 1m, 5m, 15m, 1h, 4h, 1d
- Overlay indicators: EMA 9/21, SMA 50/200, Bollinger Bands
- Volume histogram (toggleable)
- Chart screenshot export

### Technical Indicators
- **RSI (14)** - Relative Strength Index with overbought/oversold zones
- **MACD** - Moving Average Convergence Divergence with histogram
- **Bollinger Bands** (20, 2) - Volatility bands
- **Stochastic Oscillator** (14, 3, 3) - Momentum indicator
- **ATR (14)** - Average True Range with volatility % and stop-loss suggestions
- **Moving Averages** - EMA 9/21, SMA 50/200

### Trading Signals
- Aggregate signal meter (Strong Buy to Strong Sell)
- Individual indicator signals
- Buy/Neutral/Sell counts
- Confidence percentage

### Order Book & Trades
- Live order book with depth visualization
- Real-time trades stream with buy/sell coloring
- Bid-ask spread indicator

### Portfolio & Alerts
- Watchlist with live price updates
- Portfolio tracker with P&L calculations
- Price alerts with sound notifications

### Trading Interface
- Market/Limit/Stop order types
- Percentage-based position sizing
- Fee estimation

### Additional Features
- Dark/Light theme toggle
- Demo mode (works without API)
- Responsive design
- Screenshot export

## Quick Start

### Option 1: Open Directly
Simply open `index.html` in your web browser.

### Option 2: Local Server
```bash
# Using Python
python3 -m http.server 8080

# Using Node.js
npx serve .

# Using live-server (with auto-reload)
npx live-server --port=3000
```

Then open http://localhost:8080 (or 3000)

## Deployment

### Deploy to Vercel
```bash
npx vercel --prod
```

### Deploy to Surge.sh
```bash
npx surge . your-domain.surge.sh
```

### Deploy to Netlify
1. Push to GitHub
2. Connect repository on Netlify
3. Deploy with default settings

### Deploy to GitHub Pages
1. Go to repository Settings > Pages
2. Select branch and root folder
3. Save and wait for deployment

## Demo Mode

The app automatically switches to demo mode when:
- Binance API is unreachable
- WebSocket connection fails
- Running in restricted environments

Demo mode provides:
- Simulated candlestick data
- Live price updates
- Order book simulation
- Trade stream simulation

## Technologies

- **Charts**: TradingView Lightweight Charts
- **Data**: Binance REST API & WebSocket
- **Icons**: Font Awesome
- **Styling**: Custom CSS with CSS Variables

## API Usage

The app uses Binance's free public API endpoints:
- REST API for historical data
- WebSocket for real-time updates
- No API key required

## Browser Support

- Chrome (recommended)
- Firefox
- Safari
- Edge

## License

MIT License - feel free to use and modify for your projects.
