"""
Slack 웹훅 API 엔드포인트
"""
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from typing import Optional
import json
from datetime import datetime
from services.slack_webhook import SlackWebhookService

router = APIRouter(prefix="/api/slack", tags=["slack"])

# 전역 Slack 웹훅 서비스 인스턴스 (main.py에서 설정)
slack_webhook_service: Optional[SlackWebhookService] = None


def set_slack_webhook_service(service: SlackWebhookService):
    """Slack 웹훅 서비스 설정"""
    global slack_webhook_service
    slack_webhook_service = service


@router.post("/webhook")
async def slack_webhook(
    request: Request,
    x_slack_signature: Optional[str] = Header(None, alias="X-Slack-Signature"),
    x_slack_request_timestamp: Optional[str] = Header(None, alias="X-Slack-Request-Timestamp"),
):
    """Slack 웹훅 엔드포인트"""
    # 요청 본문 읽기
    body = await request.body()
    body_str = body.decode('utf-8')
    
    # 모든 요청 로그 출력 (디버깅)
    print(f"\n{'='*60}")
    print(f"[SlackWebhook] New request received at {datetime.now().isoformat()}")
    print(f"[SlackWebhook] Method: {request.method}")
    print(f"[SlackWebhook] URL: {request.url}")
    print(f"[SlackWebhook] Headers: {dict(request.headers)}")
    print(f"[SlackWebhook] Body length: {len(body_str)}")
    print(f"[SlackWebhook] Body: {body_str[:1000]}")  # 처음 1000자 출력
    print(f"{'='*60}\n")
    
    # 이벤트 파싱
    try:
        event_data = json.loads(body_str)
    except json.JSONDecodeError as e:
        print(f"[SlackWebhook] JSON decode error: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # URL 검증 처리 (서명 검증 전에 먼저 처리)
    if event_data.get("type") == "url_verification":
        challenge = event_data.get("challenge")
        if challenge:
            print(f"[SlackWebhook] URL verification challenge received: {challenge}")
            return JSONResponse(content={"challenge": challenge})
        else:
            raise HTTPException(status_code=400, detail="Challenge parameter missing")
    
    # URL 검증이 아닌 경우에만 서비스 초기화 확인 및 서명 검증
    if not slack_webhook_service:
        print(f"[SlackWebhook] ERROR: Slack webhook service not initialized")
        raise HTTPException(status_code=500, detail="Slack webhook service not initialized")
    
    # 서명 검증 (URL 검증 후 실제 이벤트에서만)
    # 개발 환경에서는 서명이 없어도 처리 가능하도록 함
    if x_slack_signature and x_slack_request_timestamp:
        is_valid = slack_webhook_service.verify_signature(
            x_slack_request_timestamp,
            body_str,
            x_slack_signature
        )
        if not is_valid:
            print(f"[SlackWebhook] ERROR: Invalid signature")
            print(f"[SlackWebhook] Expected signature: {x_slack_signature}")
            raise HTTPException(status_code=401, detail="Invalid signature")
        print(f"[SlackWebhook] Signature verified successfully")
    else:
        print(f"[SlackWebhook] WARNING: No signature provided (development mode?)")
    
    # 이벤트 처리
    try:
        # 디버깅: 받은 이벤트 로그 출력
        print(f"[SlackWebhook] Received event: type={event_data.get('type')}")
        print(f"[SlackWebhook] Event data: {json.dumps(event_data, indent=2, ensure_ascii=False)}")
        
        task = slack_webhook_service.process_event(event_data)
        
        if task:
            print(f"[SlackWebhook] Task created: {task.title}")
            return JSONResponse(content={
                "status": "success",
                "task_id": task.id,
                "message": "Task created successfully"
            })
        else:
            print(f"[SlackWebhook] Event processed but no task created")
            return JSONResponse(content={
                "status": "success",
                "message": "Event processed, no task created"
            })
    except Exception as e:
        print(f"[SlackWebhook] Error processing event: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

