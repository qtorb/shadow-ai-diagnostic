import asyncio
import httpx
import ssl
import socket
import re
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TIMEOUT = 12
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

AI_PATTERNS = [
    ("Intercom",         "intercom.io"),
    ("Drift",            "js.drift.com"),
    ("Zendesk Chat",     "zdassets.com"),
    ("HubSpot Chat",     "js.hs-scripts.com"),
    ("Freshchat",        "wchat.freshchat.com"),
    ("Tidio",            "code.tidio.co"),
    ("Crisp",            "client.crisp.chat"),
    ("ChatBase",         "chatbase.co"),
    ("Botpress",         "cdn.botpress.cloud"),
    ("LiveChat",         "cdn.livechatinc.com"),
    ("Voiceflow",        "cdn.voiceflow.com"),
    ("Landbot",          "landbot.io"),
    ("OpenAI API",       "api.openai.com"),
    ("Anthropic API",    "api.anthropic.com"),
    ("LangChain",        "langchain"),
    ("Chainlit",         "chainlit"),
    ("Gradio",           "gradio.app"),
]

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


# ─── HTTP Headers ─────────────────────────────────────────────────────────────

async def check_http_headers(domain: str) -> dict:
    findings = []
    score = 0
    https_ok = False
    csp_value = ""

    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT, follow_redirects=True,
            headers={"User-Agent": UA}, verify=True
        ) as client:
            try:
                resp = await client.get(f"https://{domain}")
                https_ok = True
                score += 5
                h = {k.lower(): v for k, v in resp.headers.items()}

                # HSTS
                if "strict-transport-security" in h:
                    score += 5
                else:
                    findings.append({
                        "id": "hsts_missing", "severity": "high",
                        "title": "HSTS no configurado",
                        "detail": "Sin HSTS los navegadores no fuerzan HTTPS en visitas posteriores.",
                        "recommendation": "Añade: Strict-Transport-Security: max-age=31536000; includeSubDomains"
                    })

                # CSP
                csp_value = h.get("content-security-policy", "")
                if csp_value:
                    score += 6
                    if "'unsafe-inline'" not in csp_value and "'unsafe-eval'" not in csp_value:
                        score += 3
                    else:
                        findings.append({
                            "id": "csp_unsafe", "severity": "medium",
                            "title": "CSP permite inline scripts (unsafe-inline / unsafe-eval)",
                            "detail": "El CSP no restringe eficazmente la ejecución de scripts inline.",
                            "recommendation": "Elimina 'unsafe-inline' del CSP y usa nonces o hashes."
                        })
                else:
                    findings.append({
                        "id": "csp_missing", "severity": "high",
                        "title": "Content-Security-Policy ausente",
                        "detail": "Sin CSP el sitio no controla qué scripts externos (incluidos chatbots IA) pueden ejecutarse.",
                        "recommendation": "Implementa una política CSP que restrinja orígenes de scripts."
                    })

                # X-Frame-Options
                if "x-frame-options" in h:
                    score += 3
                else:
                    findings.append({
                        "id": "xframe_missing", "severity": "medium",
                        "title": "X-Frame-Options no configurado",
                        "detail": "El sitio puede ser embebido en iframes de terceros (clickjacking).",
                        "recommendation": "X-Frame-Options: DENY o SAMEORIGIN"
                    })

                # X-Content-Type-Options
                if h.get("x-content-type-options", "").lower() == "nosniff":
                    score += 3
                else:
                    findings.append({
                        "id": "xcontent_missing", "severity": "low",
                        "title": "X-Content-Type-Options: nosniff ausente",
                        "detail": "Los navegadores pueden interpretar erróneamente el tipo MIME de las respuestas.",
                        "recommendation": "X-Content-Type-Options: nosniff"
                    })

                # Referrer-Policy
                if "referrer-policy" in h:
                    score += 2
                else:
                    findings.append({
                        "id": "referrer_missing", "severity": "low",
                        "title": "Referrer-Policy no configurada",
                        "detail": "Las URLs pueden filtrar información sensible a dominios de terceros.",
                        "recommendation": "Referrer-Policy: strict-origin-when-cross-origin"
                    })

                # Server version disclosure
                server = h.get("server", "")
                if server and re.search(r"\d", server):
                    findings.append({
                        "id": "server_disclosure", "severity": "low",
                        "title": f"Server header revela versión: {server}",
                        "detail": "El servidor expone su software y versión exacta.",
                        "recommendation": "Configura el servidor para ocultar o generalizar el header Server."
                    })
                else:
                    score += 3

                # X-Powered-By
                if "x-powered-by" in h:
                    findings.append({
                        "id": "xpoweredby", "severity": "low",
                        "title": f"X-Powered-By expuesto: {h['x-powered-by']}",
                        "detail": "Este header revela el stack tecnológico del servidor.",
                        "recommendation": "Desactiva X-Powered-By en la configuración del servidor."
                    })
                else:
                    score += 3

            except (httpx.ConnectError, httpx.SSLError, httpx.TimeoutException):
                findings.append({
                    "id": "no_https", "severity": "critical",
                    "title": "HTTPS no accesible o no forzado",
                    "detail": "No se pudo establecer conexión HTTPS con el dominio.",
                    "recommendation": "Instala un certificado SSL/TLS válido y fuerza la redirección HTTPS."
                })

    except Exception as e:
        findings.append({
            "id": "http_error", "severity": "info",
            "title": "No se pudo conectar al dominio",
            "detail": str(e)[:200],
            "recommendation": "Verifica que el dominio sea accesible públicamente."
        })

    return {"score": score, "max_score": 33, "https_ok": https_ok,
            "csp_value": csp_value, "findings": findings}


