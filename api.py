from fastapi import FastAPI, HTTPException, Response, Depends
from pydantic import BaseModel
from typing import Optional
import joblib
import pandas as pd
from datetime import datetime, timedelta
import gspread
from fastapi.middleware.cors import CORSMiddleware
from read_json import response_json
from fpdf import FPDF
from pathlib import Path
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
import pickle
import logging
import os

app = FastAPI()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене укажите конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Настройки JWT
SECRET_KEY = "your-secret-key-stored-in-env"  # В продакшене храните в переменных окружения
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 часа

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Загрузка хэшированных паролей
file_path = Path(__file__).parent / "hashed_pw.pkl"
with file_path.open("rb") as file:
    hashed_passwords = pickle.load(file)

# Модель пользователя
class User(BaseModel):
    username: str
    full_name: str

# Словарь пользователей
USERS = {
    "jakhongir": {"full_name": "Мирзоев Чахонгир", "hashed_password": hashed_passwords[0]},
    "kamoljon": {"full_name": "Нурматов Камолчон", "hashed_password": hashed_passwords[1]},
    "bakhrom": {"full_name": "Махмадияров Бахром", "hashed_password": hashed_passwords[2]},
    "ulugbek": {"full_name": "Зокиров Улугбек", "hashed_password": hashed_passwords[3]}
}

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_user(username: str):
    if username in USERS:
        user_dict = USERS[username]
        return User(username=username, full_name=user_dict["full_name"])

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, USERS[username]["hashed_password"]):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(username)
    if user is None:
        raise credentials_exception
    return user

# Настраиваем логирование
log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{log_directory}/api_{datetime.now().strftime('%Y-%m-%d')}.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Эндпоинт для получения токена
@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    logger.info(f"Login attempt for user: {form_data.username}")
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(f"Successful login for user: {form_data.username}")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    # Добавляем информацию о пользователе в ответ
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "username": user.username,
            "full_name": user.full_name,
            # Добавляем маппинг филиала для менеджера
            "district": {
                "Мирзоев Чахонгир": "Джаббор Расулов",
                "Нурматов Камолчон": "Спитамен",
                "Махмадияров Бахром": "Пенджикент",
                "Зокиров Улугбек": "Худжанд"
            }.get(user.full_name, "Душанбе")
        }
    }

# Загрузка модели
model = joblib.load('model.pkl')

class ScoringRequest(BaseModel):
    manager: str
    district: str
    name: str
    age: int
    gender: str
    marital_status: str
    amount: float
    duration: int
    phone: str
    credit_history_count: int
    has_active_credit: bool

class ScoringResponse(BaseModel):
    manager: str
    district: str
    phone: str
    name: str
    age: int
    gender: str
    amount: float
    duration: int
    marital_status: str
    credit_history_count: int
    result: str
    probability: float
    date: str
    document_number: str

def authenticate_gspread():
    response_ = response_json()
    sa = gspread.service_account_from_dict(response_)
    return sa

def duplicate_to_gsheet(data: dict):
    try:
        gc = authenticate_gspread()
        sh = gc.open("KreditMarket")
        worksheet = sh.worksheet("Scoring")

        existing_data = worksheet.get_all_values()
        headers = existing_data[0] if existing_data else [
            'Менеджер', 'Филиал', 'Телефон номер', 'ФИО', 'Возраст', 'Пол',
            'Сумма кредита', 'Период', 'Семейное положение', 'Количество кредитов(история)',
            'Результат', 'Вероятность возврата', 'Дата', 'Номер документа'
        ]

        if not existing_data:
            worksheet.append_row(headers)

        new_row = [
            data['manager'], data['district'], data['phone'], data['name'],
            data['age'], data['gender'], data['amount'], data['duration'],
            data['marital_status'], data['credit_history_count'], data['result'],
            f"{data['probability']}%", data['date'], data['document_number']
        ]
        worksheet.append_row(new_row)
        logger.info(f"Successfully saved data to Google Sheets for {data['name']}")
    except Exception as e:
        logger.error(f"Error saving to Google Sheets: {str(e)}")
        raise

# Добавим новый эндпоинт для получения информации о текущем пользователе
@app.get("/api/user/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "full_name": current_user.full_name
    }

