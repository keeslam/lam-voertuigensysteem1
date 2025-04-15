import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition, ContentId
import base64
from flask import current_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_email(to_email, subject, html_content, attachments=None):
    """
    Send an email using SendGrid
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        html_content (str): HTML content of the email
        attachments (list): Optional list of file paths to attach
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Get API key from environment variables
        api_key = os.environ.get('SENDGRID_API_KEY')
        
        if not api_key:
            logger.error("SendGrid API key not found in environment variables")
            return False
        
        # Set sender email (you might want to configure this)
        from_email = 'noreply@autoverhuurbeheer.nl'
        
        # Create the email message
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        
        # Add attachments if provided
        if attachments:
            for file_path in attachments:
                if not os.path.exists(file_path):
                    logger.warning(f"Attachment file not found: {file_path}")
                    continue
                
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                    encoded = base64.b64encode(file_data).decode()
                
                # Get the file name and type
                file_name = os.path.basename(file_path)
                _, file_ext = os.path.splitext(file_name)
                file_type = 'application/pdf' if file_ext.lower() == '.pdf' else 'application/octet-stream'
                
                # If it's an image, set the appropriate content type
                if file_ext.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                    file_type = f'image/{file_ext[1:].lower()}'
                
                # Create attachment
                attachment = Attachment()
                attachment.file_content = FileContent(encoded)
                attachment.file_name = FileName(file_name)
                attachment.file_type = FileType(file_type)
                attachment.disposition = Disposition('attachment')
                attachment.content_id = ContentId(file_name)
                
                message.attachment = attachment
        
        # Send the email
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        # Log the response
        logger.info(f"Email sent to {to_email}, status code: {response.status_code}")
        return response.status_code in [200, 201, 202]
    
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False