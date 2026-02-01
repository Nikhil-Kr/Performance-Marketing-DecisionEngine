"""
Offline Channel Executor - Notification-based action handling.

Offline channels (TV, Radio, Podcast, Direct Mail, OOH, Events) don't have APIs.
Actions are executed by sending notifications to the appropriate teams:
- Slack messages to media buying team
- Email to vendor contacts
- Logging for audit trail

This executor translates proposed actions into human-readable alerts
that prompt manual follow-up.
"""
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Any

from ..interfaces.base import BaseActionExecutor


class OfflineExecutor(BaseActionExecutor):
    """
    Notification-based executor for offline marketing channels.
    
    Since offline channels don't have APIs, this executor:
    1. Formats the action into a human-readable message
    2. Sends to Slack (media buying team)
    3. Optionally sends email to vendor contacts
    4. Logs for audit trail
    
    Supported channels: TV, Podcast, Radio, Direct Mail, OOH, Events
    """
    
    def __init__(self, channel: str = "offline"):
        """
        Initialize the offline executor.
        
        Args:
            channel: Specific offline channel (tv, podcast, radio, etc.)
        """
        from src.utils.config import settings
        
        self.settings = settings
        self.channel = channel.lower()
        self._execution_log: list[dict] = []
        
        # Channel-specific Slack routing
        self.channel_slack_map = {
            "tv": settings.slack_channel_media_buying,
            "tv_buying": settings.slack_channel_media_buying,
            "radio": settings.slack_channel_media_buying,
            "radio_buying": settings.slack_channel_media_buying,
            "podcast": settings.slack_channel_media_buying,
            "podcast_network": settings.slack_channel_media_buying,
            "direct_mail": settings.slack_channel_media_buying,
            "ooh": settings.slack_channel_media_buying,
            "ooh_vendor": settings.slack_channel_media_buying,
            "events": settings.slack_channel_media_buying,
            "events_team": settings.slack_channel_media_buying,
            "notification": settings.slack_channel_alerts,
        }
    
    @property
    def platform_name(self) -> str:
        return f"offline_{self.channel}"
    
    @property
    def supported_actions(self) -> list[str]:
        return [
            "negotiation",      # Request make-goods, renegotiate
            "communication",    # Contact vendor/partner
            "notification",     # Alert internal team
            "pause",            # Request campaign pause
            "budget_change",    # Request budget modification
        ]
    
    def execute(self, action: dict) -> dict[str, Any]:
        """
        Execute action by sending notifications.
        
        1. Validates the action
        2. Formats message for humans
        3. Sends Slack notification
        4. Optionally sends email
        5. Returns execution result
        """
        execution_id = f"offline_exec_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now().isoformat()
        
        # Validate
        is_valid, error = self.validate(action)
        if not is_valid:
            return {
                "status": "failed",
                "execution_id": execution_id,
                "timestamp": timestamp,
                "error": error,
                "action": action,
            }
        
        # Format the message
        message = self._format_action_message(action)
        slack_channel = self._get_slack_channel(action)
        
        # Send Slack notification
        slack_result = self._send_slack_notification(message, slack_channel)
        
        # Send email if configured and appropriate
        email_result = None
        if self._should_send_email(action):
            email_result = self._send_email_notification(action, message)
        
        # Log execution
        log_entry = {
            "execution_id": execution_id,
            "timestamp": timestamp,
            "action": action,
            "message": message,
            "slack_result": slack_result,
            "email_result": email_result,
            "status": "success" if slack_result.get("ok") else "partial",
        }
        self._execution_log.append(log_entry)
        
        # Print for visibility
        self._print_execution(action, execution_id, slack_channel)
        
        return {
            "status": log_entry["status"],
            "execution_id": execution_id,
            "timestamp": timestamp,
            "message": f"Notification sent to {slack_channel}",
            "slack_result": slack_result,
            "email_result": email_result,
            "action_message": message,
        }
    
    def _format_action_message(self, action: dict) -> str:
        """Format action into human-readable Slack message."""
        action_type = action.get("action_type", "unknown")
        operation = action.get("operation", "unknown")
        channel = action.get("platform", self.channel)
        resource_id = action.get("resource_id", "N/A")
        params = action.get("parameters", {})
        impact = action.get("estimated_impact", "")
        risk = action.get("risk_level", "medium")
        context = action.get("context", "")
        
        # Emoji based on action type
        emoji_map = {
            "negotiation": "🤝",
            "communication": "📞",
            "notification": "🔔",
            "pause": "⏸️",
            "budget_change": "💰",
        }
        emoji = emoji_map.get(action_type, "📋")
        
        # Risk emoji
        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "🚨"}.get(risk, "🟡")
        
        # Build message blocks
        message_parts = [
            f"{emoji} *ACTION REQUIRED: {channel.upper().replace('_', ' ')}*",
            "",
            f"*Action Type:* {action_type.replace('_', ' ').title()}",
            f"*Operation:* {operation.replace('_', ' ').title()}",
            f"*Campaign/Resource:* {resource_id}",
            f"*Risk Level:* {risk_emoji} {risk.upper()}",
        ]
        
        # Add parameters if present
        if params:
            message_parts.append("")
            message_parts.append("*Details:*")
            for key, value in params.items():
                message_parts.append(f"  • {key.replace('_', ' ').title()}: {value}")
        
        # Add context
        if context:
            message_parts.append("")
            message_parts.append(f"*Context:* {context}")
        
        # Add impact
        if impact:
            message_parts.append("")
            message_parts.append(f"*Expected Impact:* {impact}")
        
        # Add call to action
        message_parts.append("")
        message_parts.append("_Please take action and update the team on resolution._")
        
        return "\n".join(message_parts)
    
    def _get_slack_channel(self, action: dict) -> str:
        """Determine which Slack channel to send to."""
        # Check if team is specified in parameters
        params = action.get("parameters", {})
        team = params.get("team", "").lower()
        
        if team:
            return self.settings.get_slack_channel_for_team(team)
        
        # Default to channel-specific mapping
        platform = action.get("platform", self.channel).lower()
        return self.channel_slack_map.get(platform, self.settings.slack_channel_media_buying)
    
    def _send_slack_notification(self, message: str, channel: str) -> dict:
        """Send notification to Slack."""
        if not self.settings.has_slack_configured:
            print("  ⚠️ Slack not configured - notification logged only")
            return {"ok": False, "error": "Slack not configured"}
        
        try:
            import requests
            
            payload = {
                "channel": channel,
                "text": message,
                "mrkdwn": True,
            }
            
            response = requests.post(
                self.settings.slack_webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                return {"ok": True, "channel": channel}
            else:
                return {"ok": False, "error": f"HTTP {response.status_code}"}
        
        except Exception as e:
            print(f"  ⚠️ Slack send failed: {e}")
            return {"ok": False, "error": str(e)}
    
    def _should_send_email(self, action: dict) -> bool:
        """Determine if email should be sent."""
        if not self.settings.has_email_configured:
            return False
        
        # Send email for vendor-related actions
        action_type = action.get("action_type", "")
        return action_type in ("negotiation", "communication")
    
    def _send_email_notification(self, action: dict, message: str) -> dict:
        """Send email notification to vendor contact."""
        try:
            platform = action.get("platform", self.channel)
            vendor_email = self.settings.get_vendor_email(platform)
            
            if not vendor_email:
                return {"ok": False, "error": "No vendor email configured"}
            
            # Create email
            msg = MIMEMultipart()
            msg["From"] = self.settings.email_sender
            msg["To"] = vendor_email
            msg["Subject"] = f"[Action Required] {platform.upper()} Campaign Update"
            
            # Convert Slack markdown to plain text
            body = message.replace("*", "").replace("_", "").replace("`", "")
            msg.attach(MIMEText(body, "plain"))
            
            # Send
            with smtplib.SMTP(self.settings.email_smtp_host, self.settings.email_smtp_port) as server:
                server.starttls()
                server.login(self.settings.email_sender, self.settings.email_sender_password)
                server.send_message(msg)
            
            return {"ok": True, "recipient": vendor_email}
        
        except Exception as e:
            print(f"  ⚠️ Email send failed: {e}")
            return {"ok": False, "error": str(e)}
    
    def _print_execution(self, action: dict, execution_id: str, channel: str) -> None:
        """Print execution details for visibility."""
        action_type = action.get("action_type", "unknown")
        platform = action.get("platform", self.channel)
        
        print(f"\n  📢 [OFFLINE NOTIFICATION] {action_type}")
        print(f"     ID: {execution_id}")
        print(f"     Channel: {platform}")
        print(f"     Slack: {channel}")
    
    def validate(self, action: dict) -> tuple[bool, str]:
        """Validate action for offline execution."""
        action_type = action.get("action_type")
        
        if action_type not in self.supported_actions:
            return False, f"Unsupported action type for Offline: {action_type}"
        
        return True, ""
    
    def preview(self, action: dict) -> dict[str, Any]:
        """Preview what the notification would look like."""
        message = self._format_action_message(action)
        slack_channel = self._get_slack_channel(action)
        
        return {
            "preview": "Would send notification to team",
            "slack_channel": slack_channel,
            "email_recipient": self.settings.get_vendor_email(action.get("platform", self.channel)),
            "message_preview": message[:500] + "..." if len(message) > 500 else message,
            "requires_approval": False,  # Notifications don't need approval
        }
    
    def rollback(self, execution_id: str) -> dict[str, Any]:
        """Notifications cannot be rolled back."""
        return {
            "status": "failed",
            "error": "Notifications cannot be rolled back",
        }
    
    def get_execution_log(self) -> list[dict]:
        """Get execution log."""
        return self._execution_log.copy()