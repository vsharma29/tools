/**
 * CryptoTrader Pro - Intraday Trading Assistant
 * Real-time cryptocurrency trading dashboard with technical analysis
 */

// ============================================
// Global State & Configuration
// ============================================
const state = {
    currentSymbol: 'BTCUSDT',
    currentTimeframe: '15m',
    candleData: [],
    chart: null,
    candleSeries: null,
    volumeSeries: null,
    indicators: {
        ema9Line: null,
        ema21Line: null,
        sma50Line: null,
        sma200Line: null,
        bbUpperLine: null,
        bbLowerLine: null
    },
    websockets: {
        kline: null,
        ticker: null,
        depth: null,
        trades: null
    },
    watchlist: ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT'],
    portfolio: [
        { symbol: 'BTC', amount: 0.5, avgPrice: 42000 },
        { symbol: 'ETH', amount: 2.0, avgPrice: 2500 },
        { symbol: 'SOL', amount: 10, avgPrice: 100 }
    ],
    alerts: [],
    prices: {},
    showVolume: true,
    tradeSide: 'buy',
    orderType: 'market',
    demoMode: false
};

// Demo data for when API is unavailable
const DEMO_PRICES = {
    BTCUSDT: { price: 98500, change: 2.34, high: 99200, low: 96800, volume: 1234567890 },
    ETHUSDT: { price: 3250, change: 1.85, high: 3320, low: 3180, volume: 567890123 },
    BNBUSDT: { price: 625, change: -0.45, high: 635, low: 618, volume: 123456789 },
    SOLUSDT: { price: 185, change: 4.21, high: 192, low: 178, volume: 234567890 },
    XRPUSDT: { price: 2.45, change: -1.23, high: 2.52, low: 2.38, volume: 345678901 },
    ADAUSDT: { price: 0.92, change: 0.87, high: 0.95, low: 0.89, volume: 156789012 },
    DOGEUSDT: { price: 0.38, change: 3.45, high: 0.40, low: 0.36, volume: 267890123 },
    DOTUSDT: { price: 8.75, change: -0.92, high: 8.95, low: 8.55, volume: 178901234 },
    MATICUSDT: { price: 1.15, change: 1.56, high: 1.20, low: 1.10, volume: 189012345 },
    LTCUSDT: { price: 105, change: 0.23, high: 108, low: 102, volume: 90123456 }
};

// Generate realistic demo candlestick data
const generateDemoCandles = (symbol, count = 500) => {
    const basePrice = DEMO_PRICES[symbol]?.price || 50000;
    const candles = [];
    const now = Math.floor(Date.now() / 1000);
    const interval = 15 * 60; // 15 minutes in seconds

    let price = basePrice * 0.95;

    for (let i = 0; i < count; i++) {
        const time = now - (count - i) * interval;
        const volatility = basePrice * 0.002;
        const trend = Math.sin(i / 50) * volatility;
        const random = (Math.random() - 0.5) * volatility * 2;

        const open = price;
        const change = trend + random;
        const close = open + change;
        const high = Math.max(open, close) + Math.random() * volatility;
        const low = Math.min(open, close) - Math.random() * volatility;
        const volume = basePrice * (1000 + Math.random() * 5000);

        candles.push({ time, open, high, low, close, volume });
        price = close;
    }

    return candles;
};

// Generate demo order book
const generateDemoOrderBook = (symbol) => {
    const basePrice = DEMO_PRICES[symbol]?.price || 50000;
    const asks = [];
    const bids = [];

    for (let i = 0; i < 10; i++) {
        const askPrice = basePrice * (1 + 0.0001 * (i + 1));
        const bidPrice = basePrice * (1 - 0.0001 * (i + 1));
        const amount = (Math.random() * 2 + 0.1).toFixed(4);

        asks.push([askPrice.toFixed(2), amount]);
        bids.push([bidPrice.toFixed(2), amount]);
    }

    return { asks, bids };
};

// Binance API endpoints
const BINANCE_REST = 'https://api.binance.com/api/v3';
const BINANCE_WS = 'wss://stream.binance.com:9443/ws';

// ============================================
// Utility Functions
// ============================================
const formatPrice = (price, decimals = 2) => {
    if (!price) return '--';
    const num = parseFloat(price);
    if (num >= 1000) return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (num >= 1) return num.toFixed(decimals);
    return num.toFixed(6);
};

const formatVolume = (volume) => {
    const num = parseFloat(volume);
    if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B';
    if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M';
    if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K';
    return num.toFixed(2);
};

const formatChange = (change) => {
    const num = parseFloat(change);
    const sign = num >= 0 ? '+' : '';
    return `${sign}${num.toFixed(2)}%`;
};

const getSymbolBase = (symbol) => symbol.replace('USDT', '');

