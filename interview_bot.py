import openai
from config import configure_openai

configure_openai()

def generate_interview_questions(role):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un entrenador de entrevistas de trabajo."},
            {"role": "user", "content": f"Genera 5 preguntas comunes para una entrevista de trabajo para el rol de {role}."}
        ],
        max_tokens=200
    )
    return response['choices'][0]['message']['content'].strip()


