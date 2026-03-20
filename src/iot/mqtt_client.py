#!/usr/bin/env python3
"""
MQTT Client - VisionMoto
Cliente MQTT para comunicação IoT avançada
"""

import json
import time
import threading
from datetime import datetime
from typing import Dict, Callable, Optional
import paho.mqtt.client as mqtt
import requests


class MQTTIoTClient:
    """Cliente MQTT para comunicação IoT"""

    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        api_url: str = "http://localhost:5000",
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.api_url = api_url
        self.client = mqtt.Client()
        self.connected = False

        # Topics MQTT
        self.topics = {
            "sensors": "visionmoto/sensors/+/data",
            "actuators": "visionmoto/actuators/+/data",
            "alerts": "visionmoto/alerts",
            "status": "visionmoto/status",
        }

        # Configurar callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        """Callback de conexão MQTT"""
        if rc == 0:
            self.connected = True
            print("Conectado ao broker MQTT")

            # Subscrever aos tópicos
            for topic_name, topic in self.topics.items():
                client.subscribe(topic)
                print(f"Subscrito ao tópico: {topic}")
        else:
            print(f"Falha na conexão MQTT: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback de desconexão MQTT"""
        self.connected = False
        print("Desconectado do broker MQTT")

    def _on_message(self, client, userdata, msg):
        """Callback de mensagem recebida"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())

            print(
                f"MQTT Recebido [{topic}]: {payload.get('sensor_id', payload.get('actuator_id', 'unknown'))}"
            )

            # Processa mensagem baseado no tópico
            if "sensors" in topic:
                self._process_sensor_data(payload)
            elif "actuators" in topic:
                self._process_actuator_data(payload)
            elif "alerts" in topic:
                self._process_alert(payload)

        except Exception as e:
            print(f"Erro ao processar mensagem MQTT: {e}")

    def _process_sensor_data(self, data: Dict):
        """Processa dados de sensor via MQTT"""
        try:
            # Envia para API HTTP como backup/integração
            response = requests.post(f"{self.api_url}/iot/sensor", json=data, timeout=2)
            if response.status_code == 201:
                print(f"Sensor {data['sensor_id']}: Dados processados via MQTT+HTTP")
        except requests.exceptions.RequestException:
            print(
                f"Falha HTTP para sensor {data['sensor_id']}, dados via MQTT apenas"
            )

    def _process_actuator_data(self, data: Dict):
        """Processa dados de atuador via MQTT"""
        try:
            # Envia para API HTTP como backup/integração
            response = requests.post(
                f"{self.api_url}/iot/actuator", json=data, timeout=2
            )
            if response.status_code == 201:
                print(
                    f"Atuador {data['actuator_id']}: Dados processados via MQTT+HTTP"
                )
        except requests.exceptions.RequestException:
            print(
                f"Falha HTTP para atuador {data['actuator_id']}, dados via MQTT apenas"
            )

    def _process_alert(self, data: Dict):
        """Processa alertas via MQTT"""
        print(f"Alerta MQTT: {data.get('message', 'Alerta desconhecido')}")

    def connect(self) -> bool:
        """Conecta ao broker MQTT"""
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()

            # Aguarda conexão
            timeout = 5
            while not self.connected and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1

            return self.connected
        except Exception as e:
            # Silencioso - será tratado pelo simulador
            return False

    def disconnect(self):
        """Desconecta do broker MQTT"""
        if self.connected:
            self.client.loop_stop()
            self.client.disconnect()

    def publish_sensor_data(self, sensor_id: str, data: Dict):
        """Publica dados de sensor via MQTT"""
        if self.connected:
            topic = f"visionmoto/sensors/{sensor_id}/data"
            payload = json.dumps(data)
            self.client.publish(topic, payload)
            print(f"MQTT Enviado [{topic}]: {sensor_id}")

    def publish_actuator_data(self, actuator_id: str, data: Dict):
        """Publica dados de atuador via MQTT"""
        if self.connected:
            topic = f"visionmoto/actuators/{actuator_id}/data"
            payload = json.dumps(data)
            self.client.publish(topic, payload)
            print(f"MQTT Enviado [{topic}]: {actuator_id}")

    def publish_alert(self, alert_data: Dict):
        """Publica alerta via MQTT"""
        if self.connected:
            topic = "visionmoto/alerts"
            payload = json.dumps(alert_data)
            self.client.publish(topic, payload)
            print(f"Alerta MQTT enviado: {alert_data.get('message', 'Alerta')}")

    def get_status(self) -> Dict:
        """Retorna status da conexão MQTT"""
        return {
            "connected": self.connected,
            "broker_host": self.broker_host,
            "broker_port": self.broker_port,
            "topics": self.topics,
        }


def main():
    """Teste do cliente MQTT"""
    client = MQTTIoTClient()

    if client.connect():
        print("Cliente MQTT conectado com sucesso")

        # Teste de publicação
        test_data = {
            "sensor_id": "TEST_01",
            "timestamp": datetime.now().isoformat(),
            "temperature": 25.5,
            "status": "online",
        }

        client.publish_sensor_data("TEST_01", test_data)

        # Aguarda mensagens
        time.sleep(5)

        client.disconnect()
    else:
        print("Falha ao conectar cliente MQTT")


if __name__ == "__main__":
    main()