// ============================================
// Technical Indicators
// ============================================
const TechnicalIndicators = {
    // Simple Moving Average
    SMA: (data, period) => {
        const result = [];
        for (let i = 0; i < data.length; i++) {
            if (i < period - 1) {
                result.push(null);
                continue;
            }
            let sum = 0;
            for (let j = 0; j < period; j++) {
                sum += data[i - j].close;
            }
            result.push(sum / period);
        }
        return result;
    },

    // Exponential Moving Average
    EMA: (data, period) => {
        const result = [];
        const multiplier = 2 / (period + 1);

        // First EMA is SMA
        let sum = 0;
        for (let i = 0; i < period; i++) {
            sum += data[i].close;
            result.push(null);
        }
        result[period - 1] = sum / period;

        // Calculate EMA
        for (let i = period; i < data.length; i++) {
            const ema = (data[i].close - result[i - 1]) * multiplier + result[i - 1];
            result.push(ema);
        }
        return result;
    },

    // Relative Strength Index
    RSI: (data, period = 14) => {
        const result = [];
        let gains = 0;
        let losses = 0;

        for (let i = 0; i < data.length; i++) {
            if (i === 0) {
                result.push(null);
                continue;
            }

            const change = data[i].close - data[i - 1].close;
            const gain = change > 0 ? change : 0;
            const loss = change < 0 ? Math.abs(change) : 0;

            if (i < period) {
                gains += gain;
                losses += loss;
                result.push(null);
                continue;
            }

            if (i === period) {
                gains = gains / period;
                losses = losses / period;
            } else {
                gains = (gains * (period - 1) + gain) / period;
                losses = (losses * (period - 1) + loss) / period;
            }

            const rs = losses === 0 ? 100 : gains / losses;
            const rsi = 100 - (100 / (1 + rs));
            result.push(rsi);
        }
        return result;
    },

    // MACD
    MACD: (data, fastPeriod = 12, slowPeriod = 26, signalPeriod = 9) => {
        const emaFast = TechnicalIndicators.EMA(data, fastPeriod);
        const emaSlow = TechnicalIndicators.EMA(data, slowPeriod);

        const macdLine = [];
        for (let i = 0; i < data.length; i++) {
            if (emaFast[i] === null || emaSlow[i] === null) {
                macdLine.push(null);
            } else {
                macdLine.push(emaFast[i] - emaSlow[i]);
            }
        }

        // Calculate signal line (EMA of MACD)
        const signalLine = [];
        const multiplier = 2 / (signalPeriod + 1);
        let firstValidIndex = macdLine.findIndex(v => v !== null);

        for (let i = 0; i < data.length; i++) {
            if (i < firstValidIndex + signalPeriod - 1) {
                signalLine.push(null);
                continue;
            }
            if (i === firstValidIndex + signalPeriod - 1) {
                let sum = 0;
                for (let j = 0; j < signalPeriod; j++) {
                    sum += macdLine[firstValidIndex + j];
                }
                signalLine.push(sum / signalPeriod);
                continue;
            }
            const signal = (macdLine[i] - signalLine[i - 1]) * multiplier + signalLine[i - 1];
            signalLine.push(signal);
        }

        // Calculate histogram
        const histogram = [];
        for (let i = 0; i < data.length; i++) {
            if (macdLine[i] === null || signalLine[i] === null) {
                histogram.push(null);
            } else {
                histogram.push(macdLine[i] - signalLine[i]);
            }
        }

        return { macdLine, signalLine, histogram };
    },

    // Bollinger Bands
    BollingerBands: (data, period = 20, stdDev = 2) => {
        const sma = TechnicalIndicators.SMA(data, period);
        const upper = [];
        const lower = [];
        const middle = sma;

        for (let i = 0; i < data.length; i++) {
            if (i < period - 1) {
                upper.push(null);
                lower.push(null);
                continue;
            }

            let sumSquaredDiff = 0;
            for (let j = 0; j < period; j++) {
                sumSquaredDiff += Math.pow(data[i - j].close - sma[i], 2);
            }
            const std = Math.sqrt(sumSquaredDiff / period);

            upper.push(sma[i] + stdDev * std);
            lower.push(sma[i] - stdDev * std);
        }

        return { upper, middle, lower };
    },

    // Stochastic Oscillator
    Stochastic: (data, kPeriod = 14, dPeriod = 3) => {
        const kValues = [];

        for (let i = 0; i < data.length; i++) {
            if (i < kPeriod - 1) {
                kValues.push(null);
                continue;
            }

            let highestHigh = -Infinity;
            let lowestLow = Infinity;

            for (let j = 0; j < kPeriod; j++) {
                highestHigh = Math.max(highestHigh, data[i - j].high);
                lowestLow = Math.min(lowestLow, data[i - j].low);
            }

            const k = ((data[i].close - lowestLow) / (highestHigh - lowestLow)) * 100;
            kValues.push(k);
        }

        // Calculate %D (SMA of %K)
        const dValues = [];
        for (let i = 0; i < data.length; i++) {
            if (i < kPeriod - 1 + dPeriod - 1) {
                dValues.push(null);
                continue;
            }
            let sum = 0;
            for (let j = 0; j < dPeriod; j++) {
                sum += kValues[i - j];
            }
            dValues.push(sum / dPeriod);
        }

        return { k: kValues, d: dValues };
    },

    // Average True Range
    ATR: (data, period = 14) => {
        const trueRanges = [];
        const atr = [];

        for (let i = 0; i < data.length; i++) {
            if (i === 0) {
                trueRanges.push(data[i].high - data[i].low);
                atr.push(null);
                continue;
            }

            const tr = Math.max(
                data[i].high - data[i].low,
                Math.abs(data[i].high - data[i - 1].close),
                Math.abs(data[i].low - data[i - 1].close)
            );
            trueRanges.push(tr);

            if (i < period - 1) {
                atr.push(null);
                continue;
            }

            if (i === period - 1) {
                let sum = 0;
                for (let j = 0; j < period; j++) {
                    sum += trueRanges[j];
                }
                atr.push(sum / period);
                continue;
            }

            const currentATR = (atr[i - 1] * (period - 1) + tr) / period;
            atr.push(currentATR);
        }

        return atr;
    }
};

