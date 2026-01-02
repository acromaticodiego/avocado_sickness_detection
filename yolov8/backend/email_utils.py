from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
import os
from fastapi import BackgroundTasks


# Ruta base del proyecto (donde está este archivo)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

conf = ConnectionConfig(
    MAIL_USERNAME="smartvision667@gmail.com",
    MAIL_PASSWORD="glov sjsv sljk uhnd",  # Gmail recomienda contraseña de app
    MAIL_FROM="smartvision667@gmail.com",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,   # 👈 reemplaza MAIL_TLS
    MAIL_SSL_TLS=False,   # 👈 reemplaza MAIL_SSL
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def enviar_correo_bienvenida(email_destino: EmailStr):
    message = MessageSchema(
        subject="Bienvenido a SmartVision",
        recipients=[email_destino],
        body="Bienvenido a Smartvision, estas son las instrucciones del proceso de calidad.",
        subtype=MessageType.plain,
        attachments=[os.path.join(BASE_DIR, "sqlitebase/documentos/Sama_SmartVision.pdf")]
    )

    fm = FastMail(conf)
    await fm.send_message(message)