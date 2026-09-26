# Dashboard R2

Interfaz web estatica para consultar eventos del TCP Client desde archivos JSON.

## Uso local

Desde esta carpeta:

```powershell
python -m http.server 8080
```

Abrir:

```text
http://127.0.0.1:8080
```

## Uso con R2

Cuando exista un JSON publico en R2:

```text
https://tu-dominio-r2/events/latest.json
```

abrir el dashboard con:

```text
http://127.0.0.1:8080/?data=https://tu-dominio-r2/events/latest.json
```

El JSON puede ser un arreglo de eventos o un objeto con propiedad `events`.

Formato esperado:

```json
[
  {
    "event_time": "2026-09-26T14:55:01.452",
    "line_id": "LINEA_1",
    "event_type": "sent",
    "code_type": "SN",
    "code": "55N2617FNH00336",
    "message": "window=ok edit=ok set_text=ok enter_down=ok enter_up=ok",
    "ip": "192.168.1.10",
    "port": "6000"
  }
]
```
