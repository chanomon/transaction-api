FROM python:3.11-slim
#este sera  el directorio de trabajo
WORKDIR /app

# Copiar e instalar dependencias primero (mejora el cache de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del codigo
COPY ./app /app

# Exponer el puerto donde corre la app
EXPOSE 8000

# Comando para iniciar el servidor
# --host 0.0.0.0 permite que el contenedor reciba peticiones desde fuera
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