# ─── Email Security ───────────────────────────────────────────────────────────

async def check_email_security(domain: str) -> dict:
    findings = []
    score = 0
    spf_record = None
    dmarc_record = None

    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.timeout = 5
        resolver.lifetime = 5

        # SPF
        try:
            for rdata in resolver.resolve(domain, "TXT"):
                txt = str(rdata).strip('"')
                if txt.startswith("v=spf1"):
                    spf_record = txt
                    score += 8
                    break
            if not spf_record:
                findings.append({
                    "id": "spf_missing", "severity": "high",
                    "title": "SPF no configurado",
                    "detail": "Sin SPF cualquier servidor puede enviar emails en nombre de este dominio.",
                    "recommendation": "Añade registro TXT: v=spf1 include:... ~all"
                })
        except Exception:
            findings.append({
                "id": "spf_error", "severity": "info",
                "title": "No se pudo verificar SPF",
                "detail": "No se obtuvo respuesta DNS para registros TXT.",
                "recommendation": "Verifica los registros DNS del dominio."
            })

        # DMARC
        try:
            dmarc_record = None
            for rdata in resolver.resolve(f"_dmarc.{domain}", "TXT"):
                txt = str(rdata).strip('"')
                if txt.startswith("v=DMARC1"):
                    dmarc_record = txt
                    score += 7
                    if "p=reject" in txt:
                        score += 5
                    elif "p=quarantine" in txt:
                        score += 3
                        findings.append({
                            "id": "dmarc_quarantine", "severity": "medium",
                            "title": "DMARC en cuarentena, no rechazo",
                            "detail": "DMARC usa p=quarantine en lugar de p=reject.",
                            "recommendation": "Cambia a p=reject para protección total contra spoofing."
                        })
                    else:
                        findings.append({
                            "id": "dmarc_none", "severity": "high",
                            "title": "DMARC con política p=none (solo monitorización)",
                            "detail": "DMARC no aplica ninguna acción sobre emails no autorizados.",
                            "recommendation": "Cambia a p=quarantine o p=reject."
                        })
                    break
            if not dmarc_record:
                raise Exception("No DMARC record found")
        except Exception:
            if not dmarc_record:
                findings.append({
                    "id": "dmarc_missing", "severity": "high",
                    "title": "DMARC no configurado",
                    "detail": "Sin DMARC no hay política de rechazo para emails fraudulentos.",
                    "recommendation": "Añade TXT en _dmarc.dominio: v=DMARC1; p=quarantine; rua=mailto:..."
                })

    except ImportError:
        findings.append({
            "id": "dns_unavailable", "severity": "info",
            "title": "dnspython no instalado",
            "detail": "Instala dnspython para verificación DNS.",
            "recommendation": "pip install dnspython"
        })

    return {"score": score, "max_score": 20,
            "spf_record": spf_record, "dmarc_record": dmarc_record,
            "findings": findings}


