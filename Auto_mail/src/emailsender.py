import os
import smtplib
import mimetypes
from .logger import Logger
from typing import Union, List, Optional
from email.message import EmailMessage

class EmailSender:
    def __init__(self, config: Union[dict,str]):
        # 移除了setup_logger()的調用，直接初始化Logger
        self.provider = config.get('provider', 'smtp').lower()  # 預設為 smtp
        self.email_address = config['email_address']
        self.use_ssl = config.get('use_ssl', True)
        self.email_password = config.get('email_password')
        self.smtp_server = config['smtp_server']
        self.smtp_port = config['smtp_port']
        self.logger = Logger(name="EmailSenderLogger")

    def send(
        self,
        recipients: List[str],
        subject: str,
        content_text: Optional[str] = None,
        attachment_files: Union[str, List[str], None] = None,
        attachments_dir: Union[str, List[str], None] = None,
        html_body: Optional[str] = None
    ):
        if recipients is None or not recipients:
            error_msg = "收件人列表不能為空。請提供至少一個收件人。"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
            
        self.send_email_smtp(
            recipients=recipients,
            subject=subject,
            content_text=content_text,
            html_body=html_body,
            attachment_files=attachment_files,
            attachments_dir=attachments_dir
        )
    
    def send_email_smtp(
        self,
        recipients: List[str],
        subject: str,
        content_text: Optional[str] = None,
        attachment_files: Union[str, List[str], None] = None,
        attachments_dir: Union[str, List[str], None] = None,
        html_body: Optional[str] = None,
    ):
        self.logger.info(f"準備發送郵件給: {recipients}")
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = self.email_address
        msg['To'] = ', '.join(recipients)
        msg.set_content(content_text if content_text else "請參閱附件。")

        
        if html_body and content_text:
            html_body = f"<p>{content_text}</p><hr>" + html_body
            
        if html_body:
            msg.add_alternative(html_body, subtype='html')
            self.logger.info("已添加HTML內容到郵件")

        try:
            if attachment_files:
                if isinstance(attachment_files, str):
                    attachment_files = [attachment_files]
                self.logger.info(f"處理單獨指定的附件: {len(attachment_files)}個文件")
                for file_path in attachment_files:
                    if os.path.exists(file_path):
                        self._attach_file(msg, file_path)
                    else:
                        error_msg = f"找不到檔案: {file_path}"
                        self.logger.error(error_msg)
                        raise FileNotFoundError(error_msg)

            if attachments_dir and len(attachments_dir) > 0:
                if isinstance(attachments_dir, str):
                    attachments_dir = [attachments_dir]
                self.logger.info(f"處理附件目錄: {len(attachments_dir)}個目錄")
                for folder in attachments_dir:
                    if os.path.isdir(folder):
                        file_count = 0
                        for filename in os.listdir(folder):
                            file_path = os.path.join(folder, filename)
                            if os.path.isfile(file_path):
                                self._attach_file(msg, file_path)
                                file_count += 1
                        self.logger.info(f"從目錄 {folder} 添加了 {file_count} 個文件")
                    else:
                        error_msg = f"找不到目錄: {folder}"
                        self.logger.error(error_msg)
                        raise NotADirectoryError(error_msg)

        except Exception as e:
            error_msg = f"由於附件錯誤，郵件發送已中止: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            if self.use_ssl:
                self.logger.info(f"使用SSL連接到SMTP伺服器: {self.smtp_server}:{self.smtp_port}")
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as smtp:
                    smtp.login(self.email_address, self.email_password)
                    smtp.send_message(msg)
            else:
                self.logger.info(f"使用TLS連接到SMTP伺服器: {self.smtp_server}:{self.smtp_port}")
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as smtp:
                    smtp.starttls()
                    smtp.login(self.email_address, self.email_password)
                    smtp.send_message(msg)
            return_message = f"Email sent successfully to: {recipients}"
            self.logger.info(return_message)
            return return_message
        except Exception as e:
            error_msg = f"Failed to send email: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

    def _attach_file(self, msg, file_path):
        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            maintype, subtype = mime_type.split('/') if mime_type else ('application', 'octet-stream')
            with open(file_path, 'rb') as f:
                msg.add_attachment(
                    f.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=os.path.basename(file_path)
                )
            self.logger.info(f"已添加附件: {file_path}")
        except Exception as e:
            error_msg = f"添加附件 '{file_path}' 失敗: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)