// ============================================
// Chart Functions
// ============================================
const initChart = () => {
    const container = document.getElementById('chartContainer');

    state.chart = LightweightCharts.createChart(container, {
        width: container.clientWidth,
        height: container.clientHeight,
        layout: {
            background: { type: 'solid', color: '#0b0e11' },
            textColor: '#848e9c',
        },
        grid: {
            vertLines: { color: '#1e2329' },
            horzLines: { color: '#1e2329' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
            vertLine: {
                width: 1,
                color: '#505050',
                style: LightweightCharts.LineStyle.Dashed,
            },
            horzLine: {
                width: 1,
                color: '#505050',
                style: LightweightCharts.LineStyle.Dashed,
            },
        },
        rightPriceScale: {
            borderColor: '#2b3139',
            scaleMargins: {
                top: 0.1,
                bottom: 0.2,
            },
        },
        timeScale: {
            borderColor: '#2b3139',
            timeVisible: true,
            secondsVisible: false,
        },
    });

    // Candlestick series
    state.candleSeries = state.chart.addCandlestickSeries({
        upColor: '#0ecb81',
        downColor: '#f6465d',
        borderDownColor: '#f6465d',
        borderUpColor: '#0ecb81',
        wickDownColor: '#f6465d',
        wickUpColor: '#0ecb81',
    });

    // Volume series
    state.volumeSeries = state.chart.addHistogramSeries({
        color: '#26a69a',
        priceFormat: {
            type: 'volume',
        },
        priceScaleId: '',
        scaleMargins: {
            top: 0.8,
            bottom: 0,
        },
    });

    // Add indicator lines
    state.indicators.ema9Line = state.chart.addLineSeries({
        color: '#f0b90b',
        lineWidth: 1,
        title: 'EMA 9',
    });

    state.indicators.ema21Line = state.chart.addLineSeries({
        color: '#1e88e5',
        lineWidth: 1,
        title: 'EMA 21',
    });

    state.indicators.sma50Line = state.chart.addLineSeries({
        color: '#ab47bc',
        lineWidth: 1,
        title: 'SMA 50',
        visible: false,
    });

    state.indicators.sma200Line = state.chart.addLineSeries({
        color: '#ef5350',
        lineWidth: 1,
        title: 'SMA 200',
        visible: false,
    });

    // Bollinger Bands
    state.indicators.bbUpperLine = state.chart.addLineSeries({
        color: 'rgba(38, 166, 154, 0.5)',
        lineWidth: 1,
        lineStyle: LightweightCharts.LineStyle.Dashed,
    });

    state.indicators.bbLowerLine = state.chart.addLineSeries({
        color: 'rgba(38, 166, 154, 0.5)',
        lineWidth: 1,
        lineStyle: LightweightCharts.LineStyle.Dashed,
    });

    // Handle resize
    window.addEventListener('resize', () => {
        state.chart.applyOptions({
            width: container.clientWidth,
            height: container.clientHeight,
        });
    });

    // Crosshair subscription for real-time data display
    state.chart.subscribeCrosshairMove((param) => {
        if (!param.time) return;
        // Could update indicators display here based on crosshair position
    });
};

const updateChart = (data) => {
    if (!state.candleSeries) return;

    const candleData = data.map(d => ({
        time: d.time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
    }));

    const volumeData = data.map(d => ({
        time: d.time,
        value: d.volume,
        color: d.close >= d.open ? 'rgba(14, 203, 129, 0.5)' : 'rgba(246, 70, 93, 0.5)',
    }));

    state.candleSeries.setData(candleData);
    state.volumeSeries.setData(volumeData);

    // Update indicator lines
    updateIndicatorLines(data);
};

const updateIndicatorLines = (data) => {
    if (data.length < 200) return;

    const ema9 = TechnicalIndicators.EMA(data, 9);
    const ema21 = TechnicalIndicators.EMA(data, 21);
    const sma50 = TechnicalIndicators.SMA(data, 50);
    const sma200 = TechnicalIndicators.SMA(data, 200);
    const bb = TechnicalIndicators.BollingerBands(data, 20, 2);

    const formatLineData = (values, data) => {
        return values.map((v, i) => v !== null ? { time: data[i].time, value: v } : null).filter(d => d !== null);
    };

    state.indicators.ema9Line.setData(formatLineData(ema9, data));
    state.indicators.ema21Line.setData(formatLineData(ema21, data));
    state.indicators.sma50Line.setData(formatLineData(sma50, data));
    state.indicators.sma200Line.setData(formatLineData(sma200, data));
    state.indicators.bbUpperLine.setData(formatLineData(bb.upper, data));
    state.indicators.bbLowerLine.setData(formatLineData(bb.lower, data));
};

const addCandleToChart = (candle) => {
    if (!state.candleSeries) return;

    state.candleSeries.update({
        time: candle.time,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
    });

    state.volumeSeries.update({
        time: candle.time,
        value: candle.volume,
        color: candle.close >= candle.open ? 'rgba(14, 203, 129, 0.5)' : 'rgba(246, 70, 93, 0.5)',
    });
};

// ============================================
// API & WebSocket Functions
// ============================================
const fetchKlines = async (symbol, interval, limit = 500) => {
    if (state.demoMode) {
        return generateDemoCandles(symbol, limit);
    }
    try {
        const response = await fetch(`${BINANCE_REST}/klines?symbol=${symbol}&interval=${interval}&limit=${limit}`);
        if (!response.ok) throw new Error('API error');
        const data = await response.json();

        return data.map(k => ({
            time: Math.floor(k[0] / 1000),
            open: parseFloat(k[1]),
            high: parseFloat(k[2]),
            low: parseFloat(k[3]),
            close: parseFloat(k[4]),
            volume: parseFloat(k[5]),
        }));
    } catch (error) {
        console.error('Error fetching klines, switching to demo mode:', error);
        state.demoMode = true;
        showToast('warning', 'Demo Mode', 'Using simulated data - API unavailable');
        return generateDemoCandles(symbol, limit);
    }
};

const fetch24hTicker = async (symbol) => {
    if (state.demoMode) {
        const demo = DEMO_PRICES[symbol] || DEMO_PRICES.BTCUSDT;
        return {
            c: demo.price.toString(),
            P: demo.change.toString(),
            h: demo.high.toString(),
            l: demo.low.toString(),
            q: demo.volume.toString()
        };
    }
    try {
        const response = await fetch(`${BINANCE_REST}/ticker/24hr?symbol=${symbol}`);
        if (!response.ok) throw new Error('API error');
        return await response.json();
    } catch (error) {
        console.error('Error fetching ticker:', error);
        const demo = DEMO_PRICES[symbol] || DEMO_PRICES.BTCUSDT;
        return {
            c: demo.price.toString(),
            P: demo.change.toString(),
            h: demo.high.toString(),
            l: demo.low.toString(),
            q: demo.volume.toString()
        };
    }
};

const fetchOrderBook = async (symbol, limit = 10) => {
    if (state.demoMode) {
        return generateDemoOrderBook(symbol);
    }
    try {
        const response = await fetch(`${BINANCE_REST}/depth?symbol=${symbol}&limit=${limit}`);
        if (!response.ok) throw new Error('API error');
        return await response.json();
    } catch (error) {
        console.error('Error fetching order book:', error);
        return generateDemoOrderBook(symbol);
    }
};

const fetchRecentTrades = async (symbol, limit = 20) => {
    if (state.demoMode) {
        return generateDemoTrades(symbol, limit);
    }
    try {
        const response = await fetch(`${BINANCE_REST}/trades?symbol=${symbol}&limit=${limit}`);
        if (!response.ok) throw new Error('API error');
        return await response.json();
    } catch (error) {
        console.error('Error fetching trades:', error);
        return generateDemoTrades(symbol, limit);
    }
};

// Generate demo trades
const generateDemoTrades = (symbol, limit = 20) => {
    const basePrice = DEMO_PRICES[symbol]?.price || 50000;
    const trades = [];
    const now = Date.now();

    for (let i = 0; i < limit; i++) {
        trades.push({
            p: (basePrice * (1 + (Math.random() - 0.5) * 0.001)).toFixed(2),
            q: (Math.random() * 0.5 + 0.01).toFixed(4),
            T: now - i * 1000,
            m: Math.random() > 0.5
        });
    }
    return trades;
};

// Demo mode intervals
let demoIntervals = [];

const clearDemoIntervals = () => {
    demoIntervals.forEach(id => clearInterval(id));
    demoIntervals = [];
};

const startDemoUpdates = (symbol) => {
    clearDemoIntervals();

    // Simulate price updates every second
    demoIntervals.push(setInterval(() => {
        const demo = DEMO_PRICES[symbol] || DEMO_PRICES.BTCUSDT;
        const priceChange = (Math.random() - 0.5) * demo.price * 0.0005;
        demo.price += priceChange;

        updateTickerDisplay({
            c: demo.price.toString(),
            P: demo.change.toString(),
            h: demo.high.toString(),
            l: demo.low.toString(),
            q: demo.volume.toString()
        });

        // Update last candle
        if (state.candleData.length > 0) {
            const lastCandle = state.candleData[state.candleData.length - 1];
            lastCandle.close = demo.price;
            lastCandle.high = Math.max(lastCandle.high, demo.price);
            lastCandle.low = Math.min(lastCandle.low, demo.price);
            addCandleToChart(lastCandle);
        }

        checkAlerts(symbol, demo.price);
    }, 1000));

    // Simulate order book updates every 500ms
    demoIntervals.push(setInterval(() => {
        updateOrderBook(generateDemoOrderBook(symbol));
    }, 500));

    // Simulate trade updates every 300ms
    demoIntervals.push(setInterval(() => {
        const demo = DEMO_PRICES[symbol] || DEMO_PRICES.BTCUSDT;
        addRecentTrade({
            p: (demo.price * (1 + (Math.random() - 0.5) * 0.0002)).toFixed(2),
            q: (Math.random() * 0.3 + 0.01).toFixed(4),
            T: Date.now(),
            m: Math.random() > 0.5
        });
    }, 300));
};

const connectWebSocket = (symbol, timeframe) => {
    // Close existing connections
    Object.values(state.websockets).forEach(ws => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.close();
        }
    });
    clearDemoIntervals();

    // If in demo mode, use simulated updates
    if (state.demoMode) {
        startDemoUpdates(symbol);
        return;
    }

    const symbolLower = symbol.toLowerCase();

    // Kline WebSocket
    state.websockets.kline = new WebSocket(`${BINANCE_WS}/${symbolLower}@kline_${timeframe}`);
    state.websockets.kline.onerror = () => {
        console.log('WebSocket error, switching to demo mode');
        state.demoMode = true;
        showToast('warning', 'Demo Mode', 'Using simulated data - WebSocket unavailable');
        startDemoUpdates(symbol);
    };
    state.websockets.kline.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const kline = data.k;

        const candle = {
            time: Math.floor(kline.t / 1000),
            open: parseFloat(kline.o),
            high: parseFloat(kline.h),
            low: parseFloat(kline.l),
            close: parseFloat(kline.c),
            volume: parseFloat(kline.v),
        };

        // Update or add candle
        const lastCandle = state.candleData[state.candleData.length - 1];
        if (lastCandle && lastCandle.time === candle.time) {
            state.candleData[state.candleData.length - 1] = candle;
        } else if (kline.x) {
            state.candleData.push(candle);
            if (state.candleData.length > 500) {
                state.candleData.shift();
            }
        }

        addCandleToChart(candle);
        updateIndicatorsDisplay();
    };

    // Ticker WebSocket
    state.websockets.ticker = new WebSocket(`${BINANCE_WS}/${symbolLower}@ticker`);
    state.websockets.ticker.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateTickerDisplay(data);
        checkAlerts(symbol, parseFloat(data.c));
    };

    // Depth WebSocket
    state.websockets.depth = new WebSocket(`${BINANCE_WS}/${symbolLower}@depth10@100ms`);
    state.websockets.depth.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateOrderBook(data);
    };

    // Trades WebSocket
    state.websockets.trades = new WebSocket(`${BINANCE_WS}/${symbolLower}@trade`);
    state.websockets.trades.onmessage = (event) => {
        const data = JSON.parse(event.data);
        addRecentTrade(data);
    };
};

