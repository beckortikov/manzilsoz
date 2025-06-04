import pickle
from pathlib import Path

import streamlit_authenticator as stauth  # pip install streamlit-authenticator

import streamlit as st
import pandas as pd
import joblib
import gspread
import time

# Загрузка модели
model = joblib.load('model.pkl')

def authenticate_gspread():
    # Load Google Sheets API credentials
    from read_json import response_json
    response_ = response_json()
    sa = gspread.service_account_from_dict(response_)
    return sa

# Function to save data to Google Sheets
def save_to_gsheet(new_row, max_retries=3):
    for attempt in range(max_retries):
        try:
            # Authenticate with Google Sheets
            gc = authenticate_gspread()

            # Open the spreadsheet
            sh = gc.open("Manzilsoz")
            worksheet = sh.worksheet("ScoringDB")

            # Check if there's any content in the worksheet
            existing_data = worksheet.get_all_values()

            # Get existing headers if they exist
            headers = existing_data[0] if existing_data else None

            if not headers:
                headers = ['Менеджер', 'Филиал', 'Телефон номер', 'ФИО', 'Возраст', 'Пол', 'Сумма кредита', 'Период',
                        'Семейное положение', 'Количество кредитов(история)', 'Результат', 'Вероятность возврата', 'Дата',
                        'Номер документа', 'Сфера деятельности', 'Уровень зарплаты', 'Опыт работы', 'Иждивенцы']
                worksheet.append_row(headers)

            # Convert the new_row DataFrame to a list and append it to the worksheet
            new_row = new_row[['Manager','district', 'phone', 'name', 'age', 'gender', 'amount', 'duration',
                            'marital_status', "credit_history_count", 'Result', 'Probability', 'Date', 'DocumentNumber',
                            'occupation', 'salary_level', 'work_experience', 'dependents']]
            new_row_list = new_row.values.tolist()
            worksheet.append_rows(new_row_list)
            return True
        except Exception as e:
            if attempt == max_retries - 1:  # Last attempt
                st.error(f"Ошибка при сохранении данных: {str(e)}")
                return False
            time.sleep(2)  # Wait before retrying
    return False

st.set_page_config(
    page_title="Kredit Market",
    layout="wide"
)

