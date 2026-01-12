"""
ConfigHandlers - 설정 관련 핸들러

처리하는 메시지 타입:
- UPDATE_LLM_CONFIG
"""

from .base_handler import BaseHandler


class ConfigHandlers(BaseHandler):
    """설정 관련 메시지 핸들러"""

    async def handle_update_llm_config(self, client_id: str, payload: dict):
        """LLM 설정 업데이트 처리 (UPDATE_LLM_CONFIG)"""
        provider = payload.get('provider')
        model = payload.get('model')
        api_key = payload.get('apiKey')
        base_url = payload.get('baseUrl')
        temperature = payload.get('temperature')
        max_tokens = payload.get('maxTokens')

        self.log(f"Received LLM config update: provider={provider}, model={model}, baseUrl={base_url}")

        # LLMClient 설정 업데이트 (models.orchestration의 Singleton 사용)
        from models.orchestration import LLMClient
        llm_client = LLMClient()
        updated = llm_client.update_config(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens
        )

        if updated:
            self.broadcast_notification(
                f"LLM 설정이 업데이트되었습니다: {model}",
                "success"
            )
            self.log(f"LLM config updated successfully: {model}")
        else:
            self.log(f"LLM config update failed or no changes")
