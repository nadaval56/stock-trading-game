import streamlit as st
import yfinance as yf
from datetime import datetime
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials

# ============================================
# הגדרות ראשוניות
# ============================================

st.set_page_config(
    page_title="בורסת הכיתה",
    page_icon="📈",
    layout="wide"
)

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
        # טעינה מ-Google Sheets רק בפעם הראשונה
        st.session_state.portfolios = load_portfolios()
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()

def refresh_portfolios():
    """רענון נתונים מ-Google Sheets (אופציונלי)"""
    st.session_state.portfolios = load_portfolios()
    st.session_state.last_refresh = datetime.now()
    st.success("הנתונים רוענ נו מהשרת!")

def get_google_sheet():
    """התחברות ל-Google Sheets"""
    try:
        # הגדרת credentials מ-Streamlit Secrets
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        
        # טעינת credentials מ-Secrets
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        # פתיחת הגיליון
        sheet = client.open("בורסת הכיתה - נתונים").sheet1
        return sheet
    except Exception as e:
        st.error(f"שגיאה בחיבור ל-Google Sheets: {e}")
        return None

def load_portfolios():
    """טעינת נתוני תיקים מ-Google Sheets"""
    sheet = get_google_sheet()
    if not sheet:
        # במקרה של שגיאה - החזר תיקים ריקים
        return init_empty_portfolios()
    
    try:
        # קריאת כל הנתונים
        all_data = sheet.get_all_records()
        
        if not all_data:
            # אם הגיליון ריק - אתחל תיקים חדשים
            portfolios = init_empty_portfolios()
            save_portfolios(portfolios)
            return portfolios
        
        # המרת נתוני הגיליון לפורמט של portfolios
        portfolios = {}
        for row in all_data:
            username = row['username']
            portfolios[username] = {
                'cash': float(row['cash']),
                'stocks': json.loads(row['stocks']) if row['stocks'] else {},
                'history': json.loads(row['history']) if row['history'] else []
            }
        
        return portfolios
    except Exception as e:
        st.error(f"שגיאה בטעינת נתונים: {e}")
        return init_empty_portfolios()

def init_empty_portfolios():
    """יצירת תיקים ריקים לכל המשתמשים"""
    users = st.secrets['users']
    portfolios = {}
    for username in users.keys():
        portfolios[username] = {
            'cash': 10000,
            'stocks': {},
            'history': []
        }
    return portfolios

def save_portfolios(portfolios=None):
    """שמירת נתוני התיקים ל-Google Sheets"""
    if portfolios is None:
        portfolios = st.session_state.portfolios
    
    sheet = get_google_sheet()
    if not sheet:
        return False
    
    try:
        # בניית הנתונים לשמירה
        data_to_save = []
        for username, portfolio in portfolios.items():
            data_to_save.append({
                'username': username,
                'cash': portfolio['cash'],
                'stocks': json.dumps(portfolio['stocks'], ensure_ascii=False),
                'history': json.dumps(portfolio['history'], ensure_ascii=False)
            })
        
        # יצירת DataFrame
        df = pd.DataFrame(data_to_save)
        
        # ניקוי הגיליון ושמירת נתונים חדשים
        sheet.clear()
        
        # כותרות
        headers = ['username', 'cash', 'stocks', 'history']
        sheet.insert_row(headers, 1)
        
        # נתונים
        for idx, row in df.iterrows():
            sheet.insert_row(row.tolist(), idx + 2)
        
        return True
    except Exception as e:
        st.error(f"שגיאה בשמירת נתונים: {e}")
        return False

def get_stock_price(symbol):
    """משיכת מחיר מניה מ-Yahoo Finance"""
    try:
        stock = yf.Ticker(symbol)
        # מחיר סגירה אחרון
        hist = stock.history(period='1d')
        if not hist.empty:
            return hist['Close'].iloc[-1]
        else:
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

def calculate_commission(amount):
    """חישוב עמלה: 0.1% עם מינימום 5 ₪"""
    commission = amount * 0.001  # 0.1%
    return max(commission, 5)

