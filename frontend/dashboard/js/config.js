/* MIFTEH OS — Backend API Configuration
 *
 * Set MIFTEH_API_BASE to the URL of the MIFTEH OS FastAPI backend.
 *
 * Production examples:
 *   'https://api.miftehos.com'         — dedicated API subdomain
 *   'https://mifteh-api.onrender.com'  — Render deployment
 *   'https://mifteh.railway.app'       — Railway deployment
 *   ''                                 — same origin (FastAPI serves both UI + API)
 *
 * After updating, redeploy the frontend (push to main triggers GitHub Pages deploy).
 */
window.MIFTEH_API_BASE = '';