// ============================================
// UI Update Functions
// ============================================
const updateTickerDisplay = (ticker) => {
    const priceElement = document.querySelector('#currentPrice .price');
    const changeElement = document.querySelector('#currentPrice .change');
    const highElement = document.getElementById('highPrice');
    const lowElement = document.getElementById('lowPrice');
    const volumeElement = document.getElementById('volume');

    const price = parseFloat(ticker.c);
    const change = parseFloat(ticker.P);
    const previousPrice = state.prices[state.currentSymbol];

    // Flash animation
    if (previousPrice) {
        priceElement.classList.remove('price-up', 'price-down');
        if (price > previousPrice) {
            priceElement.classList.add('price-up');
        } else if (price < previousPrice) {
            priceElement.classList.add('price-down');
        }
    }

    state.prices[state.currentSymbol] = price;

    priceElement.textContent = '$' + formatPrice(price);
    changeElement.textContent = formatChange(change);
    changeElement.className = 'change ' + (change >= 0 ? 'positive' : 'negative');

    highElement.textContent = '$' + formatPrice(ticker.h);
    lowElement.textContent = '$' + formatPrice(ticker.l);
    volumeElement.textContent = formatVolume(ticker.q) + ' USDT';

    // Update time
    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();

    // Update trade button
    const submitBtn = document.getElementById('submitTrade');
    const base = getSymbolBase(state.currentSymbol);
    submitBtn.textContent = `${state.tradeSide === 'buy' ? 'Buy' : 'Sell'} ${base}`;
};

