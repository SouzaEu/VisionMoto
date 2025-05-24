# 🎥 VisionMoto - Sistema de Detecção e Rastreamento de Motos com Visão Computacional

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green)](https://opencv.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-red)](https://github.com/ultralytics/ultralytics)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

VisionMoto é uma solução open source para detecção e rastreamento de motos utilizando visão computacional. O projeto implementa dois métodos diferentes de detecção: OpenCV com MobileNet SSD e YOLOv8, permitindo flexibilidade na escolha do método mais adequado para cada caso de uso.

## ✨ Características

- Detecção de motos em tempo real usando câmeras comuns
- Múltiplos métodos de detecção (OpenCV + MobileNet SSD e YOLOv8)
- Fácil integração com sistemas existentes
- Baixo custo de implementação
- Compatível com hardware simples

## 🚀 Começando

### Pré-requisitos

- Python 3.11 ou superior
- Webcam ou arquivo de vídeo para teste
- GPU (opcional, mas recomendado para melhor performance)

### Instalação

1. Clone o repositório:
```bash
git clone https://github.com/SouzaEu/visionmoto.git
cd visionmoto
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Baixe o modelo YOLOv8 (se for usar o detector YOLOv8):
```bash
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
```

## 🧪 Uso

### Detecção com OpenCV + MobileNet SSD
```bash
python detection/detect_motos_opencv.py
```

### Detecção com YOLOv8
```bash
python detection/yolov8_detect.py
```

## 🤝 Contribuindo

Contribuições são sempre bem-vindas! Aqui estão algumas maneiras de contribuir:

1. **Reportando Bugs**
   - Abra uma issue descrevendo o bug
   - Inclua passos para reprodução
   - Adicione screenshots se relevante

2. **Sugerindo Melhorias**
   - Abra uma issue com a tag "enhancement"
   - Descreva a melhoria proposta
   - Explique por que seria útil

3. **Pull Requests**
   - Fork o projeto
   - Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
   - Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
   - Push para a branch (`git push origin feature/AmazingFeature`)
   - Abra um Pull Request

## 📁 Estrutura do Projeto

```
visionmoto/
├── detection/
│   ├── detect_motos_opencv.py
│   ├── yolov8_detect.py
│   ├── MobileNetSSD_deploy.prototxt
│   └── MobileNetSSD_deploy.caffemodel
├── assets/
│   └── sample_video.mp4
├── requirements.txt
├── README.md
└── LICENSE
```

## 📝 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🙏 Agradecimentos

- [OpenCV](https://opencv.org/) pela biblioteca de visão computacional
- [Ultralytics](https://github.com/ultralytics/ultralytics) pelo YOLOv8
- Todos os contribuidores que ajudaram no projeto