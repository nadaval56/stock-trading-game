# 📈 בורסת הכיתה - מדריך התקנה

## מה זה?
מערכת סימולציה למסחר במניות לתלמידים, עם מחירים אמיתיים מהבורסה.
**הנתונים נשמרים ב-Google Sheets** - התלמידים יכולים להיכנס מהבית ולעקוב אחרי התיק שלהם!

## קבצים במערכת
- `app.py` - הקוד הראשי של האפליקציה
- `requirements.txt` - רשימת ספריות Python
- `README.md` - הקובץ הזה

---

## 🗂️ שלב 0: הגדרת Google Sheets (חשוב!)

לפני שמתחילים - צריך להגדיר Google Sheets לשמירת נתונים.

### 0.1 יצירת פרויקט ב-Google Cloud

1. לך ל-https://console.cloud.google.com
2. לחץ על "Select a project" למעלה
3. לחץ "NEW PROJECT"
4. תן שם (לדוגמה: "Stock Trading Game")
5. לחץ "CREATE"
6. **המתן** עד שהפרויקט ייווצר (כ-30 שניות)

### 0.2 הפעלת Google Sheets API

1. וודא שהפרויקט החדש נבחר (למעלה)
2. לחץ על "☰" (תפריט) → "APIs & Services" → "Library"
3. חפש "Google Sheets API"
4. לחץ עליו → לחץ "ENABLE"
5. המתן שההפעלה תסתיים

### 0.3 יצירת Service Account

1. לחץ על "☰" → "APIs & Services" → "Credentials"
2. לחץ "+ CREATE CREDENTIALS" → "Service Account"
3. תן שם (לדוגמה: "sheets-bot")
4. לחץ "CREATE AND CONTINUE"
5. תחת "Role" בחר: "Editor"
6. לחץ "CONTINUE" → "DONE"

### 0.4 הורדת מפתח JSON

1. עדיין ב-Credentials, גלול למטה ל-"Service Accounts"
2. לחץ על ה-Service Account שיצרת (sheets-bot@...)
3. לך לטאב "KEYS"
4. לחץ "ADD KEY" → "Create new key"
5. בחר "JSON"
6. לחץ "CREATE"
7. **קובץ JSON יורד אוטומטית - שמור אותו במקום בטוח!**

⚠️ **חשוב**: אל תשתף את הקובץ הזה עם אף אחד! זה כמו סיסמה.

### 0.5 יצירת Google Sheet

1. לך ל-https://sheets.google.com
2. לחץ "+" (גיליון ריק)
3. תן לו שם: **"בורסת הכיתה - נתונים"** (בדיוק כך!)
4. השאר אותו ריק - הקוד ימלא אותו אוטומטית

### 0.6 שיתוף הגיליון עם ה-Bot

זה החלק הכי חשוב!

1. פתח את קובץ ה-JSON שהורדת
2. חפש את השורה: `"client_email": "sheets-bot@......iam.gserviceaccount.com"`
3. **העתק את כל המייל הזה**
4. חזור לגיליון ב-Google Sheets
5. לחץ "Share" (שיתוף) למעלה מימין
6. הדבק את המייל
7. וודא שהוא מסומן כ-"Editor"
8. לחץ "Share"

✅ עכשיו ה-bot יכול לכתוב ולקרוא מהגיליון!

---

## 🚀 שלב 1: העלאה ל-GitHub

### 1.1 צור repository חדש ב-GitHub
1. היכנס ל-https://github.com
2. לחץ על "+" למעלה → "New repository"
3. תן שם (לדוגמה: `stock-trading-game`)
4. **חשוב**: בחר **Public** (Streamlit Cloud דורש זאת)
5. לחץ "Create repository"

### 1.2 העלה את הקבצים
שתי דרכים:

**דרך A - דרך הדפדפן (קל):**
1. ב-repository שיצרת, לחץ "Add file" → "Upload files"
2. גרור את 3 הקבצים: `app.py`, `requirements.txt`, `README.md`
3. לחץ "Commit changes"

**דרך B - דרך Git (מתקדם):**
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/[USERNAME]/stock-trading-game.git
git push -u origin main
```

---

## 🔐 שלב 2: הגדרת Streamlit Cloud

### 2.1 התחבר ל-Streamlit Cloud
1. לך ל-https://share.streamlit.io
2. לחץ "Sign in with GitHub"
3. אשר הרשאות

### 2.2 פרוס את האפליקציה
1. לחץ "New app"
2. בחר את ה-repository שיצרת
3. Branch: `main`
4. Main file path: `app.py`
5. **עוד לא תלחץ Deploy!** - קודם צריך להגדיר Secrets

### 2.3 הגדרת Secrets (חשוב!)
לפני Deploy, לחץ על "Advanced settings" → "Secrets"

העתק והדבק את הטקסט הבא, **עם שינוי הפרטים שלך**:

```toml
# ========== רשימת תלמידים ==========
[users]
# שנה את השמות והסיסמאות למשהו אמיתי!
# פורמט: שם_משתמש = "סיסמה"

תלמיד1 = "1234"
תלמיד2 = "5678"
תלמיד3 = "abcd"

# הוסף כמה תלמידים שצריך...

# ========== Google Service Account ==========
[gcp_service_account]
# פתח את קובץ ה-JSON שהורדת בשלב 0.4
# והעתק את כל התוכן שלו לכאן (בדיוק כמו שהוא!)
# זה אמור להיראות בערך ככה:

type = "service_account"
project_id = "stock-trading-game-123456"
private_key_id = "abc123def456..."
private_key = "-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----\n"
client_email = "sheets-bot@stock-trading-game-123456.iam.gserviceaccount.com"
client_id = "123456789..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