const updateOrderBook = (depth) => {
    const asksContainer = document.getElementById('orderbookAsks');
    const bidsContainer = document.getElementById('orderbookBids');
    const spreadElement = document.getElementById('orderbookSpread');

    // Calculate totals for depth visualization
    let askTotal = 0;
    let bidTotal = 0;
    depth.asks.slice(0, 8).forEach(a => askTotal += parseFloat(a[1]));
    depth.bids.slice(0, 8).forEach(b => bidTotal += parseFloat(b[1]));

    // Render asks (reversed for display)
    let asksHTML = '';
    let runningAskTotal = 0;
    depth.asks.slice(0, 8).reverse().forEach(ask => {
        runningAskTotal += parseFloat(ask[1]);
        const percent = (runningAskTotal / askTotal) * 100;
        asksHTML += `
            <div class="orderbook-row" style="--depth: ${percent}%;">
                <span class="price">${formatPrice(ask[0])}</span>
                <span>${parseFloat(ask[1]).toFixed(4)}</span>
                <span>${formatPrice(runningAskTotal * parseFloat(ask[0]))}</span>
            </div>
        `;
    });
    asksContainer.innerHTML = asksHTML;

    // Render bids
    let bidsHTML = '';
    let runningBidTotal = 0;
    depth.bids.slice(0, 8).forEach(bid => {
        runningBidTotal += parseFloat(bid[1]);
        const percent = (runningBidTotal / bidTotal) * 100;
        bidsHTML += `
            <div class="orderbook-row" style="--depth: ${percent}%;">
                <span class="price">${formatPrice(bid[0])}</span>
                <span>${parseFloat(bid[1]).toFixed(4)}</span>
                <span>${formatPrice(runningBidTotal * parseFloat(bid[0]))}</span>
            </div>
        `;
    });
    bidsContainer.innerHTML = bidsHTML;

    // Update spread
    if (depth.asks.length && depth.bids.length) {
        const bestAsk = parseFloat(depth.asks[0][0]);
        const bestBid = parseFloat(depth.bids[0][0]);
        const spread = bestAsk - bestBid;
        const spreadPercent = (spread / bestAsk) * 100;

        spreadElement.innerHTML = `
            <span class="spread-price">$${formatPrice((bestAsk + bestBid) / 2)}</span>
            <span class="spread-percent">Spread: ${spread.toFixed(2)} (${spreadPercent.toFixed(3)}%)</span>
        `;
    }
};

const recentTrades = [];
const addRecentTrade = (trade) => {
    recentTrades.unshift({
        price: parseFloat(trade.p),
        amount: parseFloat(trade.q),
        time: new Date(trade.T).toLocaleTimeString(),
        isBuy: trade.m === false,
    });

    if (recentTrades.length > 50) {
        recentTrades.pop();
    }

    renderRecentTrades();
};

const renderRecentTrades = () => {
    const container = document.getElementById('tradesList');
    container.innerHTML = recentTrades.slice(0, 20).map(trade => `
        <div class="trade-row ${trade.isBuy ? 'buy' : 'sell'}">
            <span class="price">${formatPrice(trade.price)}</span>
            <span>${trade.amount.toFixed(4)}</span>
            <span class="time">${trade.time}</span>
        </div>
    `).join('');
};

const updateIndicatorsDisplay = () => {
    if (state.candleData.length < 200) return;

    const data = state.candleData;
    const currentPrice = data[data.length - 1].close;

    // RSI
    const rsi = TechnicalIndicators.RSI(data, 14);
    const currentRSI = rsi[rsi.length - 1];
    const rsiValue = document.getElementById('rsiValue');
    const rsiFill = document.getElementById('rsiFill');
    const rsiSignal = document.getElementById('rsiSignal');

    if (currentRSI) {
        rsiValue.textContent = currentRSI.toFixed(2);
        rsiFill.style.width = `${currentRSI}%`;

        if (currentRSI > 70) {
            rsiSignal.textContent = 'Overbought';
            rsiSignal.className = 'indicator-signal sell';
        } else if (currentRSI < 30) {
            rsiSignal.textContent = 'Oversold';
            rsiSignal.className = 'indicator-signal buy';
        } else {
            rsiSignal.textContent = 'Neutral';
            rsiSignal.className = 'indicator-signal neutral';
        }
    }

    // MACD
    const macd = TechnicalIndicators.MACD(data);
    const currentMACD = macd.macdLine[macd.macdLine.length - 1];
    const currentSignal = macd.signalLine[macd.signalLine.length - 1];
    const currentHistogram = macd.histogram[macd.histogram.length - 1];

    const macdValue = document.getElementById('macdValue');
    const macdSignalLine = document.getElementById('macdSignalLine');
    const macdSignalEl = document.getElementById('macdSignal');

    if (currentMACD) {
        macdValue.textContent = currentMACD.toFixed(4);
        macdSignalLine.textContent = currentSignal?.toFixed(4) || '--';

        if (currentHistogram > 0) {
            macdSignalEl.textContent = 'Bullish';
            macdSignalEl.className = 'indicator-signal buy';
        } else {
            macdSignalEl.textContent = 'Bearish';
            macdSignalEl.className = 'indicator-signal sell';
        }
    }

    // Render MACD histogram
    const histogramContainer = document.getElementById('macdHistogram');
    const recentHistogram = macd.histogram.slice(-20).filter(h => h !== null);
    const maxHist = Math.max(...recentHistogram.map(Math.abs));
    histogramContainer.innerHTML = recentHistogram.map(h => {
        const height = Math.abs(h) / maxHist * 100;
        const color = h >= 0 ? 'var(--success)' : 'var(--danger)';
        return `<div style="height: ${height}%; background: ${color}; flex: 1;"></div>`;
    }).join('');

    // Bollinger Bands
    const bb = TechnicalIndicators.BollingerBands(data, 20, 2);
    const bbUpper = bb.upper[bb.upper.length - 1];
    const bbMiddle = bb.middle[bb.middle.length - 1];
    const bbLower = bb.lower[bb.lower.length - 1];

    document.getElementById('bbUpper').textContent = '$' + formatPrice(bbUpper);
    document.getElementById('bbMiddle').textContent = '$' + formatPrice(bbMiddle);
    document.getElementById('bbLower').textContent = '$' + formatPrice(bbLower);

    const bbSignal = document.getElementById('bbSignal');
    if (currentPrice > bbUpper) {
        bbSignal.textContent = 'Above Upper';
        bbSignal.className = 'indicator-signal sell';
    } else if (currentPrice < bbLower) {
        bbSignal.textContent = 'Below Lower';
        bbSignal.className = 'indicator-signal buy';
    } else {
        bbSignal.textContent = 'In Range';
        bbSignal.className = 'indicator-signal neutral';
    }

    // Moving Averages
    const ema9 = TechnicalIndicators.EMA(data, 9);
    const ema21 = TechnicalIndicators.EMA(data, 21);
    const sma50 = TechnicalIndicators.SMA(data, 50);
    const sma200 = TechnicalIndicators.SMA(data, 200);

    document.getElementById('ema9').textContent = '$' + formatPrice(ema9[ema9.length - 1]);
    document.getElementById('ema21').textContent = '$' + formatPrice(ema21[ema21.length - 1]);
    document.getElementById('sma50').textContent = '$' + formatPrice(sma50[sma50.length - 1]);
    document.getElementById('sma200').textContent = '$' + formatPrice(sma200[sma200.length - 1]);

    const maSignal = document.getElementById('maSignal');
    const currentEma9 = ema9[ema9.length - 1];
    const currentEma21 = ema21[ema21.length - 1];
    const currentSma50 = sma50[sma50.length - 1];

    if (currentEma9 > currentEma21 && currentPrice > currentSma50) {
        maSignal.textContent = 'Bullish';
        maSignal.className = 'indicator-signal buy';
    } else if (currentEma9 < currentEma21 && currentPrice < currentSma50) {
        maSignal.textContent = 'Bearish';
        maSignal.className = 'indicator-signal sell';
    } else {
        maSignal.textContent = 'Mixed';
        maSignal.className = 'indicator-signal neutral';
    }

    // Stochastic
    const stoch = TechnicalIndicators.Stochastic(data, 14, 3);
    const currentK = stoch.k[stoch.k.length - 1];

    const stochValue = document.getElementById('stochValue');
    const stochFill = document.getElementById('stochFill');
    const stochSignal = document.getElementById('stochSignal');

    if (currentK) {
        stochValue.textContent = currentK.toFixed(2);
        stochFill.style.width = `${currentK}%`;

        if (currentK > 80) {
            stochSignal.textContent = 'Overbought';
            stochSignal.className = 'indicator-signal sell';
        } else if (currentK < 20) {
            stochSignal.textContent = 'Oversold';
            stochSignal.className = 'indicator-signal buy';
        } else {
            stochSignal.textContent = 'Neutral';
            stochSignal.className = 'indicator-signal neutral';
        }
    }

    // ATR
    const atr = TechnicalIndicators.ATR(data, 14);
    const currentATR = atr[atr.length - 1];

    document.getElementById('atrValue').textContent = '$' + formatPrice(currentATR);

    const volatilityPercent = (currentATR / currentPrice) * 100;
    document.getElementById('atrVolatility').textContent = volatilityPercent.toFixed(2) + '%';
    document.getElementById('atrStopLoss').textContent = '$' + formatPrice(currentPrice - (currentATR * 2));

    const atrSignal = document.getElementById('atrSignal');
    if (volatilityPercent > 5) {
        atrSignal.textContent = 'High Vol';
        atrSignal.className = 'indicator-signal sell';
    } else if (volatilityPercent < 2) {
        atrSignal.textContent = 'Low Vol';
        atrSignal.className = 'indicator-signal buy';
    } else {
        atrSignal.textContent = 'Normal';
        atrSignal.className = 'indicator-signal neutral';
    }

    // Update overall signals
    updateTradingSignals({
        rsi: currentRSI,
        macdHistogram: currentHistogram,
        bbPosition: currentPrice > bbUpper ? 'above' : currentPrice < bbLower ? 'below' : 'in',
        emaPosition: currentEma9 > currentEma21 ? 'bullish' : 'bearish',
        priceVsSMA50: currentPrice > currentSma50 ? 'above' : 'below',
        priceVsSMA200: sma200[sma200.length - 1] ? (currentPrice > sma200[sma200.length - 1] ? 'above' : 'below') : null,
        stochK: currentK,
    });
};