def buy_stock(username, symbol, shares):
    """קניית מניה"""
    # בדיקה שהסימול תקין
    info = get_stock_info(symbol)
    if not info or info['price'] is None:
        return False, "לא נמצא סימול מניה תקין"
    
    price = info['price']
    total_cost = price * shares
    commission = calculate_commission(total_cost)
    total_with_commission = total_cost + commission
    
    portfolio = st.session_state.portfolios[username]
    
    # בדיקת יתרה
    if portfolio['cash'] < total_with_commission:
        return False, f"אין מספיק כסף. צריך: {total_with_commission:.2f} ₪, יש: {portfolio['cash']:.2f} ₪"
    
    # ביצוע הקנייה
    portfolio['cash'] -= total_with_commission
    
    # עדכון מניות בתיק
    if symbol in portfolio['stocks']:
        # עדכון ממוצע משוקלל
        old_shares = portfolio['stocks'][symbol]['shares']
        old_avg = portfolio['stocks'][symbol]['avg_price']
        new_avg = (old_shares * old_avg + shares * price) / (old_shares + shares)
        portfolio['stocks'][symbol]['shares'] += shares
        portfolio['stocks'][symbol]['avg_price'] = new_avg
    else:
        portfolio['stocks'][symbol] = {
            'shares': shares,
            'avg_price': price
        }
    
    # תיעוד בהיסטוריה
    portfolio['history'].append({
        'date': datetime.now().isoformat(),
        'action': 'buy',
        'symbol': symbol,
        'shares': shares,
        'price': price,
        'commission': commission,
        'total': total_with_commission
    })
    
    save_portfolios()
    return True, f"קנית {shares} מניות של {symbol} ב-${price:.2f} (עמלה: {commission:.2f} ₪)"

def sell_stock(username, symbol, shares):
    """מכירת מניה"""
    portfolio = st.session_state.portfolios[username]
    
    # בדיקה שיש את המניה
    if symbol not in portfolio['stocks']:
        return False, "אין לך מניות מסוג זה"
    
    if portfolio['stocks'][symbol]['shares'] < shares:
        return False, f"אין לך מספיק מניות. יש לך: {portfolio['stocks'][symbol]['shares']}"
    
    # קבלת מחיר נוכחי
    price = get_stock_price(symbol)
    if price is None:
        return False, "שגיאה במשיכת מחיר"
    
    total_value = price * shares
    commission = calculate_commission(total_value)
    total_after_commission = total_value - commission
    
    # ביצוע המכירה
    portfolio['cash'] += total_after_commission
    portfolio['stocks'][symbol]['shares'] -= shares
    
    # אם מכרנו הכל - מוחקים מהתיק
    if portfolio['stocks'][symbol]['shares'] == 0:
        del portfolio['stocks'][symbol]
    
    # תיעוד
    portfolio['history'].append({
        'date': datetime.now().isoformat(),
        'action': 'sell',
        'symbol': symbol,
        'shares': shares,
        'price': price,
        'commission': commission,
        'total': total_after_commission
    })
    
    save_portfolios()
    return True, f"מכרת {shares} מניות של {symbol} ב-${price:.2f} (עמלה: {commission:.2f} ₪)"

# ============================================
# ממשק משתמש - התחברות
# ============================================

