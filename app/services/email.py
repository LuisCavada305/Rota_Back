from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Sequence
from urllib.parse import urlencode

from app.core.settings import settings

logger = logging.getLogger(__name__)


def _ensure_list(recipients: Sequence[str] | str) -> list[str]:
    if isinstance(recipients, str):
        recipients = [recipients]
    cleaned = [r.strip() for r in recipients if r and r.strip()]
    if not cleaned:
        raise ValueError("Pelo menos um destinatário é obrigatório")
    return cleaned


class BaseEmailBackend:
    def send(self, message: EmailMessage) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class ConsoleEmailBackend(BaseEmailBackend):
    def send(self, message: EmailMessage) -> None:
        preview = [
            "--- Email (console backend) ---",
            f"To: {message['To']}",
            f"Subject: {message['Subject']}",
            "",
            message.get_body(preferencelist=('plain',)).get_content()
            if message.get_body(preferencelist=("plain",))
            else "",
        ]
        if message.get_body(preferencelist=("html",)):
            preview.extend([
                "",
                "(HTML body omitted)",
            ])
        logger.info("\n".join(preview))


class SMTPEmailBackend(BaseEmailBackend):
    def send(self, message: EmailMessage) -> None:
        use_ssl = settings.SMTP_USE_SSL
        host = settings.SMTP_HOST
        port = settings.SMTP_PORT
        timeout = settings.SMTP_TIMEOUT

        smtp_cls = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        with smtp_cls(host=host, port=port, timeout=timeout) as connection:
            connection.ehlo()
            if settings.SMTP_USE_TLS and not use_ssl:
                connection.starttls()
                connection.ehlo()
            username = settings.SMTP_USERNAME
            if username:
                connection.login(username, settings.SMTP_PASSWORD or "")
            connection.send_message(message)


_backend_cache: BaseEmailBackend | None = None


def get_email_backend() -> BaseEmailBackend:
    global _backend_cache
    if _backend_cache is None:
        backend_name = settings.EMAIL_BACKEND.lower()
        if backend_name == "smtp":
            _backend_cache = SMTPEmailBackend()
        else:
            _backend_cache = ConsoleEmailBackend()
    return _backend_cache


def reset_email_backend_cache() -> None:
    global _backend_cache
    _backend_cache = None


def build_email_message(
    *,
    subject: str,
    to: Sequence[str] | str,
    body_text: str,
    body_html: str | None = None,
    from_email: str | None = None,
    reply_to: str | None = None,
) -> EmailMessage:
    recipients = _ensure_list(to)
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_email or settings.DEFAULT_FROM_EMAIL
    message["To"] = ", ".join(recipients)
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(body_text)
    if body_html:
        message.add_alternative(body_html, subtype="html")
    return message


def send_email(
    *,
    subject: str,
    to: Sequence[str] | str,
    body_text: str,
    body_html: str | None = None,
    from_email: str | None = None,
    reply_to: str | None = None,
) -> None:
    message = build_email_message(
        subject=subject,
        to=to,
        body_text=body_text,
        body_html=body_html,
        from_email=from_email,
        reply_to=reply_to,
    )
    backend = get_email_backend()
    backend.send(message)


def _user_display_name(user) -> str:
    for candidate in (
        getattr(user, "social_name", None),
        getattr(user, "name_for_certificate", None),
        getattr(user, "username", None),
        getattr(user, "email", None),
    ):
        if candidate:
            return candidate
    return "usuário"


def _password_reset_link(token: str) -> str:
    base = settings.FRONTEND_ORIGIN.rstrip("/")
    query = urlencode({"token": token})
    return f"{base}/reset-password?{query}"


_ROTA_BLUE = "#0F4C81"