# Изменим эндпоинт scoring, чтобы он автоматически использовал имя текущего пользователя
@app.post("/api/scoring", response_model=None)
async def calculate_scoring(
    request: ScoringRequest,
    current_user: User = Depends(get_current_user)
):
    logger.info(f"New scoring request from {current_user.full_name} for client: {request.name}")

    request.manager = current_user.full_name

    if request.has_active_credit:
        logger.info(f"Automatic rejection due to active credit for client: {request.name}")
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        document_number = f'Doc_{datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}'
        result = {
            **request.dict(),
            "result": "Отказано",
            "probability": 0,
            "date": current_date,
            "document_number": document_number,
            "pdf_url": f"/api/scoring/pdf/{document_number}"
        }
        try:
            duplicate_to_gsheet(result)
            logger.info(f"Results saved to Google Sheets for document: {document_number}")
        except Exception as e:
            logger.error(f"Failed to save to Google Sheets: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to save results")
        return result

    mapping_dis = {
        "Душанбе": "dushanbe",
        "Худжанд": "khujand",
        "Пенджикент": "panjakent",
        "Джаббор Расулов": "j.rasulov",
        "Спитамен": "spitamen"
    }

    mapping_mar = {
        'Женат/Замужем': 'married',
        'Не женат/Не замужем': 'single',
        'Вдова/Вдовец': 'widow/widower',
        'Разведен': 'divorced'
    }

    input_data = pd.DataFrame({
        'age': [request.age],
        'amount': [request.amount],
        'credit_history_count': [request.credit_history_count],
        'district': [mapping_dis[request.district]],
        'duration': [request.duration],
        'gender': [1 if request.gender == 'Мужчина' else 0],
        'marital_status': [mapping_mar[request.marital_status]],
    })

    try:
        prediction = model.predict_proba(input_data)[:, 0]
        probability = prediction[0]
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        document_number = f'Doc_{current_date.replace(" ", "_").replace(":", "_")}'

        result = {
            **request.dict(),
            "result": "Одобрено" if probability > 0.89 else "Отказано",
            "probability": round(probability * 100, 2),
            "date": current_date,
            "document_number": document_number,
            "pdf_url": f"/api/scoring/pdf/{document_number}"
        }

        logger.info(
            f"Scoring result for {request.name}: {result['result']} "
            f"(probability: {result['probability']}%)"
        )

        try:
            duplicate_to_gsheet(result)
            logger.info(f"Results saved to Google Sheets for document: {document_number}")
        except Exception as e:
            logger.error(f"Failed to save to Google Sheets: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to save results")

        return result

    except Exception as e:
        logger.error(f"Error during scoring calculation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

def generate_pdf(data: dict) -> bytes:
    # Create instance of FPDF class
    pdf = FPDF()

    # Add a page
    pdf.add_page()

    # Set font for the title
    pdf.add_font('DejaVu', '', 'DejaVuSansCondensed.ttf', uni=True)
    pdf.set_font('DejaVu', '', 14)

    # Add logo
    pdf.image('logo manzilsoz.png', x=15, y=15, w=40)
    pdf.ln(20)

    # Title
    pdf.cell(200, 10, txt="Скоринг рассрочки", ln=True, align='C')
    pdf.ln(10)

    # Define variable mapping
    variable_mapping = {
        'manager': 'Менеджер',
        'district': 'Филиал',
        'phone': 'Телефон номер',
        'name': 'ФИО',
        'age': 'Возраст',
        'gender': 'Пол',
        'amount': 'Сумма рассрочки',
        'duration': 'Срок',
        'marital_status': 'Семейное положение',
        'credit_history_count': 'Количество кредитов(история)',
        'result': 'Результат',
        'probability': 'Вероятность возврата',
        'date': 'Дата',
        'document_number': 'Номер документа'
    }

    # Add content using table
    col_width = 80
    row_height = 10
    x_position = (pdf.w - col_width * 2) / 2
    y_position = pdf.get_y()

    for key, label in variable_mapping.items():
        value = str(data.get(key, ''))
        if key == 'probability':
            value = f"{value}%"

        pdf.set_xy(x_position, y_position)
        pdf.cell(col_width, row_height, txt=label, border=1)
        pdf.cell(col_width, row_height, txt=value, border=1)
        pdf.ln(row_height)
        y_position = pdf.get_y()

    # Add signature lines
    pdf.set_xy(x_position, pdf.get_y() + 20)
    pdf.cell(col_width, row_height, txt="Менеджер:", border=0)
    pdf.cell(col_width, row_height, txt="Директор:", border=0)

    # Save to bytes buffer instead of file
    return pdf.output(dest='S').encode('latin-1')

@app.get("/api/scoring/pdf/{document_number}")
async def get_scoring_pdf(document_number: str):
    logger.info(f"PDF request for document {document_number}")
    try:
        gc = authenticate_gspread()
        sh = gc.open("KreditMarket")
        worksheet = sh.worksheet("Scoring")

        all_records = worksheet.get_all_records()
        record = next((r for r in all_records if r['Номер документа'] == document_number), None)

        if not record:
            logger.warning(f"Document not found: {document_number}")
            raise HTTPException(status_code=404, detail="Document not found")

        # Преобразуем данные из записи в нужный формат
        data = {
            'manager': record['Менеджер'],
            'district': record['Филиал'],
            'phone': record['Телефон номер'],
            'name': record['ФИО'],
            'age': record['Возраст'],
            'gender': record['Пол'],
            'amount': record['Сумма кредита'],
            'duration': record['Период'],
            'marital_status': record['Семейное положение'],
            'credit_history_count': record['Количество кредитов(история)'],
            'result': record['Результат'],
            'probability': record['Вероятность возврата'].rstrip('%'),
            'date': record['Дата'],
            'document_number': record['Номер документа']
        }

        # Генерируем PDF
        pdf_content = generate_pdf(data)
        logger.info(f"PDF generated successfully for document {document_number}")
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                'Content-Disposition': f'attachment; filename=scoring_{document_number}.pdf'
            }
        )
    except Exception as e:
        logger.error(f"Error generating PDF for document {document_number}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )