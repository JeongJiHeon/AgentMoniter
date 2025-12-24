"""
Slack 웹훅 서비스

Slack 이벤트를 받아서 Task로 변환하는 서비스
"""
import json
import hmac
import hashlib
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from models.task import Task, CreateTaskInput, TaskPriority, TaskSource


class SlackWebhookService:
    """Slack 웹훅 이벤트 처리 서비스"""
    
    def __init__(self, signing_secret: Optional[str] = None):
        self.signing_secret = signing_secret
        self.task_handlers: list = []
    
    def verify_signature(self, timestamp: str, body: str, signature: str) -> bool:
        """Slack 서명 검증"""
        if not self.signing_secret:
            print(f"[SlackWebhookService] WARNING: No signing secret configured, skipping verification")
            return True  # 개발 환경에서는 검증 생략
        
        # 타임스탬프 검증 (5분 이내)
        if abs(time.time() - int(timestamp)) > 60 * 5:
            return False
        
        # 서명 생성
        sig_basestring = f"v0:{timestamp}:{body}"
        my_signature = 'v0=' + hmac.new(
            self.signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(my_signature, signature)
    
    def on_task_created(self, handler: Callable[[Task], None]):
        """Task 생성 핸들러 등록"""
        self.task_handlers.append(handler)
    
    def process_event(self, event_data: Dict[str, Any]) -> Optional[Task]:
        """Slack 이벤트 처리"""
        event_type = event_data.get("type")
        
        print(f"[SlackWebhookService] Processing event type: {event_type}")
        print(f"[SlackWebhookService] Full event data keys: {list(event_data.keys())}")
        
        if event_type == "url_verification":
            # Slack URL 검증 - 이미 API 레벨에서 처리됨
            print(f"[SlackWebhookService] URL verification event (should be handled by API)")
            return None
        
        if event_type == "event_callback":
            event = event_data.get("event", {})
            event_subtype = event.get("type")
            print(f"[SlackWebhookService] Event callback received: {event_subtype}")
            print(f"[SlackWebhookService] Event details: {json.dumps(event, indent=2, ensure_ascii=False)}")
            
            if not event:
                print(f"[SlackWebhookService] WARNING: Empty event in event_callback")
                return None
            
            return self._handle_event(event)
        
        print(f"[SlackWebhookService] Unknown event type: {event_type}")
        print(f"[SlackWebhookService] Event data: {json.dumps(event_data, indent=2, ensure_ascii=False)}")
        return None
    
    def _handle_event(self, event: Dict[str, Any]) -> Optional[Task]:
        """이벤트 타입별 처리"""
        event_type = event.get("type")
        
        print(f"[SlackWebhookService] Handling event type: {event_type}")
        print(f"[SlackWebhookService] Event details: {json.dumps(event, indent=2, ensure_ascii=False)}")
        
        if event_type == "app_mention":
            # 봇이 멘션된 경우
            print(f"[SlackWebhookService] Detected app_mention event")
            return self._handle_mention(event)
        
        elif event_type == "message":
            # 메시지 이벤트
            print(f"[SlackWebhookService] Detected message event")
            
            # 메시지 삭제 이벤트는 무시
            subtype = event.get("subtype")
            if subtype == "message_deleted":
                print(f"[SlackWebhookService] Message deleted event, skipping")
                return None
            
            # DM인지 확인 (channel_type이 'im'인 경우)
            channel_type = event.get("channel_type")
            if channel_type == "im":
                print(f"[SlackWebhookService] Detected DM (channel_type=im)")
                return self._handle_dm(event)
            
            # 멘션이 포함된 경우
            text = event.get("text", "")
            if "<@" in text or "<!subteam^" in text:
                print(f"[SlackWebhookService] Detected mention in message text")
                return self._handle_mention(event)
        
        print(f"[SlackWebhookService] Event type {event_type} not handled")
        return None
    
    def _handle_mention(self, event: Dict[str, Any]) -> Optional[Task]:
        """멘션 이벤트 처리"""
        print(f"[SlackWebhookService] Handling mention event")
        print(f"[SlackWebhookService] Event keys: {list(event.keys())}")
        
        text = event.get("text", "")
        user = event.get("user", "")
        channel = event.get("channel", "")
        ts = event.get("ts", "")
        subtype = event.get("subtype")
        
        print(f"[SlackWebhookService] Mention details:")
        print(f"  - text: {text[:100] if text else '(empty)'}")
        print(f"  - user: {user}")
        print(f"  - channel: {channel}")
        print(f"  - ts: {ts}")
        print(f"  - subtype: {subtype}")
        
        # 봇 메시지는 무시
        if subtype == "bot_message":
            print(f"[SlackWebhookService] Bot message, skipping")
            return None
        
        # 멘션 제거
        import re
        cleaned_text = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
        cleaned_text = re.sub(r'<!subteam\^[A-Z0-9]+\|[^>]+>', '', cleaned_text).strip()
        cleaned_text = re.sub(r'<!channel>', '', cleaned_text).strip()
        cleaned_text = re.sub(r'<!here>', '', cleaned_text).strip()
        
        print(f"[SlackWebhookService] Cleaned text: {cleaned_text[:100] if cleaned_text else '(empty)'}")
        
        if not cleaned_text:
            print(f"[SlackWebhookService] No text after cleaning, skipping")
            return None
        
        # Task 생성 (Slack에서 온 Task는 기본적으로 자동 할당)
        try:
            task = Task(
                title=f"Slack 멘션: {cleaned_text[:50]}",
                description=f"채널: {channel}\n메시지: {cleaned_text}",
                priority=TaskPriority.MEDIUM,
                source=TaskSource.SLACK,
                sourceReference=f"{channel}:{ts}",
                tags=["slack", "mention"],
                autoAssign=True,  # Slack에서 온 Task는 자동 할당
            )
            
            print(f"[SlackWebhookService] Created task: {task.id} - {task.title}")
            print(f"[SlackWebhookService] Task details: {task.model_dump_json(indent=2)}")
        except Exception as e:
            print(f"[SlackWebhookService] ERROR creating task: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        # 핸들러 호출
        print(f"[SlackWebhookService] Calling {len(self.task_handlers)} task handler(s)")
        for i, handler in enumerate(self.task_handlers):
            try:
                print(f"[SlackWebhookService] Calling handler {i+1}/{len(self.task_handlers)}")
                handler(task)
                print(f"[SlackWebhookService] Task handler {i+1} called successfully")
            except Exception as e:
                print(f"[SlackWebhookService] Handler {i+1} error: {e}")
                import traceback
                traceback.print_exc()
        
        return task
    
    def _handle_dm(self, event: Dict[str, Any]) -> Optional[Task]:
        """DM 이벤트 처리"""
        print(f"[SlackWebhookService] Handling DM event: {event}")
        
        text = event.get("text", "")
        user = event.get("user", "")
        channel = event.get("channel", "")
        ts = event.get("ts", "")
        subtype = event.get("subtype")
        
        print(f"[SlackWebhookService] DM details: text={text}, user={user}, channel={channel}, subtype={subtype}")
        
        if not text:
            print(f"[SlackWebhookService] No text in DM, skipping")
            return None
        
        # 봇 메시지는 무시
        if subtype == "bot_message":
            print(f"[SlackWebhookService] Bot message, skipping")
            return None
        
        # Task 생성 (Slack에서 온 Task는 기본적으로 자동 할당)
        try:
            task = Task(
                title=f"Slack DM: {text[:50]}",
                description=f"DM 메시지:\n{text}",
                priority=TaskPriority.MEDIUM,
                source=TaskSource.SLACK,
                sourceReference=f"{channel}:{ts}",
                tags=["slack", "dm"],
                autoAssign=True,  # Slack에서 온 Task는 자동 할당
            )
            
            print(f"[SlackWebhookService] Created DM task: {task.id} - {task.title}")
            print(f"[SlackWebhookService] Task details: {task.model_dump_json(indent=2)}")
        except Exception as e:
            print(f"[SlackWebhookService] ERROR creating DM task: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        # 핸들러 호출
        print(f"[SlackWebhookService] Calling {len(self.task_handlers)} task handler(s)")
        for i, handler in enumerate(self.task_handlers):
            try:
                print(f"[SlackWebhookService] Calling handler {i+1}/{len(self.task_handlers)}")
                handler(task)
                print(f"[SlackWebhookService] Task handler {i+1} called successfully")
            except Exception as e:
                print(f"[SlackWebhookService] Handler {i+1} error: {e}")
                import traceback
                traceback.print_exc()
        
        return task

