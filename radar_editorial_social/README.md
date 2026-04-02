# Radar Editorial Social (MVP Fase 1)

Aplicación local (un solo ordenador) hecha con **Python + Streamlit + SQLite**.

## Qué incluye esta versión

- 4 pantallas:
  - Temas
  - Radar
  - Memoria
  - Briefing
- Hasta 3 temas.
- Hasta 3 subtemas por tema.
- Exclusiones por tema.
- Carga manual de señales.
- Ingestión básica desde RSS (URL de feed + límite de entradas).
- Evita duplicados simples de señales (mismo título + misma fuente).
- Score inicial de relevancia (0-100) al guardar cada señal.
- Filtros básicos en Radar por tema y estado.
- Estados por señal: `guardada`, `descartada`, `idea`.
- Briefing semanal simple desde señales guardadas (últimos 7 días).

## Requisitos

- Python 3.10+

## Mover a un nuevo workspace (recomendado)

Si quieres separar este MVP del repo `shadow-ai-diagnostic`, usa:

```bash
cd /workspace/shadow-ai-diagnostic/radar_editorial_social
./export_to_workspace.sh
```

Esto crea/actualiza el workspace independiente en:

- `/workspace/Radar editorial social`

Y luego puedes ejecutarlo así:

```bash
cd "/workspace/Radar editorial social"
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Ejecutar (pasos simples)

1. Entrar a la carpeta del proyecto:

   ```bash
   cd radar_editorial_social
   ```

2. Crear entorno virtual:

   ```bash
   python -m venv .venv
   ```

3. Activar entorno virtual:

   Linux / macOS:
   ```bash
   source .venv/bin/activate
   ```

   Windows (PowerShell):
   ```powershell
   .venv\Scripts\Activate.ps1
   ```

4. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```

5. Lanzar la app:

   ```bash
   streamlit run app.py
   ```

6. Abrir en navegador la URL que muestra Streamlit (normalmente `http://localhost:8501`).

## Uso rápido de RSS

1. Entra en la pantalla **Radar**.
2. En la sección **Ingestión básica desde RSS**:
   - elige un tema (opcional),
   - pega la URL del feed,
   - define cuántas entradas importar.
3. Pulsa **Importar RSS**.
4. Las señales nuevas se guardan en SQLite con:
   - `origin = web/rss`,
   - estado inicial `idea`,
   - score inicial de relevancia.

## Feeds RSS de ejemplo usados

- https://blog.streamlit.io/rss/
- https://openai.com/news/rss.xml
- https://www.theverge.com/rss/index.xml

## Notas

- La base de datos se crea automáticamente al iniciar (`radar_editorial_social.db`).
- No hay autenticación ni multiusuario en esta fase.

## Publicarlo en GitHub (rápido)

1. Crea un repositorio vacío en GitHub (privado o público).
2. Ejecuta:

```bash
cd /workspace/shadow-ai-diagnostic/radar_editorial_social
./export_to_workspace.sh
./publish_to_github.sh <URL_REPO_GITHUB>
```

Ejemplo de URL:

- `git@github.com:tu-org/radar-editorial-social.git`
- `https://github.com/tu-org/radar-editorial-social.git`

> Nota: para que el push funcione, este equipo debe tener acceso a GitHub (SSH key o token).
