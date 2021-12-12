FROM python:3.9.4

WORKDIR /usr/src/app

COPY main/requirements.txt ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./main/bot.py" ]