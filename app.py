import pickle
from pathlib import Path

import streamlit_authenticator as stauth  # pip install streamlit-authenticator

import streamlit as st
import pandas as pd
import joblib
import gspread

# Загрузка модели

model = joblib.load('model.pkl')


# Функция для генерации PDF
from datetime import datetime
from fpdf import FPDF
from PIL import Image



st.set_page_config(
        page_title="Kredit Market",
        layout="wide"
)

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
    st.markdown(
    """
    <style>
        section[data-testid="stSidebar"] {
            width: 40px important;
            background-color: white;
        }
        .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
    </style>
    """,
    unsafe_allow_html=True,
)
    authenticator.logout("Выход", "sidebar")
    def generate_pdf(data, document_number, date):
        # Create instance of FPDF class
        pdf = FPDF()

        # Add a page
        pdf.add_page()

        # Set font for the title
        pdf.add_font('DejaVu', '', 'DejaVuSansCondensed.ttf', uni=True)
        pdf.set_font('DejaVu', '', 14)

        pdf.image('logo manzilsoz.png', x=15, y=15, w=40)
        pdf.ln(20)
        # Title
        pdf.cell(200, 10, txt="Скоринг рассрочки",  ln=True, align='C')
        pdf.ln(10)  # Add a little space after the title


        # Define the variables list on the left side
        # Mapping between internal variable names and human-readable names
        variable_mapping = {
            'Manager': 'Менеджер',
            'district': 'Филиал',
            'phone': 'Телефон номер',
            'name': 'ФИО',
            'age': 'Возраст',
            'gender': 'Пол',
            'amount': 'Сумма рассрочки',
            'duration': 'Срок',
            'marital_status': 'Семейное положение',
            'credit_history_count': 'Количество кредитов(история)',
            'Result': 'Результат',
            'Probability': 'Вероятность возврата',
            'Date': 'Дата',
            'DocumentNumber': 'Номер документа'
        }

        var = ['Manager', 'district', 'phone', 'name', 'age', 'gender', 'amount', 'duration',
            'marital_status', 'credit_history_count', 'Result', 'Probability', 'Date', 'DocumentNumber']

        # Add content to the PDF using a table
        pdf.set_fill_color(255, 255, 255)  # Set white fill color
        col_width = 80
        row_height = 10
        x_position = (pdf.w - col_width * 2) / 2  # Calculate x position to center the table
        y_position = pdf.get_y()
        for var_name in var:
            # Get the human-readable name corresponding to the internal variable name
            variable = variable_mapping.get(var_name, '')
            value = data.get(var_name, [''])[0]  # Get the value from data or empty string if not found
            pdf.set_xy(x_position, y_position)
            pdf.cell(col_width, row_height, txt=variable, border=1, fill=False)
            pdf.cell(col_width, row_height, txt=str(value), border=1, fill=False)
            pdf.ln(row_height)
            y_position = pdf.get_y()
        pdf.set_xy(x_position, pdf.get_y() + 20)  # Move down 10 units
        pdf.cell(col_width, row_height, txt="Менеджер:", border=0, fill=False)
        pdf.cell(col_width, row_height, txt="Директор:", border=0, fill=False)

        # current_x = pdf.get_x()  # Get current X position
        # current_y = pdf.get_y()  # Get current Y position

        # # Calculate new positions with desired margins
        # new_x = current_x -100 # Add 20mm to the right
        # new_y = current_y + 15   # Subtract 5mm from the top (moving upwards)

        # # Set new position
        # pdf.set_xy(new_x, new_y)
        # pdf.cell(0, 10, 'Менеджер:', 0, 0, 'L')
        # pdf.cell(0, 10, 'Директор:', 0, 0, 'C')
        # Output the cell
        # pdf.cell(0, 10, txt="Подпись: ______________________", ln=True, align='R')

        # Save the PDF to a file
        pdf.output("result.pdf")

        # Return the PDF file name or content depending on your requirement
        with open("result.pdf", "rb") as pdf_file:
            PDFbyte = pdf_file.read()

        st.download_button(label="Скачать документ",
                        data=PDFbyte,
                        file_name="test.pdf",
                        mime='application/octet-stream')

    st.image("logo manzilsoz.png", use_column_width=False, width=300)
    # Ввод данных с использованием инпутов
    st.title('Модель скоринга')


    top_left, top_right = st.columns((3, 1))
    prediction = None
    input_data = None
    document_number = None
    current_date = None
    kredit = None
    with top_left:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                manager = st.selectbox(r'$\textsf{\normalsize Менеджер}$', [name])
                district_options = {
                    "Болтабоев Аслиддин": "Джаббор Расулов",
                    "Файзиев Тимур": "Джаббор Расулов",
                    "Болтабоев Аслиддин": "Спитамен",
                    "Файзиев Тимур": "Спитамен",
                    "Болтабоев Аслиддин": "Пенджикент",
                    "Файзиев Тимур": "Пенджикент",
                    "Болтабоев Аслиддин": "Худжанд",
                    "Файзиев Тимур": "Худжанд"
                }

                default_district = "Душанбе"  # Default district if no match found

                district = district_options.get(manager, default_district)

                # # Use district variable in your Streamlit app
                # st.write(rf'$\textsf{{\normalsize Филиал}}$: {district}')
                st.selectbox(r'$\textsf{\normalsize Филиал}$', [district])
                name = st.text_input(r'$\textsf{\normalsize ФИО}$', '')
                # surname = st.text_input(r'$\textsf{\normalsize Фамилия}$', '')
                age = st.number_input(r'$\textsf{\normalsize Возраст}$', value=24, step=1)
            with col2:
                gender = st.selectbox(r'$\textsf{\normalsize Пол}$', ['Мужчина', 'Женщина'])
                marital_status = st.selectbox(r'$\textsf{\normalsize Семейный статус}$', ['Женат/Замужем', 'Не женат/Не замужем', 'Вдова/Вдовец', 'Разведен'])
                amount = st.number_input(r'$\textsf{\normalsize Сумма рассрочки}$', value=0, placeholder="Телефон нархи")
                duration = st.selectbox(r'$\textsf{\normalsize Срок}$', [3, 6, 9, 12])

            with col3:
                phone = st.text_input(r'$\textsf{\normalsize Телефон номер}$', value=None, placeholder="928009292")

                credit_history_count = st.number_input(r'$\textsf{\normalsize Количество рассрочки (история клиента)}$', value=0, step=1)
                kredit = st.selectbox(r'$\textsf{\normalsize Активный кредит в других банках}$', ['Нет', "Да"])
                if st.button('Получить результат', type="primary"):
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
                        'Женат/Замужем': 'married', 'Не женат/Не замужем':'single', 'Вдова/Вдовец':'widow/widower', 'Разведен':'divorced'
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


                    input_data['Manager'] = manager
                    input_data['district'] = district
                    input_data['name'] = name
                    # input_data['surname'] = surname
                    input_data['phone'] = phone
                    input_data['Result'] = 'Одобрено' if prediction > 1 - 0.15 else 'Отказано'
                    input_data['gender'] = gender
                    input_data['marital_status'] = marital_status
                    input_data['Probability'] = f'{round(prediction[0]*100, 2)}%'
                    input_data['Date'] = current_date
                    input_data['DocumentNumber'] = document_number
    with top_right:
        def authenticate_gspread():
            # Load Google Sheets API credentials
            from  read_json import  response_json
            response_ = response_json()
            sa = gspread.service_account_from_dict(response_)
            return sa

        # Function to duplicate data to Google Sheets
        def duplicate_to_gsheet(new_row):
            # Authenticate with Google Sheets
            gc = authenticate_gspread()

            # Create a new Google Sheets spreadsheet
            sh = gc.open("KreditMarket")

            # Select the first sheet (index 0)
            worksheet = sh.worksheet("Scoring")

            # Check if there's any content in the worksheet
            existing_data = worksheet.get_all_values()

            # Get existing headers if they exist
            headers = existing_data[0] if existing_data else None

            if not headers:
                headers = ['Менеджер', 'Филиал', 'Телефон номер', 'ФИО', 'Возраст', 'Пол', 'Сумма кредита', 'Период', 'Семейное положение', 'Количество кредитов(история)', 'Результат', 'Вероятность возврата', 'Дата', 'Номер документа']
                worksheet.append_row(headers)

            # Convert the new_row DataFrame to a list and append it to the worksheet
            new_row = new_row[['Manager','district', 'phone', 'name', 'age', 'gender', 'amount', 'duration', 'marital_status', "credit_history_count",
                                'Result', 'Probability', 'Date', 'DocumentNumber']]
            new_row_list = new_row.values.tolist()
            worksheet.append_rows(new_row_list)

        # Предсказание
        st.subheader('Результат:')
        if kredit is not None:
            if kredit == "Да":
                st.error(r'$\textsf{\Large Отказано! 😞}$')
            else:
                if prediction is not None:
                    st.write(f'Вероятность возврата: {round(prediction[0]*100, 2)}%')
                    if prediction > 1 - 0.15:
                        if_success="Одобрено!"
                        htmlstr1=f"""<p style='background-color:green;
                                                                color:white;
                                                                font-size:35px;
                                                                border-radius:3px;
                                                                line-height:60px;
                                                                padding-left:17px;
                                                                opacity:0.6'>
                                                                {if_success}</style>
                                                                <br></p>"""
                        st.markdown(htmlstr1,unsafe_allow_html=True)
                        # st.success(r'$\textsf{\Large }$')
                        st.balloons()
                        generate_pdf(input_data, document_number, current_date)
                        duplicate_to_gsheet(input_data)
                    else:
                        st.error(r'$\textsf{\Large Отказано! 😞}$')
                        generate_pdf(input_data, document_number, current_date)
                        duplicate_to_gsheet(input_data)

                    # generate_pdf(input_data, document_number, current_date)