def login_page():
    """עמוד התחברות"""
    st.title("📈 בורסת הכיתה")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("התחברות")
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
    portfolio = st.session_state.portfolios[username]
    
    # כותרת עליונה
    col_title, col_refresh, col_logout = st.columns([3, 1, 1])
    
    with col_title:
        st.title(f"שלום {username}! 👋")
    
    with col_refresh:
        if st.button("🔄 רענן נתונים"):
            refresh_portfolios()
            st.rerun()
    
    with col_logout:
        if st.button("התנתק"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()
    
    st.markdown("---")
    
    # חישוב שווי תיק נוכחי
    stocks_value = 0
    for symbol, data in portfolio['stocks'].items():
        current_price = get_stock_price(symbol)
        if current_price:
            stocks_value += current_price * data['shares']
    
    total_value = portfolio['cash'] + stocks_value
    profit_loss = total_value - 10000
    profit_loss_percent = (profit_loss / 10000) * 100
    
    # תצוגת סטטיסטיקות
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💵 יתרת מזומן", f"{portfolio['cash']:.2f} ₪")
    
    with col2:
        st.metric("📊 שווי מניות", f"{stocks_value:.2f} ₪")
    
    with col3:
        st.metric("💼 שווי תיק כולל", f"{total_value:.2f} ₪")
    
    with col4:
        st.metric(
            "📈 רווח/הפסד", 
            f"{profit_loss:+.2f} ₪",
            f"{profit_loss_percent:+.2f}%",
            delta_color="normal"
        )
    
    st.markdown("---")
    
    # טאבים
    tab1, tab2, tab3 = st.tabs(["💰 קנה/מכור", "📊 התיק שלי", "📜 היסטוריה"])
    
    # ===== טאב 1: קנייה ומכירה =====
    with tab1:
        col1, col2 = st.columns(2)
        
        # קנייה
        with col1:
            st.subheader("🛒 קנה מניה")
            
            buy_symbol = st.text_input(
                "סימול מניה (לדוגמה: AAPL, MSFT, TEVA)",
                key="buy_symbol"
            ).upper()
            
            if buy_symbol:
                info = get_stock_info(buy_symbol)
                if info and info['price']:
                    st.info(f"**{info['name']}** - מחיר נוכחי: ${info['price']:.2f}")
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
        
        # מכירה
        with col2:
            st.subheader("💸 מכור מניה")
            
            if portfolio['stocks']:
                symbols_owned = list(portfolio['stocks'].keys())
                sell_symbol = st.selectbox("בחר מניה למכירה", symbols_owned)
                
                max_shares = portfolio['stocks'][sell_symbol]['shares']
                st.info(f"יש לך {max_shares} מניות")
                
                current_price = get_stock_price(sell_symbol)
                if current_price:
                    st.info(f"מחיר נוכחי: ${current_price:.2f}")
                
                sell_shares = st.number_input(
                    "כמות מניות למכירה", 
                    min_value=1, 
                    max_value=max_shares, 
                    value=1,
                    key="sell_shares"
                )
                
                if st.button("מכור", use_container_width=True):
                    success, message = sell_stock(username, sell_symbol, sell_shares)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.info("אין לך מניות למכירה")
    
    # ===== טאב 2: התיק =====
    with tab2:
        st.subheader("📊 המניות שלי")
        
        if portfolio['stocks']:
            # יצירת טבלה
            rows = []
            for symbol, data in portfolio['stocks'].items():
                current_price = get_stock_price(symbol)
                if current_price:
                    current_value = current_price * data['shares']
                    purchase_value = data['avg_price'] * data['shares']
                    profit_loss = current_value - purchase_value
                    profit_loss_pct = (profit_loss / purchase_value) * 100
                    
                    rows.append({
                        'סימול': symbol,
                        'כמות': data['shares'],
                        'מחיר קנייה ממוצע': f"${data['avg_price']:.2f}",
                        'מחיר נוכחי': f"${current_price:.2f}",
                        'שווי נוכחי': f"${current_value:.2f}",
                        'רווח/הפסד': f"${profit_loss:+.2f} ({profit_loss_pct:+.2f}%)"
                    })
            
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("אין לך מניות בתיק כרגע")
    
    # ===== טאב 3: היסטוריה =====
    with tab3:
        st.subheader("📜 היסטוריית עסקאות")
        
        if portfolio['history']:
            # הצגת 20 העסקאות האחרונות
            recent = portfolio['history'][-20:][::-1]  # הפוך - החדש ראשון
            
            for transaction in recent:
                action_emoji = "🛒" if transaction['action'] == 'buy' else "💸"
                action_text = "קנייה" if transaction['action'] == 'buy' else "מכירה"
                date_str = datetime.fromisoformat(transaction['date']).strftime("%d/%m/%Y %H:%M")
                
                st.markdown(f"""
                {action_emoji} **{action_text}** - {transaction['symbol']}  
                {transaction['shares']} מניות × ${transaction['price']:.2f} = ${transaction['shares'] * transaction['price']:.2f}  
                עמלה: {transaction['commission']:.2f} ₪ | סה"כ: {transaction['total']:.2f} ₪  
                📅 {date_str}
                """)
                st.markdown("---")
        else:
            st.info("עדיין לא ביצעת עסקאות")

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
