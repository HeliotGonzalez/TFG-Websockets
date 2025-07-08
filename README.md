# TFG Websockets

Servidor de WebSocket en Python con integración de Redis. Permite mantener conexiones por usuario y reenviar eventos recibidos por pub/sub a través de WebSocket.

## Requisitos

- Python 3.10 o superior
- [websockets](https://pypi.org/project/websockets/)
- [redis](https://pypi.org/project/redis/) (con soporte asyncio)

Puedes instalar las dependencias básicas con:

```bash
pip install websockets redis
```

Necesitas tener un servidor de Redis accesible, en mi caso desde Docker, en la dirección indicada en `config.py` (`REDIS_URL`).

## Ejecución

```bash
python main.py
```

El servidor escuchará por defecto en `0.0.0.0:8765`. Cada cliente debe conectarse usando un identificador de usuario, por ejemplo:

```
ws://localhost:8765/?user=123
```

Si la conexión está inactiva durante 30 segundos se cerrará automáticamente.

## Funcionamiento

- `main.py` inicia el servidor WebSocket y un "listener" de Redis que se mantiene activo incluso si la conexión a Redis se interrumpe.
- `app/connection_manager.py` gestiona las conexiones abiertas por usuario y ofrece un `broadcast` para enviar eventos a los clientes conectados.
- `app/redis_listener.py` se subscribe a los canales definidos en `config.py` y reenvía a los usuarios los mensajes JSON recibidos.
- `app/events.py` contiene los tipos de eventos soportados.

Para que un mensaje se envíe a un usuario concreto, debe incluir la clave `to` con el identificador del usuario destino. Por ejemplo:

```json
{"from": 20, "to": 42, "text": "hola"}
```

## Estructura del proyecto

```
app/
  connection_manager.py  # gestiona conexiones por usuario
  events.py              # enumeración de eventos
  redis_listener.py      # escucha pub/sub de Redis y reenvía eventos
config.py                # configuración de puertos y canales
main.py                  # punto de entrada del servidor
```