# ─── SSL / TLS ────────────────────────────────────────────────────────────────

async def check_ssl(domain: str) -> dict:
    findings = []
    score = 0
    ssl_info = {}

    def _get_ssl():
        ctx = ssl.create_default_context()
        sock = socket.create_connection((domain, 443), timeout=10)
        conn = ctx.wrap_socket(sock, server_hostname=domain)
        cert = conn.getpeercert()
        cipher = conn.cipher()
        version = conn.version()
        conn.close()
        return cert, cipher, version

    try:
        loop = asyncio.get_event_loop()
        cert, cipher, version = await loop.run_in_executor(None, _get_ssl)

        score += 5  # SSL valid and trusted

        not_after_str = cert.get("notAfter", "")
        if not_after_str:
            not_after = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            days_left = (not_after - datetime.now(timezone.utc)).days
            ssl_info["days_until_expiry"] = days_left

            if days_left < 14:
                findings.append({
                    "id": "ssl_expiring_critical", "severity": "critical",
                    "title": f"Certificado SSL expira en {days_left} días",
                    "detail": "El certificado está a punto de expirar.",
                    "recommendation": "Renueva el certificado SSL de inmediato."
                })
            elif days_left < 45:
                findings.append({
                    "id": "ssl_expiring", "severity": "high",
                    "title": f"Certificado SSL expira en {days_left} días",
                    "detail": "El certificado expirará pronto.",
                    "recommendation": "Renueva el certificado SSL."
                })
            else:
                score += 5

        ssl_info["tls_version"] = version
        ssl_info["cipher"] = cipher[0] if cipher else ""

        if version in ("TLSv1.2", "TLSv1.3"):
            score += 5
        else:
            findings.append({
                "id": "tls_outdated", "severity": "high",
                "title": f"Versión TLS obsoleta: {version}",
                "detail": f"{version} tiene vulnerabilidades conocidas.",
                "recommendation": "Configura el servidor para usar únicamente TLS 1.2 o TLS 1.3."
            })

        ssl_info["valid"] = True

    except ssl.SSLCertVerificationError as e:
        findings.append({
            "id": "ssl_invalid", "severity": "critical",
            "title": "Certificado SSL inválido o no confiable",
            "detail": str(e)[:200],
            "recommendation": "Instala un certificado SSL de una CA de confianza."
        })
    except (socket.timeout, ConnectionRefusedError, OSError):
        findings.append({
            "id": "ssl_unreachable", "severity": "critical",
            "title": "Puerto HTTPS (443) no accesible",
            "detail": "No se pudo establecer conexión SSL.",
            "recommendation": "Verifica que el puerto 443 esté abierto y configurado correctamente."
        })
    except Exception as e:
        findings.append({
            "id": "ssl_error", "severity": "info",
            "title": "No se pudo verificar SSL",
            "detail": str(e)[:200],
            "recommendation": "Verifica manualmente la configuración SSL."
        })

    return {"score": score, "max_score": 15, "ssl_info": ssl_info, "findings": findings}


# ─── AI Surface Detection ─────────────────────────────────────────────────────

