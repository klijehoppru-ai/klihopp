import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="Анализ PDF", layout="wide")

def extract_text_from_pdf(file, progress_bar):
    """Извлекает текст и структуру страниц из PDF"""
    pages_data = []
    with pdfplumber.open(file) as pdf:
        total_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            tables = page.extract_tables()
            pages_data.append({
                "page_num": i + 1,
                "text": text,
                "tables": tables
            })
            # Обновляем прогресс бар
            progress_bar.progress((i + 1) / total_pages, text=f"Обработка страницы {i + 1} из {total_pages}")
    return pages_data

def find_keywords(pages_data):
    """Ищет ключевые слова и резьбы"""
    results = []
    keywords = ["строг", "фрез"]
    # Паттерн для резьбы М1-М50
    thread_pattern = re.compile(r'[Рр]езьба\s*[Мм]\s*(\d{1,2})(?:\s*х|\s*–|\s*-|\s)?', re.IGNORECASE)
    
    for page in pages_data:
        text = page["text"]
        lines = text.split('\n')
        
        for line_idx, line in enumerate(lines):
            # Поиск простых слов
            for kw in keywords:
                if kw.lower() in line.lower():
                    results.append({
                        "type": "Ключевое слово",
                        "found": line.strip(),
                        "page": page["page_num"],
                        "context": f"Строка {line_idx+1}"
                    })
            
            # Поиск резьбы
            matches = thread_pattern.findall(line)
            if matches:
                for m in matches:
                    try:
                        val = int(m)
                        if 1 <= val <= 50:
                            results.append({
                                "type": "Резьба",
                                "found": f"Резьба М{val}",
                                "page": page["page_num"],
                                "context": line.strip()
                            })
                    except ValueError:
                        pass
    return results

def find_part_numbers(pages_data):
    """Ищет номера деталей в таблицах под заголовком 'Деталь №'"""
    parts = []
    
    for page in pages_data:
        tables = page["tables"]
        if not tables:
            continue
            
        for table in tables:
            if not table:
                continue
            
            # Ищем заголовок "Деталь №" (или похожие вариации)
            header_row_idx = -1
            col_idx = -1
            
            for r_idx, row in enumerate(table):
                if row:
                    clean_row = [str(cell).strip() if cell else "" for cell in row]
                    full_header = " ".join(clean_row)
                    if "деталь" in full_header.lower() and ("№" in full_header or "номер" in full_header.lower()):
                        # Пытаемся найти колонку с номером
                        for c_idx, cell in enumerate(clean_row):
                            if "№" in str(cell) or "номер" in str(cell).lower():
                                header_row_idx = r_idx
                                col_idx = c_idx
                                break
                        if col_idx != -1:
                            break
                        # Если просто заголовок таблицы, берем следующую колонку как номер? 
                        # Обычно номер первой колонкой после заголовка или внутри него
                        # Упрощение: если нашли строку заголовка, считаем что номера в следующей строке в той же колонке где есть цифры
                    
                    # Альтернативный поиск: если в ячейке просто "Деталь №"
                    for c_idx, cell in enumerate(clean_row):
                        if cell and "деталь" in cell.lower() and "№" in cell:
                             header_row_idx = r_idx
                             col_idx = c_idx
                             break
                    if col_idx != -1:
                        break
            
            # Если заголовок найден, собираем данные из следующих строк
            if header_row_idx != -1 and col_idx != -1:
                for r_idx in range(header_row_idx + 1, len(table)):
                    row = table[r_idx]
                    if row and len(row) > col_idx:
                        val = row[col_idx]
                        if val and str(val).strip().isdigit():
                            # Пытаемся найти марку (обычно в соседней колонке)
                            brand = ""
                            if len(row) > col_idx + 1:
                                brand = str(row[col_idx+1]).strip()
                            
                            parts.append({
                                "part_number": str(val).strip(),
                                "page": page["page_num"],
                                "brand": brand if brand else "Не найдена",
                                "context": "Таблица"
                            })
    return parts

st.title("📄 Анализатор PDF файлов")
st.markdown("""
Приложение ищет:
- Слова: **строг**, **фрез**
- Резьбы: **М1 – М50**
- Номера позиций деталей из таблиц (**Деталь №**)
""")

uploaded_file = st.file_uploader("Загрузите PDF файл", type="pdf")

if uploaded_file is not None:
    # Создаем прогресс бар
    progress_bar = st.progress(0)
    with st.spinner("Обработка файла..."):
        pages_data = extract_text_from_pdf(uploaded_file, progress_bar)
        
        # Поиск ключевых слов и резьб
        keyword_results = find_keywords(pages_data)
        
        # Поиск деталей
        part_results = find_part_numbers(pages_data)
        
        # Заполняем прогресс бар до 100%
        progress_bar.progress(1.0, text="Готово!")
        
        st.success(f"Файл обработан! Страниц: {len(pages_data)}")
        
        # Вкладка 1: Ключевые слова и резьбы
        st.subheader("🔍 Найденные слова и резьбы")
        if keyword_results:
            df_kw = st.dataframe(keyword_results, use_container_width=True, hide_index=True)
        else:
            st.info("Слова 'строг', 'фрез' и резьбы М1-М50 не найдены.")
            
        # Вкладка 2: Детали
        st.subheader("⚙️ Найденные позиции деталей")
        if part_results:
            df_parts = st.dataframe(part_results, use_container_width=True, hide_index=True)
        else:
            st.warning("Номера деталей в таблицах с заголовком 'Деталь №' не найдены.")
else:
    st.info("Пожалуйста, загрузите PDF файл для начала анализа.")
