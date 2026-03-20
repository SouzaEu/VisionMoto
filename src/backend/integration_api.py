#!/usr/bin/env python3
"""
Integration API - API REST refatorada para integração com outras disciplinas
Versão 2.1 - Refatorada com serviços, rate limiting e tratamento de erros específico
Desenvolvido para o 4º Sprint - Challenge 2025
"""

import os
import sqlite3
import json
import logging
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Optional

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pydantic import ValidationError

# Importa constantes
from src.constants import (
    DEFAULT_API_PORT,
    DEFAULT_DB_PATH,
    JWT_EXPIRATION_HOURS,
    JWT_ALGORITHM,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE_SIZE,
    VALID_ALERT_STATUSES,
    ALERT_STATUS_OPEN,
    ALERT_STATUS_RESOLVED,
    RATE_LIMIT_PER_MINUTE,
    RATE_LIMIT_PER_HOUR,
    DEFAULT_CORS_ORIGINS,
    ALLOWED_TABLES
)

# Importa serviços
from src.services.moto_service import MotoService
from src.services.alert_service import AlertService
from src.services.auth_service import AuthService

# Importa formatadores
from src.formatters.mobile_formatter import MobileFormatter
from src.formatters.java_formatter import JavaFormatter
from src.formatters.dotnet_formatter import DotNetFormatter

# Importa modelos
from src.models.user import UserLogin


# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VisionMotoIntegrationAPI:
    """API REST refatorada para integração multi-disciplinar
    
    Usa serviços centralizados, formatadores específicos por cliente,
    rate limiting, e tratamento de erros específico.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.app = Flask(__name__, static_folder="static")
        
        # SECRET_KEY obrigatória em produção
        secret_key = os.environ.get("SECRET_KEY")
        debug_mode = os.environ.get("FLASK_ENV", "development") == "development"
        
        if not secret_key:
            if not debug_mode:
                raise RuntimeError(
                    "SECRET_KEY environment variable must be set in production! "
                    "Set it in your .env file or environment."
                )
            # Apenas em desenvolvimento, usa chave fixa para não invalidar tokens
            secret_key = "dev-secret-key-change-in-production-12345678"
            logger.warning(
                "Using development SECRET_KEY. Set SECRET_KEY env var for production!"
            )
        
        self.app.config["SECRET_KEY"] = secret_key
        self.db_path = db_path or os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH)

        # CORS configurado com origens específicas
        allowed_origins = os.environ.get(
            "CORS_ORIGINS",
            DEFAULT_CORS_ORIGINS if debug_mode else ""
        ).split(",")
        
        CORS(self.app, resources={
            r"/api/*": {
                "origins": allowed_origins if allowed_origins != [''] else "*",
                "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "Idempotency-Key"],
                "expose_headers": ["Content-Type", "Authorization"],
                "supports_credentials": True,
                "max_age": 3600
            }
        })

        # Rate Limiting
        self.limiter = Limiter(
            app=self.app,
            key_func=get_remote_address,
            default_limits=[f"{RATE_LIMIT_PER_MINUTE}/minute", f"{RATE_LIMIT_PER_HOUR}/hour"],
            storage_uri="memory://"
        )

        # Inicializa serviços
        self.moto_service = MotoService(self.db_path)
        self.alert_service = AlertService(self.db_path)
        self.auth_service = AuthService(self.db_path, secret_key)

        self._init_database()
        self._setup_routes()

    @contextmanager
    def get_db_connection(self):
        """Context manager para conexões de banco de dados"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def _validate_table_name(self, table_name: str) -> bool:
        """Valida nome de tabela para prevenir SQL injection"""
        return table_name in ALLOWED_TABLES and table_name.replace("_", "").isalnum()
    
    def _init_database(self):
        """Inicializa banco de dados com tabelas para integração"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()

            # Tabela de detecções (existente)
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

            # Tabela de usuários (para mobile app)
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

        # Popula dados iniciais se necessário
        self._populate_initial_data()

    def _populate_initial_data(self):
        """Popula dados iniciais para demonstração"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()

            # Verifica se já existem motos
            try:
                cursor.execute("SELECT COUNT(*) FROM motos_patio")
                if cursor.fetchone()[0] == 0:
                    # Adiciona motos de exemplo com localização detalhada
                    motos_exemplo = [
                        (
                            "MOTO001",
                            "Honda CG 160",
                            "ABC-1234",
                            "disponivel",
                            95,
                            10.5,
                            20.3,
                            "A1",
                            "Rua das Palmeiras, 123 - Setor A",
                            "Setor A",
                            1,
                            "A1-001",
                            "Próximo à entrada principal, primeira fileira",
                        ),
                    (
                        "MOTO002",
                        "Yamaha Factor",
                        "DEF-5678",
                        "em_uso",
                        78,
                        15.2,
                        25.1,
                        "A2",
                        "Rua das Palmeiras, 123 - Setor A",
                        "Setor A",
                        1,
                        "A2-005",
                        "Segunda fileira, próximo ao banheiro",
                    ),
                    (
                        "MOTO003",
                        "Honda Biz",
                        "GHI-9012",
                        "disponivel",
                        100,
                        8.7,
                        18.9,
                        "A1",
                        "Rua das Palmeiras, 123 - Setor A",
                        "Setor A",
                        1,
                        "A1-003",
                        "Primeira fileira, vaga coberta",
                    ),
                    (
                        "MOTO004",
                        "Yamaha Neo",
                        "JKL-3456",
                        "manutencao",
                        45,
                        12.1,
                        22.4,
                        "B1",
                        "Av. Industrial, 456 - Setor B",
                        "Setor B",
                        2,
                        "B1-010",
                        "Segundo andar, área de manutenção",
                    ),
                    (
                        "MOTO005",
                        "Honda PCX",
                        "MNO-7890",
                        "disponivel",
                        88,
                        20.3,
                        30.2,
                        "B2",
                        "Av. Industrial, 456 - Setor B",
                        "Setor B",
                        1,
                        "B2-007",
                        "Térreo, próximo ao elevador",
                    ),
                    (
                        "MOTO006",
                        "Suzuki Burgman",
                        "PQR-1357",
                        "em_uso",
                        92,
                        25.1,
                        35.8,
                        "C1",
                        "Rua dos Motociclistas, 789 - Setor C",
                        "Setor C",
                        1,
                        "C1-015",
                        "Área VIP, vaga premium",
                    ),
                ]

                    for moto in motos_exemplo:
                        cursor.execute("""
                            INSERT INTO motos_patio 
                            (id, modelo, placa, status, bateria, localizacao_x, localizacao_y, zona, endereco, setor, andar, vaga, descricao_localizacao, ultima_atualizacao)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (*moto, datetime.now(timezone.utc).isoformat()))

                # Adiciona dispositivos IoT de exemplo
                cursor.execute("SELECT COUNT(*) FROM dispositivos_iot")
                if cursor.fetchone()[0] == 0:
                    dispositivos = [
                        ("SENSOR001", "Sensor de Movimento A1", "sensor_movimento", "online", "Zona A1"),
                        ("SENSOR002", "Sensor de Movimento A2", "sensor_movimento", "online", "Zona A2"),
                        ("SENSOR003", "Sensor de Movimento B1", "sensor_movimento", "offline", "Zona B1"),
                        ("CAMERA001", "Câmera Principal", "camera", "online", "Entrada Principal"),
                        ("LOCK001", "Trava Inteligente A1", "atuador_trava", "online", "Zona A1"),
                        ("ALARM001", "Sistema de Alarme", "atuador_alarme", "online", "Central"),
                    ]

                    for dispositivo in dispositivos:
                        cursor.execute("""
                            INSERT INTO dispositivos_iot 
                            (id, nome, tipo, status, localizacao, ultima_comunicacao)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (*dispositivo, datetime.now(timezone.utc).isoformat()))
            except sqlite3.Error as e:
                # Se houver erro (ex: tabelas não existem), ignora
                logger.warning(f"Error populating initial data: {e}")

    def _setup_routes(self):
        """Configura todas as rotas da API"""

        # Rotas básicas
        @self.app.route("/")
        def index():
            return jsonify({
                "service": "VisionMoto Integration API",
                "version": "2.1-refactored",
                "status": "running",
                    "endpoints": {
                        "mobile": "/api/mobile/*",
                        "java": "/api/java/*",
                        "dotnet": "/api/dotnet/*",
                        "database": "/api/database/*",
                        "iot": "/api/iot/*",
                        "dashboard": "/dashboard",
                        "busca_por_placa": {
                            "mobile": "/api/mobile/motos/buscar/<placa>",
                            "java": "/api/java/motos/buscar/<placa>",
                            "dotnet": "/api/dotnet/Motorcycles/FindByPlate/<placa>"
                        }
                    },
                }
            )

        @self.app.route("/health")
        def health():
            return jsonify(
                {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
            )

        # ==================== MOBILE ENDPOINTS ====================
        @self.app.route("/api/mobile/auth/login", methods=["POST"])
        @self.limiter.limit("10/minute")
        def mobile_login():
            """Endpoint de login para mobile - USA AuthService"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"error": "Invalid JSON payload"}), 400
                
                # Validação com Pydantic
                try:
                    login_data = UserLogin(**data)
                except ValidationError as e:
                    logger.warning(f"Validation error in login: {e}")
                    return jsonify({"error": "Invalid email or password format"}), 400
                
                # USA O SERVIÇO DE AUTENTICAÇÃO
                result = self.auth_service.authenticate(login_data.email, login_data.senha)
                
                if not result:
                    return jsonify({"error": "Invalid credentials"}), 401
                
                logger.info(f"Login successful for email: {login_data.email}")
                return jsonify(result), 200
                
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in login request")
                return jsonify({"error": "Invalid JSON format"}), 400
            except ValueError as e:
                logger.warning(f"Login validation error: {e}")
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                logger.error(f"Unexpected login error: {e}", exc_info=True)
                return jsonify({"error": "Authentication failed. Please try again."}), 500

        @self.app.route("/api/mobile/motos", methods=["GET"])
        def mobile_motos():
            """Lista motos disponíveis para o app mobile - USA MotoService"""
            try:
                motos = self.moto_service.get_all_motos(status_filter=['disponivel', 'em_uso'])
                return jsonify(MobileFormatter.format_moto_list(motos)), 200
            except sqlite3.Error as e:
                logger.error(f"Database error listing motos: {e}", exc_info=True)
                return jsonify({"error": "Database error"}), 503
            except Exception as e:
                logger.error(f"Unexpected error listing motos: {e}", exc_info=True)
                return jsonify({"error": "Failed to retrieve motorcycles"}), 500

        @self.app.route("/api/mobile/motos/buscar/<placa>", methods=["GET"])
        def mobile_buscar_moto_por_placa(placa):
            """Busca moto por placa - USA MotoService (SEM DUPLICAÇÃO)"""
            try:
                moto = self.moto_service.find_by_placa(placa)
                
                if not moto:
                    return jsonify({"error": f"Moto com placa {placa} não encontrada"}), 404
                
                return jsonify(MobileFormatter.format_moto_detail(moto)), 200
            except sqlite3.Error as e:
                logger.error(f"Database error finding moto: {e}", exc_info=True)
                return jsonify({"error": "Database error"}), 503
            except Exception as e:
                logger.error(f"Unexpected error finding moto: {e}", exc_info=True)
                return jsonify({"error": "Failed to find motorcycle"}), 500

        @self.app.route("/api/mobile/motos/<moto_id>/reservar", methods=["POST"])
        def mobile_reservar_moto(moto_id):
            """Reserva uma moto - USA MotoService"""
            try:
                data = request.get_json() or {}
                usuario_id = data.get("usuario_id")
                
                if not usuario_id:
                    return jsonify({"error": "usuario_id é obrigatório"}), 400
                
                self.moto_service.reservar_moto(moto_id, usuario_id)
                
                return jsonify({
                    "message": "Moto reservada com sucesso",
                    "moto_id": moto_id
                }), 200
            except ValueError as e:
                logger.warning(f"Reservation validation error: {e}")
                return jsonify({"error": str(e)}), 400
            except sqlite3.IntegrityError as e:
                logger.error(f"Database integrity error: {e}")
                return jsonify({"error": "Database constraint violation"}), 409
            except sqlite3.Error as e:
                logger.error(f"Database error reserving moto: {e}", exc_info=True)
                return jsonify({"error": "Database error"}), 503
            except Exception as e:
                logger.error(f"Unexpected error reserving moto: {e}", exc_info=True)
                return jsonify({"error": "Failed to reserve motorcycle"}), 500

        # ==================== JAVA ENDPOINTS ====================
        @self.app.route("/api/java/motos/status", methods=["GET"])
        def java_motos_status():
            """Endpoint para integração com Spring Boot - USA MotoService"""
            try:
                motos = self.moto_service.get_all_motos()
                return jsonify(JavaFormatter.format_moto_list(motos)), 200
            except sqlite3.Error as e:
                logger.error(f"Database error: {e}", exc_info=True)
                return jsonify({"success": False, "error": "Database error"}), 503
            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                return jsonify({"success": False, "error": "Internal server error"}), 500

        @self.app.route("/api/java/motos/buscar/<placa>", methods=["GET"])
        def java_buscar_moto_por_placa(placa):
            """Busca moto por placa - USA MotoService (SEM DUPLICAÇÃO)"""
            try:
                moto = self.moto_service.find_by_placa(placa)
                
                if not moto:
                    return jsonify({
                        "success": False,
                        "error": f"Moto com placa {placa} não encontrada",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }), 404
                
                return jsonify(JavaFormatter.format_moto_detail(moto)), 200
            except sqlite3.Error as e:
                logger.error(f"Database error: {e}", exc_info=True)
                return jsonify({"success": False, "error": "Database error"}), 503
            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                return jsonify({"success": False, "error": "Internal server error"}), 500

        @self.app.route("/api/java/alertas", methods=["GET", "POST"])
        def java_alertas():
            """Gerenciamento de alertas para Java"""
            if request.method == "GET":
                try:
                    conn = sqlite3.connect(self.db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    cursor.execute(
                        """
                        SELECT * FROM alertas 
                        WHERE ativo = 1 
                        ORDER BY criado_em DESC
                    """
                    )

                    alertas = [dict(row) for row in cursor.fetchall()]
                    conn.close()

                    return jsonify({"success": True, "alertas": alertas})

                except Exception as e:
                    return jsonify({"success": False, "error": str(e)}), 500

            elif request.method == "POST":
                try:
                    data = request.get_json()

                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()

                    cursor.execute(
                        """
                        INSERT INTO alertas (id, tipo, severidade, titulo, descricao, moto_id, zona, criado_em)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            str(uuid.uuid4()),
                            data.get("tipo", "info"),
                            data.get("severidade", "info"),
                            data.get("titulo", ""),
                            data.get("descricao", ""),
                            data.get("motoId"),
                            data.get("zona"),
                            datetime.now().isoformat(),
                        ),
                    )

                    conn.commit()
                    conn.close()

                    return jsonify({"success": True, "message": "Alerta criado"})

                except Exception as e:
                    return jsonify({"success": False, "error": str(e)}), 500

        # .NET endpoints
        @self.app.route("/api/dotnet/Dashboard/GetMotorcycleData", methods=["GET"])
        def dotnet_motorcycle_data():
            """Endpoint para integração com .NET (formato C#)"""
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT 
                        id as Id,
                        modelo as Model,
                        placa as LicensePlate,
                        status as Status,
                        bateria as BatteryLevel,
                        localizacao_x as LocationX,
                        localizacao_y as LocationY,
                        zona as Zone,
                        endereco as Address,
                        setor as Sector,
                        andar as Floor,
                        vaga as ParkingSpot,
                        descricao_localizacao as LocationDescription,
                        ultima_atualizacao as LastUpdate
                    FROM motos_patio
                """
                )

                motorcycles = [dict(row) for row in cursor.fetchall()]
                conn.close()

                # Formato .NET-friendly
                response = {
                    "IsSuccess": True,
                    "Data": {
                        "Motorcycles": motorcycles,
                        "Summary": {
                            "TotalCount": len(motorcycles),
                            "AvailableCount": len(
                                [m for m in motorcycles if m["Status"] == "disponivel"]
                            ),
                            "InUseCount": len(
                                [m for m in motorcycles if m["Status"] == "em_uso"]
                            ),
                            "MaintenanceCount": len(
                                [m for m in motorcycles if m["Status"] == "manutencao"]
                            ),
                        },
                    },
                    "Message": "Data retrieved successfully",
                    "Timestamp": datetime.now().isoformat(),
                }

                return jsonify(response)

            except Exception as e:
                return (
                    jsonify(
                        {
                            "IsSuccess": False,
                            "Error": str(e),
                            "Message": "Failed to retrieve motorcycle data",
                        }
                    ),
                    500,
                )

        @self.app.route("/api/dotnet/Motorcycles/FindByPlate/<placa>", methods=["GET"])
        def dotnet_buscar_moto_por_placa(placa):
            """Busca moto específica por placa - Endpoint .NET"""
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT 
                        id as Id,
                        modelo as Model,
                        placa as LicensePlate,
                        status as Status,
                        bateria as BatteryLevel,
                        localizacao_x as LocationX,
                        localizacao_y as LocationY,
                        zona as Zone,
                        endereco as Address,
                        setor as Sector,
                        andar as Floor,
                        vaga as ParkingSpot,
                        descricao_localizacao as LocationDescription,
                        ultima_atualizacao as LastUpdate,
                        em_uso_por as InUseBy
                    FROM motos_patio 
                    WHERE placa = ? COLLATE NOCASE
                """,
                    (placa,),
                )

                motorcycle = cursor.fetchone()
                conn.close()

                if not motorcycle:
                    return jsonify({
                        "IsSuccess": False,
                        "Error": f"Motorcycle with plate {placa} not found",
                        "Message": "Motorcycle not found in database",
                        "Timestamp": datetime.now().isoformat()
                    }), 404

                motorcycle_dict = dict(motorcycle)
                
                # Adiciona localização formatada para .NET
                motorcycle_dict["LocationDetails"] = {
                    "Address": motorcycle_dict["Address"],
                    "Sector": motorcycle_dict["Sector"],
                    "Floor": motorcycle_dict["Floor"],
                    "ParkingSpot": motorcycle_dict["ParkingSpot"],
                    "Description": motorcycle_dict["LocationDescription"],
                    "Coordinates": {
                        "X": motorcycle_dict["LocationX"],
                        "Y": motorcycle_dict["LocationY"]
                    },
                    "Zone": motorcycle_dict["Zone"]
                }

                # Instruções de localização
                motorcycle_dict["LocationInstructions"] = [
                    f"Address: {motorcycle_dict['Address']}",
                    f"Sector: {motorcycle_dict['Sector']} - Floor {motorcycle_dict['Floor']}",
                    f"Parking Spot: {motorcycle_dict['ParkingSpot']}",
                    f"Reference: {motorcycle_dict['LocationDescription']}"
                ]

                return jsonify({
                    "IsSuccess": True,
                    "Data": {
                        "Motorcycle": motorcycle_dict,
                        "Found": True
                    },
                    "Message": "Motorcycle found successfully",
                    "Timestamp": datetime.now().isoformat()
                })

            except Exception as e:
                return jsonify({
                    "IsSuccess": False,
                    "Error": str(e),
                    "Message": "Failed to find motorcycle"
                }), 500

        @self.app.route("/api/dotnet/Reports/GenerateUsageReport", methods=["POST"])
        def dotnet_usage_report():
            """Gera relatório de uso para .NET"""
            try:
                data = request.get_json()
                start_date = data.get(
                    "StartDate", (datetime.now() - timedelta(days=7)).isoformat()
                )
                end_date = data.get("EndDate", datetime.now().isoformat())

                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT 
                        h.moto_id as MotorcycleId,
                        m.modelo as Model,
                        COUNT(*) as UsageCount,
                        AVG(h.tempo_uso) as AverageUsageTime,
                        SUM(h.distancia_percorrida) as TotalDistance
                    FROM historico_uso h
                    JOIN motos_patio m ON h.moto_id = m.id
                    WHERE h.inicio_uso BETWEEN ? AND ?
                    GROUP BY h.moto_id, m.modelo
                """,
                    (start_date, end_date),
                )

                report_data = [dict(row) for row in cursor.fetchall()]
                conn.close()

                return jsonify(
                    {
                        "IsSuccess": True,
                        "ReportData": report_data,
                        "GeneratedAt": datetime.now().isoformat(),
                        "Period": {"StartDate": start_date, "EndDate": end_date},
                    }
                )

            except Exception as e:
                return jsonify({"IsSuccess": False, "Error": str(e)}), 500

        # Database endpoints
        @self.app.route("/api/database/backup", methods=["POST"])
        def database_backup():
            """Cria backup do banco de dados"""
            try:
                backup_path = (
                    f"backup_visionmoto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                )

                # Copia banco atual
                import shutil

                shutil.copy2(self.db_path, backup_path)

                return jsonify(
                    {
                        "success": True,
                        "backup_file": backup_path,
                        "created_at": datetime.now().isoformat(),
                    }
                )

            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/database/analytics", methods=["GET"])
        def database_analytics():
            """Retorna analytics do banco de dados"""
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Estatísticas gerais
                stats = {}

                # Contagem de tabelas com validação
                ALLOWED_TABLES = [
                    "motos_patio",
                    "usuarios",
                    "alertas",
                    "dispositivos_iot",
                    "historico_uso",
                    "detections",
                ]
                for table in ALLOWED_TABLES:
                    # Valida nome da tabela antes de usar em query
                    if not self._validate_table_name(table):
                        logger.error(f"Invalid table name attempted: {table}")
                        continue
                    
                    # Agora é seguro usar f-string pois validamos
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[f"{table}_count"] = cursor.fetchone()[0]

                # Estatísticas de uso
                cursor.execute(
                    """
                    SELECT 
                        COUNT(*) as total_usos,
                        AVG(tempo_uso) as tempo_medio,
                        SUM(distancia_percorrida) as distancia_total
                    FROM historico_uso
                    WHERE inicio_uso >= date('now', '-30 days')
                """
                )

                uso_stats = cursor.fetchone()
                stats.update(
                    {
                        "usos_ultimo_mes": uso_stats[0],
                        "tempo_medio_uso": uso_stats[1] or 0,
                        "distancia_total_mes": uso_stats[2] or 0,
                    }
                )

                conn.close()

                return jsonify(
                    {
                        "success": True,
                        "analytics": stats,
                        "generated_at": datetime.now().isoformat(),
                    }
                )

            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        # IoT endpoints
        @self.app.route("/api/iot/eventos", methods=["POST"])
        def iot_eventos():
            """Recebe eventos IoT e cria/atualiza alerta com idempotência"""
            try:
                data = request.get_json() or {}
                idem = request.headers.get("Idempotency-Key") or data.get("id")
                if not idem:
                    return jsonify({"error": "Idempotency-Key obrigatório"}), 400

                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Idempotência: já existe?
                cursor.execute(
                    "SELECT alert_id FROM iot_eventos WHERE idempotency_key = ?",
                    (idem,),
                )
                row = cursor.fetchone()
                if row:
                    alert_id = row[0]
                    conn.close()
                    return (
                        jsonify({"alertId": alert_id, "status": "OPEN", "idempotent": True}),
                        200,
                    )

                # Cria alerta
                alert_id = f"ALR-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
                titulo = "Moto fora da vaga" if data.get("type") else "Alerta IoT"
                descricao = (
                    f"Dispositivo {data.get('deviceId','desconhecido')} detectou irregularidade"
                )

                cursor.execute(
                    """
                    INSERT INTO alertas (id, tipo, severidade, titulo, descricao, moto_id, zona, ativo, criado_em)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                    """,
                    (
                        alert_id,
                        data.get("type", "iot"),
                        "HIGH" if data.get("type") else "info",
                        titulo,
                        descricao,
                        None,
                        (data.get("metadata") or {}).get("slot"),
                        datetime.now().isoformat(),
                    ),
                )

                # Registra idempotência
                cursor.execute(
                    "INSERT INTO iot_eventos (idempotency_key, alert_id, created_at) VALUES (?, ?, ?)",
                    (idem, alert_id, datetime.now().isoformat()),
                )

                conn.commit()
                conn.close()

                return jsonify({"alertId": alert_id, "status": "OPEN"}), 201
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/iot/devices", methods=["GET"])
        def iot_devices():
            """Lista dispositivos IoT"""
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM dispositivos_iot ORDER BY nome")
                devices = [dict(row) for row in cursor.fetchall()]
                conn.close()

                return jsonify(
                    {
                        "devices": devices,
                        "total": len(devices),
                        "online": len([d for d in devices if d["status"] == "online"]),
                    }
                )

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/iot/devices/<device_id>/data", methods=["POST"])
        def iot_device_data(device_id):
            """Recebe dados de dispositivo IoT"""
            try:
                data = request.get_json()

                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Atualiza dados do dispositivo
                cursor.execute(
                    """
                    UPDATE dispositivos_iot 
                    SET dados_sensor = ?, ultima_comunicacao = ?, status = 'online'
                    WHERE id = ?
                """,
                    (json.dumps(data), datetime.now().isoformat(), device_id),
                )

                conn.commit()
                conn.close()

                return jsonify({"success": True, "message": "Dados recebidos"})

            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        # Mobile alert endpoints (consumidos pelo app)
        @self.app.route("/api/mobile/alertas", methods=["GET"])
        def mobile_alertas_list():
            try:
                status = request.args.get("status", "OPEN").upper()
                
                # Validação de paginação
                try:
                    limit = int(request.args.get("limit", 50))
                    offset = int(request.args.get("offset", 0))
                    
                    # Limita valores para prevenir DoS
                    limit = max(1, min(limit, 100))  # Entre 1 e 100
                    offset = max(0, offset)  # Mínimo 0
                except (ValueError, TypeError):
                    return jsonify({"error": "Invalid pagination parameters"}), 400
                
                # Valida status
                if status not in ["OPEN", "RESOLVED", "ALL"]:
                    return jsonify({"error": "Invalid status. Use OPEN, RESOLVED, or ALL"}), 400

                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                if status == "OPEN":
                    cursor.execute(
                        "SELECT * FROM alertas WHERE ativo = 1 ORDER BY criado_em DESC LIMIT ? OFFSET ?",
                        (limit, offset),
                    )
                elif status == "RESOLVED":
                    cursor.execute(
                        "SELECT * FROM alertas WHERE ativo = 0 ORDER BY resolvido_em DESC LIMIT ? OFFSET ?",
                        (limit, offset),
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM alertas ORDER BY criado_em DESC LIMIT ? OFFSET ?",
                        (limit, offset),
                    )

                items = []
                for row in cursor.fetchall():
                    d = dict(row)
                    items.append(
                        {
                            "id": d["id"],
                            "status": "OPEN" if d["ativo"] else "RESOLVED",
                            "title": d["titulo"],
                            "message": d.get("descricao"),
                            "severity": d.get("severidade", "info").upper(),
                            "deviceId": None,
                            "createdAt": d.get("criado_em"),
                            "location": {"lat": None, "lng": None},
                        }
                    )

                conn.close()
                return jsonify({"items": items, "total": len(items)})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/mobile/alertas/<alert_id>/resolver", methods=["PATCH"])
        def mobile_alertas_resolver(alert_id):
            try:
                data = request.get_json() or {}
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE alertas SET ativo = 0, resolvido_em = ?, resolvido_por = ?
                    WHERE id = ? AND ativo = 1
                    """,
                    (datetime.now().isoformat(), data.get("resolvedBy"), alert_id),
                )
                if cursor.rowcount == 0:
                    conn.close()
                    return jsonify({"error": "Alerta não encontrado ou já resolvido"}), 404
                conn.commit()
                conn.close()
                return jsonify({"id": alert_id, "status": "RESOLVED", "updatedAt": datetime.now().isoformat()})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/mobile/devices/register", methods=["POST"])
        def mobile_devices_register():
            try:
                data = request.get_json() or {}
                token = data.get("token")
                if not token:
                    return jsonify({"error": "token obrigatório"}), 400
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO push_devices (token, user_id, platform, created_at, last_seen)
                    VALUES (?, ?, ?, COALESCE((SELECT created_at FROM push_devices WHERE token = ?), ?), ?)
                    """,
                    (
                        token,
                        data.get("userId"),
                        data.get("platform", "android"),
                        token,
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()
                conn.close()
                return jsonify({"ok": True})
            except Exception as e:
                return jsonify({"ok": False, "error": str(e)}), 500

        # Dashboard
        @self.app.route("/dashboard")
        def dashboard():
            return send_from_directory(self.app.static_folder, "index.html")

        @self.app.route("/static/<path:path>")
        def send_static(path):
            return send_from_directory(self.app.static_folder, path)

    def run(self, host="0.0.0.0", port=5001, debug=False):
        """Executa a API de integração"""
        print(f"VisionMoto Integration API rodando em http://{host}:{port}")
        print(f"Mobile endpoints: http://{host}:{port}/api/mobile/*")
        print(f"Java endpoints: http://{host}:{port}/api/java/*")
        print(f".NET endpoints: http://{host}:{port}/api/dotnet/*")
        print(f"Database endpoints: http://{host}:{port}/api/database/*")
        print(f"IoT endpoints: http://{host}:{port}/api/iot/*")
        self.app.run(host=host, port=port, debug=debug)


def main():
    """Função principal"""
    api = VisionMotoIntegrationAPI()
    api.run()


if __name__ == "__main__":
    main()
