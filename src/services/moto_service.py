#!/usr/bin/env python3
"""
Serviço de Motos - Lógica de negócio centralizada
Remove duplicação e separa responsabilidades
"""

import sqlite3
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.utils.logger import get_logger
from src.schemas import MotoResponse, MotoStatus

logger = get_logger(__name__)


class MotoService:
    """Serviço para operações de motos"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        """Retorna conexão com banco"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_all_motos(
        self, 
        status_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Lista todas as motos com filtro opcional
        
        Args:
            status_filter: Lista de status para filtrar
        
        Returns:
            Lista de motos
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if status_filter:
                placeholders = ','.join('?' * len(status_filter))
                query = f"""
                    SELECT 
                        id, modelo, placa, status, bateria, zona, 
                        endereco, setor, andar, vaga, descricao_localizacao,
                        ultima_atualizacao, localizacao_x, localizacao_y
                    FROM motos_patio 
                    WHERE status IN ({placeholders})
                    ORDER BY status, bateria DESC
                """
                cursor.execute(query, status_filter)
            else:
                cursor.execute("""
                    SELECT 
                        id, modelo, placa, status, bateria, zona, 
                        endereco, setor, andar, vaga, descricao_localizacao,
                        ultima_atualizacao, localizacao_x, localizacao_y
                    FROM motos_patio 
                    ORDER BY status, bateria DESC
                """)
            
            motos = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            logger.info(
                "Motos listadas com sucesso",
                total=len(motos),
                status_filter=status_filter
            )
            
            return motos
            
        except sqlite3.Error as e:
            logger.error("Erro ao listar motos", error=e, db_path=self.db_path)
            raise
    
    def find_by_placa(self, placa: str) -> Optional[Dict[str, Any]]:
        """
        Busca moto por placa (CÓDIGO ÚNICO - SEM DUPLICAÇÃO)
        
        Args:
            placa: Placa da moto
        
        Returns:
            Dados da moto ou None se não encontrada
        """
        try:
            placa = placa.strip().upper()
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    id, modelo, placa, status, bateria, 
                    localizacao_x, localizacao_y, zona,
                    endereco, setor, andar, vaga, descricao_localizacao,
                    ultima_atualizacao, em_uso_por
                FROM motos_patio 
                WHERE UPPER(placa) = ?
            """, (placa,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                logger.warning("Moto não encontrada", placa=placa)
                return None
            
            moto = dict(row)
            
            # Adiciona informações de localização formatadas
            moto["localizacao_completa"] = self._format_location(moto)
            moto["instrucoes_localizacao"] = self._format_instructions(moto)
            
            logger.info("Moto encontrada por placa", placa=placa, moto_id=moto["id"])
            
            return moto
            
        except sqlite3.Error as e:
            logger.error("Erro ao buscar moto por placa", error=e, placa=placa)
            raise
    
    def _format_location(self, moto: Dict[str, Any]) -> Dict[str, Any]:
        """Formata informações de localização"""
        return {
            "endereco": moto.get("endereco", ""),
            "setor": moto.get("setor", ""),
            "andar": moto.get("andar", 1),
            "vaga": moto.get("vaga", ""),
            "descricao": moto.get("descricao_localizacao", ""),
            "coordenadas": {
                "x": moto.get("localizacao_x", 0),
                "y": moto.get("localizacao_y", 0)
            },
            "zona": moto.get("zona", "")
        }
    
    def _format_instructions(self, moto: Dict[str, Any]) -> str:
        """Formata instruções de como chegar"""
        placa = moto.get("placa", "")
        endereco = moto.get("endereco", "")
        setor = moto.get("setor", "")
        andar = moto.get("andar", 1)
        vaga = moto.get("vaga", "")
        descricao = moto.get("descricao_localizacao", "")
        
        instrucoes = f"Para encontrar a moto {placa}:\n"
        instrucoes += f"Endereço: {endereco}\n"
        instrucoes += f"{setor} - {andar}º andar\n"
        instrucoes += f"Vaga: {vaga}\n"
        instrucoes += f"{descricao}"
        
        return instrucoes
    
    def reservar_moto(
        self, 
        moto_id: str, 
        usuario_id: str
    ) -> bool:
        """
        Reserva uma moto para um usuário
        
        Args:
            moto_id: ID da moto
            usuario_id: ID do usuário
        
        Returns:
            True se reservada com sucesso
        
        Raises:
            ValueError: Se moto não disponível
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Atualiza status da moto
            cursor.execute("""
                UPDATE motos_patio 
                SET status = 'em_uso', 
                    em_uso_por = ?, 
                    ultima_atualizacao = ?
                WHERE id = ? AND status = 'disponivel'
            """, (usuario_id, datetime.now().isoformat(), moto_id))
            
            if cursor.rowcount == 0:
                conn.close()
                logger.warning(
                    "Tentativa de reservar moto indisponível",
                    moto_id=moto_id,
                    usuario_id=usuario_id
                )
                raise ValueError("Moto não disponível para reserva")
            
            # Registra histórico
            import uuid
            cursor.execute("""
                INSERT INTO historico_uso (id, moto_id, usuario_id, inicio_uso)
                VALUES (?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                moto_id,
                usuario_id,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(
                "Moto reservada com sucesso",
                moto_id=moto_id,
                usuario_id=usuario_id
            )
            
            return True
            
        except sqlite3.Error as e:
            logger.error(
                "Erro ao reservar moto",
                error=e,
                moto_id=moto_id,
                usuario_id=usuario_id
            )
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Retorna estatísticas das motos
        
        Returns:
            Dicionário com estatísticas
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Query otimizada com agregação
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'disponivel' THEN 1 ELSE 0 END) as disponiveis,
                    SUM(CASE WHEN status = 'em_uso' THEN 1 ELSE 0 END) as em_uso,
                    SUM(CASE WHEN status = 'manutencao' THEN 1 ELSE 0 END) as manutencao,
                    AVG(bateria) as bateria_media,
                    MIN(bateria) as bateria_minima,
                    MAX(bateria) as bateria_maxima
                FROM motos_patio
            """)
            
            row = cursor.fetchone()
            conn.close()
            
            stats = {
                "total": row["total"],
                "disponiveis": row["disponiveis"],
                "em_uso": row["em_uso"],
                "manutencao": row["manutencao"],
                "bateria_media": round(row["bateria_media"] or 0, 2),
                "bateria_minima": row["bateria_minima"] or 0,
                "bateria_maxima": row["bateria_maxima"] or 0,
            }
            
            logger.debug("Estatísticas calculadas", **stats)
            
            return stats
            
        except sqlite3.Error as e:
            logger.error("Erro ao calcular estatísticas", error=e)
            raise
