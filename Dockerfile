FROM python:3.10 
WORKDIR /app

RUN apt-get update && apt-get install -y 
COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt 
COPY google_cloud_aiplatform-1.71.dev20241017+vertex.agents.v2-py2.py3-none-any.whl /app/
RUN pip install /app/google_cloud_aiplatform-1.71.dev20241017+vertex.agents.v2-py2.py3-none-any.whl
COPY . . 
EXPOSE 8080
CMD [ "python3", "main.py" ] 