async def detect_ai_assistants(domain: str) -> dict:
    findings = []
    detected = []
    score = 32

    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT, follow_redirects=True,
            headers={"User-Agent": UA}, verify=True
        ) as client:
            try:
                resp = await client.get(f"https://{domain}")
                html = resp.text

                for name, pattern in AI_PATTERNS:
                    if pattern.lower() in html.lower() and name not in detected:
                        detected.append(name)

                internal_apis = re.findall(
                    r'["\'](/api/(?:chat|message|query|llm|ai|gpt|assistant)[^"\']{0,60})["\']',
                    html, re.IGNORECASE
                )
                if internal_apis:
                    detected.append(f"Endpoints IA internos ({', '.join(set(internal_apis[:3]))})")

                if detected:
                    score -= 22
                    findings.append({
                        "id": "ai_detected", "severity": "high",
                        "title": f"Asistente(s) IA detectado(s): {', '.join(detected)}",
                        "detail": (
                            "Se han identificado uno o más asistentes de IA embebidos. "
                            "Estos sistemas pueden ser vectores de prompt injection, data leakage "
                            "o manipulación semántica si no están correctamente configurados."
                        ),
                        "recommendation": (
                            "Audita los prompts del sistema de cada asistente. "
                            "Implementa CSP estricto que restrinja los orígenes de scripts. "
                            "Establece controles de acceso y monitorización de conversaciones."
                        )
                    })
                else:
                    findings.append({
                        "id": "no_ai_detected", "severity": "info",
                        "title": "No se detectaron asistentes IA embebidos en la capa pública",
                        "detail": (
                            "No se encontraron scripts o endpoints de IA conocidos en el HTML público. "
                            "Esto no excluye el uso de IA en sistemas internos o back-office."
                        ),
                        "recommendation": "Mantén esta verificación periódica e incluye sistemas internos en el diagnóstico completo."
                    })

            except (httpx.ConnectError, httpx.SSLError, httpx.TimeoutException) as e:
                findings.append({
                    "id": "ai_fetch_error", "severity": "info",
                    "title": "No se pudo analizar el HTML del sitio",
                    "detail": str(e)[:200],
                    "recommendation": "Verifica el acceso público al dominio."
                })
                score = 15

    except Exception as e:
        findings.append({
            "id": "ai_error", "severity": "info",
            "title": "Error en detección de superficie IA",
            "detail": str(e)[:200],
            "recommendation": ""
        })
        score = 15

    return {"score": max(0, score), "max_score": 32, "detected": detected, "findings": findings}


# ─── Scoring ──────────────────────────────────────────────────────────────────

def calculate_score(results: dict) -> dict:
    http_s = results["http_headers"]["score"]
    email_s = results["email_security"]["score"]
    ssl_s = results["ssl"]["score"]
    ai_s = results["ai_detection"]["score"]
    total = http_s + email_s + ssl_s + ai_s

    if total >= 75:
        risk_level, risk_color = "Bajo", "#3fb950"
    elif total >= 50:
        risk_level, risk_color = "Moderado", "#d29922"
    elif total >= 25:
        risk_level, risk_color = "Alto", "#f0883e"
    else:
        risk_level, risk_color = "Crítico", "#f85149"

    all_findings = (
        results["http_headers"]["findings"] +
        results["email_security"]["findings"] +
        results["ssl"]["findings"] +
        results["ai_detection"]["findings"]
    )
    all_findings.sort(key=lambda f: SEVERITY_ORDER.get(f.get("severity", "info"), 4))

    return {
        "total": total,
        "max": 100,
        "risk_level": risk_level,
        "risk_color": risk_color,
        "categories": {
            "http_headers": {"score": http_s, "max": 33, "label": "Cabeceras HTTP"},
            "email_security": {"score": email_s, "max": 20, "label": "Seguridad de email"},
            "ssl": {"score": ssl_s, "max": 15, "label": "SSL / TLS"},
            "ai_surface": {"score": ai_s, "max": 32, "label": "Superficie IA"},
        },
        "findings": all_findings,
    }