**⚠️ חשוב מאוד:**
1. שנה את שמות המשתמשים והסיסמאות בחלק `[users]`!
2. פתח את קובץ ה-JSON שהורדת והעתק את **כל התוכן** שלו לחלק `[gcp_service_account]`
3. רק **אתה** יכול לראות את ה-Secrets האלה
4. גם אם הקוד ציבורי - הסיסמאות והמפתחות פרטיים!

💡 **טיפ**: הדרך הכי קלה להעתיק את ה-JSON:
1. פתח את קובץ ה-JSON בעורך טקסט (Notepad, VSCode...)
2. Ctrl+A (בחר הכל)
3. Ctrl+C (העתק)
4. הדבק במקום החלק של `[gcp_service_account]` (החלף את הדוגמה)

### 2.4 Deploy
עכשיו לחץ "Deploy"!

המערכת תתחיל להתקין - זה לוקח כ-2-3 דקות.

---

## ✅ שלב 3: בדיקה

1. כשההתקנה תסתיים, תקבל קישור כמו: `https://your-app.streamlit.app`
2. פתח אותו
3. התחבר עם אחד משמות המשתמש שהגדרת
4. בדוק שהמערכת עובדת!

---

## 🎯 שימוש במערכת

### למורה:
1. שתף את הקישור עם התלמידים
2. תן להם שמות משתמש וסיסמאות
3. עקוב אחרי הביצועים שלהם

### לתלמידים:
1. התחבר עם שם משתמש וסיסמה
2. כל תלמיד מתחיל עם 10,000 ₪
3. קנה ומכור מניות
4. עקוב אחרי הרווח/הפסד שלך

---

## 📝 עריכת רשימת תלמידים

אם צריך להוסיף/להסיר תלמידים:

1. היכנס ל-https://share.streamlit.io
2. לחץ על האפליקציה שלך
3. Settings → Secrets
4. ערוך את רשימת ה-users
5. שמור - האפליקציה תתחדש אוטומטית

---

## 🐛 פתרון בעיות

**בעיה: "Invalid credentials"**
- בדוק שהשם והסיסמה נכונים ב-Secrets (חלק `[users]`)

**בעיה: "Module not found"**
- בדוק שה-requirements.txt הועלה נכון
- וודא שיש בו גם את `gspread` ו-`oauth2client`

**בעיה: "Error connecting to Google Sheets"**
1. וודא ששם הגיליון הוא בדיוק: "בורסת הכיתה - נתונים"
2. בדוק שהגיליון משותף עם ה-client_email מה-JSON
3. וודא שהעתקת את **כל** תוכן קובץ ה-JSON ל-Secrets
4. בדוק שאין רווחים מיותרים בתחילת או בסוף ה-private_key

**בעיה: "Sheet not found"**
- שם הגיליון חייב להיות **בדיוק**: "בורסת הכיתה - נתונים" (כולל המקפים והרווחים)
- אם שמית אחרת - שנה בקוד (שורה 29 ב-app.py)

**בעיה: סימול מניה לא עובד**
- וודא שהסימול נכון (לדוגמה: AAPL ולא Apple)
- נסה סימולים פופולריים: AAPL, MSFT, GOOGL, TEVA

**בעיה: המחירים לא מתעדכנים**
- API חינמי יכול להיות עם עיכוב של 15-20 דקות
- זה נורמלי ולא פוגע בחוויה

**בעיה: נתונים לא נשמרים**
1. פתח את הגיליון ב-Google Sheets
2. בצע עסקה באפליקציה
3. רענן את הגיליון - אמור לראות את העדכון
4. אם לא - בדוק את ההרשאות (Editor) של ה-Service Account

---

## 🔧 התאמות אישיות

רוצה לשנות משהו? ערוך את `app.py`:

- **תקציב התחלתי**: שורה 57 - `'cash': 10000`
- **עמלה**: שורה 109 - `amount * 0.001` (זה 0.1%)
- **מינימום עמלה**: שורה 110 - `max(commission, 5)`

אחרי עריכה - push ל-GitHub, והאפליקציה תתעדכן אוטומטית!

---

## 💡 טיפים לשימוש בכיתה

1. **מסחר מוגבל**: תגביל מסחר לפעם ביום כדי למנוע מסחר אימפולסיבי
2. **דיונים**: עצור ודבר על החלטות אחרי אירועים גדולים בשוק
3. **מחקר**: עודד תלמידים לחקור חברות לפני קנייה
4. **יומן**: בקש מתלמידים לרשום למה הם קונים/מוכרים
5. **תחרות**: הכרז על מקום ראשון בסוף התקופה!

---

## 📊 צפייה בנתונים (רק למורה!)

אחד היתרונות הגדולים של השימוש ב-Google Sheets:

1. **פתח את הגיליון** "בורסת הכיתה - נתונים"
2. **תראה את כל התיקים** של כל התלמידים
3. **עקוב בזמן אמת** - הגיליון מתעדכן אוטומטית
4. **ייצא ל-Excel** - File → Download → Excel
5. **צור גרפים** - תוכל לבנות גרפים מהנתונים

**עמודות בגיליון:**
- `username` - שם התלמיד
- `cash` - כסף נזיל (₪)
- `stocks` - המניות שלו (פורמט JSON)
- `history` - כל העסקאות (פורמט JSON)

💡 **רעיון**: תוכל להעתיק את הגיליון כל שבוע לארכיון ולהשוות ביצועים!

---

## 📞 צריך עזרה?

אם משהו לא עובד - בדוק שוב את:
1. ה-Secrets מוגדרים נכון
2. כל 3 הקבצים ב-GitHub
3. השם של הקובץ הראשי הוא `app.py` (לא `App.py` או משהו אחר)

בהצלחה! 🚀
