from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

def generate_design_pdf(filename):
    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=colors.HexColor("#2E7D32"),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor("#388E3C"),
        alignment=TA_LEFT,
        spaceBefore=15,
        spaceAfter=10
    )

    elements = []

    # Title
    elements.append(Paragraph("Especificação Técnica: Arquitetura de Software", title_style))
    elements.append(Paragraph("Estrutura do Núcleo de Inteligência e Processamento de Bordas", styles['Italic']))
    elements.append(Spacer(1, 20))

    # 1. Pipeline de Dados Assíncrono
    elements.append(Paragraph("1. Pipeline de Dados Assíncrono", subtitle_style))
    elements.append(Paragraph(
        "A arquitetura é baseada em um pipeline desacoplado para garantir latência mínima na interface visual "
        "independente da carga de processamento da IA.",
        styles['BodyText']
    ))
    
    pipeline_data = [
        ["Estágio", "Ação", "Responsabilidade"],
        ["Ingestão", "Captura Dual (Térmica + RGB)", "SensorManager"],
        ["Sincronia", "Alinhamento por Timestamps", "SyncEngine"],
        ["Inferência", "Detecção YOLOv8 (ROI)", "DetectionWorker"],
        ["Ação", "Orquestração de Alertas", "AlertManager"]
    ]
    t = Table(pipeline_data, colWidths=[100, 180, 180])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#388E3C")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    elements.append(t)

    # 2. Componentização (Python Core)
    elements.append(Paragraph("2. Componentização e Serviços", subtitle_style))
    elements.append(Paragraph("<b>DetectionWorker:</b> Thread isolado para execução do YOLOv8 via ONNX/TensorRT.", styles['BodyText']))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph("<b>StateStore:</b> Repositório reativo de estado (Detecções, Alertas e Status dos Sensores).", styles['BodyText']))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph("<b>AudioService:</b> Motor sonoro com frequências variáveis baseado no nível de risco.", styles['BodyText']))

    # 3. Resiliência e Segurança Operacional
    elements.append(Paragraph("3. Resiliência e Segurança", subtitle_style))
    res_data = [
        ["Falha Detectada", "Ação de Mitigação", "Status do Sistema"],
        ["Perda Sensor Térmico", "Ativação Modo RGB Puro", "Modo Degradado (Aviso)"],
        ["Travamento da IA", "Watchdog Reset Automático", "Recuperação em <1s"],
        ["Baixa Bateria (Mobile)", "Redução de FPS da Inferência", "Modo Econômico"]
    ]
    t2 = Table(res_data, colWidths=[130, 200, 130])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#C8E6C9")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t2)

    # 4. Tecnologias Core
    elements.append(Paragraph("4. Tecnologias Core", subtitle_style))
    elements.append(Paragraph("- <b>Linguagem:</b> Python 3.11+ (Portabilidade Total)", styles['BodyText']))
    elements.append(Paragraph("- <b>Visão Computacional:</b> OpenCV + ONNX Runtime", styles['BodyText']))
    elements.append(Paragraph("- <b>Interface:</b> Kivy / OpenGL (Performance Gráfica)", styles['BodyText']))

    # Footer
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("<i>Documento de Engenharia - Antigravity AI Designer</i>", styles['Normal']))

    doc.build(elements)

if __name__ == "__main__":
    generate_design_pdf("Design_Tecnico_e_Arquitetura_Software.pdf")
    print("PDF de Design Técnico gerado com sucesso.")
