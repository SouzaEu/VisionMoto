# VisionMoto - Sistema para Gestão de Motos

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-green.svg)](https://opencv.org/)
[![YOLO](https://img.shields.io/badge/YOLO-v8-red.svg)](https://ultralytics.com/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-orange.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com/)

> Sistema de visão computacional e IoT para detecção, rastreamento e gestão de motocicletas em pátios. Projeto desenvolvido no contexto do Challenge FIAP 2025.

---

## Visão Geral

O VisionMoto combina:
- Visão computacional (YOLO v8) para detecção de motos
- APIs REST para integrações
- Dashboard web para monitoramento
- Relatórios e estatísticas

### **Problema Resolvido**
Automatização completa do controle de pátios da Mottu através de visão computacional, eliminando processos manuais e aumentando precisão operacional.

---

## Execução e Acesso

### Endereços
- **API Principal:** `http://localhost:5001`
- **Dashboard IoT:** `http://localhost:5001/dashboard`
- **Health Check:** `http://localhost:5001/health`
- **Integração Mobile:** `http://localhost:5001/api/mobile/*`

---

## Tecnologias

### **Backend & APIs**
- **Python 3.9+** - Linguagem principal
- **Flask 2.3+** - Framework web
- **SQLite** - Banco de dados integrado
- **OpenCV 4.8+** - Processamento de imagem
- **YOLO v8** - Detecção de objetos

### **IoT & Visão Computacional**
- **Ultralytics YOLO** - Modelo de detecção
- **OpenCV** - Processamento de vídeo
- **NumPy** - Computação científica
- **Pillow** - Manipulação de imagens

### **DevOps & Deploy**
- **Docker** - Containerização
- **GitHub Actions** - CI/CD
- **pytest** - Testes automatizados

---

## Funcionalidades

### Sistema de Visão Computacional
- Detecção de motos com YOLO v8
- Rastreamento
- Análise de vídeo e imagens
- Contagem automática
- Detecção de movimento e ocupação

### APIs REST
- Mobile API (`/api/mobile/*`)
- Java API (`/api/java/*`)
- .NET API (`/api/dotnet/*`)
- Database API (`/api/database/*`)
- IoT API (`/api/iot/*`)
- Health checks

### Dashboard
- Mapa visual do pátio
- Visualização e estatísticas
- Alertas e histórico

### Integração
- Integrações via endpoints dedicados por cliente

### Banco de Dados
- SQLite para desenvolvimento
- Backup

---

## Arquitetura

### **Padrões Aplicados:**
- **MVC** - Separação de responsabilidades
- **REST API** - Comunicação padronizada
- **Observer Pattern** - Notificações em tempo real
- **Factory Pattern** - Criação de objetos
- **Singleton** - Gerenciamento de recursos

### Princípios
- Separação de responsabilidades
- APIs específicas por cliente

---

## Como Executar

### Pré-requisitos
- Python 3.9+
- pip

### **Instalação Rápida:**

```bash
# 1. Clone o repositório
git clone https://github.com/VisionMoto/VisionMoto.git
cd VisionMoto

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Execute o sistema completo
python start_integration.py
```

### Modos de Execução

#### Sistema Completo
```bash
python start_integration.py
# API REST em http://localhost:5001
# Dashboard em http://localhost:5001/dashboard
# Integrações ativas
```

#### Demonstração Visual
```bash
python visionmoto.py demo
# Interface com detecção
# Processamento de vídeo
```

#### API Backend
```bash
python visionmoto.py backend
# Apenas APIs REST
```

#### Testes
```bash
pytest tests/ -v
# Testes
```

---

## Endpoints

### Mobile
- `GET /api/mobile/motos` - Lista motos detectadas
- `GET /api/mobile/dashboard` - Estatísticas para mobile
- `POST /api/mobile/sync` - Sincronização de dados

### Java
- `GET /api/java/health` - Health check Java
- `POST /api/java/motos` - Recebe dados do Java
- `GET /api/java/dashboard` - Dashboard para Java

### Database
- `GET /api/database/motos` - Consulta banco
- `POST /api/database/backup` - Backup automático
- `GET /api/database/stats` - Estatísticas do banco

### IoT
- `GET /api/iot/sensors` - Status dos sensores
- `POST /api/iot/data` - Dados dos sensores
- `GET /api/iot/alerts` - Alertas ativos

### Monitoring
- `GET /health` - Health check geral
- `GET /dashboard` - Interface web
- `GET /metrics` - Métricas do sistema

---

## Estrutura do Projeto

```text
VisionMoto/
├── src/                          # Código fonte
│   ├── backend/                  # API
│   ├── routes/                   # Blueprints/rotas
│   ├── services/                 # Serviços
│   ├── models/                   # Modelos
│   └── iot/                      # IoT
├── demos/                        # Demonstrações
│   └── demo_final.py               # Demo completa
├── tests/                        # Testes
├── integration/                  # Documentação de integração
│   ├── mobile/                     # Docs Mobile
│   ├── java/                       # Docs Java
│   └── dotnet/                     # Docs .NET
├── assets/                       # Recursos
│   └── sample_video.mp4            # Vídeo de exemplo
├── .github/workflows/            # CI/CD
│   └── ci.yml                      # Pipeline automatizado
├── Dockerfile                    # Container Docker
├── docker-compose.yml            # Orquestração
├── requirements.txt              # Dependências Python
├── pytest.ini                    # Configuração de testes
├── start_integration.py          # Script de inicialização
├── visionmoto.py                 # Script principal
└── README.md                     # Documentação
```

---

## Integração Multidisciplinar

### **Disciplinas Aplicadas:**

#### Mobile
- APIs REST otimizadas para React Native
- Endpoints de sincronização em tempo real
- Dados formatados para consumo mobile
- Notificações push integradas

#### Java
- Integração bidirecional com Spring Boot
- Sincronização de dados de motos
- Health checks e monitoramento
- APIs REST padronizadas

#### Database
- Modelos de dados otimizados
- Análise de padrões de uso
- Relatórios automatizados
- Backup e recovery

#### DevOps
- Pipeline CI/CD automatizado
- Containerização com Docker
- Deploy em nuvem
- Monitoramento contínuo

---

## Evidências e Documentação

### Demonstrações
- Dashboard web
- Detecção em tempo real
- Endpoints de integração

### Métricas
- Métricas de performance podem ser consultadas na documentação de testes.

### Qualidade
- Testes com `pytest`
- Formatação e lint via ferramentas do projeto

---

## Equipe

| Nome | RM | Função | GitHub |
|------|----|---------|---------| 
| **Vinicius Souza Carvalho** | 556089 | Tech Lead & IoT | [@SouzaEu](https://github.com/SouzaEu) |
| **Thomaz Oliveira Vilas Boas Bartol** | 555323 | Backend & Vision | [@ThomazBartol](https://github.com/ThomazBartol) |
| **Gabriel Duarte** | 556972 | Frontend & Integration | [@gabrielduart7](https://github.com/gabrielduart7) |

---

## Notas

### **Inovação Tecnológica:**
- **YOLO v8** - Modelo de detecção
- **Tempo Real** - Processamento < 100ms
- **Multi-API** - Integração com 4 disciplinas
- **Analytics** - Insights automatizados

### **Alinhamento com Mottu:**
- **Problema Real** - Gestão automatizada de pátios
- **Solução Prática** - Redução de 90% do trabalho manual
- **ROI Mensurável** - Economia comprovada
- **Escalabilidade** - Suporte a múltiplos pátios

---

## Troubleshooting

### **Problemas Comuns:**

#### **Erro de Dependências**
```bash
# Solução:
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

#### **Modelo YOLO não encontrado**
```bash
# Solução:
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

#### **Porta já em uso**
```bash
# Verificar processos:
lsof -i :5001
# Matar processo:
kill -9 <PID>
```

#### **Webcam não detectada**
```bash
# Usar vídeo de exemplo:
python visionmoto.py demo --source assets/sample_video.mp4
```

---

## Contato

- **Email:** equipe.visionmoto@fiap.com.br
- **Discord:** VisionMoto Team
- **WhatsApp:** Grupo da equipe
- **Issues:** [GitHub Issues](https://github.com/VisionMoto/VisionMoto/issues)

---

## Licença

Este projeto está licenciado sob a **MIT License** - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

 
