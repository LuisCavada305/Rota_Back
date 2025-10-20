from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from typing import Iterable
from urllib.parse import urljoin

from app.core.settings import settings


logger = logging.getLogger(__name__)


def _brand_color() -> str:
    color = settings.rota_brand_color.strip()
    if not color.startswith("#"):
        color = f"#{color}"
    return color


def _base_url() -> str:
    return settings.app_base_url or settings.API_ORIGIN


def _build_reset_url(token: str) -> str:
    if settings.password_reset_base_url:
        base = settings.password_reset_base_url.rstrip("/") + "/"
    else:
        base = _base_url().rstrip("/") + "/"
    path = settings.password_reset_path.lstrip("/")
    url = urljoin(base, path)
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}token={token}"


def _render_email_html(
    title: str,
    body: str,
    *,
    action_url: str | None = None,
    action_label: str | None = None,
) -> str:
    brand_color = _brand_color()
    background_color = "#f3f4f6"
    button_html = ""
    if action_url and action_label:
        button_html = f"""
            <tr>
                <td align=\"center\" style=\"padding: 24px;\">
                    <a href=\"{action_url}\" style=\"display: inline-block; padding: 14px 32px; border-radius: 9999px; background-color: {brand_color}; color: #ffffff; font-weight: 600; text-decoration: none;\">{action_label}</a>
                </td>
            </tr>
        """

    return f"""
    <html>
        <body style=\"margin:0;padding:0;background-color:{background_color};\">
            <table role=\"presentation\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" width=\"100%\" style=\"background-color:{background_color};padding:24px 12px;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;\">
                <tr>
                    <td align=\"center\">
                        <table role=\"presentation\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" width=\"100%\" style=\"max-width:600px;background-color:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 12px 32px rgba(10,61,143,0.25);\">
                            <tr>
                                <td style=\"background-color:{brand_color};color:#ffffff;padding:24px 32px;font-size:24px;font-weight:700;\">Rota</td>
                            </tr>
                            <tr>
                                <td style=\"padding:32px;color:#1f2937;font-size:16px;line-height:1.6;\">
                                    <h1 style=\"margin:0 0 16px 0;font-size:24px;color:{brand_color};\">{title}</h1>
                                    <p style=\"margin:0 0 12px 0;\">{body}</p>
                                </td>
                            </tr>
                            {button_html}
                            <tr>
                                <td style=\"padding:24px 32px 32px 32px;color:#6b7280;font-size:12px;line-height:1.4;text-align:center;\">
                                    Você está recebendo este email porque possui uma conta ativa na plataforma Rota.
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
    </html>
    """


def _render_email_text(
    title: str,
    body: str,
    *,
    action_url: str | None = None,
    action_label: str | None = None,
) -> str:
    text = f"{title}\n\n{body}"
    if action_url and action_label:
        text += f"\n\n{action_label}: {action_url}"
    text += "\n\nEquipe Rota"
    return text


def _ensure_recipients(addresses: Iterable[str]) -> list[str]:
    return [addr for addr in addresses if addr]


def send_email(
    *, subject: str, to: Iterable[str], html_body: str, text_body: str | None = None
) -> bool:
    recipients = _ensure_recipients(to)
    if not recipients:
        logger.warning("Nenhum destinatário informado para email '%s'", subject)
        return False

    if not settings.smtp_host or not settings.smtp_from_email:
        logger.info(
            "SMTP não configurado; email '%s' para %s foi ignorado.",
            subject,
            ", ".join(recipients),
        )
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((settings.smtp_from_name, settings.smtp_from_email))
    message["To"] = ", ".join(recipients)

    text_version = text_body or ""
    if not text_version:
        text_version = "Seu cliente de email não suporta conteúdo em HTML."
    message.set_content(text_version)
    message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(
            settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout
        ) as server:
            if settings.smtp_starttls:
                server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password or "")
            server.send_message(message)
            logger.info("Email '%s' enviado para %s", subject, ", ".join(recipients))
            return True
    except Exception as exc:  # pragma: no cover - dependent on external SMTP
        logger.exception("Falha ao enviar email '%s': %s", subject, exc)
        return False


def send_welcome_email(*, email: str, name: str | None = None):
    display_name = name or ""
    body = ""
    if display_name:
        body += f"Olá, {display_name}! "
    body += "Sua conta na plataforma Rota foi criada com sucesso. Agora você já pode acessar o portal, explorar as trilhas e iniciar sua jornada de aprendizagem."

    html = _render_email_html(
        "Bem-vindo ao Rota",
        body,
        action_url=_base_url(),
        action_label="Acessar o Rota",
    )
    text = _render_email_text(
        "Bem-vindo ao Rota",
        body,
        action_url=_base_url(),
        action_label="Acessar o Rota",
    )
    send_email(
        subject="Sua conta Rota está pronta", to=[email], html_body=html, text_body=text
    )


def send_trail_enrollment_email(*, email: str, name: str | None, trail_name: str):
    greeting = f"Olá, {name}! " if name else "Olá! "
    body = f"{greeting}Você acabou de se inscrever na trilha '{trail_name}'. Continue acompanhando suas aulas e atividades para concluir o curso e receber seu certificado."
    html = _render_email_html(
        "Inscrição confirmada",
        body,
        action_url=_base_url(),
        action_label="Ver minha trilha",
    )
    text = _render_email_text(
        "Inscrição confirmada",
        body,
        action_url=_base_url(),
        action_label="Ver minha trilha",
    )
    send_email(
        subject="Inscrição na trilha confirmada",
        to=[email],
        html_body=html,
        text_body=text,
    )


def send_password_reset_email(*, email: str, name: str | None, token: str):
    reset_url = _build_reset_url(token)
    greeting = f"Olá, {name}! " if name else "Olá! "
    body = f"{greeting}Recebemos uma solicitação para redefinir a sua senha. Clique no botão abaixo para criar uma nova senha. Se você não fez essa solicitação, pode ignorar este email."
    html = _render_email_html(
        "Redefinição de senha",
        body,
        action_url=reset_url,
        action_label="Redefinir senha",
    )
    text = _render_email_text(
        "Redefinição de senha",
        body,
        action_url=reset_url,
        action_label="Redefinir senha",
    )
    send_email(
        subject="Redefina sua senha no Rota", to=[email], html_body=html, text_body=text
    )


def send_password_changed_notification(*, email: str, name: str | None = None):
    greeting = f"Olá, {name}! " if name else "Olá! "
    body = f"{greeting}Sua senha foi atualizada com sucesso. Se você não reconhece esta alteração, acesse o Rota imediatamente e entre em contato com o suporte."
    html = _render_email_html(
        "Senha atualizada",
        body,
        action_url=_base_url(),
        action_label="Ir para o Rota",
    )
    text = _render_email_text(
        "Senha atualizada",
        body,
        action_url=_base_url(),
        action_label="Ir para o Rota",
    )
    send_email(
        subject="Sua senha foi atualizada", to=[email], html_body=html, text_body=text
    )


__all__ = [
    "send_email",
    "send_password_changed_notification",
    "send_password_reset_email",
    "send_trail_enrollment_email",
    "send_welcome_email",
]
