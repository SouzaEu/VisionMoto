#!/usr/bin/env python3
"""
Configuração centralizada do VisionMoto
Usa variáveis de ambiente para segurança
"""

import os
import secrets
from typing import Optional
from pathlib import Path


class Config:
    """Configuração base do sistema"""

    # Diretório base do projeto
    BASE_DIR = Path(__file__).parent.parent

    # Segurança - NUNCA hardcode isso
    SECRET_KEY: str = os.getenv("VISIONMOTO_SECRET_KEY", secrets.token_urlsafe(32))
    
    # Banco de dados
    DATABASE_PATH: str = os.getenv(
        "DATABASE_PATH", 
        str(BASE_DIR / "data" / "visionmoto_integration.db")
    )
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "5001"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # CORS
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # YOLO Model
    YOLO_MODEL_PATH: str = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
    YOLO_CONFIDENCE_THRESHOLD: float = float(
        os.getenv("YOLO_CONFIDENCE_THRESHOLD", "0.5")
    )
    
    # IoT
    MQTT_BROKER: str = os.getenv("MQTT_BROKER", "localhost")
    MQTT_PORT: int = int(os.getenv("MQTT_PORT", "1883"))
    MQTT_USERNAME: Optional[str] = os.getenv("MQTT_USERNAME")
    MQTT_PASSWORD: Optional[str] = os.getenv("MQTT_PASSWORD")
    
    # Performance
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "4"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    
    @classmethod
    def validate(cls) -> bool:
        """Valida configurações críticas"""
        errors = []
        
        # Verifica se SECRET_KEY não é o padrão em produção
        if not cls.DEBUG and cls.SECRET_KEY == secrets.token_urlsafe(32):
            errors.append("SECRET_KEY deve ser definida em produção via VISIONMOTO_SECRET_KEY")
        
        # Verifica diretório de dados
        data_dir = Path(cls.DATABASE_PATH).parent
        if not data_dir.exists():
            try:
                data_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Não foi possível criar diretório de dados: {e}")
        
        if errors:
            import logging
            logger = logging.getLogger(__name__)
            for error in errors:
                logger.error(f"ERRO DE CONFIGURAÇÃO: {error}")
            return False
        
        return True
    
    @classmethod
    def display(cls) -> None:
        """Exibe configurações (sem dados sensíveis)"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Configurações do VisionMoto:")
        logger.info(f"  • API: {cls.API_HOST}:{cls.API_PORT}")
        logger.info(f"  • Debug: {cls.DEBUG}")
        logger.info(f"  • Database: {cls.DATABASE_PATH}")
        logger.info(f"  • Log Level: {cls.LOG_LEVEL}")
        logger.info(f"  • YOLO Model: {cls.YOLO_MODEL_PATH}")
        logger.info(f"  • Rate Limit: {cls.RATE_LIMIT_PER_MINUTE}/min")
        logger.info(f"  • Secret Key: {'Configurada' if cls.SECRET_KEY else 'Não configurada'}")


class DevelopmentConfig(Config):
    """Configuração para desenvolvimento"""
    DEBUG = True
    LOG_LEVEL = "DEBUG"


class ProductionConfig(Config):
    """Configuração para produção"""
    DEBUG = False
    LOG_LEVEL = "WARNING"
    RATE_LIMIT_ENABLED = True


class TestingConfig(Config):
    """Configuração para testes"""
    DEBUG = True
    DATABASE_PATH = ":memory:"
    LOG_LEVEL = "ERROR"
    RATE_LIMIT_ENABLED = False


def get_config() -> Config:
    """Retorna configuração baseada no ambiente"""
    env = os.getenv("VISIONMOTO_ENV", "development").lower()
    
    config_map = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }
    
    config_class = config_map.get(env, DevelopmentConfig)
    return config_class()
