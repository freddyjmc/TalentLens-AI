from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QTextEdit, QPushButton, QWidget
import sys
from config import configure_openai
import openai

class AssistantWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Asistente de Trabajo")
        self.setGeometry(100, 100, 600, 400)

        # Configuración de OpenAI
        configure_openai()

        # Widgets principales
        self.central_widget = QWidget()
        self.layout = QVBoxLayout(self.central_widget)

        self.input_text = QTextEdit(self)
        self.input_text.setPlaceholderText("Escribe tu pregunta o solicitud aquí...")

        self.output_text = QTextEdit(self)
        self.output_text.setReadOnly(True)

        self.submit_button = QPushButton("Enviar", self)
        self.submit_button.clicked.connect(self.handle_input)

        # Agregar widgets al layout
        self.layout.addWidget(self.input_text)
        self.layout.addWidget(self.submit_button)
        self.layout.addWidget(self.output_text)

        self.setCentralWidget(self.central_widget)

    def handle_input(self):
        user_input = self.input_text.toPlainText().strip()
        if not user_input:
            self.output_text.setText("Por favor, escribe algo para interactuar.")
            return

        # Llamada a OpenAI
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un asistente especializado en temas de trabajo, CVs, cursos, y sugerencias de mejoras profesionales."},
                    {"role": "user", "content": user_input}
                ],
                max_tokens=500
            )
            self.output_text.setText(response['choices'][0]['message']['content'].strip())
        except Exception as e:
            self.output_text.setText(f"Error al procesar la solicitud: {e}")

def launch_assistant():
    app = QApplication(sys.argv)
    window = AssistantWindow()
    window.show()
    sys.exit(app.exec_())
