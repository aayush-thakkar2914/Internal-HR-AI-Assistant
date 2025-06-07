"""
Notification service for the HR AI Assistant.

This service handles all types of notifications including email, SMS, and in-app notifications
for various HR events like leave approvals, document requests, survey invitations, etc.
"""

import os
import smtplib
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template
import asyncio
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.models.document import DocumentRequest
from app.models.survey import Survey, SurveyResponse
from app.models.query import QueryLog
from app.utils.logger import get_logger
from app.utils.helpers import format_date, format_currency

logger = get_logger(__name__)

class NotificationService:
    """
    Comprehensive notification service for HR AI Assistant
    """
    
    def __init__(self):
        # Email configuration
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.smtp_use_tls = os.getenv("SMTP_USE_TLS", "True").lower() == "true"
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username)
        self.from_name = os.getenv("FROM_NAME", "HR AI Assistant")
        
        # SMS configuration (for services like Twilio)
        self.sms_enabled = os.getenv("SMS_ENABLED", "False").lower() == "true"
        self.sms_service = os.getenv("SMS_SERVICE", "twilio")
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")
        
        # Template configuration
        self.template_dir = Path("app/templates/notifications")
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True
        )
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        # Company information
        self.company_name = os.getenv("COMPANY_NAME", "Our Company")
        self.company_website = os.getenv("COMPANY_WEBSITE", "https://company.com")
        self.hr_email = os.getenv("HR_EMAIL", "hr@company.com")
        self.hr_phone = os.getenv("HR_PHONE", "+91-1234567890")
        
        # Notification preferences
        self.notification_preferences = {
            "leave_requests": {"email": True, "sms": False, "in_app": True},
            "document_requests": {"email": True, "sms": False, "in_app": True},
            "survey_invitations": {"email": True, "sms": False, "in_app": True},
            "escalations": {"email": True, "sms": True, "in_app": True},
            "reminders": {"email": True, "sms": False, "in_app": True}
        }
        
        # Initialize templates
        self._create_default_templates()
        
        logger.info("Notification service initialized")
    
    def _create_default_templates(self):
        """Create default email templates if they don't exist"""
        templates = {
            "leave_request_submitted.html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Leave Request Submitted</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; }
        .content { background-color: #f9f9f9; padding: 20px; }
        .footer { background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px; }
        .details { background-color: white; padding: 15px; margin: 10px 0; border-left: 4px solid #4CAF50; }
        .button { display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Leave Request Submitted</h1>
        </div>
        <div class="content">
            <p>Dear {{ employee_name }},</p>
            <p>Your leave request has been successfully submitted and is pending approval.</p>
            
            <div class="details">
                <h3>Leave Details:</h3>
                <p><strong>Request ID:</strong> {{ request_id }}</p>
                <p><strong>Leave Type:</strong> {{ leave_type }}</p>
                <p><strong>Start Date:</strong> {{ start_date }}</p>
                <p><strong>End Date:</strong> {{ end_date }}</p>
                <p><strong>Total Days:</strong> {{ total_days }}</p>
                <p><strong>Reason:</strong> {{ reason }}</p>
            </div>
            
            <p>Your request will be reviewed by your manager. You will receive an email notification once a decision is made.</p>
            
            <p><a href="{{ portal_link }}" class="button">View Request Status</a></p>
        </div>
        <div class="footer">
            <p>{{ company_name }} HR Department | {{ hr_email }} | {{ hr_phone }}</p>
        </div>
    </div>
</body>
</html>
            """,
            
            "leave_request_approved.html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Leave Request Approved</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; }
        .content { background-color: #f9f9f9; padding: 20px; }
        .footer { background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px; }
        .details { background-color: white; padding: 15px; margin: 10px 0; border-left: 4px solid #4CAF50; }
        .approved { color: #4CAF50; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ Leave Request Approved</h1>
        </div>
        <div class="content">
            <p>Dear {{ employee_name }},</p>
            <p class="approved">Great news! Your leave request has been approved.</p>
            
            <div class="details">
                <h3>Approved Leave Details:</h3>
                <p><strong>Request ID:</strong> {{ request_id }}</p>
                <p><strong>Leave Type:</strong> {{ leave_type }}</p>
                <p><strong>Start Date:</strong> {{ start_date }}</p>
                <p><strong>End Date:</strong> {{ end_date }}</p>
                <p><strong>Total Days:</strong> {{ total_days }}</p>
                <p><strong>Approved By:</strong> {{ approver_name }}</p>
                <p><strong>Approval Date:</strong> {{ approval_date }}</p>
                {% if manager_comments %}
                <p><strong>Manager Comments:</strong> {{ manager_comments }}</p>
                {% endif %}
            </div>
            
            <p>Please ensure proper handover of your responsibilities before your leave begins.</p>
            
            <p>Have a great time off!</p>
        </div>
        <div class="footer">
            <p>{{ company_name }} HR Department | {{ hr_email }} | {{ hr_phone }}</p>
        </div>
    </div>
</body>
</html>
            """,
            
            "leave_request_rejected.html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Leave Request Status Update</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #f44336; color: white; padding: 20px; text-align: center; }
        .content { background-color: #f9f9f9; padding: 20px; }
        .footer { background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px; }
        .details { background-color: white; padding: 15px; margin: 10px 0; border-left: 4px solid #f44336; }
        .rejected { color: #f44336; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Leave Request Status Update</h1>
        </div>
        <div class="content">
            <p>Dear {{ employee_name }},</p>
            <p>We regret to inform you that your leave request could not be approved at this time.</p>
            
            <div class="details">
                <h3>Request Details:</h3>
                <p><strong>Request ID:</strong> {{ request_id }}</p>
                <p><strong>Leave Type:</strong> {{ leave_type }}</p>
                <p><strong>Requested Dates:</strong> {{ start_date }} to {{ end_date }}</p>
                <p><strong>Total Days:</strong> {{ total_days }}</p>
                <p class="rejected"><strong>Status:</strong> Not Approved</p>
                {% if rejection_reason %}
                <p><strong>Reason:</strong> {{ rejection_reason }}</p>
                {% endif %}
            </div>
            
            <p>If you have any questions or would like to discuss alternative dates, please contact your manager or HR.</p>
            
            <p>We appreciate your understanding.</p>
        </div>
        <div class="footer">
            <p>{{ company_name }} HR Department | {{ hr_email }} | {{ hr_phone }}</p>
        </div>
    </div>
</body>
</html>
            """,
            
            "document_request_completed.html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Document Request Completed</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #2196F3; color: white; padding: 20px; text-align: center; }
        .content { background-color: #f9f9f9; padding: 20px; }
        .footer { background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px; }
        .details { background-color: white; padding: 15px; margin: 10px 0; border-left: 4px solid #2196F3; }
        .button { display: inline-block; padding: 10px 20px; background-color: #2196F3; color: white; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📄 Document Ready for Download</h1>
        </div>
        <div class="content">
            <p>Dear {{ employee_name }},</p>
            <p>Your requested document has been processed and is ready for download.</p>
            
            <div class="details">
                <h3>Document Details:</h3>
                <p><strong>Request ID:</strong> {{ request_id }}</p>
                <p><strong>Document:</strong> {{ document_title }}</p>
                <p><strong>Type:</strong> {{ document_type }}</p>
                <p><strong>Processed By:</strong> {{ processed_by }}</p>
                <p><strong>Completion Date:</strong> {{ completion_date }}</p>
                {% if completion_notes %}
                <p><strong>Notes:</strong> {{ completion_notes }}</p>
                {% endif %}
            </div>
            
            <p>{% if download_link %}<a href="{{ download_link }}" class="button">Download Document</a>{% else %}Please contact HR to collect your document.{% endif %}</p>
            
            <p>If you have any questions, please don't hesitate to contact us.</p>
        </div>
        <div class="footer">
            <p>{{ company_name }} HR Department | {{ hr_email }} | {{ hr_phone }}</p>
        </div>
    </div>
</body>
</html>
            """,
            
            "survey_invitation.html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Survey Invitation</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #FF9800; color: white; padding: 20px; text-align: center; }
        .content { background-color: #f9f9f9; padding: 20px; }
        .footer { background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px; }
        .details { background-color: white; padding: 15px; margin: 10px 0; border-left: 4px solid #FF9800; }
        .button { display: inline-block; padding: 12px 25px; background-color: #FF9800; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Your Feedback Matters</h1>
        </div>
        <div class="content">
            <p>Dear {{ employee_name }},</p>
            <p>You have been invited to participate in an important survey. Your feedback helps us improve our workplace and better serve our employees.</p>
            
            <div class="details">
                <h3>Survey Details:</h3>
                <p><strong>Title:</strong> {{ survey_title }}</p>
                <p><strong>Description:</strong> {{ survey_description }}</p>
                <p><strong>Estimated Time:</strong> {{ estimated_duration }} minutes</p>
                <p><strong>Deadline:</strong> {{ deadline }}</p>
                {% if is_anonymous %}
                <p><strong>Type:</strong> Anonymous Survey</p>
                {% endif %}
            </div>
            
            <p style="text-align: center;">
                <a href="{{ survey_link }}" class="button">Take Survey Now</a>
            </p>
            
            <p>Your participation is valuable and appreciated. All responses will be treated confidentially.</p>
        </div>
        <div class="footer">
            <p>{{ company_name }} HR Department | {{ hr_email }} | {{ hr_phone }}</p>
        </div>
    </div>
</body>
</html>
            """,
            
            "password_reset.html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Password Reset Request</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #9C27B0; color: white; padding: 20px; text-align: center; }
        .content { background-color: #f9f9f9; padding: 20px; }
        .footer { background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px; }
        .warning { background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .button { display: inline-block; padding: 12px 25px; background-color: #9C27B0; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Password Reset Request</h1>
        </div>
        <div class="content">
            <p>Dear {{ employee_name }},</p>
            <p>We received a request to reset your password for your HR AI Assistant account.</p>
            
            <div class="warning">
                <p><strong>Security Notice:</strong> If you did not request this password reset, please ignore this email and contact IT support immediately.</p>
            </div>
            
            <p>To reset your password, click the button below:</p>
            
            <p style="text-align: center;">
                <a href="{{ reset_link }}" class="button">Reset Password</a>
            </p>
            
            <p><strong>This link will expire in 1 hour for security reasons.</strong></p>
            
            <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
            <p style="word-break: break-all; background-color: #f0f0f0; padding: 10px;">{{ reset_link }}</p>
        </div>
        <div class="footer">
            <p>{{ company_name }} IT Support | {{ hr_email }} | {{ hr_phone }}</p>
        </div>
    </div>
</body>
</html>
            """,
            
            "escalation_notification.html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>HR Escalation Alert</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #f44336; color: white; padding: 20px; text-align: center; }
        .content { background-color: #f9f9f9; padding: 20px; }
        .footer { background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px; }
        .alert { background-color: #ffebee; border: 1px solid #f44336; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .urgent { color: #f44336; font-weight: bold; font-size: 18px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 HR Escalation Alert</h1>
        </div>
        <div class="content">
            <p class="urgent">URGENT: HR Attention Required</p>
            
            <div class="alert">
                <h3>Escalation Details:</h3>
                <p><strong>Employee:</strong> {{ employee_name }} ({{ employee_id }})</p>
                <p><strong>Query:</strong> {{ query_text }}</p>
                <p><strong>Reason for Escalation:</strong> {{ escalation_reason }}</p>
                <p><strong>AI Confidence:</strong> {{ confidence_score }}%</p>
                <p><strong>Timestamp:</strong> {{ timestamp }}</p>
                {% if sentiment %}
                <p><strong>Employee Sentiment:</strong> {{ sentiment }}</p>
                {% endif %}
            </div>
            
            <p>This query requires human intervention. Please review and respond promptly.</p>
            
            <p><strong>Action Required:</strong> Contact the employee directly or through the HR portal to address their concern.</p>
        </div>
        <div class="footer">
            <p>{{ company_name }} AI Assistant | Automated Alert System</p>
        </div>
    </div>
</body>
</html>
            """
        }
        
        # Create template files
        for filename, content in templates.items():
            template_path = self.template_dir / filename
            if not template_path.exists():
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Created template: {filename}")
    
    def _get_template(self, template_name: str) -> Template:
        """Get Jinja2 template by name"""
        try:
            return self.jinja_env.get_template(template_name)
        except Exception as e:
            logger.error(f"Failed to load template {template_name}: {e}")
            # Return a basic fallback template
            return self.jinja_env.from_string("""
            <html><body>
            <h2>{{ subject }}</h2>
            <p>{{ message }}</p>
            <p>Best regards,<br>{{ company_name }}</p>
            </body></html>
            """)
    
    def _send_email(self, to_email: str, subject: str, html_content: str,
                   text_content: str = None, attachments: List[str] = None) -> bool:
        """
        Send email using SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text content (optional)
            attachments: List of file paths to attach (optional)
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            if not self.smtp_username or not self.smtp_password:
                logger.warning("SMTP credentials not configured, skipping email")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Add text content
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Add attachments
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {os.path.basename(file_path)}'
                            )
                            msg.attach(part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def _send_sms(self, to_phone: str, message: str) -> bool:
        """
        Send SMS using configured SMS service
        
        Args:
            to_phone: Recipient phone number
            message: SMS message content
            
        Returns:
            bool: True if SMS sent successfully
        """
        try:
            if not self.sms_enabled:
                logger.debug("SMS service not enabled")
                return False
            
            if self.sms_service == "twilio":
                return self._send_twilio_sms(to_phone, message)
            else:
                logger.warning(f"SMS service '{self.sms_service}' not implemented")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_phone}: {e}")
            return False
    
    def _send_twilio_sms(self, to_phone: str, message: str) -> bool:
        """Send SMS using Twilio"""
        try:
            from twilio.rest import Client
            
            if not self.twilio_account_sid or not self.twilio_auth_token:
                logger.warning("Twilio credentials not configured")
                return False
            
            client = Client(self.twilio_account_sid, self.twilio_auth_token)
            
            message = client.messages.create(
                body=message,
                from_=self.twilio_phone_number,
                to=to_phone
            )
            
            logger.info(f"SMS sent successfully to {to_phone}, SID: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Twilio SMS to {to_phone}: {e}")
            return False
    
    async def send_notification_async(self, notification_type: str, recipient: Employee,
                                    data: Dict[str, Any], channels: List[str] = None) -> Dict[str, bool]:
        """
        Send notification asynchronously
        
        Args:
            notification_type: Type of notification
            recipient: Recipient employee
            data: Notification data
            channels: List of channels to use (email, sms, in_app)
            
        Returns:
            Dict[str, bool]: Success status for each channel
        """
        loop = asyncio.get_event_loop()
        
        return await loop.run_in_executor(
            self.executor,
            self.send_notification,
            notification_type,
            recipient,
            data,
            channels
        )
    
    def send_notification(self, notification_type: str, recipient: Employee,
                         data: Dict[str, Any], channels: List[str] = None) -> Dict[str, bool]:
        """
        Send notification through specified channels
        
        Args:
            notification_type: Type of notification
            recipient: Recipient employee
            data: Notification data
            channels: List of channels to use (email, sms, in_app)
            
        Returns:
            Dict[str, bool]: Success status for each channel
        """
        results = {}
        
        # Get default channels if not specified
        if not channels:
            prefs = self.notification_preferences.get(notification_type, {})
            channels = [ch for ch, enabled in prefs.items() if enabled]
        
        # Add common data
        common_data = {
            "employee_name": recipient.full_name,
            "employee_id": recipient.employee_id,
            "company_name": self.company_name,
            "company_website": self.company_website,
            "hr_email": self.hr_email,
            "hr_phone": self.hr_phone,
            "portal_link": f"{self.company_website}/portal",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        common_data.update(data)
        
        # Send through each channel
        if "email" in channels and recipient.email:
            results["email"] = self._send_email_notification(
                notification_type, recipient.email, common_data
            )
        
        if "sms" in channels and recipient.phone_number:
            results["sms"] = self._send_sms_notification(
                notification_type, recipient.phone_number, common_data
            )
        
        if "in_app" in channels:
            results["in_app"] = self._send_in_app_notification(
                notification_type, recipient.id, common_data
            )
        
        return results
    
    def _send_email_notification(self, notification_type: str, email: str, data: Dict[str, Any]) -> bool:
        """Send email notification based on type"""
        try:
            # Get template and subject based on notification type
            template_mapping = {
                "leave_request_submitted": ("leave_request_submitted.html", "Leave Request Submitted"),
                "leave_request_approved": ("leave_request_approved.html", "Leave Request Approved ✅"),
                "leave_request_rejected": ("leave_request_rejected.html", "Leave Request Status Update"),
                "manager_approval_needed": ("manager_approval_needed.html", "Leave Approval Required"),
                "document_request_completed": ("document_request_completed.html", "Document Ready for Download 📄"),
                "survey_invitation": ("survey_invitation.html", "Survey Invitation - Your Feedback Matters 📊"),
                "password_reset": ("password_reset.html", "Password Reset Request 🔐"),
                "escalation_notification": ("escalation_notification.html", "🚨 HR Escalation Alert - Immediate Attention Required"),
                "welcome_new_employee": ("welcome_new_employee.html", "Welcome to the Team! 🎉"),
                "reminder_leave_expiring": ("reminder_leave_expiring.html", "Reminder: Annual Leave Expiring Soon"),
                "reminder_survey_pending": ("reminder_survey_pending.html", "Reminder: Survey Response Pending")
            }
            
            template_name, subject = template_mapping.get(
                notification_type, 
                ("generic_notification.html", "Notification from HR")
            )
            
            # Customize subject with additional data
            if notification_type == "leave_request_submitted":
                subject = f"Leave Request {data.get('request_id', '')} Submitted"
            elif notification_type == "leave_request_approved":
                subject = f"Leave Request {data.get('request_id', '')} Approved ✅"
            elif notification_type == "leave_request_rejected":
                subject = f"Leave Request {data.get('request_id', '')} Status Update"
            
            # Load template and render
            template = self._get_template(template_name)
            html_content = template.render(**data)
            
            # Generate plain text version
            text_content = self._html_to_text(html_content)
            
            return self._send_email(email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Failed to send email notification {notification_type}: {e}")
            return False
    
    def _send_sms_notification(self, notification_type: str, phone: str, data: Dict[str, Any]) -> bool:
        """Send SMS notification based on type"""
        try:
            # SMS templates (shorter versions)
            sms_templates = {
                "leave_request_approved": "✅ Your leave request {request_id} from {start_date} to {end_date} has been approved. Enjoy your time off! - {company_name}",
                "leave_request_rejected": "Your leave request {request_id} could not be approved. Please contact your manager for details. - {company_name}",
                "escalation_notification": "🚨 URGENT: Employee {employee_name} needs immediate HR assistance. Please check the HR portal. - {company_name}",
                "document_request_completed": "📄 Your requested document {document_title} is ready for download. Check your email for details. - {company_name}",
                "password_reset": "🔐 Password reset requested for your account. Check your email for the reset link. If you didn't request this, contact IT support. - {company_name}",
                "reminder_survey_pending": "📊 Reminder: Please complete the {survey_title} survey by {deadline}. Your feedback matters! - {company_name}"
            }
            
            template = sms_templates.get(notification_type)
            if not template:
                return False
            
            message = template.format(**data)
            return self._send_sms(phone, message)
            
        except Exception as e:
            logger.error(f"Failed to send SMS notification {notification_type}: {e}")
            return False
    
    def _send_in_app_notification(self, notification_type: str, user_id: int, data: Dict[str, Any]) -> bool:
        """Send in-app notification (placeholder for future implementation)"""
        try:
            # This would integrate with your in-app notification system
            # For now, we'll just log it
            logger.info(f"In-app notification {notification_type} for user {user_id}: {data.get('title', 'Notification')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send in-app notification {notification_type}: {e}")
            return False
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML content to plain text"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text()
        except:
            # Fallback: basic HTML tag removal
            import re
            text = re.sub('<[^<]+?>', '', html_content)
            return text.strip()
    
    # Specific notification methods for different HR events
    
    def notify_leave_request_submitted(self, leave_request: LeaveRequest):
        """Notify employee that leave request was submitted"""
        try:
            data = {
                "request_id": leave_request.request_id,
                "leave_type": leave_request.leave_type.name if leave_request.leave_type else "Leave",
                "start_date": format_date(leave_request.start_date, "display"),
                "end_date": format_date(leave_request.end_date, "display"),
                "total_days": float(leave_request.total_days),
                "reason": leave_request.reason
            }
            
            self.send_notification(
                "leave_request_submitted",
                leave_request.employee,
                data,
                ["email", "in_app"]
            )
            
        except Exception as e:
            logger.error(f"Failed to send leave request submitted notification: {e}")
    
    def notify_leave_request_approved(self, leave_request: LeaveRequest, approver: Employee):
        """Notify employee that leave request was approved"""
        try:
            data = {
                "request_id": leave_request.request_id,
                "leave_type": leave_request.leave_type.name if leave_request.leave_type else "Leave",
                "start_date": format_date(leave_request.start_date, "display"),
                "end_date": format_date(leave_request.end_date, "display"),
                "total_days": float(leave_request.total_days),
                "approver_name": approver.full_name,
                "approval_date": format_date(leave_request.approved_date, "display") if leave_request.approved_date else "Today",
                "manager_comments": leave_request.manager_comments or ""
            }
            
            self.send_notification(
                "leave_request_approved",
                leave_request.employee,
                data,
                ["email", "sms", "in_app"]
            )
            
        except Exception as e:
            logger.error(f"Failed to send leave request approval notification: {e}")
    
    def notify_leave_request_rejected(self, leave_request: LeaveRequest, approver: Employee):
        """Notify employee that leave request was rejected"""
        try:
            data = {
                "request_id": leave_request.request_id,
                "leave_type": leave_request.leave_type.name if leave_request.leave_type else "Leave",
                "start_date": format_date(leave_request.start_date, "display"),
                "end_date": format_date(leave_request.end_date, "display"),
                "total_days": float(leave_request.total_days),
                "rejection_reason": leave_request.manager_comments or "Please contact your manager for details"
            }
            
            self.send_notification(
                "leave_request_rejected",
                leave_request.employee,
                data,
                ["email", "in_app"]
            )
            
        except Exception as e:
            logger.error(f"Failed to send leave request rejection notification: {e}")
    
    def notify_manager_approval_needed(self, leave_request: LeaveRequest):
        """Notify manager that leave approval is needed"""
        try:
            if not leave_request.manager:
                return
            
            data = {
                "request_id": leave_request.request_id,
                "employee_name": leave_request.employee.full_name,
                "employee_id": leave_request.employee.employee_id,
                "leave_type": leave_request.leave_type.name if leave_request.leave_type else "Leave",
                "start_date": format_date(leave_request.start_date, "display"),
                "end_date": format_date(leave_request.end_date, "display"),
                "total_days": float(leave_request.total_days),
                "reason": leave_request.reason,
                "submitted_date": format_date(leave_request.submitted_date, "display") if leave_request.submitted_date else "Today",
                "approval_link": f"{self.company_website}/portal/leave-requests/{leave_request.request_id}"
            }
            
            # Create manager approval template if it doesn't exist
            manager_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Leave Approval Required</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #FF9800; color: white; padding: 20px; text-align: center; }
        .content { background-color: #f9f9f9; padding: 20px; }
        .footer { background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px; }
        .details { background-color: white; padding: 15px; margin: 10px 0; border-left: 4px solid #FF9800; }
        .button { display: inline-block; padding: 12px 25px; background-color: #FF9800; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; }
        .urgent { color: #FF9800; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⏰ Leave Approval Required</h1>
        </div>
        <div class="content">
            <p>Dear {{ manager_name }},</p>
            <p class="urgent">A leave request from your team member requires your approval.</p>
            
            <div class="details">
                <h3>Leave Request Details:</h3>
                <p><strong>Employee:</strong> {{ employee_name }} ({{ employee_id }})</p>
                <p><strong>Request ID:</strong> {{ request_id }}</p>
                <p><strong>Leave Type:</strong> {{ leave_type }}</p>
                <p><strong>Dates:</strong> {{ start_date }} to {{ end_date }}</p>
                <p><strong>Total Days:</strong> {{ total_days }}</p>
                <p><strong>Reason:</strong> {{ reason }}</p>
                <p><strong>Submitted:</strong> {{ submitted_date }}</p>
            </div>
            
            <p style="text-align: center;">
                <a href="{{ approval_link }}" class="button">Review & Approve</a>
            </p>
            
            <p>Please review this request at your earliest convenience.</p>
        </div>
        <div class="footer">
            <p>{{ company_name }} HR Department | {{ hr_email }} | {{ hr_phone }}</p>
        </div>
    </div>
</body>
</html>
            """
            
            # Save template if it doesn't exist
            template_path = self.template_dir / "manager_approval_needed.html"
            if not template_path.exists():
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(manager_template)
            
            data["manager_name"] = leave_request.manager.full_name
            
            self.send_notification(
                "manager_approval_needed",
                leave_request.manager,
                data,
                ["email", "in_app"]
            )
            
        except Exception as e:
            logger.error(f"Failed to send manager approval notification: {e}")
    
    def notify_document_request_completed(self, document_request: DocumentRequest):
        """Notify employee that document request is completed"""
        try:
            data = {
                "request_id": document_request.request_id,
                "document_title": document_request.document_title,
                "document_type": document_request.document_type.value if document_request.document_type else "Document",
                "processed_by": document_request.assigned_employee.full_name if document_request.assigned_employee else "HR Team",
                "completion_date": format_date(document_request.completed_at, "display") if document_request.completed_at else "Today",
                "completion_notes": document_request.completion_notes or "",
                "download_link": f"{self.company_website}/portal/documents/download/{document_request.request_id}" if document_request.generated_file_path else None
            }
            
            self.send_notification(
                "document_request_completed",
                document_request.employee,
                data,
                ["email", "sms", "in_app"]
            )
            
        except Exception as e:
            logger.error(f"Failed to send document completion notification: {e}")
    
    def send_survey_invitation(self, survey: Survey, employee: Employee):
        """Send survey invitation to employee"""
        try:
            data = {
                "survey_title": survey.title,
                "survey_description": survey.description or "Please participate in this important survey",
                "estimated_duration": survey.estimated_duration or 10,
                "deadline": format_date(survey.end_date, "display") if survey.end_date else "Soon",
                "is_anonymous": survey.is_anonymous,
                "survey_link": f"{self.company_website}/portal/surveys/{survey.id}/respond"
            }
            
            self.send_notification(
                "survey_invitation",
                employee,
                data,
                ["email", "in_app"]
            )
            
        except Exception as e:
            logger.error(f"Failed to send survey invitation: {e}")
    
    def send_password_reset_email(self, employee: Employee, reset_token: str, reset_link: str):
        """Send password reset email"""
        try:
            data = {
                "reset_token": reset_token,
                "reset_link": reset_link
            }
            
            self.send_notification(
                "password_reset",
                employee,
                data,
                ["email"]
            )
            
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")
    
    def notify_escalation(self, query_log: QueryLog, employee: Employee):
        """Send escalation notification to HR"""
        try:
            # Find HR personnel to notify
            from sqlalchemy.orm import Session
            from app.config.database import SessionLocal
            
            db = SessionLocal()
            try:
                hr_employees = db.query(Employee).join(Employee.role).filter(
                    Employee.role.has(title="HR Manager")
                ).all()
                
                if not hr_employees:
                    # Fallback to any HR department employee
                    hr_employees = db.query(Employee).join(Employee.department).filter(
                        Employee.department.has(name="Human Resources")
                    ).all()
                
                data = {
                    "query_text": query_log.user_query[:200] + "..." if len(query_log.user_query) > 200 else query_log.user_query,
                    "escalation_reason": query_log.escalation_reason or "Low AI confidence",
                    "confidence_score": float(query_log.confidence_score) if query_log.confidence_score else 0,
                    "sentiment": query_log.user_sentiment.value if query_log.user_sentiment else "Unknown"
                }
                
                for hr_employee in hr_employees:
                    self.send_notification(
                        "escalation_notification",
                        hr_employee,
                        data,
                        ["email", "sms", "in_app"]
                    )
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to send escalation notification: {e}")
    
    def send_bulk_notifications(self, employees: List[Employee], notification_type: str, data: Dict[str, Any]):
        """Send notifications to multiple employees"""
        try:
            logger.info(f"Sending bulk {notification_type} notifications to {len(employees)} employees")
            
            # Send notifications asynchronously
            tasks = []
            for employee in employees:
                task = self.send_notification_async(notification_type, employee, data)
                tasks.append(task)
            
            # Wait for all notifications to complete
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(asyncio.gather(*tasks))
                successful = sum(1 for result in results if any(result.values()))
                logger.info(f"Bulk notification completed: {successful}/{len(employees)} successful")
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Failed to send bulk notifications: {e}")
    
    def send_reminder_notifications(self):
        """Send various reminder notifications (to be called by scheduler)"""
        try:
            from sqlalchemy.orm import Session
            from app.config.database import SessionLocal
            from app.models.leave import LeaveBalance
            from app.models.survey import Survey, SurveyResponse
            from datetime import date, timedelta
            
            db = SessionLocal()
            try:
                # Remind about expiring leave balances
                self._send_leave_expiry_reminders(db)
                
                # Remind about pending surveys
                self._send_survey_reminders(db)
                
                # Remind about pending document requests (could be added)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to send reminder notifications: {e}")
    
    def _send_leave_expiry_reminders(self, db: Session):
        """Send reminders for leave balances expiring soon"""
        try:
            from sqlalchemy import and_
            
            current_year = date.today().year
            
            # Find employees with significant unused leave
            leave_balances = db.query(LeaveBalance).filter(
                and_(
                    LeaveBalance.year == current_year,
                    LeaveBalance.available_days > 5  # More than 5 days remaining
                )
            ).all()
            
            for balance in leave_balances:
                if balance.leave_type.is_carry_forward:
                    continue  # Skip if carry forward is allowed
                
                data = {
                    "leave_type": balance.leave_type.name,
                    "available_days": balance.available_days,
                    "expiry_date": f"December 31, {current_year}"
                }
                
                # Create expiry reminder template if needed
                self.send_notification(
                    "reminder_leave_expiring",
                    balance.employee,
                    data,
                    ["email", "in_app"]
                )
                
        except Exception as e:
            logger.error(f"Failed to send leave expiry reminders: {e}")
    
    def _send_survey_reminders(self, db: Session):
        """Send reminders for pending surveys"""
        try:
            from sqlalchemy import and_
            
            # Find active surveys ending soon
            reminder_date = date.today() + timedelta(days=3)
            
            active_surveys = db.query(Survey).filter(
                and_(
                    Survey.status == "active",
                    Survey.end_date >= date.today(),
                    Survey.end_date <= reminder_date
                )
            ).all()
            
            for survey in active_surveys:
                # Find employees who haven't responded
                responded_employee_ids = db.query(SurveyResponse.employee_id).filter(
                    SurveyResponse.survey_id == survey.id
                ).distinct().all()
                
                responded_ids = [r[0] for r in responded_employee_ids if r[0]]
                
                # Get all employees (based on targeting - simplified here)
                all_employees = db.query(Employee).filter(Employee.is_active == True).all()
                
                pending_employees = [emp for emp in all_employees if emp.id not in responded_ids]
                
                data = {
                    "survey_title": survey.title,
                    "deadline": format_date(survey.end_date, "display") if survey.end_date else "Soon"
                }
                
                for employee in pending_employees[:50]:  # Limit to avoid spam
                    self.send_notification(
                        "reminder_survey_pending",
                        employee,
                        data,
                        ["email", "in_app"]
                    )
                    
        except Exception as e:
            logger.error(f"Failed to send survey reminders: {e}")
    
    def get_notification_history(self, employee_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get notification history for an employee (placeholder)"""
        try:
            # This would query a notifications table if implemented
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Failed to get notification history: {e}")
            return []
    
    def update_notification_preferences(self, employee_id: int, preferences: Dict[str, Any]) -> bool:
        """Update notification preferences for an employee (placeholder)"""
        try:
            # This would update employee notification preferences
            # For now, just log the update
            logger.info(f"Updated notification preferences for employee {employee_id}: {preferences}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update notification preferences: {e}")
            return False
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        try:
            # This would return actual stats from a notifications table
            # For now, return placeholder data
            return {
                "total_sent": 0,
                "email_sent": 0,
                "sms_sent": 0,
                "in_app_sent": 0,
                "failed_notifications": 0,
                "last_24_hours": 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get notification stats: {e}")
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check notification service health"""
        try:
            status = {
                "email_service": False,
                "sms_service": False,
                "templates_loaded": False,
                "configuration": {}
            }
            
            # Check email configuration
            if self.smtp_username and self.smtp_password:
                try:
                    with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                        if self.smtp_use_tls:
                            server.starttls()
                        server.login(self.smtp_username, self.smtp_password)
                        status["email_service"] = True
                except:
                    pass
            
            # Check SMS configuration
            if self.sms_enabled and self.twilio_account_sid and self.twilio_auth_token:
                status["sms_service"] = True
            
            # Check templates
            template_files = list(self.template_dir.glob("*.html"))
            status["templates_loaded"] = len(template_files) > 0
            
            # Configuration summary
            status["configuration"] = {
                "smtp_host": self.smtp_host,
                "smtp_port": self.smtp_port,
                "from_email": self.from_email,
                "sms_enabled": self.sms_enabled,
                "template_count": len(template_files)
            }
            
            return {
                "status": "healthy" if status["email_service"] else "degraded",
                "services": status,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Notification service health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# Global notification service instance
notification_service = NotificationService()