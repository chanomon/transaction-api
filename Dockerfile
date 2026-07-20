FROM python:3.11-slim
#este sera  el directorio de trabajo
WORKDIR /app

# Copiar e instalar dependencias primero (mejora el cache de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

## Hacer grupo y usuario predeterminado para que solo grupo tenga control en la app (así evitamos que sea root por default y evito vulnerabilidad por escalamiento a root y por otro lado dejo el control solo al grupo)
RUN groupadd -g 1000 appgroup && \
	useradd -m -u 1000 -g appgroup appuser

# Copiar el resto del codigo
COPY ./app /app
RUN chown -R appuser:appgroup /app
# con esta línea, /app en el docker pertenece a appgroup 



# Exponer el puerto donde corre la app
EXPOSE 8000

USER appuser 
# de aqui en adelante ejecuta appuser (que está en el grupo appgroup)

# Comando para iniciar el servidor
# --host 0.0.0.0 permite que el contenedor reciba peticiones desde fuera
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