const updateTradingSignals = (indicators) => {
    let buyCount = 0;
    let sellCount = 0;
    let neutralCount = 0;

    // RSI
    if (indicators.rsi < 30) buyCount++;
    else if (indicators.rsi > 70) sellCount++;
    else neutralCount++;

    // MACD
    if (indicators.macdHistogram > 0) buyCount++;
    else if (indicators.macdHistogram < 0) sellCount++;
    else neutralCount++;

    // Bollinger Bands
    if (indicators.bbPosition === 'below') buyCount++;
    else if (indicators.bbPosition === 'above') sellCount++;
    else neutralCount++;

    // EMA Cross
    if (indicators.emaPosition === 'bullish') buyCount++;
    else sellCount++;

    // Price vs SMA 50
    if (indicators.priceVsSMA50 === 'above') buyCount++;
    else sellCount++;

    // Price vs SMA 200
    if (indicators.priceVsSMA200 === 'above') buyCount++;
    else if (indicators.priceVsSMA200 === 'below') sellCount++;

    // Stochastic
    if (indicators.stochK < 20) buyCount++;
    else if (indicators.stochK > 80) sellCount++;
    else neutralCount++;

    // Update counts
    document.getElementById('buyCount').textContent = buyCount;
    document.getElementById('sellCount').textContent = sellCount;
    document.getElementById('neutralCount').textContent = neutralCount;

    // Calculate overall signal
    const total = buyCount + sellCount + neutralCount;
    const signalScore = ((buyCount - sellCount) / total + 1) / 2 * 100;

    // Update gauge
    const needle = document.getElementById('gaugeNeedle');
    needle.style.left = `${signalScore}%`;

    // Update recommendation
    const recommendation = document.getElementById('signalRecommendation');
    const recValue = recommendation.querySelector('.recommendation-value');
    const recConfidence = recommendation.querySelector('.recommendation-confidence');

    const netSignal = buyCount - sellCount;
    const confidence = Math.abs(netSignal) / total * 100;

    if (netSignal >= 3) {
        recValue.textContent = 'STRONG BUY';
        recValue.className = 'recommendation-value buy';
    } else if (netSignal >= 1) {
        recValue.textContent = 'BUY';
        recValue.className = 'recommendation-value buy';
    } else if (netSignal <= -3) {
        recValue.textContent = 'STRONG SELL';
        recValue.className = 'recommendation-value sell';
    } else if (netSignal <= -1) {
        recValue.textContent = 'SELL';
        recValue.className = 'recommendation-value sell';
    } else {
        recValue.textContent = 'NEUTRAL';
        recValue.className = 'recommendation-value neutral';
    }

    recConfidence.textContent = `Confidence: ${confidence.toFixed(0)}%`;
};

