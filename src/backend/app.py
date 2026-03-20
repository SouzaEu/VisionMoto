#!/usr/bin/env python3
"""
VisionMoto API - Versão Refatorada e Profissional
Arquitetura modular com separação de responsabilidades
"""

import os
import logging
from contextlib import contextmanager
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

# Configuração de logging ANTES de importar qualquer coisa
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config=None):
    """
    Factory pattern para criar aplicação Flask
    
    Args:
        config: Dicionário de configuração (opcional)
    
    Returns:
        Aplicação Flask configurada
    """
    app = Flask(__name__, static_folder="static")
    
    # Configuração
    configure_app(app, config)
    
    # Inicialização
    init_database(app)
    
    # CORS
    configure_cors(app)
    
    # Registra blueprints
    register_blueprints(app)
    
    # Rotas básicas
    register_basic_routes(app)
    
    # Error handlers
    register_error_handlers(app)
    
    logger.info("VisionMoto API initialized successfully")
    
    return app


def configure_app(app, config=None):
    """Configura aplicação com variáveis de ambiente"""
    
    # SECRET_KEY obrigatória em produção
    secret_key = os.environ.get("SECRET_KEY") or os.environ.get("VISIONMOTO_SECRET_KEY")
    debug_mode = os.environ.get("FLASK_ENV", "development") == "development"
    
    if not secret_key:
        if not debug_mode:
            raise RuntimeError(
                "SECRET_KEY environment variable must be set in production! "
                "Set VISIONMOTO_SECRET_KEY or SECRET_KEY."
            )
        # Apenas em desenvolvimento, gera uma chave temporária
        import secrets
        secret_key = secrets.token_urlsafe(32)
        logger.warning("Using temporary SECRET_KEY for development. DO NOT use in production!")
    
    app.config["SECRET_KEY"] = secret_key
    app.config["DATABASE_PATH"] = os.environ.get(
        "DATABASE_PATH",
        "visionmoto_integration.db"
    )
    app.config["DEBUG"] = debug_mode
    
    # Configurações adicionais
    if config:
        app.config.update(config)
    
    logger.info(f"App configured - Debug: {debug_mode}, DB: {app.config['DATABASE_PATH']}")


def configure_cors(app):
    """Configura CORS com origens específicas"""
    debug_mode = app.config.get("DEBUG", False)
    
    allowed_origins = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:8080" if debug_mode else ""
    ).split(",")
    
    CORS(app, resources={
        r"/api/*": {
            "origins": allowed_origins if allowed_origins != [''] else "*",
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Idempotency-Key"],
            "expose_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
            "max_age": 3600
        }
    })
    
    logger.info(f"CORS configured - Origins: {allowed_origins}")


def init_database(app):
    """Inicializa banco de dados"""
    import sqlite3
    from datetime import datetime
    
    db_path = app.config["DATABASE_PATH"]
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Tabela de detecções
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                frame INTEGER,
                class_name TEXT,
                confidence REAL,
                bbox TEXT,
                fps REAL,
                location_x REAL DEFAULT 0,
                location_y REAL DEFAULT 0,
                zone_id TEXT DEFAULT 'A1'
            )
        """)
        
        # Tabela de motos no pátio
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS motos_patio (
                id TEXT PRIMARY KEY,
                modelo TEXT,
                placa TEXT,
                status TEXT DEFAULT 'disponivel',
                bateria INTEGER DEFAULT 100,
                localizacao_x REAL DEFAULT 0,
                localizacao_y REAL DEFAULT 0,
                zona TEXT DEFAULT 'A1',
                endereco TEXT DEFAULT '',
                setor TEXT DEFAULT '',
                andar INTEGER DEFAULT 1,
                vaga TEXT DEFAULT '',
                descricao_localizacao TEXT DEFAULT '',
                ultima_atualizacao TEXT,
                em_uso_por TEXT,
                manutencao_agendada TEXT
            )
        """)
        
        # Tabela de usuários
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                senha_hash TEXT NOT NULL,
                tipo TEXT DEFAULT 'usuario',
                criado_em TEXT,
                ultimo_acesso TEXT,
                ativo BOOLEAN DEFAULT 1
            )
        """)
        
        # Tabela de alertas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alertas (
                id TEXT PRIMARY KEY,
                tipo TEXT NOT NULL,
                severidade TEXT DEFAULT 'info',
                titulo TEXT NOT NULL,
                descricao TEXT,
                moto_id TEXT,
                zona TEXT,
                ativo BOOLEAN DEFAULT 1,
                criado_em TEXT,
                resolvido_em TEXT,
                resolvido_por TEXT
            )
        """)
        
        # Tabela para idempotência de eventos IoT
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS iot_eventos (
                idempotency_key TEXT PRIMARY KEY,
                alert_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Tabela para tokens de push (mobile)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS push_devices (
                token TEXT PRIMARY KEY,
                user_id TEXT,
                platform TEXT,
                created_at TEXT NOT NULL,
                last_seen TEXT
            )
        """)
        
        # Tabela de dispositivos IoT
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dispositivos_iot (
                id TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                tipo TEXT NOT NULL,
                status TEXT DEFAULT 'online',
                localizacao TEXT,
                ultima_comunicacao TEXT,
                dados_sensor TEXT,
                configuracao TEXT
            )
        """)
        
        # Tabela de histórico de uso
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_uso (
                id TEXT PRIMARY KEY,
                moto_id TEXT NOT NULL,
                usuario_id TEXT,
                inicio_uso TEXT,
                fim_uso TEXT,
                localizacao_inicial TEXT,
                localizacao_final TEXT,
                distancia_percorrida REAL DEFAULT 0,
                tempo_uso INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
        
        # Popula dados iniciais
        populate_initial_data(db_path)
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)
        raise