# ─── Claude Narrative ─────────────────────────────────────────────────────────

async def generate_narrative(results: dict) -> str:
    if not ANTHROPIC_API_KEY:
        return "API key de Anthropic no configurada."
    try:
        score = results["score"]
        detected_ai = results["ai_detection"]["detected"]
        critical = [f["title"] for f in score["findings"] if f.get("severity") == "critical"]
        high = [f["title"] for f in score["findings"] if f.get("severity") == "high"]

        prompt = f"""Analiza el perfil de riesgo Shadow AI del dominio {results['domain']}.

Puntuación: {score['total']}/100 — Riesgo {score['risk_level']}
IA detectada: {', '.join(detected_ai) if detected_ai else 'Ninguna (capa pública)'}
Hallazgos críticos: {', '.join(critical) if critical else 'Ninguno'}
Hallazgos altos: {', '.join(high) if high else 'Ninguno'}
Categorías: HTTP {results['http_headers']['score']}/33 · Email {results['email_security']['score']}/20 · SSL {results['ssl']['score']}/15 · IA {results['ai_detection']['score']}/32

Escribe un diagnóstico técnico de 2-3 párrafos cortos para el Shadow AI Diagnostic de RosmarOps.
Tono: analítico, directo, sin grandilocuencia. En castellano. Sin bullet points ni headers.
Conecta los hallazgos con las implicaciones concretas de Shadow AI para esta organización."""

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 600,
                    "system": (
                        "Eres un analista de ciberseguridad especializado en Shadow AI y riesgos de LLMs "
                        "en organizaciones. Escribes diagnósticos técnicos rigurosos, directos y sin "
                        "grandilocuencia. Sin moraleja."
                    ),
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
        if resp.status_code == 200:
            return resp.json()["content"][0]["text"]
        else:
            print(f"[narrative error] HTTP {resp.status_code}: {resp.text[:300]}")
            return f"Error generando narrativa: HTTP {resp.status_code} — {resp.text[:200]}"
    except Exception as e:
        error_type = type(e).__name__
        error_detail = str(e)
        print(f"[narrative error] {error_type}: {error_detail}")
        return f"Error generando narrativa: [{error_type}] {error_detail}"


# ─── Main orchestrator ────────────────────────────────────────────────────────

async def run_full_recon(domain: str):
    yield {"type": "progress", "check": "http", "label": "Analizando cabeceras HTTP y HTTPS..."}
    http_result = await check_http_headers(domain)
    yield {"type": "check_done", "check": "http", "partial": {"http_headers": http_result}}

    yield {"type": "progress", "check": "email", "label": "Verificando seguridad de email (SPF, DMARC)..."}
    email_result = await check_email_security(domain)
    yield {"type": "check_done", "check": "email", "partial": {"email_security": email_result}}

    yield {"type": "progress", "check": "ssl", "label": "Comprobando certificado SSL/TLS..."}
    ssl_result = await check_ssl(domain)
    yield {"type": "check_done", "check": "ssl", "partial": {"ssl": ssl_result}}

    yield {"type": "progress", "check": "ai", "label": "Detectando asistentes IA embebidos..."}
    ai_result = await detect_ai_assistants(domain)
    yield {"type": "check_done", "check": "ai", "partial": {"ai_detection": ai_result}}

    all_results = {
        "domain": domain,
        "http_headers": http_result,
        "email_security": email_result,
        "ssl": ssl_result,
        "ai_detection": ai_result,
    }
    all_results["score"] = calculate_score(all_results)

    yield {"type": "progress", "check": "narrative", "label": "Generando diagnóstico con Claude..."}
    all_results["narrative"] = await generate_narrative(all_results)

    yield {"type": "result", "data": all_results}