// ============================================
// Watchlist Functions
// ============================================
const loadWatchlist = async () => {
    const container = document.getElementById('watchlist');
    container.innerHTML = '<div class="loading"></div>';

    const watchlistData = await Promise.all(
        state.watchlist.map(symbol => fetch24hTicker(symbol))
    );

    container.innerHTML = watchlistData.map((ticker, index) => {
        if (!ticker) return '';
        const symbol = state.watchlist[index];
        const change = parseFloat(ticker.P);
        const isActive = symbol === state.currentSymbol;

        return `
            <div class="watchlist-item ${isActive ? 'active' : ''}" data-symbol="${symbol}">
                <span class="symbol">${getSymbolBase(symbol)}/USDT</span>
                <div class="price-info">
                    <span class="price">$${formatPrice(ticker.c)}</span>
                    <span class="change ${change >= 0 ? 'positive' : 'negative'}">${formatChange(change)}</span>
                </div>
            </div>
        `;
    }).join('');

    // Add click handlers
    container.querySelectorAll('.watchlist-item').forEach(item => {
        item.addEventListener('click', () => {
            const symbol = item.dataset.symbol;
            switchSymbol(symbol);
        });
    });

    // Update watchlist prices periodically
    setInterval(updateWatchlistPrices, 5000);
};

const updateWatchlistPrices = async () => {
    const items = document.querySelectorAll('.watchlist-item');

    for (const item of items) {
        const symbol = item.dataset.symbol;
        const ticker = await fetch24hTicker(symbol);

        if (ticker) {
            const change = parseFloat(ticker.P);
            item.querySelector('.price').textContent = '$' + formatPrice(ticker.c);
            const changeEl = item.querySelector('.change');
            changeEl.textContent = formatChange(change);
            changeEl.className = `change ${change >= 0 ? 'positive' : 'negative'}`;
        }
    }
};

// ============================================
// Portfolio Functions
// ============================================
const updatePortfolio = async () => {
    const container = document.getElementById('portfolioList');
    let totalValue = 0;
    let totalPnl = 0;

    const portfolioHTML = await Promise.all(state.portfolio.map(async (asset) => {
        const ticker = await fetch24hTicker(asset.symbol + 'USDT');
        if (!ticker) return '';

        const currentPrice = parseFloat(ticker.c);
        const value = asset.amount * currentPrice;
        const costBasis = asset.amount * asset.avgPrice;
        const pnl = value - costBasis;
        const pnlPercent = (pnl / costBasis) * 100;

        totalValue += value;
        totalPnl += pnl;

        return `
            <div class="portfolio-item">
                <div class="asset-info">
                    <div class="asset-icon">${asset.symbol.substring(0, 2)}</div>
                    <div>
                        <div class="asset-name">${asset.symbol}</div>
                        <div class="asset-amount">${asset.amount} ${asset.symbol}</div>
                    </div>
                </div>
                <div class="asset-value">
                    <div class="value-usd">$${formatPrice(value)}</div>
                    <div class="value-change ${pnl >= 0 ? 'positive' : 'negative'}">${formatChange(pnlPercent)}</div>
                </div>
            </div>
        `;
    }));

    container.innerHTML = portfolioHTML.join('');

    // Update totals
    document.getElementById('portfolioTotal').textContent = '$' + formatPrice(totalValue);
    const pnlElement = document.getElementById('portfolioPnl');
    pnlElement.textContent = (totalPnl >= 0 ? '+$' : '-$') + formatPrice(Math.abs(totalPnl));
    pnlElement.className = `value ${totalPnl >= 0 ? 'positive' : 'negative'}`;
};

// ============================================
// Alerts Functions
// ============================================
const checkAlerts = (symbol, price) => {
    state.alerts.forEach((alert, index) => {
        if (alert.symbol !== symbol || alert.triggered) return;

        let triggered = false;
        if (alert.condition === 'above' && price >= alert.price) {
            triggered = true;
        } else if (alert.condition === 'below' && price <= alert.price) {
            triggered = true;
        } else if (alert.condition === 'cross') {
            const previousPrice = state.prices[symbol];
            if (previousPrice && ((previousPrice < alert.price && price >= alert.price) ||
                (previousPrice > alert.price && price <= alert.price))) {
                triggered = true;
            }
        }

        if (triggered) {
            state.alerts[index].triggered = true;
            showToast('success', 'Alert Triggered!',
                `${getSymbolBase(symbol)} ${alert.condition} $${formatPrice(alert.price)}`);

            if (alert.sound) {
                playAlertSound();
            }

            renderAlerts();
        }
    });
};

const renderAlerts = () => {
    const container = document.getElementById('alertsList');

    const activeAlerts = state.alerts.filter(a => !a.triggered);

    if (activeAlerts.length === 0) {
        container.innerHTML = '<div class="no-alerts">No active alerts</div>';
        return;
    }

    container.innerHTML = activeAlerts.map((alert, index) => `
        <div class="alert-item">
            <div class="alert-info">
                <span class="alert-symbol">${getSymbolBase(alert.symbol)}</span>
                <span class="alert-condition">${alert.condition} $${formatPrice(alert.price)}</span>
            </div>
            <button class="alert-delete" data-index="${index}">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `).join('');

    container.querySelectorAll('.alert-delete').forEach(btn => {
        btn.addEventListener('click', () => {
            const index = parseInt(btn.dataset.index);
            state.alerts.splice(index, 1);
            renderAlerts();
        });
    });
};

const playAlertSound = () => {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    oscillator.frequency.value = 800;
    oscillator.type = 'sine';
    gainNode.gain.value = 0.3;

    oscillator.start();
    oscillator.stop(audioContext.currentTime + 0.3);
};

// ============================================
// Toast Notifications
// ============================================
const showToast = (type, title, message) => {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: 'fa-check-circle',
        warning: 'fa-exclamation-triangle',
        error: 'fa-times-circle'
    };

    toast.innerHTML = `
        <i class="fas ${icons[type]} toast-icon"></i>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close"><i class="fas fa-times"></i></button>
    `;

    container.appendChild(toast);

    toast.querySelector('.toast-close').addEventListener('click', () => {
        toast.remove();
    });

    setTimeout(() => {
        toast.remove();
    }, 5000);
};

// ============================================
// Event Handlers
// ============================================
const switchSymbol = async (symbol) => {
    state.currentSymbol = symbol;

    // Update UI
    document.getElementById('symbolSelect').value = symbol;
    document.querySelectorAll('.watchlist-item').forEach(item => {
        item.classList.toggle('active', item.dataset.symbol === symbol);
    });

    // Fetch new data
    state.candleData = await fetchKlines(symbol, state.currentTimeframe);
    updateChart(state.candleData);
    updateIndicatorsDisplay();

    // Reconnect WebSocket
    connectWebSocket(symbol, state.currentTimeframe);
};