def _wrap_email_html(*, title: str, content_html: str, button_html: str = "", footer_html: str = "") -> str:
    return (
        "<!DOCTYPE html>"
        "<html lang=\"pt-BR\">"
        "<head>"
        "<meta charset=\"utf-8\"/>"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>"
        "<title>Rota</title>"
        "</head>"
        "<body style=\"margin:0;padding:0;background-color:#f4f7fa;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;\">"
        "<table role=\"presentation\" cellpadding=\"0\" cellspacing=\"0\" width=\"100%\" style=\"border-collapse:collapse;\">"
        "<tr>"
        "<td style=\"padding:24px;\">"
        "<table role=\"presentation\" cellpadding=\"0\" cellspacing=\"0\" width=\"100%\" style=\"max-width:640px;margin:0 auto;border-collapse:collapse;\">"
        "<tr>"
        f"<td style=\"background-color:{_ROTA_BLUE};color:#ffffff;border-radius:20px;padding:36px 32px;text-align:left;\">"
        f"<h1 style=\"margin:0 0 24px;font-size:28px;line-height:1.2;font-weight:700;\">{title}</h1>"
        f"<div style=\"font-size:16px;line-height:1.6;\">{content_html}</div>"
        f"{button_html}"
        f"{footer_html}"
        "</td>"
        "</tr>"
        "</table>"
        "</td>"
        "</tr>"
        "</table>"
        "</body>"
        "</html>"
    )


def send_welcome_email(user) -> None:
    name = _user_display_name(user)
    subject = "Bem-vindo(a) à Rota"
    body_text = (
        f"Olá {name},\n\n"
        "Sua conta foi criada com sucesso! Estamos felizes em tê-lo(a) na plataforma "
        "Rota.\n\nSe precisar de ajuda, basta responder este email."
    )
    content_html = (
        f"<p style=\"margin:0 0 16px;\">Olá {name},</p>"
        "<p style=\"margin:0 0 16px;\">Sua conta foi criada com sucesso e estamos felizes em tê-lo(a) com a gente na plataforma Rota.</p>"
        "<p style=\"margin:0 0 16px;\">Se precisar de qualquer ajuda, basta responder este email e nossa equipe falará com você o quanto antes.</p>"
    )
    footer_html = (
        "<p style=\"margin:24px 0 0;font-size:13px;opacity:0.8;\">Abraços da equipe Rota 🚀</p>"
    )
    body_html = _wrap_email_html(title="Bem-vindo(a)!", content_html=content_html, footer_html=footer_html)
    send_email(subject=subject, to=[user.email], body_text=body_text, body_html=body_html)


def send_password_reset_email(user, token: str) -> None:
    name = _user_display_name(user)
    reset_link = _password_reset_link(token)
    subject = "Redefinição de senha"
    body_text = (
        f"Olá {name},\n\n"
        "Recebemos uma solicitação para redefinir a sua senha. "
        "Caso tenha sido você, acesse o link abaixo:\n\n"
        f"{reset_link}\n\n"
        "Se você não solicitou essa alteração, pode ignorar este email."
    )
    content_html = (
        f"<p style=\"margin:0 0 16px;\">Olá {name},</p>"
        "<p style=\"margin:0 0 24px;\">Recebemos uma solicitação para redefinir a sua senha. Caso tenha sido você, use o botão abaixo para continuar o processo com segurança.</p>"
    )
    button_html = (
        f"<p style=\"margin:0 0 24px;text-align:center;\"><a href=\"{reset_link}\" style=\"display:inline-block;padding:14px 28px;background-color:#ffffff;color:{_ROTA_BLUE};text-decoration:none;border-radius:999px;font-weight:600;\">Redefinir senha</a></p>"
        f"<p style=\"margin:0 0 16px;font-size:13px;\">Ou, se preferir, copie e cole este link no navegador: <br/><span style=\"word-break:break-all;\"><a href=\"{reset_link}\" style=\"color:#ffffff;text-decoration:underline;\">{reset_link}</a></span></p>"
    )
    footer_html = (
        "<p style=\"margin:24px 0 0;font-size:13px;opacity:0.8;\">Se você não solicitou essa alteração, pode ignorar este email com segurança.</p>"
    )
    body_html = _wrap_email_html(
        title="Redefinição de senha",
        content_html=content_html,
        button_html=button_html,
        footer_html=footer_html,
    )
    send_email(subject=subject, to=[user.email], body_text=body_text, body_html=body_html)

