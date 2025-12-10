from flask import Flask, render_template_string, request
from playwright.sync_api import sync_playwright
import urllib.parse
import os
import time
import sqlite3
import re

# Inicializamos la aplicación Flask
app = Flask(__name__)
DB_NAME = "maker_final.db"  # Nombre del archivo de base de datos local

# --- FRONTEND (HTML + CSS + JS) ---
# Esta variable contiene toda la interfaz gráfica.
# Incluye estilos CSS para el "Modo Oscuro" y las tarjetas de resultados.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title> MakerWorld Scraper</title>
    <style>
        /* ESTILOS GENERALES: Fondo oscuro y tipografía limpia */
        body { font-family: 'Segoe UI', sans-serif; background: #222; padding: 20px; color: #ddd; }
        .container { max-width: 1100px; margin: 0 auto; }
        
        h1 { text-align: center; color: #00e676; margin-bottom: 5px; }
        p { text-align: center; color: #888; margin-bottom: 30px; }

        /* PANEL DE CONTROL: Formulario de búsqueda */
        .controls { 
            background: #333; padding: 25px; border-radius: 12px; 
            display: flex; gap: 15px; margin-bottom: 40px; align-items: flex-end; flex-wrap: wrap; border: 1px solid #444;
        }
        
        .input-group { flex: 1; min-width: 200px; }
        .input-group label { display: block; font-size: 12px; font-weight: bold; color: #aaa; margin-bottom: 5px; text-transform: uppercase; }
        
        input, select { width: 100%; padding: 12px; border: 1px solid #555; background: #222; color: white; border-radius: 8px; font-size: 16px; box-sizing: border-box; }
        
        /* BOTÓN DE ESCANEO */
        button { 
            padding: 12px 30px; background: #00e676; color: black; border: none; 
            border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 16px; 
            height: 46px; transition: 0.2s; 
        }
        button:hover { background: #00b359; }

        /* MENSAJE DE CARGA (Oculto por defecto) */
        .loading { display: none; text-align: center; font-size: 18px; color: #00e676; background: #1a3322; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #00e676;}

        /* SECCIONES Y TARJETAS DE MODELOS */
        .category-section { margin-bottom: 50px; border-top: 1px solid #444; padding-top: 20px; }
        .cat-title { font-size: 28px; color: #fff; border-left: 5px solid #00e676; padding-left: 15px; margin-bottom: 20px; }

        .cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }

        .card { 
            background: #333; border-radius: 10px; overflow: hidden; 
            border: 1px solid #444; transition: transform 0.2s; display: flex; flex-direction: column;
        }
        .card:hover { transform: translateY(-5px); border-color: #00e676; }
        
        .card-header { position: relative; height: 220px; }
        .thumb { width: 100%; height: 100%; object-fit: cover; background: #111; }
        
        /* BADGE DE RANKING (#1, #2...) */
        .rank-badge { 
            position: absolute; top: 10px; left: 10px; background: #00e676; color: black; 
            width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; 
            font-weight: bold; border-radius: 50%; 
        }
        
        .info { padding: 15px; flex: 1; display: flex; flex-direction: column; justify-content: space-between; }
        .model-link { font-size: 18px; font-weight: bold; color: #fff; text-decoration: none; display: block; margin-bottom: 10px; line-height: 1.3; }
        .model-link:hover { color: #00e676; }
        
        /* ETIQUETAS DE CARACTERÍSTICAS (Material, Relleno, etc) */
        .tags-container { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 15px; }
        .tag { font-size: 11px; padding: 4px 8px; border-radius: 4px; font-weight: bold; color: #fff; background: #444; border: 1px solid #555; }
        
        /* Colores específicos para cada tipo de etiqueta */
        .tag-mat { border-color: #2196f3; color: #90caf9; background: rgba(33, 150, 243, 0.1); }
        .tag-cal { border-color: #4caf50; color: #a5d6a7; background: rgba(76, 175, 80, 0.1); }
        .tag-imp { border-color: #ff9800; color: #ffcc80; background: rgba(255, 152, 0, 0.1); }
        .tag-inf { border-color: #9c27b0; color: #ce93d8; background: rgba(156, 39, 176, 0.1); }
        
        /* ANÁLISIS DE IA (Dificultad y Razón) */
        .ai-analysis {
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #444;
        }
        .diff-text { font-weight: bold; font-size: 12px; margin-right: 5px; }
        /* Colores dinámicos según dificultad */
        .diff-Baja { color: #00e676; } /* Verde */
        .diff-Media { color: #ffeb3b; } /* Amarillo */
        .diff-Alta { color: #ff5252; } /* Rojo */
        
        .ai-reason { font-size: 11px; color: #aaa; font-style: italic; display: block; margin-top: 3px; }

    </style>
    <script>function load(){document.getElementById('loading').style.display='block';}</script>
</head>
<body>
    <div class="container">
        <h1>🕵️ MakerWorld Scraper </h1>
        
        <form method="POST" class="controls" onsubmit="load()">
            <div class="input-group" style="flex: 2;">
                <label>BÚSQUEDA</label>
                <input type="text" name="keywords" placeholder="Ej: Pokemon, Navidad" required value="{{ keywords }}">
            </div>

            <div class="input-group">
                <label>TIEMPO</label>
                <select name="dias">
                    <option value="0" {% if dias == '0' %}selected{% endif %}>Todo el tiempo</option>
                    <option value="7" {% if dias == '7' %}selected{% endif %}>Última semana</option>
                    <option value="30" {% if dias == '30' %}selected{% endif %}>Último mes</option>
                </select>
            </div>

            <div class="input-group">
                <label>ORDENAR POR</label>
                <select name="orden">
                    <option value="hotScore" {% if orden == 'hotScore' %}selected{% endif %}>🔥 Tendencia</option>
                    <option value="likeCount" {% if orden == 'likeCount' %}selected{% endif %}>❤️ Me Gusta</option>
                    <option value="downloadCount" {% if orden == 'downloadCount' %}selected{% endif %}>⬇️ Descargas</option>
                </select>
            </div>
            
            <button type="submit">ESCANEAR PROFUNDO</button>
        </form>
        
        <div id="loading" class="loading">
            🤖 Analizando modelos con IA Lógica... Por favor espera.
        </div>

        {% if reporte %}
            {% for categoria in reporte %}
            <div class="category-section">
                <h2 class="cat-title">📂 {{ categoria.termino }}</h2>
                <div class="cards-grid">
                    {% for item in categoria.modelos %}
                    <div class="card">
                        <div class="card-header">
                            <div class="rank-badge">#{{ loop.index }}</div>
                            <img src="{{ item.img }}" class="thumb">
                        </div>
                        <div class="info">
                            <a href="{{ item.link }}" target="_blank" class="model-link">{{ item.titulo }}</a>
                            
                            <div class="ai-analysis">
                                <span class="diff-text diff-{{ item.dificultad }}">
                                    Dificultad: {{ item.dificultad }}
                                </span>
                                <span class="ai-reason">
                                    {{ item.razon_ai }}
                                </span>
                            </div>

                            <div class="tags-container">
                                {% if item.material and item.material != 'N/A' %}<span class="tag tag-mat">🧵 {{ item.material }}</span>{% endif %}
                                {% if item.calidad and item.calidad != 'N/A' %}<span class="tag tag-cal">📏 {{ item.calidad }}</span>{% endif %}
                                {% if item.relleno and item.relleno != 'N/A' %}<span class="tag tag-inf">🧱 {{ item.relleno }}</span>{% endif %}
                                {% if item.impresora and item.impresora != 'N/A' %}<span class="tag tag-imp">🖨️ {{ item.impresora }}</span>{% endif %}
                                {% if item.paredes %}<span class="tag tag-inf">Muros: {{ item.paredes }}</span>{% endif %}
                            </div>

                            <div style="font-size:11px; color:#666; margin-top:auto;">🔗 {{ item.link }}</div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endfor %}
        {% endif %}
    </div>
</body>
</html>
"""

# --- BASE DE DATOS (SQLite) ---

def init_db():
    """Crea la tabla si no existe. Esto permite guardar historial de búsquedas."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Creamos columnas para guardar todo lo que scrapeamos (incluyendo la IA)
    c.execute('''
        CREATE TABLE IF NOT EXISTS modelos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            termino TEXT,
            titulo TEXT,
            link TEXT,
            img TEXT,
            material TEXT,
            calidad TEXT,
            relleno TEXT,
            impresora TEXT,
            paredes TEXT,
            dificultad TEXT,
            razon_ai TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def guardar_resultados_db(termino, lista_modelos):
    """Limpia los resultados anteriores para esa palabra clave y guarda los nuevos."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Borramos para no duplicar si buscamos lo mismo dos veces
    c.execute("DELETE FROM modelos WHERE termino = ?", (termino,))
    for m in lista_modelos:
        c.execute("""
            INSERT INTO modelos (termino, titulo, link, img, material, calidad, relleno, impresora, paredes, dificultad, razon_ai) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (termino, m['titulo'], m['link'], m['img'], m['material'], m['calidad'], m['relleno'],
              m['impresora'], m['paredes'], m['dificultad'], m['razon_ai']))
    conn.commit()
    conn.close()


def cargar_resultados_db():
    """Recupera todos los modelos guardados para mostrarlos en el HTML."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Esto permite acceder a columnas por nombre
    c = conn.cursor()
    c.execute("SELECT * FROM modelos ORDER BY id DESC")
    filas = c.fetchall()
    conn.close()

    # Agrupamos los modelos por término de búsqueda para mostrarlos ordenados
    agrupado = {}
    orden_terminos = []
    for row in filas:
        term = row['termino']
        if term not in agrupado:
            agrupado[term] = []
            orden_terminos.append(term)
        agrupado[term].append({
            'titulo': row['titulo'], 'link': row['link'], 'img': row['img'],
            'material': row['material'], 'calidad': row['calidad'], 'relleno': row['relleno'],
            'impresora': row['impresora'], 'paredes': row['paredes'],
            'dificultad': row['dificultad'], 'razon_ai': row['razon_ai']
        })

    return [{'termino': t, 'modelos': agrupado[t]} for t in orden_terminos]

# --- IA LÓGICA (Heurística) ---
# Aquí determinamos la dificultad basándonos en reglas, no en redes neuronales.

def evaluar_dificultad(datos):
    """Calcula la dificultad (Baja/Media/Alta) analizando palabras clave y material."""
    score = 0
    razones = []

    t = datos.get('titulo', '').lower()
    mat = datos.get('material', '').upper()

    # 1. Reglas por Material
    if mat in ['ABS', 'ASA', 'NYLON']:
        score += 3
        razones.append(f"{mat} requiere cerramiento") # Materiales técnicos
    elif mat in ['TPU', 'FLEX']:
        score += 2
        razones.append("Flexible (difícil extrusión)")
    elif mat == 'PETG':
        score += 1 # Un poco más difícil que PLA

    # 2. Reglas por Geometría (Keywords en título)
    if 'support' in t or 'soporte' in t:
        score += 1
        razones.append("Requiere soportes")
    if 'articulated' in t or 'articulado' in t:
        score += 2
        razones.append("Articulado (calibración precisa)")
    if 'print in place' in t:
        score += 1
        razones.append("Print-in-place")

    # 3. Resultado final según puntuación
    if score == 0:
        return "Baja", "Material estándar, geometría simple"
    elif score < 3:
        return "Media", ". ".join(razones)
    else:
        return "Alta", ". ".join(razones)

# --- SCRAPER PROFUNDO (Playwright) ---

def analizar_texto_profundo(texto):
    """Usa Expresiones Regulares (Regex) para extraer datos técnicos de la descripción del modelo."""
    res = {'material': 'N/A', 'calidad': 'N/A',
           'relleno': 'N/A', 'impresora': 'N/A', 'paredes': ''}

    # Busca palabras como PLA, PETG, ABS...
    mat_match = re.search(
        r'\b(PLA|PETG|ABS|TPU|ASA|PVA|PETG-CF|PLA-CF)\b', texto, re.IGNORECASE)
    if mat_match:
        res['material'] = mat_match.group(0).upper()

    # Busca altura de capa (ej: 0.2mm)
    cal_match = re.search(r'(\d+\.\d+)\s*mm', texto, re.IGNORECASE)
    if cal_match:
        res['calidad'] = f"{cal_match.group(1)}mm"

    # Busca porcentaje de relleno (ej: 15%)
    inf_match = re.search(r'(\d+)%\s*(?:infill|relleno)?',
                          texto, re.IGNORECASE)
    if inf_match:
        res['relleno'] = f"{inf_match.group(1)}%"

    # Busca modelos de impresora Bambu Lab
    imp_match = re.search(
        r'\b(A1|A1\s*Mini|X1C|X1-Carbon|P1S|P1P)\b', texto, re.IGNORECASE)
    if imp_match:
        res['impresora'] = imp_match.group(0).upper()

    # Busca número de paredes/muros
    wall_match = re.search(
        r'(\d+)\s*(?:walls|paredes|loops|muros)', texto, re.IGNORECASE)
    if wall_match:
        res['paredes'] = wall_match.group(1)

    return res


def extraer_profundo(keywords_str, dias, orden):
    """
    Función principal del Scraper:
    1. Abre navegador.
    2. Busca la keyword.
    3. Extrae los primeros 5 links.
    4. Entra UNO POR UNO a esos links para analizar el texto completo.
    """
    lista_busqueda = [k.strip() for k in keywords_str.split(',') if k.strip()]
    
    # Creamos una carpeta para guardar la sesión del navegador (cookies/cache)
    # Esto evita que la web nos detecte como bot fácilmente.
    user_data = os.path.join(os.getcwd(), 'maker_final_session')

    with sync_playwright() as p:
        # Lanzamos Chromium NO headless (visible) para ver qué hace
        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data,
            headless=False, # Ponlo en True si no quieres ver la ventana
            viewport={'width': 1280, 'height': 800},
            args=['--disable-blink-features=AutomationControlled'] # Truco anti-bot
        )
        page = browser.new_page()

        for termino in lista_busqueda:
            try:
                # Construcción de la URL de búsqueda con filtros
                base = "https://makerworld.com/es/search/models"
                params = f"?keyword={urllib.parse.quote(termino)}"
                if dias != "0":
                    params += f"&designCreateSince={dias}"
                if orden:
                    params += f"&orderBy={orden}"

                page.goto(base + params)
                
                # Esperamos a que aparezcan los resultados
                try:
                    page.wait_for_selector('a[href*="/models/"]', timeout=8000)
                except:
                    time.sleep(2)

                # Ejecutamos Javascript en el navegador para sacar links e imágenes rápido
                raw_items = page.evaluate("""() => {
                    const links = Array.from(document.querySelectorAll('a[href*="/models/"]'));
                    // Filtramos solo los links que tienen imagen dentro (tarjetas válidas)
                    const validCards = links.filter(a => a.querySelector('img')).map(a => {
                         const img = a.querySelector('img');
                         return { link: a.href, title: img.alt || a.innerText, img: img.src };
                    });
                    // Eliminamos duplicados
                    const seen = new Set();
                    const unique = [];
                    for (const item of validCards) {
                        if (!seen.has(item.link)) { seen.add(item.link); unique.push(item); }
                    }
                    // LIMITAMOS A LOS 5 PRIMEROS para no tardar mucho
                    return unique.slice(0, 5);
                }""")

                modelos_completos = []

                # BUCLE DE EXTRACCIÓN PROFUNDA
                for item in raw_items:
                    link = item['link']
                    try:
                        # Navegamos al detalle del modelo
                        page.goto(link)
                        page.wait_for_load_state('domcontentloaded')
                        time.sleep(1.5) # Pausa humana

                        # Obtenemos todo el texto visible
                        texto_pagina = page.inner_text('body')

                        # 1. Análisis con Regex (buscar "PLA", "20% infill", etc)
                        analisis = analizar_texto_profundo(texto_pagina)
                        analisis['titulo'] = item['title']

                        # 2. Análisis con IA Lógica (calcular dificultad)
                        dif, razon = evaluar_dificultad(analisis)

                        modelos_completos.append({
                            'titulo': item['title'],
                            'link': link,
                            'img': item['img'],
                            'dificultad': dif,
                            'razon_ai': razon,
                            **analisis # Desempaqueta el diccionario de análisis
                        })

                    except Exception as e:
                        print(f"Error entrando al modelo: {e}")

                # Guardamos en SQLite
                guardar_resultados_db(termino, modelos_completos)

            except Exception as e:
                print(f"Error global en '{termino}': {e}")


# --- RUTAS DE FLASK ---

@app.route('/', methods=['GET', 'POST'])
def home():
    """Ruta principal. Maneja tanto mostrar la web como recibir el formulario."""
    keywords = ""
    dias = "7"
    orden = "likeCount"

    # Si el usuario pulsó el botón (POST)
    if request.method == 'POST':
        keywords = request.form.get('keywords')
        dias = request.form.get('dias')
        orden = request.form.get('orden')
        if keywords:
            # Ejecutamos el scraper (esto congelará la web unos segundos/minutos)
            extraer_profundo(keywords, dias, orden)

    # Cargamos datos de la DB y renderizamos el HTML
    reporte = cargar_resultados_db()
    return render_template_string(HTML_TEMPLATE, reporte=reporte, keywords=keywords, dias=dias, orden=orden)


if __name__ == '__main__':
    init_db() # Asegurar que la DB existe al arrancar
    app.run(debug=True, port=5000)