const switchTimeframe = async (timeframe) => {
    state.currentTimeframe = timeframe;

    // Update UI
    document.querySelectorAll('.tf-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tf === timeframe);
    });

    // Fetch new data
    state.candleData = await fetchKlines(state.currentSymbol, timeframe);
    updateChart(state.candleData);
    updateIndicatorsDisplay();

    // Reconnect WebSocket
    connectWebSocket(state.currentSymbol, timeframe);
};

const setupEventListeners = () => {
    // Symbol selector
    document.getElementById('symbolSelect').addEventListener('change', (e) => {
        switchSymbol(e.target.value);
    });

    // Timeframe buttons
    document.querySelectorAll('.tf-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            switchTimeframe(btn.dataset.tf);
        });
    });

    // Trade tabs
    document.querySelectorAll('.trade-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.trade-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            state.tradeSide = tab.dataset.side;

            const submitBtn = document.getElementById('submitTrade');
            submitBtn.className = `trade-submit-btn ${state.tradeSide}-btn`;
            submitBtn.textContent = `${state.tradeSide === 'buy' ? 'Buy' : 'Sell'} ${getSymbolBase(state.currentSymbol)}`;
        });
    });

    // Order type buttons
    document.querySelectorAll('.type-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.orderType = btn.dataset.type;

            const limitPriceGroup = document.getElementById('limitPriceGroup');
            limitPriceGroup.style.display = state.orderType === 'limit' || state.orderType === 'stop' ? 'block' : 'none';
        });
    });

    // Amount percentage buttons
    document.querySelectorAll('.amount-buttons button').forEach(btn => {
        btn.addEventListener('click', () => {
            const percent = parseInt(btn.dataset.percent);
            // Simulated balance
            const balance = 10000;
            const amount = (balance * percent / 100) / state.prices[state.currentSymbol];
            document.getElementById('tradeAmount').value = amount.toFixed(6);
            updateTradeTotal();
        });
    });

    // Trade amount input
    document.getElementById('tradeAmount').addEventListener('input', updateTradeTotal);

    // Submit trade
    document.getElementById('submitTrade').addEventListener('click', () => {
        const amount = parseFloat(document.getElementById('tradeAmount').value);
        if (!amount || amount <= 0) {
            showToast('error', 'Invalid Amount', 'Please enter a valid amount');
            return;
        }

        showToast('success', 'Order Placed',
            `${state.tradeSide.toUpperCase()} ${amount.toFixed(6)} ${getSymbolBase(state.currentSymbol)} at market price`);
        document.getElementById('tradeAmount').value = '';
        document.getElementById('tradeTotal').value = '';
    });

    // Alert modal
    document.getElementById('addAlertBtn').addEventListener('click', () => {
        document.getElementById('alertModal').classList.add('active');
        document.getElementById('alertSymbol').value = state.currentSymbol;
        document.getElementById('alertPrice').value = state.prices[state.currentSymbol]?.toFixed(2) || '';
    });

    document.querySelectorAll('.modal-close, .modal-cancel').forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('alertModal').classList.remove('active');
        });
    });

    document.getElementById('createAlert').addEventListener('click', () => {
        const symbol = document.getElementById('alertSymbol').value;
        const condition = document.getElementById('alertCondition').value;
        const price = parseFloat(document.getElementById('alertPrice').value);
        const sound = document.getElementById('alertSound').checked;

        if (!price || price <= 0) {
            showToast('error', 'Invalid Price', 'Please enter a valid price');
            return;
        }

        state.alerts.push({ symbol, condition, price, sound, triggered: false });
        renderAlerts();
        document.getElementById('alertModal').classList.remove('active');
        showToast('success', 'Alert Created', `${getSymbolBase(symbol)} ${condition} $${formatPrice(price)}`);
    });

    // Volume toggle
    document.getElementById('toggleVolume').addEventListener('click', () => {
        state.showVolume = !state.showVolume;
        state.volumeSeries.applyOptions({ visible: state.showVolume });
        document.getElementById('toggleVolume').classList.toggle('active', state.showVolume);
    });

    // Theme toggle
    document.getElementById('themeToggle').addEventListener('click', () => {
        const currentTheme = document.body.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        document.body.setAttribute('data-theme', newTheme);

        const icon = document.querySelector('#themeToggle i');
        icon.className = newTheme === 'light' ? 'fas fa-sun' : 'fas fa-moon';

        // Update chart theme
        if (state.chart) {
            state.chart.applyOptions({
                layout: {
                    background: { type: 'solid', color: newTheme === 'light' ? '#ffffff' : '#0b0e11' },
                    textColor: newTheme === 'light' ? '#1e2329' : '#848e9c',
                },
                grid: {
                    vertLines: { color: newTheme === 'light' ? '#e0e0e0' : '#1e2329' },
                    horzLines: { color: newTheme === 'light' ? '#e0e0e0' : '#1e2329' },
                },
            });
        }
    });

    // Screenshot
    document.getElementById('screenshotBtn').addEventListener('click', () => {
        if (state.chart) {
            const canvas = document.querySelector('#chartContainer canvas');
            if (canvas) {
                const link = document.createElement('a');
                link.download = `${state.currentSymbol}_${state.currentTimeframe}_${Date.now()}.png`;
                link.href = canvas.toDataURL();
                link.click();
                showToast('success', 'Screenshot Saved', 'Chart screenshot downloaded');
            }
        }
    });
};

const updateTradeTotal = () => {
    const amount = parseFloat(document.getElementById('tradeAmount').value) || 0;
    const price = state.prices[state.currentSymbol] || 0;
    const total = amount * price;
    document.getElementById('tradeTotal').value = total.toFixed(2);

    const fee = total * 0.001; // 0.1% fee
    document.getElementById('tradeFee').textContent = fee.toFixed(4) + ' USDT';
};

// ============================================
// Initialization
// ============================================
const init = async () => {
    console.log('Initializing CryptoTrader Pro...');

    // Initialize chart
    initChart();

    // Load initial data
    state.candleData = await fetchKlines(state.currentSymbol, state.currentTimeframe);
    updateChart(state.candleData);

    // Connect WebSocket
    connectWebSocket(state.currentSymbol, state.currentTimeframe);

    // Load watchlist
    await loadWatchlist();

    // Load portfolio
    await updatePortfolio();

    // Update indicators
    updateIndicatorsDisplay();

    // Setup event listeners
    setupEventListeners();

    // Periodic portfolio update
    setInterval(updatePortfolio, 60000);

    console.log('CryptoTrader Pro initialized successfully!');
};

// Start the application
document.addEventListener('DOMContentLoaded', init);
