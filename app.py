import streamlit as st
import yfinance as yf
from datetime import datetime
import pandas as pd
import json
import gspread
import time
from google.oauth2.service_account import Credentials

# ============================================
# הגדרות ראשוניות
# ============================================

st.set_page_config(
    page_title="בורסת הכיתה",
    page_icon="📈",
    layout="wide"
)

# הגדרת כיווניות מימין לשמאל (RTL) לעברית
st.markdown("""
<style>
    .stApp { direction: rtl; }
    h1, h2, h3, h4, h5, h6 { text-align: right !important; direction: rtl !important; }
    .stMarkdown, .stText { text-align: right; }
    .stButton > button { direction: rtl; }
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > div { text-align: right; direction: rtl; }
    .stDataFrame { direction: rtl; }
    [data-testid="stMetricLabel"] { text-align: right !important; direction: rtl !important; }
    [data-testid="stMetricValue"] { direction: ltr !important; text-align: right !important; display: block !important; }
    [data-testid="stMetricDelta"] { direction: ltr !important; text-align: right !important; }
    [data-testid="column"] { text-align: right; }
    .stAlert { direction: rtl; text-align: right; }
</style>
""", unsafe_allow_html=True)

# ============================================
# פונקציות עזר
# ============================================

def init_session_state():
    """אתחול משתני session"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'portfolios' not in st.session_state:
        st.session_state.portfolios = load_portfolios()

def get_google_sheet():
    """התחברות ל-Google Sheets"""
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open("בורסת הכיתה - נתונים")
        sheet = spreadsheet.sheet1
        return sheet
    except Exception as e:
        st.error(f"שגיאה בהתחברות ל-Google Sheets: {e}")
        return None

def load_portfolios():
    """טעינת נתוני תיקים מ-Google Sheets - עם הגנות חזקות"""
    sheet = get_google_sheet()
    
    # 🛡️ אם אין חיבור - עצור הכל
    if not sheet:
        st.error("🔴 **שגיאה קריטית:** לא ניתן להתחבר ל-Google Sheets!")
        st.info("נסה לרענן את הדף. אם הבעיה נמשכת, פנה למורה.")
        st.stop()
    
    try:
        all_data = sheet.get_all_records()
        
        # 🛡️ אם הגיליון ריק - זו בעיה חמורה
        if not all_data:
            st.error("🔴 **שגיאה קריטית:** הגיליון ריק לגמרי!")
            st.warning("ייתכן שיש בעיה בגיליון Google Sheets. פנה למורה.")
            st.stop()
        
        portfolios = {}
        for row in all_data:
            username = row.get('username')
            if not username:
                continue
            
            portfolios[username] = {
                'cash': float(row.get('cash', 10000)),
                'stocks': json.loads(row.get('stocks', '{}')) if row.get('stocks') else {},
                'history': json.loads(row.get('history', '[]')) if row.get('history') else []
            }
        
        # 🛡️ בדיקת תקינות - חייב להיות לפחות 3 תיקים
        if len(portfolios) < 3:
            st.error(f"🔴 **שגיאה קריטית:** נטענו רק {len(portfolios)} תיקים!")
            st.warning("זה לא נורמלי. ייתכן שיש בעיה בנתונים. פנה למורה.")
            st.stop()
        
        # ✅ הכל תקין
        return portfolios
        
    except Exception as e:
        st.error(f"🔴 **שגיאה קריטית בטעינת נתונים:** {e}")
        st.info("נסה לרענן את הדף. אם הבעיה נמשכת, פנה למורה.")
        st.stop()

def save_single_user(username):
    """שמירת תיק של משתמש בודד - בטוח ומדויק!"""
    sheet = get_google_sheet()
    
    # 🛡️ אם אין חיבור - לא שומרים
    if not sheet:
        st.error("🔴 לא ניתן לשמור - אין חיבור ל-Google Sheets")
        return False
    
    try:
        # וידוא שהמשתמש קיים ב-session
        if username not in st.session_state.portfolios:
            st.error(f"🔴 שגיאה: {username} לא קיים ב-session")
            return False
        
        portfolio = st.session_state.portfolios[username]
        
        # קריאת כל הנתונים כדי למצוא את השורה
        all_data = sheet.get_all_records()
        row_number = None
        
        # חיפוש השורה של המשתמש
        for idx, row in enumerate(all_data):
            if row.get('username') == username:
                row_number = idx + 2  # +2 כי: 1=header, 0-indexed
                break
        
        # הכנת הנתונים
        cash_value = portfolio['cash']
        stocks_json = json.dumps(portfolio['stocks'], ensure_ascii=False)
        history_json = json.dumps(portfolio['history'], ensure_ascii=False)
        
        if row_number:
            # עדכון שורה קיימת
            sheet.update_cell(row_number, 2, cash_value)
            sheet.update_cell(row_number, 3, stocks_json)
            sheet.update_cell(row_number, 4, history_json)
        else:
            # הוספת שורה חדשה
            sheet.append_row([username, cash_value, stocks_json, history_json])
        
        return True
        
    except Exception as e:
        st.error(f"🔴 שגיאה בשמירת {username}: {e}")
        return False

def get_usd_to_ils():
    """קבלת שער USD/ILS"""
    try:
        ticker = yf.Ticker("ILS=X")
        hist = ticker.history(period='1d')
        if not hist.empty:
            return hist['Close'].iloc[-1]
        return 3.6
    except:
        return 3.6

def get_stock_price(symbol):
    """משיכת מחיר מניה"""
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period='1d')
        if not hist.empty:
            return hist['Close'].iloc[-1]
        return None
    except:
        return None

def get_stock_info(symbol):
    """משיכת מידע על מניה"""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        return {
            'name': info.get('longName', symbol),
            'price': get_stock_price(symbol),
            'currency': info.get('currency', 'USD')
        }
    except:
        return None

def get_stock_performance(symbol):
    """קבלת ביצועים היסטוריים"""
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period='1mo')
        if hist.empty:
            return None
        
        current_price = hist['Close'].iloc[-1]
        perf = {}
        
        if len(hist) >= 2:
            perf['daily_change'] = ((current_price - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
        if len(hist) >= 5:
            perf['weekly_change'] = ((current_price - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5]) * 100
        if len(hist) >= 20:
            perf['monthly_change'] = ((current_price - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
        
        return perf
    except:
        return None

def get_stock_description(symbol):
    """תיאור המניה בעברית"""
    descriptions = {
        'SPY': '📊 מניית סל העוקבת אחר מדד S&P 500 - 500 החברות הגדולות בארה"ב מכל התחומים.',
        'QQQ': '📊 מניית סל העוקבת אחר מדד NASDAQ 100 - 100 חברות הטכנולוגיה המובילות (אפל, מיקרוסופט, גוגל ועוד).',
        'VTI': '📊 מניית סל של Vanguard - כמעט כל השוק האמריקאי (כ-4,000 מניות!).',
        'VXUS': '📊 מניית סל של Vanguard - חברות מכל העולם מחוץ לארה"ב (אירופה, אסיה, שווקים מתעוררים).',
        'VOO': '📊 מניית סל של Vanguard - עוקבת אחר S&P 500, דומה ל-SPY עם עמלות נמוכות יותר.',
        'AAPL': '🍎 אפל - מייצרת iPhone, iPad, Mac ועוד. אחת החברות הגדולות בעולם.',
        'MSFT': '💻 מיקרוסופט - Windows, Office, Xbox, Azure ועוד. ענקית התוכנה.',
        'GOOGL': '🔍 גוגל (אלפבית) - מנוע החיפוש, YouTube, Android, Gmail ועוד.',
        'META': '📱 מטא (פייסבוק לשעבר) - פייסבוק, אינסטגרם, ווטסאפ.',
        'NVDA': '🎮 אנבידיה - כרטיסי מסך, בינוי מלאכותית, מחשוב על.',
        'AMZN': '🌐 אמזון - קניות אונליין, AWS (שירותי ענן), פריים.',
        'NFLX': '🎬 נטפליקס - שירות סטרימינג לסרטים וסדרות.',
        'INTC': '💾 אינטל - מעבדים ושבבים למחשבים.',
        'AMD': '🖥️ AMD - מעבדים וכרטיסי מסך, מתחרה של אינטל ואנבידיה.',
        'IBM': '💻 IBM - חברת טכנולוגיה ותוכנה ותיקה, מחשוב ענן ובינה מלאכותית.',
        'ORCL': '☁️ אורקל - מסדי נתונים, תוכנה עסקית, שירותי ענן.',
        'TSLA': '🚗 טסלה - מכוניות חשמליות, סולאריות, סוללות.',
        'F': '🚙 פורד - אחת מיצרניות הרכב הותיקות בארה"ב.',
        'GM': '🏭 ג\'נרל מוטורס - יצרנית רכב אמריקאית גדולה (שברולט, קדילאק).',
        'BA': '✈️ בואינג - מטוסי נוסעים ומטוסי קרב.',
        'KO': '🥤 קוקה קולה - משקאות קלים בעולם כולו.',
        'MCD': '🍔 מקדונלד\'ס - רשת מזון מהיר עולמית.',
        'SBUX': '☕ סטארבקס - רשת בתי קפה עולמית.',
        'WMT': '🛒 וולמארט - רשת סופרמרקטים ענקית בארה"ב.',
        'TGT': '🎯 טארגט - רשת חנויות כלבו אמריקאית.',
        'NKE': '👟 נייקי - ביגוד וציוד ספורט.',
        'DIS': '🏰 דיסני - סרטים, פארקי שעשועים, ערוצי טלוויזיה.',
        'V': '💳 ויזה - כרטיסי אשראי בעולם כולו.',
        'MA': '💳 מאסטרקארד - כרטיסי אשראי, מתחרה של ויזה.',
        'PYPL': '💰 פייפאל - תשלומים דיגיטליים.',
        'TEVA': '💊 טבע - תרופות גנריות, אחת החברות הגדולות בישראל.',
        'CHKP': '🔒 צ\'ק פוינט - אבטחת סייבר, חברה ישראלית.',
        'WIX': '🌐 וויקס - בניית אתרים, חברה ישראלית.',
        'NICE': '📞 נייס - תוכנה לניתוח שיחות ונתונים, חברה ישראלית.',
        'MNDY': '📋 מאנדיי - ניהול פרויקטים ומשימות, חברה ישראלית.'
    }
    return descriptions.get(symbol, None)

def calculate_commission(amount):
    """חישוב עמלה: 0.1% עם מינימום 5 ₪"""
    commission = amount * 0.001
    return max(commission, 5)

def buy_stock(username, symbol, shares):
    """קניית מניה"""
    info = get_stock_info(symbol)
    if not info or info['price'] is None:
        return False, "לא נמצא סימול מניה תקין"
    
    price_usd = info['price']
    usd_to_ils = get_usd_to_ils()
    price_ils = price_usd * usd_to_ils
    
    total_cost = price_ils * shares
    commission = calculate_commission(total_cost)
    total_with_commission = total_cost + commission
    
    portfolio = st.session_state.portfolios[username]
    
    if portfolio['cash'] < total_with_commission:
        return False, f"אין מספיק כסף. צריך: ₪{total_with_commission:.2f}, יש: ₪{portfolio['cash']:.2f}"
    
    portfolio['cash'] -= total_with_commission
    
    if symbol in portfolio['stocks']:
        old_shares = portfolio['stocks'][symbol]['shares']
        old_avg = portfolio['stocks'][symbol]['avg_price']
        new_avg = (old_shares * old_avg + shares * price_ils) / (old_shares + shares)
        portfolio['stocks'][symbol]['shares'] += shares
        portfolio['stocks'][symbol]['avg_price'] = new_avg
    else:
        portfolio['stocks'][symbol] = {
            'shares': shares,
            'avg_price': price_ils
        }
    
    portfolio['history'].append({
        'date': datetime.now().isoformat(),
        'action': 'buy',
        'symbol': symbol,
        'shares': shares,
        'price': price_ils,
        'commission': commission,
        'total': total_with_commission
    })
    
    save_single_user(username)
    return True, f"קנית {shares} מניות של {symbol} ב-${price_usd:.2f} (₪{price_ils:.2f}) | עמלה: ₪{commission:.2f}"

def sell_stock(username, symbol, shares):
    """מכירת מניה"""
    portfolio = st.session_state.portfolios[username]
    
    if symbol not in portfolio['stocks']:
        return False, "אין לך מניות מסוג זה"
    
    if portfolio['stocks'][symbol]['shares'] < shares:
        return False, f"אין לך מספיק מניות. יש לך: {portfolio['stocks'][symbol]['shares']}"
    
    price_usd = get_stock_price(symbol)
    if price_usd is None:
        return False, "שגיאה במשיכת מחיר"
    
    usd_to_ils = get_usd_to_ils()
    price_ils = price_usd * usd_to_ils
    
    total_value = price_ils * shares
    commission = calculate_commission(total_value)
    total_after_commission = total_value - commission
    
    portfolio['cash'] += total_after_commission
    portfolio['stocks'][symbol]['shares'] -= shares
    
    if portfolio['stocks'][symbol]['shares'] == 0:
        del portfolio['stocks'][symbol]
    
    portfolio['history'].append({
        'date': datetime.now().isoformat(),
        'action': 'sell',
        'symbol': symbol,
        'shares': shares,
        'price': price_ils,
        'commission': commission,
        'total': total_after_commission
    })
    
    save_single_user(username)
    return True, f"מכרת {shares} מניות של {symbol} ב-${price_usd:.2f} (₪{price_ils:.2f}) | עמלה: ₪{commission:.2f}"

def create_portfolio(username):
    """יצירת תיק חדש למשתמש"""
    st.session_state.portfolios[username] = {
        'cash': 10000,
        'stocks': {},
        'history': []
    }
    save_single_user(username)

def reset_portfolio(username):
    """איפוס תיק"""
    if username in st.session_state.portfolios:
        st.session_state.portfolios[username] = {
            'cash': 10000,
            'stocks': {},
            'history': []
        }
        save_single_user(username)
        return True
    return False

# ============================================
# ממשק משתמש - התחברות
# ============================================

def login_page():
    """דף התחברות"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🎮 בורסת הכיתה")
        st.markdown("---")
        
        username = st.text_input("שם משתמש")
        password = st.text_input("סיסמה", type="password")
        
        if st.button("היכנס", use_container_width=True):
            users = st.secrets['users']
            if username in users and users[username] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("שם משתמש או סיסמה שגויים")

