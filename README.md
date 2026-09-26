# Grabado de serie - TCP Client Hisense

Aplicacion Python/Tkinter para recibir codigos por TCP, validar el tipo de codigo y enviarlo a HSmartTest.

## Componentes

- `app.py`: interfaz principal del cliente TCP.
- `tcp_client_app.py`: conexion, reconexion, recepcion y validacion TCP.
- `send_keys_manager.py`: envio del codigo hacia la ventana HSmartTest.
- `tcp_port_simulator.py`: simulador TCP para pruebas.
- `hsmarttest_simulator.py`: simulador basico de HSmartTest.
- `build_windows7.bat`: empaquetado con PyInstaller para Windows 7.

## Notas

La aplicacion genera logs locales en `Logs/`. Esa carpeta no se sube a GitHub.

Tambien se excluyen builds, ejecutables, entornos virtuales y caches para mantener el repositorio ligero.
