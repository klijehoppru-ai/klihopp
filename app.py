from flask import Flask, request, jsonify, render_template_string
import fitz  # PyMuPDF
import re
import os

app = Flask(__name__)

# HTML шаблон для веб-интерфейса
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Анализатор</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .upload-section {
            text-align: center;
            padding: 40px;
            border: 2px dashed #ccc;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .upload-section:hover {
            border-color: #667eea;
        }
        input[type="file"] {
            display: none;
        }
        .custom-file-upload {
            display: inline-block;
            padding: 12px 24px;
            background-color: #667eea;
            color: white;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        .custom-file-upload:hover {
            background-color: #5a6fd6;
        }
        button {
            padding: 12px 24px;
            background-color: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 20px;
        }
        button:hover {
            background-color: #5a6fd6;
        }
        button:disabled {
            background-color: #ccc;
            cursor: not-allowed;
        }
        .results {
            margin-top: 30px;
        }
        .result-section {
            margin-bottom: 30px;
            padding: 20px;
            background-color: #f9f9f9;
            border-radius: 8px;
        }
        .result-section h2 {
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #667eea;
            color: white;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .highlight {
            background-color: #fff3cd;
            padding: 2px 5px;
            border-radius: 3px;
        }
        .no-results {
            color: #999;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📄 PDF Анализатор</h1>
        <p style="text-align: center; color: #666;">
            Анализ PDF файлов на наличие слов: "строг", "фрез", "резьба М1-М50"<br>
            Поиск номеров позиций деталей из таблицы "Деталь №"
        </p>
        
        <div class="upload-section">
            <label for="file-upload" class="custom-file-upload">
                📁 Выбрать PDF файл
            </label>
            <input id="file-upload" type="file" accept=".pdf" />
            <p id="file-name" style="margin-top: 15px; color: #666;"></p>
            <button onclick="analyzePDF()" id="analyze-btn" disabled>🔍 Анализировать</button>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Анализ файла...</p>
        </div>
        
        <div class="results" id="results" style="display: none;">
            <div class="result-section">
                <h2>🔑 Ключевые слова</h2>
                <div id="keywords-results"></div>
            </div>
            
            <div class="result-section">
                <h2>📋 Номера позиций деталей</h2>
                <div id="positions-results"></div>
            </div>
        </div>
    </div>

    <script>
        let selectedFile = null;
        
        document.getElementById('file-upload').addEventListener('change', function(e) {
            if (e.target.files.length > 0) {
                selectedFile = e.target.files[0];
                document.getElementById('file-name').textContent = 'Выбран файл: ' + selectedFile.name;
                document.getElementById('analyze-btn').disabled = false;
            }
        });
        
        async function analyzePDF() {
            if (!selectedFile) return;
            
            const formData = new FormData();
            formData.append('file', selectedFile);
            
            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            document.getElementById('analyze-btn').disabled = true;
            
            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                displayResults(data);
            } catch (error) {
                alert('Ошибка при анализе файла: ' + error.message);
            } finally {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('analyze-btn').disabled = false;
            }
        }
        
        function displayResults(data) {
            const resultsDiv = document.getElementById('results');
            const keywordsDiv = document.getElementById('keywords-results');
            const positionsDiv = document.getElementById('positions-results');
            
            // Отображение ключевых слов
            if (data.keywords && data.keywords.length > 0) {
                let keywordsHtml = '<table><thead><tr><th>Слово</th><th>Страница</th><th>Контекст</th></tr></thead><tbody>';
                data.keywords.forEach(item => {
                    keywordsHtml += `<tr>
                        <td><span class="highlight">${item.word}</span></td>
                        <td>${item.page}</td>
                        <td>${item.context}</td>
                    </tr>`;
                });
                keywordsHtml += '</tbody></table>';
                keywordsDiv.innerHTML = keywordsHtml;
            } else {
                keywordsDiv.innerHTML = '<p class="no-results">Ключевые слова не найдены</p>';
            }
            
            // Отображение позиций деталей
            if (data.positions && data.positions.length > 0) {
                let positionsHtml = '<table><thead><tr><th>Номер позиции</th><th>Страница</th><th>Марка/Контекст</th></tr></thead><tbody>';
                data.positions.forEach(item => {
                    positionsHtml += `<tr>
                        <td><strong>${item.position}</strong></td>
                        <td>${item.page}</td>
                        <td>${item.mark || 'Не указано'}</td>
                    </tr>`;
                });
                positionsHtml += '</tbody></table>';
                positionsDiv.innerHTML = positionsHtml;
            } else {
                positionsDiv.innerHTML = '<p class="no-results">Номера позиций деталей не найдены</p>';
            }
            
            resultsDiv.style.display = 'block';
        }
    </script>
</body>
</html>
'''

def extract_text_from_pdf(pdf_path):
    """Извлекает текст из PDF файла с информацией о страницах"""
    doc = fitz.open(pdf_path)
    pages_data = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        tables = page.find_tables()
        
        pages_data.append({
            'page_number': page_num + 1,
            'text': text,
            'tables': tables
        })
    
    doc.close()
    return pages_data

def search_keywords(pages_data):
    """Ищет ключевые слова в тексте"""
    keywords_patterns = [
        r'строг\w*',  # строг, строгать, строгальный и т.д.
        r'фрез\w*',   # фрез, фреза, фрезерный и т.д.
        r'резьб\s*м\d+',  # резьба м1, резьба м2, и т.д.
        r'м\d+\s*[-–]\s*м\d+',  # м1-м50, м1–м50
    ]
    
    results = []
    
    for page in pages_data:
        text = page['text']
        page_num = page['page_number']
        
        for pattern in keywords_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end].replace('\n', ' ').strip()
                
                results.append({
                    'word': match.group(),
                    'page': page_num,
                    'context': '...' + context + '...'
                })
    
    return results

def search_positions(pages_data):
    """Ищет номера позиций деталей в таблицах под заголовком 'Деталь №'"""
    results = []
    
    for page in pages_data:
        page_num = page['page_number']
        tables = page['tables']
        
        if not tables:
            continue
        
        for table in tables:
            try:
                data = table.extract()
                if not data:
                    continue
                
                # Ищем заголовок "Деталь №" или похожие вариации
                header_row_idx = None
                position_col_idx = None
                
                for row_idx, row in enumerate(data):
                    if row:
                        for col_idx, cell in enumerate(row):
                            if cell and re.search(r'детал[ья]\s*№|деталь\s*№|№\s*детал[ья]|позиц', str(cell), re.IGNORECASE):
                                header_row_idx = row_idx
                                position_col_idx = col_idx
                                break
                        if header_row_idx is not None:
                            break
                
                # Если нашли заголовок, извлекаем данные из следующих строк
                if header_row_idx is not None and position_col_idx is not None:
                    for row_idx in range(header_row_idx + 1, len(data)):
                        row = data[row_idx]
                        if row and len(row) > position_col_idx:
                            position_value = row[position_col_idx]
                            if position_value and re.search(r'\d+', str(position_value)):
                                # Пытаемся найти марку в той же строке
                                mark = None
                                for cell in row:
                                    if cell and re.search(r'марк|марка|материал|сталь|гост', str(cell), re.IGNORECASE, re.I):
                                        mark = cell
                                        break
                                
                                results.append({
                                    'position': str(position_value).strip(),
                                    'page': page_num,
                                    'mark': mark
                                })
            except Exception as e:
                continue
    
    # Также ищем в обычном тексте паттерны позиций
    for page in pages_data:
        text = page['text']
        page_num = page['page_number']
        
        # Ищем паттерны типа "Поз. 1", "Позиция 1", "№1" и т.д.
        patterns = [
            r'поз\.?\s*(\d+)',
            r'позици[яи]\s*(\d+)',
            r'№\s*(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                position_num = match.group(1)
                # Проверяем, что это не часть другого числа
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                
                # Извлекаем возможную марку из контекста
                mark_match = re.search(r'марк[аи]?\s*[:\-]?\s*([A-Za-zА-Яа-я0-9\s]+)', context, re.IGNORECASE)
                mark = mark_match.group(1).strip() if mark_match else None
                
                results.append({
                    'position': position_num,
                    'page': page_num,
                    'mark': mark
                })
    
    # Удаляем дубликаты
    seen = set()
    unique_results = []
    for result in results:
        key = (result['position'], result['page'])
        if key not in seen:
            seen.add(key)
            unique_results.append(result)
    
    return unique_results

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if not file.filename.endswith('.pdf'):
        return jsonify({'error': 'Загрузите PDF файл'}), 400
    
    # Сохраняем временный файл
    temp_path = f'/tmp/{file.filename}'
    file.save(temp_path)
    
    try:
        # Извлекаем текст из PDF
        pages_data = extract_text_from_pdf(temp_path)
        
        # Ищем ключевые слова
        keywords = search_keywords(pages_data)
        
        # Ищем номера позиций деталей
        positions = search_positions(pages_data)
        
        return jsonify({
            'keywords': keywords,
            'positions': positions
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        # Удаляем временный файл
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
