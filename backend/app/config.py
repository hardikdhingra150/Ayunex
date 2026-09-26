import os
from pathlib import Path
from dataclasses import dataclass, field


def _normalize_db_url(url: str | None = None) -> str:
    raw = url if url is not None else os.getenv('DATABASE_URL', '')
    if raw:
        if raw.startswith('sqlite:///') and not raw.startswith('sqlite:////') and not raw.startswith('sqlite:///:memory:'):
            rel_path = raw[len('sqlite:///'):]
            if rel_path.startswith('./'):
                rel_path = rel_path[2:]
            backend_dir = Path(__file__).resolve().parents[1]
            return f'sqlite:///{backend_dir / rel_path}'
        return raw
    backend_dir = Path(__file__).resolve().parents[1]
    return f'sqlite:///{backend_dir / "ayunex.db"}'


def _default_dev_token():
    if os.getenv('APP_ENV','development') not in {'development','test'}:
        return ''
    env_token = os.getenv('DEV_API_TOKEN', '')
    if env_token:
        return env_token
    token_file = Path(__file__).resolve().parents[1] / '.dev-token'
    if token_file.exists():
        try:
            return token_file.read_text().strip()
        except OSError:
            pass
    return ''


@dataclass
class Settings:
    auth_mode: str = field(default_factory=lambda: os.getenv('AUTH_MODE','builtin'))
    public_app_url: str = field(default_factory=lambda: os.getenv('PUBLIC_APP_URL','http://127.0.0.1:8000'))
    smtp_host: str = field(default_factory=lambda: os.getenv('SMTP_HOST',''))
    smtp_port: int = field(default_factory=lambda: int(os.getenv('SMTP_PORT','587')))
    smtp_user: str = field(default_factory=lambda: os.getenv('SMTP_USER',''))
    smtp_password: str = field(default_factory=lambda: os.getenv('SMTP_PASSWORD',''))
    mail_from: str = field(default_factory=lambda: os.getenv('MAIL_FROM',''))
    ai_provider: str = field(default_factory=lambda: os.getenv('AI_PROVIDER',''))
    ai_key: str = field(default_factory=lambda: os.getenv('AI_API_KEY',''))
    ai_model: str = field(default_factory=lambda: os.getenv('AI_GENERATION_MODEL',''))
    embedding_model: str = field(default_factory=lambda: os.getenv('AI_EMBEDDING_MODEL',''))
    cloud_processing_allowed: bool = field(default_factory=lambda: os.getenv('CLOUD_PROCESSING_ALLOWED','false')=='true')
    allowed_hosts: list[str] = field(default_factory=lambda: os.getenv('ALLOWED_HOSTS','localhost,127.0.0.1,testserver').split(','))
    redis_url: str = field(default_factory=lambda: os.getenv('REDIS_URL',''))
    rate_limit: int = field(default_factory=lambda: int(os.getenv('RATE_LIMIT_PER_MINUTE','120')))
    max_body_bytes: int = 1024*1024
    guidance_mode: str = field(default_factory=lambda: os.getenv('GUIDANCE_MODE','external'))
    database_url: str = field(default_factory=_normalize_db_url)
    environment: str = field(default_factory=lambda: os.getenv('APP_ENV', 'development'))
    dev_token: str = field(default_factory=_default_dev_token)
    identity_url: str = field(default_factory=lambda: os.getenv('IDENTITY_INTROSPECTION_URL', ''))
    identity_service_token: str = field(default_factory=lambda: os.getenv('IDENTITY_SERVICE_TOKEN', ''))
    guidance_url: str = field(default_factory=lambda: os.getenv('GUIDANCE_SERVICE_URL', ''))
    guidance_service_token: str = field(default_factory=lambda: os.getenv('GUIDANCE_SERVICE_TOKEN', ''))
    cors_origins: list[str] = field(default_factory=lambda: os.getenv('CORS_ORIGINS', 'http://127.0.0.1:5173,http://localhost:5173').split(','))

    def __post_init__(self):
        self.database_url = _normalize_db_url(self.database_url)
        if not self.dev_token and self.environment == 'development':
            self.dev_token = _default_dev_token()

    def validate(self):
        if self.auth_mode not in {'builtin','external'}:raise ValueError('Invalid AUTH_MODE')
        if self.guidance_mode not in {'external','corpus','hosted'}:raise ValueError('Invalid GUIDANCE_MODE')
        if self.guidance_mode=='hosted':
            if self.ai_provider not in {'openai','gemini','groq'}:raise ValueError('Choose AI_PROVIDER=openai, gemini or groq')
            if not all((self.ai_key,self.ai_model,self.cloud_processing_allowed)) or (self.ai_provider!='groq' and not self.embedding_model):
                raise ValueError('Hosted mode requires key, model IDs and explicit CLOUD_PROCESSING_ALLOWED=true')
            if self.ai_provider=='groq' and self.embedding_model:
                raise ValueError('Groq adapter is generation-only; leave AI_EMBEDDING_MODEL empty')
        if self.rate_limit<1:raise ValueError('Rate limit must be positive')
        if self.environment not in {'development', 'test', 'production'}:
            raise ValueError('Invalid APP_ENV')
        for url in (self.identity_url, self.guidance_url):
            if url and not url.startswith('https://'):
                raise ValueError('External service URLs must use HTTPS')
        if self.dev_token and len(self.dev_token) < 32:
            raise ValueError('DEV_API_TOKEN must contain at least 32 characters')
        if self.environment == 'production':
            if not self.redis_url:raise ValueError('Production requires shared Redis rate limits')
            if '*' in self.allowed_hosts or 'testserver' in self.allowed_hosts:raise ValueError('Production requires explicit ALLOWED_HOSTS')
            if self.guidance_mode=='external' and (not self.guidance_url or not self.guidance_service_token):raise ValueError('Production external guidance needs configured service credentials')
            if self.dev_token or (self.auth_mode=='external' and (not self.identity_url or not self.identity_service_token)):
                raise ValueError('Production requires Module D identity; development tokens forbidden')
            if self.auth_mode=='builtin' and (not self.public_app_url.startswith('https://') or not all((self.smtp_host,self.smtp_user,self.smtp_password,self.mail_from))):
                raise ValueError('Builtin production accounts require HTTPS PUBLIC_APP_URL and authenticated SMTP')
            if not self.database_url.startswith('postgresql'):
                raise ValueError('Production requires PostgreSQL')
            if '*' in self.cors_origins or any(not x.startswith('https://') for x in self.cors_origins):
                raise ValueError('Production CORS requires explicit HTTPS origins')
