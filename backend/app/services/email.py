import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict

from backend.app.config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD

logger = logging.getLogger(__name__)

def send_bulk_invites(campaign_name: str, invites: List[Dict[str, str]]):
    """
    Service to send transactional emails via standard SMTP.
    """
    logger.info(f"🚀 Starting email dispatch for campaign '{campaign_name}' ({len(invites)} recipients)")
    
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.warning("⚠️ SMTP credentials not configured. Falling back to MOCK email dispatch.")
        _mock_send_bulk_invites(campaign_name, invites)
        return

    try:
        # Establish SMTP connection
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        
        for invite in invites:
            name = invite.get('name', 'Candidate')
            email = invite.get('email')
            link = invite.get('link')
            
            if not email:
                continue

            msg = MIMEMultipart()
            msg['From'] = f"Interview AI <{SMTP_USERNAME}>"
            msg['To'] = email
            msg['Subject'] = f"You've been invited to an interview for {campaign_name}"
            
            body = f"Hi {name},\n\nYou have been invited to complete an AI interview.\n\nPlease click the link below to start your interview:\n{link}\n\nGood luck!"
            msg.attach(MIMEText(body, 'plain'))
            
            server.send_message(msg)
            logger.info(f"📧 Sent email to: {email}")
            
        server.quit()
        logger.info("✅ All emails dispatched successfully.")
        
    except Exception as e:
        logger.error(f"❌ Failed to send emails: {str(e)}")


def _mock_send_bulk_invites(campaign_name: str, invites: List[Dict[str, str]]):
    for invite in invites:
        name = invite.get('name', 'Candidate')
        email = invite.get('email')
        link = invite.get('link')
        
        logger.info(f"📧 [MOCK EMAIL] To: {email}")
        logger.info(f"   Subject: You've been invited to an interview")
        logger.info(f"   Body: Hi {name},\n\nPlease click here to start your interview:\n{link}\n")
        
    logger.info("✅ All mock emails dispatched successfully.")
