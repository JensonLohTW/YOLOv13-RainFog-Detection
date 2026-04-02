from pathlib import Path

from common.core.env import env, env_bool, env_csv, env_float, env_int

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = BACKEND_DIR.parent

SECRET_KEY = env("DJANGO_SECRET_KEY", "replace-me")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_csv("DJANGO_ALLOWED_HOSTS", ["127.0.0.1", "localhost"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "apps.agent",
    "apps.accounts",
    "apps.media",
    "apps.detection",
    "apps.dashboard",
    "apps.audit",
    "apps.system",
    "apps.training",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.audit.middleware.OperationLogMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("MYSQL_DATABASE", "rainfog"),
        "USER": env("MYSQL_USER", "rainfog"),
        "PASSWORD": env("MYSQL_PASSWORD", "rainfog123"),
        "HOST": env("MYSQL_HOST", "127.0.0.1"),
        "PORT": env("MYSQL_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = REPO_ROOT / "data" / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = REPO_ROOT / "data" / "uploads"
RESULTS_URL = "/media-results/"
RESULTS_ROOT = REPO_ROOT / "data" / "results"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOW_ALL_ORIGINS = True

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": env_int("API_PAGE_SIZE", 20),
}

INFERENCE_BASE_URL = env("INFERENCE_BASE_URL", "http://127.0.0.1:9000")
INFERENCE_TIMEOUT = env_int("INFERENCE_TIMEOUT", 30)
INFERENCE_USE_MOCK = env_bool("INFERENCE_USE_MOCK", True)

DETECTION_DEFAULT_RECOGNITION_MODE = env("DETECTION_DEFAULT_RECOGNITION_MODE", "scene_default")
DETECTION_DEFAULT_SCENE = env("DETECTION_DEFAULT_SCENE", "rain_fog")
DETECTION_SCENE_CONFIDENCE_THRESHOLD = env_float("DETECTION_SCENE_CONFIDENCE_THRESHOLD", 0.35)
DETECTION_SCENE_IOU_THRESHOLD = env_float("DETECTION_SCENE_IOU_THRESHOLD", 0.5)
DETECTION_SCENE_PREPROCESS_MODE = env("DETECTION_SCENE_PREPROCESS_MODE", "auto")
DETECTION_SCENE_PREPROCESS_PROFILE = env("DETECTION_SCENE_PREPROCESS_PROFILE", "scene_default")
DETECTION_SCENE_PREPROCESS_ENABLE_GAMMA = env_bool("DETECTION_SCENE_PREPROCESS_ENABLE_GAMMA", True)
DETECTION_SCENE_MODEL_PROFILE = env("DETECTION_SCENE_MODEL_PROFILE", "scene_default")
DETECTION_SCENE_IMAGE_SIZE = env_int("DETECTION_SCENE_IMAGE_SIZE", 960)
DETECTION_SCENE_ENABLE_AUGMENT = env_bool("DETECTION_SCENE_ENABLE_AUGMENT", True)

REDIS_HOST = env("REDIS_HOST", "127.0.0.1")
REDIS_PORT = env_int("REDIS_PORT", 6379)
REDIS_DB = env_int("REDIS_DB", 0)
REDIS_CACHE_TTL = env_int("REDIS_CACHE_TTL", 60)

LLM_PROVIDER = env("LLM_PROVIDER", "mock")
LLM_BASE_URL = env("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = env("LLM_MODEL", "gpt-4o-mini")
LLM_API_KEY = env("LLM_API_KEY", "")
LLM_TEMPERATURE = env_float("LLM_TEMPERATURE", 0.2)
LLM_MAX_TOKENS = env_int("LLM_MAX_TOKENS", 600)
LLM_TIMEOUT = env_int("LLM_TIMEOUT", 20)