# Улучшенные стили
st.markdown("""
    <style>
        section[data-testid="stSidebar"] {
            width: 40px !important;
            background-color: white;
        }
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            padding-left: 5rem;
            padding-right: 5rem;
        }
        .stSelectbox {
            margin-bottom: 1rem;
        }
        .stNumberInput {
            margin-bottom: 1rem;
        }
        .stTextInput {
            margin-bottom: 1rem;
        }
        div[data-testid="stVerticalBlock"] > div {
            padding: 0.5rem;
            background-color: #f8f9fa;
            border-radius: 5px;
            margin-bottom: 0.5rem;
        }
        button[kind="primary"] {
            background-color: #ff4b4b;
            color: white;
            border-radius: 5px;
            padding: 0.5rem 2rem;
            margin-top: 1rem;
        }
        .stAlert {
            background-color: #f8d7da;
            color: #721c24;
            padding: 1rem;
            border-radius: 5px;
            margin-bottom: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

names = ["Болтабоев Аслиддин", "Файзиев Тимур"]
usernames = ["aslidin", "timur"]

# load hashed passwords
file_path = Path(__file__).parent / "hashed_pw.pkl"
with file_path.open("rb") as file:
    hashed_passwords = pickle.load(file)

authenticator = stauth.Authenticate(names, usernames, hashed_passwords,
    "sales_dashboard", "abcdef", cookie_expiry_days=30)

name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status == False:
    st.error("Username/password is incorrect")

if authentication_status == None:
    st.warning("Please enter your username and password")

if authentication_status:
    authenticator.logout("Выход", "sidebar")
    st.image("logo manzilsoz.png", use_column_width=False, width=150)
    st.title('Модель скоринга')

    # Создаем 4 колонки для более компактного размещения
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        manager = st.selectbox('Менеджер', [name])
        district_options = {
            "Болтабоев Аслиддин": ["Джаббор Расулов", "Спитамен"],
            "Файзиев Тимур": ["Джаббор Расулов", "Спитамен"]
        }
        available_districts = district_options.get(manager, ["Душанбе"])
        district = st.selectbox('Филиал', available_districts)
        name_input = st.text_input('ФИО', '')
        age = st.number_input('Возраст', value=24, step=1)

    with col2:
        gender = st.selectbox('Пол', ['Мужчина', 'Женщина'])
        marital_status = st.selectbox('Семейный статус',
            ['Женат/Замужем', 'Не женат/Не замужем', 'Вдова/Вдовец', 'Разведен'])
        amount = st.number_input('Сумма рассрочки', value=0,
            help="Введите сумму рассрочки")
        duration = st.selectbox('Срок', [3, 6, 9, 12])

    with col3:
        phone = st.text_input('Телефон номер', value=None,
            placeholder="928009292")
        credit_history_count = st.number_input(
            'Количество рассрочки (история клиента)', value=0, step=1)
        kredit = st.selectbox('Активный кредит в других банках',
            ['Нет', "Да"])
        occupation = st.selectbox('Сфера деятельности',
            ['Торговля', 'Услуги', 'Производство', 'Сельское хозяйство',
             'Государственный служащий', 'Частный сектор', 'Другое'])

    with col4:
        salary_level = st.selectbox('Уровень зарплаты',
            ['до 3000', 'от 3000 до 5000', 'от 5000 до 10000', 'от 10000'])
        work_experience = st.selectbox('Опыт работы',
            ['Нет опыта', 'до 1 года', 'от 1 до 3 лет', 'от 3 до 5 лет', 'от 5 лет'])
        dependents = st.selectbox('Иждивенцы', [1, 2, 3, 4, 5])

    # Центрируем кнопку
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        if st.button('Рассчитать скоринг', type="primary"):
            try:
                current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                document_number = f'Doc_{current_date.replace(" ", "_").replace(":", "_")}'
                mapping_dis = {
                    "Душанбе": "dushanbe",
                    "Худжанд": "khujand",
                    "Пенджикент": "panjakent",
                    "Джаббор Расулов": "j.rasulov",
                    "Спитамен": "spitamen"
                }
                mapping_mar = {
                    'Женат/Замужем': 'married',
                    'Не женат/Не замужем':'single',
                    'Вдова/Вдовец':'widow/widower',
                    'Разведен':'divorced'
                }

                input_data = pd.DataFrame({
                    'age': [age],
                    'amount': [amount],
                    'credit_history_count': [credit_history_count],
                    'district': [mapping_dis[district]],
                    'duration': [duration],
                    'gender': [1 if gender == 'Мужчина' else 0],
                    'marital_status': [mapping_mar[marital_status]],
                })

                prediction = model.predict_proba(input_data)[:, 0]

                # Prepare data for saving
                input_data['Manager'] = manager
                input_data['district'] = district
                input_data['name'] = name_input
                input_data['phone'] = phone
                input_data['Result'] = 'Одобрено' if prediction > 1 - 0.15 else 'Отказано'
                input_data['gender'] = gender
                input_data['marital_status'] = marital_status
                input_data['Probability'] = f'{round(prediction[0]*100, 2)}%'
                input_data['Date'] = current_date
                input_data['DocumentNumber'] = document_number
                input_data['occupation'] = occupation
                input_data['salary_level'] = salary_level
                input_data['work_experience'] = work_experience
                input_data['dependents'] = dependents

                # Save data first
                save_success = save_to_gsheet(input_data)

                # Then show results and generate PDF
                if kredit == "Да":
                    st.error('Отказано! 😞')
                else:
                    st.write(f'Вероятность возврата: {round(prediction[0]*100, 2)}%')
                    if prediction > 1 - 0.15:
                        st.success('Одобрено! 🎉')
                        st.balloons()
                    else:
                        st.error('Отказано! 😞')

                # Generate PDF after showing results
                try:
                    generate_pdf(input_data, document_number, current_date)
                except Exception as e:
                    st.error(f"Ошибка при генерации PDF: {str(e)}")

            except Exception as e:
                st.error(f"Произошла ошибка: {str(e)}")

    with top_right:
        def authenticate_gspread():
            # Load Google Sheets API credentials
            from  read_json import  response_json
            response_ = response_json()
            sa = gspread.service_account_from_dict(response_)
            return sa

        # Function to duplicate data to Google Sheets
        def save_to_gsheet(new_row, max_retries=3):
            for attempt in range(max_retries):
                try:
                    # Authenticate with Google Sheets
                    gc = authenticate_gspread()

                    # Open the spreadsheet
                    sh = gc.open("Manzilsoz")
                    worksheet = sh.worksheet("ScoringDB")

                    # Check if there's any content in the worksheet
                    existing_data = worksheet.get_all_values()

                    # Get existing headers if they exist
                    headers = existing_data[0] if existing_data else None

                    if not headers:
                        headers = ['Менеджер', 'Филиал', 'Телефон номер', 'ФИО', 'Возраст', 'Пол', 'Сумма кредита', 'Период',
                                'Семейное положение', 'Количество кредитов(история)', 'Результат', 'Вероятность возврата', 'Дата',
                                'Номер документа', 'Сфера деятельности', 'Уровень зарплаты', 'Опыт работы', 'Иждивенцы']
                        worksheet.append_row(headers)

                    # Convert the new_row DataFrame to a list and append it to the worksheet
                    new_row = new_row[['Manager','district', 'phone', 'name', 'age', 'gender', 'amount', 'duration',
                                    'marital_status', "credit_history_count", 'Result', 'Probability', 'Date', 'DocumentNumber',
                                    'occupation', 'salary_level', 'work_experience', 'dependents']]
                    new_row_list = new_row.values.tolist()
                    worksheet.append_rows(new_row_list)
                    return True
                except Exception as e:
                    if attempt == max_retries - 1:  # Last attempt
                        st.error(f"Ошибка при сохранении данных: {str(e)}")
                        return False
                    time.sleep(2)  # Wait before retrying
            return False
