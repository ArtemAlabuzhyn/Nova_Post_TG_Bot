from nova_post_bot.config import settings

def test_app_env_is_development():
    assert settings.app_env == 'development'

def test_log_level_is_info():
    assert settings.log_level == 'INFO'

def test_telegram_bot_token_is_not_empty():
    assert settings.telegram_bot_token

def test_api_key_is_not_empty():
    assert settings.nova_post_api_key