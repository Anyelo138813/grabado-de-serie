Version Python de la aplicacion VB
==================================

Compatibilidad:
  - El EXE normal generado con Python 3.12 es para Windows 10/11.
  - Para Windows 7 se debe compilar con Python 3.8.
  - Windows 7 de 32 bits necesita el EXE x86.
  - Windows 7 de 64 bits puede usar x86 o x64; se recomienda x86 si se
    desconoce la arquitectura de todas las computadoras destino.

Ejecutar:
  run_python_app.bat

Tambien se puede abrir desde consola:
  python app.py

Crear EXE para Windows 7:
  1. Instalar Python 3.8.10 de 32 o 64 bits en la computadora de desarrollo.
  2. Para maxima compatibilidad ejecutar:
       build_windows7.bat x86
  3. Para generar exclusivamente la version de 64 bits ejecutar:
       build_windows7.bat x64
  4. Copiar al equipo destino toda la carpeta dist_windows7_x86 o
     dist_windows7_x64, segun corresponda.

Comportamiento migrado:
  - Cliente TCP con IP y puerto configurables.
  - Tipos de codigo SN=15, DSN=16, 3TE=23.
  - Limpieza de datos recibidos dejando solo letras y numeros.
  - Descarte de lecturas que contengan NO READ.
  - Envio del codigo a la primera ventana cuyo titulo empiece con HSmartTest.
  - Guardado de ultima IP/puerto en settings.ini.
  - Log diario en Logs\TcpClientLog_YYYY-MM-DD.txt.

La aplicacion solo usa la biblioteca estandar de Python. PyInstaller se usa
unicamente en la computadora de desarrollo para crear el EXE portable.