def populate_initial_data(db_path):
    """Popula dados iniciais para demonstração"""
    import sqlite3
    from datetime import datetime
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Verifica se já existem motos
        cursor.execute("SELECT COUNT(*) FROM motos_patio")
        if cursor.fetchone()[0] == 0:
            # Adiciona motos de exemplo
            motos_exemplo = [
                ("MOTO001", "Honda CG 160", "ABC-1234", "disponivel", 95, 10.5, 20.3, "A1",
                 "Rua das Palmeiras, 123 - Setor A", "Setor A", 1, "A1-001",
                 "Próximo à entrada principal, primeira fileira"),
                ("MOTO002", "Yamaha Factor", "DEF-5678", "em_uso", 78, 15.2, 25.1, "A2",
                 "Rua das Palmeiras, 123 - Setor A", "Setor A", 1, "A2-005",
                 "Segunda fileira, próximo ao banheiro"),
                ("MOTO003", "Honda Biz", "GHI-9012", "disponivel", 100, 8.7, 18.9, "A1",
                 "Rua das Palmeiras, 123 - Setor A", "Setor A", 1, "A1-003",
                 "Primeira fileira, vaga coberta"),
            ]
            
            for moto in motos_exemplo:
                cursor.execute("""
                    INSERT INTO motos_patio 
                    (id, modelo, placa, status, bateria, localizacao_x, localizacao_y, zona,
                     endereco, setor, andar, vaga, descricao_localizacao, ultima_atualizacao)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (*moto, datetime.now().isoformat()))
            
            logger.info("Initial motorcycle data populated")
        
        # Adiciona dispositivos IoT de exemplo
        cursor.execute("SELECT COUNT(*) FROM dispositivos_iot")
        if cursor.fetchone()[0] == 0:
            dispositivos = [
                ("SENSOR001", "Sensor de Movimento A1", "sensor_movimento", "online", "Zona A1"),
                ("CAMERA001", "Câmera Principal", "camera", "online", "Entrada Principal"),
            ]
            
            for dispositivo in dispositivos:
                cursor.execute("""
                    INSERT INTO dispositivos_iot 
                    (id, nome, tipo, status, localizacao, ultima_comunicacao)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (*dispositivo, datetime.now().isoformat()))
            
            logger.info("Initial IoT device data populated")
        
        conn.commit()
        
    except Exception as e:
        logger.error(f"Error populating initial data: {e}", exc_info=True)
    finally:
        conn.close()


def register_blueprints(app):
    """Registra todos os blueprints"""
    from src.routes import mobile_bp, java_bp, dotnet_bp, iot_bp, database_bp
    
    app.register_blueprint(mobile_bp)
    app.register_blueprint(java_bp)
    app.register_blueprint(dotnet_bp)
    app.register_blueprint(iot_bp)
    app.register_blueprint(database_bp)
    
    logger.info("All blueprints registered")


def register_basic_routes(app):
    """Registra rotas básicas"""
    
    @app.route("/")
    def index():
        return jsonify({
            "service": "VisionMoto Integration API",
            "version": "3.0",
            "status": "running",
            "endpoints": {
                "mobile": "/api/mobile/*",
                "java": "/api/java/*",
                "dotnet": "/api/dotnet/*",
                "database": "/api/database/*",
                "iot": "/api/iot/*",
                "dashboard": "/dashboard",
                "health": "/health"
            }
        })
    
    @app.route("/health")
    def health():
        from datetime import datetime, timezone
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    @app.route("/dashboard")
    def dashboard():
        return send_from_directory(app.static_folder, "index.html")
    
    @app.route("/static/<path:path>")
    def send_static(path):
        return send_from_directory(app.static_folder, path)


def register_error_handlers(app):
    """Registra handlers de erro"""
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Resource not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred"}), 500


# Instância global da aplicação
app = create_app()


def main():
    """Função principal para executar a API"""
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "5001"))
    debug = os.environ.get("FLASK_ENV", "development") == "development"
    
    logger.info(f"VisionMoto Integration API starting on http://{host}:{port}")
    logger.info(f"Mobile endpoints: http://{host}:{port}/api/mobile/*")
    logger.info(f"Java endpoints: http://{host}:{port}/api/java/*")
    logger.info(f".NET endpoints: http://{host}:{port}/api/dotnet/*")
    logger.info(f"Database endpoints: http://{host}:{port}/api/database/*")
    logger.info(f"IoT endpoints: http://{host}:{port}/api/iot/*")
    
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
