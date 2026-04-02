# Radar de Novedades Editoriales (MVP Fase 2)

Aplicación local (un solo ordenador) hecha con **Python + Streamlit + SQLite**.

## Qué incluye esta versión

- 4 pantallas:
  - Inicio
  - Configurar radar
  - Novedades
  - Shortlist
  - Briefing
- Hasta 12 temas.
- Hasta 5 subtemas por tema.
- Exclusiones por tema.
- Configuración editorial por tema:
  - idioma principal,
  - solo no ficción,
  - ventana temporal (30/60/90),
  - autores preferidos,
  - editoriales preferidas.
- Ingestión real de libros desde:
  - Google Books
  - Open Library
- Normalización a una estructura común de libro.
- Dedupe simple por `titulo + autor`.
- Score editorial inicial (0-100).
- Estados por libro: `guardado`, `descartado`, `siguiendo`.
- Briefing editorial semanal con patrones básicos.

## Requisitos

- Python 3.10+

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

## Uso rápido de Fase 2

1. Entra en **Inicio** para ver estado y siguiente paso recomendado.
2. Ve a **Configurar radar** y crea al menos un tema con preferencias editoriales.
3. Añade subtemas (máx. 5).
4. Entra en **Novedades** y pulsa **Buscar novedades reales**.
5. Revisa libros detectados y cambia estado (`guardado`, `descartado`, `siguiendo`).
6. Consulta **Shortlist** y **Briefing**.

## Variables de entorno / credenciales

- Esta fase usa endpoints públicos de Google Books y Open Library.
- **No requiere credenciales obligatorias** para el flujo básico actual.
- Si en una siguiente fase quieres cuota dedicada en Google Books, se podrá añadir API key como variable de entorno.

## Notas

- La base de datos se crea automáticamente al iniciar (`radar_editorial_social.db`).
- No hay autenticación ni multiusuario en esta fase.
- Si una fuente externa falla temporalmente, la app muestra aviso y continúa con la otra.