# ============================================
# ממשק משתמש - דף ראשי
# ============================================

def main_page():
    """הדף הראשי של המערכת"""
    username = st.session_state.username
    
    # בדיקה פשוטה: האם יש תיק?
    if username not in st.session_state.portfolios:
        st.error(f"❌ אין תיק עבור {username}")
        
        # אם זה המורה - תן לו ליצור
        if username == "nadav":
            if st.button("✅ צור תיק למשתמש זה"):
                create_portfolio(username)
                st.success("תיק נוצר!")
                st.rerun()
        else:
            st.info("נא לפנות למורה")
        return
    
    portfolio = st.session_state.portfolios[username]
    
    # כותרת
    col_title, col_logout = st.columns([3, 1])
    with col_title:
        st.title(f"שלום {username}! 👋")
    with col_logout:
        if st.button("התנתק"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()
    
    st.markdown("---")
    
    # שער דולר
    usd_to_ils = get_usd_to_ils()
    st.info(f"💱 **שער דולר-שקל היום:** $1.00 = ₪{usd_to_ils:.3f}")
    
    # חישוב שווי תיק
    stocks_value = 0
    stocks_value_yesterday = 0
    
    for symbol, data in portfolio['stocks'].items():
        current_price_usd = get_stock_price(symbol)
        if current_price_usd:
            current_price_ils = current_price_usd * usd_to_ils
            stocks_value += current_price_ils * data['shares']
            
            try:
                stock = yf.Ticker(symbol)
                hist = stock.history(period='2d')
                if len(hist) >= 2:
                    yesterday_price_usd = hist['Close'].iloc[-2]
                    yesterday_price_ils = yesterday_price_usd * usd_to_ils
                    stocks_value_yesterday += yesterday_price_ils * data['shares']
                else:
                    stocks_value_yesterday += current_price_ils * data['shares']
            except:
                stocks_value_yesterday += current_price_ils * data['shares']
    
    total_value = portfolio['cash'] + stocks_value
    total_value_yesterday = portfolio['cash'] + stocks_value_yesterday
    
    profit_loss = total_value - 10000
    profit_loss_percent = (profit_loss / 10000) * 100
    
    daily_change = total_value - total_value_yesterday
    daily_change_percent = (daily_change / total_value_yesterday) * 100 if total_value_yesterday > 0 else 0
    
    # מטריקות
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("💵 יתרת מזומן", f"₪{portfolio['cash']:.2f}")
    with col2:
        st.metric("📊 שווי מניות", f"₪{stocks_value:.2f}")
    with col3:
        st.metric("💼 שווי תיק כולל", f"₪{total_value:.2f}")
    with col4:
        st.metric("📅 רווח/הפסד יומי", f"₪{daily_change:+.2f}", f"{daily_change_percent:+.2f}%", delta_color="normal")
    with col5:
        st.metric("📈 רווח/הפסד כולל", f"₪{profit_loss:+.2f}", f"{profit_loss_percent:+.2f}%", delta_color="normal")
    
    st.markdown("---")
    
    # טאבים
    is_teacher = (username == "nadav")
    
    if is_teacher:
        tab1, tab2, tab3, tab4 = st.tabs(["💰 קנה/מכור", "📊 התיק שלי", "📜 היסטוריה", "👨‍🏫 לוח בקרת מורה"])
    else:
        tab1, tab2, tab3 = st.tabs(["💰 קנה/מכור", "📊 התיק שלי", "📜 היסטוריה"])
    
    # טאב 1: קנייה/מכירה
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🛒 קנה מניה")
            
            popular_stocks = {
                "--- מניות סל (ETFs) ---": "HEADER1",
                "📊 SPY - S&P 500": "SPY",
                "📊 QQQ - NASDAQ 100": "QQQ",
                "📊 VTI - כלל שוק ארה\"ב": "VTI",
                "📊 VXUS - כלל עולמי": "VXUS",
                "📊 VOO - S&P 500 (Vanguard)": "VOO",
                "--- טכנולוגיה ---": "HEADER2",
                "🍎 Apple (AAPL)": "AAPL",
                "💻 Microsoft (MSFT)": "MSFT",
                "🔍 Google (GOOGL)": "GOOGL",
                "📱 Meta/Facebook (META)": "META",
                "🎮 NVIDIA (NVDA)": "NVDA",
                "🌐 Amazon (AMZN)": "AMZN",
                "🎬 Netflix (NFLX)": "NFLX",
                "💾 Intel (INTC)": "INTC",
                "🖥️ AMD (AMD)": "AMD",
                "💻 IBM (IBM)": "IBM",
                "☁️ Oracle (ORCL)": "ORCL",
                "--- רכב וחלל ---": "HEADER3",
                "🚗 Tesla (TSLA)": "TSLA",
                "🚙 Ford (F)": "F",
                "🏭 General Motors (GM)": "GM",
                "✈️ Boeing (BA)": "BA",
                "--- צריכה ומזון ---": "HEADER4",
                "🥤 Coca-Cola (KO)": "KO",
                "🍔 McDonald's (MCD)": "MCD",
                "☕ Starbucks (SBUX)": "SBUX",
                "🛒 Walmart (WMT)": "WMT",
                "🎯 Target (TGT)": "TGT",
                "--- ספורט ופיננסים ---": "HEADER5",
                "👟 Nike (NKE)": "NKE",
                "🏰 Disney (DIS)": "DIS",
                "💳 Visa (V)": "V",
                "💳 Mastercard (MA)": "MA",
                "💰 PayPal (PYPL)": "PYPL",
                "--- חברות ישראליות ---": "HEADER6",
                "💊 Teva (TEVA)": "TEVA",
                "🔒 Check Point (CHKP)": "CHKP",
                "🌐 Wix (WIX)": "WIX",
                "📞 Nice (NICE)": "NICE",
                "📋 Monday.com (MNDY)": "MNDY",
                "--- או הכנס ידנית ---": "CUSTOM"
            }
            
            stock_choice = st.selectbox("בחר מניה", options=list(popular_stocks.keys()), key="stock_choice")
            
            buy_symbol = None
            
            if popular_stocks[stock_choice].startswith("HEADER"):
                st.info("👆 בחר מניה מהרשימה")
            elif popular_stocks[stock_choice] == "CUSTOM":
                buy_symbol = st.text_input("הכנס סימול", key="buy_symbol_custom").upper()
            else:
                buy_symbol = popular_stocks[stock_choice]
            
            if buy_symbol and buy_symbol != "CUSTOM":
                info = get_stock_info(buy_symbol)
                if info and info['price']:
                    price_ils = info['price'] * usd_to_ils
                    st.info(f"**{info['name']}** - מחיר נוכחי: ${info['price']:.2f} (₪{price_ils:.2f})")
                    
                    description = get_stock_description(buy_symbol)
                    if description:
                        st.markdown(f"ℹ️ {description}")
                    
                    perf = get_stock_performance(buy_symbol)
                    if perf:
                        perf_cols = st.columns(3)
                        if 'daily_change' in perf:
                            with perf_cols[0]:
                                emoji = "🟢 ⬆️" if perf['daily_change'] >= 0 else "🔴 ⬇️"
                                color = "green" if perf['daily_change'] >= 0 else "red"
                                st.markdown(f"{emoji} **יומי:** :{color}[{perf['daily_change']:+.2f}%]")
                        if 'weekly_change' in perf:
                            with perf_cols[1]:
                                emoji = "🟢 ⬆️" if perf['weekly_change'] >= 0 else "🔴 ⬇️"
                                color = "green" if perf['weekly_change'] >= 0 else "red"
                                st.markdown(f"{emoji} **שבועי:** :{color}[{perf['weekly_change']:+.2f}%]")
                        if 'monthly_change' in perf:
                            with perf_cols[2]:
                                emoji = "🟢 ⬆️" if perf['monthly_change'] >= 0 else "🔴 ⬇️"
                                color = "green" if perf['monthly_change'] >= 0 else "red"
                                st.markdown(f"{emoji} **חודשי:** :{color}[{perf['monthly_change']:+.2f}%]")
                else:
                    st.warning("לא נמצא סימול תקין")
            
            buy_shares = st.number_input("כמות מניות", min_value=1, value=1, key="buy_shares")
            
            if st.button("קנה", use_container_width=True):
                if buy_symbol:
                    success, message = buy_stock(username, buy_symbol, buy_shares)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("נא להזין סימול מניה")
        
        with col2:
            st.subheader("💸 מכור מניה")
            
            if portfolio['stocks']:
                symbols_owned = list(portfolio['stocks'].keys())
                sell_symbol = st.selectbox("בחר מניה למכירה", symbols_owned)
                
                max_shares = portfolio['stocks'][sell_symbol]['shares']
                st.info(f"יש לך {max_shares} מניות")
                
                current_price = get_stock_price(sell_symbol)
                if current_price:
                    price_ils = current_price * usd_to_ils
                    st.info(f"מחיר נוכחי: ${current_price:.2f} (₪{price_ils:.2f})")
                
                sell_shares = st.number_input("כמות מניות למכירה", min_value=1, max_value=max_shares, value=1, key="sell_shares")
                
                if st.button("מכור", use_container_width=True):
                    success, message = sell_stock(username, sell_symbol, sell_shares)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.info("אין לך מניות למכירה")
    
    # טאב 2: התיק
    with tab2:
        st.subheader("📊 המניות שלי")
        
        if portfolio['stocks']:
            rows = []
            for symbol, data in portfolio['stocks'].items():
                current_price_usd = get_stock_price(symbol)
                if current_price_usd:
                    current_price_ils = current_price_usd * usd_to_ils
                    current_value = current_price_ils * data['shares']
                    purchase_value = data['avg_price'] * data['shares']
                    profit_loss = current_value - purchase_value
                    profit_loss_pct = (profit_loss / purchase_value) * 100
                    
                    rows.append({
                        'סימול': symbol,
                        'כמות': data['shares'],
                        'מחיר קנייה ממוצע': f"₪{data['avg_price']:.2f}",
                        'מחיר נוכחי': f"${current_price_usd:.2f} (₪{current_price_ils:.2f})",
                        'שווי נוכחי': f"₪{current_value:.2f}",
                        'רווח/הפסד': f"₪{profit_loss:+.2f} ({profit_loss_pct:+.2f}%)"
                    })
            
            df = pd.DataFrame(rows)
            st.dataframe(df, hide_index=True)
        else:
            st.info("אין לך מניות בתיק כרגע")
    
    # טאב 3: היסטוריה
    with tab3:
        st.subheader("📜 היסטוריית עסקאות")
        
        if portfolio['history']:
            recent = portfolio['history'][-20:][::-1]
            
            for transaction in recent:
                action_emoji = "🛒" if transaction['action'] == 'buy' else "💸"
                action_text = "קנייה" if transaction['action'] == 'buy' else "מכירה"
                date_str = datetime.fromisoformat(transaction['date']).strftime("%d/%m/%Y %H:%M")
                
                st.markdown(f"""
                {action_emoji} **{action_text}** - {transaction['symbol']}  
                {transaction['shares']} מניות × ₪{transaction['price']:.2f} = ₪{transaction['shares'] * transaction['price']:.2f}  
                עמלה: ₪{transaction['commission']:.2f} | סה"כ: ₪{transaction['total']:.2f}  
                📅 {date_str}
                """)
                st.markdown("---")
        else:
            st.info("עדיין לא ביצעת עסקאות")
    
    # טאב 4: לוח בקרת מורה
    if is_teacher:
        with tab4:
            st.subheader("👨‍🏫 לוח בקרת מורה")
            
            # סטטיסטיקות
            st.markdown("### 📊 סטטיסטיקות כיתה")
            col1, col2, col3 = st.columns(3)
            
            total_students = len(st.session_state.portfolios) - 1
            total_cash = sum(p['cash'] for u, p in st.session_state.portfolios.items() if u != username)
            total_trades = sum(len(p['history']) for u, p in st.session_state.portfolios.items() if u != username)
            
            with col1:
                st.metric("👥 מספר תלמידים", total_students)
            with col2:
                st.metric("💰 סך מזומן בכיתה", f"₪{total_cash:.2f}")
            with col3:
                st.metric("📈 סך עסקאות", total_trades)
            
            st.markdown("---")
            
            # טבלת תלמידים
            st.markdown("### 👥 ניהול תלמידים")
            
            students_data = []
            for student_name, student_portfolio in st.session_state.portfolios.items():
                if student_name == username:
                    continue
                
                stocks_value = 0
                for symbol, data in student_portfolio['stocks'].items():
                    current_price = get_stock_price(symbol)
                    if current_price:
                        stocks_value += current_price * usd_to_ils * data['shares']
                
                total_value = student_portfolio['cash'] + stocks_value
                profit = total_value - 10000
                
                students_data.append({
                    'תלמיד': student_name,
                    'יתרת מזומן': f"₪{student_portfolio['cash']:.2f}",
                    'שווי מניות': f"₪{stocks_value:.2f}",
                    'שווי כולל': f"₪{total_value:.2f}",
                    'רווח/הפסד': f"₪{profit:+.2f}",
                    'עסקאות': len(student_portfolio['history']),
                    'מניות בתיק': len(student_portfolio['stocks'])
                })
            
            if students_data:
                df = pd.DataFrame(students_data)
                st.dataframe(df, hide_index=True)
            
            st.markdown("---")
            
            # יצירת תיקים למשתמשים חדשים
            st.markdown("### ➕ הוספת תלמידים חדשים")
            
            users_in_secrets = set(st.secrets['users'].keys())
            users_with_portfolio = set(st.session_state.portfolios.keys())
            missing_users = users_in_secrets - users_with_portfolio
            
            if missing_users:
                st.info(f"🆕 נמצאו {len(missing_users)} משתמשים ב-Secrets שאין להם תיק:")
                for user in missing_users:
                    col_user, col_btn = st.columns([3, 1])
                    with col_user:
                        st.write(f"👤 **{user}**")
                    with col_btn:
                        if st.button("➕ צור תיק", key=f"create_{user}"):
                            create_portfolio(user)
                            st.success(f"✅ תיק נוצר עבור {user}!")
                            time.sleep(1)
                            st.rerun()
            else:
                st.success("✅ לכל המשתמשים ב-Secrets יש תיק!")
            
            st.markdown("---")
            
            # איפוס תלמיד
            st.markdown("### 🔄 איפוס תיק תלמיד")
            st.warning("⚠️ פעולת איפוס תמחק את כל המניות וההיסטוריה ותחזיר את התיק ל-₪10,000")
            
            students_list = [s for s in st.session_state.portfolios.keys() if s != username]
            if students_list:
                selected_student = st.selectbox("בחר תלמיד לאיפוס", students_list)
                
                col_btn, col_space = st.columns([1, 3])
                with col_btn:
                    if st.button("🔄 אפס תיק", type="primary"):
                        if 'confirm_teacher_reset' not in st.session_state:
                            st.session_state.confirm_teacher_reset = selected_student
                            st.rerun()
                
                if st.session_state.get('confirm_teacher_reset'):
                    student_to_reset = st.session_state.confirm_teacher_reset
                    st.error(f"❗ **האם לאפס את התיק של {student_to_reset}?** זו פעולה בלתי הפיכה!")
                    
                    col_yes, col_no = st.columns(2)
                    
                    with col_yes:
                        if st.button("✅ כן, אפס תיק", type="primary", key="confirm_yes"):
                            if reset_portfolio(student_to_reset):
                                st.session_state.confirm_teacher_reset = None
                                st.success(f"✅ התיק של {student_to_reset} אופס בהצלחה!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ שגיאה באיפוס התיק")
                    
                    with col_no:
                        if st.button("❌ ביטול", key="confirm_no"):
                            st.session_state.confirm_teacher_reset = None
                            st.rerun()
            else:
                st.info("אין תלמידים במערכת")
            
            st.markdown("---")
            
            # איפוס תיק המורה
            st.markdown("### 🔄 איפוס התיק שלי (מורה)")
            st.warning("⚠️ פעולת איפוס תמחק את כל המניות וההיסטוריה שלך")
            
            col_btn2, col_space2 = st.columns([1, 3])
            with col_btn2:
                if st.button("🔄 אפס את התיק שלי", type="secondary"):
                    if 'confirm_self_reset' not in st.session_state:
                        st.session_state.confirm_self_reset = True
                        st.rerun()
            
            if st.session_state.get('confirm_self_reset'):
                st.error("❗ **האם לאפס את התיק שלך?** זו פעולה בלתי הפיכה!")
                
                col_yes2, col_no2 = st.columns(2)
                
                with col_yes2:
                    if st.button("✅ כן, אפס", type="primary", key="confirm_self_yes"):
                        if reset_portfolio(username):
                            st.session_state.confirm_self_reset = None
                            st.success("✅ התיק שלך אופס בהצלחה!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ שגיאה באיפוס התיק")
                
                with col_no2:
                    if st.button("❌ ביטול", key="confirm_self_no"):
                        st.session_state.confirm_self_reset = None
                        st.rerun()

# ============================================
# הרצת האפליקציה
# ============================================

def main():
    init_session_state()
    
    if not st.session_state.logged_in:
        login_page()
    else:
        main_page()

if __name__ == "__main__":
    main()
